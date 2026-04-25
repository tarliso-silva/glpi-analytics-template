"""
Seed estendido — CMDB + Problems + Changes + Projects
Cobre os domínios: ativos de TI, problemas, mudanças e projetos do GLPI.
Pré-requisito: seed_glpi.py já executado (usuários, grupos, tickets existentes).
"""
import mysql.connector
import random
import uuid
from datetime import datetime, timedelta

random.seed(42)

DB = dict(host='localhost', port=3306, database='glpi', user='glpi', password='glpi')
conn = mysql.connector.connect(**DB)
conn.autocommit = False
cur = conn.cursor()

# ─── helpers ──────────────────────────────────────────────────────────────────
def rand_dt(start, end):
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))

def rand_str(start, end):
    return rand_dt(start, end).strftime('%Y-%m-%d %H:%M:%S')

SIM_START = datetime(2024, 1, 1)
SIM_END   = datetime(2025, 12, 31)


# ─── LIMPEZA ──────────────────────────────────────────────────────────────────
print("=" * 68)
print("  Limpando dados estendidos anteriores")
print("=" * 68)

CLEAN_ORDER = [
    'glpi_projecttasks_tickets',
    'glpi_projecttaskteams',
    'glpi_projectteams',
    'glpi_projecttasks',
    'glpi_projects',
    'glpi_changetasks',
    'glpi_changes_items',
    'glpi_changes_users',
    'glpi_changes_tickets',
    'glpi_changes',
    'glpi_items_problems',
    'glpi_groups_problems',
    'glpi_problems_users',
    'glpi_problems_tickets',
    'glpi_problems',
    'glpi_items_tickets',
    'glpi_printers',
    'glpi_monitors',
    'glpi_networkequipments',
    'glpi_computers',
    'glpi_printermodels',
    'glpi_printertypes',
    'glpi_monitormodels',
    'glpi_monitortypes',
    'glpi_networkequipmentmodels',
    'glpi_networkequipmenttypes',
    'glpi_computermodels',
    'glpi_computertypes',
    'glpi_states',
    'glpi_locations',
    'glpi_manufacturers',
]
for tbl in CLEAN_ORDER:
    try:
        cur.execute(f'DELETE FROM `{tbl}`')
        cur.execute(f'ALTER TABLE `{tbl}` AUTO_INCREMENT = 1')
    except Exception as e:
        print(f"  Aviso {tbl}: {e}")
conn.commit()
print("  Limpeza concluída")


# ─── FABRICANTES ──────────────────────────────────────────────────────────────
print("\n[1/8] Fabricantes")
mfr_names = [
    'Dell Technologies', 'HP Inc.', 'Lenovo', 'Cisco Systems',
    'Fortinet', 'Aruba Networks', 'Samsung', 'Brother',
]
cur.executemany(
    "INSERT INTO glpi_manufacturers (name, date_mod, date_creation) VALUES (%s, NOW(), NOW())",
    [(n,) for n in mfr_names]
)
conn.commit()
cur.execute("SELECT id, name FROM glpi_manufacturers")
MFR = {n: i for i, n in cur.fetchall()}
print(f"  {len(MFR)} fabricantes")


# ─── ESTADOS DE ATIVO ─────────────────────────────────────────────────────────
print("\n[2/8] Estados de ativo")
states_def = [
    ('Em uso',         1),
    ('Em manutencao',  1),
    ('Disponivel',     1),
    ('Desativado',     0),
]
for sname, visible in states_def:
    cur.execute("""
        INSERT INTO glpi_states
          (name, completename, entities_id, is_recursive, is_helpdesk_visible,
           states_id, level, ancestors_cache, sons_cache, date_mod, date_creation)
        VALUES (%s, %s, 0, 1, %s, 0, 1, '', '', NOW(), NOW())
    """, (sname, sname, visible))
conn.commit()
cur.execute("SELECT id, name FROM glpi_states")
ST = {n: i for i, n in cur.fetchall()}
print(f"  {len(ST)} estados")


# ─── LOCALIZAÇÕES ─────────────────────────────────────────────────────────────
print("\n[3/8] Localizacoes")
locs_def = [
    ('Sao Paulo HQ',   'SP-HQ'),
    ('Rio de Janeiro', 'RJ'),
    ('Curitiba',       'CWB'),
    ('Belo Horizonte', 'BH'),
    ('Home Office',    'HO'),
]
LOC = {}
for lname, code in locs_def:
    cur.execute("""
        INSERT INTO glpi_locations
          (entities_id, is_recursive, name, code, completename,
           locations_id, level, ancestors_cache, sons_cache, date_mod, date_creation)
        VALUES (0, 1, %s, %s, %s, 0, 1, '', '', NOW(), NOW())
    """, (lname, code, lname))
    LOC[lname] = cur.lastrowid
conn.commit()
print(f"  {len(LOC)} localizacoes")


# ─── TIPOS E MODELOS ──────────────────────────────────────────────────────────
print("\n[4/8] Tipos e modelos de CMDB")

# Computer types
for t in ['Desktop', 'Notebook', 'Servidor']:
    cur.execute("INSERT INTO glpi_computertypes (name, date_mod, date_creation) VALUES (%s, NOW(), NOW())", (t,))
conn.commit()
cur.execute("SELECT id, name FROM glpi_computertypes")
CTYPE = {n: i for i, n in cur.fetchall()}

# Computer models
cmodel_list = [
    'Dell OptiPlex 7090', 'Dell Latitude 5520', 'Dell PowerEdge R750',
    'HP EliteDesk 800 G6', 'HP EliteBook 840 G8', 'HP ProLiant DL380 Gen10',
    'Lenovo ThinkCentre M90q', 'Lenovo ThinkPad T14',
]
cur.executemany(
    "INSERT INTO glpi_computermodels (name, date_mod, date_creation) VALUES (%s, NOW(), NOW())",
    [(m,) for m in cmodel_list]
)
conn.commit()
cur.execute("SELECT id, name FROM glpi_computermodels")
CMODEL = {n: i for i, n in cur.fetchall()}

# Network equipment types
for t in ['Switch', 'Router', 'Firewall', 'Access Point']:
    cur.execute(
        "INSERT INTO glpi_networkequipmenttypes (name, date_mod, date_creation) VALUES (%s, NOW(), NOW())", (t,)
    )
conn.commit()
cur.execute("SELECT id, name FROM glpi_networkequipmenttypes")
NETYPE = {n: i for i, n in cur.fetchall()}

# Network equipment models
nemodel_list = [
    'Cisco Catalyst 9300', 'Cisco Catalyst 2960-X', 'Cisco ISR 4331',
    'Cisco ASA 5516-X', 'Fortinet FortiGate 100F', 'Aruba AP-515',
]
cur.executemany(
    "INSERT INTO glpi_networkequipmentmodels (name, date_mod, date_creation) VALUES (%s, NOW(), NOW())",
    [(m,) for m in nemodel_list]
)
conn.commit()
cur.execute("SELECT id, name FROM glpi_networkequipmentmodels")
NEMODEL = {n: i for i, n in cur.fetchall()}

# Monitor types & models (minimal)
cur.execute("INSERT INTO glpi_monitortypes (name, date_mod, date_creation) VALUES ('Monitor LCD', NOW(), NOW())")
conn.commit()
cur.execute("SELECT id FROM glpi_monitortypes LIMIT 1")
MON_TYPE_ID = cur.fetchone()[0]

for m in ['Dell P2422H', 'HP E24 G4', 'Samsung S24A336']:
    cur.execute(
        "INSERT INTO glpi_monitormodels (name, date_mod, date_creation) VALUES (%s, NOW(), NOW())", (m,)
    )
conn.commit()
cur.execute("SELECT id FROM glpi_monitormodels")
MON_MODEL_IDS = [r[0] for r in cur.fetchall()]

# Printer types & models
cur.execute("INSERT INTO glpi_printertypes (name, date_mod, date_creation) VALUES ('Laser', NOW(), NOW())")
conn.commit()
cur.execute("SELECT id FROM glpi_printertypes LIMIT 1")
PRT_TYPE_ID = cur.fetchone()[0]

for m in ['HP LaserJet Pro M404n', 'HP Color LaserJet M454dw', 'Brother MFC-L8900CDW']:
    cur.execute(
        "INSERT INTO glpi_printermodels (name, date_mod, date_creation) VALUES (%s, NOW(), NOW())", (m,)
    )
conn.commit()
cur.execute("SELECT id FROM glpi_printermodels")
PRT_MODEL_IDS = [r[0] for r in cur.fetchall()]

print("  Tipos e modelos inseridos")


# ─── COMPUTADORES ─────────────────────────────────────────────────────────────
print("\n[5/8] Computadores")

cur.execute("SELECT id FROM glpi_users WHERE id > 2 ORDER BY id")
all_users = [r[0] for r in cur.fetchall()]
cur.execute("SELECT id FROM glpi_users WHERE id >= 68 ORDER BY id")
TECH_IDS = [r[0] for r in cur.fetchall()]
# requesters = users NOT in tech range
REQR_IDS = [u for u in all_users if u < 68]
if not TECH_IDS:
    raise RuntimeError("Nenhum técnico encontrado — execute seed_glpi.py primeiro")

cur.execute("SELECT id FROM glpi_groups ORDER BY id")
GRP_IDS = [r[0] for r in cur.fetchall()]

LOC_LIST = list(LOC.values())

# model→(type, manufacturer) mapping
WS_MODELS = {
    'Dell OptiPlex 7090':    ('Desktop',  'Dell Technologies'),
    'HP EliteDesk 800 G6':   ('Desktop',  'HP Inc.'),
    'Lenovo ThinkCentre M90q':('Desktop', 'Lenovo'),
    'Dell Latitude 5520':    ('Notebook', 'Dell Technologies'),
    'HP EliteBook 840 G8':   ('Notebook', 'HP Inc.'),
    'Lenovo ThinkPad T14':   ('Notebook', 'Lenovo'),
}
SRV_MODELS = {
    'Dell PowerEdge R750':       'Dell Technologies',
    'HP ProLiant DL380 Gen10':   'HP Inc.',
}

COMP_IDS = []
SRV_IDS  = []

# 50 workstations
for i in range(50):
    model = random.choice(list(WS_MODELS))
    ctype_name, mfr_name = WS_MODELS[model]
    user_id  = random.choice(REQR_IDS) if REQR_IDS else 0
    tech_id  = random.choice(TECH_IDS)
    loc_id   = random.choice(LOC_LIST)
    state_id = ST.get('Em uso') if random.random() < 0.85 else ST.get('Em manutencao')
    cur.execute("""
        INSERT INTO glpi_computers
          (entities_id, name, serial, users_id, users_id_tech,
           locations_id, states_id, manufacturers_id,
           computermodels_id, computertypes_id,
           is_deleted, is_dynamic, is_template,
           uuid, date_creation, date_mod)
        VALUES (0,%s,%s,%s,%s,%s,%s,%s,%s,%s,0,0,0,%s,NOW(),NOW())
    """, (
        f"WS-{i+1:03d}", f"SN{random.randint(100000,999999)}",
        user_id, tech_id, loc_id, state_id,
        MFR.get(mfr_name, 1), CMODEL.get(model, 1), CTYPE.get(ctype_name, 1),
        str(uuid.uuid4())
    ))
    COMP_IDS.append(cur.lastrowid)

# 15 servers (HQ only)
hq_loc = LOC.get('Sao Paulo HQ', LOC_LIST[0])
for i in range(15):
    model    = random.choice(list(SRV_MODELS))
    mfr_name = SRV_MODELS[model]
    tech_id  = random.choice(TECH_IDS)
    state_id = ST.get('Em uso') if random.random() < 0.9 else ST.get('Em manutencao')
    cur.execute("""
        INSERT INTO glpi_computers
          (entities_id, name, serial, users_id, users_id_tech,
           locations_id, states_id, manufacturers_id,
           computermodels_id, computertypes_id,
           is_deleted, is_dynamic, is_template,
           uuid, date_creation, date_mod)
        VALUES (0,%s,%s,0,%s,%s,%s,%s,%s,%s,0,0,0,%s,NOW(),NOW())
    """, (
        f"SRV-{i+1:02d}", f"SR{random.randint(100000,999999)}",
        tech_id, hq_loc, state_id,
        MFR.get(mfr_name, 1), CMODEL.get(model, 1), CTYPE.get('Servidor', 1),
        str(uuid.uuid4())
    ))
    cid = cur.lastrowid
    COMP_IDS.append(cid)
    SRV_IDS.append(cid)

conn.commit()
print(f"  {len(COMP_IDS)} computadores ({len(SRV_IDS)} servidores)")


# ─── EQUIPAMENTOS DE REDE ─────────────────────────────────────────────────────
NE_DEF = [
    ('SW-CORE-01', 'Cisco Catalyst 9300',   'Switch',       'Sao Paulo HQ'),
    ('SW-CORE-02', 'Cisco Catalyst 9300',   'Switch',       'Sao Paulo HQ'),
    ('SW-ACC-01',  'Cisco Catalyst 2960-X', 'Switch',       'Sao Paulo HQ'),
    ('SW-ACC-02',  'Cisco Catalyst 2960-X', 'Switch',       'Sao Paulo HQ'),
    ('SW-ACC-03',  'Cisco Catalyst 2960-X', 'Switch',       'Sao Paulo HQ'),
    ('RT-BORDA-01','Cisco ISR 4331',        'Router',       'Sao Paulo HQ'),
    ('FW-01',      'Cisco ASA 5516-X',      'Firewall',     'Sao Paulo HQ'),
    ('FW-02',      'Fortinet FortiGate 100F','Firewall',    'Sao Paulo HQ'),
    ('AP-SP-01',   'Aruba AP-515',          'Access Point', 'Sao Paulo HQ'),
    ('AP-SP-02',   'Aruba AP-515',          'Access Point', 'Sao Paulo HQ'),
    ('SW-RJ-01',   'Cisco Catalyst 2960-X', 'Switch',       'Rio de Janeiro'),
    ('AP-RJ-01',   'Aruba AP-515',          'Access Point', 'Rio de Janeiro'),
]
NE_MFR = {
    'Cisco Catalyst 9300':     'Cisco Systems',
    'Cisco Catalyst 2960-X':   'Cisco Systems',
    'Cisco ISR 4331':          'Cisco Systems',
    'Cisco ASA 5516-X':        'Cisco Systems',
    'Fortinet FortiGate 100F': 'Fortinet',
    'Aruba AP-515':            'Aruba Networks',
}
NE_IDS = []
for name, model, ne_type, loc_name in NE_DEF:
    tech_id  = random.choice(TECH_IDS)
    loc_id   = LOC.get(loc_name, hq_loc)
    state_id = ST.get('Em uso')
    cur.execute("""
        INSERT INTO glpi_networkequipments
          (entities_id, is_recursive, name, serial, users_id_tech,
           locations_id, states_id, manufacturers_id,
           networkequipmentmodels_id, networkequipmenttypes_id,
           is_deleted, is_dynamic, is_template,
           uuid, date_creation, date_mod)
        VALUES (0,0,%s,%s,%s,%s,%s,%s,%s,%s,0,0,0,%s,NOW(),NOW())
    """, (
        name, f"NE{random.randint(100000,999999)}",
        tech_id, loc_id, state_id,
        MFR.get(NE_MFR.get(model, 'Cisco Systems'), 1),
        NEMODEL.get(model, 1), NETYPE.get(ne_type, 1),
        str(uuid.uuid4())
    ))
    NE_IDS.append(cur.lastrowid)
conn.commit()
print(f"  {len(NE_IDS)} equipamentos de rede")


# ─── MONITORES ────────────────────────────────────────────────────────────────
MON_IDS = []
for i in range(30):
    user_id  = random.choice(REQR_IDS) if REQR_IDS else 0
    loc_id   = random.choice(LOC_LIST)
    state_id = ST.get('Em uso') if random.random() < 0.9 else ST.get('Disponivel')
    mfr_id   = MFR.get(random.choice(['Dell Technologies', 'HP Inc.', 'Samsung']), 1)
    cur.execute("""
        INSERT INTO glpi_monitors
          (entities_id, name, serial, users_id, users_id_tech,
           locations_id, states_id, manufacturers_id,
           monitortypes_id, monitormodels_id,
           is_deleted, is_dynamic, is_template, is_global,
           uuid, date_creation, date_mod)
        VALUES (0,%s,%s,%s,0,%s,%s,%s,%s,%s,0,0,0,0,%s,NOW(),NOW())
    """, (
        f"MON-{i+1:03d}", f"MN{random.randint(100000,999999)}",
        user_id, loc_id, state_id, mfr_id,
        MON_TYPE_ID, random.choice(MON_MODEL_IDS),
        str(uuid.uuid4())
    ))
    MON_IDS.append(cur.lastrowid)
conn.commit()
print(f"  {len(MON_IDS)} monitores")


# ─── IMPRESSORAS ──────────────────────────────────────────────────────────────
PRT_IDS = []
PRT_MFR_MAP = {
    'HP LaserJet Pro M404n':    'HP Inc.',
    'HP Color LaserJet M454dw': 'HP Inc.',
    'Brother MFC-L8900CDW':     'Brother',
}
prt_models_names = list(PRT_MFR_MAP.keys())
for i in range(8):
    model_name = random.choice(prt_models_names)
    loc_id     = random.choice(LOC_LIST)
    tech_id    = random.choice(TECH_IDS)
    state_id   = ST.get('Em uso')
    mfr_id     = MFR.get(PRT_MFR_MAP[model_name], 1)
    cur.execute("""
        INSERT INTO glpi_printers
          (entities_id, is_recursive, name, serial, users_id_tech,
           locations_id, states_id, manufacturers_id,
           printertypes_id, printermodels_id,
           is_deleted, is_dynamic, is_template, is_global,
           uuid, date_creation, date_mod)
        VALUES (0,0,%s,%s,%s,%s,%s,%s,%s,%s,0,0,0,0,%s,NOW(),NOW())
    """, (
        f"IMP-{i+1:02d}", f"PR{random.randint(100000,999999)}",
        tech_id, loc_id, state_id, mfr_id,
        PRT_TYPE_ID, random.choice(PRT_MODEL_IDS),
        str(uuid.uuid4())
    ))
    PRT_IDS.append(cur.lastrowid)
conn.commit()
print(f"  {len(PRT_IDS)} impressoras")


# ─── TICKETS → ATIVOS ─────────────────────────────────────────────────────────
print("\n[6/8] Vinculos ticket-ativo")

cur.execute("SELECT id, itilcategories_id FROM glpi_tickets ORDER BY id")
ALL_TICKETS = cur.fetchall()
cur.execute("SELECT id, name FROM glpi_itilcategories")
CAT_NAMES = {i: n for i, n in cur.fetchall()}

items_tk = []
for ticket_id, cat_id in ALL_TICKETS:
    if random.random() > 0.30:
        continue
    cname = CAT_NAMES.get(cat_id, '')
    if any(k in cname for k in ['Rede', 'Conectividade', 'VPN', 'Wi-Fi', 'Wireless']):
        itemtype = 'NetworkEquipment'
        items_id = random.choice(NE_IDS)
    elif any(k in cname for k in ['Servidor', 'Virtualiz', 'Backup']):
        itemtype = 'Computer'
        items_id = random.choice(SRV_IDS)
    elif 'Impressora' in cname:
        itemtype = 'Printer'
        items_id = random.choice(PRT_IDS)
    elif any(k in cname for k in ['Monitor', 'Hardware', 'Periférico']):
        if random.random() < 0.5:
            itemtype = 'Monitor'; items_id = random.choice(MON_IDS)
        else:
            itemtype = 'Computer'; items_id = random.choice(COMP_IDS)
    else:
        itemtype = 'Computer'
        items_id = random.choice(COMP_IDS)
    items_tk.append((itemtype, items_id, ticket_id))

cur.executemany(
    "INSERT INTO glpi_items_tickets (itemtype, items_id, tickets_id) VALUES (%s,%s,%s)",
    items_tk
)
conn.commit()
print(f"  {len(items_tk)} vinculos ticket-ativo")


# ─── PROBLEMAS ────────────────────────────────────────────────────────────────
print("\n[7/8] Problemas")

PROBLEM_DEFS = [
    ('Instabilidade recorrente Wi-Fi corporativo', 3, 4, 4,
     'Usuarios relatam desconexoes frequentes na rede wireless. Afeta produtividade de 3 andares.'),
    ('Lentidao no acesso ao ERP em horario de pico', 2, 4, 4,
     'Sistema ERP apresenta lentidao >30s em consultas entre 09h e 11h.'),
    ('Falhas silenciosas no backup noturno', 3, 5, 5,
     'Jobs de backup falhando sem alerta, comprometendo RPO de 24h.'),
    ('Impressoras offline apos atualizacao de driver', 2, 3, 3,
     'Atualizacao automatica do Windows causou falha em 6 impressoras.'),
    ('E-mails presos na fila do servidor Exchange', 3, 4, 4,
     'Fila acumulando 1200+ mensagens sem entrega ha 8h.'),
    ('Falha de autenticacao LDAP intermitente', 3, 4, 4,
     'Active Directory retorna erro 49 esporadicamente, bloqueando acessos.'),
    ('CPU elevada nos servidores de aplicacao', 2, 4, 4,
     'APP01 e APP02 com CPU >92% em horario comercial causando timeouts.'),
    ('Cotas de disco esgotadas no file server', 2, 3, 3,
     'FS01 com 98% de uso. Usuarios nao conseguem salvar arquivos.'),
    ('Loop de Spanning Tree no switch de core', 3, 5, 5,
     'SW-CORE-01 causando broadcast storm, derrubando segmento de rede.'),
    ('Timeout nas queries do banco de dados', 3, 5, 5,
     'Queries de relatorio travando por >120s, causando failover manual.'),
    ('Certificado SSL expirado no portal web', 2, 4, 4,
     'Certificado do portal intranet expirou. Usuarios veem aviso de seguranca.'),
    ('Ramais VoIP nao registrando apos reinicio', 2, 3, 3,
     'Asterisk reiniciou e 40 ramais nao conseguem re-registrar no SIP trunk.'),
    ('Antivirus desatualizado em workstations', 1, 2, 2,
     'Scan central indica 23 maquinas com definicoes com mais de 7 dias.'),
    ('Erro na geracao de relatorios financeiros PDF', 3, 4, 4,
     'Modulo de BI nao exporta PDF para relatorios acima de 50 paginas.'),
    ('Firewall de borda reiniciando sozinho', 3, 5, 5,
     'FW-01 com 5 reboots espontaneos em 48h. Investigacao em andamento.'),
    ('Permissoes incorretas no Active Directory', 2, 3, 3,
     'Apos migracao de UO, 12 usuarios perderam acesso a pastas compartilhadas.'),
    ('Servidores sem monitoramento no Zabbix', 1, 2, 2,
     'Zabbix nao captura metricas de SRV-11, SRV-12 e SRV-13.'),
    ('Crash periodico do sistema de ponto eletronico', 3, 4, 4,
     'Aplicacao PontoWeb trava diariamente as 08h05, causando indisponibilidade de 20min.'),
    ('Transaction log 100% cheio no SQL Server', 3, 5, 5,
     'Log do banco ERPDB atingiu limite. Todas as transacoes falhando.'),
    ('Resolucao DNS interna falhando para dominios .local', 2, 3, 3,
     'Clientes de Curitiba nao resolvem nomes internos. DNS forwarder mal configurado.'),
    ('Falha de replicacao entre Domain Controllers', 3, 4, 4,
     'DC01 e DC02 com delta de replicacao >1h. Usuarios com senhas inconsistentes.'),
    ('Lentidao no SharePoint apos migracao', 2, 3, 3,
     'Paginas do SharePoint levando >15s para carregar apos upgrade.'),
    ('Swap alto nos servidores Linux de aplicacao', 2, 4, 4,
     'Servidores com swappiness alta causando degradacao de performance.'),
    ('Jobs do SQL Server Agent falhando silenciosamente', 2, 3, 3,
     'Relatorios noturnos nao sendo gerados. Jobs concluem sem erro no log.'),
    ('Indisponibilidade recorrente do sistema legado', 3, 4, 4,
     'Sistema legado ficou fora do ar 4x na semana. Migracao urgente necessaria.'),
]

cur.execute("SELECT id, itilcategories_id, 0 FROM glpi_tickets ORDER BY RAND() LIMIT 300")
TK_SAMPLE = cur.fetchall()

PROB_IDS = []
for pname, urgency, impact, priority, content in PROBLEM_DEFS:
    pdate  = rand_str(SIM_START, SIM_END)
    status = random.choices([1, 2, 3, 5, 6], weights=[1, 2, 1, 3, 3])[0]
    solve  = None
    close  = None
    if status in (5, 6):
        s_dt  = rand_dt(SIM_START, SIM_END)
        solve = s_dt.strftime('%Y-%m-%d %H:%M:%S')
        if status == 6:
            close = (s_dt + timedelta(hours=random.randint(1, 48))).strftime('%Y-%m-%d %H:%M:%S')

    cur.execute("""
        INSERT INTO glpi_problems
          (name, entities_id, status, content, date, date_mod, date_creation,
           urgency, impact, priority, itilcategories_id,
           solvedate, closedate,
           users_id_recipient, users_id_lastupdater,
           is_deleted, actiontime, waiting_duration,
           close_delay_stat, solve_delay_stat)
        VALUES (%s,0,%s,%s,%s,NOW(),NOW(),%s,%s,%s,0,
                %s,%s,%s,%s,
                0,0,0,0,0)
    """, (pname, status, content, pdate, urgency, impact, priority,
          solve, close,
          random.choice(TECH_IDS), random.choice(TECH_IDS)))
    pid = cur.lastrowid
    PROB_IDS.append(pid)

    # Link 3–8 tickets
    linked = random.sample(TK_SAMPLE, min(random.randint(3, 8), len(TK_SAMPLE)))
    for t_id, _, _ in linked:
        cur.execute(
            "INSERT INTO glpi_problems_tickets (problems_id, tickets_id, link) VALUES (%s,%s,1)",
            (pid, t_id)
        )

    # Assign tech (type=2)
    cur.execute(
        "INSERT INTO glpi_problems_users (problems_id, users_id, type, use_notification) VALUES (%s,%s,2,1)",
        (pid, random.choice(TECH_IDS))
    )
    # Assign group (type=2)
    if GRP_IDS:
        cur.execute(
            "INSERT INTO glpi_groups_problems (problems_id, groups_id, type) VALUES (%s,%s,2)",
            (pid, random.choice(GRP_IDS))
        )
    # Link asset
    if urgency >= 4 and NE_IDS:
        cur.execute(
            "INSERT INTO glpi_items_problems (problems_id, itemtype, items_id) VALUES (%s,'NetworkEquipment',%s)",
            (pid, random.choice(NE_IDS))
        )
    elif random.random() < 0.5 and SRV_IDS:
        cur.execute(
            "INSERT INTO glpi_items_problems (problems_id, itemtype, items_id) VALUES (%s,'Computer',%s)",
            (pid, random.choice(SRV_IDS))
        )

conn.commit()
print(f"  {len(PROB_IDS)} problemas com vinculos")


# ─── MUDANÇAS ─────────────────────────────────────────────────────────────────
CHANGE_DEFS = [
    ('Atualizacao firmware Cisco Catalyst 9300', 2, 3, 3,
     'Aplicar firmware 17.6.3 nos 2 switches de core durante janela noturna.'),
    ('Migracao do servidor de arquivos FS01', 3, 4, 4,
     'Migrar FS01 (Dell PE R730) para novo hardware FS01-NEW (Dell PE R750).'),
    ('Implantacao firewall Fortinet FortiGate 100F', 3, 5, 5,
     'Substituir Cisco ASA 5516-X por FortiGate 100F no perimetro.'),
    ('Upgrade Windows Server 2019 para 2022', 2, 3, 3,
     'In-place upgrade em APP01 e APP02 para Windows Server 2022.'),
    ('Expansao de RAM: APP01 e APP02 32GB', 2, 3, 3,
     'Adicionar 2x16GB DDR4 ECC em cada servidor de aplicacao.'),
    ('Implantacao de MFA para VPN GlobalProtect', 3, 4, 4,
     'Habilitar Duo MFA integrado ao GlobalProtect para todos os colaboradores.'),
    ('Migracao Exchange On-Prem para Microsoft 365', 3, 5, 5,
     'Migracao hibrida por fases: TI > Financeiro > RH > demais areas.'),
    ('Upgrade plataforma VMware para vSphere 8', 2, 4, 4,
     'Atualizar vCenter 7.0 e hosts ESXi para vSphere 8.0 U2.'),
    ('Implantacao backup em nuvem com Veeam + Azure', 2, 3, 3,
     'Configurar Veeam Backup & Replication com repositorio Azure Blob Storage.'),
    ('Renovacao certificados SSL corporativos', 1, 2, 2,
     'Renovar 8 certificados SSL que vencem nos proximos 90 dias.'),
    ('Implantacao monitoramento Zabbix 6.4', 2, 3, 3,
     'Expandir cobertura do Zabbix para todos os 65 ativos do CMDB.'),
    ('Migracao antivirus Symantec para CrowdStrike', 1, 2, 2,
     'Substituicao gradual via GPO em 3 waves de 50 maquinas.'),
    ('Segregacao de VLANs por departamento', 3, 4, 4,
     'Reestruturar segmentacao criando VLANs: Corp, Dev, DMZ, Guest, IoT.'),
    ('Implantacao SD-WAN nas filiais', 3, 4, 4,
     'POC em Rio de Janeiro; rollout para Curitiba e BH apos aprovacao.'),
    ('Cluster MariaDB Galera para alta disponibilidade', 3, 5, 5,
     'Implementar cluster 3 nos para ERPDB eliminando SPOF de banco de dados.'),
    ('Elevacao nivel funcional Active Directory', 2, 4, 4,
     'Elevar dominio e floresta para Windows Server 2022 functional level.'),
    ('Deploy GLPI 10.x em producao', 3, 4, 4,
     'Migrar GLPI 9.5 para 10.0.x com migracao de dados, plugins e treinamento.'),
    ('Implantacao NAC com Aruba ClearPass', 3, 4, 4,
     'Controle de acesso a rede baseado em identidade e postura do dispositivo.'),
]

CHANGE_IDS = []
for cname, urgency, impact, priority, content in CHANGE_DEFS:
    cdate  = rand_str(SIM_START, SIM_END)
    status = random.choices([1, 2, 5, 6], weights=[1, 2, 3, 4])[0]
    solve  = None
    close  = None
    if status in (5, 6):
        s_dt  = rand_dt(SIM_START, SIM_END)
        solve = s_dt.strftime('%Y-%m-%d %H:%M:%S')
        if status == 6:
            close = (s_dt + timedelta(hours=random.randint(2, 72))).strftime('%Y-%m-%d %H:%M:%S')

    cur.execute("""
        INSERT INTO glpi_changes
          (name, entities_id, status, content, backoutplancontent,
           date, date_mod, date_creation,
           urgency, impact, priority, itilcategories_id,
           solvedate, closedate,
           users_id_recipient, users_id_lastupdater,
           is_deleted, actiontime, waiting_duration,
           close_delay_stat, solve_delay_stat, global_validation)
        VALUES (%s,0,%s,%s,'Desfazer alteracoes e restaurar backup pre-mudanca.',%s,NOW(),NOW(),
                %s,%s,%s,0,
                %s,%s,%s,%s,
                0,0,0,0,0,1)
    """, (cname, status, content, cdate, urgency, impact, priority,
          solve, close,
          random.choice(TECH_IDS), random.choice(TECH_IDS)))
    cid = cur.lastrowid
    CHANGE_IDS.append(cid)

    # Link 1–4 tickets
    linked = random.sample(TK_SAMPLE, min(random.randint(1, 4), len(TK_SAMPLE)))
    for t_id, _, _ in linked:
        cur.execute(
            "INSERT INTO glpi_changes_tickets (changes_id, tickets_id, link) VALUES (%s,%s,1)",
            (cid, t_id)
        )

    # Assign tech
    cur.execute(
        "INSERT INTO glpi_changes_users (changes_id, users_id, type, use_notification) VALUES (%s,%s,2,1)",
        (cid, random.choice(TECH_IDS))
    )

    # Link asset
    net_keywords = ['firewall', 'cisco', 'switch', 'vlan', 'sd-wan', 'rede', 'nac']
    if any(k in cname.lower() for k in net_keywords) and NE_IDS:
        cur.execute(
            "INSERT INTO glpi_changes_items (changes_id, itemtype, items_id) VALUES (%s,'NetworkEquipment',%s)",
            (cid, random.choice(NE_IDS))
        )
    elif COMP_IDS:
        cur.execute(
            "INSERT INTO glpi_changes_items (changes_id, itemtype, items_id) VALUES (%s,'Computer',%s)",
            (cid, random.choice(COMP_IDS))
        )

    # Change tasks (2–3 per change)
    task_base = datetime.strptime(cdate[:10], '%Y-%m-%d')
    task_names = ['Planejamento e aprovacao', 'Execucao tecnica', 'Testes e validacao', 'Documentacao']
    for j in range(random.randint(2, 3)):
        ts = (task_base + timedelta(days=j)).strftime('%Y-%m-%d %H:%M:%S')
        te = (task_base + timedelta(days=j, hours=3)).strftime('%Y-%m-%d %H:%M:%S')
        t_state = 2 if status == 6 else (1 if j == 0 else 0)
        cur.execute("""
            INSERT INTO glpi_changetasks
              (changes_id, state, date, begin, end, users_id_tech,
               content, actiontime, date_mod, date_creation, timeline_position)
            VALUES (%s,%s,%s,%s,%s,%s,%s,10800,NOW(),NOW(),1)
        """, (cid, t_state, ts, ts, te, random.choice(TECH_IDS), task_names[j % 4]))

conn.commit()
print(f"\n[7.5/8] {len(CHANGE_IDS)} mudancas com tarefas e vinculos")


# ─── PROJETOS ─────────────────────────────────────────────────────────────────
print("\n[8/8] Projetos e tarefas")

PROJ_DEFS = [
    {
        'name': 'Modernizacao da Infraestrutura de Rede',
        'code': 'PRJ-2024-001', 'priority': 3, 'state': 2,
        'start': datetime(2024, 2, 1),  'end': datetime(2024, 8, 31),
        'done': 75,
        'content': 'Substituicao da infraestrutura de rede core e acesso em 3 escritorios.',
        'tasks': [
            ('Levantamento e inventario atual',      datetime(2024, 2, 1),  datetime(2024, 2, 28),  100, False),
            ('Aquisicao de equipamentos',            datetime(2024, 3, 1),  datetime(2024, 4, 15),  100, False),
            ('Instalacao switches de core',          datetime(2024, 4, 16), datetime(2024, 5, 31),  100, False),
            ('Migracao switches de acesso',          datetime(2024, 6, 1),  datetime(2024, 7, 15),  80,  False),
            ('Testes e validacao',                   datetime(2024, 7, 16), datetime(2024, 8, 15),  50,  False),
            ('Go-Live e documentacao final',         datetime(2024, 8, 16), datetime(2024, 8, 31),  20,  True),
        ]
    },
    {
        'name': 'Migracao para Microsoft 365',
        'code': 'PRJ-2024-002', 'priority': 2, 'state': 2,
        'start': datetime(2024, 3, 1),  'end': datetime(2024, 12, 31),
        'done': 60,
        'content': 'Migracao do Exchange on-premises para Microsoft 365 por fases departamentais.',
        'tasks': [
            ('Assessment e planejamento',            datetime(2024, 3, 1),  datetime(2024, 3, 31),  100, False),
            ('Configuracao tenant M365',             datetime(2024, 4, 1),  datetime(2024, 4, 30),  100, False),
            ('Migracao piloto — TI (30 caixas)',     datetime(2024, 5, 1),  datetime(2024, 5, 31),  100, False),
            ('Migracao Financeiro e RH',             datetime(2024, 6, 1),  datetime(2024, 7, 31),  100, False),
            ('Migracao demais departamentos',        datetime(2024, 8, 1),  datetime(2024, 10, 31), 60,  False),
            ('Descomissionamento Exchange',          datetime(2024, 11, 1), datetime(2024, 12, 31), 0,   True),
        ]
    },
    {
        'name': 'Implantacao ITSM com GLPI',
        'code': 'PRJ-2024-003', 'priority': 2, 'state': 3,
        'start': datetime(2024, 1, 1),  'end': datetime(2024, 6, 30),
        'done': 100,
        'content': 'Implantacao do GLPI como ferramenta central de Service Desk e CMDB.',
        'tasks': [
            ('Instalacao e configuracao base',       datetime(2024, 1, 1),  datetime(2024, 1, 31),  100, False),
            ('Customizacao e integracao com AD',     datetime(2024, 2, 1),  datetime(2024, 2, 28),  100, False),
            ('Importacao de ativos no CMDB',         datetime(2024, 3, 1),  datetime(2024, 3, 31),  100, False),
            ('Treinamento da equipe de TI',          datetime(2024, 4, 1),  datetime(2024, 4, 30),  100, False),
            ('Rollout para usuarios finais',         datetime(2024, 5, 1),  datetime(2024, 5, 31),  100, False),
            ('Ajustes pos-implantacao',              datetime(2024, 6, 1),  datetime(2024, 6, 30),  100, True),
        ]
    },
    {
        'name': 'Alta Disponibilidade de Servidores Criticos',
        'code': 'PRJ-2025-001', 'priority': 3, 'state': 2,
        'start': datetime(2025, 1, 15), 'end': datetime(2025, 9, 30),
        'done': 40,
        'content': 'Implementar cluster HA VMware para todos os servidores criticos.',
        'tasks': [
            ('Definicao da arquitetura HA',          datetime(2025, 1, 15), datetime(2025, 2, 15),  100, False),
            ('Aquisicao de servidores adicionais',   datetime(2025, 2, 16), datetime(2025, 3, 31),  100, False),
            ('Configuracao do cluster VMware',       datetime(2025, 4, 1),  datetime(2025, 5, 31),  60,  False),
            ('Migracao das VMs para cluster',        datetime(2025, 6, 1),  datetime(2025, 7, 31),  20,  False),
            ('Testes de failover automatizados',     datetime(2025, 8, 1),  datetime(2025, 8, 31),  0,   False),
            ('Documentacao e handover',              datetime(2025, 9, 1),  datetime(2025, 9, 30),  0,   True),
        ]
    },
    {
        'name': 'Expansao TI — Filial Curitiba',
        'code': 'PRJ-2025-002', 'priority': 2, 'state': 2,
        'start': datetime(2025, 3, 1),  'end': datetime(2025, 12, 31),
        'done': 30,
        'content': 'Implantacao de infraestrutura TI completa na nova filial de Curitiba.',
        'tasks': [
            ('Planejamento de rede e TI',            datetime(2025, 3, 1),  datetime(2025, 3, 31),  100, False),
            ('Aquisicao de equipamentos',            datetime(2025, 4, 1),  datetime(2025, 5, 15),  100, False),
            ('Instalacao rede estruturada',          datetime(2025, 5, 16), datetime(2025, 6, 30),  80,  False),
            ('Configuracao de servidores locais',    datetime(2025, 7, 1),  datetime(2025, 8, 31),  20,  False),
            ('Integracao VPN/SD-WAN com HQ',         datetime(2025, 9, 1),  datetime(2025, 10, 31), 0,   False),
            ('Go-Live e suporte inicial',            datetime(2025, 11, 1), datetime(2025, 12, 31), 0,   True),
        ]
    },
    {
        'name': 'Programa de Seguranca da Informacao ISO 27001',
        'code': 'PRJ-2025-003', 'priority': 3, 'state': 2,
        'start': datetime(2025, 2, 1),  'end': datetime(2025, 12, 31),
        'done': 25,
        'content': 'Implementacao de controles de seguranca para certificacao ISO 27001.',
        'tasks': [
            ('Gap Analysis ISO 27001',               datetime(2025, 2, 1),  datetime(2025, 2, 28),  100, False),
            ('Implantacao de MFA corporativo',       datetime(2025, 3, 1),  datetime(2025, 4, 30),  80,  False),
            ('Treinamento de conscientizacao',       datetime(2025, 4, 1),  datetime(2025, 5, 31),  60,  False),
            ('Segmentacao Zero Trust',               datetime(2025, 5, 1),  datetime(2025, 7, 31),  30,  False),
            ('Auditoria interna de controles',       datetime(2025, 8, 1),  datetime(2025, 9, 30),  0,   False),
            ('Auditoria externa e certificacao',     datetime(2025, 10, 1), datetime(2025, 12, 31), 0,   True),
        ]
    },
]

PROJ_IDS   = []
TASK_COUNT = 0

for proj in PROJ_DEFS:
    grp_id    = random.choice(GRP_IDS) if GRP_IDS else 0
    usr_id    = random.choice(TECH_IDS)
    real_start = proj['start'].strftime('%Y-%m-%d %H:%M:%S') if proj['done'] > 0 else None
    real_end   = proj['end'].strftime('%Y-%m-%d %H:%M:%S')   if proj['done'] == 100 else None

    cur.execute("""
        INSERT INTO glpi_projects
          (name, code, priority, entities_id, projectstates_id,
           users_id, groups_id,
           plan_start_date, plan_end_date, real_start_date, real_end_date,
           percent_done, auto_percent_done,
           content, is_deleted, show_on_global_gantt,
           date_mod, date_creation)
        VALUES (%s,%s,%s,0,%s,%s,%s,%s,%s,%s,%s,%s,0,%s,0,1,NOW(),NOW())
    """, (
        proj['name'], proj['code'], proj['priority'], proj['state'],
        usr_id, grp_id,
        proj['start'].strftime('%Y-%m-%d %H:%M:%S'),
        proj['end'].strftime('%Y-%m-%d %H:%M:%S'),
        real_start, real_end,
        proj['done'], proj['content']
    ))
    pid = cur.lastrowid
    PROJ_IDS.append(pid)

    # Project team (3 members)
    for tm in random.sample(TECH_IDS, min(3, len(TECH_IDS))):
        cur.execute(
            "INSERT INTO glpi_projectteams (projects_id, itemtype, items_id) VALUES (%s,'User',%s)",
            (pid, tm)
        )

    # Tasks
    for t_name, t_start, t_end, t_done, t_milestone in proj['tasks']:
        task_uid = str(uuid.uuid4())
        r_start  = t_start.strftime('%Y-%m-%d %H:%M:%S') if t_done > 0 else None
        r_end    = t_end.strftime('%Y-%m-%d %H:%M:%S')   if t_done == 100 else None
        t_state  = 2 if t_done == 100 else (1 if t_done > 0 else 0)
        task_usr = random.choice(TECH_IDS)

        cur.execute("""
            INSERT INTO glpi_projecttasks
              (uuid, name, entities_id, projects_id, projecttasks_id,
               plan_start_date, plan_end_date, real_start_date, real_end_date,
               percent_done, auto_percent_done, projectstates_id, users_id,
               is_milestone, is_deleted, date_mod, date_creation)
            VALUES (%s,%s,0,%s,0,%s,%s,%s,%s,%s,0,%s,%s,%s,0,NOW(),NOW())
        """, (
            task_uid, t_name, pid,
            t_start.strftime('%Y-%m-%d %H:%M:%S'),
            t_end.strftime('%Y-%m-%d %H:%M:%S'),
            r_start, r_end,
            t_done, t_state, task_usr,
            1 if t_milestone else 0
        ))
        task_id = cur.lastrowid
        TASK_COUNT += 1

        # Task team
        cur.execute(
            "INSERT INTO glpi_projecttaskteams (projecttasks_id, itemtype, items_id) VALUES (%s,'User',%s)",
            (task_id, random.choice(TECH_IDS))
        )

        # Link completed tasks to tickets (30% chance, max 2 tickets)
        if t_done == 100 and random.random() < 0.30 and TK_SAMPLE:
            for t_id, _, _ in random.sample(TK_SAMPLE, min(2, len(TK_SAMPLE))):
                cur.execute(
                    "INSERT INTO glpi_projecttasks_tickets (projecttasks_id, tickets_id) VALUES (%s,%s)",
                    (task_id, t_id)
                )

conn.commit()
print(f"  {len(PROJ_IDS)} projetos, {TASK_COUNT} tarefas")


# ─── RESUMO FINAL ─────────────────────────────────────────────────────────────
print("\n" + "=" * 68)
print("  RESUMO DA SIMULACAO ESTENDIDA")
print("=" * 68)

checks = [
    ("Fabricantes",                   "SELECT COUNT(*) FROM glpi_manufacturers"),
    ("Estados de ativo",              "SELECT COUNT(*) FROM glpi_states"),
    ("Localizacoes",                  "SELECT COUNT(*) FROM glpi_locations"),
    ("Computadores (total)",          "SELECT COUNT(*) FROM glpi_computers"),
    ("  - Servidores",                "SELECT COUNT(*) FROM glpi_computers WHERE name LIKE 'SRV-%'"),
    ("Equip. de rede",                "SELECT COUNT(*) FROM glpi_networkequipments"),
    ("Monitores",                     "SELECT COUNT(*) FROM glpi_monitors"),
    ("Impressoras",                   "SELECT COUNT(*) FROM glpi_printers"),
    ("Vinculos ticket-ativo",         "SELECT COUNT(*) FROM glpi_items_tickets"),
    ("Problemas",                     "SELECT COUNT(*) FROM glpi_problems"),
    ("Prob -> Tickets",               "SELECT COUNT(*) FROM glpi_problems_tickets"),
    ("Prob -> Ativos",                "SELECT COUNT(*) FROM glpi_items_problems"),
    ("Mudancas",                      "SELECT COUNT(*) FROM glpi_changes"),
    ("Mudancas -> Tickets",           "SELECT COUNT(*) FROM glpi_changes_tickets"),
    ("Mudancas -> Ativos",            "SELECT COUNT(*) FROM glpi_changes_items"),
    ("Tarefas de mudanca",            "SELECT COUNT(*) FROM glpi_changetasks"),
    ("Projetos",                      "SELECT COUNT(*) FROM glpi_projects"),
    ("Tarefas de projeto",            "SELECT COUNT(*) FROM glpi_projecttasks"),
    ("Proj.Tarefas -> Tickets",       "SELECT COUNT(*) FROM glpi_projecttasks_tickets"),
]
for label, query in checks:
    cur.execute(query)
    n = cur.fetchone()[0]
    print(f"  {label:<35} {n:>6}")

conn.close()
print("\nSeed estendido concluido com sucesso!")
