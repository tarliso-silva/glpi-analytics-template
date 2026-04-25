"""
seed_expansion_3.py — Documentos, Base de Conhecimento, Telefones e Periféricos
Insere:
  - Categorias e documentos (políticas, manuais, contratos) vinculados a ativos/tickets
  - Categorias e artigos de KB (soluções e how-tos) vinculados a tickets e categorias
  - Telefones/VoIP com tipos e modelos
  - Periféricos (mouses, teclados, headsets, câmeras) com tipos e modelos
NÃO altera dados existentes.
random.seed(42) para reprodutibilidade.
"""
import mysql.connector, random, uuid as _uuid
from datetime import date, timedelta, datetime

random.seed(42)

DB = dict(host="localhost", port=3306, database="glpi", user="glpi", password="glpi")
conn = mysql.connector.connect(**DB)
conn.autocommit = False
cur = conn.cursor()

def count(t):
    cur.execute(f"SELECT COUNT(*) FROM `{t}`")
    return cur.fetchone()[0]

print("=" * 68)
print("  EXPANSION 3 — Documentos, KB, Telefones e Periféricos")
print("=" * 68)

# Carregar dados existentes
cur.execute("SELECT id FROM glpi_computers ORDER BY id")
ALL_COMPUTERS = [r[0] for r in cur.fetchall()]
cur.execute("SELECT id FROM glpi_computers WHERE name LIKE 'SRV-%'")
SRV_IDS = set(r[0] for r in cur.fetchall())
cur.execute("SELECT id FROM glpi_tickets ORDER BY id")
ALL_TICKETS = [r[0] for r in cur.fetchall()]
cur.execute("SELECT id FROM glpi_networkequipments ORDER BY id")
NET_IDS = [r[0] for r in cur.fetchall()]
cur.execute("SELECT id FROM glpi_users WHERE name NOT LIKE 'glpi%' ORDER BY id LIMIT 20")
TECH_IDS = [r[0] for r in cur.fetchall()]
cur.execute("SELECT id FROM glpi_locations ORDER BY id")
LOC_IDS = [r[0] for r in cur.fetchall()]
cur.execute("SELECT id FROM glpi_states ORDER BY id LIMIT 1")
row = cur.fetchone()
STATE_ACTIVE = row[0] if row else 1
cur.execute("SELECT id FROM glpi_manufacturers ORDER BY id")
MFR_IDS = [r[0] for r in cur.fetchall()]

today = date.today()

# ─── 1. CATEGORIAS DE DOCUMENTOS ─────────────────────────────────────────────
print("\n[1/8] Categorias de documentos")

if count("glpi_documentcategories") == 0:
    DOC_CATS = [
        ("Politicas de TI",          "Politicas e normas internas de TI"),
        ("Manuais e Procedimentos",  "Manuais operacionais e de usuario"),
        ("Contratos e SLAs",         "Documentos contratuais e acordos de nivel de servico"),
        ("Inventario e Ativos",      "Relatorios e planilhas de inventario"),
        ("Seguranca da Informacao",  "Politicas e planos de seguranca"),
        ("Infraestrutura",           "Diagramas, topologias e configuracoes"),
        ("Projetos",                 "Documentacao de projetos de TI"),
    ]
    DOC_CAT_IDS = {}
    for name, comment in DOC_CATS:
        cur.execute("""
            INSERT INTO glpi_documentcategories
              (name, comment, documentcategories_id, completename,
               level, date_mod, date_creation)
            VALUES (%s, %s, 0, %s, 1, NOW(), NOW())
        """, (name, comment, name))
        DOC_CAT_IDS[name] = cur.lastrowid
    conn.commit()
    print(f"  {len(DOC_CAT_IDS)} categorias de documento")
else:
    cur.execute("SELECT id, name FROM glpi_documentcategories")
    DOC_CAT_IDS = {n: i for i, n in cur.fetchall()}
    print(f"  Já existem {len(DOC_CAT_IDS)} categorias")

# ─── 2. DOCUMENTOS ────────────────────────────────────────────────────────────
print("\n[2/8] Documentos")

if count("glpi_documents") > 0:
    print("  Documentos já existem, pulando.")
    cur.execute("SELECT id FROM glpi_documents")
    DOC_IDS = [r[0] for r in cur.fetchall()]
else:
    DOCUMENTS = [
        ("POL-TI-001 Politica de Uso Aceitavel",          "Politicas de TI",         "POL-TI-001.pdf",   "application/pdf"),
        ("POL-TI-002 Politica de Senhas e Acessos",       "Politicas de TI",         "POL-TI-002.pdf",   "application/pdf"),
        ("POL-TI-003 Politica de Backup e Recuperacao",   "Politicas de TI",         "POL-TI-003.pdf",   "application/pdf"),
        ("POL-SI-001 Plano de Resposta a Incidentes",     "Seguranca da Informacao", "POL-SI-001.pdf",   "application/pdf"),
        ("POL-SI-002 Classificacao de Dados",             "Seguranca da Informacao", "POL-SI-002.pdf",   "application/pdf"),
        ("MAN-001 Manual do Usuario - Microsoft 365",     "Manuais e Procedimentos", "MAN-001.pdf",      "application/pdf"),
        ("MAN-002 Guia de Configuracao VPN",              "Manuais e Procedimentos", "MAN-002.pdf",      "application/pdf"),
        ("MAN-003 Manual de Backup com Veeam",            "Manuais e Procedimentos", "MAN-003.pdf",      "application/pdf"),
        ("MAN-004 Procedimento de Onboarding TI",         "Manuais e Procedimentos", "MAN-004.pdf",      "application/pdf"),
        ("INF-001 Diagrama de Topologia de Rede",         "Infraestrutura",          "INF-001.png",      "image/png"),
        ("INF-002 Planilha de Inventario de Ativos",      "Inventario e Ativos",     "INF-002.xlsx",     "application/vnd.ms-excel"),
        ("INF-003 Mapa de Servidor - Rack A",             "Infraestrutura",          "INF-003.pdf",      "application/pdf"),
        ("PRJ-001 Plano de Migracao Office 365",          "Projetos",                "PRJ-001.pdf",      "application/pdf"),
        ("PRJ-002 EAP - Implantacao ITSM",                "Projetos",                "PRJ-002.pdf",      "application/pdf"),
        ("CTR-001 Contrato TechCorp Manutencao HW",       "Contratos e SLAs",        "CTR-001.pdf",      "application/pdf"),
        ("CTR-002 SLA - Suporte Gerenciado Servidores",   "Contratos e SLAs",        "CTR-002.pdf",      "application/pdf"),
        ("CTR-003 Contrato Microsoft CSP",                "Contratos e SLAs",        "CTR-003.pdf",      "application/pdf"),
        ("CTR-004 Contrato NetConnect Link",              "Contratos e SLAs",        "CTR-004.pdf",      "application/pdf"),
    ]

    DOC_IDS = []
    author_id = TECH_IDS[0] if TECH_IDS else 1

    for name, cat_name, filename, mime in DOCUMENTS:
        cat_id = DOC_CAT_IDS.get(cat_name, 0)
        tag = f"DOC-{_uuid.uuid4().hex[:8].upper()}"
        cur.execute("""
            INSERT INTO glpi_documents
              (entities_id, is_recursive, name, filename, filepath,
               documentcategories_id, mime, comment, is_deleted,
               link, users_id, tag, date_mod, date_creation)
            VALUES (0, 1, %s, %s, %s, %s, %s, %s, 0, '', %s, %s, NOW(), NOW())
        """, (name, filename, f"document/{filename}", cat_id, mime,
              f"Documento gerenciado: {name}", author_id, tag))
        DOC_IDS.append(cur.lastrowid)

    conn.commit()
    print(f"  {len(DOC_IDS)} documentos")

# ─── 3. VINCULAR DOCUMENTOS A ITENS ──────────────────────────────────────────
print("\n[3/8] Vínculos documento ↔ ativo/ticket")

if count("glpi_documents_items") == 0:
    doc_item_rows = []
    author_id = TECH_IDS[0] if TECH_IDS else 1

    # Políticas → primeiros 30 tickets
    policy_docs = DOC_IDS[:5]
    sample_tickets = random.sample(ALL_TICKETS, min(30, len(ALL_TICKETS)))
    for doc_id in policy_docs[:2]:
        for tkt_id in sample_tickets[:10]:
            doc_item_rows.append((doc_id, tkt_id, "Ticket", author_id))

    # Infraestrutura → servidores e network
    infra_docs = [DOC_IDS[9], DOC_IDS[11]] if len(DOC_IDS) > 11 else DOC_IDS[:2]
    for doc_id in infra_docs:
        for srv_id in list(SRV_IDS)[:5]:
            doc_item_rows.append((doc_id, srv_id, "Computer", author_id))
        for net_id in NET_IDS[:4]:
            doc_item_rows.append((doc_id, net_id, "NetworkEquipment", author_id))

    # Contratos → computadores aleatórios
    ctr_docs = DOC_IDS[14:18] if len(DOC_IDS) >= 18 else DOC_IDS[-4:]
    for doc_id in ctr_docs:
        for comp_id in random.sample(ALL_COMPUTERS, min(5, len(ALL_COMPUTERS))):
            doc_item_rows.append((doc_id, comp_id, "Computer", author_id))

    inserted = 0
    for doc_id, item_id, itemtype, uid in doc_item_rows:
        cur.execute("""
            INSERT INTO glpi_documents_items
              (documents_id, items_id, itemtype, entities_id, is_recursive,
               users_id, date_mod, date_creation)
            VALUES (%s, %s, %s, 0, 1, %s, NOW(), NOW())
        """, (doc_id, item_id, itemtype, uid))
        inserted += 1

    conn.commit()
    print(f"  {inserted} vínculos documento ↔ item")
else:
    print("  documents_items já preenchido, pulando.")

# ─── 4. CATEGORIAS DE KB ──────────────────────────────────────────────────────
print("\n[4/8] Categorias de KB")

if count("glpi_knowbaseitemcategories") == 0:
    KB_CATS = [
        ("Hardware e CMDB",            "Problemas e solucoes relacionados a equipamentos"),
        ("Software e Sistemas",        "Instalacao, configuracao e troubleshooting de software"),
        ("Rede e Conectividade",       "Diagnostico e resolucao de problemas de rede"),
        ("Seguranca da Informacao",    "Procedimentos de seguranca e resposta a incidentes"),
        ("Servicos e Processos ITSM",  "Como usar o GLPI, SLAs, abertura de chamados"),
        ("Dicas e How-Tos",            "Tutoriais e procedimentos gerais de TI"),
    ]
    KB_CAT_IDS = {}
    for name, comment in KB_CATS:
        cur.execute("""
            INSERT INTO glpi_knowbaseitemcategories
              (name, comment, knowbaseitemcategories_id, completename,
               level, date_mod, date_creation)
            VALUES (%s, %s, 0, %s, 1, NOW(), NOW())
        """, (name, comment, name))
        KB_CAT_IDS[name] = cur.lastrowid
    conn.commit()
    print(f"  {len(KB_CAT_IDS)} categorias de KB")
else:
    cur.execute("SELECT id, name FROM glpi_knowbaseitemcategories")
    KB_CAT_IDS = {n: i for i, n in cur.fetchall()}
    print(f"  Já existem {len(KB_CAT_IDS)} categorias")

# ─── 5. ARTIGOS DE KB ─────────────────────────────────────────────────────────
print("\n[5/8] Artigos de Base de Conhecimento")

if count("glpi_knowbaseitems") > 0:
    print("  knowbaseitems já preenchido, pulando.")
    cur.execute("SELECT id FROM glpi_knowbaseitems")
    KB_IDS = [r[0] for r in cur.fetchall()]
else:
    KB_ARTICLES = [
        # (título, categoria, is_faq, resumo/answer)
        ("Como resetar senha do usuario no Active Directory",
         "Servicos e Processos ITSM", 1,
         "Acesse o AD, localize o usuario, clique com o botao direito e selecione 'Redefinir Senha'..."),
        ("Configuracao de VPN com cliente FortiClient",
         "Rede e Conectividade", 1,
         "Instale o FortiClient VPN, configure o gateway como vpn.empresa.com.br, porta 443..."),
        ("Procedimento de formatacao e reinstalacao de Windows",
         "Hardware e CMDB", 0,
         "Faca backup dos dados, inicialize pelo pendrive com Windows 10/11, siga o assistente de instalacao..."),
        ("Configuracao de email no Outlook (Microsoft 365)",
         "Software e Sistemas", 1,
         "Abra o Outlook, em Conta adicionar, informe o email corporativo, autenticacao moderna via MFA..."),
        ("Como abrir um chamado no GLPI corretamente",
         "Servicos e Processos ITSM", 1,
         "Acesse https://glpi.empresa.com.br, clique em Criar Chamado, preencha categoria, descricao detalhada e urgencia..."),
        ("Lentidao na maquina - passos de diagnostico",
         "Software e Sistemas", 1,
         "Verifique o Gerenciador de Tarefas, processos com alto consumo de CPU/RAM, execute CCleaner, verifique disco..."),
        ("Impressora nao imprime - troubleshooting",
         "Hardware e CMDB", 1,
         "Verifique fila de impressao, reinicie o spooler (services.msc > Print Spooler), reinstale o driver..."),
        ("Configuracao de MFA (autenticacao multifator) no Microsoft 365",
         "Seguranca da Informacao", 1,
         "Acesse aka.ms/mfasetup, escolha o aplicativo Microsoft Authenticator, escaneie o QR Code..."),
        ("Backup manual de arquivos para OneDrive",
         "Dicas e How-Tos", 1,
         "Abra o OneDrive, arraste os arquivos para a pasta sincronizada, aguarde o icone de nuvem verde..."),
        ("Erro 'Nao e possivel conectar ao servidor' no Protheus",
         "Software e Sistemas", 0,
         "Verifique se o servico AppServer esta em execucao no servidor TOTVS, verifique conectividade na porta 1234..."),
        ("Como acessar o servidor de arquivos via mapeamento de rede",
         "Rede e Conectividade", 1,
         "Abra o Explorer, clique em 'Este Computador > Mapear unidade de rede', informe \\\\fileserver\\dados..."),
        ("Politica de senhas - requisitos e boas praticas",
         "Seguranca da Informacao", 1,
         "Minimo 12 caracteres, letras maiusculas/minusculas, numeros e simbolos, troca a cada 90 dias..."),
        ("Zabbix Agent - instalacao e configuracao manual",
         "Software e Sistemas", 0,
         "Baixe o Zabbix Agent 6.4, configure zabbix_agentd.conf com Server=IP_ZABBIX, reinicie o servico..."),
        ("Como identificar e tratar phishing",
         "Seguranca da Informacao", 1,
         "Verifique o remetente real, nao clique em links suspeitos, reporte ao time de seguranca via email..."),
        ("Procedimento de onboarding - TI para novos colaboradores",
         "Servicos e Processos ITSM", 0,
         "Crie usuario no AD, atribua licenca M365, configure MFA, forneça credenciais ao gestor, entregue equipamento..."),
        ("Como conectar dois monitores no notebook",
         "Dicas e How-Tos", 1,
         "Conecte o cabo HDMI/DisplayPort, pressione Win+P e selecione Estender, ajuste a resolucao nas configuracoes..."),
        ("Swap de disco HD por SSD - guia tecnico",
         "Hardware e CMDB", 0,
         "Faca clone do disco com Macrium Reflect, troque o disco, ajuste o boot, valide integridade..."),
        ("Certificado SSL expirado - renovacao no IIS",
         "Infraestrutura", 0,
         "No IIS Manager, selecione Certificados do Servidor, importe o novo certificado .pfx, vincule ao site..."),
    ]

    author_id = TECH_IDS[0] if TECH_IDS else 1
    KB_IDS = []
    created_start = date(2022, 1, 1)

    for title, cat_name, is_faq, answer in KB_ARTICLES:
        # Verificar se a coluna forms_categories_id existe
        days_offset = random.randint(0, 700)
        created_dt = created_start + timedelta(days=days_offset)
        begin_d = str(created_dt)
        cur.execute("""
            INSERT INTO glpi_knowbaseitems
              (entities_id, is_recursive, name, answer, is_faq,
               users_id, view, show_in_service_catalog,
               date_creation, date_mod, begin_date)
            VALUES (0, 1, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)
        """, (title, answer, is_faq, author_id,
              random.randint(5, 150), is_faq,
              str(created_dt), begin_d))
        kb_id = cur.lastrowid
        KB_IDS.append(kb_id)

        # Vincular ao autor em knowbaseitems_users
        cur.execute(
            "INSERT INTO glpi_knowbaseitems_users (knowbaseitems_id, users_id) "
            "VALUES (%s, %s)", (kb_id, author_id)
        )

    conn.commit()
    print(f"  {len(KB_IDS)} artigos de KB")

# ─── 6. VINCULAR KB A TICKETS ────────────────────────────────────────────────
print("\n[6/8] KB ↔ tickets")

if count("glpi_knowbaseitems_items") == 0:
    kb_sample = random.sample(KB_IDS, min(10, len(KB_IDS)))
    ticket_sample = random.sample(ALL_TICKETS, min(40, len(ALL_TICKETS)))

    inserted_kb_items = 0
    for kb_id in kb_sample:
        n_links = random.randint(2, 6)
        for tkt_id in random.sample(ticket_sample, min(n_links, len(ticket_sample))):
            cur.execute("""
                INSERT INTO glpi_knowbaseitems_items
                  (knowbaseitems_id, itemtype, items_id, date_creation, date_mod)
                VALUES (%s, 'Ticket', %s, NOW(), NOW())
            """, (kb_id, tkt_id))
            inserted_kb_items += 1

    conn.commit()
    print(f"  {inserted_kb_items} vínculos KB ↔ ticket")
else:
    print("  knowbaseitems_items já preenchido, pulando.")

# ─── 7. TELEFONES ─────────────────────────────────────────────────────────────
print("\n[7/8] Telefones/VoIP")

if count("glpi_phonetypes") == 0:
    PHONE_TYPES = ["VoIP SIP", "Ramal Fisico", "Softphone", "Celular Corporativo"]
    PT_IDS = {}
    for pt in PHONE_TYPES:
        cur.execute(
            "INSERT INTO glpi_phonetypes (name, date_mod, date_creation) VALUES (%s, NOW(), NOW())", (pt,)
        )
        PT_IDS[pt] = cur.lastrowid
    conn.commit()
    print(f"  {len(PT_IDS)} tipos de telefone")
else:
    cur.execute("SELECT id, name FROM glpi_phonetypes")
    PT_IDS = {n: i for i, n in cur.fetchall()}

if count("glpi_phonemodels") == 0:
    PHONE_MODELS = [
        ("Cisco 8845", "CP-8845-K9"),
        ("Grandstream GXP2140", "GXP2140"),
        ("Yealink T54W", "T54W"),
        ("Polycom VVX 450", "VVX-450"),
    ]
    PM_IDS = {}
    for name, pn in PHONE_MODELS:
        cur.execute(
            "INSERT INTO glpi_phonemodels (name, product_number, date_mod, date_creation) "
            "VALUES (%s, %s, NOW(), NOW())", (name, pn)
        )
        PM_IDS[name] = cur.lastrowid
    conn.commit()
    print(f"  {len(PM_IDS)} modelos de telefone")
else:
    cur.execute("SELECT id, name FROM glpi_phonemodels")
    PM_IDS = {n: i for i, n in cur.fetchall()}

if count("glpi_phones") == 0:
    # 30 telefones: mix de VoIP e celular
    pt_keys = list(PT_IDS.keys())
    pm_keys = list(PM_IDS.keys())
    loc_ids = LOC_IDS or [0]
    mfr_voip = MFR_IDS[0] if MFR_IDS else 1

    phones_inserted = 0
    for i in range(1, 31):
        ph_type = random.choice(pt_keys)
        ph_model = random.choice(pm_keys)
        suffix = f"{i:03d}"
        name = f"PHONE-{suffix}"
        ramal = f"1{random.randint(100,999)}" if "VoIP" in ph_type or "Ramal" in ph_type else ""
        user_id = random.choice(TECH_IDS) if TECH_IDS and random.random() > 0.3 else 0
        loc_id = random.choice(loc_ids)
        serial = f"PHN{random.randint(100000, 999999)}"
        cur.execute("""
            INSERT INTO glpi_phones
              (entities_id, name, phonetypes_id, phonemodels_id,
               manufacturers_id, serial, number_line,
               users_id, locations_id, states_id,
               is_deleted, is_template, is_recursive,
               date_mod, date_creation)
            VALUES (0, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0, 0, 0, NOW(), NOW())
        """, (name, PT_IDS.get(ph_type, 1), PM_IDS.get(ph_model, 1),
              mfr_voip, serial, ramal,
              user_id, loc_id, STATE_ACTIVE))
        phones_inserted += 1

    conn.commit()
    print(f"  {phones_inserted} telefones")
else:
    print(f"  Telefones já existem ({count('glpi_phones')}), pulando.")

# ─── 8. PERIFÉRICOS ───────────────────────────────────────────────────────────
print("\n[8/8] Periféricos")

if count("glpi_peripheraltypes") == 0:
    PERIPH_TYPES = [
        "Mouse",
        "Teclado",
        "Headset",
        "Webcam",
        "Docking Station",
        "Monitor Externo",
    ]
    PERIPH_TYPE_IDS = {}
    for pt in PERIPH_TYPES:
        cur.execute(
            "INSERT INTO glpi_peripheraltypes (name, date_mod, date_creation) VALUES (%s, NOW(), NOW())", (pt,)
        )
        PERIPH_TYPE_IDS[pt] = cur.lastrowid
    conn.commit()
    print(f"  {len(PERIPH_TYPE_IDS)} tipos de periférico")
else:
    cur.execute("SELECT id, name FROM glpi_peripheraltypes")
    PERIPH_TYPE_IDS = {n: i for i, n in cur.fetchall()}

if count("glpi_peripheralmodels") == 0:
    PERIPH_MODELS = [
        ("Logitech MX Master 3S",   "910-006559"),
        ("Logitech G Pro Wireless", "910-005272"),
        ("Dell KB216",              "KB216"),
        ("Logitech K400 Plus",      "920-007119"),
        ("Jabra Evolve2 85",        "28599-999-999"),
        ("Poly Voyager Focus 2",    "213726-01"),
        ("Logitech C920s",          "960-001257"),
        ("Dell WD19S Dock",         "WD19S180W"),
        ("Dell UltraSharp U2422H",  "U2422H"),
    ]
    PERIPH_MODEL_IDS = {}
    for name, pn in PERIPH_MODELS:
        cur.execute(
            "INSERT INTO glpi_peripheralmodels (name, product_number, date_mod, date_creation) "
            "VALUES (%s, %s, NOW(), NOW())", (name, pn)
        )
        PERIPH_MODEL_IDS[name] = cur.lastrowid
    conn.commit()
    print(f"  {len(PERIPH_MODEL_IDS)} modelos de periférico")
else:
    cur.execute("SELECT id, name FROM glpi_peripheralmodels")
    PERIPH_MODEL_IDS = {n: i for i, n in cur.fetchall()}

if count("glpi_peripherals") == 0:
    # Cada workstation: mouse, teclado, headset (opcional)
    MOUSE_MODELS = [m for m in PERIPH_MODEL_IDS if "MX Master" in m or "G Pro" in m]
    KB_MODELS    = [m for m in PERIPH_MODEL_IDS if "KB216" in m or "K400" in m]
    HS_MODELS    = [m for m in PERIPH_MODEL_IDS if "Jabra" in m or "Poly" in m]
    CAM_MODELS   = [m for m in PERIPH_MODEL_IDS if "C920" in m]
    DOCK_MODELS  = [m for m in PERIPH_MODEL_IDS if "WD19" in m]
    MON_MODELS   = [m for m in PERIPH_MODEL_IDS if "UltraSharp" in m]

    WS_IDS = [c for c in ALL_COMPUTERS if c not in SRV_IDS]
    loc_ids = LOC_IDS or [0]
    periph_inserted = 0

    for ws_id in WS_IDS:
        user_id = random.choice(TECH_IDS) if TECH_IDS and random.random() > 0.4 else 0
        loc_id = random.choice(loc_ids)

        # Mouse (100%)
        if MOUSE_MODELS:
            m = random.choice(MOUSE_MODELS)
            serial = f"MSE{random.randint(100000,999999)}"
            cur.execute("""
                INSERT INTO glpi_peripherals
                  (entities_id, name, peripheraltypes_id, peripheralmodels_id,
                   manufacturers_id, serial, users_id, locations_id, states_id,
                   is_deleted, is_template, is_recursive, date_mod, date_creation)
                VALUES (0, %s, %s, %s, %s, %s, %s, %s, %s, 0, 0, 0, NOW(), NOW())
            """, (f"MOUSE-{serial}", PERIPH_TYPE_IDS.get("Mouse", 1),
                  PERIPH_MODEL_IDS.get(m, 1), MFR_IDS[0] if MFR_IDS else 1,
                  serial, user_id, loc_id, STATE_ACTIVE))
            periph_inserted += 1

        # Teclado (100%)
        if KB_MODELS:
            m = random.choice(KB_MODELS)
            serial = f"KBD{random.randint(100000,999999)}"
            cur.execute("""
                INSERT INTO glpi_peripherals
                  (entities_id, name, peripheraltypes_id, peripheralmodels_id,
                   manufacturers_id, serial, users_id, locations_id, states_id,
                   is_deleted, is_template, is_recursive, date_mod, date_creation)
                VALUES (0, %s, %s, %s, %s, %s, %s, %s, %s, 0, 0, 0, NOW(), NOW())
            """, (f"KBD-{serial}", PERIPH_TYPE_IDS.get("Teclado", 1),
                  PERIPH_MODEL_IDS.get(m, 1), MFR_IDS[0] if MFR_IDS else 1,
                  serial, user_id, loc_id, STATE_ACTIVE))
            periph_inserted += 1

        # Headset (60%)
        if HS_MODELS and random.random() < 0.60:
            m = random.choice(HS_MODELS)
            serial = f"HST{random.randint(100000,999999)}"
            cur.execute("""
                INSERT INTO glpi_peripherals
                  (entities_id, name, peripheraltypes_id, peripheralmodels_id,
                   manufacturers_id, serial, users_id, locations_id, states_id,
                   is_deleted, is_template, is_recursive, date_mod, date_creation)
                VALUES (0, %s, %s, %s, %s, %s, %s, %s, %s, 0, 0, 0, NOW(), NOW())
            """, (f"HST-{serial}", PERIPH_TYPE_IDS.get("Headset", 1),
                  PERIPH_MODEL_IDS.get(m, 1), MFR_IDS[0] if MFR_IDS else 1,
                  serial, user_id, loc_id, STATE_ACTIVE))
            periph_inserted += 1

        # Webcam (40%)
        if CAM_MODELS and random.random() < 0.40:
            m = random.choice(CAM_MODELS)
            serial = f"CAM{random.randint(100000,999999)}"
            cur.execute("""
                INSERT INTO glpi_peripherals
                  (entities_id, name, peripheraltypes_id, peripheralmodels_id,
                   manufacturers_id, serial, users_id, locations_id, states_id,
                   is_deleted, is_template, is_recursive, date_mod, date_creation)
                VALUES (0, %s, %s, %s, %s, %s, %s, %s, %s, 0, 0, 0, NOW(), NOW())
            """, (f"CAM-{serial}", PERIPH_TYPE_IDS.get("Webcam", 1),
                  PERIPH_MODEL_IDS.get(m, 1), MFR_IDS[0] if MFR_IDS else 1,
                  serial, user_id, loc_id, STATE_ACTIVE))
            periph_inserted += 1

    # Docking stations para todos notebooks (30% dos WS)
    if DOCK_MODELS:
        for ws_id in random.sample(WS_IDS, int(len(WS_IDS) * 0.30)):
            m = random.choice(DOCK_MODELS)
            serial = f"DCK{random.randint(100000,999999)}"
            cur.execute("""
                INSERT INTO glpi_peripherals
                  (entities_id, name, peripheraltypes_id, peripheralmodels_id,
                   manufacturers_id, serial, locations_id, states_id,
                   is_deleted, is_template, is_recursive, date_mod, date_creation)
                VALUES (0, %s, %s, %s, %s, %s, %s, %s, 0, 0, 0, NOW(), NOW())
            """, (f"DOCK-{serial}", PERIPH_TYPE_IDS.get("Docking Station", 1),
                  PERIPH_MODEL_IDS.get(m, 1), MFR_IDS[0] if MFR_IDS else 1,
                  serial, random.choice(loc_ids), STATE_ACTIVE))
            periph_inserted += 1

    conn.commit()
    print(f"  {periph_inserted} periféricos")
else:
    print(f"  Periféricos já existem ({count('glpi_peripherals')}), pulando.")

# ─── RESUMO ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 68)
print("  RESUMO — EXPANSION 3")
print("=" * 68)
for tbl in [
    "glpi_documentcategories", "glpi_documents", "glpi_documents_items",
    "glpi_knowbaseitemcategories", "glpi_knowbaseitems",
    "glpi_knowbaseitems_users", "glpi_knowbaseitems_items",
    "glpi_phonetypes", "glpi_phonemodels", "glpi_phones",
    "glpi_peripheraltypes", "glpi_peripheralmodels", "glpi_peripherals",
]:
    cur.execute(f"SELECT COUNT(*) FROM `{tbl}`")
    print(f"  {tbl:<40} {cur.fetchone()[0]:>6}")

conn.close()
print("\nExpansion 3 concluída!")
