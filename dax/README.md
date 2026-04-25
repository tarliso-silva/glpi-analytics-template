# DAX Measures — GLPI Analytics Template

Este diretório contém todas as medidas DAX para o modelo Power BI, organizadas por domínio.

---

## Arquivos

| Arquivo | Domínio | Seções | Medidas |
|---|---|---|---|
| `01_core_measures.dax` | Tickets, SLA, MTTR, Backlog, Produtividade, Tendências | 1–6 | ~35 |
| `02_entity_measures.dax` | Entidades geográficas (Filiais) + Racks/DC | 7–8 | ~18 |
| `03_cmdb_measures.dax` | CMDB, Financeiro, Softwares, KB, Satisfação, ITIL, Projetos | 9–15 | ~32 |
| `measures.dax` | Arquivo combinado (legado — mantido para referência) | 1–8 | ~45 |

> **Recomendação**: use os arquivos numerados (`01_`, `02_`, `03_`) para importar por domínio no Power BI. O `measures.dax` é mantido como referência histórica.

---

## Como importar no Power BI Desktop

### Opção A — Copiar e colar
1. Abra o Power BI Desktop
2. Vá em **Modelagem → Nova Medida** (ou **Home → Enter Data**)
3. Cole o conteúdo do arquivo `.dax` diretamente no editor de fórmulas

### Opção B — Usar o Tabular Editor (recomendado)
1. Instale o [Tabular Editor 2](https://tabulareditor.com/) (gratuito)
2. Em Power BI Desktop: **External Tools → Tabular Editor**
3. No Tabular Editor: **File → Open from Power BI Desktop**
4. Arraste os arquivos `.dax` ou use **Advanced Scripting** para importar em lote

### Opção C — Script C# no Tabular Editor
```csharp
// Importa todas as medidas de um arquivo .dax
var dax = System.IO.File.ReadAllText(@"C:\path\to\01_core_measures.dax");
// Parse e cria medidas automaticamente
```

---

## Tabelas necessárias no modelo Power BI

| Tabela | Arquivo SQL | Tipo de carga |
|---|---|---|
| `vw_glpi_tickets` | `sql/vw_glpi_tickets.sql` | Import / DirectQuery |
| `vw_fact_tickets` | `sql/vw_star_schema.sql` | Import |
| `vw_dim_category` | `sql/vw_star_schema.sql` | Import |
| `vw_dim_technician` | `sql/vw_star_schema.sql` | Import |
| `vw_dim_group` | `sql/vw_star_schema.sql` | Import |
| `vw_dim_sla` | `sql/vw_star_schema.sql` | Import |
| `vw_dim_asset` | `sql/vw_star_schema.sql` | Import |
| `vw_sla_monthly` | `sql/vw_star_schema.sql` | Import |
| `vw_tech_productivity` | `sql/vw_star_schema.sql` | Import |
| `vw_backlog_open` | `sql/vw_star_schema.sql` | Import |
| `vw_volume_trend` | `sql/vw_star_schema.sql` | Import |
| `vw_fact_problems` | `sql/vw_extended_analytics.sql` | Import |
| `vw_fact_changes` | `sql/vw_extended_analytics.sql` | Import |
| `vw_fact_projects` | `sql/vw_extended_analytics.sql` | Import |
| `vw_fact_project_tasks` | `sql/vw_extended_analytics.sql` | Import |
| `vw_cmdb_summary` | `sql/vw_extended_analytics.sql` | Import |
| `vw_fact_asset_incidents` | `sql/vw_extended_analytics.sql` | Import |
| `vw_fact_software_licenses` | `sql/vw_analytics_v2.sql` | Import |
| `vw_fact_supplier_contracts` | `sql/vw_analytics_v2.sql` | Import |
| `vw_fact_asset_financials` | `sql/vw_analytics_v2.sql` | Import |
| `vw_fact_kb_usage` | `sql/vw_analytics_v2.sql` | Import |
| `vw_fact_satisfaction_summary` | `sql/vw_analytics_v2.sql` | Import |
| `vw_entity_overview` | `sql/vw_entity_analytics.sql` | Import |
| `vw_entity_sla_monthly` | `sql/vw_entity_analytics.sql` | Import |
| `vw_entity_asset_distribution` | `sql/vw_entity_analytics.sql` | Import |
| `vw_entity_project_performance` | `sql/vw_entity_analytics.sql` | Import |
| `vw_rack_inventory` | `sql/vw_entity_analytics.sql` | Import |
| `Date` | Gerada via DAX `CALENDAR()` | Calculada |

---

## Tabela de Datas (obrigatória)

Crie uma tabela de datas no Power BI com:

```dax
Date = 
ADDCOLUMNS(
    CALENDAR( DATE(2024,1,1), DATE(2026,12,31) ),
    "Year",        YEAR([Date]),
    "Month",       MONTH([Date]),
    "Month Name",  FORMAT([Date], "MMMM"),
    "Quarter",     "Q" & QUARTER([Date]),
    "Week",        WEEKNUM([Date]),
    "Weekday",     WEEKDAY([Date], 2),
    "Weekday Name",FORMAT([Date], "dddd"),
    "Is Weekend",  WEEKDAY([Date], 2) >= 6,
    "Year Month",  FORMAT([Date], "YYYY-MM")
)
```

Marque como **Tabela de Datas** em: Modelagem → Marcar como tabela de datas → coluna `Date`.
