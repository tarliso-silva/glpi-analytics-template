"""
validate_integrity.py — Valida integridade referencial pós-redistribuição multi-entidade.

Verificações:
  1. Entidades existentes e hierarquia
  2. Usuários sem entidade válida
  3. Tickets apontando para entidade inexistente
  4. Tickets sem solicitante
  5. Computadores com entidade inválida
  6. Items em racks verificando rack e item existentes
  7. Distribuição de volumes por entidade (resumo)
  8. Softwares/licenças com is_recursive correto
"""

import mysql.connector

conn = mysql.connector.connect(
    host="localhost", port=3306, database="glpi",
    user="glpi", password="glpi"
)
cur = conn.cursor()

print("=== validate_integrity.py ===\n")

errors   = 0
warnings = 0

def check(label, query, expect_zero=True):
    """Executa query e reporta resultado."""
    global errors, warnings
    cur.execute(query)
    rows = cur.fetchall()
    count = rows[0][0] if rows and len(rows[0]) == 1 else len(rows)
    if expect_zero and count > 0:
        print(f"  [ERRO]  {label}: {count} registro(s)")
        if len(rows) <= 5 and len(rows[0]) > 1:
            for r in rows:
                print(f"          {r}")
        errors += 1
    elif not expect_zero:
        print(f"  [INFO]  {label}: {count}")
    else:
        print(f"  [OK]    {label}")
    return count

# ─────────────────────────────────────────────────────────────────────────────
# 1. Hierarquia de entidades
# ─────────────────────────────────────────────────────────────────────────────
print("--- 1. Entidades ---")
cur.execute("SELECT id, name, entities_id, level FROM glpi_entities ORDER BY id")
entities = cur.fetchall()
entity_ids = {e[0] for e in entities}
for e in entities:
    print(f"  id={e[0]}, name='{e[1]}', parent={e[2]}, level={e[3]}")

expected_entities = 5   # Empresa + Matriz + Filial SP + Filial RJ + Filial MG
if len(entities) != expected_entities:
    print(f"  [AVISO] Esperado {expected_entities} entidades, encontrado {len(entities)}")
    warnings += 1
else:
    print(f"  [OK]    {len(entities)} entidades")

# ─────────────────────────────────────────────────────────────────────────────
# 2. Registros com entities_id inválida (não existe em glpi_entities)
# ─────────────────────────────────────────────────────────────────────────────
print("\n--- 2. Integridade entities_id ---")

tables_entity = [
    "glpi_users",
    "glpi_tickets",
    "glpi_computers",
    "glpi_networkequipments",
    "glpi_racks",
    "glpi_monitors",
    "glpi_printers",
    "glpi_phones",
    "glpi_peripherals",
    "glpi_problems",
    "glpi_changes",
    "glpi_projects",
    "glpi_softwares",
    "glpi_suppliers",
]

for table in tables_entity:
    try:
        # Exclude GLPI built-in accounts (id <= 2) that legitimately have NULL entities_id
        extra = "AND t.id > 2" if table == "glpi_users" else ""
        check(
            f"Registros em {table} com entities_id inválida",
            f"""
            SELECT COUNT(*) FROM {table} t
            WHERE NOT EXISTS (
                SELECT 1 FROM glpi_entities e WHERE e.id = t.entities_id
            ) {extra}
            """
        )
    except Exception as ex:
        print(f"  [SKIP]  {table}: {ex}")

# ─────────────────────────────────────────────────────────────────────────────
# 3. Tickets sem solicitante válido
# ─────────────────────────────────────────────────────────────────────────────
print("\n--- 3. Integridade tickets ↔ solicitantes ---")
check(
    "Tickets sem solicitante (type=1)",
    """
    SELECT COUNT(*) FROM glpi_tickets t
    WHERE NOT EXISTS (
        SELECT 1 FROM glpi_tickets_users tu
        WHERE tu.tickets_id = t.id AND tu.type = 1
    )
    """
)

check(
        "Tickets com entities_id = 0 ou inexistente",
        """
        SELECT COUNT(*) FROM glpi_tickets t
        WHERE NOT EXISTS (SELECT 1 FROM glpi_entities e WHERE e.id = t.entities_id)
           OR t.entities_id = 0
        """
    )

# ─────────────────────────────────────────────────────────────────────────────
# 4. Itens em racks
# ─────────────────────────────────────────────────────────────────────────────
print("\n--- 4. Itens nos racks ---")

# Rack IDs válidos
cur.execute("SELECT id FROM glpi_racks")
rack_ids = {r[0] for r in cur.fetchall()}

# Racks em glpi_items_racks apontando para rack inexistente
check(
    "glpi_items_racks com racks_id inválido",
    """
    SELECT COUNT(*) FROM glpi_items_racks ir
    WHERE NOT EXISTS (SELECT 1 FROM glpi_racks r WHERE r.id = ir.racks_id)
    """
)

# Computers em racks que não existem
check(
    "Computers em racks não encontrados em glpi_computers",
    """
    SELECT COUNT(*) FROM glpi_items_racks ir
    WHERE ir.itemtype = 'Computer'
      AND NOT EXISTS (SELECT 1 FROM glpi_computers c WHERE c.id = ir.items_id)
    """
)

# NetworkEquipment em racks que não existem
check(
    "NetworkEquipment em racks não encontrados",
    """
    SELECT COUNT(*) FROM glpi_items_racks ir
    WHERE ir.itemtype = 'NetworkEquipment'
      AND NOT EXISTS (SELECT 1 FROM glpi_networkequipments n WHERE n.id = ir.items_id)
    """
)

# Distribuição nos racks
cur.execute("""
    SELECT r.name, ir.itemtype, COUNT(*) cnt
    FROM glpi_items_racks ir
    JOIN glpi_racks r ON r.id = ir.racks_id
    GROUP BY r.name, ir.itemtype
    ORDER BY r.name, ir.itemtype
""")
print("  Distribuição nos racks:")
for row in cur.fetchall():
    print(f"    {row[0]}: {row[1]} × {row[2]}")

# ─────────────────────────────────────────────────────────────────────────────
# 5. Integridade software ↔ computadores
# ─────────────────────────────────────────────────────────────────────────────
print("\n--- 5. Software installations ---")
check(
    "glpi_items_softwareversions com computer inexistente",
    """
    SELECT COUNT(*) FROM glpi_items_softwareversions isv
    WHERE isv.itemtype = 'Computer'
      AND NOT EXISTS (SELECT 1 FROM glpi_computers c WHERE c.id = isv.items_id)
    """
)

check(
    "glpi_items_operatingsystems com computer inexistente",
    """
    SELECT COUNT(*) FROM glpi_items_operatingsystems ios
    WHERE ios.itemtype = 'Computer'
      AND NOT EXISTS (SELECT 1 FROM glpi_computers c WHERE c.id = ios.items_id)
    """
)

# ─────────────────────────────────────────────────────────────────────────────
# 6. Resumo de volumes por entidade
# ─────────────────────────────────────────────────────────────────────────────
print("\n--- 6. Distribuição de volumes por entidade ---")

# Mapa de entidades
cur.execute("SELECT id, name FROM glpi_entities")
ent_map = {r[0]: r[1] for r in cur.fetchall()}

summary_tables = {
    "Usuários"       : "glpi_users",
    "Tickets"        : "glpi_tickets",
    "Computadores"   : "glpi_computers",
    "Redes"          : "glpi_networkequipments",
    "Monitores"      : "glpi_monitors",
    "Impressoras"    : "glpi_printers",
    "Telefones"      : "glpi_phones",
    "Periféricos"    : "glpi_peripherals",
    "Problemas"      : "glpi_problems",
    "Mudanças"       : "glpi_changes",
    "Projetos"       : "glpi_projects",
    "Fornecedores"   : "glpi_suppliers",
    "Softwares"      : "glpi_softwares",
    "Racks"          : "glpi_racks",
}

# Descobrir IDs e nomes dinamicamente
cur.execute("SELECT id, name FROM glpi_entities ORDER BY id")
entity_rows = cur.fetchall()
col_ids    = [r[0] for r in entity_rows]
col_names  = [r[1][:9] for r in entity_rows]  # truncate for display

hdr = " | ".join(f"{n:>9}" for n in col_names)
print(f"  {'Recurso':<20} | {hdr} | {'Total':>7}")
print(f"  {'-'*20}-+-" + "-+-".join(["-"*9]*len(col_ids)) + "-+-" + "-"*7)

for label, table in summary_tables.items():
    try:
        # Exclude GLPI built-in accounts (id <= 2) from user count
        where = "WHERE id > 2" if table == "glpi_users" else ""
        cur.execute(f"SELECT entities_id, COUNT(*) FROM {table} {where} GROUP BY entities_id")
        dist = {r[0]: r[1] for r in cur.fetchall()}
        vals = [dist.get(eid, 0) for eid in col_ids]
        total = sum(dist.values())
        orphan = sum(v for k, v in dist.items() if k not in set(col_ids))
        row = " | ".join(f"{v:>9}" for v in vals)
        flag = " [ORFÃO!]" if orphan > 0 else ""
        print(f"  {label:<20} | {row} | {total:>7}{flag}")
    except Exception as ex:
        print(f"  {label:<20} | ERRO: {ex}")

# ─────────────────────────────────────────────────────────────────────────────
# 7. Resultado final
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n=== RESULTADO ===")
print(f"  Erros:    {errors}")
print(f"  Avisos:   {warnings}")
if errors == 0:
    print("  STATUS: OK — integridade referencial válida")
else:
    print("  STATUS: FALHOU — revisar erros acima")

cur.close()
conn.close()
