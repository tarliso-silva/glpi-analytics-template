-- =============================================================================
-- vw_entity_analytics.sql
-- Analytics views para modelo multi-entidade + Data Center / Racks
-- GLPI 10.x | MariaDB
--
-- Views criadas:
--   vw_entity_overview          — visão geral por entidade (tickets, ativos, usuários)
--   vw_entity_sla_monthly       — conformidade SLA por entidade e mês
--   vw_entity_asset_distribution — distribuição de ativos por tipo e entidade
--   vw_entity_project_performance— desempenho de projetos por entidade
--   vw_rack_inventory            — inventário de racks com incidentes vinculados
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 0. vw_dim_entity
--    Dimensão de entidades — use como slicer "Filial" no Power BI.
--    Relacione entity_id desta view com entity_id de:
--      vw_fact_tickets, vw_glpi_tickets, vw_dim_asset,
--      vw_fact_problems, vw_fact_changes, vw_fact_projects
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_dim_entity AS
SELECT
    e.id                AS entity_id,
    e.name              AS entity_name,
    e.level             AS entity_level,
    e.completename      AS entity_full_path,
    CASE e.level
        WHEN 0 THEN 'Empresa'
        WHEN 1 THEN 'Filial'
        ELSE        'Sub-entidade'
    END                 AS entity_type
FROM glpi_entities e
ORDER BY e.level, e.name;


-- ---------------------------------------------------------------------------
-- 1. vw_entity_overview
--    Resumo executivo por entidade: tickets, usuários, computadores,
--    chamados abertos e tempo médio de resolução.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_entity_overview AS
SELECT
    e.id                                        AS entity_id,
    e.name                                      AS entity_name,
    e.level                                     AS entity_level,

    -- Usuários
    (SELECT COUNT(*) FROM glpi_users u
     WHERE u.entities_id = e.id)                AS total_users,

    -- Tickets totais
    (SELECT COUNT(*) FROM glpi_tickets t
     WHERE t.entities_id = e.id
       AND t.is_deleted = 0)                    AS total_tickets,

    -- Tickets abertos (status 1=New, 2=Processing assigned, 3=Processing planned)
    (SELECT COUNT(*) FROM glpi_tickets t
     WHERE t.entities_id = e.id
       AND t.is_deleted = 0
       AND t.status IN (1, 2, 3))               AS open_tickets,

    -- Tickets fechados (status 5=Solved, 6=Closed)
    (SELECT COUNT(*) FROM glpi_tickets t
     WHERE t.entities_id = e.id
       AND t.is_deleted = 0
       AND t.status IN (5, 6))                  AS closed_tickets,

    -- Tempo médio de resolução em horas (apenas resolvidos)
    ROUND(
        (SELECT AVG(TIMESTAMPDIFF(HOUR, t.date, t.solvedate))
         FROM glpi_tickets t
         WHERE t.entities_id = e.id
           AND t.is_deleted = 0
           AND t.solvedate IS NOT NULL
           AND t.date IS NOT NULL), 1
    )                                           AS avg_resolution_hours,

    -- Computadores
    (SELECT COUNT(*) FROM glpi_computers c
     WHERE c.entities_id = e.id
       AND c.is_deleted = 0)                    AS total_computers,

    -- Servidores (baseado no nome SRV-*)
    (SELECT COUNT(*) FROM glpi_computers c
     WHERE c.entities_id = e.id
       AND c.is_deleted = 0
       AND c.name LIKE 'SRV-%')                 AS total_servers,

    -- Workstations (WS-*)
    (SELECT COUNT(*) FROM glpi_computers c
     WHERE c.entities_id = e.id
       AND c.is_deleted = 0
       AND c.name LIKE 'WS-%')                  AS total_workstations,

    -- Equipamentos de rede
    (SELECT COUNT(*) FROM glpi_networkequipments n
     WHERE n.entities_id = e.id
       AND n.is_deleted = 0)                    AS total_network_equipment,

    -- Projetos ativos (status != 0 e end_date futuro ou nulo)
    (SELECT COUNT(*) FROM glpi_projects p
     WHERE p.entities_id = e.id
       AND p.is_deleted = 0)                    AS total_projects

FROM glpi_entities e
ORDER BY e.level, e.name;


-- ---------------------------------------------------------------------------
-- 2. vw_entity_sla_monthly
--    Conformidade de SLA por entidade e mês:
--    dentro do prazo vs violado vs sem SLA definido.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_entity_sla_monthly AS
SELECT
    e.id                                        AS entity_id,
    e.name                                      AS entity_name,
    DATE_FORMAT(t.date, '%Y-%m')                AS `year_month`,
    COUNT(*)                                    AS total_tickets,

    -- Com SLA definido (time_to_resolve != NULL)
    SUM(CASE WHEN t.time_to_resolve IS NOT NULL THEN 1 ELSE 0 END)
                                                AS tickets_with_sla,

    -- Dentro do SLA: resolvido antes ou no prazo
    SUM(CASE
        WHEN t.time_to_resolve IS NOT NULL
         AND t.solvedate IS NOT NULL
         AND t.solvedate <= t.time_to_resolve
        THEN 1 ELSE 0
    END)                                        AS within_sla,

    -- Violado: resolvido depois do prazo
    SUM(CASE
        WHEN t.time_to_resolve IS NOT NULL
         AND t.solvedate IS NOT NULL
         AND t.solvedate > t.time_to_resolve
        THEN 1 ELSE 0
    END)                                        AS breached_sla,

    -- Em aberto com SLA pendente (ainda não resolvido)
    SUM(CASE
        WHEN t.time_to_resolve IS NOT NULL
         AND t.solvedate IS NULL
         AND t.status NOT IN (5, 6)
        THEN 1 ELSE 0
    END)                                        AS pending_with_sla,

    -- Taxa de conformidade (%)
    ROUND(
        100.0 *
        SUM(CASE
            WHEN t.time_to_resolve IS NOT NULL
             AND t.solvedate IS NOT NULL
             AND t.solvedate <= t.time_to_resolve
            THEN 1 ELSE 0
        END)
        / NULLIF(
            SUM(CASE
                WHEN t.time_to_resolve IS NOT NULL
                 AND t.solvedate IS NOT NULL
                THEN 1 ELSE 0
            END), 0
        ), 1
    )                                           AS sla_compliance_pct,

    -- Tipo de ticket predominante no mês
    (SELECT t2.type
     FROM glpi_tickets t2
     WHERE t2.entities_id = e.id
       AND t2.is_deleted = 0
       AND DATE_FORMAT(t2.date, '%Y-%m') = DATE_FORMAT(t.date, '%Y-%m')
     GROUP BY t2.type
     ORDER BY COUNT(*) DESC
     LIMIT 1)                                   AS predominant_type

FROM glpi_tickets t
JOIN glpi_entities e ON e.id = t.entities_id
WHERE t.is_deleted = 0
GROUP BY
    e.id,
    e.name,
    DATE_FORMAT(t.date, '%Y-%m')
ORDER BY e.name, `year_month`;


-- ---------------------------------------------------------------------------
-- 3. vw_entity_asset_distribution
--    Distribuição de ativos por tipo e entidade, com valor financeiro
--    e porcentagem em relação ao total geral.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_entity_asset_distribution AS
SELECT
    e.id                        AS entity_id,
    e.name                      AS entity_name,
    asset_data.asset_type,
    asset_data.total_assets,
    asset_data.total_value_brl,
    ROUND(
        100.0 * asset_data.total_assets
        / NULLIF((SELECT COUNT(*) FROM (
            SELECT id FROM glpi_computers WHERE is_deleted = 0
            UNION ALL SELECT id FROM glpi_networkequipments WHERE is_deleted = 0
            UNION ALL SELECT id FROM glpi_monitors WHERE is_deleted = 0
            UNION ALL SELECT id FROM glpi_printers WHERE is_deleted = 0
            UNION ALL SELECT id FROM glpi_phones WHERE is_deleted = 0
            UNION ALL SELECT id FROM glpi_peripherals WHERE is_deleted = 0
        ) all_assets), 0), 1
    )                           AS pct_of_total_assets
FROM glpi_entities e
JOIN (
    -- Computadores — Servidores
    SELECT entities_id, 'Servidor' AS asset_type,
           COUNT(*) AS total_assets,
           SUM(COALESCE((
               SELECT ic.value FROM glpi_infocoms ic
               WHERE ic.itemtype = 'Computer' AND ic.items_id = c.id LIMIT 1
           ), 0)) AS total_value_brl
    FROM glpi_computers c
    WHERE c.is_deleted = 0 AND c.name LIKE 'SRV-%'
    GROUP BY c.entities_id

    UNION ALL

    -- Computadores — Workstations
    SELECT entities_id, 'Workstation' AS asset_type,
           COUNT(*) AS total_assets,
           SUM(COALESCE((
               SELECT ic.value FROM glpi_infocoms ic
               WHERE ic.itemtype = 'Computer' AND ic.items_id = c.id LIMIT 1
           ), 0)) AS total_value_brl
    FROM glpi_computers c
    WHERE c.is_deleted = 0 AND c.name LIKE 'WS-%'
    GROUP BY c.entities_id

    UNION ALL

    -- Equipamentos de rede
    SELECT entities_id, 'Rede' AS asset_type,
           COUNT(*) AS total_assets,
           SUM(COALESCE((
               SELECT ic.value FROM glpi_infocoms ic
               WHERE ic.itemtype = 'NetworkEquipment' AND ic.items_id = n.id LIMIT 1
           ), 0)) AS total_value_brl
    FROM glpi_networkequipments n
    WHERE n.is_deleted = 0
    GROUP BY n.entities_id

    UNION ALL

    -- Monitores
    SELECT entities_id, 'Monitor' AS asset_type,
           COUNT(*) AS total_assets,
           SUM(COALESCE((
               SELECT ic.value FROM glpi_infocoms ic
               WHERE ic.itemtype = 'Monitor' AND ic.items_id = m.id LIMIT 1
           ), 0)) AS total_value_brl
    FROM glpi_monitors m
    WHERE m.is_deleted = 0
    GROUP BY m.entities_id

    UNION ALL

    -- Impressoras
    SELECT entities_id, 'Impressora' AS asset_type,
           COUNT(*) AS total_assets,
           SUM(COALESCE((
               SELECT ic.value FROM glpi_infocoms ic
               WHERE ic.itemtype = 'Printer' AND ic.items_id = p.id LIMIT 1
           ), 0)) AS total_value_brl
    FROM glpi_printers p
    WHERE p.is_deleted = 0
    GROUP BY p.entities_id

    UNION ALL

    -- Telefones
    SELECT entities_id, 'Telefone' AS asset_type,
           COUNT(*) AS total_assets,
           0 AS total_value_brl
    FROM glpi_phones
    WHERE is_deleted = 0
    GROUP BY entities_id

    UNION ALL

    -- Periféricos
    SELECT entities_id, 'Periférico' AS asset_type,
           COUNT(*) AS total_assets,
           0 AS total_value_brl
    FROM glpi_peripherals
    WHERE is_deleted = 0
    GROUP BY entities_id

) asset_data ON asset_data.entities_id = e.id
ORDER BY e.name, asset_data.asset_type;


-- ---------------------------------------------------------------------------
-- 4. vw_entity_project_performance
--    Desempenho de projetos por entidade: progresso, tarefas concluídas
--    e atividade de tickets vinculados.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_entity_project_performance AS
SELECT
    e.id                                        AS entity_id,
    e.name                                      AS entity_name,
    p.id                                        AS project_id,
    p.name                                      AS project_name,
    p.percent_done                              AS percent_done,
    p.plan_start_date                           AS planned_start,
    p.plan_end_date                             AS planned_end,
    p.real_start_date                           AS real_start,
    p.real_end_date                             AS real_end,
    p.projectstates_id                          AS project_state_id,
    p.code                                      AS project_code,

    -- Total de tarefas
    (SELECT COUNT(*) FROM glpi_projecttasks pt
     WHERE pt.projects_id = p.id)               AS total_tasks,

    -- Tarefas concluídas (percent_done = 100)
    (SELECT COUNT(*) FROM glpi_projecttasks pt
     WHERE pt.projects_id = p.id
       AND pt.percent_done = 100)               AS completed_tasks,

    -- Tickets vinculados ao projeto
    (SELECT COUNT(*) FROM glpi_itils_projects ip
     WHERE ip.projects_id = p.id
       AND ip.itemtype = 'Ticket')              AS linked_tickets,

    -- Orçamento do projeto
    0                                           AS budget_id

FROM glpi_projects p
JOIN glpi_entities e ON e.id = p.entities_id
WHERE p.is_deleted = 0
ORDER BY e.name, p.percent_done DESC;


-- ---------------------------------------------------------------------------
-- 5. vw_rack_inventory
--    Inventário de racks com detalhe de cada ativo alocado,
--    entidade do rack e contagem de incidentes do ativo.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_rack_inventory AS
SELECT
    r.id                                        AS rack_id,
    r.name                                      AS rack_name,
    e.name                                      AS entity_name,
    l.name                                      AS location_name,
    r.number_units                              AS rack_units,
    r.max_power                                 AS max_power_w,
    ir.position                                 AS unit_position,
    ir.itemtype,

    -- Nome do ativo (Computer ou NetworkEquipment)
    COALESCE(
        c.name,
        ne.name
    )                                           AS asset_name,

    -- Serial do ativo
    COALESCE(
        c.serial,
        ne.serial
    )                                           AS asset_serial,

    -- Incidentes vinculados ao ativo (tipo Incident = 1)
    COALESCE((
        SELECT COUNT(*)
        FROM glpi_items_tickets it2
        JOIN glpi_tickets t2 ON t2.id = it2.tickets_id
        WHERE it2.itemtype = ir.itemtype
          AND it2.items_id = ir.items_id
          AND t2.type = 1
          AND t2.is_deleted = 0
    ), 0)                                       AS incident_count,

    -- Último incidente
    (
        SELECT MAX(t2.date)
        FROM glpi_items_tickets it2
        JOIN glpi_tickets t2 ON t2.id = it2.tickets_id
        WHERE it2.itemtype = ir.itemtype
          AND it2.items_id = ir.items_id
          AND t2.type = 1
          AND t2.is_deleted = 0
    )                                           AS last_incident_date,

    ir.bgcolor                                  AS slot_color

FROM glpi_items_racks ir
JOIN glpi_racks r        ON r.id  = ir.racks_id
JOIN glpi_entities e     ON e.id  = r.entities_id
LEFT JOIN glpi_locations l ON l.id = r.locations_id
LEFT JOIN glpi_computers c
    ON ir.itemtype = 'Computer'
    AND c.id = ir.items_id
LEFT JOIN glpi_networkequipments ne
    ON ir.itemtype = 'NetworkEquipment'
    AND ne.id = ir.items_id
ORDER BY r.name, ir.position;
