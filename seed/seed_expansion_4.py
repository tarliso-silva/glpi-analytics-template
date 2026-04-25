"""
seed_expansion_4.py — Follow-ups, Tarefas, Satisfação, Problem Tasks, Changes↔Problems
Insere:
  - glpi_itilfollowups: ~200 follow-ups em tickets (respostas e atualizações)
  - glpi_tickettasks: ~150 tarefas em tickets
  - glpi_ticketsatisfactions: ~350 avaliações de satisfação (tickets fechados)
  - glpi_problemtasks: 2-3 tarefas por problema fechado
  - glpi_changes_problems: vínculos entre mudanças e problemas
NÃO altera dados existentes.
random.seed(42) para reprodutibilidade.
"""
import mysql.connector, random, uuid as _uuid
from datetime import date, datetime, timedelta

random.seed(42)

DB = dict(host="localhost", port=3306, database="glpi", user="glpi", password="glpi")
conn = mysql.connector.connect(**DB)
conn.autocommit = False
cur = conn.cursor()

def count(t):
    cur.execute(f"SELECT COUNT(*) FROM `{t}`")
    return cur.fetchone()[0]

print("=" * 68)
print("  EXPANSION 4 — Follow-ups, Tarefas, Satisfação e Vínculos")
print("=" * 68)

# ─── Carregar contexto ────────────────────────────────────────────────────────
cur.execute("SELECT id, status, date_creation FROM glpi_tickets ORDER BY id")
ALL_TICKETS = cur.fetchall()   # [(id, status, date_creation), ...]
# Status: 1=New, 2=Processing(assigned), 3=Processing(planned), 4=Pending, 5=Solved, 6=Closed
CLOSED_TKT   = [(tid, dc) for tid, st, dc in ALL_TICKETS if st == 6]
SOLVED_TKT   = [(tid, dc) for tid, st, dc in ALL_TICKETS if st in (5, 6)]
OPEN_TKT     = [(tid, dc) for tid, st, dc in ALL_TICKETS if st not in (5, 6)]
ALL_TKT_IDS  = [tid for tid, _, _ in ALL_TICKETS]

cur.execute("""
    SELECT u.id FROM glpi_users u
    JOIN glpi_groups_users gu ON gu.users_id = u.id
    ORDER BY u.id
""")
TECH_IDS = list({r[0] for r in cur.fetchall()})
if not TECH_IDS:
    cur.execute("SELECT id FROM glpi_users WHERE name NOT LIKE 'glpi%' ORDER BY id LIMIT 15")
    TECH_IDS = [r[0] for r in cur.fetchall()]

cur.execute("SELECT id, date FROM glpi_problems ORDER BY id")
ALL_PROBLEMS = cur.fetchall()
cur.execute("SELECT id, date FROM glpi_changes ORDER BY id")
ALL_CHANGES = cur.fetchall()

cur.execute("SELECT id FROM glpi_requesttypes LIMIT 4")
REQ_TYPES = [r[0] for r in cur.fetchall()]

print(f"  Tickets: {len(ALL_TKT_IDS)} | Fechados: {len(CLOSED_TKT)} | Resolvidos: {len(SOLVED_TKT)}")
print(f"  Tecnicos: {len(TECH_IDS)} | Problemas: {len(ALL_PROBLEMS)} | Mudanças: {len(ALL_CHANGES)}")

# ─── 1. FOLLOW-UPS (itilfollowups) ────────────────────────────────────────────
print("\n[1/5] Follow-ups de tickets")

if count("glpi_itilfollowups") > 0:
    print("  itilfollowups já preenchido, pulando.")
else:
    FOLLOWUP_TEMPLATES = [
        "Analise iniciada. Aguardando informacoes adicionais do usuario.",
        "Problema reproduzido. Investigando causa raiz.",
        "Identificado o problema: {issue}. Aplicando solucao.",
        "Solucao aplicada. Aguardando confirmacao do usuario.",
        "Usuario confirmou resolucao. Encerrando ticket.",
        "Escalado para a equipe {group}. Aguardando retorno.",
        "Reinicio do servico realizado. Monitorando estabilidade.",
        "Atualizado driver/firmware conforme KB disponivel.",
        "Configuracao corrigida. Servico restabelecido.",
        "Pendente retorno do fornecedor. SLA em monitoramento.",
        "Backup verificado com sucesso. Dados restaurados.",
        "Acesso remoto realizado. Problema solucionado.",
        "Substituicao de hardware agendada para {date}.",
        "Usuario sem acesso ao sistema. Reset de senha executado.",
        "Politica de grupo atualizada. Propagacao em andamento.",
    ]

    ISSUES = ["falha no driver de rede", "conflito de software", "corrupcao de perfil",
              "expiracao de certificado", "falta de permissao no AD"]
    GROUPS = ["Infraestrutura", "Sistemas", "Redes e Conectividade"]

    # Selecionar ~220 tickets para ter follow-ups (mix de abertos e fechados)
    sample_tkts = random.sample(SOLVED_TKT, min(150, len(SOLVED_TKT))) + \
                  random.sample(OPEN_TKT, min(70, len(OPEN_TKT)))

    followup_count = 0
    for tkt_id, tkt_date_creation in sample_tkts:
        if isinstance(tkt_date_creation, str):
            base_dt = datetime.strptime(tkt_date_creation[:19], "%Y-%m-%d %H:%M:%S")
        else:
            base_dt = datetime.combine(tkt_date_creation, datetime.min.time())

        n_followups = random.randint(1, 3)
        delta_hours = random.randint(1, 4)
        for fi in range(n_followups):
            delta_hours += random.randint(2, 24)
            fu_dt = base_dt + timedelta(hours=delta_hours)
            template = random.choice(FOLLOWUP_TEMPLATES)
            content = template.format(
                issue=random.choice(ISSUES),
                group=random.choice(GROUPS),
                date=(fu_dt + timedelta(days=3)).strftime("%d/%m/%Y")
            )
            req_type = random.choice(REQ_TYPES) if REQ_TYPES else 1
            tech_id  = random.choice(TECH_IDS)
            cur.execute("""
                INSERT INTO glpi_itilfollowups
                  (itemtype, items_id, date, users_id, content, is_private,
                   requesttypes_id, date_mod, date_creation, timeline_position)
                VALUES ('Ticket', %s, %s, %s, %s, 0, %s, NOW(), NOW(), 1)
            """, (tkt_id, fu_dt.strftime("%Y-%m-%d %H:%M:%S"),
                  tech_id, content, req_type))
            followup_count += 1

    conn.commit()
    print(f"  {followup_count} follow-ups inseridos")

# ─── 2. TAREFAS DE TICKET (tickettasks) ───────────────────────────────────────
print("\n[2/5] Tarefas de tickets")

if count("glpi_tickettasks") > 0:
    print("  tickettasks já preenchido, pulando.")
else:
    TASK_CONTENTS = [
        "Verificar log de eventos do sistema operacional.",
        "Executar scan de antivirus no equipamento afetado.",
        "Fazer backup dos dados antes de qualquer alteracao.",
        "Contato com o usuario para coleta de evidencias.",
        "Testar conectividade de rede com traceroute.",
        "Reiniciar servico afetado e monitorar por 30 minutos.",
        "Atualizar driver/firmware para versao atual.",
        "Restaurar configuracao anterior (rollback).",
        "Validar resolucao com o usuario solicitante.",
        "Documentar solucao na base de conhecimento.",
        "Abrir acionamento com o fornecedor.",
        "Trocar hardware defeituoso por equipamento reserva.",
        "Aplicar patch de seguranca disponivel.",
        "Revisar ACL e permissoes de acesso.",
        "Reprogramar tarefa agendada que falhou.",
    ]
    # States: 1=informations, 2=todo, 3=done
    TASK_STATES = [1, 2, 3, 3, 3]  # maioria concluída

    # ~150 tarefas em tickets resolvidos/fechados
    sample_for_tasks = random.sample(SOLVED_TKT, min(120, len(SOLVED_TKT)))
    task_count = 0
    for tkt_id, tkt_date_creation in sample_for_tasks:
        if isinstance(tkt_date_creation, str):
            base_dt = datetime.strptime(tkt_date_creation[:19], "%Y-%m-%d %H:%M:%S")
        else:
            base_dt = datetime.combine(tkt_date_creation, datetime.min.time())

        n_tasks = random.randint(1, 2)
        delta_h = random.randint(1, 8)
        for ti in range(n_tasks):
            delta_h += random.randint(1, 12)
            task_dt = base_dt + timedelta(hours=delta_h)
            end_dt  = task_dt + timedelta(hours=random.randint(1, 4))
            content = random.choice(TASK_CONTENTS)
            state   = random.choice(TASK_STATES)
            tech_id = random.choice(TECH_IDS)
            uid     = str(_uuid.uuid4())
            cur.execute("""
                INSERT INTO glpi_tickettasks
                  (uuid, tickets_id, date, users_id, content, is_private,
                   actiontime, begin, end, state, users_id_tech,
                   date_mod, date_creation, timeline_position)
                VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s,
                        NOW(), NOW(), 1)
            """, (uid, tkt_id,
                  task_dt.strftime("%Y-%m-%d %H:%M:%S"),
                  tech_id, content,
                  random.randint(1800, 14400),
                  task_dt.strftime("%Y-%m-%d %H:%M:%S"),
                  end_dt.strftime("%Y-%m-%d %H:%M:%S"),
                  state, tech_id))
            task_count += 1

    conn.commit()
    print(f"  {task_count} tarefas de ticket")

# ─── 3. SATISFAÇÃO (ticketsatisfactions) ─────────────────────────────────────
print("\n[3/5] Satisfação de tickets")

if count("glpi_ticketsatisfactions") > 0:
    print("  ticketsatisfactions já preenchido, pulando.")
else:
    # Apenas tickets fechados recebem satisfação
    # Satisfaction: 1-5 (convertidos para scaled_to_5)
    # Type: 1=internal, 2=external
    satisfaction_count = 0
    # ~80% dos tickets fechados responderam
    respondents = random.sample(CLOSED_TKT, int(len(CLOSED_TKT) * 0.80))

    for tkt_id, tkt_date_creation in respondents:
        if isinstance(tkt_date_creation, str):
            base_dt = datetime.strptime(tkt_date_creation[:19], "%Y-%m-%d %H:%M:%S")
        else:
            base_dt = datetime.combine(tkt_date_creation, datetime.min.time())

        answered_dt = base_dt + timedelta(hours=random.randint(24, 72))
        begin_dt    = base_dt + timedelta(hours=random.randint(1, 6))

        # Distribuição realista: 60% 5-estrelas, 20% 4, 10% 3, 7% 2, 3% 1
        score = random.choices([5, 4, 3, 2, 1], weights=[60, 20, 10, 7, 3])[0]
        comment = ""
        if score <= 2:
            comment = random.choice([
                "Demorou muito para resolver.",
                "Nao resolveu meu problema completamente.",
                "Precisei ligar multiplas vezes.",
            ])
        elif score == 5:
            comment = random.choice([
                "Otimo atendimento, muito rapido!",
                "Tecnico muito prestativo.",
                "Resolvido rapidamente, parabens!",
                "",
            ])

        cur.execute("""
            INSERT INTO glpi_ticketsatisfactions
              (tickets_id, type, date_begin, date_answered,
               satisfaction, satisfaction_scaled_to_5, comment)
            VALUES (%s, 1, %s, %s, %s, %s, %s)
        """, (tkt_id,
              begin_dt.strftime("%Y-%m-%d %H:%M:%S"),
              answered_dt.strftime("%Y-%m-%d %H:%M:%S"),
              score, score, comment))
        satisfaction_count += 1

    conn.commit()
    print(f"  {satisfaction_count} avaliações de satisfação")

# ─── 4. TAREFAS DE PROBLEMA (problemtasks) ────────────────────────────────────
print("\n[4/5] Tarefas de problemas")

if count("glpi_problemtasks") > 0:
    print("  problemtasks já preenchido, pulando.")
else:
    # Checar colunas disponíveis
    cur.execute("DESCRIBE glpi_problemtasks")
    prob_task_cols = [r[0] for r in cur.fetchall()]

    PROB_TASK_CONTENTS = [
        "Identificar todos os sistemas afetados pelo problema.",
        "Coletar logs dos ultimos 7 dias para analise.",
        "Reproduzir o problema em ambiente de homologacao.",
        "Implementar workaround temporario para restaurar servico.",
        "Analisar causa raiz com a equipe tecnica.",
        "Desenvolver e testar correcao definitiva.",
        "Aplicar correcao em producao apos janela de mudanca.",
        "Validar resolucao com os usuarios afetados.",
        "Atualizar documentacao tecnica e base de conhecimento.",
        "Criar alerta de monitoramento para detectar reincidencia.",
    ]

    prob_task_count = 0
    for prob_id, prob_date in ALL_PROBLEMS:
        if isinstance(prob_date, str):
            base_dt = datetime.strptime(prob_date[:19], "%Y-%m-%d %H:%M:%S")
        else:
            base_dt = datetime.combine(prob_date, datetime.min.time())

        n_tasks = random.randint(2, 3)
        delta_h = random.randint(2, 8)
        for ti in range(n_tasks):
            delta_h += random.randint(4, 24)
            task_dt = base_dt + timedelta(hours=delta_h)
            end_dt  = task_dt + timedelta(hours=random.randint(2, 8))
            content = random.choice(PROB_TASK_CONTENTS)
            state   = random.choice([1, 3, 3])  # maioria concluída
            tech_id = random.choice(TECH_IDS)
            uid     = str(_uuid.uuid4())

            # Construir INSERT com base nas colunas disponíveis
            has_uuid    = "uuid" in prob_task_cols
            has_begin   = "begin" in prob_task_cols
            has_end     = "end" in prob_task_cols
            has_actiont = "actiontime" in prob_task_cols
            has_tlpos   = "timeline_position" in prob_task_cols

            extra_cols = []
            extra_vals = []
            if has_uuid:
                extra_cols.append("uuid")
                extra_vals.append(uid)
            if has_begin:
                extra_cols.append("`begin`")
                extra_vals.append(task_dt.strftime("%Y-%m-%d %H:%M:%S"))
            if has_end:
                extra_cols.append("`end`")
                extra_vals.append(end_dt.strftime("%Y-%m-%d %H:%M:%S"))
            if has_actiont:
                extra_cols.append("actiontime")
                extra_vals.append(random.randint(3600, 28800))
            if has_tlpos:
                extra_cols.append("timeline_position")
                extra_vals.append(1)

            base_cols = "problems_id, taskcategories_id, date, users_id, content, is_private, state, users_id_tech, date_mod, date_creation"
            all_cols  = base_cols + (", " + ", ".join(extra_cols) if extra_cols else "")
            placeholders = "%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()" + (", " + ", ".join(["%s"] * len(extra_vals)) if extra_vals else "")

            cur.execute(
                f"INSERT INTO glpi_problemtasks ({all_cols}) VALUES ({placeholders})",
                (prob_id, 0,
                 task_dt.strftime("%Y-%m-%d %H:%M:%S"),
                 tech_id, content, 0, state, tech_id) + tuple(extra_vals)
            )
            prob_task_count += 1

    conn.commit()
    print(f"  {prob_task_count} tarefas de problema")

# ─── 5. CHANGES ↔ PROBLEMS ───────────────────────────────────────────────────
print("\n[5/5] Vínculos changes ↔ problems")

if count("glpi_changes_problems") > 0:
    print("  changes_problems já preenchido, pulando.")
else:
    # Checar colunas da tabela
    cur.execute("DESCRIBE glpi_changes_problems")
    cp_cols = [r[0] for r in cur.fetchall()]

    chg_ids   = [cid for cid, _ in ALL_CHANGES]
    prob_ids  = [pid for pid, _ in ALL_PROBLEMS]

    # Cada mudança tem 1-2 problemas relacionados
    cp_pairs = set()
    for chg_id in chg_ids:
        n_probs = random.randint(1, 2)
        for prob_id in random.sample(prob_ids, min(n_probs, len(prob_ids))):
            cp_pairs.add((chg_id, prob_id))

    # Inserir com base nas colunas disponíveis
    cp_count = 0
    for chg_id, prob_id in cp_pairs:
        if "changes_id" in cp_cols and "problems_id" in cp_cols:
            cur.execute(
                "INSERT INTO glpi_changes_problems (changes_id, problems_id) VALUES (%s, %s)",
                (chg_id, prob_id)
            )
        elif "items_id" in cp_cols and "itemtype" in cp_cols:
            cur.execute(
                "INSERT INTO glpi_changes_problems (changes_id, itemtype, items_id) "
                "VALUES (%s, 'Problem', %s)", (chg_id, prob_id)
            )
        cp_count += 1

    conn.commit()
    print(f"  {cp_count} vínculos change ↔ problem")

# ─── RESUMO ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 68)
print("  RESUMO — EXPANSION 4")
print("=" * 68)
for tbl in [
    "glpi_itilfollowups", "glpi_tickettasks", "glpi_ticketsatisfactions",
    "glpi_problemtasks", "glpi_changes_problems",
]:
    cur.execute(f"SELECT COUNT(*) FROM `{tbl}`")
    print(f"  {tbl:<40} {cur.fetchone()[0]:>6}")

conn.close()
print("\nExpansion 4 concluída!")
