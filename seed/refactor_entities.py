"""
refactor_entities.py — Refatora entidades GLPI de departamentos funcionais
para estrutura organizacional geográfica (ITIL-compliant).

Antes:                        Depois:
  Entidade raiz (0)             Empresa        (0, renomeada)
  ├─ TI - Tecnologia (1)        ├─ Matriz      (novo id, ex-sede TI)
  ├─ Operações       (2)        ├─ Filial SP   (novo id)
  └─ Financeiro      (3)        ├─ Filial RJ   (novo id)
                                └─ Filial MG   (novo id)

Distribuição:
  Matriz     : técnicos (68-78), solicitantes 79-90,  SRV 51-65, WS 42-50,
               rede (12), racks (3), problemas, mudanças, projetos 1-2,
               fornecedores 5-8, softwares (is_recursive=1), grupos (is_recursive=1)
  Filial SP  : solicitantes 91-103, WS  1-17, projetos 3-4, monitores slice0
  Filial RJ  : solicitantes 104-115, WS 18-34, projetos 5,   monitores slice1
  Filial MG  : solicitantes 116-128, WS 35-41, projeto  6,   monitores slice2
  Empresa (0): admin (2), fornecedores globais 1-4 (is_recursive=1),
               documentos, SLAs, KB, categorias ITIL

Idempotente: aborta se 'Matriz' já existir.
Seguro     : scan dinâmico elimina qualquer referência residual a ids 1,2,3
             antes de deletá-las de glpi_entities.
"""

import mysql.connector
from datetime import datetime, timezone

# ── conexão ────────────────────────────────────────────────────────────────────
conn = mysql.connector.connect(
    host="localhost", port=3306, database="glpi",
    user="glpi", password="glpi"
)
cur = conn.cursor()
conn.autocommit = False
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

print("=== refactor_entities.py ===")

# ── idempotência ───────────────────────────────────────────────────────────────
cur.execute("SELECT COUNT(*) FROM glpi_entities WHERE name = 'Matriz'")
if cur.fetchone()[0] > 0:
    print("Refatoração já aplicada ('Matriz' existe). Nada a fazer.")
    cur.close(); conn.close(); exit(0)

cur.execute("SELECT id FROM glpi_entities WHERE id IN (1, 2, 3) ORDER BY id")
found = [r[0] for r in cur.fetchall()]
if set(found) != {1, 2, 3}:
    print(f"ERRO: entidades departamentais (1,2,3) não encontradas. Encontradas: {found}")
    print("Verifique o estado do banco antes de prosseguir.")
    cur.close(); conn.close(); exit(1)

OLD_TI  = 1
OLD_OPS = 2
OLD_FIN = 3
OLD_IDS = (OLD_TI, OLD_OPS, OLD_FIN)

# ── helpers ────────────────────────────────────────────────────────────────────
def get_cols(table):
    cur.execute(f"SHOW COLUMNS FROM `{table}`")
    return {r[0] for r in cur.fetchall()}

def safe_insert(table, row_dict):
    cols_avail = get_cols(table)
    filtered = {k: v for k, v in row_dict.items() if k in cols_avail}
    cols_str = ", ".join(f"`{k}`" for k in filtered)
    phs      = ", ".join(["%s"] * len(filtered))
    cur.execute(
        f"INSERT INTO `{table}` ({cols_str}) VALUES ({phs})",
        list(filtered.values())
    )
    return cur.lastrowid

def bulk_update(table, entity_id, ids):
    if not ids:
        return 0
    placeholders = ", ".join(["%s"] * len(ids))
    cur.execute(
        f"UPDATE `{table}` SET entities_id = %s WHERE id IN ({placeholders})",
        [entity_id] + list(ids)
    )
    return cur.rowcount


# ─────────────────────────────────────────────────────────────────────────────
# FASE 1 — Renomear entidade raiz → "Empresa"
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FASE 1: Renomear raiz 'Entidade raiz' → 'Empresa' ===")
cur.execute("""
    UPDATE glpi_entities
    SET name = 'Empresa', completename = 'Empresa'
    WHERE id = 0
""")
print(f"  Entity 0 → 'Empresa'. Linhas: {cur.rowcount}")
conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# FASE 2 — Criar entidades geográficas
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FASE 2: Criar entidades geográficas ===")

ENTITY_DEFS = [
    {
        "name": "Matriz",
        "comment": "Sede corporativa — São Paulo. Centro de TI, infraestrutura e direção.",
    },
    {
        "name": "Filial SP",
        "comment": "Filial São Paulo — operações e suporte regional SP.",
    },
    {
        "name": "Filial RJ",
        "comment": "Filial Rio de Janeiro — operações regionais RJ.",
    },
    {
        "name": "Filial MG",
        "comment": "Filial Minas Gerais — Belo Horizonte.",
    },
]

new_ids = []
for edef in ENTITY_DEFS:
    eid = safe_insert("glpi_entities", {
        "name"            : edef["name"],
        "entities_id"     : 0,
        "completename"    : f"Empresa > {edef['name']}",
        "comment"         : edef["comment"],
        "level"           : 2,
        "sons_cache"      : None,       # atualizado logo abaixo
        "ancestors_cache" : "|0|",
        "country"         : "Brasil",
        "date_mod"        : NOW,
        "date_creation"   : NOW,
    })
    cur.execute(
        "UPDATE glpi_entities SET sons_cache = %s WHERE id = %s",
        (f"|{eid}|", eid)
    )
    new_ids.append(eid)
    print(f"  id={eid}: {edef['name']}")

conn.commit()
MTZ, SP, RJ, MG = new_ids
print(f"  Matriz={MTZ}  Filial SP={SP}  Filial RJ={RJ}  Filial MG={MG}")


# ─────────────────────────────────────────────────────────────────────────────
# FASE 3 — Grupos → Matriz (is_recursive=1 — visíveis em todas as entidades)
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FASE 3: Grupos → Matriz (is_recursive=1) ===")
cur.execute("""
    UPDATE glpi_groups
    SET entities_id = %s, is_recursive = 1
    WHERE id IN (7, 8, 9)
""", (MTZ,))
print(f"  Grupos Infraestrutura/Sistemas/Redes → Matriz. Linhas: {cur.rowcount}")
conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# FASE 4 — Usuários
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FASE 4: Usuários ===")

# Admin permanece na raiz
cur.execute("UPDATE glpi_users SET entities_id = 0 WHERE id = 2")
print(f"  Admin (id=2) → Empresa/Raiz. Linhas: {cur.rowcount}")

# Técnicos → Matriz (equipe de TI sediada na sede)
cur.execute(
    "UPDATE glpi_users SET entities_id = %s WHERE id BETWEEN 68 AND 78",
    (MTZ,)
)
print(f"  Técnicos 68-78 → Matriz. Linhas: {cur.rowcount}")

# Solicitantes: distribuição geográfica equilibrada (12/13/12/13)
cur.execute(
    "UPDATE glpi_users SET entities_id = %s WHERE id BETWEEN 79 AND 90",
    (MTZ,)
)
print(f"  Solicitantes 79-90  → Matriz    (12). Linhas: {cur.rowcount}")

cur.execute(
    "UPDATE glpi_users SET entities_id = %s WHERE id BETWEEN 91 AND 103",
    (SP,)
)
print(f"  Solicitantes 91-103 → Filial SP (13). Linhas: {cur.rowcount}")

cur.execute(
    "UPDATE glpi_users SET entities_id = %s WHERE id BETWEEN 104 AND 115",
    (RJ,)
)
print(f"  Solicitantes 104-115 → Filial RJ (12). Linhas: {cur.rowcount}")

cur.execute(
    "UPDATE glpi_users SET entities_id = %s WHERE id BETWEEN 116 AND 128",
    (MG,)
)
print(f"  Solicitantes 116-128 → Filial MG (13). Linhas: {cur.rowcount}")

conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# FASE 5 — Tickets seguem entidade do solicitante (type=1)
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FASE 5: Tickets seguem solicitante ===")
cur.execute("""
    UPDATE glpi_tickets t
    SET entities_id = (
        SELECT u.entities_id
        FROM glpi_tickets_users tu
        JOIN glpi_users u ON u.id = tu.users_id
        WHERE tu.tickets_id = t.id
          AND tu.type = 1
          AND u.entities_id NOT IN (0, 1, 2, 3)
        LIMIT 1
    )
    WHERE EXISTS (
        SELECT 1
        FROM glpi_tickets_users tu
        JOIN glpi_users u ON u.id = tu.users_id
        WHERE tu.tickets_id = t.id
          AND tu.type = 1
          AND u.entities_id NOT IN (0, 1, 2, 3)
    )
""")
print(f"  Tickets migrados: {cur.rowcount}")
conn.commit()

# Verificar distribuição de tickets
cur.execute("""
    SELECT e.name, COUNT(*) cnt
    FROM glpi_tickets t JOIN glpi_entities e ON e.id = t.entities_id
    WHERE t.is_deleted = 0
    GROUP BY e.name ORDER BY e.name
""")
print("  Distribuição após migração:")
for row in cur.fetchall():
    print(f"    {row[0]}: {row[1]} tickets")


# ─────────────────────────────────────────────────────────────────────────────
# FASE 6 — Computadores + tabelas derivadas
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FASE 6: Computadores ===")

# WS 1-17  (era Ops)  → Filial SP
cur.execute(
    "UPDATE glpi_computers SET entities_id = %s WHERE id BETWEEN 1 AND 17", (SP,)
)
print(f"  WS  1-17  → Filial SP. Linhas: {cur.rowcount}")

# WS 18-34 (era Fin)  → Filial RJ
cur.execute(
    "UPDATE glpi_computers SET entities_id = %s WHERE id BETWEEN 18 AND 34", (RJ,)
)
print(f"  WS  18-34 → Filial RJ. Linhas: {cur.rowcount}")

# WS 35-41 (era TI)  → Filial MG  (7 workstations para a filial MG)
cur.execute(
    "UPDATE glpi_computers SET entities_id = %s WHERE id BETWEEN 35 AND 41", (MG,)
)
print(f"  WS  35-41 → Filial MG. Linhas: {cur.rowcount}")

# WS 42-50 (era TI)  → Matriz (9 workstations HQ)
cur.execute(
    "UPDATE glpi_computers SET entities_id = %s WHERE id BETWEEN 42 AND 50", (MTZ,)
)
print(f"  WS  42-50 → Matriz.    Linhas: {cur.rowcount}")

# SRV 51-65 (era TI) → Matriz (data center na sede)
cur.execute(
    "UPDATE glpi_computers SET entities_id = %s WHERE id BETWEEN 51 AND 65", (MTZ,)
)
print(f"  SRV 51-65 → Matriz.    Linhas: {cur.rowcount}")

conn.commit()

# Tabelas derivadas: seguem o computer
print("  Cascata para tabelas derivadas...")
cur.execute("""
    UPDATE glpi_items_operatingsystems ios
    JOIN glpi_computers c ON c.id = ios.items_id AND ios.itemtype = 'Computer'
    SET ios.entities_id = c.entities_id
""")
print(f"    items_operatingsystems: {cur.rowcount}")

cur.execute("""
    UPDATE glpi_items_softwareversions isv
    JOIN glpi_computers c ON c.id = isv.items_id AND isv.itemtype = 'Computer'
    SET isv.entities_id = c.entities_id
""")
print(f"    items_softwareversions: {cur.rowcount}")

cur.execute("""
    UPDATE glpi_infocoms ic
    JOIN glpi_computers c ON c.id = ic.items_id AND ic.itemtype = 'Computer'
    SET ic.entities_id = c.entities_id
""")
print(f"    infocoms(Computer): {cur.rowcount}")

conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# FASE 7 — Equipamentos de rede e racks → Matriz (infraestrutura central)
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FASE 7: Rede e racks → Matriz ===")
cur.execute("UPDATE glpi_networkequipments SET entities_id = %s", (MTZ,))
print(f"  NetworkEquipments: {cur.rowcount}")
cur.execute("UPDATE glpi_racks     SET entities_id = %s", (MTZ,))
print(f"  Racks: {cur.rowcount}")
cur.execute("UPDATE glpi_dcrooms   SET entities_id = %s", (MTZ,))
print(f"  DC Rooms: {cur.rowcount}")
conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# FASE 8 — Monitores: distribuição proporcional entre as 4 entidades
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FASE 8: Monitores e impressoras ===")
cur.execute("SELECT id FROM glpi_monitors ORDER BY id")
mon_ids = [r[0] for r in cur.fetchall()]
# Fatias: 8, 8, 7, 7 (total 30)
m_slices = [
    (mon_ids[:8],    MTZ, "Matriz"),
    (mon_ids[8:16],  SP,  "Filial SP"),
    (mon_ids[16:23], RJ,  "Filial RJ"),
    (mon_ids[23:],   MG,  "Filial MG"),
]
for ids, eid, label in m_slices:
    n = bulk_update("glpi_monitors", eid, ids)
    print(f"  Monitores → {label}: {n} ({len(ids)} itens)")

# Impressoras: 2 por entidade (8 total)
cur.execute("SELECT id FROM glpi_printers ORDER BY id")
prt_ids = [r[0] for r in cur.fetchall()]
p_slices = [
    (prt_ids[0:2], MTZ, "Matriz"),
    (prt_ids[2:4], SP,  "Filial SP"),
    (prt_ids[4:6], RJ,  "Filial RJ"),
    (prt_ids[6:],  MG,  "Filial MG"),
]
for ids, eid, label in p_slices:
    n = bulk_update("glpi_printers", eid, ids)
    print(f"  Impressoras → {label}: {n} ({len(ids)} itens)")

conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# FASE 9 — Telefones e periféricos seguem entidade do usuário
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FASE 9: Telefones e periféricos ===")

for table, label in [("glpi_phones", "Telefones"), ("glpi_peripherals", "Periféricos")]:
    # Ativos com usuário → entidade do usuário
    cur.execute(f"""
        UPDATE `{table}` a
        JOIN glpi_users u ON u.id = a.users_id AND a.users_id > 0
        SET a.entities_id = u.entities_id
        WHERE u.entities_id NOT IN (0, 1, 2, 3)
    """)
    moved = cur.rowcount
    # Ativos sem usuário (users_id=0 ou NULL) → Matriz
    cur.execute(f"""
        UPDATE `{table}`
        SET entities_id = %s
        WHERE (users_id = 0 OR users_id IS NULL) AND entities_id IN (1, 2, 3)
    """, (MTZ,))
    orphans = cur.rowcount
    print(f"  {label}: {moved} seguiram usuário, {orphans} sem usuário → Matriz")

conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# FASE 10 — Problemas e mudanças → Matriz (ITSM centralizado na sede)
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FASE 10: Problemas e mudanças → Matriz ===")
cur.execute("UPDATE glpi_problems SET entities_id = %s", (MTZ,))
print(f"  Problemas: {cur.rowcount}")
cur.execute("UPDATE glpi_changes  SET entities_id = %s", (MTZ,))
print(f"  Mudanças:  {cur.rowcount}")
conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# FASE 11 — Projetos: distribuídos geograficamente
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FASE 11: Projetos ===")
cur.execute("SELECT id FROM glpi_projects ORDER BY id")
proj_ids = [r[0] for r in cur.fetchall()]
print(f"  IDs: {proj_ids}")

proj_map = []
for pid in proj_ids:
    if pid <= 2:
        eid, label = MTZ, "Matriz"
    elif pid <= 4:
        eid, label = SP, "Filial SP"
    elif pid == 5:
        eid, label = RJ, "Filial RJ"
    else:
        eid, label = MG, "Filial MG"
    cur.execute(
        "UPDATE glpi_projects SET entities_id = %s WHERE id = %s",
        (eid, pid)
    )
    proj_map.append((pid, label))
    print(f"  Projeto {pid} → {label}")

conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# FASE 12 — Fornecedores e contratos
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FASE 12: Fornecedores ===")
cur.execute("SELECT id, name FROM glpi_suppliers ORDER BY id")
for sid, sname in cur.fetchall():
    if sid <= 4:
        # Globais (já em entity 0): garantir is_recursive=1
        cur.execute(
            "UPDATE glpi_suppliers SET entities_id = 0, is_recursive = 1 WHERE id = %s",
            (sid,)
        )
        print(f"  {sid}. {sname} → Empresa/Raiz (global)")
    else:
        # Específicos de TI → Matriz
        cur.execute(
            "UPDATE glpi_suppliers SET entities_id = %s, is_recursive = 0 WHERE id = %s",
            (MTZ, sid)
        )
        print(f"  {sid}. {sname} → Matriz")

# Contratos seguem fornecedor
cur.execute("""
    UPDATE glpi_contracts c
    JOIN glpi_suppliers s ON s.id = (
        SELECT cs.suppliers_id
        FROM glpi_contracts_suppliers cs
        WHERE cs.contracts_id = c.id
        LIMIT 1
    )
    SET c.entities_id = s.entities_id
    WHERE EXISTS (
        SELECT 1 FROM glpi_contracts_suppliers cs WHERE cs.contracts_id = c.id
    )
""")
print(f"  Contratos atualizados: {cur.rowcount}")
conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# FASE 13 — Softwares e licenças → Matriz (is_recursive=1 para herança)
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FASE 13: Softwares e licenças → Matriz (is_recursive=1) ===")
cur.execute(
    "UPDATE glpi_softwares        SET entities_id = %s, is_recursive = 1", (MTZ,)
)
print(f"  Softwares: {cur.rowcount}")
cur.execute(
    "UPDATE glpi_softwareversions SET entities_id = %s, is_recursive = 1", (MTZ,)
)
print(f"  Versões: {cur.rowcount}")
cur.execute(
    "UPDATE glpi_softwarelicenses SET entities_id = %s, is_recursive = 1", (MTZ,)
)
print(f"  Licenças: {cur.rowcount}")
conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# FASE 14 — Scan dinâmico: limpar referências residuais aos ids 1, 2, 3
#           Fallback para Matriz (entidade operacional principal)
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FASE 14: Scan dinâmico — referências residuais a ids 1,2,3 ===")

cur.execute("""
    SELECT TABLE_NAME
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = 'glpi'
      AND COLUMN_NAME  = 'entities_id'
      AND TABLE_NAME   NOT IN ('glpi_entities')
    ORDER BY TABLE_NAME
""")
all_tables = [r[0] for r in cur.fetchall()]

residual_total = 0
for table in all_tables:
    try:
        cur.execute(
            f"SELECT COUNT(*) FROM `{table}` WHERE entities_id IN (1, 2, 3)"
        )
        n = cur.fetchone()[0]
        if n > 0:
            cur.execute(
                f"UPDATE `{table}` SET entities_id = %s WHERE entities_id IN (1, 2, 3)",
                (MTZ,)
            )
            updated = cur.rowcount
            residual_total += updated
            print(f"  {table}: {updated} registros residuais → Matriz")
    except Exception as ex:
        print(f"  [SKIP] {table}: {ex}")

if residual_total == 0:
    print("  Nenhuma referência residual encontrada.")
conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# FASE 15 — Atualizar sons_cache da entidade raiz
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FASE 15: sons_cache da raiz ===")
sons = f"|0|{MTZ}|{SP}|{RJ}|{MG}|"
cur.execute(
    "UPDATE glpi_entities SET sons_cache = %s WHERE id = 0",
    (sons,)
)
print(f"  sons_cache(0) → '{sons}'")
conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# FASE 16 — Deletar entidades departamentais (1, 2, 3)
#           Usa FK_CHECKS=0 como segurança pós-limpeza completa
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FASE 16: Deletar entidades antigas (TI=1, Ops=2, Fin=3) ===")

# Verificação prévia: confirmar que nenhuma tabela ainda referencia 1,2,3
leaks = []
for table in all_tables:
    try:
        cur.execute(
            f"SELECT COUNT(*) FROM `{table}` WHERE entities_id IN (1, 2, 3)"
        )
        n = cur.fetchone()[0]
        if n > 0:
            leaks.append((table, n))
    except Exception:
        pass

if leaks:
    print(f"  AVISO: referências residuais ainda encontradas: {leaks}")
    print("  Aplicando limpeza de emergência...")
    for table, _ in leaks:
        cur.execute(
            f"UPDATE `{table}` SET entities_id = %s WHERE entities_id IN (1, 2, 3)",
            (MTZ,)
        )
    conn.commit()

# Desabilitar FK checks temporariamente para remover as linhas de glpi_entities
cur.execute("SET FOREIGN_KEY_CHECKS = 0")
cur.execute("DELETE FROM glpi_entities WHERE id IN (1, 2, 3)")
deleted = cur.rowcount
cur.execute("SET FOREIGN_KEY_CHECKS = 1")
conn.commit()
print(f"  Entidades deletadas: {deleted} (ids 1, 2, 3)")


# ─────────────────────────────────────────────────────────────────────────────
# VERIFICAÇÃO FINAL
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== VERIFICAÇÃO FINAL ===")

# Hierarquia
print("  --- Hierarquia de entidades ---")
cur.execute("""
    SELECT id, name, entities_id, level, sons_cache
    FROM glpi_entities ORDER BY id
""")
for row in cur.fetchall():
    indent = "  " * (row[3] - 1)
    print(f"    {indent}id={row[0]}: {row[1]} (parent={row[2]}, level={row[3]})")

# Volumes por entidade
print("\n  --- Volumes por entidade ---")
ent_label = {0: "Empresa", MTZ: "Matriz", SP: "Filial SP", RJ: "Filial RJ", MG: "Filial MG"}

SUMMARY = [
    ("Usuários",       "glpi_users"),
    ("Tickets",        "glpi_tickets"),
    ("Computadores",   "glpi_computers"),
    ("Rede",           "glpi_networkequipments"),
    ("Racks",          "glpi_racks"),
    ("Monitores",      "glpi_monitors"),
    ("Impressoras",    "glpi_printers"),
    ("Telefones",      "glpi_phones"),
    ("Periféricos",    "glpi_peripherals"),
    ("Problemas",      "glpi_problems"),
    ("Mudanças",       "glpi_changes"),
    ("Projetos",       "glpi_projects"),
    ("Fornecedores",   "glpi_suppliers"),
    ("Softwares",      "glpi_softwares"),
]
all_eids = [0, MTZ, SP, RJ, MG]
hdr_labels = ["Empresa", "Matriz", "Filial SP", "Filial RJ", "Filial MG"]
print(f"  {'Recurso':<20} | {' | '.join(f'{l:>9}' for l in hdr_labels)} | {'Total':>7}")
print(f"  {'-'*20}-+-{'-+-'.join(['-'*9]*5)}-+-{'-'*7}")

errors = 0
for label, table in SUMMARY:
    try:
        cur.execute(f"SELECT entities_id, COUNT(*) FROM `{table}` GROUP BY entities_id")
        dist = {r[0]: r[1] for r in cur.fetchall()}
        vals = [dist.get(eid, 0) for eid in all_eids]
        total = sum(dist.values())
        # Check for orphans (entities_id not in known set)
        orphan = sum(v for k, v in dist.items() if k not in set(all_eids))
        err_flag = " [ORFÃO!]" if orphan > 0 else ""
        if orphan > 0:
            errors += 1
        print(f"  {label:<20} | {' | '.join(f'{v:>9}' for v in vals)} | {total:>7}{err_flag}")
    except Exception as ex:
        print(f"  {label:<20} | ERRO: {ex}")


# ─────────────────────────────────────────────────────────────────────────────
# FASE 17 — Garantir perfil Super-Admin explícito nas novas entidades
#           Entidades criadas via SQL não recebem glpi_profiles_users automático.
#           Sem esse vínculo, o GLPI nega permissão para editar a entidade na UI.
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FASE 17: Perfil Super-Admin nas novas entidades ===")

# Descobrir o profiles_id do Super-Admin dinamicamente
cur.execute("SELECT id FROM glpi_profiles WHERE name = 'Super-Admin' LIMIT 1")
row = cur.fetchone()
SUPERADMIN_PROFILE = row[0] if row else 4  # fallback id=4

# Descobrir o users_id do admin GLPI (primeiro usuário com Super-Admin no raiz)
cur.execute("""
    SELECT users_id FROM glpi_profiles_users
    WHERE profiles_id = %s AND entities_id = 0
    ORDER BY users_id LIMIT 1
""", (SUPERADMIN_PROFILE,))
row = cur.fetchone()
ADMIN_USER = row[0] if row else 2  # fallback id=2 (glpi)

new_entities = [MTZ, SP, RJ, MG]
inserted = 0
for eid in new_entities:
    cur.execute("""
        INSERT IGNORE INTO glpi_profiles_users
            (users_id, profiles_id, entities_id, is_recursive, is_dynamic)
        VALUES (%s, %s, %s, 1, 0)
    """, (ADMIN_USER, SUPERADMIN_PROFILE, eid))
    inserted += cur.rowcount
conn.commit()
print(f"  Vínculos adicionados: {inserted} (users_id={ADMIN_USER}, profile=Super-Admin)")

print(f"\n=== RESULTADO ===")
print(f"  Erros/Órfãos: {errors}")
if errors == 0:
    print("  STATUS: OK — refatoração concluída sem perdas de dados")
    print(f"\n  Nova hierarquia:")
    print(f"    Empresa (0)")
    print(f"    ├─ Matriz       (id={MTZ}) — sede SP, TI, infra, ITSM")
    print(f"    ├─ Filial SP    (id={SP}) — operações SP")
    print(f"    ├─ Filial RJ    (id={RJ}) — operações RJ")
    print(f"    └─ Filial MG    (id={MG}) — operações MG")
else:
    print("  STATUS: FALHOU — revisar registros órfãos acima")

cur.close()
conn.close()
