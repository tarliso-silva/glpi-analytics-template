-- =============================================================================
-- View: vw_glpi_tickets
-- Description: Main analytics view combining ticket, user, group, category,
--              and SLA data from GLPI for use in Power BI reports.
-- Database: MySQL / MariaDB (GLPI schema)
-- Version: 1.0
-- =============================================================================
-- USAGE:
--   Run this script against your GLPI database (e.g. `glpi`) as a user that
--   has SELECT privileges on all referenced tables and CREATE VIEW privilege.
--   Replace `glpi` with your actual schema name if different.
-- =============================================================================

CREATE OR REPLACE VIEW `glpi`.`vw_glpi_tickets` AS
SELECT
    -- -------------------------------------------------------------------------
    -- Ticket core fields
    -- -------------------------------------------------------------------------
    t.id                        AS ticket_id,
    t.name                      AS ticket_title,
    t.content                   AS ticket_description,
    t.date                      AS created_at,
    t.closedate                 AS closed_at,
    t.solvedate                 AS resolved_at,
    t.date_mod                  AS last_modified_at,

    -- Status mapping (GLPI status codes → human-readable labels)
    CASE t.status
        WHEN 1 THEN 'New'
        WHEN 2 THEN 'Processing (assigned)'
        WHEN 3 THEN 'Processing (planned)'
        WHEN 4 THEN 'Pending'
        WHEN 5 THEN 'Solved'
        WHEN 6 THEN 'Closed'
        ELSE 'Unknown'
    END                         AS status_label,
    t.status                    AS status_code,

    -- Priority mapping
    CASE t.priority
        WHEN 1 THEN 'Very Low'
        WHEN 2 THEN 'Low'
        WHEN 3 THEN 'Medium'
        WHEN 4 THEN 'High'
        WHEN 5 THEN 'Very High'
        WHEN 6 THEN 'Major'
        ELSE 'Not defined'
    END                         AS priority_label,
    t.priority                  AS priority_code,

    -- Ticket type (Incident vs Request)
    CASE t.type
        WHEN 1 THEN 'Incident'
        WHEN 2 THEN 'Request'
        ELSE 'Unknown'
    END                         AS ticket_type,

    -- -------------------------------------------------------------------------
    -- Category
    -- -------------------------------------------------------------------------
    cat.id                      AS category_id,
    cat.name                    AS category_name,
    cat.completename            AS category_full_path,

    -- -------------------------------------------------------------------------
    -- Assigned group
    -- -------------------------------------------------------------------------
    grp.id                      AS assigned_group_id,
    grp.name                    AS assigned_group_name,

    -- -------------------------------------------------------------------------
    -- Requester (ticket author)
    -- -------------------------------------------------------------------------
    req_user.id                 AS requester_id,
    CONCAT(
        req_user.firstname, ' ', req_user.realname
    )                           AS requester_name,
    req_user.email              AS requester_email,

    -- -------------------------------------------------------------------------
    -- Assigned technician
    -- -------------------------------------------------------------------------
    tech_user.id                AS technician_id,
    CONCAT(
        tech_user.firstname, ' ', tech_user.realname
    )                           AS technician_name,

    -- -------------------------------------------------------------------------
    -- SLA fields
    -- -------------------------------------------------------------------------
    t.time_to_resolve           AS sla_due_at,
    CASE
        -- No SLA defined — must be checked first to avoid NULL comparisons below
        WHEN t.time_to_resolve IS NULL
            THEN 'No SLA'
        -- Resolved/closed tickets: compare resolution date against SLA deadline
        WHEN t.status IN (5, 6) AND t.solvedate <= t.time_to_resolve
            THEN 'Within SLA'
        WHEN t.status IN (5, 6) AND t.solvedate > t.time_to_resolve
            THEN 'Breached'
        -- Open tickets: compare current time against SLA deadline
        WHEN t.status NOT IN (5, 6) AND NOW() > t.time_to_resolve
            THEN 'Breached (open)'
        WHEN t.status NOT IN (5, 6) AND NOW() <= t.time_to_resolve
            THEN 'At risk'
        ELSE 'No SLA'
    END                         AS sla_status,

    -- -------------------------------------------------------------------------
    -- Derived duration metrics (in minutes)
    -- -------------------------------------------------------------------------
    CASE
        WHEN t.solvedate IS NOT NULL
            THEN TIMESTAMPDIFF(MINUTE, t.date, t.solvedate)
        ELSE NULL
    END                         AS resolution_time_minutes,

    CASE
        WHEN t.closedate IS NOT NULL
            THEN TIMESTAMPDIFF(MINUTE, t.date, t.closedate)
        ELSE NULL
    END                         AS closure_time_minutes

FROM
    `glpi`.`glpi_tickets` t

-- Category (left join — tickets may have no category)
LEFT JOIN `glpi`.`glpi_itilcategories` cat
    ON cat.id = t.itilcategories_id

-- Assigned group (via ticket-group link, role 2 = assigned)
LEFT JOIN `glpi`.`glpi_groups_tickets` gt
    ON gt.tickets_id = t.id
   AND gt.type = 2          -- 1 = requester, 2 = assigned
LEFT JOIN `glpi`.`glpi_groups` grp
    ON grp.id = gt.groups_id

-- Requester user (role 1 in ticket-user link)
LEFT JOIN `glpi`.`glpi_tickets_users` tu_req
    ON tu_req.tickets_id = t.id
   AND tu_req.type = 1      -- 1 = requester
LEFT JOIN `glpi`.`glpi_users` req_user
    ON req_user.id = tu_req.users_id

-- Assigned technician user (role 2 in ticket-user link)
LEFT JOIN `glpi`.`glpi_tickets_users` tu_tech
    ON tu_tech.tickets_id = t.id
   AND tu_tech.type = 2     -- 2 = assigned
LEFT JOIN `glpi`.`glpi_users` tech_user
    ON tech_user.id = tu_tech.users_id

-- Exclude deleted tickets
WHERE
    t.is_deleted = 0;

-- =============================================================================
-- End of vw_glpi_tickets.sql
-- =============================================================================
