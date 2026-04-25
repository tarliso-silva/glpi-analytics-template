"""
seed_expansion_1.py — Software, Licenças e Sistemas Operacionais
Expande os dados GLPI com:
  - Softwares corporativos reais (por categoria)
  - Versões de software
  - Tipos de licença (OEM, Subscription, Volume, Open Source, Freeware)
  - Licenças por software (quantity, expiry, supplier ref)
  - Instalações em computadores (glpi_items_softwareversions)
  - Sistemas Operacionais em computadores
NÃO altera dados existentes.
random.seed(42) para reprodutibilidade.
"""
import mysql.connector, random, uuid
from datetime import datetime, timedelta, date

random.seed(42)

DB = dict(host="localhost", port=3306, database="glpi", user="glpi", password="glpi")
conn = mysql.connector.connect(**DB)
conn.autocommit = False
cur = conn.cursor()

# ─── Helpers ──────────────────────────────────────────────────────────────────
def count(t):
    cur.execute(f"SELECT COUNT(*) FROM `{t}`")
    return cur.fetchone()[0]

def table_exists(t):
    cur.execute(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema='glpi' AND table_name=%s", (t,)
    )
    return cur.fetchone()[0] > 0

print("=" * 68)
print("  EXPANSION 1 — Software, Licenças e Sistemas Operacionais")
print("=" * 68)

# Verificar se já existem dados (não duplicar)
if count("glpi_softwares") > 0:
    print("  AVISO: glpi_softwares já tem dados. Abortando para não duplicar.")
    conn.close()
    exit(0)

# ─── Carregar dados existentes ────────────────────────────────────────────────
cur.execute("SELECT id FROM glpi_computers ORDER BY id")
ALL_COMPUTERS = [r[0] for r in cur.fetchall()]
cur.execute("SELECT id FROM glpi_computers WHERE name LIKE 'SRV-%'")
SRV_IDS = [r[0] for r in cur.fetchall()]
WS_IDS = [c for c in ALL_COMPUTERS if c not in SRV_IDS]

cur.execute("SELECT id FROM glpi_manufacturers")
MFR_IDS = [r[0] for r in cur.fetchall()]

cur.execute("SELECT id, name FROM glpi_manufacturers")
MFR_BY_NAME = {n: i for i, n in cur.fetchall()}

cur.execute("SELECT id FROM glpi_states LIMIT 1")
row = cur.fetchone()
STATE_ACTIVE = row[0] if row else 1

print(f"  Computadores: {len(ALL_COMPUTERS)} ({len(SRV_IDS)} servidores, {len(WS_IDS)} workstations)")

# ─── 1. TIPOS DE LICENÇA ──────────────────────────────────────────────────────
print("\n[1/6] Tipos de licença")

# Verificar o que já existe
cur.execute("SELECT id, name FROM glpi_softwarelicensetypes")
existing_lictypes = {n.lower(): i for i, n in cur.fetchall()}

LICENSE_TYPES = [
    "OEM",
    "Subscription - Anual",
    "Volume - Enterprise Agreement",
    "Open Source",
    "Freeware",
    "Perpetua - Corporativa",
    "SaaS - Por Usuario",
    "Education / NFR",
]
LIC_TYPE_IDS = {}
for lt in LICENSE_TYPES:
    if lt.lower() not in existing_lictypes:
        cur.execute(
            "INSERT INTO glpi_softwarelicensetypes "
            "(name, date_mod, date_creation) VALUES (%s, NOW(), NOW())",
            (lt,)
        )
        LIC_TYPE_IDS[lt] = cur.lastrowid
    else:
        LIC_TYPE_IDS[lt] = existing_lictypes[lt.lower()]

conn.commit()
print(f"  {len(LIC_TYPE_IDS)} tipos de licença")

# ─── 2. SISTEMAS OPERACIONAIS ─────────────────────────────────────────────────
print("\n[2/6] Sistemas Operacionais")

OS_DEF = [
    "Windows 10 Pro",
    "Windows 11 Pro",
    "Windows Server 2019 Standard",
    "Windows Server 2022 Standard",
    "Ubuntu Server 22.04 LTS",
    "Red Hat Enterprise Linux 9",
    "Debian 12 (Bookworm)",
]
OS_IDS = {}
for osname in OS_DEF:
    cur.execute("SELECT id FROM glpi_operatingsystems WHERE name=%s", (osname,))
    row = cur.fetchone()
    if row:
        OS_IDS[osname] = row[0]
    else:
        cur.execute(
            "INSERT INTO glpi_operatingsystems (name, date_mod, date_creation) VALUES (%s, NOW(), NOW())",
            (osname,)
        )
        OS_IDS[osname] = cur.lastrowid

conn.commit()

# Versões de SO (para items_operatingsystems)
OS_VER_DEF = [
    (OS_IDS["Windows 10 Pro"],                  "22H2 (Build 19045)"),
    (OS_IDS["Windows 11 Pro"],                  "23H2 (Build 22631)"),
    (OS_IDS["Windows Server 2019 Standard"],    "1809 (Build 17763)"),
    (OS_IDS["Windows Server 2022 Standard"],    "21H2 (Build 20348)"),
    (OS_IDS["Ubuntu Server 22.04 LTS"],         "22.04.3"),
    (OS_IDS["Red Hat Enterprise Linux 9"],      "9.3"),
    (OS_IDS["Debian 12 (Bookworm)"],            "12.4"),
]
OS_VER_IDS = {}
for os_id, ver_name in OS_VER_DEF:
    cur.execute(
        "SELECT id FROM glpi_operatingsystemversions WHERE name=%s", (ver_name,)
    )
    row = cur.fetchone()
    if row:
        OS_VER_IDS[(os_id, ver_name)] = row[0]
    else:
        cur.execute(
            "INSERT INTO glpi_operatingsystemversions (name, date_mod, date_creation) "
            "VALUES (%s, NOW(), NOW())", (ver_name,)
        )
        OS_VER_IDS[(os_id, ver_name)] = cur.lastrowid

conn.commit()

# Atribuir SO a cada computador (1 SO por máquina)
os_records = []
for comp_id in ALL_COMPUTERS:
    # Servidores usam Server 2019/2022 ou Linux, workstations usam Win10/11
    if comp_id in SRV_IDS:
        os_opts = [
            (OS_IDS["Windows Server 2022 Standard"], "21H2 (Build 20348)"),
            (OS_IDS["Windows Server 2019 Standard"], "1809 (Build 17763)"),
            (OS_IDS["Ubuntu Server 22.04 LTS"],      "22.04.3"),
            (OS_IDS["Red Hat Enterprise Linux 9"],   "9.3"),
        ]
        weights = [40, 30, 20, 10]
    else:
        os_opts = [
            (OS_IDS["Windows 10 Pro"],  "22H2 (Build 19045)"),
            (OS_IDS["Windows 11 Pro"],  "23H2 (Build 22631)"),
        ]
        weights = [55, 45]

    chosen_os, chosen_ver = random.choices(os_opts, weights=weights[:len(os_opts)])[0]
    ver_id = OS_VER_IDS.get((chosen_os, chosen_ver), 0)
    os_records.append((comp_id, chosen_os, ver_id))

# Inserir em lote
for comp_id, os_id, ver_id in os_records:
    cur.execute("""
        INSERT INTO glpi_items_operatingsystems
          (items_id, itemtype, operatingsystems_id, operatingsystemversions_id,
           operatingsystemservicepacks_id, operatingsystemarchitectures_id,
           operatingsystemkernelversions_id, entities_id, is_recursive,
           is_deleted, is_dynamic, date_mod, date_creation)
        VALUES (%s,'Computer',%s,%s,0,0,0,0,0,0,0,NOW(),NOW())
    """, (comp_id, os_id, ver_id))

conn.commit()
print(f"  {len(OS_IDS)} SOs | {len(OS_VER_IDS)} versões | {len(os_records)} vinc. computador-SO")


# ─── 3. SOFTWARES ─────────────────────────────────────────────────────────────
print("\n[3/6] Softwares corporativos")

# Formato: (nome, fabricante, categoria_analítica, helpdesk_visible)
SOFTWARE_CATALOG = [
    # Microsoft
    ("Microsoft 365 Apps for Enterprise",   "Microsoft",           "Produtividade",     1),
    ("Microsoft Teams",                      "Microsoft",           "Colaboracao",        1),
    ("Microsoft Visio Professional 2021",    "Microsoft",           "Produtividade",     1),
    ("Microsoft Project Professional 2021",  "Microsoft",           "Gestao de Projetos",1),
    ("Microsoft SQL Server 2022 Standard",   "Microsoft",           "Banco de Dados",    0),
    ("Visual Studio Code",                   "Microsoft",           "Desenvolvimento",   1),
    ("Windows Subsystem for Linux",          "Microsoft",           "Desenvolvimento",   1),
    # Segurança
    ("CrowdStrike Falcon",                   "CrowdStrike",         "Seguranca",         0),
    ("Trend Micro Deep Security",            "Trend Micro",         "Seguranca",         0),
    # Virtualização
    ("VMware Workstation Pro 17",            "VMware",              "Virtualizacao",     0),
    ("Oracle VirtualBox",                    "Oracle",              "Virtualizacao",     1),
    # Monitoramento
    ("Zabbix Agent 6.4",                     "Zabbix",              "Monitoramento",     0),
    ("PRTG Network Monitor",                 "Paessler",            "Monitoramento",     0),
    # Banco de Dados
    ("MySQL Community Server 8.0",           "Oracle",              "Banco de Dados",    0),
    ("PostgreSQL 16",                        "PostgreSQL Global",   "Banco de Dados",    0),
    # Utilitários e Dev
    ("7-Zip",                                "7-Zip",               "Utilitarios",       1),
    ("Notepad++",                            "Notepad++",           "Utilitarios",       1),
    ("Git for Windows",                      "Git",                 "Desenvolvimento",   1),
    ("Python 3.12",                          "Python Software Fnd", "Desenvolvimento",   1),
    ("Google Chrome",                        "Google",              "Browser",           1),
    ("Mozilla Firefox ESR",                  "Mozilla",             "Browser",           1),
    # ERP / Negócio
    ("TOTVS Protheus ERP",                   "TOTVS",               "ERP",               1),
    ("SAP GUI 7.70",                         "SAP",                 "ERP",               1),
    # Backup
    ("Veeam Backup & Replication 12",        "Veeam Software",      "Backup",            0),
    ("Bacula Enterprise",                    "Bacula Systems",      "Backup",            0),
    # Colaboração
    ("Zoom Workplace",                       "Zoom",                "Colaboracao",        1),
    ("Slack",                                "Salesforce",          "Colaboracao",        1),
    # Impressão
    ("PaperCut MF",                          "PaperCut Software",   "Impressao",         0),
]

# Garantir que os fabricantes de software existam
extra_mfrs = set(m for _, m, _, _ in SOFTWARE_CATALOG) - set(MFR_BY_NAME.keys())
for mname in sorted(extra_mfrs):
    cur.execute(
        "INSERT INTO glpi_manufacturers (name, date_mod, date_creation) VALUES (%s, NOW(), NOW())",
        (mname,)
    )
    MFR_BY_NAME[mname] = cur.lastrowid
    MFR_IDS.append(cur.lastrowid)
conn.commit()

SW_IDS = {}
SW_VER_IDS = {}

# Mapear versão padrão por software
SW_VERSIONS = {
    "Microsoft 365 Apps for Enterprise":    "Version 2401 (16.0.17231)",
    "Microsoft Teams":                       "23306.3002.2715",
    "Microsoft Visio Professional 2021":    "16.0.17231.20194",
    "Microsoft Project Professional 2021":  "16.0.17231.20194",
    "Microsoft SQL Server 2022 Standard":   "16.0.4075.1 (RTM CU6)",
    "Visual Studio Code":                   "1.86.2",
    "Windows Subsystem for Linux":          "2.0.14",
    "CrowdStrike Falcon":                   "7.14.17205",
    "Trend Micro Deep Security":            "20.0.1070",
    "VMware Workstation Pro 17":            "17.5.1",
    "Oracle VirtualBox":                    "7.0.14",
    "Zabbix Agent 6.4":                     "6.4.12",
    "PRTG Network Monitor":                 "23.4.90.1577",
    "MySQL Community Server 8.0":           "8.0.36",
    "PostgreSQL 16":                        "16.2",
    "7-Zip":                                "23.01",
    "Notepad++":                            "8.6.2",
    "Git for Windows":                      "2.44.0",
    "Python 3.12":                          "3.12.2",
    "Google Chrome":                        "122.0.6261.128",
    "Mozilla Firefox ESR":                  "115.8.0",
    "TOTVS Protheus ERP":                   "12.1.2401",
    "SAP GUI 7.70":                         "7700.3.28.1085",
    "Veeam Backup & Replication 12":        "12.1.2.172",
    "Bacula Enterprise":                    "18.0.8",
    "Zoom Workplace":                       "5.17.11 (35480)",
    "Slack":                                "4.37.91",
    "PaperCut MF":                          "23.0.4",
}

for sw_name, mfr_name, category, helpdesk_vis in SOFTWARE_CATALOG:
    mfr_id = MFR_BY_NAME.get(mfr_name, 1)
    cur.execute("""
        INSERT INTO glpi_softwares
          (entities_id, is_recursive, name, manufacturers_id,
           is_helpdesk_visible, is_deleted, is_template,
           date_mod, date_creation)
        VALUES (0, 1, %s, %s, %s, 0, 0, NOW(), NOW())
    """, (sw_name, mfr_id, helpdesk_vis))
    sw_id = cur.lastrowid
    SW_IDS[sw_name] = sw_id

    # Versão
    ver_name = SW_VERSIONS.get(sw_name, "1.0")
    cur.execute("""
        INSERT INTO glpi_softwareversions
          (entities_id, is_recursive, softwares_id, name,
           states_id, date_mod, date_creation)
        VALUES (0, 1, %s, %s, %s, NOW(), NOW())
    """, (sw_id, ver_name, STATE_ACTIVE))
    SW_VER_IDS[sw_name] = cur.lastrowid

conn.commit()
print(f"  {len(SW_IDS)} softwares | {len(SW_VER_IDS)} versões")


# ─── 4. LICENÇAS ──────────────────────────────────────────────────────────────
print("\n[4/6] Licenças de software")

today = date.today()

# (sw_name, license_type, qty, years_duration, serial_prefix, allow_overquota)
LICENSE_DEFS = [
    ("Microsoft 365 Apps for Enterprise",  "Subscription - Anual",          62, 1, "MS365-EA",   0),
    ("Microsoft Teams",                     "Subscription - Anual",          62, 1, "MSTMS-",     0),
    ("Microsoft Visio Professional 2021",   "Volume - Enterprise Agreement",  5, 3, "VISIO-",     0),
    ("Microsoft Project Professional 2021", "Volume - Enterprise Agreement",  5, 3, "PROJ-",      0),
    ("Microsoft SQL Server 2022 Standard",  "Perpetua - Corporativa",         3, 0, "MSSQL22-",   0),
    ("Visual Studio Code",                  "Open Source",                  999, 0, "VSC-OS",      1),
    ("Windows Subsystem for Linux",         "Freeware",                     999, 0, "WSL-FW",      1),
    ("CrowdStrike Falcon",                  "Subscription - Anual",          65, 1, "CRW-",        0),
    ("Trend Micro Deep Security",           "Subscription - Anual",          15, 1, "TMDS-",       0),
    ("VMware Workstation Pro 17",           "Perpetua - Corporativa",        12, 0, "VMWWS-",      0),
    ("Oracle VirtualBox",                   "Open Source",                  999, 0, "VBX-OS",      1),
    ("Zabbix Agent 6.4",                    "Open Source",                  999, 0, "ZBX-OS",      1),
    ("PRTG Network Monitor",                "Subscription - Anual",           1, 1, "PRTG-ENT",    0),
    ("MySQL Community Server 8.0",          "Open Source",                  999, 0, "MYS-OS",      1),
    ("PostgreSQL 16",                       "Open Source",                  999, 0, "PG16-OS",     1),
    ("7-Zip",                               "Open Source",                  999, 0, "7ZIP-OS",     1),
    ("Notepad++",                           "Open Source",                  999, 0, "NPP-OS",      1),
    ("Git for Windows",                     "Open Source",                  999, 0, "GIT-OS",      1),
    ("Python 3.12",                         "Open Source",                  999, 0, "PY312-OS",    1),
    ("Google Chrome",                       "Freeware",                     999, 0, "GCHM-FW",     1),
    ("Mozilla Firefox ESR",                 "Open Source",                  999, 0, "FFX-OS",      1),
    ("TOTVS Protheus ERP",                  "Subscription - Anual",          60, 1, "TOTVS-",      0),
    ("SAP GUI 7.70",                        "Perpetua - Corporativa",        15, 0, "SAPGUI-",     0),
    ("Veeam Backup & Replication 12",       "Subscription - Anual",          1, 1, "VEEAM-",       0),
    ("Bacula Enterprise",                   "Subscription - Anual",          1, 1, "BACULA-",      0),
    ("Zoom Workplace",                      "SaaS - Por Usuario",            62, 1, "ZOOM-",        0),
    ("Slack",                               "SaaS - Por Usuario",            62, 1, "SLACK-",       0),
    ("PaperCut MF",                         "Subscription - Anual",           1, 3, "PCUT-",        0),
]

LIC_IDS = {}
for sw_name, lic_type, qty, yrs, serial_pfx, allow_over in LICENSE_DEFS:
    sw_id    = SW_IDS.get(sw_name)
    lt_id    = LIC_TYPE_IDS.get(lic_type, 1)
    ver_id   = SW_VER_IDS.get(sw_name, 0)
    serial   = f"{serial_pfx}{random.randint(1000,9999)}"
    expire_d = None if yrs == 0 else str(today.replace(year=today.year + yrs))
    cur.execute("""
        INSERT INTO glpi_softwarelicenses
          (softwares_id, entities_id, is_recursive, name,
           softwarelicensetypes_id, number,
           softwareversions_id_buy, softwareversions_id_use,
           serial, expire,
           states_id, is_deleted, is_template, is_valid,
           allow_overquota, date_mod, date_creation)
        VALUES (%s, 0, 1, %s, %s, %s, %s, %s, %s, %s,
                %s, 0, 0, 1, %s, NOW(), NOW())
    """, (sw_id, sw_name, lt_id, qty, ver_id, ver_id,
          serial, expire_d, STATE_ACTIVE, allow_over))
    LIC_IDS[sw_name] = cur.lastrowid

conn.commit()
print(f"  {len(LIC_IDS)} licenças cadastradas")


# ─── 5. SOFTWARE INSTALADO EM COMPUTADORES ────────────────────────────────────
print("\n[5/6] Instalações de software")

# Verificar se a tabela existe (no GLPI 10 é glpi_items_softwareversions)
sw_install_table = None
for tname in ["glpi_items_softwareversions", "glpi_computers_softwareversions"]:
    cur.execute(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema='glpi' AND table_name=%s", (tname,)
    )
    if cur.fetchone()[0]:
        sw_install_table = tname
        break

if not sw_install_table:
    print("  AVISO: Nenhuma tabela de instalação de software encontrada. Pulando.")
else:
    cur.execute(f"DESCRIBE `{sw_install_table}`")
    sw_install_cols = [r[0] for r in cur.fetchall()]
    print(f"  Tabela: {sw_install_table} | colunas: {sw_install_cols}")

    # Definir quais softwares vão em quais tipos de máquina
    WS_SW = [
        "Microsoft 365 Apps for Enterprise",
        "Microsoft Teams",
        "CrowdStrike Falcon",
        "7-Zip",
        "Google Chrome",
        "Zoom Workplace",
    ]
    SRV_SW = [
        "Zabbix Agent 6.4",
        "CrowdStrike Falcon",
        "Trend Micro Deep Security",
        "7-Zip",
    ]
    OPTIONAL_WS = [
        "Visual Studio Code",
        "Git for Windows",
        "Python 3.12",
        "Notepad++",
        "Oracle VirtualBox",
        "VMware Workstation Pro 17",
        "Mozilla Firefox ESR",
        "Slack",
        "SAP GUI 7.70",
        "TOTVS Protheus ERP",
    ]

    installs = []
    for comp_id in ALL_COMPUTERS:
        sw_list = SRV_SW if comp_id in SRV_IDS else WS_SW
        for sw_name in sw_list:
            ver_id = SW_VER_IDS.get(sw_name)
            if ver_id:
                installs.append((comp_id, ver_id))

        # Opcionais para workstations (50% chance cada)
        if comp_id not in SRV_IDS:
            for sw_name in OPTIONAL_WS:
                if random.random() < 0.50:
                    ver_id = SW_VER_IDS.get(sw_name)
                    if ver_id:
                        installs.append((comp_id, ver_id))

    # Inserir de acordo com as colunas da tabela
    inserted = 0
    if "items_id" in sw_install_cols and "itemtype" in sw_install_cols:
        # GLPI 10 style: glpi_items_softwareversions (date_install, sem date_mod)
        date_install_col = "date_install" if "date_install" in sw_install_cols else None
        for comp_id, ver_id in installs:
            if date_install_col:
                cur.execute(
                    f"INSERT INTO `{sw_install_table}` "
                    "(items_id, itemtype, softwareversions_id, entities_id, "
                    " is_deleted, is_dynamic, date_install) "
                    "VALUES (%s, 'Computer', %s, 0, 0, 0, CURDATE())",
                    (comp_id, ver_id)
                )
            else:
                cur.execute(
                    f"INSERT INTO `{sw_install_table}` "
                    "(items_id, itemtype, softwareversions_id, entities_id, "
                    " is_deleted, is_dynamic) "
                    "VALUES (%s, 'Computer', %s, 0, 0, 0)",
                    (comp_id, ver_id)
                )
            inserted += 1
    elif "computers_id" in sw_install_cols:
        # GLPI 9 style: glpi_computers_softwareversions
        for comp_id, ver_id in installs:
            cur.execute(
                f"INSERT INTO `{sw_install_table}` "
                "(computers_id, softwareversions_id, entities_id, "
                " is_deleted, is_dynamic) "
                "VALUES (%s, %s, 0, 0, 0)",
                (comp_id, ver_id)
            )
            inserted += 1

    conn.commit()
    print(f"  {inserted} instalações em {len(ALL_COMPUTERS)} computadores")


# ─── 6. RESUMO ────────────────────────────────────────────────────────────────
print("\n" + "=" * 68)
print("  RESUMO — EXPANSION 1")
print("=" * 68)

checks = [
    ("glpi_operatingsystems",       "SELECT COUNT(*) FROM glpi_operatingsystems"),
    ("glpi_operatingsystemversions","SELECT COUNT(*) FROM glpi_operatingsystemversions"),
    ("glpi_items_operatingsystems", "SELECT COUNT(*) FROM glpi_items_operatingsystems"),
    ("glpi_softwares",              "SELECT COUNT(*) FROM glpi_softwares"),
    ("glpi_softwareversions",       "SELECT COUNT(*) FROM glpi_softwareversions"),
    ("glpi_softwarelicensetypes",   "SELECT COUNT(*) FROM glpi_softwarelicensetypes"),
    ("glpi_softwarelicenses",       "SELECT COUNT(*) FROM glpi_softwarelicenses"),
]
if sw_install_table:
    checks.append((sw_install_table, f"SELECT COUNT(*) FROM `{sw_install_table}`"))

for label, q in checks:
    cur.execute(q)
    print(f"  {label:<45} {cur.fetchone()[0]:>6}")

conn.close()
print("\nExpansion 1 concluída!")
