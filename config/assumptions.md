# Project Assumptions & Configuration

This file documents the key assumptions, environment settings, and configurable parameters used in the GLPI analytics template. Update these values to match your specific GLPI deployment before running SQL views or publishing Power BI reports.

---

## 1. Database Environment

| Parameter | Default Value | Description |
|---|---|---|
| Database engine | MySQL 8.x / MariaDB 10.6+ | GLPI supports both; adjust SQL syntax if needed |
| Schema / database name | `glpi` | Replace all occurrences of `` `glpi`. `` in SQL files with your schema |
| SQL view owner | `glpi_readonly` | Read-only DB user used by Power BI to connect |
| Character set | `utf8mb4` | Assumed encoding for all text fields |

---

## 2. GLPI Version

| Parameter | Value |
|---|---|
| Assumed GLPI version | 10.x |
| Table prefix | `glpi_` (default) |

> If your GLPI installation uses a custom table prefix (set during installation), replace `glpi_` in all SQL view files with your prefix.

---

## 3. SLA Thresholds

These thresholds are used in DAX measures and may be displayed as reference lines in Power BI reports. Update them to match your SLA agreements.

| Priority | Target Resolution Time |
|---|---|
| Very Low (1) | 5 business days (7,200 min) |
| Low (2) | 3 business days (4,320 min) |
| Medium (3) | 1 business day (480 min) |
| High (4) | 4 hours (240 min) |
| Very High (5) | 2 hours (120 min) |
| Major (6) | 1 hour (60 min) |

---

## 4. Date Range

| Parameter | Default Value | Description |
|---|---|---|
| Historical data start | `2020-01-01` | Minimum date used in the Date dimension table |
| Historical data end | `2030-12-31` | Maximum date used in the Date dimension table |
| Fiscal year start month | January (1) | Change if your fiscal year starts in a different month |

---

## 5. Business Hours

Business hours affect SLA calculations when GLPI is configured to count only working hours. Document your settings here for reference:

| Parameter | Value |
|---|---|
| Working hours start | 08:00 |
| Working hours end | 18:00 |
| Working days | Monday–Friday |
| Public holiday calendar | Configured in GLPI directly |

> The SQL view currently uses wall-clock time (not business hours) for `resolution_time_minutes`. If GLPI's SLA uses business hours, rely on `glpi_tickets.time_to_resolve` (which respects GLPI's configured calendars) rather than the derived column.

---

## 6. Power BI Connection Mode

| Parameter | Recommended Value | Notes |
|---|---|---|
| Connection mode | Import | Simplest setup; scheduled refresh via Power BI Service |
| Refresh frequency | Daily (off-peak) | Adjust based on ticket volume and stakeholder needs |
| Data gateway | On-premises data gateway | Required to reach your internal GLPI database from Power BI Service |

---

## 7. Excluded Data

The following records are excluded from all SQL views by default:

| Condition | Reason |
|---|---|
| `glpi_tickets.is_deleted = 1` | Soft-deleted tickets are not relevant for operational reporting |
| Tickets with `status = 6` (Closed) older than 3 years | Configurable retention window — adjust the `WHERE` clause if needed |

---

## 8. Known Limitations

- **Multi-assignment:** When a ticket has more than one assigned technician or group, the SQL view joins to only the first matched record. Tickets with multiple assignees may appear once per assignee in some configurations.
- **Rich text content:** `ticket_description` contains raw HTML from GLPI's editor. Strip HTML tags in Power Query if plain text is needed.
- **Deleted users:** Technician/requester names will be `NULL` if the user account has been deleted from GLPI.
- **Language:** GLPI stores category names in the installation language. Status and priority labels in the SQL view are hardcoded in English; adjust `CASE` expressions if you need a different language.
