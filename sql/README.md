# SQL Views — GLPI Analytics

Este diretório contém todas as views SQL que formam a camada analítica entre o banco de dados GLPI e o Power BI.

---

## Ordem de aplicação

Execute nesta ordem (dependências entre views):

```bash
python pipeline/deploy_views.py
```

Ou manualmente na sequência:

| # | Arquivo | Descrição | Views criadas |
|---|---|---|---|
| 1 | `vw_glpi_tickets.sql` | View principal de tickets com todas as dimensões joined | `vw_glpi_tickets` |
| 2 | `vw_star_schema.sql` | Star schema completo (fact + dims + agregações) | `vw_fact_tickets`, `vw_dim_*`, `vw_sla_monthly`, `vw_tech_productivity`, `vw_backlog_open`, `vw_volume_trend` |
| 3 | `vw_extended_analytics.sql` | CMDB, problemas, mudanças, projetos | `vw_fact_problems`, `vw_fact_changes`, `vw_fact_projects`, `vw_fact_project_tasks`, `vw_cmdb_summary`, `vw_fact_asset_*` |
| 4 | `vw_analytics_v2.sql` | Softwares, contratos, financeiro, KB, satisfação | `vw_fact_software_licenses`, `vw_fact_supplier_contracts`, `vw_fact_asset_financials`, `vw_fact_kb_usage`, `vw_fact_satisfaction_summary` |
| 5 | `vw_entity_analytics.sql` | Entidades geográficas + racks | `vw_entity_overview`, `vw_entity_sla_monthly`, `vw_entity_asset_distribution`, `vw_entity_project_performance`, `vw_rack_inventory` |

**Total: 32 views**

---

## Inventário completo de views

### Grupo 1 — Tickets (base)
| View | Linhas (dataset demo) | Descrição |
|---|---|---|
| `vw_glpi_tickets` | 1.071 | Tickets com joins completos: usuário, grupo, categoria, SLA, entidade |

### Grupo 2 — Star Schema
| View | Linhas | Descrição |
|---|---|---|
| `vw_fact_tickets` | 1.071 | Fato de tickets normalizado para star schema |
| `vw_fact_ticket_enrichment` | 1.071 | Enriquecimento: follow-ups, tasks, satisfação |
| `vw_dim_category` | 26 | Dimensão de categorias ITIL |
| `vw_dim_technician` | 11 | Dimensão de técnicos |
| `vw_dim_group` | 3 | Dimensão de grupos/equipes |
| `vw_dim_sla` | 6 | Dimensão de SLAs por prioridade |
| `vw_dim_asset` | 115 | Dimensão de ativos CMDB |
| `vw_dim_software` | 28 | Dimensão de softwares |
| `vw_dim_supplier` | 8 | Dimensão de fornecedores |
| `vw_dim_os_inventory` | 65 | Inventário de sistemas operacionais |
| `vw_sla_monthly` | 301 | Conformidade SLA agregada por mês e prioridade |
| `vw_tech_productivity` | 245 | Produtividade por técnico e mês |
| `vw_backlog_open` | 88 | Tickets abertos com idade em dias |
| `vw_volume_trend` | 24 | Tendência de volume por mês |

### Grupo 3 — Analytics Estendida (CMDB, ITIL)
| View | Linhas | Descrição |
|---|---|---|
| `vw_fact_problems` | 25 | Problemas com tickets vinculados |
| `vw_fact_changes` | 18 | Mudanças com tickets e tarefas |
| `vw_fact_projects` | 6 | Projetos com status e datas |
| `vw_fact_project_tasks` | 36 | Tarefas de projetos |
| `vw_cmdb_summary` | 61 | Resumo CMDB por tipo de ativo |
| `vw_fact_asset_tickets` | 303 | Tickets vinculados a ativos |
| `vw_fact_asset_incidents` | 88 | Incidentes por ativo CMDB |

### Grupo 4 — Analytics v2 (Financeiro, SW, KB)
| View | Linhas | Descrição |
|---|---|---|
| `vw_fact_software_licenses` | 28 | Licenças vs. instalações |
| `vw_fact_supplier_contracts` | 8 | Contratos com fornecedores |
| `vw_fact_asset_financials` | 77 | Valores financeiros dos ativos |
| `vw_fact_kb_usage` | 18 | Uso da base de conhecimento |
| `vw_fact_satisfaction_summary` | 74 | Avaliações de satisfação |

### Grupo 5 — Entidades & Racks
| View | Linhas | Descrição |
|---|---|---|
| `vw_entity_overview` | 5 | Resumo por entidade (tickets, usuários, ativos, MTTR) |
| `vw_entity_sla_monthly` | 96 | SLA por entidade e mês |
| `vw_entity_asset_distribution` | 16 | Ativos por tipo e entidade com valor |
| `vw_entity_project_performance` | 6 | Projetos por entidade |
| `vw_rack_inventory` | 27 | Inventário completo dos racks |

---

## Requisitos

- MariaDB 10.7+ ou MySQL 8.0+
- Schema `glpi` com GLPI 10.x instalado
- Usuário com permissão `SELECT` em todas as tabelas `glpi_*`

## Quirks do schema GLPI validados

| Problema | Solução aplicada |
|---|---|
| `glpi_entities` sem `is_recursive` | Coluna não existe — recursividade está nos itens |
| `glpi_items_racks` sem `date_mod`/`date_creation` | Colunas omitidas |
| `year_month` é palavra reservada | Envolvido em backticks `` `year_month` `` |
| `glpi_users.login` não existe | Usar `glpi_users.name` |
| MariaDB não suporta `WITH RECURSIVE` | Substituído por joins diretos |
| `GROUP BY` não aceita aliases em views | Expressões repetidas no GROUP BY |
