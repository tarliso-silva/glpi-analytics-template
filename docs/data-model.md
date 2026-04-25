# Modelo de Dados â€” GLPI Analytics Template

Este documento descreve o modelo de dados analÃ­tico completo: as 33 SQL views, os 24
relacionamentos do Power BI, a hierarquia de entidades e as limitaÃ§Ãµes tÃ©cnicas do ambiente.

---

## 1. Ambiente TÃ©cnico

| Componente | VersÃ£o / Detalhe |
|---|---|
| GLPI | 10.x |
| Banco de dados | MariaDB 10.7 (Docker â€” container `glpi-mysql`) |
| Host / Porta | `localhost:3306` |
| Schema | `glpi` |
| Credenciais (demo) | usuÃ¡rio `glpi` / senha `glpi` |
| Conector Power BI | **MySQL Connector/NET 8.0.33** (obrigatÃ³rio â€” 9.x incompatÃ­vel) |
| Driver Power BI | **Banco de dados MySQL** (nÃ£o use MariaDB connector) |
| Python | 3.11+ Â· sempre use `.venv\Scripts\python.exe` (caminho completo) |

### Containers Docker

| Container | Imagem | Porta |
|---|---|---|
| `glpi-app` | GLPI 10.x | 8080 |
| `glpi-mysql` | MariaDB 10.7 | 3306 |
| `dw-postgres` | PostgreSQL | 5432 |

### LimitaÃ§Ãµes do MariaDB 10.7 (crÃ­ticas para SQL views)

| LimitaÃ§Ã£o | Impacto |
|---|---|
| Sem `WITH RECURSIVE` | NÃ£o use CTEs recursivos â€” construa a dimensÃ£o de datas via DAX no Power BI |
| `GROUP BY` nÃ£o aceita aliases | Repita as expressÃµes no `GROUP BY` ou use subconsultas |
| `year_month` Ã© palavra reservada | Envolva sempre em backticks: `` `year_month` `` |
| `glpi_entities` sem `is_recursive` | A recursividade Ã© definida nos itens, nÃ£o na entidade |
| `glpi_items_racks` sem `date_mod`/`date_creation` | NÃ£o use estas colunas na view de racks |

---

## 2. Hierarquia de Entidades

```
Empresa (id=0)                          â† raiz corporativa
â”œâ”€ Matriz       (id=4, level=2)         â† sede SP â€” TI, infra, ITSM
â”œâ”€ Filial SP    (id=5, level=2)         â† operaÃ§Ãµes regionais SP
â”œâ”€ Filial RJ    (id=6, level=2)         â† operaÃ§Ãµes Rio de Janeiro
â””â”€ Filial MG    (id=7, level=2)         â† operaÃ§Ãµes Belo Horizonte
```

**Grupos de suporte** (Infraestrutura id=7, Sistemas id=8, Redes id=9) tÃªm `is_recursive=1`
e ficam na Matriz â€” sÃ£o visÃ­veis e atribuÃ­veis em qualquer filial, refletindo equipes
centralizadas que atendem todo o grupo.

**AtenÃ§Ã£o**: Use `glpi_users.name` (nÃ£o `users.login`) para identificar usuÃ¡rios.

---

## 3. As 33 SQL Views

### 3.1 `sql/vw_glpi_tickets.sql` â€” View denormalizada principal

| View | Tipo | DescriÃ§Ã£o |
|---|---|---|
| `vw_glpi_tickets` | Fato denormalizado | 1 linha por ticket com todos os campos joinados: datas, status, prioridade, tipo, categoria, grupo, tÃ©cnico, SLA, mÃ©tricas de tempo |

**Campos-chave**: `ticket_id`, `entity_id`, `created_at`, `status_code`, `status_label`,
`priority_label`, `ticket_type_label`, `category_name`, `category_full_path`,
`assigned_group_name`, `technician_name`, `sla_status`, `resolution_time_min`,
`is_open`, `is_resolved`, `is_closed`, `sla_compliant`

---

### 3.2 `sql/vw_star_schema.sql` â€” Star schema de tickets

| View | Tipo | DescriÃ§Ã£o |
|---|---|---|
| `vw_fact_tickets` | **Fato** | 1 linha por ticket com FKs para todas as dimensÃµes + flags + mÃ©tricas |
| `vw_dim_category` | DimensÃ£o | Categorias ITIL com hierarquia (pai/filho), nÃ­vel e caminho completo |
| `vw_dim_technician` | DimensÃ£o | TÃ©cnicos com nome completo, grupo, e-mail |
| `vw_dim_group` | DimensÃ£o | Grupos de suporte (`is_assign=1`) com nome e cÃ³digo |
| `vw_dim_sla` | DimensÃ£o | SLAs com tempo-alvo convertido para minutos e tipo (TTR/TTO) |
| `vw_sla_monthly` | MÃ©trica agregada | Compliance SLA (%) por mÃªs / grupo / prioridade |
| `vw_tech_productivity` | MÃ©trica agregada | Tickets atribuÃ­dos, resolvidos, MTTR e % SLA por tÃ©cnico por mÃªs |
| `vw_backlog_open` | Snapshot | Tickets abertos com age_days, sla_urgency e minutos restantes de SLA |
| `vw_volume_trend` | TendÃªncia | Volume mensal de tickets criados e resolvidos |

**`vw_fact_tickets` â€” colunas principais**:
`ticket_id`, `entity_id`, `created_date`, `resolved_date`, `closed_date`,
`group_id`, `category_id`, `technician_id`, `requester_id`, `sla_id`,
`status_code`, `priority_code`, `ticket_type_code`,
`is_open`, `is_resolved`, `is_closed`, `sla_met`, `sla_status`,
`resolution_min`, `closure_min`, `tto_min`, `age_open_min`, `ticket_count`

---

### 3.3 `sql/vw_extended_analytics.sql` â€” CMDB, Problemas, MudanÃ§as, Projetos

| View | Tipo | DescriÃ§Ã£o |
|---|---|---|
| `vw_dim_asset` | DimensÃ£o | Ativos unificados: Computer, NetworkEquipment, Monitor, Printer â€” chave `asset_key = CONCAT(itemtype, '-', id)` |
| `vw_fact_asset_tickets` | Fato | 1 linha por vÃ­nculo ativoâ†”ticket (`glpi_items_tickets`) |
| `vw_fact_asset_incidents` | MÃ©trica agregada | total_tickets, tickets_closed, avg_resolution_min por ativo |
| `vw_fact_problems` | Fato | 1 linha por problema: `entity_id`, status, prioridade, linked_tickets, linked_assets, resolution_minutes |
| `vw_fact_changes` | Fato | 1 linha por mudanÃ§a: `entity_id`, status, prioridade, linked_tickets, total_tasks, tasks_done |
| `vw_fact_projects` | Fato | 1 linha por projeto: `entity_id`, estado, pct_done, total_tasks, tasks_closed, linked_tickets |
| `vw_fact_project_tasks` | Fato | 1 linha por tarefa de projeto com planned_days, actual_days, delay_days |
| `vw_cmdb_summary` | SumÃ¡rio | InventÃ¡rio CMDB por tipo / fabricante / estado / localizaÃ§Ã£o (derivado de `vw_dim_asset`) |

**`vw_dim_asset` â€” colunas principais**:
`asset_key`, `asset_itemtype`, `asset_id`, `asset_name`, `asset_type`, `asset_model`,
`manufacturer`, `asset_state`, `location`, `entity_id`, `assigned_user`, `serial_number`

---

### 3.4 `sql/vw_analytics_v2.sql` â€” Financeiro, Software, KB, SatisfaÃ§Ã£o

| View | Tipo | DescriÃ§Ã£o |
|---|---|---|
| `vw_dim_supplier` | DimensÃ£o | Fornecedores com tipo, e-mail, status ativo |
| `vw_dim_software` | DimensÃ£o | Softwares com fabricante, versÃ£o, qtd. licenÃ§as, validade |
| `vw_fact_software_licenses` | Compliance | LicenÃ§as emitidas vs. instalaÃ§Ãµes (compliance_status por software) |
| `vw_fact_asset_financials` | Fato | Custo de aquisiÃ§Ã£o, garantia e idade em meses (join com `glpi_infocoms`) |
| `vw_fact_supplier_contracts` | Fato | Contratos com status (Ativo/Expirado/Futuro), datas e cobertura de ativos |
| `vw_fact_kb_usage` | Fato | Artigos KB com view_count e linked_tickets |
| `vw_fact_ticket_enrichment` | Fato | followup_count, task_count, satisfaÃ§Ã£o por ticket_id |
| `vw_dim_os_inventory` | DimensÃ£o | SO instalado por computador (tipo, versÃ£o, asset_type) |
| `vw_fact_satisfaction_summary` | MÃ©trica | avg_satisfaction, promoters, detractors por mÃªs e grupo tÃ©cnico |

> `vw_fact_supplier_contracts` e `vw_fact_asset_financials` ligam ao fornecedor via campo
> de texto `supplier` â€” relacionamento Power BI usa `supplier_name` (nÃ£o um ID numÃ©rico).

---

### 3.5 `sql/vw_entity_analytics.sql` â€” Entidade e Data Center

| View | Tipo | DescriÃ§Ã£o |
|---|---|---|
| `vw_dim_entity` | **DimensÃ£o** | Entidades GLPI: `entity_id`, `entity_name`, `entity_level`, `entity_full_path`, `entity_type` â€” use como **slicer de Filial** |
| `vw_entity_overview` | MÃ©trica agregada | Por entidade: total_tickets, open_tickets, avg_resolution_hours, total_computers |
| `vw_entity_sla_monthly` | MÃ©trica agregada | SLA compliance (%) por entidade e mÃªs |
| `vw_entity_asset_distribution` | MÃ©trica agregada | Ativos por tipo e entidade com total_value_brl |
| `vw_entity_project_performance` | Fato | project_id, entity_id â€” ponte para `vw_fact_projects` |
| `vw_rack_inventory` | Snapshot | Racks com posiÃ§Ã£o U, asset vinculado, serial e incident_count |

---

## 4. Volumes do Dataset de DemonstraÃ§Ã£o

| Entidade | Qtde |
|---|---|
| Entidades geogrÃ¡ficas | 5 (Empresa + Matriz + Filial SP/RJ/MG) |
| UsuÃ¡rios | 62 (1 admin, 11 tÃ©cnicos, 50 solicitantes) |
| Tickets | 1.071 (Jan/2024 â€“ Dez/2025) |
| Computadores | 65 (15 servidores SRV-* + 50 workstations WS-*) |
| Equipamentos de rede | 12 |
| Monitores | 30 |
| Impressoras | 8 |
| Telefones | 30 |
| PerifÃ©ricos | 168 |
| Racks (42U, DC SÃ£o Paulo) | 3 |
| Problemas | 25 |
| MudanÃ§as | 18 |
| Projetos | 6 (36 tarefas) |
| Softwares | 28 (608 instalaÃ§Ãµes) |
| Fornecedores | 8 |
| Contratos | 8 |
| Infocoms (financeiro) | 77 |
| Artigos de KB | 18 |
| Follow-ups de ticket | 444 |
| Tarefas de ticket | 178 |
| AvaliaÃ§Ãµes de satisfaÃ§Ã£o | 712 |

---

## 5. Tabela de Datas (DimDate)

O MariaDB 10.7 nÃ£o suporta `WITH RECURSIVE`, portanto a dimensÃ£o de datas Ã© criada
diretamente no Power BI como **tabela calculada DAX**:

```dax
DimDate = ADDCOLUMNS(
    CALENDAR(DATE(2024,1,1), DATE(2026,12,31)),
    "Year",        YEAR([Date]),
    "Month",       MONTH([Date]),
    "MonthNum",    FORMAT([Date], "MM"),
    "MonthName",   FORMAT([Date], "MMM/YYYY"),
    "Quarter",     "Q" & ROUNDUP(MONTH([Date])/3, 0),
    "YearMonth",   FORMAT([Date], "YYYY-MM"),
    "Weekday",     WEEKDAY([Date], 2),
    "IsWeekend",   IF(WEEKDAY([Date], 2) >= 6, 1, 0),
    "IsWorkday",   IF(WEEKDAY([Date], 2) <= 5, 1, 0)
)
```

ApÃ³s criar: clique com o botÃ£o direito em `DimDate` â†’ **Marcar como Tabela de Data** â†’
coluna `Date`.

---

## 6. Relacionamentos Power BI (24 no total)

Configure todos em **Modelagem â†’ Gerenciar Relacionamentos**.
Cardinalidade padrÃ£o: **Muitos para um (\*:1)** Â· DireÃ§Ã£o padrÃ£o: **Ãšnico** Â· todos Ativos.

### 6.1 Star Schema de Tickets (#1â€“6)

| # | Da tabela (muitos) | Coluna | Para tabela (um) | Coluna | Obs. |
|---|---|---|---|---|---|
| 1 | `vw_fact_tickets` | `created_date` | `DimDate` | `Date` | â€” |
| 2 | `vw_fact_tickets` | `category_id` | `vw_dim_category` | `id` | â€” |
| 3 | `vw_fact_tickets` | `technician_id` | `vw_dim_technician` | `id` | â€” |
| 4 | `vw_fact_tickets` | `group_id` | `vw_dim_group` | `id` | â€” |
| 5 | `vw_fact_tickets` | `sla_id` | `vw_dim_sla` | `id` | â€” |
| 6 | `vw_fact_tickets` | `ticket_id` | `vw_fact_ticket_enrichment` | `ticket_id` | 1:1 |

### 6.2 CMDB (#7â€“9)

| # | Da tabela (muitos) | Coluna | Para tabela (um) | Coluna | Obs. |
|---|---|---|---|---|---|
| 7 | `vw_fact_asset_incidents` | `asset_key` | `vw_dim_asset` | `asset_key` | â€” |
| 8 | `vw_fact_asset_tickets` | `asset_key` | `vw_dim_asset` | `asset_key` | **Bidirecional** âš ï¸ |
| 9 | `vw_fact_asset_tickets` | `ticket_id` | `vw_fact_tickets` | `ticket_id` | â€” |

> **âš ï¸ Relacionamento #8**: configure **DireÃ§Ã£o do filtro cruzado = Ambos** para evitar
> caminho ambÃ­guo entre `vw_fact_asset_tickets` e `vw_dim_entity`.

### 6.3 Projetos e Produtividade (#10â€“11)

| # | Da tabela (muitos) | Coluna | Para tabela (um) | Coluna |
|---|---|---|---|---|
| 10 | `vw_fact_project_tasks` | `project_id` | `vw_fact_projects` | `project_id` |
| 11 | `vw_tech_productivity` | `technician_id` | `vw_dim_technician` | `id` |

### 6.4 Backlog e Analytics v2 (#12â€“15)

| # | Da tabela (muitos) | Coluna | Para tabela (um) | Coluna |
|---|---|---|---|---|
| 12 | `vw_backlog_open` | `ticket_id` | `vw_fact_tickets` | `ticket_id` |
| 13 | `vw_fact_software_licenses` | `software_id` | `vw_dim_software` | `software_id` |
| 14 | `vw_fact_supplier_contracts` | `supplier` | `vw_dim_supplier` | `supplier_name` |
| 15 | `vw_fact_asset_financials` | `supplier` | `vw_dim_supplier` | `supplier_name` |

### 6.5 Datas em Problemas, MudanÃ§as e Projetos (#16â€“18)

| # | Da tabela (muitos) | Coluna | Para tabela (um) | Coluna |
|---|---|---|---|---|
| 16 | `vw_fact_problems` | `open_date` | `DimDate` | `Date` |
| 17 | `vw_fact_changes` | `open_date` | `DimDate` | `Date` |
| 18 | `vw_entity_project_performance` | `project_id` | `vw_fact_projects` | `project_id` |

### 6.6 Entidade / Filial â€” Slicer Central (#19â€“24)

| # | Da tabela (muitos) | Coluna | Para tabela (um) | Coluna |
|---|---|---|---|---|
| 19 | `vw_fact_tickets` | `entity_id` | `vw_dim_entity` | `entity_id` |
| 20 | `vw_glpi_tickets` | `entity_id` | `vw_dim_entity` | `entity_id` |
| 21 | `vw_dim_asset` | `entity_id` | `vw_dim_entity` | `entity_id` |
| 22 | `vw_fact_problems` | `entity_id` | `vw_dim_entity` | `entity_id` |
| 23 | `vw_fact_changes` | `entity_id` | `vw_dim_entity` | `entity_id` |
| 24 | `vw_fact_projects` | `entity_id` | `vw_dim_entity` | `entity_id` |

> Um slicer com `vw_dim_entity[entity_name]` filtra simultaneamente tickets,
> ativos, problemas, mudanÃ§as e projetos em todas as pÃ¡ginas do relatÃ³rio.

### 6.7 Views standalone (sem relacionamento necessÃ¡rio)

| View | Motivo |
|---|---|
| `vw_sla_monthly` | PrÃ©-agregada (sem FK para ligar) |
| `vw_volume_trend` | PrÃ©-agregada |
| `vw_cmdb_summary` | PrÃ©-agregada (derivada de `vw_dim_asset`) |
| `vw_entity_overview` | PrÃ©-agregada por entidade |
| `vw_entity_sla_monthly` | PrÃ©-agregada por entidade |
| `vw_entity_asset_distribution` | PrÃ©-agregada por entidade |
| `vw_rack_inventory` | Self-contained |
| `vw_fact_satisfaction_summary` | PrÃ©-agregada |
| `vw_dim_os_inventory` | Opcional: liga via `computer_id` â†’ `vw_dim_asset[asset_id]` |
| `vw_fact_kb_usage` | Self-contained |

---

## 7. Mapa de Arquivos SQL â†’ Views

| Arquivo | Views contidas |
|---|---|
| `sql/vw_glpi_tickets.sql` | `vw_glpi_tickets` |
| `sql/vw_star_schema.sql` | `vw_fact_tickets`, `vw_dim_category`, `vw_dim_technician`, `vw_dim_group`, `vw_dim_sla`, `vw_sla_monthly`, `vw_tech_productivity`, `vw_backlog_open`, `vw_volume_trend` |
| `sql/vw_extended_analytics.sql` | `vw_dim_asset`, `vw_fact_asset_tickets`, `vw_fact_asset_incidents`, `vw_fact_problems`, `vw_fact_changes`, `vw_fact_projects`, `vw_fact_project_tasks`, `vw_cmdb_summary` |
| `sql/vw_analytics_v2.sql` | `vw_dim_supplier`, `vw_dim_software`, `vw_fact_software_licenses`, `vw_fact_asset_financials`, `vw_fact_supplier_contracts`, `vw_fact_kb_usage`, `vw_fact_ticket_enrichment`, `vw_dim_os_inventory`, `vw_fact_satisfaction_summary` |
| `sql/vw_entity_analytics.sql` | `vw_dim_entity`, `vw_entity_overview`, `vw_entity_sla_monthly`, `vw_entity_asset_distribution`, `vw_entity_project_performance`, `vw_rack_inventory` |

---

## 8. GlossÃ¡rio

| Termo | DefiniÃ§Ã£o |
|---|---|
| **GLPI** | Gestionnaire Libre de Parc Informatique â€” sistema ITSM/ITAM open-source |
| **SLA** | Service Level Agreement â€” tempo mÃ¡ximo de resoluÃ§Ã£o por prioridade |
| **MTTR** | Mean Time To Resolve â€” tempo mÃ©dio do ticket aberto ao resolvido |
| **TTR** | Time To Resolve â€” SLA de resoluÃ§Ã£o |
| **TTO** | Time To Own â€” SLA de atendimento inicial |
| **Entidade** | Unidade organizacional/geogrÃ¡fica no GLPI (Matriz, Filial SPâ€¦) |
| **Grupo** | Equipe tÃ©cnica no GLPI (Infraestrutura, Sistemas, Redes) |
| **asset_key** | Chave surrogate dos ativos: `CONCAT(itemtype, '-', id)` â€” ex: `Computer-42` |
| **DAX** | Data Analysis Expressions â€” linguagem de fÃ³rmulas do Power BI |

