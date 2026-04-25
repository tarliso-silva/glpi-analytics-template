-- =============================================================================
--  vw_analytics_v2.sql — Views analíticas expandidas (Expansion 1-4)
--  Compatível com: MariaDB / GLPI 10.x
--  Gerado em: 2025
-- =============================================================================

-- ─── 1. vw_dim_supplier ──────────────────────────────────────────────────────
-- Dimensão Fornecedores (para star schema)
CREATE OR REPLACE VIEW vw_dim_supplier AS
SELECT
    s.id                            AS supplier_id,
    s.name                          AS supplier_name,
    st.name                         AS supplier_type,
    s.email,
    s.phonenumber                   AS phone,
    s.town,
    s.state,
    s.website,
    s.is_active
FROM glpi_suppliers s
LEFT JOIN glpi_suppliertypes st ON st.id = s.suppliertypes_id
WHERE s.is_deleted = 0;


-- ─── 2. vw_dim_software ──────────────────────────────────────────────────────
-- Dimensão Software (catálogo corporativo)
CREATE OR REPLACE VIEW vw_dim_software AS
SELECT
    sw.id                           AS software_id,
    sw.name                         AS software_name,
    m.name                          AS manufacturer,
    sv.id                           AS version_id,
    sv.name                         AS version_name,
    lt.name                         AS license_type,
    sl.number                       AS licenses_qty,
    sl.expire                       AS license_expiry,
    sl.serial                       AS license_serial,
    sw.is_helpdesk_visible          AS helpdesk_visible
FROM glpi_softwares sw
LEFT JOIN glpi_manufacturers m       ON m.id  = sw.manufacturers_id
LEFT JOIN glpi_softwareversions sv   ON sv.softwares_id = sw.id
LEFT JOIN glpi_softwarelicenses sl   ON sl.softwares_id = sw.id
LEFT JOIN glpi_softwarelicensetypes lt ON lt.id = sl.softwarelicensetypes_id
WHERE sw.is_deleted = 0;


-- ─── 3. vw_fact_software_licenses ────────────────────────────────────────────
-- Compliance de licenças: emitidas vs instaladas
CREATE OR REPLACE VIEW vw_fact_software_licenses AS
SELECT
    sw.id                                                       AS software_id,
    sw.name                                                     AS software_name,
    m.name                                                      AS manufacturer,
    sl.number                                                   AS licenses_qty,
    sl.allow_overquota,
    sl.expire                                                   AS license_expiry,
    CASE
        WHEN sl.expire IS NULL OR sl.expire >= CURDATE() THEN 'Vigente'
        ELSE 'Expirada'
    END                                                         AS license_status,
    COUNT(isv.id)                                               AS installations_count,
    sl.number - COUNT(isv.id)                                   AS available_qty,
    CASE
        WHEN sl.number = 0       THEN 'Open/Free'
        WHEN COUNT(isv.id) > sl.number THEN 'Over-licensed'
        WHEN COUNT(isv.id) = sl.number THEN 'Fully Used'
        WHEN COUNT(isv.id) >= sl.number * 0.9 THEN 'Near Limit (>=90%)'
        ELSE 'OK'
    END                                                         AS compliance_status
FROM glpi_softwares sw
LEFT JOIN glpi_manufacturers m       ON m.id  = sw.manufacturers_id
LEFT JOIN glpi_softwarelicenses sl   ON sl.softwares_id = sw.id
LEFT JOIN glpi_softwareversions sv   ON sv.softwares_id = sw.id
LEFT JOIN glpi_items_softwareversions isv ON isv.softwareversions_id = sv.id
                                        AND isv.is_deleted = 0
WHERE sw.is_deleted = 0
GROUP BY
    sw.id, sw.name, m.name, sl.number, sl.allow_overquota,
    sl.expire;


-- ─── 4. vw_fact_asset_financials ─────────────────────────────────────────────
-- Informações financeiras e ciclo de vida de ativos
CREATE OR REPLACE VIEW vw_fact_asset_financials AS
SELECT
    ic.itemtype,
    ic.items_id,
    CASE
        WHEN ic.itemtype = 'Computer'          THEN c.name
        WHEN ic.itemtype = 'NetworkEquipment'  THEN ne.name
        WHEN ic.itemtype = 'Printer'           THEN pr.name
        ELSE CONCAT(ic.itemtype, '#', ic.items_id)
    END                                                             AS asset_name,
    loc.name                                                        AS location,
    s.name                                                          AS supplier,
    ic.buy_date,
    ic.use_date,
    ic.value                                                        AS purchase_value,
    ic.warranty_duration                                            AS warranty_months,
    ic.warranty_info,
    DATE_ADD(ic.buy_date, INTERVAL ic.warranty_duration MONTH)      AS warranty_end_date,
    CASE
        WHEN ic.warranty_duration = 0 THEN 'Sem garantia'
        WHEN DATE_ADD(ic.buy_date, INTERVAL ic.warranty_duration MONTH) < CURDATE() THEN 'Expirada'
        WHEN DATE_ADD(ic.buy_date, INTERVAL ic.warranty_duration MONTH) < DATE_ADD(CURDATE(), INTERVAL 3 MONTH) THEN 'Expira em <3 meses'
        ELSE 'Em garantia'
    END                                                             AS warranty_status,
    TIMESTAMPDIFF(MONTH, ic.buy_date, CURDATE())                    AS age_months
FROM glpi_infocoms ic
LEFT JOIN glpi_suppliers s           ON s.id  = ic.suppliers_id
LEFT JOIN glpi_computers c           ON c.id  = ic.items_id AND ic.itemtype = 'Computer'
LEFT JOIN glpi_networkequipments ne  ON ne.id = ic.items_id AND ic.itemtype = 'NetworkEquipment'
LEFT JOIN glpi_printers pr           ON pr.id = ic.items_id AND ic.itemtype = 'Printer'
LEFT JOIN glpi_locations loc         ON loc.id = COALESCE(c.locations_id, ne.locations_id, pr.locations_id);


-- ─── 5. vw_fact_supplier_contracts ───────────────────────────────────────────
-- Contratos por fornecedor com cobertura de ativos
CREATE OR REPLACE VIEW vw_fact_supplier_contracts AS
SELECT
    ct.name                                                     AS contract_name,
    ct.num                                                      AS contract_num,
    ctt.name                                                    AS contract_type,
    s.name                                                      AS supplier,
    ct.begin_date,
    DATE_ADD(ct.begin_date, INTERVAL ct.duration MONTH)         AS end_date,
    ct.duration                                                 AS duration_months,
    CASE
        WHEN DATE_ADD(ct.begin_date, INTERVAL ct.duration MONTH) < CURDATE() THEN 'Expirado'
        WHEN DATE_ADD(ct.begin_date, INTERVAL ct.duration MONTH) < DATE_ADD(CURDATE(), INTERVAL 3 MONTH) THEN 'Expira em <3 meses'
        ELSE 'Vigente'
    END                                                         AS contract_status,
    COUNT(ci.id)                                                AS assets_covered,
    ct.comment
FROM glpi_contracts ct
LEFT JOIN glpi_contracttypes ctt     ON ctt.id = ct.contracttypes_id
LEFT JOIN glpi_contracts_suppliers cs ON cs.contracts_id = ct.id
LEFT JOIN glpi_suppliers s            ON s.id  = cs.suppliers_id
LEFT JOIN glpi_contracts_items ci     ON ci.contracts_id = ct.id
WHERE ct.is_deleted = 0
GROUP BY
    ct.id, ct.name, ct.num, ctt.name, s.name,
    ct.begin_date, ct.duration, ct.comment;


-- ─── 6. vw_fact_kb_usage ─────────────────────────────────────────────────────
-- Base de conhecimento: artigos com estatísticas de uso
CREATE OR REPLACE VIEW vw_fact_kb_usage AS
SELECT
    kb.id                                           AS kb_id,
    kb.name                                         AS kb_title,
    kbc.name                                        AS kb_category,
    kb.is_faq                                       AS is_faq,
    kb.view                                         AS view_count,
    kb.date_creation,
    kb.date_mod                                     AS last_modified,
    COUNT(kbi.id)                                   AS linked_items_count,
    SUM(CASE WHEN kbi.itemtype = 'Ticket'   THEN 1 ELSE 0 END) AS linked_tickets,
    SUM(CASE WHEN kbi.itemtype = 'Computer' THEN 1 ELSE 0 END) AS linked_assets,
    u.name                                          AS author_login,
    CONCAT(u.firstname, ' ', u.realname)            AS author_name
FROM glpi_knowbaseitems kb
LEFT JOIN glpi_knowbaseitemcategories kbc ON kbc.id = kb.forms_categories_id
LEFT JOIN glpi_knowbaseitems_items kbi    ON kbi.knowbaseitems_id = kb.id
LEFT JOIN glpi_users u                   ON u.id = kb.users_id
GROUP BY
    kb.id, kb.name, kbc.name, kb.is_faq, kb.view,
    kb.date_creation, kb.date_mod, u.name, u.firstname, u.realname;


-- ─── 7. vw_fact_ticket_enrichment ────────────────────────────────────────────
-- Tickets com contagem de follow-ups, tarefas e satisfação
CREATE OR REPLACE VIEW vw_fact_ticket_enrichment AS
SELECT
    t.id                                                        AS ticket_id,
    t.name                                                      AS ticket_title,
    t.status,
    CASE t.status
        WHEN 1 THEN 'Novo'
        WHEN 2 THEN 'Em andamento (atribuido)'
        WHEN 3 THEN 'Em andamento (planejado)'
        WHEN 4 THEN 'Pendente'
        WHEN 5 THEN 'Resolvido'
        WHEN 6 THEN 'Fechado'
        ELSE 'Desconhecido'
    END                                                         AS status_label,
    t.date                                                      AS open_date,
    t.solvedate,
    t.closedate,
    TIMESTAMPDIFF(HOUR, t.date, COALESCE(t.solvedate, NOW()))   AS resolution_hours,
    (SELECT COUNT(*) FROM glpi_itilfollowups
     WHERE itemtype = 'Ticket' AND items_id = t.id)             AS followup_count,
    (SELECT COUNT(*) FROM glpi_tickettasks WHERE tickets_id = t.id) AS task_count,
    sat.satisfaction,
    sat.satisfaction_scaled_to_5,
    sat.comment                                                 AS satisfaction_comment,
    sat.date_answered                                           AS satisfaction_date
FROM glpi_tickets t
LEFT JOIN glpi_ticketsatisfactions sat ON sat.tickets_id = t.id;


-- ─── 8. vw_dim_os_inventory ──────────────────────────────────────────────────
-- Inventário de sistemas operacionais por ativo
CREATE OR REPLACE VIEW vw_dim_os_inventory AS
SELECT
    c.id                                AS computer_id,
    c.name                              AS computer_name,
    CASE
        WHEN c.name LIKE 'SRV-%' THEN 'Servidor'
        ELSE 'Workstation'
    END                                 AS asset_type,
    loc.name                            AS location,
    os.name                             AS os_name,
    osv.name                            AS os_version,
    ios.is_dynamic,
    ios.date_creation                   AS inventory_date
FROM glpi_items_operatingsystems ios
JOIN glpi_computers c               ON c.id  = ios.items_id AND ios.itemtype = 'Computer'
LEFT JOIN glpi_operatingsystems os  ON os.id = ios.operatingsystems_id
LEFT JOIN glpi_operatingsystemversions osv ON osv.id = ios.operatingsystemversions_id
LEFT JOIN glpi_locations loc        ON loc.id = c.locations_id
WHERE c.is_deleted = 0;


-- ─── 9. vw_fact_satisfaction_summary ─────────────────────────────────────────
-- Resumo de satisfação por mês e grupo técnico
CREATE OR REPLACE VIEW vw_fact_satisfaction_summary AS
SELECT
    DATE_FORMAT(sat.date_answered, '%Y-%m')         AS `year_month`,
    YEAR(sat.date_answered)                         AS `year`,
    MONTH(sat.date_answered)                        AS `month`,
    g.name                                          AS tech_group,
    COUNT(sat.id)                                   AS responses,
    ROUND(AVG(sat.satisfaction_scaled_to_5), 2)     AS avg_satisfaction,
    SUM(CASE WHEN sat.satisfaction_scaled_to_5 >= 4 THEN 1 ELSE 0 END) AS promoters,
    SUM(CASE WHEN sat.satisfaction_scaled_to_5 = 3  THEN 1 ELSE 0 END) AS neutrals,
    SUM(CASE WHEN sat.satisfaction_scaled_to_5 <= 2 THEN 1 ELSE 0 END) AS detractors
FROM glpi_ticketsatisfactions sat
JOIN glpi_tickets t               ON t.id = sat.tickets_id
LEFT JOIN glpi_groups_tickets gt  ON gt.tickets_id = t.id AND gt.type = 2
LEFT JOIN glpi_groups g           ON g.id = gt.groups_id
WHERE sat.date_answered IS NOT NULL
GROUP BY
    DATE_FORMAT(sat.date_answered, '%Y-%m'),
    YEAR(sat.date_answered),
    MONTH(sat.date_answered),
    g.name;
