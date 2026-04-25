"""
seed_racks.py — Cria Rack Types, DC Rooms, Racks e popula com servidores e
equipamentos de rede para análises de Data Center no GLPI 10.x.

Layout:
  RACK-DC-01 (São Paulo HQ): SRV-001..005  + SW-CORE-01/02, RT-BORDA-01, FW-01
  RACK-DC-02 (São Paulo HQ): SRV-006..010  + SW-ACC-01/02/03, FW-02
  RACK-DC-03 (São Paulo HQ): SRV-011..015  + AP-SP-01/02, SW-RJ-01, AP-RJ-01

Idempotente: aborta se já existirem racks no banco.
"""

import mysql.connector
from datetime import datetime, timezone

# ─── conexão ───────────────────────────────────────────────────────────────────
conn = mysql.connector.connect(
    host="localhost", port=3306, database="glpi",
    user="glpi", password="glpi"
)
cur = conn.cursor()
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

print("=== seed_racks.py ===")

# ─── idempotência ──────────────────────────────────────────────────────────────
cur.execute("SELECT COUNT(*) FROM glpi_racks")
if cur.fetchone()[0] > 0:
    print("Racks já existem. Nada a fazer.")
    cur.close(); conn.close(); exit()

# ─── detectar colunas disponíveis ─────────────────────────────────────────────
def get_cols(table):
    cur.execute(f"SHOW COLUMNS FROM {table}")
    return {r[0] for r in cur.fetchall()}

rack_cols   = get_cols("glpi_racks")
rtype_cols  = get_cols("glpi_racktypes")
item_r_cols = get_cols("glpi_items_racks")
room_cols   = get_cols("glpi_dcrooms")

print(f"glpi_racks cols:       {sorted(rack_cols)}")
print(f"glpi_racktypes cols:   {sorted(rtype_cols)}")
print(f"glpi_items_racks cols: {sorted(item_r_cols)}")
print(f"glpi_dcrooms cols:     {sorted(room_cols)}")

# ─── helpers ──────────────────────────────────────────────────────────────────
def insert(table, row_dict):
    """Insere apenas colunas existentes na tabela; retorna lastrowid."""
    cols_avail = get_cols(table)
    filtered   = {k: v for k, v in row_dict.items() if k in cols_avail}
    cols  = ", ".join(filtered.keys())
    phs   = ", ".join(["%s"] * len(filtered))
    cur.execute(f"INSERT INTO {table} ({cols}) VALUES ({phs})", list(filtered.values()))
    return cur.lastrowid

# ─── 1. Rack Types ─────────────────────────────────────────────────────────────
print("\n--- Rack Types ---")
rack_type_ids = []
for name in ["Armário 42U 19\"", "Open Frame 42U"]:
    row = {
        "entities_id": 0, "is_recursive": 1,
        "name": name, "comment": "",
        "date_creation": NOW, "date_mod": NOW,
    }
    rid = insert("glpi_racktypes", row)
    rack_type_ids.append(rid)
    print(f"  RackType id={rid}: {name}")

conn.commit()
rack_type_armario    = rack_type_ids[0]   # Armário 42U 19"
rack_type_openframe  = rack_type_ids[1]   # Open Frame 42U

# ─── 2. DC Room (sala do data center) ─────────────────────────────────────────
print("\n--- DC Room ---")
dcroom_row = {
    "name": "Sala DC Principal",
    "entities_id": 0, "is_recursive": 0,
    "locations_id": 1,          # São Paulo HQ
    "vis_cols": 10, "vis_rows": 10,
    "vis_cell_width": 100, "vis_cell_height": 100,
    "datacenters_id": 0,
    "is_deleted": 0,
    "date_creation": NOW, "date_mod": NOW,
}
dcroom_id = insert("glpi_dcrooms", dcroom_row)
print(f"  DC Room id={dcroom_id}: Sala DC Principal")
conn.commit()

# ─── 3. Racks ─────────────────────────────────────────────────────────────────
print("\n--- Racks ---")

RACKS_DEF = [
    {
        "name": "RACK-DC-01",
        "comment": "Rack principal — core networking + servidores 01-05",
        "serial": "RK-2024-001",
        "racktypes_id": rack_type_armario,
        "position_x": 1,           # coluna na sala
    },
    {
        "name": "RACK-DC-02",
        "comment": "Rack distribuição — access switches + servidores 06-10",
        "serial": "RK-2024-002",
        "racktypes_id": rack_type_armario,
        "position_x": 2,
    },
    {
        "name": "RACK-DC-03",
        "comment": "Rack periférico — APs, regional + servidores 11-15",
        "serial": "RK-2024-003",
        "racktypes_id": rack_type_openframe,
        "position_x": 3,
    },
]

rack_ids = []
for rdef in RACKS_DEF:
    row = {
        "name": rdef["name"],
        "comment": rdef["comment"],
        "entities_id": 0,          # entity 0 agora; seed_multi_entity.py move para TI
        "is_recursive": 0,
        "locations_id": 1,         # São Paulo HQ
        "serial": rdef["serial"],
        "otherserial": "",
        "racktypes_id": rdef["racktypes_id"],
        "manufacturers_id": 0,
        "rackmodels_id": 0,
        "states_id": 0,
        "users_id": 0,
        "users_id_tech": 0,
        "width": 600,              # mm
        "height": 1800,            # mm (42U ≈ 1866mm)
        "depth": 1000,             # mm
        "number_units": 42,
        "is_template": 0,
        "template_name": "",
        "is_deleted": 0,
        "dcrooms_id": dcroom_id,
        "room_orientation": 0,
        "bgcolor": "#fec95c",
        "max_power": 10000,        # watts
        "mesured_power": 0,
        "max_weight": 1500,        # kg
        "date_creation": NOW,
        "date_mod": NOW,
    }
    rack_id = insert("glpi_racks", row)
    rack_ids.append(rack_id)
    print(f"  Rack id={rack_id}: {rdef['name']}")

conn.commit()
rack01_id, rack02_id, rack03_id = rack_ids

# ─── 4. Vincular itens aos racks ──────────────────────────────────────────────
print("\n--- Items in Racks ---")
# IDs confirmados pelo audit:
#   Servidores (SRV-001..015): IDs 51-65
#   Network (por nome):
#     SW-CORE-01=1, SW-CORE-02=2, SW-ACC-01=3, SW-ACC-02=4, SW-ACC-03=5
#     RT-BORDA-01=6, FW-01=7, FW-02=8, AP-SP-01=9, AP-SP-02=10
#     SW-RJ-01=11, AP-RJ-01=12

def place_in_rack(racks_id, itemtype, items_id, u_position):
    """Insere item no rack na posição U indicada (1-based)."""
    row = {
        "racks_id": racks_id,
        "itemtype": itemtype,
        "items_id": items_id,
        "position": u_position,
        "orientation": 0,     # frente
        "bgcolor": "#69d1f7" if itemtype == "Computer" else "#b2e0b2",
        "hpos": 0,            # largura total
        "is_reserved": 0,
    }
    # Filtra apenas colunas existentes
    cols_avail = item_r_cols
    filtered   = {k: v for k, v in row.items() if k in cols_avail}
    cols  = ", ".join(filtered.keys())
    phs   = ", ".join(["%s"] * len(filtered))
    cur.execute(
        f"INSERT INTO glpi_items_racks ({cols}) VALUES ({phs})",
        list(filtered.values())
    )

total_items = 0

# ── RACK-DC-01 ────────────────────────────────────────────────────────────────
# Equipamentos de rede: posições U38-U41 (topo, descendente)
rack01_net = [
    (1,  "SW-CORE-01"),
    (2,  "SW-CORE-02"),
    (6,  "RT-BORDA-01"),
    (7,  "FW-01"),
]
for u_offset, (net_id, net_name) in enumerate(rack01_net):
    place_in_rack(rack01_id, "NetworkEquipment", net_id, 38 + u_offset)
    print(f"  RACK-DC-01 U{38+u_offset}: NetworkEquipment id={net_id} ({net_name})")
    total_items += 1

# Servidores: SRV-001..005 → IDs 51-55, a partir de U2 (cada um ocupa 2U)
for i, srv_id in enumerate(range(51, 56)):
    u = 2 + i * 2
    place_in_rack(rack01_id, "Computer", srv_id, u)
    print(f"  RACK-DC-01 U{u}: Computer id={srv_id} (SRV-{i+1:03d})")
    total_items += 1

# ── RACK-DC-02 ────────────────────────────────────────────────────────────────
rack02_net = [
    (3,  "SW-ACC-01"),
    (4,  "SW-ACC-02"),
    (5,  "SW-ACC-03"),
    (8,  "FW-02"),
]
for u_offset, (net_id, net_name) in enumerate(rack02_net):
    place_in_rack(rack02_id, "NetworkEquipment", net_id, 38 + u_offset)
    print(f"  RACK-DC-02 U{38+u_offset}: NetworkEquipment id={net_id} ({net_name})")
    total_items += 1

# Servidores: SRV-006..010 → IDs 56-60
for i, srv_id in enumerate(range(56, 61)):
    u = 2 + i * 2
    place_in_rack(rack02_id, "Computer", srv_id, u)
    print(f"  RACK-DC-02 U{u}: Computer id={srv_id} (SRV-{i+6:03d})")
    total_items += 1

# ── RACK-DC-03 ────────────────────────────────────────────────────────────────
rack03_net = [
    (9,  "AP-SP-01"),
    (10, "AP-SP-02"),
    (11, "SW-RJ-01"),
    (12, "AP-RJ-01"),
]
for u_offset, (net_id, net_name) in enumerate(rack03_net):
    place_in_rack(rack03_id, "NetworkEquipment", net_id, 38 + u_offset)
    print(f"  RACK-DC-03 U{38+u_offset}: NetworkEquipment id={net_id} ({net_name})")
    total_items += 1

# Servidores: SRV-011..015 → IDs 61-65
for i, srv_id in enumerate(range(61, 66)):
    u = 2 + i * 2
    place_in_rack(rack03_id, "Computer", srv_id, u)
    print(f"  RACK-DC-03 U{u}: Computer id={srv_id} (SRV-{i+11:03d})")
    total_items += 1

conn.commit()

# ─── Resumo ────────────────────────────────────────────────────────────────────
print(f"\n=== CONCLUÍDO ===")
print(f"  Rack Types criados : 2")
print(f"  DC Rooms criados   : 1 (id={dcroom_id})")
print(f"  Racks criados      : 3 (ids {rack01_id}, {rack02_id}, {rack03_id})")
print(f"  Items em racks     : {total_items} ({total_items-12} servidores + 12 net)")
print(f"  RACK-DC-01 (id={rack01_id}): SRV-001..005, SW-CORE-01/02, RT-BORDA, FW-01")
print(f"  RACK-DC-02 (id={rack02_id}): SRV-006..010, SW-ACC-01/02/03, FW-02")
print(f"  RACK-DC-03 (id={rack03_id}): SRV-011..015, AP-SP-01/02, SW-RJ-01, AP-RJ-01")

cur.close()
conn.close()
