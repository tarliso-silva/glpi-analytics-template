# Power BI — Especificações de Páginas (Storytelling)

Este diretório contém as especificações detalhadas para cada página do relatório Power BI.

---

## Filosofia de Storytelling

O relatório segue um fluxo narrativo em **funil de análise**:

```
p01 Overview (Onde estamos?)
  └─► p02 SLA Analysis (Onde estamos falhando?)
        └─► p03 Ticket Operations (O que está gerando mais volume?)
              └─► p04 Productivity (Quem está performando?)
                    └─► p05 Trends (Quando os problemas ocorrem?)
                          └─► p06 Entity/Geographic (Onde geograficamente?)
                                └─► p07 CMDB Assets (Quais ativos causam incidentes?)
                                      └─► p08 Storytelling Flow (resumo executivo)
```

Cada página tem:
- **Drill-through** para a página de detalhe relevante
- **Tooltip personalizado** com contexto adicional
- **Filtro de período** sincronizado (usando `vw_dim_date` como slicer mestre)
- **Botão de navegação** para a próxima página da narrativa

---

## Páginas

| # | Arquivo | Título | Público-alvo |
|---|---|---|---|
| 1 | [p01_overview.md](p01_overview.md) | Overview Executivo | C-level, Gestores |
| 2 | [p02_sla_analysis.md](p02_sla_analysis.md) | Desempenho de SLA | Gestores de TI |
| 3 | [p03_ticket_operations.md](p03_ticket_operations.md) | Operações de Tickets | Coordenadores |
| 4 | [p04_productivity.md](p04_productivity.md) | Produtividade das Equipes | Supervisores |
| 5 | [p05_trends.md](p05_trends.md) | Tendências & Padrões | Analistas |
| 6 | [p06_entity_geographic.md](p06_entity_geographic.md) | Visão por Filial | Diretores regionais |
| 7 | [p07_cmdb_assets.md](p07_cmdb_assets.md) | CMDB & Ativos | Especialistas |
| 8 | [p08_storytelling_flow.md](p08_storytelling_flow.md) | Fluxo Narrativo | Todos |

---

## Views SQL utilizadas por página

| View | p01 | p02 | p03 | p04 | p05 | p06 | p07 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `vw_fact_tickets` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | |
| `vw_glpi_tickets` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | |
| `vw_sla_monthly` | ✓ | ✓ | | | ✓ | | |
| `vw_entity_overview` | | | | | | ✓ | |
| `vw_entity_sla_monthly` | | ✓ | | | | ✓ | |
| `vw_tech_productivity` | | | | ✓ | | | |
| `vw_backlog_open` | ✓ | | ✓ | | | | |
| `vw_volume_trend` | | | | | ✓ | | |
| `vw_fact_problems` | | | ✓ | | | | |
| `vw_fact_changes` | | | ✓ | | | | |
| `vw_cmdb_summary` | | | | | | | ✓ |
| `vw_dim_asset` | | | | | | | ✓ |
| `vw_fact_asset_incidents` | | | | | | | ✓ |
| `vw_rack_inventory` | | | | | | | ✓ |
| `vw_fact_software_licenses` | | | | | | | ✓ |
