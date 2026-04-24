# GLPI Analytics Template

A reusable analytics template for **GLPI** (IT Service Management system) focused on **Power BI** integration. This project provides a structured foundation for building dashboards and reports on top of GLPI data, covering SLA compliance, ticket backlog, agent productivity, and overall Service Desk operations.

> **Important:** This is a pure analytics template — it contains no application code or web frameworks. All deliverables are SQL views, DAX measures, Power BI templates, and documentation.

---

## 📁 Folder Structure

```
glpi-analytics-template/
├── sql/          # SQL views for extracting and transforming GLPI data
├── dax/          # DAX measure files for Power BI calculations
├── powerbi/      # Power BI template files (.pbit) and layout references
├── docs/         # Data model documentation and usage guides
├── config/       # Project assumptions, environment settings, and configuration
└── src/          # Optional helper scripts (e.g., Python/PowerShell for data refresh)
```

---

## 🎯 Purpose

GLPI stores all ITSM data (tickets, assets, users, SLAs, etc.) in a relational database. This template bridges that raw data with Power BI by providing:

- **SQL Views** — pre-built queries that flatten and clean GLPI tables for BI consumption.
- **DAX Measures** — reusable calculations for KPIs such as SLA breach rate, MTTR, first-call resolution, and ticket volume trends.
- **Power BI Templates** — `.pbit` starter files with pre-configured data sources, relationships, and report pages.
- **Documentation** — a data model guide that maps GLPI tables to the analytics layer.
- **Configuration** — a central place to record assumptions (date ranges, priority mappings, SLA thresholds, etc.).

---

## 🚀 Getting Started

### Prerequisites

- GLPI (version 10.x recommended) with database access (MySQL/MariaDB)
- Power BI Desktop (free download from Microsoft)
- Read-only database credentials for the GLPI schema

### Setup Steps

1. **Create the SQL views** — run the scripts in `/sql` against your GLPI database to create the analytics views.
2. **Connect Power BI** — open the `.pbit` template in `/powerbi` and point it at your GLPI database (or use DirectQuery / Import mode as appropriate).
3. **Review DAX measures** — the measures in `/dax` are already embedded in the template; review and adjust thresholds to match your SLA agreements.
4. **Read the docs** — consult `/docs/data-model.md` to understand table relationships and field definitions.
5. **Adjust configuration** — update `/config/assumptions.md` with your environment-specific settings (database name, SLA targets, fiscal calendar, etc.).

---

## 📊 Key Analytics Areas

| Area | Description |
|------|-------------|
| **SLA Compliance** | % of tickets resolved within agreed time windows, broken down by priority and category |
| **Ticket Backlog** | Open ticket age distribution, queue depth over time |
| **Agent Productivity** | Tickets closed per agent per period, reassignment rate |
| **Category Analysis** | Volume and resolution time by ticket category/subcategory |
| **Trend Analysis** | Week-over-week and month-over-month ticket volume trends |

---

## 📂 File Inventory

| Path | Description |
|------|-------------|
| `sql/vw_glpi_tickets.sql` | Main SQL view combining ticket, user, group, and SLA data |
| `dax/measures.dax` | Core DAX measures (SLA rate, MTTR, open/closed counts, etc.) |
| `powerbi/README.md` | Instructions for using the Power BI template files |
| `docs/data-model.md` | Entity-relationship overview and field dictionary |
| `config/assumptions.md` | Project assumptions, SLA thresholds, and environment notes |
| `src/README.md` | Guide for optional data refresh / ETL helper scripts |

---

## 🤝 Contributing

1. Fork the repository.
2. Add or improve SQL views in `/sql`, DAX measures in `/dax`, or documentation in `/docs`.
3. Open a pull request with a clear description of what was changed and why.

---

## 📄 License

This project is released under the [MIT License](LICENSE).

