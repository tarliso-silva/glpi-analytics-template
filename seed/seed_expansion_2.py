"""
seed_expansion_2.py — Fornecedores, Contratos, Contatos e Informações Financeiras
Insere:
  - 2 tipos de fornecedor (Hardware, Software/Serviços)
  - 2 tipos de contrato (Manutenção, Suporte Gerenciado)
  - 8 fornecedores (reais/fictícios mas plausíveis)
  - 10 contatos de fornecedores
  - 8 contratos (manutenção + suporte)
  - Vínculos contrato ↔ fornecedor e contrato ↔ ativo
  - Informações financeiras (glpi_infocoms) para computadores e network equipments
NÃO altera dados existentes.
random.seed(42) para reprodutibilidade.
"""
import mysql.connector, random
from datetime import date, timedelta

random.seed(42)

DB = dict(host="localhost", port=3306, database="glpi", user="glpi", password="glpi")
conn = mysql.connector.connect(**DB)
conn.autocommit = False
cur = conn.cursor()

def count(t):
    cur.execute(f"SELECT COUNT(*) FROM `{t}`")
    return cur.fetchone()[0]

print("=" * 68)
print("  EXPANSION 2 — Fornecedores, Contratos e Infocoms")
print("=" * 68)

if count("glpi_suppliers") > 0:
    print("  AVISO: glpi_suppliers já tem dados. Abortando.")
    conn.close()
    exit(0)

# Carregar dados existentes
cur.execute("SELECT id FROM glpi_computers ORDER BY id")
ALL_COMPUTERS = [r[0] for r in cur.fetchall()]
cur.execute("SELECT id FROM glpi_computers WHERE name LIKE 'SRV-%'")
SRV_IDS = set(r[0] for r in cur.fetchall())
cur.execute("SELECT id FROM glpi_networkequipments ORDER BY id")
NETWORK_IDS = [r[0] for r in cur.fetchall()]

today = date.today()

# ─── 1. TIPOS DE FORNECEDOR ───────────────────────────────────────────────────
print("\n[1/6] Tipos de fornecedor")
sup_types = [
    ("Hardware",                 "Fabricantes e revendedores de equipamentos"),
    ("Software e Servicos",      "Licencas, SaaS e servicos gerenciados"),
    ("Telecomunicacoes",         "Conectividade, links e telefonia"),
    ("Manutencao e Suporte",     "Assistencia tecnica e helpdesk externo"),
]
SUP_TYPE_IDS = {}
for name, comment in sup_types:
    cur.execute(
        "INSERT INTO glpi_suppliertypes (name, comment, date_mod, date_creation) "
        "VALUES (%s, %s, NOW(), NOW())", (name, comment)
    )
    SUP_TYPE_IDS[name] = cur.lastrowid
conn.commit()
print(f"  {len(SUP_TYPE_IDS)} tipos de fornecedor")

# ─── 2. TIPOS DE CONTRATO ──────────────────────────────────────────────────────
print("\n[2/6] Tipos de contrato")
contract_types = [
    ("Manutencao Preventiva e Corretiva",   "Hardware on-site"),
    ("Suporte Gerenciado de TI",             "MSP - Managed Services"),
    ("Licenca e Subscription",               "Software anual ou perpetuo"),
    ("Conectividade e Telecomunicacoes",     "Links, MPLS, Internet"),
]
CTR_TYPE_IDS = {}
for name, comment in contract_types:
    cur.execute(
        "INSERT INTO glpi_contracttypes (name, comment, date_mod, date_creation) "
        "VALUES (%s, %s, NOW(), NOW())", (name, comment)
    )
    CTR_TYPE_IDS[name] = cur.lastrowid
conn.commit()
print(f"  {len(CTR_TYPE_IDS)} tipos de contrato")

# ─── 3. FORNECEDORES ──────────────────────────────────────────────────────────
print("\n[3/6] Fornecedores")

SUPPLIERS = [
    {
        "name": "TechCorp Solucoes em TI Ltda",
        "type": "Hardware",
        "reg": "12.345.678/0001-90",
        "addr": "Av. Paulista, 1000",
        "postcode": "01310-100",
        "town": "Sao Paulo",
        "state": "SP",
        "website": "https://www.techcorp.com.br",
        "phone": "+55 11 3100-0001",
        "email": "comercial@techcorp.com.br",
    },
    {
        "name": "DataSync Sistemas de Informacao",
        "type": "Software e Servicos",
        "reg": "23.456.789/0001-01",
        "addr": "Rua das Flores, 200",
        "postcode": "04546-050",
        "town": "Sao Paulo",
        "state": "SP",
        "website": "https://www.datasync.com.br",
        "phone": "+55 11 3200-0002",
        "email": "suporte@datasync.com.br",
    },
    {
        "name": "NetConnect Telecomunicacoes",
        "type": "Telecomunicacoes",
        "reg": "34.567.890/0001-12",
        "addr": "Av. Berrini, 1500",
        "postcode": "04571-020",
        "town": "Sao Paulo",
        "state": "SP",
        "website": "https://www.netconnect.com.br",
        "phone": "+55 11 3300-0003",
        "email": "noc@netconnect.com.br",
    },
    {
        "name": "ProServ Manutencao e Suporte",
        "type": "Manutencao e Suporte",
        "reg": "45.678.901/0001-23",
        "addr": "Rua dos Andradas, 300",
        "postcode": "90020-000",
        "town": "Porto Alegre",
        "state": "RS",
        "website": "https://www.proserv.com.br",
        "phone": "+55 51 3400-0004",
        "email": "atendimento@proserv.com.br",
    },
    {
        "name": "CloudAxis Servicos de Nuvem",
        "type": "Software e Servicos",
        "reg": "56.789.012/0001-34",
        "addr": "Av. Raja Gabaglia, 400",
        "postcode": "30350-540",
        "town": "Belo Horizonte",
        "state": "MG",
        "website": "https://www.cloudaxis.com.br",
        "phone": "+55 31 3500-0005",
        "email": "sac@cloudaxis.com.br",
    },
    {
        "name": "SecureNet Seguranca Digital",
        "type": "Software e Servicos",
        "reg": "67.890.123/0001-45",
        "addr": "SCS Quadra 2, Bl. C, 10",
        "postcode": "70300-902",
        "town": "Brasilia",
        "state": "DF",
        "website": "https://www.securenet.com.br",
        "phone": "+55 61 3600-0006",
        "email": "vendas@securenet.com.br",
    },
    {
        "name": "OmniPrint Impressao Corporativa",
        "type": "Hardware",
        "reg": "78.901.234/0001-56",
        "addr": "Rua do Comercio, 50",
        "postcode": "80010-030",
        "town": "Curitiba",
        "state": "PR",
        "website": "https://www.omniprint.com.br",
        "phone": "+55 41 3700-0007",
        "email": "contato@omniprint.com.br",
    },
    {
        "name": "InfraBase Datacenter Solutions",
        "type": "Manutencao e Suporte",
        "reg": "89.012.345/0001-67",
        "addr": "Av. das Americas, 500",
        "postcode": "22640-100",
        "town": "Rio de Janeiro",
        "state": "RJ",
        "website": "https://www.infrabase.com.br",
        "phone": "+55 21 3800-0008",
        "email": "infraestrutura@infrabase.com.br",
    },
]

SUP_IDS = {}
for s in SUPPLIERS:
    type_id = SUP_TYPE_IDS.get(s["type"], 1)
    cur.execute("""
        INSERT INTO glpi_suppliers
          (entities_id, is_recursive, name, suppliertypes_id, registration_number,
           address, postcode, town, state, website, phonenumber, email,
           is_deleted, is_active, date_mod, date_creation)
        VALUES (0, 1, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0, 1, NOW(), NOW())
    """, (s["name"], type_id, s["reg"], s["addr"], s["postcode"],
          s["town"], s["state"], s["website"], s["phone"], s["email"]))
    SUP_IDS[s["name"]] = cur.lastrowid

conn.commit()
print(f"  {len(SUP_IDS)} fornecedores")

# ─── 4. CONTATOS ─────────────────────────────────────────────────────────────
print("\n[4/6] Contatos de fornecedores")

CONTACTS = [
    ("Lima",    "Carlos",   "+55 11 99001-1001", "carlos.lima@techcorp.com.br",     "TechCorp Solucoes em TI Ltda"),
    ("Ferreira","Ana",      "+55 11 99002-1002", "ana.ferreira@datasync.com.br",    "DataSync Sistemas de Informacao"),
    ("Costa",   "Roberto",  "+55 11 99003-1003", "roberto.costa@netconnect.com.br", "NetConnect Telecomunicacoes"),
    ("Mendes",  "Patricia", "+55 51 99004-1004", "patricia.mendes@proserv.com.br",  "ProServ Manutencao e Suporte"),
    ("Alves",   "Marcelo",  "+55 31 99005-1005", "marcelo.alves@cloudaxis.com.br",  "CloudAxis Servicos de Nuvem"),
    ("Nunes",   "Juliana",  "+55 61 99006-1006", "juliana.nunes@securenet.com.br",  "SecureNet Seguranca Digital"),
    ("Ramos",   "Thiago",   "+55 41 99007-1007", "thiago.ramos@omniprint.com.br",   "OmniPrint Impressao Corporativa"),
    ("Braga",   "Fernanda", "+55 21 99008-1008", "fernanda.braga@infrabase.com.br", "InfraBase Datacenter Solutions"),
    # Contato técnico secundário para fornecedores críticos
    ("Santos",  "Lucas",    "+55 11 99009-1009", "lucas.santos@techcorp.com.br",    "TechCorp Solucoes em TI Ltda"),
    ("Oliveira","Mariana",  "+55 11 99010-1010", "mariana.oliveira@datasync.com.br","DataSync Sistemas de Informacao"),
]

CONTACT_IDS = []
for last, first, phone, email, sup_name in CONTACTS:
    cur.execute("""
        INSERT INTO glpi_contacts
          (entities_id, is_recursive, name, firstname, phone, mobile,
           email, is_deleted, date_mod, date_creation)
        VALUES (0, 1, %s, %s, %s, %s, %s, 0, NOW(), NOW())
    """, (last, first, phone, phone, email))
    cid = cur.lastrowid
    CONTACT_IDS.append(cid)
    # Vincular ao fornecedor
    sup_id = SUP_IDS.get(sup_name)
    if sup_id:
        cur.execute(
            "INSERT INTO glpi_contacts_suppliers (suppliers_id, contacts_id) VALUES (%s, %s)",
            (sup_id, cid)
        )

conn.commit()
print(f"  {len(CONTACT_IDS)} contatos vinculados a fornecedores")

# ─── 5. CONTRATOS ─────────────────────────────────────────────────────────────
print("\n[5/6] Contratos")

# Data base: 01/01/2023
base_date = date(2023, 1, 1)

CONTRACTS = [
    {
        "name": "CTR-2023-001 - Manutencao Hardware Workstations",
        "num": "CTR-2023-001",
        "type": "Manutencao Preventiva e Corretiva",
        "supplier": "TechCorp Solucoes em TI Ltda",
        "begin": date(2023, 1, 1),
        "months": 24,
        "comment": "Manutencao preventiva e corretiva de 50 workstations.",
        "items": "Computer",  # vincula a computadores WS
    },
    {
        "name": "CTR-2023-002 - Suporte Gerenciado de Servidores",
        "num": "CTR-2023-002",
        "type": "Suporte Gerenciado de TI",
        "supplier": "InfraBase Datacenter Solutions",
        "begin": date(2023, 1, 1),
        "months": 36,
        "comment": "SLA 4h para servidores em producao.",
        "items": "Server",   # vincula a computadores SRV
    },
    {
        "name": "CTR-2023-003 - Link Internet e MPLS",
        "num": "CTR-2023-003",
        "type": "Conectividade e Telecomunicacoes",
        "supplier": "NetConnect Telecomunicacoes",
        "begin": date(2023, 3, 1),
        "months": 24,
        "comment": "Link dedicado 1Gbps + MPLS entre unidades.",
        "items": None,
    },
    {
        "name": "CTR-2023-004 - Licencas Microsoft 365",
        "num": "CTR-2023-004",
        "type": "Licenca e Subscription",
        "supplier": "DataSync Sistemas de Informacao",
        "begin": date(2023, 7, 1),
        "months": 12,
        "comment": "62 licencas Microsoft 365 E3 via CSP.",
        "items": None,
    },
    {
        "name": "CTR-2024-005 - Manutencao Network Equipments",
        "num": "CTR-2024-005",
        "type": "Manutencao Preventiva e Corretiva",
        "supplier": "ProServ Manutencao e Suporte",
        "begin": date(2024, 1, 1),
        "months": 12,
        "comment": "Manutencao de switches, roteadores e APs.",
        "items": "NetworkEquipment",
    },
    {
        "name": "CTR-2024-006 - CrowdStrike Falcon Subscription",
        "num": "CTR-2024-006",
        "type": "Licenca e Subscription",
        "supplier": "SecureNet Seguranca Digital",
        "begin": date(2024, 2, 1),
        "months": 12,
        "comment": "65 endpoints — renovacao anual.",
        "items": None,
    },
    {
        "name": "CTR-2024-007 - Veeam Backup & Replication",
        "num": "CTR-2024-007",
        "type": "Licenca e Subscription",
        "supplier": "CloudAxis Servicos de Nuvem",
        "begin": date(2024, 4, 1),
        "months": 12,
        "comment": "Backup de servidores e VMs — 15 workloads.",
        "items": None,
    },
    {
        "name": "CTR-2024-008 - Outsourcing de Impressao",
        "num": "CTR-2024-008",
        "type": "Suporte Gerenciado de TI",
        "supplier": "OmniPrint Impressao Corporativa",
        "begin": date(2024, 5, 1),
        "months": 24,
        "comment": "Outsourcing de 8 impressoras — custo por pagina.",
        "items": "Printer",
    },
]

CTR_IDS = {}
for c in CONTRACTS:
    type_id = CTR_TYPE_IDS.get(c["type"], 1)
    end_date = c["begin"].replace(month=c["begin"].month) + timedelta(days=30 * c["months"])
    cur.execute("""
        INSERT INTO glpi_contracts
          (entities_id, is_recursive, name, num, contracttypes_id,
           begin_date, duration, comment,
           is_deleted, is_template, date_mod, date_creation)
        VALUES (0, 1, %s, %s, %s, %s, %s, %s, 0, 0, NOW(), NOW())
    """, (c["name"], c["num"], type_id,
          str(c["begin"]), c["months"], c["comment"]))
    ctr_id = cur.lastrowid
    CTR_IDS[c["num"]] = ctr_id

    # Vincular ao fornecedor
    sup_id = SUP_IDS.get(c["supplier"])
    if sup_id:
        cur.execute(
            "INSERT INTO glpi_contracts_suppliers (suppliers_id, contracts_id) "
            "VALUES (%s, %s)", (sup_id, ctr_id)
        )

    # Vincular a ativos
    if c["items"] == "Computer":
        for comp_id in random.sample(WS_IDS := [x for x in ALL_COMPUTERS if x not in SRV_IDS], min(20, len([x for x in ALL_COMPUTERS if x not in SRV_IDS]))):
            cur.execute(
                "INSERT INTO glpi_contracts_items (contracts_id, items_id, itemtype) "
                "VALUES (%s, %s, 'Computer')", (ctr_id, comp_id)
            )
    elif c["items"] == "Server":
        for srv_id in SRV_IDS:
            cur.execute(
                "INSERT INTO glpi_contracts_items (contracts_id, items_id, itemtype) "
                "VALUES (%s, %s, 'Computer')", (ctr_id, srv_id)
            )
    elif c["items"] == "NetworkEquipment":
        for neq_id in NETWORK_IDS:
            cur.execute(
                "INSERT INTO glpi_contracts_items (contracts_id, items_id, itemtype) "
                "VALUES (%s, %s, 'NetworkEquipment')", (ctr_id, neq_id)
            )
    elif c["items"] == "Printer":
        cur.execute("SELECT id FROM glpi_printers ORDER BY id")
        printers = [r[0] for r in cur.fetchall()]
        for pid in printers:
            cur.execute(
                "INSERT INTO glpi_contracts_items (contracts_id, items_id, itemtype) "
                "VALUES (%s, %s, 'Printer')", (ctr_id, pid)
            )

conn.commit()
print(f"  {len(CTR_IDS)} contratos")
cur.execute("SELECT COUNT(*) FROM glpi_contracts_items")
print(f"  {cur.fetchone()[0]} vínculos contrato ↔ ativo")

# ─── 6. INFORMAÇÕES FINANCEIRAS (INFOCOMS) ─────────────────────────────────────
print("\n[6/6] Informações financeiras (infocoms)")

if count("glpi_infocoms") > 0:
    print("  infocoms já preenchido, pulando.")
else:
    # Preços de referência por modelo (aproximado)
    PRICE_WS = (3_500, 8_000)    # workstation
    PRICE_SRV = (15_000, 45_000) # servidor
    PRICE_NET = (2_000, 12_000)  # network equipment

    # Datas de compra entre 2019 e 2023
    purchase_start = date(2019, 1, 1)
    purchase_end   = date(2023, 12, 31)
    date_range_days = (purchase_end - purchase_start).days

    infocoms = []

    # Computadores
    for comp_id in ALL_COMPUTERS:
        is_srv = comp_id in SRV_IDS
        buy_delta = timedelta(days=random.randint(0, date_range_days))
        buy_date  = purchase_start + buy_delta
        warranty  = 36 if is_srv else 24  # meses
        value     = round(random.uniform(*(PRICE_SRV if is_srv else PRICE_WS)), 2)
        sup_id    = SUP_IDS.get("TechCorp Solucoes em TI Ltda")
        infocoms.append(("Computer", comp_id, buy_date, warranty, value, sup_id))

    # Network Equipments
    for neq_id in NETWORK_IDS:
        buy_delta = timedelta(days=random.randint(0, date_range_days))
        buy_date  = purchase_start + buy_delta
        value     = round(random.uniform(*PRICE_NET), 2)
        sup_id    = SUP_IDS.get("TechCorp Solucoes em TI Ltda")
        infocoms.append(("NetworkEquipment", neq_id, buy_date, 36, value, sup_id))

    for itemtype, item_id, buy_date, warranty_dur, value, sup_id in infocoms:
        cur.execute("""
            INSERT INTO glpi_infocoms
              (itemtype, items_id, entities_id, is_recursive,
               buy_date, warranty_duration, warranty_info,
               suppliers_id, value, date_mod, date_creation)
            VALUES (%s, %s, 0, 1, %s, %s, '12 meses on-site', %s, %s, NOW(), NOW())
        """, (itemtype, item_id, str(buy_date), warranty_dur, sup_id, value))

    conn.commit()
    print(f"  {len(infocoms)} infocoms (computadores + network equipments)")

# ─── RESUMO ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 68)
print("  RESUMO — EXPANSION 2")
print("=" * 68)
for tbl in [
    "glpi_suppliertypes", "glpi_suppliers", "glpi_contacts",
    "glpi_contacts_suppliers", "glpi_contracttypes", "glpi_contracts",
    "glpi_contracts_suppliers", "glpi_contracts_items", "glpi_infocoms"
]:
    cur.execute(f"SELECT COUNT(*) FROM `{tbl}`")
    print(f"  {tbl:<40} {cur.fetchone()[0]:>6}")

conn.close()
print("\nExpansion 2 concluída!")
