# Data Model — GLPI Analytics Template

This document describes the logical data model used in the GLPI Power BI analytics template, maps GLPI database tables to the analytics layer, and defines all fields exposed in the SQL views.

---

## 1. Overview

GLPI stores ITSM data across dozens of relational tables. The analytics layer simplifies this by exposing a small number of wide, pre-joined **SQL views** that Power BI can consume directly. The data model inside Power BI consists of these views plus a shared **Date dimension table**.

```
┌─────────────────────┐      ┌──────────────────────────┐
│  vw_glpi_tickets    │◄─────│  Date (dimension table)  │
│  (fact-like view)   │      │  generated in Power BI   │
└─────────────────────┘      └──────────────────────────┘
```

> The current template exposes a single primary view (`vw_glpi_tickets`). Additional views (assets, changes, problems, users) can be added following the same pattern.

---

## 2. Source Tables (GLPI Database)

| GLPI Table | Description |
|---|---|
| `glpi_tickets` | Core ticket table — one row per ticket |
| `glpi_tickets_users` | Links tickets to users with role types (requester=1, assigned=2) |
| `glpi_groups_tickets` | Links tickets to groups with role types |
| `glpi_users` | GLPI user accounts |
| `glpi_groups` | GLPI groups / support teams |
| `glpi_itilcategories` | Ticket categories (hierarchical) |
| `glpi_slms` | SLA definitions |
| `glpi_slas` | SLA levels linked to ticket types and priorities |

---

## 3. Analytics View: `vw_glpi_tickets`

**Location:** `sql/vw_glpi_tickets.sql`

This is the primary fact-like view that flattens ticket data for Power BI consumption.

### 3.1 Field Dictionary

| Field | Data Type | Source | Description |
|---|---|---|---|
| `ticket_id` | Integer | `glpi_tickets.id` | Unique ticket identifier |
| `ticket_title` | String | `glpi_tickets.name` | Short ticket title |
| `ticket_description` | String | `glpi_tickets.content` | Full ticket body (HTML) |
| `created_at` | DateTime | `glpi_tickets.date` | When the ticket was created |
| `resolved_at` | DateTime | `glpi_tickets.solvedate` | When the ticket was resolved |
| `closed_at` | DateTime | `glpi_tickets.closedate` | When the ticket was closed |
| `last_modified_at` | DateTime | `glpi_tickets.date_mod` | Last modification timestamp |
| `status_code` | Integer | `glpi_tickets.status` | Raw GLPI status code (1–6) |
| `status_label` | String | Derived | Human-readable status (e.g. "New", "Solved") |
| `priority_code` | Integer | `glpi_tickets.priority` | Raw GLPI priority code (1–6) |
| `priority_label` | String | Derived | Human-readable priority (e.g. "High", "Critical") |
| `ticket_type` | String | `glpi_tickets.type` | "Incident" or "Request" |
| `category_id` | Integer | `glpi_itilcategories.id` | Ticket category ID |
| `category_name` | String | `glpi_itilcategories.name` | Category short name |
| `category_full_path` | String | `glpi_itilcategories.completename` | Full hierarchical category path |
| `assigned_group_id` | Integer | `glpi_groups.id` | ID of the assigned support group |
| `assigned_group_name` | String | `glpi_groups.name` | Name of the assigned support group |
| `requester_id` | Integer | `glpi_users.id` | User who opened the ticket |
| `requester_name` | String | `glpi_users.firstname + realname` | Full name of the requester |
| `requester_email` | String | `glpi_users.email` | Requester's email address |
| `technician_id` | Integer | `glpi_users.id` | Assigned technician's user ID |
| `technician_name` | String | `glpi_users.firstname + realname` | Full name of the assigned technician |
| `sla_due_at` | DateTime | `glpi_tickets.time_to_resolve` | SLA deadline for resolution |
| `sla_status` | String | Derived | "Within SLA", "Breached", "At risk", "No SLA" |
| `resolution_time_minutes` | Integer | Derived | Minutes from creation to resolution |
| `closure_time_minutes` | Integer | Derived | Minutes from creation to closure |

### 3.2 Status Code Mapping

| Code | Label |
|---|---|
| 1 | New |
| 2 | Processing (assigned) |
| 3 | Processing (planned) |
| 4 | Pending |
| 5 | Solved |
| 6 | Closed |

### 3.3 Priority Code Mapping

| Code | Label |
|---|---|
| 1 | Very Low |
| 2 | Low |
| 3 | Medium |
| 4 | High |
| 5 | Very High |
| 6 | Major |

---

## 4. Date Dimension Table

The **Date** table is a standard calendar dimension that should be created inside Power BI Desktop using DAX or loaded from a CSV. It enables time intelligence functions (MoM, YoY, period comparisons).

### Recommended Columns

| Column | Type | Description |
|---|---|---|
| `Date` | Date | Primary key — one row per calendar day |
| `Year` | Integer | Calendar year (e.g. 2024) |
| `Month` | Integer | Month number (1–12) |
| `MonthName` | String | Full month name (e.g. "January") |
| `Quarter` | Integer | Quarter number (1–4) |
| `WeekNumber` | Integer | ISO week number |
| `DayOfWeek` | Integer | Day of week (1=Monday … 7=Sunday) |
| `IsWeekend` | Boolean | True if Saturday or Sunday |
| `IsWorkingDay` | Boolean | True if not a weekend or public holiday |

### Sample DAX to Generate a Date Table

```dax
Date =
VAR StartDate = DATE( 2020, 1, 1 )
VAR EndDate   = DATE( 2030, 12, 31 )
RETURN
    ADDCOLUMNS(
        CALENDAR( StartDate, EndDate ),
        "Year",       YEAR( [Date] ),
        "Month",      MONTH( [Date] ),
        "MonthName",  FORMAT( [Date], "MMMM" ),
        "Quarter",    QUARTER( [Date] ),
        "WeekNumber", WEEKNUM( [Date], 2 ),
        "DayOfWeek",  WEEKDAY( [Date], 2 ),
        "IsWeekend",  WEEKDAY( [Date], 2 ) >= 6
    )
```

---

## 5. Relationships

| From Table | From Column | To Table | To Column | Cardinality | Active? |
|---|---|---|---|---|---|
| `vw_glpi_tickets` | `created_at` | `Date` | `Date` | Many-to-One | ✅ Yes |
| `vw_glpi_tickets` | `resolved_at` | `Date` | `Date` | Many-to-One | ❌ No (use USERELATIONSHIP) |
| `vw_glpi_tickets` | `closed_at` | `Date` | `Date` | Many-to-One | ❌ No (use USERELATIONSHIP) |

> In Power BI, only one relationship per table pair can be active. The inactive relationships are activated selectively inside individual measures using `USERELATIONSHIP()`.

---

## 6. Extending the Model

To add new analytics areas, follow this pattern:

1. **Add a SQL view** in `/sql/` (e.g. `vw_glpi_assets.sql`, `vw_glpi_changes.sql`).
2. **Add the view** to the Power BI data source and create the necessary relationships.
3. **Add DAX measures** in `/dax/measures.dax` following the existing naming convention.
4. **Update this document** with the new view's field dictionary.

---

## 7. Glossary

| Term | Definition |
|---|---|
| **GLPI** | Gestionnaire Libre de Parc Informatique — open-source ITSM/ITAM system |
| **SLA** | Service Level Agreement — defines maximum resolution time per ticket priority |
| **MTTR** | Mean Time To Resolve — average duration from ticket creation to resolution |
| **Backlog** | Tickets that are open beyond their expected resolution time |
| **DAX** | Data Analysis Expressions — formula language used in Power BI |
| **View (SQL)** | A virtual table defined by a SQL query, used to simplify Power BI data access |
