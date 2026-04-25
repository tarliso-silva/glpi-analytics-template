-- =============================================================================
-- View: vw_glpi_tickets
-- Description: Main analytics view — tabela fato desnormalizada que combina
--              tickets com usuários (via glpi_tickets_users), grupos
--              (via glpi_groups_tickets), categorias e SLA.
--              Otimizada para consumo no Power BI (sem duplicação de linhas).
--
-- Database: MySQL / MariaDB (GLPI 10.x)
-- Version:  2.0
--
-- ATENÇÃO — joins seguros contra duplicação:
--   glpi_tickets_users pode ter múltiplos registros por papel (type).
--   Usamos subconsultas com MIN() para garantir 1 linha por ticket.
--   O mesmo se aplica a glpi_groups_tickets.
-- =============================================================================

CREATE OR REPLACE VIEW `glpi`.`vw_glpi_tickets` AS
SELECT
    -- ─────────────────────────────────────────────────────────────────────────
    -- TICKET — campos principais
    -- ─────────────────────────────────────────────────────────────────────────
    t.id                                                AS ticket_id,
    t.name                                              AS ticket_title,
    t.date                                              AS created_at,
    t.solvedate                                         AS resolved_at,
    t.closedate                                         AS closed_at,
    t.takeintoaccountdate                               AS assigned_at,
    t.date_mod                                          AS last_modified_at,

    -- Ano-Mês de criação (útil para agrupamento em Power BI)
    DATE_FORMAT(t.date, '%Y-%m')                        AS created_year_month,
    YEAR(t.date)                                        AS created_year,
    MONTH(t.date)                                       AS created_month,
    QUARTER(t.date)                                     AS created_quarter,
    DAYOFWEEK(t.date)                                   AS created_weekday,

    -- ─────────────────────────────────────────────────────────────────────────
    -- STATUS
    -- ─────────────────────────────────────────────────────────────────────────
    t.status                                            AS status_code,
    CASE t.status
        WHEN 1 THEN 'Novo'
        WHEN 2 THEN 'Em atendimento (atribuído)'
        WHEN 3 THEN 'Em atendimento (planejado)'
        WHEN 4 THEN 'Pendente'
        WHEN 5 THEN 'Resolvido'
        WHEN 6 THEN 'Fechado'
        ELSE        'Desconhecido'
    END                                                 AS status_label,
    CASE WHEN t.status IN (1,2,3,4) THEN 1 ELSE 0 END  AS is_open,
    CASE WHEN t.status IN (5,6)     THEN 1 ELSE 0 END  AS is_resolved,
    CASE WHEN t.status = 6          THEN 1 ELSE 0 END  AS is_closed,

    -- ─────────────────────────────────────────────────────────────────────────
    -- PRIORIDADE
    -- ─────────────────────────────────────────────────────────────────────────
    t.priority                                          AS priority_code,
    CASE t.priority
        WHEN 1 THEN '1 - Muito Baixa'
        WHEN 2 THEN '2 - Baixa'
        WHEN 3 THEN '3 - Média'
        WHEN 4 THEN '4 - Alta'
        WHEN 5 THEN '5 - Muito Alta'
        WHEN 6 THEN '6 - Crítica'
        ELSE        'Não definida'
    END                                                 AS priority_label,

    -- ─────────────────────────────────────────────────────────────────────────
    -- TIPO DE TICKET
    -- ─────────────────────────────────────────────────────────────────────────
    t.type                                              AS ticket_type_code,
    CASE t.type
        WHEN 1 THEN 'Incidente'
        WHEN 2 THEN 'Requisição'
        ELSE        'Desconhecido'
    END                                                 AS ticket_type_label,

    -- ─────────────────────────────────────────────────────────────────────────
    -- CATEGORIA (com hierarquia)
    -- ─────────────────────────────────────────────────────────────────────────
    t.itilcategories_id                                 AS category_id,
    COALESCE(cat.name,         '(sem categoria)')       AS category_name,
    COALESCE(cat.completename, '(sem categoria)')       AS category_full_path,
    -- Categoria-pai (nível 1): extrai antes do " > "
    CASE
        WHEN cat.completename LIKE '% > %'
            THEN SUBSTRING_INDEX(cat.completename, ' > ', 1)
        ELSE COALESCE(cat.name, '(sem categoria)')
    END                                                 AS category_parent,

    -- ─────────────────────────────────────────────────────────────────────────
    -- GRUPO RESPONSÁVEL (type = 2 em glpi_groups_tickets)
    -- ─────────────────────────────────────────────────────────────────────────
    COALESCE(grp.id,   0)                               AS assigned_group_id,
    COALESCE(grp.name, '(sem grupo)')                   AS assigned_group_name,

    -- ─────────────────────────────────────────────────────────────────────────
    -- SOLICITANTE (type = 1 em glpi_tickets_users)
    -- ─────────────────────────────────────────────────────────────────────────
    req_u.id                                            AS requester_id,
    CONCAT(
        COALESCE(req_u.firstname,''), ' ',
        COALESCE(req_u.realname,'')
    )                                                   AS requester_name,
    COALESCE(req_email.email, '')                       AS requester_email,

    -- ─────────────────────────────────────────────────────────────────────────
    -- TÉCNICO RESPONSÁVEL (type = 2 em glpi_tickets_users)
    -- ─────────────────────────────────────────────────────────────────────────
    tech_u.id                                           AS technician_id,
    CONCAT(
        COALESCE(tech_u.firstname,''), ' ',
        COALESCE(tech_u.realname,'')
    )                                                   AS technician_name,
    -- Grupo do técnico (extraído via glpi_groups_users)
    COALESCE(tech_grp.name, '(sem grupo)')              AS technician_group,

    -- ─────────────────────────────────────────────────────────────────────────
    -- SLA
    -- ─────────────────────────────────────────────────────────────────────────
    t.slas_id_ttr                                       AS sla_id,
    COALESCE(sla.name, 'Sem SLA')                       AS sla_name,
    t.time_to_resolve                                   AS sla_due_at,

    -- Status do SLA (campo calculado central para dashboards)
    CASE
        WHEN t.time_to_resolve IS NULL
            THEN 'Sem SLA'
        WHEN t.status IN (5, 6) AND t.solvedate <= t.time_to_resolve
            THEN 'Dentro do SLA'
        WHEN t.status IN (5, 6) AND t.solvedate >  t.time_to_resolve
            THEN 'Violado'
        WHEN t.status NOT IN (5, 6) AND NOW() >  t.time_to_resolve
            THEN 'Violado (aberto)'
        WHEN t.status NOT IN (5, 6) AND NOW() <= t.time_to_resolve
            THEN 'Em risco'
        ELSE 'Sem SLA'
    END                                                 AS sla_status,

    -- Flag binário de conformidade (1 = dentro do SLA)
    CASE
        WHEN t.time_to_resolve IS NULL THEN NULL
        WHEN t.status IN (5,6) AND t.solvedate <= t.time_to_resolve THEN 1
        WHEN t.status IN (5,6) AND t.solvedate >  t.time_to_resolve THEN 0
        ELSE NULL
    END                                                 AS sla_compliant,

    -- ─────────────────────────────────────────────────────────────────────────
    -- MÉTRICAS DE TEMPO (em minutos — base para MTTR, MTTR por prioridade etc.)
    -- ─────────────────────────────────────────────────────────────────────────
    -- Tempo até a resolução
    CASE
        WHEN t.solvedate IS NOT NULL
            THEN TIMESTAMPDIFF(MINUTE, t.date, t.solvedate)
        ELSE NULL
    END                                                 AS resolution_time_min,

    -- Tempo até o fechamento
    CASE
        WHEN t.closedate IS NOT NULL
            THEN TIMESTAMPDIFF(MINUTE, t.date, t.closedate)
        ELSE NULL
    END                                                 AS closure_time_min,

    -- Tempo até o primeiro atendimento (Time to Own)
    CASE
        WHEN t.takeintoaccountdate IS NOT NULL
            THEN TIMESTAMPDIFF(MINUTE, t.date, t.takeintoaccountdate)
        ELSE NULL
    END                                                 AS time_to_own_min,

    -- Tempo aberto até agora (tickets ainda não resolvidos)
    CASE
        WHEN t.status NOT IN (5,6)
            THEN TIMESTAMPDIFF(MINUTE, t.date, NOW())
        ELSE NULL
    END                                                 AS age_open_min,

    -- Campos de estatística pré-calculados pelo GLPI (em segundos → convertidos)
    ROUND(t.solve_delay_stat  / 60.0, 2)                AS solve_delay_min,
    ROUND(t.close_delay_stat  / 60.0, 2)                AS close_delay_min

FROM `glpi`.`glpi_tickets` t

-- ─── Categoria ────────────────────────────────────────────────────────────────
LEFT JOIN `glpi`.`glpi_itilcategories` cat
    ON cat.id = t.itilcategories_id

-- ─── Grupo responsável (sem duplicação: 1 registro por ticket) ───────────────
LEFT JOIN (
    SELECT tickets_id, MIN(groups_id) AS groups_id
    FROM   `glpi`.`glpi_groups_tickets`
    WHERE  type = 2
    GROUP  BY tickets_id
) gt ON gt.tickets_id = t.id
LEFT JOIN `glpi`.`glpi_groups` grp ON grp.id = gt.groups_id

-- ─── Solicitante (type = 1, sem duplicação) ──────────────────────────────────
LEFT JOIN (
    SELECT tickets_id, MIN(users_id) AS users_id
    FROM   `glpi`.`glpi_tickets_users`
    WHERE  type = 1
    GROUP  BY tickets_id
) tu_req ON tu_req.tickets_id = t.id
LEFT JOIN `glpi`.`glpi_users` req_u
    ON req_u.id = tu_req.users_id
LEFT JOIN (
    SELECT users_id, MIN(email) AS email
    FROM   `glpi`.`glpi_useremails`
    WHERE  is_default = 1
    GROUP  BY users_id
) req_email ON req_email.users_id = req_u.id

-- ─── Técnico responsável (type = 2, sem duplicação) ──────────────────────────
LEFT JOIN (
    SELECT tickets_id, MIN(users_id) AS users_id
    FROM   `glpi`.`glpi_tickets_users`
    WHERE  type = 2
    GROUP  BY tickets_id
) tu_tech ON tu_tech.tickets_id = t.id
LEFT JOIN `glpi`.`glpi_users` tech_u
    ON tech_u.id = tu_tech.users_id
LEFT JOIN (
    SELECT gu.users_id, MIN(g.name) AS name
    FROM   `glpi`.`glpi_groups_users` gu
    JOIN   `glpi`.`glpi_groups` g ON g.id = gu.groups_id
    GROUP  BY gu.users_id
) tech_grp ON tech_grp.users_id = tech_u.id

-- ─── SLA ─────────────────────────────────────────────────────────────────────
LEFT JOIN `glpi`.`glpi_slas` sla
    ON sla.id = t.slas_id_ttr

WHERE t.is_deleted = 0;

-- =============================================================================
-- End of vw_glpi_tickets.sql  (v2.0)
-- =============================================================================
