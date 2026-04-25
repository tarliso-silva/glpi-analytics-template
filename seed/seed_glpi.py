"""
GLPI Realistic Service Desk Simulation Seed
============================================
Gera ~950 tickets realistas ao longo de 24 meses (Jan/2024 – Dez/2025)
com dimensões completas: usuários, grupos, categorias, SLAs e
relacionamentos via glpi_tickets_users e glpi_groups_tickets.

Objetivo: suportar análises avançadas de Power BI (SLA, backlog,
produtividade por técnico, tendências, análise por categoria/grupo).

Uso:
    python src/seed_glpi.py
"""
import mysql.connector
import random
import math
from datetime import datetime, timedelta
from collections import defaultdict

# Seed fixo para resultados reproduzíveis
random.seed(42)

# ── Conexão ─────────────────────────────────────────────────────────────────
conn = mysql.connector.connect(
    host="localhost", port=3306,
    database="glpi", user="glpi", password="glpi",
)
conn.autocommit = False
cur = conn.cursor()

# ── Constantes ───────────────────────────────────────────────────────────────
NOW        = datetime(2026, 4, 24)
SEED_START = datetime(2024, 1, 1)
SEED_END   = datetime(2025, 12, 31, 23, 59, 59)

def ts(dt):
    """Converte datetime em string MySQL ou retorna None."""
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None

def rand_work_dt(start: datetime, end: datetime) -> datetime:
    """Datetime aleatório com 85% de chance em horário comercial (8-18h, Seg-Sex)."""
    delta_sec = max(1, int((end - start).total_seconds()))
    if random.random() < 0.85:
        delta_days = max(1, (end - start).days)
        for _ in range(50):                      # tenta até 50x
            d = start + timedelta(days=random.randint(0, delta_days))
            if d.weekday() < 5:                  # weekday
                h = random.randint(8, 17)
                m = random.randint(0, 59)
                s = random.randint(0, 59)
                dt = d.replace(hour=h, minute=m, second=s)
                if start <= dt <= end:
                    return dt
    # fallback: qualquer horário
    return start + timedelta(seconds=random.randint(0, delta_sec))

# ════════════════════════════════════════════════════════════════════════════
print("=" * 62)
print("  GLPI SERVICE DESK SIMULATION — SEED v2.0")
print("  Período: Jan/2024 – Dez/2025 | ~950 tickets")
print("=" * 62)

# ── STEP 0: Lê perfis e request types existentes ────────────────────────────
cur.execute("SELECT id, name FROM glpi_profiles ORDER BY id")
profiles = {row[1]: row[0] for row in cur.fetchall()}
print(f"\n[0/7] Perfis encontrados: {list(profiles.keys())}")

TECH_PROFILE     = profiles.get("Technician") or profiles.get("Super-Admin") or 4
SELF_SVC_PROFILE = profiles.get("Self-Service") or profiles.get("Helpdesk") or 1
print(f"      tech_profile={TECH_PROFILE}, self_service_profile={SELF_SVC_PROFILE}")

# Request types (canais de abertura)
try:
    cur.execute("SELECT id FROM glpi_requesttypes ORDER BY id LIMIT 8")
    req_rows = cur.fetchall()
    REQ_TYPES = [r[0] for r in req_rows] if req_rows else [1, 2, 5]
except Exception:
    REQ_TYPES = [1, 2, 5]
print(f"      Request types: {REQ_TYPES}")

# ════════════════════════════════════════════════════════════════════════════
# STEP 1 — Limpeza (idempotente)
# ════════════════════════════════════════════════════════════════════════════
print("\n[1/7] Limpando dados anteriores...")

for stmt in [
    "DELETE FROM glpi_groups_tickets",
    "DELETE FROM glpi_tickets_users",
    "DELETE FROM glpi_tickets",
]:
    cur.execute(stmt)

# Remove usuários de simulação (id > 2, preserva admin glpi)
cur.execute("SELECT id FROM glpi_users WHERE id > 2")
old_users = [r[0] for r in cur.fetchall()]
if old_users:
    ph = ",".join(["%s"] * len(old_users))
    cur.execute(f"DELETE FROM glpi_profiles_users WHERE users_id IN ({ph})", old_users)
    cur.execute(f"DELETE FROM glpi_groups_users  WHERE users_id IN ({ph})", old_users)
    cur.execute(f"DELETE FROM glpi_useremails    WHERE users_id IN ({ph})", old_users)
    cur.execute(f"DELETE FROM glpi_users          WHERE id        IN ({ph})", old_users)

cur.execute("DELETE FROM glpi_groups")
cur.execute("DELETE FROM glpi_itilcategories")
cur.execute("DELETE FROM glpi_slas")
cur.execute("DELETE FROM glpi_slms")
conn.commit()
print("      Feito.")

# ════════════════════════════════════════════════════════════════════════════
# STEP 2 — Grupos (equipes de suporte)
# ════════════════════════════════════════════════════════════════════════════
print("\n[2/7] Criando grupos...")

GROUP_DEFS = [
    # (nome, código, descrição)
    ("Infraestrutura",         "INF", "Equipe de infraestrutura física e servidores"),
    ("Sistemas",               "SIS", "Equipe de sistemas, aplicações e ERP"),
    ("Redes e Conectividade",  "RED", "Equipe de redes, LAN/WAN, VPN e Wi-Fi"),
]

group_ids = {}  # código → id no banco
for name, code, comment in GROUP_DEFS:
    cur.execute("""
        INSERT INTO glpi_groups
            (name, completename, code, comment,
             entities_id, is_recursive, level, groups_id,
             is_assign, is_requester, is_usergroup, is_watcher, is_manager,
             date_creation, date_mod)
        VALUES (%s, %s, %s, %s,
                0, 1, 1, 0,
                1, 0, 1, 1, 1,
                NOW(), NOW())
    """, (name, name, code, comment))
    gid = cur.lastrowid
    group_ids[code] = gid
    print(f"      {code}: {name} → id={gid}")

conn.commit()

# ════════════════════════════════════════════════════════════════════════════
# STEP 3 — Usuários (técnicos + solicitantes)
# ════════════════════════════════════════════════════════════════════════════
print("\n[3/7] Criando usuários...")

# ── Técnicos ─────────────────────────────────────────────────────────────────
# (login, nome, sobrenome, grupo, senioridade)
# Senioridade determina o peso de tickets atribuídos
TECHNICIANS = [
    # Infraestrutura (4 técnicos)
    ("sim_carlos.oliveira",  "Carlos",   "Oliveira",  "INF", "senior"),
    ("sim_ana.lima",         "Ana",      "Lima",      "INF", "mid"),
    ("sim_roberto.santos",   "Roberto",  "Santos",    "INF", "mid"),
    ("sim_fernanda.costa",   "Fernanda", "Costa",     "INF", "junior"),
    # Sistemas (4 técnicos)
    ("sim_lucas.pereira",    "Lucas",    "Pereira",   "SIS", "senior"),
    ("sim_mariana.ferreira", "Mariana",  "Ferreira",  "SIS", "mid"),
    ("sim_paulo.rodrigues",  "Paulo",    "Rodrigues", "SIS", "mid"),
    ("sim_juliana.alves",    "Juliana",  "Alves",     "SIS", "junior"),
    # Redes (3 técnicos)
    ("sim_rodrigo.mendes",   "Rodrigo",  "Mendes",    "RED", "senior"),
    ("sim_camila.souza",     "Camila",   "Souza",     "RED", "mid"),
    ("sim_diego.barbosa",    "Diego",    "Barbosa",   "RED", "junior"),
]

SENIORITY_WEIGHT = {"senior": 3.5, "mid": 1.8, "junior": 0.7}

# ── Solicitantes (50 usuários finais) ────────────────────────────────────────
REQUESTER_NAMES = [
    ("João",     "Almeida"),    ("Maria",   "Nascimento"), ("Pedro",    "Cardoso"),
    ("Sofia",    "Martins"),    ("André",   "Correia"),    ("Beatriz",  "Carvalho"),
    ("Miguel",   "Gomes"),      ("Laura",   "Pinto"),      ("Tiago",    "Moreira"),
    ("Inês",     "Rocha"),      ("Rui",     "Azevedo"),    ("Catarina", "Melo"),
    ("Bruno",    "Fonseca"),    ("Marta",   "Lopes"),      ("Hugo",     "Dias"),
    ("Filipa",   "Fernandes"),  ("Nuno",    "Cruz"),        ("Rita",     "Monteiro"),
    ("Marco",    "Borges"),     ("Isabel",  "Andrade"),    ("Diogo",    "Teixeira"),
    ("Alice",    "Magalhães"),  ("Luís",    "Marques"),    ("Vera",     "Coelho"),
    ("Rafael",   "Machado"),    ("Susana",  "Pires"),      ("Gonçalo",  "Vaz"),
    ("Paula",    "Reis"),       ("Sérgio",  "Brito"),      ("Cláudia",  "Vieira"),
    ("Vítor",    "Nunes"),      ("Helena",  "Cunha"),      ("Artur",    "Leite"),
    ("Raquel",   "Sousa"),      ("Fábio",   "Castro"),     ("Cristina", "Duarte"),
    ("Dinis",    "Ferreira"),   ("Patrícia","Morais"),     ("Joel",     "Ramos"),
    ("Vanessa",  "Silva"),      ("Tomás",   "Henriques"),  ("Carla",    "Esteves"),
    ("Eduardo",  "Figueiredo"), ("Sandra",  "Baptista"),   ("Renato",   "Mendonça"),
    ("Ana Rita", "Pedrosa"),    ("Álvaro",  "Miranda"),    ("Teresa",   "Godinho"),
    ("Lúcio",    "Amaro"),      ("Graça",   "Tavares"),
]

tech_pool   = []   # [(user_id, grp_code, weight), ...]
requester_ids = []

def _insert_user(login, firstname, lastname, email, profile_id):
    cur.execute("""
        INSERT INTO glpi_users
            (name, firstname, realname,
             is_active, entities_id, authtype, auths_id,
             is_deleted, date_creation, date_mod)
        VALUES (%s, %s, %s,
                1, 0, 1, 0,
                0, NOW(), NOW())
    """, (login, firstname, lastname))
    uid = cur.lastrowid
    # E-mail vai em tabela separada no GLPI
    cur.execute("""
        INSERT INTO glpi_useremails
            (users_id, is_default, is_dynamic, email)
        VALUES (%s, 1, 0, %s)
    """, (uid, email))
    cur.execute("""
        INSERT INTO glpi_profiles_users
            (users_id, profiles_id, entities_id, is_recursive, is_dynamic)
        VALUES (%s, %s, 0, 1, 0)
    """, (uid, profile_id))
    return uid

# Insere técnicos
for login, firstname, lastname, grp_code, seniority in TECHNICIANS:
    base = login.replace("sim_", "")
    email = f"{base}@empresa.com.br"
    uid = _insert_user(login, firstname, lastname, email, TECH_PROFILE)
    cur.execute("""
        INSERT INTO glpi_groups_users
            (users_id, groups_id, is_dynamic, is_manager)
        VALUES (%s, %s, 0, 0)
    """, (uid, group_ids[grp_code]))
    tech_pool.append((uid, grp_code, SENIORITY_WEIGHT[seniority]))
    print(f"      Tech {grp_code}: {firstname} {lastname} → id={uid}")

# Insere solicitantes
for i, (firstname, lastname) in enumerate(REQUESTER_NAMES):
    login = f"sim_req_{i+1:02d}"
    base  = f"{firstname.lower().replace(' ', '.')}.{lastname.lower()}"
    email = f"{base}@empresa.com.br"
    uid   = _insert_user(login, firstname, lastname, email, SELF_SVC_PROFILE)
    requester_ids.append(uid)

conn.commit()
print(f"      {len(tech_pool)} técnicos | {len(requester_ids)} solicitantes criados.")

# ════════════════════════════════════════════════════════════════════════════
# STEP 4 — Categorias ITIL (hierárquicas)
# ════════════════════════════════════════════════════════════════════════════
print("\n[4/7] Criando categorias ITIL hierárquicas...")

# estrutura: nome_pai → {grupo_responsável, filhos[]}
CATEGORY_TREE = {
    "Hardware": {
        "group": "INF",
        "children": [
            "Desktop / Workstation", "Notebook",
            "Impressora / Scanner", "Monitor / Periféricos", "Dispositivo Móvel",
        ],
    },
    "Software": {
        "group": "SIS",
        "children": [
            "Sistema Operacional", "Aplicações de Negócio",
            "E-mail e Colaboração", "ERP / CRM",
        ],
    },
    "Redes e Conectividade": {
        "group": "RED",
        "children": [
            "Internet / Conectividade", "VPN Corporativa",
            "Wi-Fi", "Rede Local (LAN)",
        ],
    },
    "Segurança": {
        "group": None,  # alternado entre INF e SIS
        "children": [
            "Controle de Acesso", "Redefinição de Senha",
            "Antivírus / Endpoint", "Proteção de Dados",
        ],
    },
    "Serviços de Infraestrutura": {
        "group": "INF",
        "children": [
            "Servidores", "Backup e Storage",
            "Cloud / Virtualização", "Monitoramento",
        ],
    },
}

# Grupos alternativos para Segurança
_SEC_GROUP = {"Controle de Acesso": "INF", "Antivírus / Endpoint": "INF",
              "Redefinição de Senha": "SIS", "Proteção de Dados": "SIS"}

cat_ids      = {}   # nome → id
cat_to_group = {}   # nome → código do grupo

for parent_name, info in CATEGORY_TREE.items():
    cur.execute("""
        INSERT INTO glpi_itilcategories
            (name, completename, entities_id, is_recursive,
             itilcategories_id, level,
             is_helpdeskvisible, is_incident, is_request,
             date_creation, date_mod)
        VALUES (%s, %s, 0, 1, 0, 1, 1, 1, 1, NOW(), NOW())
    """, (parent_name, parent_name))
    pid = cur.lastrowid
    cat_ids[parent_name] = pid
    grp = info["group"]
    if grp:
        cat_to_group[parent_name] = grp

    for child_name in info["children"]:
        completename = f"{parent_name} > {child_name}"
        cur.execute("""
            INSERT INTO glpi_itilcategories
                (name, completename, entities_id, is_recursive,
                 itilcategories_id, level,
                 is_helpdeskvisible, is_incident, is_request,
                 date_creation, date_mod)
            VALUES (%s, %s, 0, 1, %s, 2, 1, 1, 1, NOW(), NOW())
        """, (child_name, completename, pid))
        cid = cur.lastrowid
        cat_ids[child_name] = cid
        cat_to_group[child_name] = grp if grp else _SEC_GROUP.get(child_name, "INF")

    print(f"      {parent_name} (id={pid}) + {len(info['children'])} subcategorias")

conn.commit()
print(f"      {len(cat_ids)} categorias no total.")

# ════════════════════════════════════════════════════════════════════════════
# STEP 5 — SLM + SLAs (por prioridade)
# ════════════════════════════════════════════════════════════════════════════
print("\n[5/7] Criando SLM e SLAs...")

cur.execute("""
    INSERT INTO glpi_slms
        (name, comment, entities_id, is_recursive,
         use_ticket_calendar, calendars_id,
         date_creation, date_mod)
    VALUES ('SLM Corporativo',
            'Gestão de Nível de Serviço corporativo',
            0, 1, 0, 0, NOW(), NOW())
""")
slm_id = cur.lastrowid

# (nome, prioridade, number_time, definition_time, total_minutos)
SLA_DEFS = [
    ("SLA Prioridade Muito Baixa", 1,  5, "day",    7200),
    ("SLA Prioridade Baixa",       2,  3, "day",    4320),
    ("SLA Prioridade Média",       3, 24, "hour",   1440),
    ("SLA Prioridade Alta",        4,  4, "hour",    240),
    ("SLA Prioridade Muito Alta",  5,  2, "hour",    120),
    ("SLA Prioridade Crítica",     6,  1, "hour",     60),
]

sla_ids     = {}   # prioridade → sla_id
sla_minutes = {}   # prioridade → minutos de SLA

for name, prio, number_time, def_time, minutes in SLA_DEFS:
    cur.execute("""
        INSERT INTO glpi_slas
            (name, comment, entities_id, is_recursive,
             type, number_time, definition_time,
             use_ticket_calendar, end_of_working_day,
             slms_id, date_creation, date_mod)
        VALUES (%s, 'TTR – Time to Resolve', 0, 1,
                0, %s, %s,
                0, 0,
                %s, NOW(), NOW())
    """, (name, number_time, def_time, slm_id))
    sid = cur.lastrowid
    sla_ids[prio]     = sid
    sla_minutes[prio] = minutes
    print(f"      Prioridade {prio}: {name} → {minutes} min (id={sid})")

conn.commit()

# ════════════════════════════════════════════════════════════════════════════
# STEP 6 — Geração de Tickets (lógica temporal + SLA + workload)
# ════════════════════════════════════════════════════════════════════════════
print("\n[6/7] Gerando tickets...")

# ── Pool de títulos por categoria ─────────────────────────────────────────────
TITLES = {
    # Hardware
    "Desktop / Workstation": [
        "Computador não liga", "Tela azul (BSOD) frequente",
        "Desempenho muito lento", "HD com ruído e erros",
        "Fonte queimada — necessita troca", "Teclado/mouse sem resposta",
        "Computador reiniciando sozinho",
    ],
    "Notebook": [
        "Notebook não carrega a bateria", "Tela do notebook piscando",
        "Notebook superaquecendo e desligando", "Tela quebrada",
        "Teclas travando no teclado do notebook", "Notebook lento após formatação",
    ],
    "Impressora / Scanner": [
        "Impressora offline na rede", "Papel enroscado na impressora",
        "Qualidade de impressão degradada", "Scanner não reconhecido pelo sistema",
        "Impressora não imprime após atualização de driver",
    ],
    "Monitor / Periféricos": [
        "Monitor sem sinal de vídeo", "Webcam não funciona em videochamadas",
        "Headset com falha no microfone", "Monitor com listras horizontais",
        "Pendrive não reconhecido pelo Windows",
    ],
    "Dispositivo Móvel": [
        "Celular corporativo sem acesso ao e-mail", "App corporativo travando no celular",
        "MDM não está sincronizando o dispositivo",
    ],
    # Software
    "Sistema Operacional": [
        "Windows não inicia corretamente", "Atualização do Windows travada/falhando",
        "Perfil de usuário corrompido no Windows", "Erro de driver após atualização",
        "Sistema extremamente lento após patch",
    ],
    "Aplicações de Negócio": [
        "Sistema interno não abre", "Erro ao salvar registros no sistema",
        "Relatório não gera corretamente", "Aplicação trava ao processar",
        "Licença do software expirada sem renovação",
    ],
    "E-mail e Colaboração": [
        "Outlook não sincroniza a caixa de entrada", "Não consigo enviar e-mail externo",
        "Acesso ao Microsoft Teams com falha", "Calendário compartilhado fora de sincronia",
        "E-mail retornando com erro de servidor",
    ],
    "ERP / CRM": [
        "ERP travando no módulo financeiro", "Erro ao emitir nota fiscal eletrônica",
        "CRM não carrega dados do cliente", "Integração ERP-estoque falhando",
        "Relatório do ERP apresentando dados incorretos",
    ],
    # Redes
    "Internet / Conectividade": [
        "Sem acesso à internet no setor", "Conexão à internet muito lenta",
        "Quedas frequentes de link", "Site corporativo inacessível externamente",
    ],
    "VPN Corporativa": [
        "VPN não conecta no home office", "VPN desconecta com frequência",
        "Acesso via VPN muito lento", "Erro de autenticação ao conectar VPN",
    ],
    "Wi-Fi": [
        "Wi-Fi corporativo sem sinal na sala de reunião",
        "Senha do Wi-Fi não aceita no dispositivo",
        "Wi-Fi cai com frequência durante o expediente",
        "Dispositivo não conecta ao SSID corporativo",
    ],
    "Rede Local (LAN)": [
        "Ponto de rede sem sinal no andar", "Switch sem funcionar — vários afetados",
        "Pasta compartilhada de rede inacessível", "Impressora de rede offline (LAN)",
    ],
    # Segurança
    "Controle de Acesso": [
        "Sem permissão para acessar pasta compartilhada",
        "Conta bloqueada no sistema corporativo",
        "Novo colaborador necessita acesso ao sistema",
        "Remover acesso de colaborador desligado — urgente",
    ],
    "Redefinição de Senha": [
        "Senha expirada — não consigo fazer login",
        "Conta bloqueada por tentativas incorretas de senha",
        "Solicitação de reset de senha — esqueci a senha",
    ],
    "Antivírus / Endpoint": [
        "Antivírus detectou ameaça e quarentenou arquivo legítimo",
        "Computador com comportamento suspeito — possível malware",
        "Antivírus não atualiza as definições de vírus",
    ],
    "Proteção de Dados": [
        "Arquivo sigiloso compartilhado indevidamente",
        "Solicitação de backup emergencial de dados críticos",
        "DLP bloqueando envio de e-mail legítimo com anexo",
    ],
    # Infraestrutura
    "Servidores": [
        "Servidor de arquivos inacessível para o setor",
        "Serviço crítico parado no servidor de produção",
        "Servidor com disco em estado crítico de espaço",
        "Alta utilização de CPU no servidor — alerta disparado",
    ],
    "Backup e Storage": [
        "Backup noturno falhou — nenhum arquivo salvo",
        "Restauração de arquivo deletado acidentalmente",
        "Storage com alerta crítico de capacidade",
        "Política de retenção de backup não executou",
    ],
    "Cloud / Virtualização": [
        "VM de produção parada inesperadamente",
        "Migração de VM falhou — dados em risco",
        "Acesso ao ambiente cloud indisponível",
        "Cota de armazenamento cloud atingida — bloqueio",
    ],
    "Monitoramento": [
        "Alerta crítico de monitoramento sem tomada de ação",
        "Serviço de monitoramento (Zabbix/Grafana) com falha",
        "Configurar novo alerta de threshold no monitoramento",
    ],
    # Fallback para categorias-pai
    "Hardware":                   ["Problema de hardware — categoria a definir"],
    "Software":                   ["Problema de software — categoria a definir"],
    "Redes e Conectividade":      ["Problema de rede — categoria a definir"],
    "Segurança":                  ["Incidente/solicitação de segurança"],
    "Serviços de Infraestrutura": ["Chamado de infraestrutura"],
}

# ── Pesos de volume por categoria (quanto cada categoria contribui) ──────────
LEAF_CATS = [c for c in cat_ids if c not in CATEGORY_TREE]
LEAF_WEIGHTS = {
    "Desktop / Workstation":   13,
    "Notebook":                 9,
    "Impressora / Scanner":     5,
    "Monitor / Periféricos":    4,
    "Dispositivo Móvel":        3,
    "Sistema Operacional":     10,
    "Aplicações de Negócio":   11,
    "E-mail e Colaboração":    10,
    "ERP / CRM":                7,
    "Internet / Conectividade": 6,
    "VPN Corporativa":          5,
    "Wi-Fi":                    4,
    "Rede Local (LAN)":         3,
    "Controle de Acesso":       6,
    "Redefinição de Senha":     4,
    "Antivírus / Endpoint":     4,
    "Proteção de Dados":        2,
    "Servidores":               5,
    "Backup e Storage":         4,
    "Cloud / Virtualização":    3,
    "Monitoramento":            2,
}
leaf_names   = list(LEAF_WEIGHTS.keys())
leaf_weights = [LEAF_WEIGHTS[n] for n in leaf_names]

# ── Distribuição de prioridade ────────────────────────────────────────────────
# Peso: P3 (Média) domina, P6 (Crítica) raro
PRIORITY_POOL   = [1]*3 + [2]*10 + [3]*40 + [4]*30 + [5]*12 + [6]*5

# ── Pool de técnicos por grupo (com pesos de senioridade) ────────────────────
tech_by_group = defaultdict(list)
wgt_by_group  = defaultdict(list)
for uid, grp_code, weight in tech_pool:
    tech_by_group[grp_code].append(uid)
    wgt_by_group[grp_code].append(weight)

def pick_tech(grp_code):
    return random.choices(tech_by_group[grp_code], weights=wgt_by_group[grp_code], k=1)[0]

# ── Sazonalidade mensal ───────────────────────────────────────────────────────
SEASON = {
    1: 1.25, 2: 1.20, 3: 1.15,    # Q1: alto (início do ano)
    4: 0.90, 5: 0.88, 6: 0.85,    # Q2: baixo
    7: 1.10, 8: 1.05, 9: 1.00,    # Q3: médio
    10: 0.88, 11: 0.82, 12: 0.80, # Q4: menor (férias/final de ano)
}

# ── Enumera os 24 meses ───────────────────────────────────────────────────────
months = []
dt = SEED_START
while dt <= SEED_END:
    months.append(dt)
    dt = datetime(dt.year + (1 if dt.month == 12 else 0),
                  1 if dt.month == 12 else dt.month + 1, 1)
n_months = len(months)

def tickets_for_month(idx):
    """Volume cresce linearmente de 30 a 60 tickets/mês com sazonalidade."""
    base  = 30 + (idx * 30 / (n_months - 1))
    noise = random.uniform(0.88, 1.12)
    return max(5, int(base * SEASON[months[idx].month] * noise))

# ── Geração ───────────────────────────────────────────────────────────────────
total_inserted   = 0
tickets_per_tech = defaultdict(int)

BATCH_SIZE = 100
ticket_rows  = []
tu_rows      = []   # glpi_tickets_users
gt_rows      = []   # glpi_groups_tickets

for month_idx, month_start in enumerate(months):
    if month_start.month == 12:
        month_end = datetime(month_start.year + 1, 1, 1) - timedelta(seconds=1)
    else:
        month_end = datetime(month_start.year, month_start.month + 1, 1) - timedelta(seconds=1)

    n_tickets = tickets_for_month(month_idx)

    for _ in range(n_tickets):
        created_at = rand_work_dt(month_start, month_end)

        # Categoria e grupo responsável
        cat_name  = random.choices(leaf_names, weights=leaf_weights, k=1)[0]
        cat_id    = cat_ids[cat_name]
        grp_code  = cat_to_group.get(cat_name, "INF")
        group_id  = group_ids[grp_code]

        # Prioridade, urgência, impacto e tipo
        priority    = random.choice(PRIORITY_POOL)
        ticket_type = random.choices([1, 2], weights=[55, 45], k=1)[0]
        urgency     = max(1, min(5, priority + random.randint(-1, 1)))
        impact      = max(1, min(5, priority + random.randint(-1, 1)))

        # Atores
        requester_id = random.choice(requester_ids)
        tech_id      = pick_tech(grp_code)
        tickets_per_tech[tech_id] += 1

        # SLA (82% dos tickets têm SLA)
        has_sla    = random.random() < 0.82
        sla_id     = sla_ids[priority] if has_sla else 0
        sla_dur    = sla_minutes[priority] if has_sla else None

        # ── Lógica de status e datas ─────────────────────────────────────────
        # ~8% dos tickets ficam abertos (backlog persistente: Pending/complexos)
        # Tickets com < 6 meses de idade têm 20% de chance de aberto
        months_ago = (NOW - created_at).days / 30.0
        if random.random() < 0.08:
            outcome = "open"          # backlog independente de idade
        elif months_ago > 6:
            outcome = random.choices(
                ["closed", "solved"], weights=[93, 7], k=1)[0]
        else:
            outcome = random.choices(
                ["closed", "solved", "open"], weights=[55, 25, 20], k=1)[0]

        solvedate        = None
        closedate        = None
        time_to_resolve  = None
        solve_delay      = 0
        close_delay      = 0

        # Prazo de SLA
        if sla_dur:
            time_to_resolve = created_at + timedelta(minutes=sla_dur)

        # TakeIntoAccount: 5–120 min após abertura
        tia_min = random.randint(5, 120)
        takeintoaccountdate = created_at + timedelta(minutes=tia_min)
        tia_delay = tia_min * 60

        if outcome in ("closed", "solved"):
            within_sla = random.random() < 0.75  # 75% conformidade

            if sla_dur:
                if within_sla:
                    resolve_min = int(sla_dur * random.uniform(0.10, 0.92))
                else:
                    resolve_min = int(sla_dur * random.uniform(1.05, 3.5))
            else:
                # Sem SLA: tempo baseado em prioridade
                base_h = {1: 120, 2: 72, 3: 36, 4: 12, 5: 5, 6: 2}
                resolve_min = int(base_h[priority] * 60 * random.uniform(0.3, 2.0))

            solvedate    = created_at + timedelta(minutes=resolve_min)
            solve_delay  = resolve_min * 60

            if outcome == "closed":
                extra_min   = random.randint(30, 2880)          # até 48h após resolve
                closedate   = solvedate + timedelta(minutes=extra_min)
                close_delay = solve_delay + extra_min * 60
                status      = 6
            else:
                status = 5

        else:
            # Ticket aberto
            if   random.random() < 0.35: status = 4   # Pending
            elif random.random() < 0.50: status = 2   # Processing (assigned)
            elif random.random() < 0.50: status = 3   # Processing (planned)
            else:                         status = 1   # New

        # date_mod = data da última atividade
        last_activity = closedate or solvedate or takeintoaccountdate or created_at

        # Título
        title_pool = TITLES.get(cat_name, ["Chamado de suporte técnico"])
        name_ticket = random.choice(title_pool)
        suffixes    = ["", "", "", " - urgente", " (reincidência)"]
        name_ticket += random.choice(suffixes)

        # Canal de abertura
        req_type = random.choice(REQ_TYPES)

        # ── Insert do ticket ─────────────────────────────────────────────────
        cur.execute("""
            INSERT INTO glpi_tickets
                (entities_id, name, date, closedate, solvedate,
                 takeintoaccountdate, date_mod, date_creation,
                 users_id_lastupdater, users_id_recipient, status,
                 content, urgency, impact, priority, type,
                 itilcategories_id, requesttypes_id,
                 slas_id_ttr, time_to_resolve,
                 close_delay_stat, solve_delay_stat,
                 takeintoaccount_delay_stat,
                 waiting_duration, sla_waiting_duration,
                 is_deleted, global_validation, actiontime,
                 tickettemplates_id, locations_id)
            VALUES
                (0, %s, %s, %s, %s,
                 %s, %s, %s,
                 %s, %s, %s,
                 %s, %s, %s, %s, %s,
                 %s, %s,
                 %s, %s,
                 %s, %s, %s,
                 0, 0,
                 0, 1, 0,
                 0, 0)
        """, (
            name_ticket,
            ts(created_at), ts(closedate), ts(solvedate),
            ts(takeintoaccountdate), ts(last_activity), ts(created_at),
            tech_id, requester_id, status,
            (f"Chamado registrado via simulação realista.\n"
             f"Categoria: {cat_name}\nDetalhe: {name_ticket}.\n"
             f"Usuário afetado reportou o problema e aguarda atendimento."),
            urgency, impact, priority, ticket_type,
            cat_id, req_type,
            sla_id, ts(time_to_resolve),
            close_delay, solve_delay, tia_delay,
        ))
        ticket_id = cur.lastrowid

        # ── glpi_tickets_users ────────────────────────────────────────────────
        # type 1 = Requester / type 2 = Assigned tech
        cur.execute("""
            INSERT INTO glpi_tickets_users
                (tickets_id, users_id, type, use_notification)
            VALUES (%s, %s, 1, 1), (%s, %s, 2, 1)
        """, (ticket_id, requester_id, ticket_id, tech_id))

        # ── glpi_groups_tickets ───────────────────────────────────────────────
        # type 2 = Assigned group
        cur.execute("""
            INSERT INTO glpi_groups_tickets
                (tickets_id, groups_id, type)
            VALUES (%s, %s, 2)
        """, (ticket_id, group_id))

        total_inserted += 1

    # Commit a cada mês para não sobrecarregar a transação
    conn.commit()
    print(f"      {month_start.strftime('%b/%Y')}: {n_tickets:3d} tickets "
          f"(total acumulado: {total_inserted})")

# ════════════════════════════════════════════════════════════════════════════
# STEP 7 — Validação e Relatório Final
# ════════════════════════════════════════════════════════════════════════════
print("\n[7/7] Validação dos dados inseridos...")
print("-" * 62)

def qry(sql):
    cur.execute(sql)
    return cur.fetchall()

# Contagens gerais
rows = qry("""
    SELECT 'Tickets' AS obj, COUNT(*) FROM glpi_tickets
    UNION ALL
    SELECT 'Ticket-Usuário',  COUNT(*) FROM glpi_tickets_users
    UNION ALL
    SELECT 'Ticket-Grupo',    COUNT(*) FROM glpi_groups_tickets
    UNION ALL
    SELECT 'Usuários',        COUNT(*) FROM glpi_users WHERE id > 2
    UNION ALL
    SELECT 'Grupos',          COUNT(*) FROM glpi_groups
    UNION ALL
    SELECT 'Categorias',      COUNT(*) FROM glpi_itilcategories
    UNION ALL
    SELECT 'SLAs',            COUNT(*) FROM glpi_slas
""")
for obj, cnt in rows:
    print(f"  {obj:<20s}: {cnt:>6,}")

# Status
print("\n  Distribuição por Status:")
for row in qry("""
    SELECT
        CASE status
            WHEN 1 THEN 'New'
            WHEN 2 THEN 'Processing (assigned)'
            WHEN 3 THEN 'Processing (planned)'
            WHEN 4 THEN 'Pending'
            WHEN 5 THEN 'Solved'
            WHEN 6 THEN 'Closed'
        END, COUNT(*)
    FROM glpi_tickets GROUP BY status ORDER BY status
"""):
    print(f"    {row[0]:<25s}: {row[1]:>5,}")

# SLA compliance
print("\n  SLA Compliance:")
for row in qry("""
    SELECT
        CASE
            WHEN time_to_resolve IS NULL         THEN 'Sem SLA'
            WHEN status IN (5,6)
                 AND solvedate <= time_to_resolve THEN 'Dentro do SLA'
            WHEN status IN (5,6)
                 AND solvedate >  time_to_resolve THEN 'Violado'
            WHEN status NOT IN (5,6)
                 AND time_to_resolve < NOW()      THEN 'Violado (aberto)'
            ELSE                                       'Em risco'
        END AS sla_status,
        COUNT(*) AS total
    FROM glpi_tickets
    GROUP BY sla_status ORDER BY total DESC
"""):
    print(f"    {row[0]:<25s}: {row[1]:>5,}")

# Top 5 técnicos por volume
print("\n  Top 5 Técnicos por Volume:")
for row in qry("""
    SELECT
        CONCAT(u.firstname, ' ', u.realname) AS tecnico,
        g.name AS grupo,
        COUNT(tu.tickets_id) AS total
    FROM glpi_tickets_users tu
    JOIN glpi_users u ON u.id = tu.users_id
    LEFT JOIN glpi_groups_users gu ON gu.users_id = u.id
    LEFT JOIN glpi_groups g ON g.id = gu.groups_id
    WHERE tu.type = 2
    GROUP BY u.id, u.firstname, u.realname, g.name
    ORDER BY total DESC
    LIMIT 5
"""):
    print(f"    {row[0]:<25s} ({row[1]}): {row[2]:>4,} tickets")

# Prioridades
print("\n  Distribuição por Prioridade:")
for row in qry("""
    SELECT
        CASE priority
            WHEN 1 THEN '1-Muito Baixa'
            WHEN 2 THEN '2-Baixa'
            WHEN 3 THEN '3-Média'
            WHEN 4 THEN '4-Alta'
            WHEN 5 THEN '5-Muito Alta'
            WHEN 6 THEN '6-Crítica'
        END, COUNT(*)
    FROM glpi_tickets GROUP BY priority ORDER BY priority
"""):
    print(f"    {row[0]:<20s}: {row[1]:>5,}")

cur.close()
conn.close()
print("\n" + "=" * 62)
print("  SEED CONCLUÍDO COM SUCESSO!")
print(f"  Total de tickets inseridos: {total_inserted:,}")
print("=" * 62)
