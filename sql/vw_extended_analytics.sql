-- =============================================================================
-- vw_extended_analytics.sql
-- Views de analytics estendidas: CMDB, Problems, Changes, Projects
-- Compatível com MariaDB — sem WITH RECURSIVE, backticks em aliases reservados
-- Para Power BI: Import Mode, atualização incremental recomendada
-- =============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. vw_dim_asset — Dimensão unificada de ativos CMDB
--    Consolida Computer, NetworkEquipment, Monitor e Printer em uma view
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW `vw_dim_asset` AS

SELECT
    CONCAT('Computer-', c.id)           AS asset_key,
    'Computer'                          AS asset_itemtype,
    c.id                                AS asset_id,
    c.name                              AS asset_name,
    ct.name                             AS asset_type,
    cm.name                             AS asset_model,
    mfr.name                            AS manufacturer,
    st.name                             AS asset_state,
    loc.name                            AS location,
    c.entities_id                       AS entity_id,
    u.name                             AS assigned_user,
    ut.name                            AS assigned_tech,
    c.serial                            AS serial_number,
    c.date_creation                     AS purchase_date,
    c.date_mod                          AS last_updated
FROM glpi_computers c
LEFT JOIN glpi_computertypes  ct  ON ct.id  = c.computertypes_id
LEFT JOIN glpi_computermodels cm  ON cm.id  = c.computermodels_id
LEFT JOIN glpi_manufacturers  mfr ON mfr.id = c.manufacturers_id
LEFT JOIN glpi_states         st  ON st.id  = c.states_id
LEFT JOIN glpi_locations      loc ON loc.id = c.locations_id
LEFT JOIN glpi_users          u   ON u.id   = c.users_id
LEFT JOIN glpi_users          ut  ON ut.id  = c.users_id_tech
WHERE c.is_deleted = 0

UNION ALL

SELECT
    CONCAT('NetworkEquipment-', ne.id)  AS asset_key,
    'NetworkEquipment'                  AS asset_itemtype,
    ne.id                               AS asset_id,
    ne.name                             AS asset_name,
    nt.name                             AS asset_type,
    nm.name                             AS asset_model,
    mfr.name                            AS manufacturer,
    st.name                             AS asset_state,
    loc.name                            AS location,
    ne.entities_id                      AS entity_id,
    NULL                                AS assigned_user,
    ut.name                            AS assigned_tech,
    ne.serial                           AS serial_number,
    ne.date_creation                    AS purchase_date,
    ne.date_mod                         AS last_updated
FROM glpi_networkequipments ne
LEFT JOIN glpi_networkequipmenttypes  nt  ON nt.id  = ne.networkequipmenttypes_id
LEFT JOIN glpi_networkequipmentmodels nm  ON nm.id  = ne.networkequipmentmodels_id
LEFT JOIN glpi_manufacturers          mfr ON mfr.id = ne.manufacturers_id
LEFT JOIN glpi_states                 st  ON st.id  = ne.states_id
LEFT JOIN glpi_locations              loc ON loc.id = ne.locations_id
LEFT JOIN glpi_users                  ut  ON ut.id  = ne.users_id_tech
WHERE ne.is_deleted = 0

UNION ALL

SELECT
    CONCAT('Monitor-', m.id)            AS asset_key,
    'Monitor'                           AS asset_itemtype,
    m.id                                AS asset_id,
    m.name                              AS asset_name,
    mty.name                            AS asset_type,
    mmo.name                            AS asset_model,
    mfr.name                            AS manufacturer,
    st.name                             AS asset_state,
    loc.name                            AS location,
    m.entities_id                       AS entity_id,
    u.name                             AS assigned_user,
    ut.name                            AS assigned_tech,
    m.serial                            AS serial_number,
    m.date_creation                     AS purchase_date,
    m.date_mod                          AS last_updated
FROM glpi_monitors m
LEFT JOIN glpi_monitortypes   mty ON mty.id = m.monitortypes_id
LEFT JOIN glpi_monitormodels  mmo ON mmo.id = m.monitormodels_id
LEFT JOIN glpi_manufacturers  mfr ON mfr.id = m.manufacturers_id
LEFT JOIN glpi_states         st  ON st.id  = m.states_id
LEFT JOIN glpi_locations      loc ON loc.id = m.locations_id
LEFT JOIN glpi_users          u   ON u.id   = m.users_id
LEFT JOIN glpi_users          ut  ON ut.id  = m.users_id_tech
WHERE m.is_deleted = 0

UNION ALL

SELECT
    CONCAT('Printer-', p.id)            AS asset_key,
    'Printer'                           AS asset_itemtype,
    p.id                                AS asset_id,
    p.name                              AS asset_name,
    pty.name                            AS asset_type,
    pmo.name                            AS asset_model,
    mfr.name                            AS manufacturer,
    st.name                             AS asset_state,
    loc.name                            AS location,
    p.entities_id                       AS entity_id,
    NULL                                AS assigned_user,
    ut.name                            AS assigned_tech,
    p.serial                            AS serial_number,
    p.date_creation                     AS purchase_date,
    p.date_mod                          AS last_updated
FROM glpi_printers p
LEFT JOIN glpi_printertypes   pty ON pty.id = p.printertypes_id
LEFT JOIN glpi_printermodels  pmo ON pmo.id = p.printermodels_id
LEFT JOIN glpi_manufacturers  mfr ON mfr.id = p.manufacturers_id
LEFT JOIN glpi_states         st  ON st.id  = p.states_id
LEFT JOIN glpi_locations      loc ON loc.id = p.locations_id
LEFT JOIN glpi_users          ut  ON ut.id  = p.users_id_tech
WHERE p.is_deleted = 0
;


-- ─────────────────────────────────────────────────────────────────────────────
-- 2. vw_fact_asset_tickets — Tickets vinculados a ativos (granularidade: 1 linha por vínculo)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW `vw_fact_asset_tickets` AS
SELECT
    it.id                               AS link_id,
    CONCAT(it.itemtype, '-', it.items_id) AS asset_key,
    it.itemtype                         AS asset_itemtype,
    it.items_id                         AS asset_id,
    it.tickets_id                       AS ticket_id,
    t.name                              AS ticket_name,
    t.date                              AS ticket_date,
    YEAR(t.date)                        AS ticket_year,
    MONTH(t.date)                       AS ticket_month,
    t.status                            AS ticket_status,
    t.priority                          AS ticket_priority,
    cat.name                            AS category,
    CASE t.status
        WHEN 1 THEN 'Novo'
        WHEN 2 THEN 'Em andamento (atribuído)'
        WHEN 3 THEN 'Em andamento (planejado)'
        WHEN 4 THEN 'Pendente'
        WHEN 5 THEN 'Resolvido'
        WHEN 6 THEN 'Fechado'
        ELSE 'Desconhecido'
    END                                 AS ticket_status_label,
    CASE t.priority
        WHEN 1 THEN 'Muito baixa'
        WHEN 2 THEN 'Baixa'
        WHEN 3 THEN 'Media'
        WHEN 4 THEN 'Alta'
        WHEN 5 THEN 'Muito alta'
        WHEN 6 THEN 'Critica'
        ELSE 'Desconhecida'
    END                                 AS priority_label
FROM glpi_items_tickets it
JOIN glpi_tickets t ON t.id = it.tickets_id
LEFT JOIN glpi_itilcategories cat ON cat.id = t.itilcategories_id
WHERE t.is_deleted = 0
;


-- ─────────────────────────────────────────────────────────────────────────────
-- 3. vw_fact_asset_incidents — Métricas de incidentes por ativo (agregado)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW `vw_fact_asset_incidents` AS
SELECT
    CONCAT(it.itemtype, '-', it.items_id)  AS asset_key,
    it.itemtype                            AS asset_itemtype,
    it.items_id                            AS asset_id,
    COUNT(t.id)                            AS total_tickets,
    SUM(CASE WHEN t.status IN (5,6) THEN 1 ELSE 0 END)  AS tickets_closed,
    SUM(CASE WHEN t.status NOT IN (5,6) THEN 1 ELSE 0 END) AS tickets_open,
    SUM(CASE WHEN t.priority >= 4 THEN 1 ELSE 0 END)    AS tickets_high_priority,
    ROUND(AVG(
        CASE WHEN t.solvedate IS NOT NULL
             THEN TIMESTAMPDIFF(MINUTE, t.date, t.solvedate)
             ELSE NULL
        END
    ), 1)                                  AS avg_resolution_min,
    MIN(t.date)                            AS first_ticket_date,
    MAX(t.date)                            AS last_ticket_date
FROM glpi_items_tickets it
JOIN glpi_tickets t ON t.id = it.tickets_id AND t.is_deleted = 0
GROUP BY it.itemtype, it.items_id
;


-- ─────────────────────────────────────────────────────────────────────────────
-- 4. vw_fact_problems — Tabela fato de Problemas
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW `vw_fact_problems` AS
SELECT
    p.id                                AS problem_id,
    p.entities_id                       AS entity_id,
    p.name                              AS problem_name,
    p.date                              AS open_date,
    p.solvedate                         AS solve_date,
    p.closedate                         AS close_date,
    YEAR(p.date)                        AS open_year,
    MONTH(p.date)                       AS open_month,
    p.status                            AS status_code,
    CASE p.status
        WHEN 1 THEN 'Novo'
        WHEN 2 THEN 'Em andamento (atribuído)'
        WHEN 3 THEN 'Em andamento (planejado)'
        WHEN 4 THEN 'Pendente'
        WHEN 5 THEN 'Resolvido'
        WHEN 6 THEN 'Fechado'
        ELSE 'Desconhecido'
    END                                 AS status_label,
    p.priority                          AS priority_code,
    CASE p.priority
        WHEN 1 THEN 'Muito baixa'
        WHEN 2 THEN 'Baixa'
        WHEN 3 THEN 'Media'
        WHEN 4 THEN 'Alta'
        WHEN 5 THEN 'Muito alta'
        WHEN 6 THEN 'Critica'
        ELSE 'Desconhecida'
    END                                 AS priority_label,
    p.urgency                           AS urgency,
    p.impact                            AS impact,
    cat.name                            AS category,
    u_tech.name                        AS assigned_tech,
    CONCAT(u_tech.firstname, ' ', u_tech.realname) AS tech_fullname,
    grp.name                            AS assigned_group,
    COUNT(DISTINCT pt.tickets_id)       AS linked_tickets,
    COUNT(DISTINCT ip.id)               AS linked_assets,
    CASE WHEN p.solvedate IS NOT NULL
         THEN TIMESTAMPDIFF(MINUTE, p.date, p.solvedate)
         ELSE NULL
    END                                 AS resolution_minutes,
    CASE WHEN p.status IN (5,6) THEN 1 ELSE 0 END AS is_closed
FROM glpi_problems p
LEFT JOIN glpi_itilcategories cat ON cat.id = p.itilcategories_id
LEFT JOIN glpi_problems_users pu
       ON pu.problems_id = p.id AND pu.type = 2
LEFT JOIN glpi_users u_tech ON u_tech.id = pu.users_id
LEFT JOIN glpi_groups_problems gp ON gp.problems_id = p.id AND gp.type = 2
LEFT JOIN glpi_groups grp ON grp.id = gp.groups_id
LEFT JOIN glpi_problems_tickets pt ON pt.problems_id = p.id
LEFT JOIN glpi_items_problems   ip ON ip.problems_id = p.id
WHERE p.is_deleted = 0
GROUP BY
    p.id, p.entities_id, p.name, p.date, p.solvedate, p.closedate,
    YEAR(p.date), MONTH(p.date),
    p.status, p.priority, p.urgency, p.impact,
    cat.name, u_tech.name, u_tech.firstname, u_tech.realname, grp.name
;


-- ─────────────────────────────────────────────────────────────────────────────
-- 5. vw_fact_changes — Tabela fato de Mudanças
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW `vw_fact_changes` AS
SELECT
    c.id                                AS change_id,
    c.entities_id                       AS entity_id,
    c.name                              AS change_name,
    c.date                              AS open_date,
    c.solvedate                         AS solve_date,
    c.closedate                         AS close_date,
    YEAR(c.date)                        AS open_year,
    MONTH(c.date)                       AS open_month,
    c.status                            AS status_code,
    CASE c.status
        WHEN 1 THEN 'Novo'
        WHEN 2 THEN 'Em andamento'
        WHEN 5 THEN 'Resolvido'
        WHEN 6 THEN 'Fechado'
        ELSE 'Outro'
    END                                 AS status_label,
    c.priority                          AS priority_code,
    CASE c.priority
        WHEN 1 THEN 'Muito baixa'
        WHEN 2 THEN 'Baixa'
        WHEN 3 THEN 'Media'
        WHEN 4 THEN 'Alta'
        WHEN 5 THEN 'Muito alta'
        WHEN 6 THEN 'Critica'
        ELSE 'Desconhecida'
    END                                 AS priority_label,
    c.urgency                           AS urgency,
    c.impact                            AS impact,
    cat.name                            AS category,
    u_tech.name                        AS assigned_tech,
    CONCAT(u_tech.firstname, ' ', u_tech.realname) AS tech_fullname,
    COUNT(DISTINCT ct.tickets_id)       AS linked_tickets,
    COUNT(DISTINCT ci.id)               AS linked_assets,
    COUNT(DISTINCT cht.id)              AS total_tasks,
    SUM(CASE WHEN cht.state = 2 THEN 1 ELSE 0 END) AS tasks_done,
    CASE WHEN c.solvedate IS NOT NULL
         THEN TIMESTAMPDIFF(MINUTE, c.date, c.solvedate)
         ELSE NULL
    END                                 AS resolution_minutes,
    CASE WHEN c.status IN (5,6) THEN 1 ELSE 0 END AS is_closed
FROM glpi_changes c
LEFT JOIN glpi_itilcategories cat ON cat.id = c.itilcategories_id
LEFT JOIN glpi_changes_users  cu
       ON cu.changes_id = c.id AND cu.type = 2
LEFT JOIN glpi_users u_tech ON u_tech.id = cu.users_id
LEFT JOIN glpi_changes_tickets ct  ON ct.changes_id  = c.id
LEFT JOIN glpi_changes_items   ci  ON ci.changes_id  = c.id
LEFT JOIN glpi_changetasks     cht ON cht.changes_id = c.id
WHERE c.is_deleted = 0
GROUP BY
    c.id, c.entities_id, c.name, c.date, c.solvedate, c.closedate,
    YEAR(c.date), MONTH(c.date),
    c.status, c.priority, c.urgency, c.impact,
    cat.name, u_tech.name, u_tech.firstname, u_tech.realname
;


-- ─────────────────────────────────────────────────────────────────────────────
-- 6. vw_fact_projects — Tabela fato de Projetos
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW `vw_fact_projects` AS
SELECT
    p.id                                AS project_id,
    p.entities_id                       AS entity_id,
    p.name                              AS project_name,
    p.code                              AS project_code,
    p.priority                          AS priority_code,
    CASE p.priority
        WHEN 1 THEN 'Muito baixa'
        WHEN 2 THEN 'Baixa'
        WHEN 3 THEN 'Media'
        WHEN 4 THEN 'Alta'
        WHEN 5 THEN 'Muito alta'
        WHEN 6 THEN 'Critica'
        ELSE 'Desconhecida'
    END                                 AS priority_label,
    ps.name                             AS project_state,
    CASE ps.is_finished
        WHEN 1 THEN 'Encerrado'
        ELSE 'Em andamento'
    END                                 AS state_category,
    p.plan_start_date                   AS planned_start,
    p.plan_end_date                     AS planned_end,
    p.real_start_date                   AS real_start,
    p.real_end_date                     AS real_end,
    p.percent_done                      AS pct_done,
    YEAR(p.plan_start_date)             AS start_year,
    MONTH(p.plan_start_date)            AS start_month,
    TIMESTAMPDIFF(DAY, p.plan_start_date, p.plan_end_date)  AS planned_duration_days,
    CASE
        WHEN p.real_end_date IS NOT NULL
             THEN TIMESTAMPDIFF(DAY, p.plan_start_date, p.real_end_date)
        WHEN p.real_start_date IS NOT NULL
             THEN TIMESTAMPDIFF(DAY, p.plan_start_date, NOW())
        ELSE NULL
    END                                 AS actual_duration_days,
    u.name                              AS project_manager,
    CONCAT(u.firstname, ' ', u.realname) AS manager_fullname,
    grp.name                            AS responsible_group,
    (SELECT COUNT(*) FROM glpi_projecttasks t2
     WHERE t2.projects_id = p.id AND t2.is_deleted = 0)     AS total_tasks,
    (SELECT COUNT(*) FROM glpi_projecttasks t2
     WHERE t2.projects_id = p.id AND t2.is_deleted = 0
       AND t2.projectstates_id = 2)                          AS tasks_closed,
    (SELECT COUNT(DISTINCT ptt2.tickets_id)
     FROM glpi_projecttasks_tickets ptt2
     JOIN glpi_projecttasks t2 ON t2.id = ptt2.projecttasks_id
     WHERE t2.projects_id = p.id)                           AS linked_project_task_tickets,
    (SELECT COUNT(*) FROM glpi_projectteams ptm2
     WHERE ptm2.projects_id = p.id)                         AS team_members
FROM glpi_projects p
LEFT JOIN glpi_projectstates ps  ON ps.id  = p.projectstates_id
LEFT JOIN glpi_users         u   ON u.id   = p.users_id
LEFT JOIN glpi_groups        grp ON grp.id = p.groups_id
WHERE p.is_deleted = 0
;


-- ─────────────────────────────────────────────────────────────────────────────
-- 7. vw_fact_project_tasks — Detalhes das tarefas de projeto
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW `vw_fact_project_tasks` AS
SELECT
    pt.id                               AS task_id,
    pt.projects_id                      AS project_id,
    p.name                              AS project_name,
    p.code                              AS project_code,
    pt.name                             AS task_name,
    pt.is_milestone                     AS is_milestone,
    pt.plan_start_date                  AS planned_start,
    pt.plan_end_date                    AS planned_end,
    pt.real_start_date                  AS real_start,
    pt.real_end_date                    AS real_end,
    pt.percent_done                     AS pct_done,
    ps.name                             AS task_state,
    u.name                             AS responsible,
    CONCAT(u.firstname, ' ', u.realname) AS responsible_fullname,
    TIMESTAMPDIFF(DAY, pt.plan_start_date, pt.plan_end_date) AS planned_days,
    CASE
        WHEN pt.real_end_date IS NOT NULL
             THEN TIMESTAMPDIFF(DAY, pt.plan_start_date, pt.real_end_date)
        ELSE NULL
    END                                 AS actual_days,
    CASE
        WHEN pt.real_end_date IS NOT NULL
             AND pt.real_end_date > pt.plan_end_date
             THEN TIMESTAMPDIFF(DAY, pt.plan_end_date, pt.real_end_date)
        ELSE 0
    END                                 AS delay_days,
    COUNT(DISTINCT ptt.tickets_id)      AS linked_tickets
FROM glpi_projecttasks pt
JOIN glpi_projects p ON p.id = pt.projects_id
LEFT JOIN glpi_projectstates ps ON ps.id = pt.projectstates_id
LEFT JOIN glpi_users u ON u.id = pt.users_id
LEFT JOIN glpi_projecttasks_tickets ptt ON ptt.projecttasks_id = pt.id
WHERE pt.is_deleted = 0
GROUP BY
    pt.id, pt.projects_id, p.name, p.code, pt.name, pt.is_milestone,
    pt.plan_start_date, pt.plan_end_date, pt.real_start_date, pt.real_end_date,
    pt.percent_done, ps.name, u.name, u.firstname, u.realname
;


-- ─────────────────────────────────────────────────────────────────────────────
-- 8. vw_cmdb_summary — Inventário CMDB por tipo/fabricante/estado/localização
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW `vw_cmdb_summary` AS
SELECT
    asset_itemtype                      AS asset_type,
    asset_type                          AS subtype,
    manufacturer,
    asset_state,
    location,
    COUNT(*)                            AS total_assets
FROM vw_dim_asset
GROUP BY asset_itemtype, asset_type, manufacturer, asset_state, location
;
