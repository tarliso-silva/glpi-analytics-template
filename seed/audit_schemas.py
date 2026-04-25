"""
audit_schemas.py — Descobre schemas de tabelas-alvo e estado atual dos dados.
Usado antes de escrever os scripts de rack e multi-entidade.
"""
import mysql.connector

DB = dict(host="localhost", port=3306, database="glpi", user="glpi", password="glpi")
conn = mysql.connector.connect(**DB)
cur  = conn.cursor()

def cols(t):
    try:
        cur.execute(f"DESCRIBE `{t}`")
        return [r[0] for r in cur.fetchall()]
    except:
        return ["[NÃO EXISTE]"]

def count(t):
    try:
        cur.execute(f"SELECT COUNT(*) FROM `{t}`")
        return cur.fetchone()[0]
    except:
        return "N/A"

print("=" * 72)
print("  AUDIT SCHEMAS — Racks e Entidades")
print("=" * 72)

# ── Tabelas de Rack ──────────────────────────────────────────────────────────
print("\n[RACKS]")
for t in ["glpi_racktypes", "glpi_racks", "glpi_items_racks", "glpi_dcrooms"]:
    print(f"  {t} (rows={count(t)})")
    for c in cols(t):
        print(f"    - {c}")

# ── Entidades ────────────────────────────────────────────────────────────────
print("\n[ENTIDADES]")
print(f"  glpi_entities (rows={count('glpi_entities')})")
for c in cols("glpi_entities"):
    print(f"    - {c}")

cur.execute("SELECT id, name, entities_id, level, sons_cache, ancestors_cache FROM glpi_entities")
for row in cur.fetchall():
    print(f"  RECORD: id={row[0]}, name='{row[1]}', parent={row[2]}, level={row[3]}, "
          f"sons='{row[4]}', anc='{row[5]}')")

# ── Usuários — distribuição técnicos vs solicitantes ─────────────────────────
print("\n[USUÁRIOS]")
cur.execute("SELECT COUNT(*) FROM glpi_users")
print(f"  Total users: {cur.fetchone()[0]}")

cur.execute("""
    SELECT u.id, u.name, u.entities_id, u.is_active,
           (SELECT COUNT(*) FROM glpi_groups_users gu WHERE gu.users_id = u.id) AS in_groups
    FROM glpi_users u
    ORDER BY u.id
""")
users = cur.fetchall()
tech_ids = [u[0] for u in users if u[4] > 0]
req_ids  = [u[0] for u in users if u[4] == 0 and not u[1].startswith('glpi')]
sys_ids  = [u[0] for u in users if u[1].startswith('glpi') or u[1] in ('admin', 'normal', 'post-only', 'tech', 'self-service')]

print(f"  Técnicos (em grupos): {len(tech_ids)} — IDs: {tech_ids}")
print(f"  Solicitantes: {len(req_ids)} — primeiros IDs: {req_ids[:5]}...{req_ids[-3:]}")
print(f"  Sys/admin users: {len(sys_ids)} — {sys_ids[:10]}")

# ── Computadores — padrão de nomes ───────────────────────────────────────────
print("\n[COMPUTADORES]")
cur.execute("SELECT id, name, entities_id FROM glpi_computers ORDER BY name")
computers = cur.fetchall()
srv = [(r[0], r[1]) for r in computers if r[1].startswith('SRV')]
ws  = [(r[0], r[1]) for r in computers if not r[1].startswith('SRV')]
print(f"  Servidores (SRV-*): {len(srv)} — IDs: {[x[0] for x in srv]}")
print(f"  Workstations:       {len(ws)}  — IDs: {[x[0] for x in ws[:5]]}...")

# ── Network equipments ───────────────────────────────────────────────────────
print("\n[NETWORK EQUIP]")
cur.execute("SELECT id, name, entities_id FROM glpi_networkequipments ORDER BY id")
neq = cur.fetchall()
print(f"  Total: {len(neq)} — IDs: {[r[0] for r in neq]}")
for r in neq:
    print(f"    id={r[0]}, name='{r[1]}', entity={r[2]}")

# ── Locations ────────────────────────────────────────────────────────────────
print("\n[LOCATIONS]")
cur.execute("SELECT id, name FROM glpi_locations ORDER BY id")
for r in cur.fetchall():
    print(f"  id={r[0]}, name='{r[1]}'")

# ── Grupos ───────────────────────────────────────────────────────────────────
print("\n[GRUPOS]")
cur.execute("SELECT id, name, entities_id, is_recursive FROM glpi_groups ORDER BY id")
for r in cur.fetchall():
    print(f"  id={r[0]}, name='{r[1]}', entity={r[2]}, recursive={r[3]}")

# ── Contagem geral das tabelas principais ─────────────────────────────────────
print("\n[DISTRIBUIÇÃO ENTITIES_ID]")
tables_with_entity = [
    "glpi_tickets", "glpi_computers", "glpi_networkequipments",
    "glpi_monitors", "glpi_printers", "glpi_problems", "glpi_changes", "glpi_projects"
]
for t in tables_with_entity:
    cur.execute(f"SELECT entities_id, COUNT(*) FROM `{t}` GROUP BY entities_id")
    rows = cur.fetchall()
    print(f"  {t}: {dict(rows)}")

conn.close()
print("\nAuditoria concluída.")
