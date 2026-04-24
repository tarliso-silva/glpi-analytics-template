# Power BI Templates

This folder contains Power BI template files (`.pbit`) and supporting assets for the GLPI analytics template.

---

## What Is a `.pbit` File?

A Power BI Template file (`.pbit`) is a portable file that contains:
- The **data model** (table relationships, column types, hierarchies)
- All **DAX measures** from `/dax/measures.dax`
- Pre-built **report pages** (dashboards, charts, tables)
- **No actual data** — data is loaded fresh each time the template is opened

When you open a `.pbit` file in Power BI Desktop, it will prompt you for connection parameters (server, database name, credentials) and then load data from your GLPI database.

---

## Files in This Folder

| File | Description | Status |
|---|---|---|
| `glpi_analytics.pbit` | Main analytics template (SLA, backlog, productivity pages) | _Placeholder — add your `.pbit` export here_ |

> **To generate the `.pbit` file:** Build your report in Power BI Desktop, then go to **File → Export → Power BI Template**, provide a description, and save the file to this folder.

---

## Getting Started with the Template

1. Install **Power BI Desktop** (free from [microsoft.com/powerbi](https://powerbi.microsoft.com/desktop/)).
2. Run `sql/vw_glpi_tickets.sql` against your GLPI database to create the analytics view.
3. Open `glpi_analytics.pbit` from this folder.
4. When prompted, enter:
   - **Server:** your MySQL/MariaDB server hostname or IP
   - **Database:** your GLPI schema name (default: `glpi`)
5. Enter read-only credentials when asked.
6. Click **Load** — Power BI will import the data and apply all pre-built measures and visuals.

---

## Recommended Report Pages

The template is designed to include the following report pages:

| Page | Key Visuals |
|---|---|
| **Overview** | KPI cards: total tickets, open tickets, SLA rate, MTTR |
| **SLA Analysis** | SLA compliance by priority, category, group; breach trend |
| **Backlog** | Open ticket age distribution; backlog by group/category |
| **Productivity** | Tickets closed per technician; workload heatmap |
| **Trends** | Month-over-month ticket volume; rolling averages |

---

## Tips

- Use **Import mode** for most deployments (data is cached, fast rendering).
- Use **DirectQuery mode** only if you need near-real-time data and your database can handle the query load.
- Schedule automatic refresh via **Power BI Service** with an **On-Premises Data Gateway** if your GLPI database is behind a firewall.
