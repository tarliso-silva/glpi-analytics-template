-- =============================================================================
-- Star Schema Analytics Views for GLPI Power BI
-- =============================================================================
-- Arquivo: sql/vw_star_schema.sql
--
-- Este arquivo cria as views complementares que compõem o modelo estrela:
--
--   FATO
--     vw_fact_tickets       — tabela fato desnormalizada (importar no PBI)
--
--   DIMENSÕES
--     vw_dim_date           — dimensão de datas (Calendário)
--     vw_dim_category       — dimensão de categorias com hierarquia
--     vw_dim_technician     — dimensão de técnicos com grupo
--     vw_dim_group          — dimensão de grupos de suporte
--     vw_dim_sla            — dimensão de SLAs
--     vw_dim_status         — dimensão de status
--     vw_dim_priority       — dimensão de prioridade
--
--   ANALÍTICAS (pré-agregadas)
--     vw_sla_monthly        — conformidade SLA por mês e grupo
--     vw_tech_productivity  — produtividade do técnico por mês
--     vw_backlog_open       — backlog atual de tickets abertos
--     vw_volume_trend       — tendência de volume mensal
--
-- Modelo de relacionamento Power BI sugerido:
--
--   vw_fact_tickets.created_date  → vw_dim_date.date        (many-to-one)
--   vw_fact_tickets.category_id   → vw_dim_category.id      (many-to-one)
--   vw_fact_tickets.technician_id → vw_dim_technician.id    (many-to-one)
--   vw_fact_tickets.group_id      → vw_dim_group.id         (many-to-one)
--   vw_fact_tickets.sla_id        → vw_dim_sla.id           (many-to-one)
--   vw_fact_tickets.status_code   → vw_dim_status.code      (many-to-one)
--   vw_fact_tickets.priority_code → vw_dim_priority.code    (many-to-one)
--
-- =============================================================================

-- =============================================================================
-- FATO: vw_fact_tickets
-- Tabela fato desnormalizada — uma linha por ticket, com chaves FK para dims.
-- Use IMPORT MODE no Power BI para melhor performance.
-- =============================================================================
CREATE OR REPLACE VIEW `glpi`.`vw_fact_tickets` AS
SELECT
    t.id                                                AS ticket_id,
    t.name                                              AS ticket_title,

    -- Chaves de data para relacionamento com vw_dim_date
    CAST(DATE(t.date)       AS DATE)                    AS created_date,
    CAST(DATE(t.solvedate)  AS DATE)                    AS resolved_date,
    CAST(DATE(t.closedate)  AS DATE)                    AS closed_date,

    -- Campos de granularidade temporal (para slicers no PBI)
    DATE_FORMAT(t.date, '%Y-%m')                        AS created_ym,
    YEAR(t.date)                                        AS created_year,
    MONTH(t.date)                                       AS created_month,
    QUARTER(t.date)                                     AS created_quarter,

    -- Chaves FK para dimensões
    COALESCE(gt.groups_id,  0)                          AS group_id,
    COALESCE(t.itilcategories_id, 0)                    AS category_id,
    COALESCE(tu_tech.users_id, 0)                       AS technician_id,
    COALESCE(tu_req.users_id,  0)                       AS requester_id,
    COALESCE(t.slas_id_ttr,    0)                       AS sla_id,
    t.status                                            AS status_code,
    t.priority                                          AS priority_code,
    t.type                                              AS ticket_type_code,

    -- Flags de estado
    CASE WHEN t.status IN (1,2,3,4) THEN 1 ELSE 0 END  AS is_open,
    CASE WHEN t.status IN (5,6)     THEN 1 ELSE 0 END  AS is_resolved,
    CASE WHEN t.status = 6          THEN 1 ELSE 0 END  AS is_closed,

    -- SLA compliance (NULL = sem SLA, 1 = dentro, 0 = violado)
    CASE
        WHEN t.time_to_resolve IS NULL THEN NULL
        WHEN t.status IN (5,6) AND t.solvedate <= t.time_to_resolve THEN 1
        WHEN t.status IN (5,6) AND t.solvedate >  t.time_to_resolve THEN 0
        ELSE NULL
    END                                                 AS sla_met,

    -- Status SLA textual
    CASE
        WHEN t.time_to_resolve IS NULL                                      THEN 'Sem SLA'
        WHEN t.status IN (5,6) AND t.solvedate <= t.time_to_resolve         THEN 'Dentro do SLA'
        WHEN t.status IN (5,6) AND t.solvedate >  t.time_to_resolve         THEN 'Violado'
        WHEN t.status NOT IN (5,6) AND NOW() > t.time_to_resolve            THEN 'Violado (aberto)'
        ELSE                                                                      'Em risco'
    END                                                 AS sla_status,

    -- Métricas de tempo em minutos
    CASE WHEN t.solvedate IS NOT NULL
        THEN TIMESTAMPDIFF(MINUTE, t.date, t.solvedate)   END              AS resolution_min,
    CASE WHEN t.closedate IS NOT NULL
        THEN TIMESTAMPDIFF(MINUTE, t.date, t.closedate)   END              AS closure_min,
    CASE WHEN t.takeintoaccountdate IS NOT NULL
        THEN TIMESTAMPDIFF(MINUTE, t.date, t.takeintoaccountdate) END      AS tto_min,
    CASE WHEN t.status NOT IN (5,6)
        THEN TIMESTAMPDIFF(MINUTE, t.date, NOW())          END              AS age_open_min,

    -- Contadores para measures simples no PBI
    1                                                   AS ticket_count

FROM `glpi`.`glpi_tickets` t
LEFT JOIN (
    SELECT tickets_id, MIN(groups_id) AS groups_id
    FROM `glpi`.`glpi_groups_tickets` WHERE type = 2 GROUP BY tickets_id
) gt ON gt.tickets_id = t.id
LEFT JOIN (
    SELECT tickets_id, MIN(users_id) AS users_id
    FROM `glpi`.`glpi_tickets_users` WHERE type = 1 GROUP BY tickets_id
) tu_req  ON tu_req.tickets_id  = t.id
LEFT JOIN (
    SELECT tickets_id, MIN(users_id) AS users_id
    FROM `glpi`.`glpi_tickets_users` WHERE type = 2 GROUP BY tickets_id
) tu_tech ON tu_tech.tickets_id = t.id
WHERE t.is_deleted = 0;


-- =============================================================================
-- DIMENSÃO: vw_dim_date
-- NOTA: A dimensão de datas é melhor criada diretamente no Power BI com DAX:
--
--   DimDate = ADDCOLUMNS(
--       CALENDAR(DATE(2024,1,1), DATE(2025,12,31)),
--       "Year",       YEAR([Date]),
--       "Month",      MONTH([Date]),
--       "MonthName",  FORMAT([Date],"MMMM"),
--       "Quarter",    QUARTER([Date]),
--       "YearMonth",  FORMAT([Date],"YYYY-MM"),
--       "IsWorkday",  IF(WEEKDAY([Date],2) <= 5, 1, 0)
--   )
--
-- Se precisar da view SQL, use uma tabela de sequência auxiliar ou
-- o recurso de generate_series do MariaDB 10.8+.
-- =============================================================================


-- =============================================================================
-- DIMENSÃO: vw_dim_category
-- Categorias ITIL com hierarquia de dois níveis.
-- =============================================================================
CREATE OR REPLACE VIEW `glpi`.`vw_dim_category` AS
SELECT
    c.id,
    c.name                                                          AS category_name,
    c.completename                                                  AS category_full_path,
    c.level,
    -- Categoria-pai (nível 1)
    CASE
        WHEN c.completename LIKE '% > %'
            THEN SUBSTRING_INDEX(c.completename, ' > ', 1)
        ELSE c.name
    END                                                             AS category_parent,
    -- Subcategoria (nível 2)
    CASE
        WHEN c.completename LIKE '% > %'
            THEN SUBSTRING_INDEX(c.completename, ' > ', -1)
        ELSE NULL
    END                                                             AS category_child,
    c.itilcategories_id                                             AS parent_id,
    CASE WHEN c.level = 1 THEN 'Categoria Raiz' ELSE 'Subcategoria' END AS category_level_label
FROM `glpi`.`glpi_itilcategories` c;


-- =============================================================================
-- DIMENSÃO: vw_dim_technician
-- Técnicos com grupo e e-mail.
-- =============================================================================
CREATE OR REPLACE VIEW `glpi`.`vw_dim_technician` AS
SELECT
    u.id,
    CONCAT(u.firstname, ' ', u.realname)                AS technician_name,
    u.firstname,
    u.realname,
    COALESCE(g.name, '(sem grupo)')                     AS team_group,
    COALESCE(g.id, 0)                                   AS group_id,
    COALESCE(em.email, '')                              AS email
FROM `glpi`.`glpi_users` u
JOIN `glpi`.`glpi_profiles_users` pu
    ON pu.users_id = u.id
JOIN `glpi`.`glpi_profiles` p
    ON p.id = pu.profiles_id
   AND p.name = 'Technician'
LEFT JOIN (
    SELECT gu.users_id, MIN(gu.groups_id) AS groups_id
    FROM `glpi`.`glpi_groups_users` gu
    GROUP BY gu.users_id
) gu2 ON gu2.users_id = u.id
LEFT JOIN `glpi`.`glpi_groups` g ON g.id = gu2.groups_id
LEFT JOIN (
    SELECT users_id, MIN(email) AS email
    FROM `glpi`.`glpi_useremails` WHERE is_default = 1 GROUP BY users_id
) em ON em.users_id = u.id
WHERE u.is_deleted = 0 AND u.is_active = 1;


-- =============================================================================
-- DIMENSÃO: vw_dim_group
-- Grupos de suporte.
-- =============================================================================
CREATE OR REPLACE VIEW `glpi`.`vw_dim_group` AS
SELECT
    id,
    name        AS group_name,
    code        AS group_code,
    comment     AS group_description
FROM `glpi`.`glpi_groups`
WHERE is_assign = 1;


-- =============================================================================
-- DIMENSÃO: vw_dim_sla
-- SLAs com tempo-alvo em minutos.
-- =============================================================================
CREATE OR REPLACE VIEW `glpi`.`vw_dim_sla` AS
SELECT
    s.id,
    s.name                              AS sla_name,
    s.number_time,
    s.definition_time,
    -- Converte para minutos (reference para calcular % de conformidade)
    CASE s.definition_time
        WHEN 'minute' THEN s.number_time
        WHEN 'hour'   THEN s.number_time * 60
        WHEN 'day'    THEN s.number_time * 1440
        ELSE               s.number_time
    END                                 AS sla_target_min,
    CASE s.type
        WHEN 0 THEN 'TTR (Tempo para Resolver)'
        WHEN 1 THEN 'TTO (Tempo para Atender)'
        ELSE        'Desconhecido'
    END                                 AS sla_type_label
FROM `glpi`.`glpi_slas` s;


-- =============================================================================
-- ANALÍTICA: vw_sla_monthly
-- Conformidade de SLA agregada por mês, grupo e prioridade.
-- Ideal para o dashboard "SLA Compliance".
-- =============================================================================
CREATE OR REPLACE VIEW `glpi`.`vw_sla_monthly` AS
SELECT
    DATE_FORMAT(t.date, '%Y-%m')    AS `year_month`,
    YEAR(t.date)                    AS `yr`,
    MONTH(t.date)                   AS `mon`,
    COALESCE(g.name, '(sem grupo)') AS group_name,
    CASE t.priority
        WHEN 1 THEN '1-Muito Baixa' WHEN 2 THEN '2-Baixa'
        WHEN 3 THEN '3-Média'       WHEN 4 THEN '4-Alta'
        WHEN 5 THEN '5-Muito Alta'  WHEN 6 THEN '6-Crítica'
        ELSE 'N/D'
    END                             AS priority_label,
    COUNT(*)                        AS total_tickets,
    SUM(CASE WHEN t.status IN (5,6) THEN 1 ELSE 0 END)  AS resolved_tickets,
    -- SLA metrics (apenas tickets com SLA definido e resolvidos)
    SUM(CASE
        WHEN t.time_to_resolve IS NOT NULL
         AND t.status IN (5,6) THEN 1 ELSE 0 END)        AS tickets_with_sla_resolved,
    SUM(CASE
        WHEN t.time_to_resolve IS NOT NULL
         AND t.status IN (5,6)
         AND t.solvedate <= t.time_to_resolve THEN 1 ELSE 0 END) AS within_sla,
    SUM(CASE
        WHEN t.time_to_resolve IS NOT NULL
         AND t.status IN (5,6)
         AND t.solvedate > t.time_to_resolve  THEN 1 ELSE 0 END) AS breached_sla,
    -- Taxa de conformidade (%)
    ROUND(
        100.0 *
        SUM(CASE WHEN t.time_to_resolve IS NOT NULL AND t.status IN (5,6) AND t.solvedate <= t.time_to_resolve THEN 1 ELSE 0 END)
        / NULLIF(SUM(CASE WHEN t.time_to_resolve IS NOT NULL AND t.status IN (5,6) THEN 1 ELSE 0 END), 0),
    2)                              AS sla_compliance_pct,
    -- MTTR médio (minutos)
    ROUND(AVG(CASE WHEN t.solvedate IS NOT NULL
        THEN TIMESTAMPDIFF(MINUTE, t.date, t.solvedate) END), 1) AS avg_resolution_min
FROM `glpi`.`glpi_tickets` t
LEFT JOIN (
    SELECT tickets_id, MIN(groups_id) AS groups_id
    FROM `glpi`.`glpi_groups_tickets` WHERE type = 2 GROUP BY tickets_id
) gt ON gt.tickets_id = t.id
LEFT JOIN `glpi`.`glpi_groups` g ON g.id = gt.groups_id
WHERE t.is_deleted = 0
GROUP BY
    DATE_FORMAT(t.date, '%Y-%m'),
    YEAR(t.date),
    MONTH(t.date),
    g.name,
    t.priority;


-- =============================================================================
-- ANALÍTICA: vw_tech_productivity
-- Produtividade do técnico por mês.
-- Ideal para o dashboard "Produtividade por Técnico".
-- =============================================================================
CREATE OR REPLACE VIEW `glpi`.`vw_tech_productivity` AS
SELECT
    DATE_FORMAT(t.date, '%Y-%m')                                AS `year_month`,
    YEAR(t.date)                                                AS `yr`,
    MONTH(t.date)                                               AS `mon`,
    CONCAT(u.firstname, ' ', u.realname)                        AS technician_name,
    u.id                                                        AS technician_id,
    COALESCE(g.name, '(sem grupo)')                             AS team_group,
    COUNT(*)                                                    AS tickets_assigned,
    SUM(CASE WHEN t.status IN (5,6) THEN 1 ELSE 0 END)          AS tickets_resolved,
    SUM(CASE WHEN t.status = 6      THEN 1 ELSE 0 END)          AS tickets_closed,
    -- MTTR do técnico (minutos)
    ROUND(AVG(CASE WHEN t.solvedate IS NOT NULL
        THEN TIMESTAMPDIFF(MINUTE, t.date, t.solvedate) END), 1) AS avg_resolution_min,
    -- % SLA compliance do técnico
    ROUND(
        100.0 *
        SUM(CASE WHEN t.time_to_resolve IS NOT NULL AND t.status IN (5,6) AND t.solvedate <= t.time_to_resolve THEN 1 ELSE 0 END)
        / NULLIF(SUM(CASE WHEN t.time_to_resolve IS NOT NULL AND t.status IN (5,6) THEN 1 ELSE 0 END), 0),
    2)                                                          AS sla_compliance_pct
FROM `glpi`.`glpi_tickets` t
JOIN (
    SELECT tickets_id, MIN(users_id) AS users_id
    FROM `glpi`.`glpi_tickets_users` WHERE type = 2 GROUP BY tickets_id
) tu ON tu.tickets_id = t.id
JOIN `glpi`.`glpi_users` u ON u.id = tu.users_id
LEFT JOIN (
    SELECT gu.users_id, MIN(g2.name) AS name
    FROM `glpi`.`glpi_groups_users` gu
    JOIN `glpi`.`glpi_groups` g2 ON g2.id = gu.groups_id
    GROUP BY gu.users_id
) g ON g.users_id = u.id
WHERE t.is_deleted = 0
GROUP BY
    DATE_FORMAT(t.date, '%Y-%m'),
    YEAR(t.date),
    MONTH(t.date),
    u.id,
    u.firstname,
    u.realname,
    g.name;


-- =============================================================================
-- ANALÍTICA: vw_backlog_open
-- Snapshot dos tickets abertos — para painel de Backlog.
-- =============================================================================
CREATE OR REPLACE VIEW `glpi`.`vw_backlog_open` AS
SELECT
    t.id                                                        AS ticket_id,
    t.name                                                      AS ticket_title,
    t.date                                                      AS created_at,
    TIMESTAMPDIFF(DAY,  t.date, NOW())                          AS age_days,
    TIMESTAMPDIFF(HOUR, t.date, NOW())                          AS age_hours,
    CASE t.status
        WHEN 1 THEN 'Novo'
        WHEN 2 THEN 'Em atendimento (atribuído)'
        WHEN 3 THEN 'Em atendimento (planejado)'
        WHEN 4 THEN 'Pendente'
    END                                                         AS status_label,
    t.priority                                                  AS priority_code,
    CASE t.priority
        WHEN 1 THEN '1-Muito Baixa' WHEN 2 THEN '2-Baixa'
        WHEN 3 THEN '3-Média'       WHEN 4 THEN '4-Alta'
        WHEN 5 THEN '5-Muito Alta'  WHEN 6 THEN '6-Crítica'
    END                                                         AS priority_label,
    COALESCE(cat.name, '(sem categoria)')                       AS category_name,
    CASE
        WHEN cat.completename LIKE '% > %'
            THEN SUBSTRING_INDEX(cat.completename, ' > ', 1)
        ELSE COALESCE(cat.name, '(sem categoria)')
    END                                                         AS category_parent,
    COALESCE(grp.name, '(sem grupo)')                           AS assigned_group,
    CONCAT(COALESCE(u.firstname,''), ' ', COALESCE(u.realname,'')) AS technician_name,
    t.time_to_resolve                                           AS sla_due_at,
    CASE
        WHEN t.time_to_resolve IS NULL  THEN 'Sem SLA'
        WHEN NOW() > t.time_to_resolve  THEN 'SLA Violado'
        WHEN TIMESTAMPDIFF(HOUR, NOW(), t.time_to_resolve) < 4
                                        THEN 'SLA Crítico (< 4h)'
        ELSE                                 'Dentro do Prazo'
    END                                                         AS sla_urgency,
    -- Minutos restantes para vencimento do SLA (negativo = já venceu)
    TIMESTAMPDIFF(MINUTE, NOW(), t.time_to_resolve)             AS sla_remaining_min
FROM `glpi`.`glpi_tickets` t
LEFT JOIN `glpi`.`glpi_itilcategories` cat
    ON cat.id = t.itilcategories_id
LEFT JOIN (
    SELECT tickets_id, MIN(groups_id) AS groups_id
    FROM `glpi`.`glpi_groups_tickets` WHERE type = 2 GROUP BY tickets_id
) gt ON gt.tickets_id = t.id
LEFT JOIN `glpi`.`glpi_groups` grp ON grp.id = gt.groups_id
LEFT JOIN (
    SELECT tickets_id, MIN(users_id) AS users_id
    FROM `glpi`.`glpi_tickets_users` WHERE type = 2 GROUP BY tickets_id
) tu ON tu.tickets_id = t.id
LEFT JOIN `glpi`.`glpi_users` u ON u.id = tu.users_id
WHERE t.is_deleted = 0
  AND t.status NOT IN (5, 6);


-- =============================================================================
-- ANALÍTICA: vw_volume_trend
-- Volume mensal de tickets criados, resolvidos e em aberto — para tendências.
-- =============================================================================
CREATE OR REPLACE VIEW `glpi`.`vw_volume_trend` AS
SELECT
    DATE_FORMAT(t.date, '%Y-%m')    AS `year_month`,
    YEAR(t.date)                    AS `yr`,
    MONTH(t.date)                   AS `mon`,
    COUNT(*)                        AS tickets_created,
    SUM(CASE WHEN t.status IN (5,6) THEN 1 ELSE 0 END) AS tickets_resolved,
    SUM(CASE WHEN t.status = 6      THEN 1 ELSE 0 END) AS tickets_closed,
    SUM(CASE WHEN t.status IN (1,2,3,4) THEN 1 ELSE 0 END) AS tickets_open,
    SUM(CASE WHEN t.type = 1        THEN 1 ELSE 0 END) AS incidents,
    SUM(CASE WHEN t.type = 2        THEN 1 ELSE 0 END) AS requests,
    ROUND(AVG(CASE WHEN t.solvedate IS NOT NULL
        THEN TIMESTAMPDIFF(MINUTE, t.date, t.solvedate) END), 1) AS avg_resolution_min
FROM `glpi`.`glpi_tickets` t
WHERE t.is_deleted = 0
GROUP BY
    DATE_FORMAT(t.date, '%Y-%m'),
    YEAR(t.date),
    MONTH(t.date)
ORDER BY DATE_FORMAT(t.date, '%Y-%m');


-- =============================================================================
-- End of vw_star_schema.sql
-- =============================================================================
