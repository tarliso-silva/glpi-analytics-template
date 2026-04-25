"""
seed_multi_entity.py — CRÍTICO
Cria hierarquia de entidades GLPI e redistribui TODOS os dados existentes
entre as entidades sem quebrar integridade referencial.

Hierarquia:
  Entidade raiz (0) — existente
  ├─ TI - Tecnologia da Informação  (id dinâmico)
  ├─ Operações                       (id dinâmico)
  └─ Financeiro                      (id dinâmico)

Distribuição:
  TI:        técnicos (68-78), SRV-* (51-65), WS 35-50, toda rede,
             racks, problemas, mudanças, projetos 1-3, softwares, KB
  Operações: solicitantes 79-103, WS 1-17, projetos 4-5, monitores 1-15,
             impressoras 1-4
  Financeiro: solicitantes 104-128, WS 18-34, projeto 6, monitores 16-30,
              impressoras 5-8
  Raiz (0):  usuário admin (2), fornecedores 1-4 (globais, is_recursive=1)

Idempotente: aborta se glpi_entities tiver mais de 1 registro.

ATENÇÃO: NÃO apaga dados existentes; apenas atualiza entities_id.
"""

import mysql.connector
from datetime import datetime, timezone

# ─── conexão ───────────────────────────────────────────────────────────────────
conn = mysql.connector.connect(
    host="localhost", port=3306, database="glpi",
    user="glpi", password="glpi"
)
cur = conn.cursor()
conn.autocommit = False
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

print("=== seed_multi_entity.py ===")

# ─── idempotência ──────────────────────────────────────────────────────────────
cur.execute("SELECT COUNT(*) FROM glpi_entities")
if cur.fetchone()[0] > 1:
    print("Entidades já criadas. Nada a fazer.")
    cur.close(); conn.close(); exit()

# ─── info da entidade raiz ─────────────────────────────────────────────────────
cur.execute("SELECT id, name, level FROM glpi_entities WHERE id = 0")
root = cur.fetchone()
root_id, root_name, root_level = root
child_level = root_level + 1
print(f"Root: id={root_id}, name='{root_name}', level={root_level}")
print(f"Nível dos filhos: {child_level}")

# ─── detectar colunas de glpi_entities ────────────────────────────────────────
cur.execute("SHOW COLUMNS FROM glpi_entities")
entity_cols = {r[0] for r in cur.fetchall()}
print(f"Colunas em glpi_entities (total): {len(entity_cols)}")

# ─── helper: insert seguro ────────────────────────────────────────────────────
def safe_insert(table, row_dict):
    cur2 = conn.cursor()
    cur2.execute(f"SHOW COLUMNS FROM {table}")
    cols_avail = {r[0] for r in cur2.fetchall()}
    cur2.close()
    filtered = {k: v for k, v in row_dict.items() if k in cols_avail}
    cols = ", ".join(filtered.keys())
    phs  = ", ".join(["%s"] * len(filtered))
    cur.execute(f"INSERT INTO {table} ({cols}) VALUES ({phs})", list(filtered.values()))
    return cur.lastrowid

# ─────────────────────────────────────────────────────────────────────────────
# FASE 1 — Criar entidades filhas
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FASE 1: Criar entidades filhas ===")

ENTITIES_DEF = [
    {
        "name": "TI - Tecnologia da Informação",
        "short": "TI",
        "comment": "Gestão de infraestrutura, sistemas e redes",
    },
    {
        "name": "Operações",
        "short": "Ops",
        "comment": "Equipes operacionais e suporte ao negócio",
    },
    {
        "name": "Financeiro",
        "short": "Fin",
        "comment": "Departamento financeiro e controladoria",
    },
]

entity_ids = {}   # "TI" / "Ops" / "Fin" → id
for edef in ENTITIES_DEF:
    completename = f"{root_name} > {edef['name']}"
    row = {
        "name"            : edef["name"],
        "entities_id"     : root_id,          # parent = 0
        "completename"    : completename,
        "comment"         : edef["comment"],
        "level"           : child_level,
        "sons_cache"      : None,              # GLPI recalcula sob demanda
        "ancestors_cache" : None,
        "address"         : "",
        "postcode"        : "",
        "town"            : "",
        "state"           : "",
        "country"         : "Brasil",
        "website"         : "",
        "phonenumber"     : "",
        "fax"             : "",
        "email"           : "",
        "date_mod"        : NOW,
        "date_creation"   : NOW,
    }
    eid = safe_insert("glpi_entities", row)
    entity_ids[edef["short"]] = eid
    print(f"  Entidade id={eid}: {edef['name']}")

conn.commit()
TI_ID  = entity_ids["TI"]
OPS_ID = entity_ids["Ops"]
FIN_ID = entity_ids["Fin"]
print(f"TI={TI_ID}  Operações={OPS_ID}  Financeiro={FIN_ID}")

# ─────────────────────────────────────────────────────────────────────────────
# FASE 2 — Mover grupos para TI (manter is_recursive=1)
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FASE 2: Grupos → TI ===")
cur.execute("""
    UPDATE glpi_groups
    SET entities_id = %s, is_recursive = 1
    WHERE id IN (7, 8, 9)
""", (TI_ID,))
print(f"  Grupos 7,8,9 → entity {TI_ID} (is_recursive=1). Linhas: {cur.rowcount}")
conn.commit()

# ─────────────────────────────────────────────────────────────────────────────
# FASE 3 — Distribuir usuários
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FASE 3: Usuários ===")

# Técnicos → TI
cur.execute("""
    UPDATE glpi_users SET entities_id = %s
    WHERE id BETWEEN 68 AND 78
""", (TI_ID,))
print(f"  Técnicos (68-78) → TI={TI_ID}. Linhas: {cur.rowcount}")

# Solicitantes 79-103 → Operações
cur.execute("""
    UPDATE glpi_users SET entities_id = %s
    WHERE id BETWEEN 79 AND 103
""", (OPS_ID,))
print(f"  Solicitantes 79-103 → Ops={OPS_ID}. Linhas: {cur.rowcount}")

# Solicitantes 104-128 → Financeiro
cur.execute("""
    UPDATE glpi_users SET entities_id = %s
    WHERE id BETWEEN 104 AND 128
""", (FIN_ID,))
print(f"  Solicitantes 104-128 → Fin={FIN_ID}. Linhas: {cur.rowcount}")

# Usuário admin (2) permanece em entity 0
conn.commit()

# ─────────────────────────────────────────────────────────────────────────────
# FASE 4 — Tickets seguem a entidade do solicitante
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FASE 4: Tickets ===")
cur.execute("""
    UPDATE glpi_tickets t
    SET entities_id = (
        SELECT u.entities_id
        FROM glpi_tickets_users tu
        JOIN glpi_users u ON u.id = tu.users_id
        WHERE tu.tickets_id = t.id
          AND tu.type = 1
          AND u.entities_id != 0
        LIMIT 1
    )
    WHERE EXISTS (
        SELECT 1
        FROM glpi_tickets_users tu
        JOIN glpi_users u ON u.id = tu.users_id
        WHERE tu.tickets_id = t.id
          AND tu.type = 1
          AND u.entities_id != 0
    )
""")
print(f"  Tickets atualizados: {cur.rowcount}")
conn.commit()

# ─────────────────────────────────────────────────────────────────────────────
# FASE 5 — Computadores
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FASE 5: Computadores ===")

# WS 1-17 → Operações
cur.execute("UPDATE glpi_computers SET entities_id = %s WHERE id BETWEEN 1 AND 17", (OPS_ID,))
print(f"  WS 1-17 → Ops. Linhas: {cur.rowcount}")

# WS 18-34 → Financeiro
cur.execute("UPDATE glpi_computers SET entities_id = %s WHERE id BETWEEN 18 AND 34", (FIN_ID,))
print(f"  WS 18-34 → Fin. Linhas: {cur.rowcount}")

# WS 35-50 → TI
cur.execute("UPDATE glpi_computers SET entities_id = %s WHERE id BETWEEN 35 AND 50", (TI_ID,))
print(f"  WS 35-50 → TI. Linhas: {cur.rowcount}")

# SRV 51-65 → TI
cur.execute("UPDATE glpi_computers SET entities_id = %s WHERE id BETWEEN 51 AND 65", (TI_ID,))
print(f"  SRV 51-65 → TI. Linhas: {cur.rowcount}")

conn.commit()

# Tabelas derivadas de Computer seguem a mesma entidade
print("  Atualizando tabelas derivadas de Computer...")

# glpi_items_operatingsystems
cur.execute("""
    UPDATE glpi_items_operatingsystems ios
    JOIN glpi_computers c ON c.id = ios.items_id AND ios.itemtype = 'Computer'
    SET ios.entities_id = c.entities_id
""")
print(f"    items_operatingsystems: {cur.rowcount} linhas")

# glpi_items_softwareversions
cur.execute("""
    UPDATE glpi_items_softwareversions isv
    JOIN glpi_computers c ON c.id = isv.items_id AND isv.itemtype = 'Computer'
    SET isv.entities_id = c.entities_id
""")
print(f"    items_softwareversions: {cur.rowcount} linhas")

# glpi_infocoms (Computer)
cur.execute("""
    UPDATE glpi_infocoms ic
    JOIN glpi_computers c ON c.id = ic.items_id AND ic.itemtype = 'Computer'
    SET ic.entities_id = c.entities_id
""")
print(f"    infocoms(Computer): {cur.rowcount} linhas")

conn.commit()

# ─────────────────────────────────────────────────────────────────────────────
# FASE 6 — Equipamentos de rede → TI
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FASE 6: Equipamentos de rede → TI ===")
cur.execute("UPDATE glpi_networkequipments SET entities_id = %s", (TI_ID,))
print(f"  NetworkEquipments → TI. Linhas: {cur.rowcount}")
conn.commit()

# ─────────────────────────────────────────────────────────────────────────────
# FASE 7 — Monitores e impressoras (distribuição proporcional)
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FASE 7: Monitores e impressoras ===")

# Monitores: IDs ordenados; primeiro terço Ops, segundo Fin, terceiro TI
cur.execute("SELECT id FROM glpi_monitors ORDER BY id")
monitor_ids = [r[0] for r in cur.fetchall()]
n = len(monitor_ids)
third = n // 3
m_ops = monitor_ids[:third]
m_fin = monitor_ids[third:2*third]
m_ti  = monitor_ids[2*third:]
if m_ops:
    cur.execute(f"UPDATE glpi_monitors SET entities_id = {OPS_ID} WHERE id IN ({','.join(map(str, m_ops))})")
    print(f"  Monitores → Ops: {cur.rowcount}")
if m_fin:
    cur.execute(f"UPDATE glpi_monitors SET entities_id = {FIN_ID} WHERE id IN ({','.join(map(str, m_fin))})")
    print(f"  Monitores → Fin: {cur.rowcount}")
if m_ti:
    cur.execute(f"UPDATE glpi_monitors SET entities_id = {TI_ID} WHERE id IN ({','.join(map(str, m_ti))})")
    print(f"  Monitores → TI: {cur.rowcount}")

# Impressoras: metade Ops, metade Fin
cur.execute("SELECT id FROM glpi_printers ORDER BY id")
printer_ids = [r[0] for r in cur.fetchall()]
half = len(printer_ids) // 2
p_ops = printer_ids[:half]
p_fin = printer_ids[half:]
if p_ops:
    cur.execute(f"UPDATE glpi_printers SET entities_id = {OPS_ID} WHERE id IN ({','.join(map(str, p_ops))})")
    print(f"  Impressoras → Ops: {cur.rowcount}")
if p_fin:
    cur.execute(f"UPDATE glpi_printers SET entities_id = {FIN_ID} WHERE id IN ({','.join(map(str, p_fin))})")
    print(f"  Impressoras → Fin: {cur.rowcount}")

conn.commit()

# ─────────────────────────────────────────────────────────────────────────────
# FASE 8 — Telefones seguem entidade do usuário associado
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FASE 8: Telefones ===")
cur.execute("""
    UPDATE glpi_phones p
    JOIN glpi_users u ON u.id = p.users_id AND p.users_id > 0
    SET p.entities_id = u.entities_id
    WHERE u.entities_id != 0
""")
print(f"  Telefones atualizados por usuário: {cur.rowcount}")
# Telefones sem usuário → TI
cur.execute("""
    UPDATE glpi_phones SET entities_id = %s
    WHERE users_id = 0 OR users_id IS NULL
""", (TI_ID,))
print(f"  Telefones sem usuário → TI: {cur.rowcount}")
conn.commit()

# ─────────────────────────────────────────────────────────────────────────────
# FASE 9 — Periféricos seguem entidade do usuário associado
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FASE 9: Periféricos ===")
cur.execute("""
    UPDATE glpi_peripherals p
    JOIN glpi_users u ON u.id = p.users_id AND p.users_id > 0
    SET p.entities_id = u.entities_id
    WHERE u.entities_id != 0
""")
print(f"  Periféricos atualizados por usuário: {cur.rowcount}")
# Periféricos sem usuário → distribuição proporcional por ID
cur.execute("""
    UPDATE glpi_peripherals SET entities_id = %s
    WHERE users_id = 0 OR users_id IS NULL
""", (TI_ID,))
print(f"  Periféricos sem usuário → TI: {cur.rowcount}")
conn.commit()

# ─────────────────────────────────────────────────────────────────────────────
# FASE 10 — Problemas e mudanças → TI
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FASE 10: Problemas e mudanças → TI ===")
cur.execute("UPDATE glpi_problems SET entities_id = %s", (TI_ID,))
print(f"  Problemas: {cur.rowcount}")
cur.execute("UPDATE glpi_changes SET entities_id = %s", (TI_ID,))
print(f"  Mudanças: {cur.rowcount}")
conn.commit()

# ─────────────────────────────────────────────────────────────────────────────
# FASE 11 — Projetos
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FASE 11: Projetos ===")
cur.execute("SELECT id FROM glpi_projects ORDER BY id")
project_ids = [r[0] for r in cur.fetchall()]
print(f"  Projetos encontrados: {project_ids}")

# Projetos 1-3 → TI; 4-5 → Operações; 6 → Financeiro
for pid in project_ids:
    if pid <= 3:
        cur.execute("UPDATE glpi_projects SET entities_id = %s WHERE id = %s", (TI_ID, pid))
        ent_name = "TI"
    elif pid <= 5:
        cur.execute("UPDATE glpi_projects SET entities_id = %s WHERE id = %s", (OPS_ID, pid))
        ent_name = "Ops"
    else:
        cur.execute("UPDATE glpi_projects SET entities_id = %s WHERE id = %s", (FIN_ID, pid))
        ent_name = "Fin"
    print(f"  Projeto {pid} → {ent_name}")
conn.commit()

# ─────────────────────────────────────────────────────────────────────────────
# FASE 12 — Fornecedores e contratos
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FASE 12: Fornecedores ===")
cur.execute("SELECT id, name FROM glpi_suppliers ORDER BY id")
suppliers = cur.fetchall()
print(f"  Fornecedores: {[(s[0], s[1]) for s in suppliers]}")

for s in suppliers:
    sid, sname = s[0], s[1]
    if sid <= 4:
        # Fornecedores globais → entidade raiz com is_recursive=1
        cur.execute("""
            UPDATE glpi_suppliers SET entities_id = 0, is_recursive = 1
            WHERE id = %s
        """, (sid,))
        print(f"  Fornecedor {sid} ({sname}) → Raiz (global)")
    else:
        # Fornecedores específicos → TI
        cur.execute("""
            UPDATE glpi_suppliers SET entities_id = %s, is_recursive = 0
            WHERE id = %s
        """, (TI_ID, sid))
        print(f"  Fornecedor {sid} ({sname}) → TI")

conn.commit()

# Contratos seguem o fornecedor
print("  Contratos seguem fornecedor...")
cur.execute("""
    UPDATE glpi_contracts c
    JOIN glpi_suppliers s ON s.id = (
        SELECT suppliers_id
        FROM glpi_contracts_suppliers
        WHERE contracts_id = c.id
        LIMIT 1
    )
    SET c.entities_id = s.entities_id
    WHERE EXISTS (
        SELECT 1 FROM glpi_contracts_suppliers WHERE contracts_id = c.id
    )
""")
print(f"  Contratos atualizados: {cur.rowcount}")
conn.commit()

# ─────────────────────────────────────────────────────────────────────────────
# FASE 13 — Softwares e licenças → TI (is_recursive=1 para visibilidade global)
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FASE 13: Softwares e licenças → TI ===")
cur.execute("UPDATE glpi_softwares SET entities_id = %s, is_recursive = 1", (TI_ID,))
print(f"  Softwares → TI (is_recursive=1): {cur.rowcount}")
cur.execute("UPDATE glpi_softwareversions SET entities_id = %s, is_recursive = 1", (TI_ID,))
print(f"  Software versions → TI (is_recursive=1): {cur.rowcount}")
cur.execute("UPDATE glpi_softwarelicenses SET entities_id = %s, is_recursive = 1", (TI_ID,))
print(f"  Licenças → TI (is_recursive=1): {cur.rowcount}")
conn.commit()

# ─────────────────────────────────────────────────────────────────────────────
# FASE 14 — KB → TI (is_recursive=1)
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FASE 14: Artigos KB → TI ===")
cur.execute("UPDATE glpi_knowbaseitems SET is_recursive = 1 WHERE entities_id = 0")
print(f"  KB items já em entity 0 → is_recursive=1: {cur.rowcount}")
# Itens da KB não têm entities_id direto; eles têm glpi_knowbaseitems_profiles
# A visibilidade é por perfil, não entidade; não alterar entities_id
conn.commit()

# ─────────────────────────────────────────────────────────────────────────────
# FASE 15 — Documentos → entidade raiz (globais)
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FASE 15: Documentos → raiz (is_recursive=1) ===")
cur.execute("UPDATE glpi_documents SET entities_id = 0, is_recursive = 1")
print(f"  Documentos: {cur.rowcount}")
conn.commit()

# ─────────────────────────────────────────────────────────────────────────────
# FASE 16 — Racks → TI
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FASE 16: Racks → TI ===")
cur.execute("UPDATE glpi_racks SET entities_id = %s", (TI_ID,))
print(f"  Racks → TI: {cur.rowcount}")
cur.execute("UPDATE glpi_dcrooms SET entities_id = %s", (TI_ID,))
print(f"  DC Rooms → TI: {cur.rowcount}")
conn.commit()

# ─────────────────────────────────────────────────────────────────────────────
# FASE 17 — Categorias ITIL e SLAs → raiz (is_recursive=1 para herança)
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FASE 17: Categorias e SLAs → raiz ===")

# Categorias ITIL
cur.execute("SHOW COLUMNS FROM glpi_itilcategories")
itilcat_cols = {r[0] for r in cur.fetchall()}
if "is_recursive" in itilcat_cols:
    cur.execute("UPDATE glpi_itilcategories SET entities_id = 0, is_recursive = 1")
    print(f"  ITIL categories is_recursive=1: {cur.rowcount}")

# SLAs
cur.execute("SHOW COLUMNS FROM glpi_slas")
sla_cols = {r[0] for r in cur.fetchall()}
if "is_recursive" in sla_cols:
    cur.execute("UPDATE glpi_slas SET entities_id = 0, is_recursive = 1")
    print(f"  SLAs is_recursive=1: {cur.rowcount}")
if "entities_id" in sla_cols and "is_recursive" not in sla_cols:
    cur.execute("UPDATE glpi_slas SET entities_id = 0")
    print(f"  SLAs → raiz: {cur.rowcount}")

# SLOs
cur.execute("SHOW TABLES LIKE 'glpi_slos'")
if cur.fetchone():
    cur.execute("SHOW COLUMNS FROM glpi_slos")
    slo_cols = {r[0] for r in cur.fetchall()}
    if "entities_id" in slo_cols:
        if "is_recursive" in slo_cols:
            cur.execute("UPDATE glpi_slos SET entities_id = 0, is_recursive = 1")
        else:
            cur.execute("UPDATE glpi_slos SET entities_id = 0")
        print(f"  SLOs → raiz: {cur.rowcount}")

conn.commit()

# ─────────────────────────────────────────────────────────────────────────────
# FASE 18 — Atualizar sons_cache da entidade raiz
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FASE 18: Atualizar sons_cache raiz ===")
sons = f"|{root_id}|{TI_ID}|{OPS_ID}|{FIN_ID}|"
cur.execute("UPDATE glpi_entities SET sons_cache = %s WHERE id = 0", (sons,))
print(f"  sons_cache root → '{sons}'")
conn.commit()

# ─────────────────────────────────────────────────────────────────────────────
# Verificação final
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== VERIFICAÇÃO FINAL ===")

tables_check = [
    ("glpi_entities",        "id"),
    ("glpi_users",           "entities_id"),
    ("glpi_tickets",         "entities_id"),
    ("glpi_computers",       "entities_id"),
    ("glpi_networkequipments","entities_id"),
    ("glpi_racks",           "entities_id"),
    ("glpi_problems",        "entities_id"),
    ("glpi_changes",         "entities_id"),
    ("glpi_projects",        "entities_id"),
    ("glpi_suppliers",       "entities_id"),
    ("glpi_softwares",       "entities_id"),
]

# Mapa de entidades para exibição
ent_map = {0: "Raiz", TI_ID: "TI", OPS_ID: "Ops", FIN_ID: "Fin"}

for table, col in tables_check:
    try:
        cur.execute(f"SELECT {col}, COUNT(*) FROM {table} GROUP BY {col} ORDER BY {col}")
        rows = cur.fetchall()
        dist = {r[0]: r[1] for r in rows}
        display = {ent_map.get(k, f"ent{k}"): v for k, v in dist.items()}
        print(f"  {table}: {display}")
    except Exception as e:
        print(f"  {table}: ERRO {e}")

print("\n=== CONCLUÍDO COM SUCESSO ===")
print(f"  Entidades criadas: TI={TI_ID}, Ops={OPS_ID}, Fin={FIN_ID}")

cur.close()
conn.close()
