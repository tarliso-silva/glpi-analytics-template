# Data Model — GLPI Analytics Template

Este documento descreve o modelo de dados analítico completo do projeto, cobrindo
Tickets, CMDB, Problemas, Mudanças e Projetos.

---

## 1. Visão Geral

O GLPI armazena dados ITSM em centenas de tabelas relacionais. A camada analítica
simplifica isso expondo **SQL views** pré-joinadas que o Power BI consome diretamente.

### Star Schema — Tickets (camada base)

```
                    ┌─────────────────┐
                    │  vw_dim_date    │  (gerada via DAX CALENDAR())
                    └────────┬────────┘
                             │
┌──────────────┐    ┌────────▼────────┐    ┌──────────────────┐
│ vw_dim_group │◄───│ vw_fact_tickets │───►│ vw_dim_technician│
└──────────────┘    └────────┬────────┘    └──────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
     ┌────────────┐  ┌─────────────┐  ┌──────────┐
     │vw_dim_sla  │  │vw_dim_categ.│  │vw_dim_ass│
     └────────────┘  └─────────────┘  └──────────┘
```

### Domínios cobertos

| Domínio | Tabelas GLPI | Views Analytics |
|---|---|---|
| Tickets (ITSM) | `glpi_tickets`, `_users`, `_groups` | `vw_fact_tickets`, `vw_glpi_tickets` |
| CMDB / Ativos | `glpi_computers`, `_networkequipments`, `_monitors`, `_printers` | `vw_dim_asset`, `vw_fact_asset_tickets`, `vw_fact_asset_incidents`, `vw_cmdb_summary` |
| Problemas | `glpi_problems`, `_tickets`, `_users`, `_groups` | `vw_fact_problems` |
| Mudanças | `glpi_changes`, `_tickets`, `_users`, `_items`, `glpi_changetasks` | `vw_fact_changes` |
| Projetos | `glpi_projects`, `_tasks`, `_teams`, `glpi_projecttasks_tickets` | `vw_fact_projects`, `vw_fact_project_tasks` |
| SLA | `glpi_slms`, `glpi_slas` | `vw_dim_sla`, `vw_sla_monthly` |
| Tendências | — | `vw_volume_trend`, `vw_tech_productivity`, `vw_backlog_open` |

---

## 2. Tabelas GLPI Utilizadas

### 2.1 ITSM — Tickets
| Tabela | Descrição |
|---|---|
| `glpi_tickets` | Tabela principal de tickets — 1 linha por ticket |
| `glpi_tickets_users` | Vínculo ticket↔usuário (type=1: solicitante, type=2: técnico) |
| `glpi_groups_tickets` | Vínculo ticket↔grupo (type=2: grupo atribuído) |
| `glpi_itilcategories` | Categorias ITIL hierárquicas |
| `glpi_slms` / `glpi_slas` | Service Level Management e SLA por prioridade |

### 2.2 CMDB — Ativos
| Tabela | Descrição |
|---|---|
| `glpi_computers` | Workstations, notebooks e servidores |
| `glpi_networkequipments` | Switches, roteadores, firewalls, APs |
| `glpi_monitors` | Monitores |
| `glpi_printers` | Impressoras |
| `glpi_items_tickets` | Vínculo polimórfico ativo↔ticket (itemtype + items_id) |
| `glpi_manufacturers` | Fabricantes de equipamentos |
| `glpi_states` | Estado do ativo (Em uso, Em manutenção, Disponível, Desativado) |
| `glpi_locations` | Localizações físicas dos ativos |

### 2.3 ITSM — Problemas
| Tabela | Descrição |
|---|---|
| `glpi_problems` | Registro de problemas ITIL |
| `glpi_problems_tickets` | Tickets vinculados a um problema |
| `glpi_problems_users` | Técnico responsável pelo problema (type=2) |
| `glpi_groups_problems` | Grupo responsável pelo problema (type=2) |
| `glpi_items_problems` | Ativos afetados pelo problema |

### 2.4 ITSM — Mudanças
| Tabela | Descrição |
|---|---|
| `glpi_changes` | Registro de mudanças (RFC) |
| `glpi_changes_tickets` | Tickets originadores da mudança |
| `glpi_changes_users` | Técnico responsável (type=2) |
| `glpi_changes_items` | Ativos impactados pela mudança |
| `glpi_changetasks` | Tarefas de execução da mudança (state: 0=todo, 1=doing, 2=done) |

### 2.5 Projetos
| Tabela | Descrição |
|---|---|
| `glpi_projects` | Projetos de TI |
| `glpi_projecttasks` | Tarefas dentro de cada projeto |
| `glpi_projecttasks_tickets` | Tickets vinculados a tarefas de projeto |
| `glpi_projectteams` | Membros da equipe do projeto |
| `glpi_projecttaskteams` | Responsáveis por tarefas individuais |
| `glpi_projectstates` | Estados do projeto (New=1, Processing=2, Closed=3) |

---

## 3. Views Disponíveis

### 3.1 Camada de Tickets (arquivo: `sql/vw_glpi_tickets.sql`)

#### `vw_glpi_tickets`
View principal com 1 linha por ticket, todos os campos joinados.

| Campo | Tipo | Descrição |
|---|---|---|
| `ticket_id` | INT | ID único do ticket |
| `ticket_title` | STRING | Título do ticket |
| `created_at` | DATETIME | Data/hora de abertura |
| `closed_at` | DATETIME | Data/hora de encerramento |
| `status_label` | STRING | Status legível (Novo, Em andamento, Resolvido, Fechado…) |
| `priority_label` | STRING | Prioridade legível |
| `category` | STRING | Categoria ITIL folha |
| `parent_category` | STRING | Categoria pai |
| `tech_name` | STRING | Nome completo do técnico atribuído |
| `group_name` | STRING | Nome do grupo de suporte |
| `sla_name` | STRING | Nome do SLA aplicado |
| `sla_status` | STRING | Dentro do SLA / Violado / Violado (aberto) / Sem SLA |
| `resolution_minutes` | INT | Tempo de resolução em minutos |
| `year` | INT | Ano de abertura |
| `month` | INT | Mês de abertura |
| `quarter` | INT | Trimestre de abertura |

---

### 3.2 Star Schema (arquivo: `sql/vw_star_schema.sql`)

| View | Tipo | Descrição |
|---|---|---|
| `vw_fact_tickets` | Fato | 1 linha por ticket com FKs para dimensões |
| `vw_dim_category` | Dimensão | Categorias ITIL com hierarquia |
| `vw_dim_technician` | Dimensão | Técnicos com grupo e senioridade |
| `vw_dim_group` | Dimensão | Grupos de suporte |
| `vw_dim_sla` | Dimensão | SLAs com tempo-alvo em minutos |
| `vw_sla_monthly` | Métrica | Compliance SLA por mês/grupo/prioridade |
| `vw_tech_productivity` | Métrica | Produtividade mensal por técnico |
| `vw_backlog_open` | Snapshot | Tickets abertos com tempo de espera |
| `vw_volume_trend` | Tendência | Volume de tickets por mês |

---

### 3.3 Analytics Estendidas (arquivo: `sql/vw_extended_analytics.sql`)

#### CMDB / Ativos
| View | Tipo | Descrição |
|---|---|---|
| `vw_dim_asset` | Dimensão | Todos os ativos CMDB (Computer, NetworkEquipment, Monitor, Printer) em uma view unificada |
| `vw_fact_asset_tickets` | Fato | 1 linha por vínculo ativo↔ticket com contexto do ticket |
| `vw_fact_asset_incidents` | Métrica | Contagem de tickets, MTTR e tickets abertos por ativo |
| `vw_cmdb_summary` | Sumário | Inventário por tipo/fabricante/estado/localização |

#### Problemas
| View | Tipo | Descrição |
|---|---|---|
| `vw_fact_problems` | Fato | 1 linha por problema com tickets linkados, ativo afetado e tempo de resolução |

#### Mudanças
| View | Tipo | Descrição |
|---|---|---|
| `vw_fact_changes` | Fato | 1 linha por mudança com tickets linkados, ativos, tarefas e % de progresso |

#### Projetos
| View | Tipo | Descrição |
|---|---|---|
| `vw_fact_projects` | Fato | 1 linha por projeto com total/concluídas de tarefas, tickets vinculados e membros da equipe |
| `vw_fact_project_tasks` | Fato | 1 linha por tarefa com desvio de prazo (delay_days) e tickets vinculados |

---

## 4. Volumes de Dados Simulados

| Entidade | Volume |
|---|---|
| Tickets | ~1.071 (Jan/2024 – Dez/2025) |
| Técnicos | 11 |
| Solicitantes | 50 |
| Categorias ITIL | 26 (5 pais + 21 filhos) |
| SLAs | 6 (por prioridade) |
| Computadores | 65 (50 workstations + 15 servidores) |
| Equipamentos de rede | 12 |
| Monitores | 30 |
| Impressoras | 8 |
| Vínculos ticket↔ativo | ~303 |
| Problemas | 25 |
| Mudanças | 18 |
| Projetos | 6 |
| Tarefas de projeto | 36 |

---

## 5. Dica: Dimensão de Data no Power BI

O MariaDB desta versão não suporta `WITH RECURSIVE`. Crie a tabela de datas via DAX:

```dax
DimDate = CALENDAR(DATE(2024,1,1), DATE(2025,12,31))
```

Adicione colunas calculadas:
```dax
Year   = YEAR([Date])
Month  = MONTH([Date])
Quarter = "Q" & ROUNDUP(MONTH([Date])/3, 0)
MonthName = FORMAT([Date], "MMM/YYYY")
```

---

## 6. Relacionamentos Power BI recomendados

```
vw_fact_tickets[category]      → vw_dim_category[category_name]
vw_fact_tickets[tech_name]     → vw_dim_technician[tech_name]
vw_fact_tickets[group_name]    → vw_dim_group[group_name]
vw_fact_tickets[sla_name]      → vw_dim_sla[sla_name]
vw_fact_tickets[created_at]    → DimDate[Date]

vw_fact_asset_tickets[ticket_id]    → vw_fact_tickets[ticket_id]
vw_fact_asset_tickets[asset_key]    → vw_dim_asset[asset_key]
vw_fact_asset_incidents[asset_key]  → vw_dim_asset[asset_key]

vw_fact_problems[problem_id]   → (autônomo, relacionar via ticket_id se necessário)
vw_fact_changes[change_id]     → (autônomo)
vw_fact_projects[project_id]   → vw_fact_project_tasks[project_id]
```


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

---

## 8. Expansion 1-4: Novos Domínios (2025)

Esta seção documenta os domínios adicionados na expansão do dataset analítico.

### 8.1 Domínios Expandidos

| Domínio | Tabelas GLPI | Views Analytics |
|---|---|---|
| **Software e Licenças** | `glpi_softwares`, `glpi_softwareversions`, `glpi_softwarelicenses`, `glpi_items_softwareversions` | `vw_dim_software`, `vw_fact_software_licenses` |
| **Sistemas Operacionais** | `glpi_operatingsystems`, `glpi_operatingsystemversions`, `glpi_items_operatingsystems` | `vw_dim_os_inventory` |
| **Fornecedores** | `glpi_suppliers`, `glpi_suppliertypes`, `glpi_contacts`, `glpi_contacts_suppliers` | `vw_dim_supplier` |
| **Contratos** | `glpi_contracts`, `glpi_contracttypes`, `glpi_contracts_suppliers`, `glpi_contracts_items` | `vw_fact_supplier_contracts` |
| **Financeiro (Ativos)** | `glpi_infocoms` | `vw_fact_asset_financials` |
| **Documentos** | `glpi_documents`, `glpi_documentcategories`, `glpi_documents_items` | — |
| **Base de Conhecimento** | `glpi_knowbaseitems`, `glpi_knowbaseitems_users`, `glpi_knowbaseitems_items`, `glpi_knowbaseitemcategories` | `vw_fact_kb_usage` |
| **Telefones / VoIP** | `glpi_phones`, `glpi_phonetypes`, `glpi_phonemodels` | (via `vw_dim_asset` se necessário) |
| **Periféricos** | `glpi_peripherals`, `glpi_peripheraltypes`, `glpi_peripheralmodels` | (via `vw_dim_asset` se necessário) |
| **Enriquecimento de Tickets** | `glpi_itilfollowups`, `glpi_tickettasks`, `glpi_ticketsatisfactions` | `vw_fact_ticket_enrichment` |
| **Problemas (tasks)** | `glpi_problemtasks` | (já coberto em `vw_fact_problems`) |
| **Mudanças ↔ Problemas** | `glpi_changes_problems` | (já coberto em `vw_fact_changes`) |
| **Satisfação** | `glpi_ticketsatisfactions` | `vw_fact_satisfaction_summary` |

---

### 8.2 Views Analytics v2 (arquivo: `sql/vw_analytics_v2.sql`)

| View | Tipo | Descrição |
|---|---|---|
| `vw_dim_supplier` | Dimensão | Fornecedores com tipo, contato, localidade e status ativo |
| `vw_dim_software` | Dimensão | Catálogo de software com fabricante, versão, tipo e validade da licença |
| `vw_fact_software_licenses` | Fato/Compliance | Licenças emitidas vs. instalações — status de compliance por software |
| `vw_fact_asset_financials` | Fato | Custo de aquisição, garantia e ciclo de vida de ativos (computadores + rede) |
| `vw_fact_supplier_contracts` | Fato | Contratos ativos/expirados com cobertura de ativos por fornecedor |
| `vw_fact_kb_usage` | Fato | Artigos KB com contagem de views, vínculos a tickets e autor |
| `vw_fact_ticket_enrichment` | Fato | Tickets com contagem de follow-ups, tarefas e nota de satisfação |
| `vw_dim_os_inventory` | Dimensão | SO instalado por computador (tipo, versão, localização) |
| `vw_fact_satisfaction_summary` | Métrica | Satisfação média, promotores/neutros/detratores por mês e grupo técnico |

---

### 8.3 Volumes de Dados — Expansão 1-4

| Entidade | Volume |
|---|---|
| Sistemas Operacionais (tipos) | 7 |
| Versões de SO | 7 |
| Vínculos computador ↔ SO | 65 (1 por computador) |
| Softwares | 28 |
| Versões de software | 28 |
| Tipos de licença | 9 (incl. 1 padrão) |
| Licenças | 28 |
| Instalações de software | 608 |
| Tipos de fornecedor | 4 |
| Fornecedores | 8 |
| Contatos de fornecedor | 10 |
| Tipos de contrato | 4 |
| Contratos | 8 |
| Vínculos contrato ↔ ativo | 55 |
| Informações financeiras (infocoms) | 77 (65 computadores + 12 network) |
| Categorias de documento | 7 |
| Documentos | 18 |
| Vínculos documento ↔ item | 58 |
| Categorias de KB | 6 |
| Artigos de KB | 18 |
| Vínculos KB ↔ ticket | 38 |
| Telefones (VoIP + celular) | 30 |
| Periféricos | 168 |
| Follow-ups de ticket | 444 |
| Tarefas de ticket | 178 |
| Avaliações de satisfação | 712 (≈80% de fechados responderam) |
| Tarefas de problema | 60 |
| Vínculos change ↔ problem | 30 |

---

### 8.4 Relacionamentos Power BI Recomendados — v2

```
-- Software e Licenças
vw_fact_software_licenses[software_id]  → vw_dim_software[software_id]
vw_fact_software_licenses[software_id]  → (filtro por fabricante, tipo de licença)

-- Financeiro
vw_fact_asset_financials[supplier]      → vw_dim_supplier[supplier_name]
vw_fact_asset_financials[asset_name]    → vw_dim_asset[asset_name]

-- Contratos
vw_fact_supplier_contracts[supplier]    → vw_dim_supplier[supplier_name]
vw_fact_supplier_contracts[begin_date]  → DimDate[Date]

-- Satisfação
vw_fact_satisfaction_summary[year_month] → DimDate (via year+month)
vw_fact_satisfaction_summary[tech_group] → vw_dim_group[group_name]

-- Enriquecimento de Tickets
vw_fact_ticket_enrichment[ticket_id]    → vw_fact_tickets[ticket_id]

-- OS Inventory
vw_dim_os_inventory[computer_id]        → vw_dim_asset[asset_id]  (where itemtype='Computer')
```

---

### 8.5 Scripts de Seed

| Script | Domínio | Idempotente? |
|---|---|---|
| `src/seed_expansion_1.py` | Software, Licenças, SO | ✅ Verifica se já existe antes de inserir |
| `src/seed_expansion_1_fix.py` | Instalações de software (glpi_items_softwareversions) | ✅ |
| `src/seed_expansion_2.py` | Fornecedores, Contratos, Infocoms | ✅ |
| `src/seed_expansion_3.py` | Documentos, KB, Telefones, Periféricos | ✅ |
| `src/seed_expansion_4.py` | Follow-ups, Tarefas, Satisfação, Problem Tasks, Changes↔Problems | ✅ |
| `src/apply_analytics_v2.py` | Aplica `sql/vw_analytics_v2.sql` | ✅ (CREATE OR REPLACE) |

---

## 9. Rack / Data Center e Estrutura Multi-Entidade (2025)

### 9.1 Hierarquia de Entidades (modelo geográfico atual)

```
Empresa (id=0)                          ← raiz corporativa
├─ Matriz       (id=4, level=2)         ← sede SP — TI, infra, ITSM
├─ Filial SP    (id=5, level=2)         ← operações regionais SP
├─ Filial RJ    (id=6, level=2)         ← operações Rio de Janeiro
└─ Filial MG    (id=7, level=2)         ← operações Belo Horizonte
```

> **Nota ITIL**: entidades representam unidades organizacionais/geográficas.
> Grupos (`glpi_groups`) representam equipes técnicas (Infraestrutura, Sistemas, Redes)
> e permanecem com `is_recursive=1` para visibilidade em todas as filiais.

### 9.2 Distribuição de Dados por Entidade

| Recurso | Empresa | Matriz | Filial SP | Filial RJ | Filial MG | Total |
|---|---|---|---|---|---|---|
| Usuários | 1 (admin) | 23 (técn.+solicit.) | 13 | 12 | 13 | 62 |
| Tickets | — | 291 | 238 | 272 | 270 | 1.071 |
| Computadores | — | 24 (SRV+WS) | 17 (WS) | 17 (WS) | 7 (WS) | 65 |
| Equipamento de rede | — | 12 | — | — | — | 12 |
| Racks | — | 3 | — | — | — | 3 |
| Monitores | — | 8 | 8 | 7 | 7 | 30 |
| Impressoras | — | 2 | 2 | 2 | 2 | 8 |
| Problemas | — | 25 | — | — | — | 25 |
| Mudanças | — | 18 | — | — | — | 18 |
| Projetos | — | 2 | 2 | 1 | 1 | 6 |
| Fornecedores | 4 (globais) | 4 | — | — | — | 8 |
| Softwares | — | 28 (is_recursive=1) | — | — | — | 28 |

### 9.3 Infraestrutura de Racks (DC São Paulo — Matriz)

| Rack | Servidores | Equipamentos de Rede |
|---|---|---|
| RACK-DC-01 | SRV-001 a SRV-005 (U2-U10) | SW-CORE-01/02, RT-BORDA-01, FW-01 (U38-U41) |
| RACK-DC-02 | SRV-006 a SRV-010 (U2-U10) | SW-ACC-01/02/03, FW-02 (U38-U41) |
| RACK-DC-03 | SRV-011 a SRV-015 (U2-U10) | AP-SP-01/02, SW-RJ-01, AP-RJ-01 (U38-U41) |

Tabelas GLPI: `glpi_racks`, `glpi_racktypes`, `glpi_dcrooms`, `glpi_items_racks`  
**Nota**: `glpi_items_racks` NÃO tem `date_mod`/`date_creation`.  
**Nota**: `glpi_entities` NÃO tem coluna `is_recursive`.

### 9.4 Views Analytics — Entidade e Rack (arquivo: `sql/vw_entity_analytics.sql`)

| View | Descrição | Linhas |
|---|---|---|
| `vw_entity_overview` | Resumo por entidade: tickets, usuários, ativos, tempo médio resolução | 5 |
| `vw_entity_sla_monthly` | Conformidade SLA por entidade e mês (within_sla, breached_sla, %) | 96 |
| `vw_entity_asset_distribution` | Ativos por tipo e entidade com valor financeiro e % do total | 16 |
| `vw_entity_project_performance` | Projetos com tarefas concluídas e tickets vinculados por entidade | 6 |
| `vw_rack_inventory` | Inventário de racks com posição U, asset, serial e contagem de incidentes | 27 |

### 9.5 Scripts desta Expansão

| Script | Descrição | Idempotente? |
|---|---|---|
| `src/audit_schemas.py` | Descoberta de schema (racks, entidades, distribuição de IDs) | ✅ |
| `src/seed_racks.py` | Rack types, DC room, 3 racks + 27 items vinculados | ✅ (aborta se racks existem) |
| `src/seed_multi_entity.py` | Modelo funcional inicial (TI/Ops/Fin) — **OBSOLETO**, não re-executar | ✅ (aborta se >1 entidade) |
| `src/refactor_entities.py` | Migração para modelo geográfico (Empresa/Matriz/Filiais) | ✅ (aborta se Matriz existe) |
| `src/validate_integrity.py` | Validação referencial pós-redistribuição | — |
| `src/apply_entity_views.py` | Aplica `sql/vw_entity_analytics.sql` | ✅ (CREATE OR REPLACE) |

### 9.6 Volumes Totais do Dataset (pós-expansão completa)

| Categoria | Qtde |
|---|---|
| Entidades | 5 (Empresa + Matriz + 3 Filiais) |
| Usuários | 62 (1 admin + 11 técnicos + 50 solicitantes) |
| Tickets | 1.071 |
| Computadores | 65 (15 SRV + 50 WS) |
| Equipamentos de rede | 12 |
| Racks | 3 (42U, DC São Paulo) |
| Monitores | 30 |
| Impressoras | 8 |
| Telefones | 30 |
| Periféricos | 168 |
| Problemas | 25 |
| Mudanças | 18 |
| Projetos | 6 |
| Softwares | 28 |
| Instalações de SW | 608 |
| Fornecedores | 8 |
| Contratos | 8 |
| Infocoms | 77 |
| Artigos KB | 18 |
| Follow-ups | 444 |
| Tarefas de tickets | 178 |
| Avaliações de satisfação | 712 |
| **Views SQL totais** | **32** (10 base + 8 star + 5 extended + 9 v2 + 5 entity) |

---

## 10. Refatoração para Modelo Geográfico (2025)

### 10.1 Motivação

O modelo inicial (`seed_multi_entity.py`) criava entidades por **departamento funcional**
(TI, Operações, Financeiro). Esta abordagem conflitava com a arquitetura ITIL 4, onde
unidades organizacionais são divisões administrativas/geográficas e as equipes técnicas
são representadas por **grupos**, não por entidades.

### 10.2 Mapeamento de Migração

| Entidade Anterior | ID Ant. | Entidade Nova | ID Novo | Ação |
|---|---|---|---|---|
| Entidade raiz | 0 | **Empresa** | 0 | Renomeada |
| TI - Tecnologia da Informação | 1 | — | — | **Excluída** |
| Operações | 2 | — | — | **Excluída** |
| Financeiro | 3 | — | — | **Excluída** |
| *(nova)* | — | **Matriz** | 4 | Criada |
| *(nova)* | — | **Filial SP** | 5 | Criada |
| *(nova)* | — | **Filial RJ** | 6 | Criada |
| *(nova)* | — | **Filial MG** | 7 | Criada |

### 10.3 Script de Migração (`src/refactor_entities.py`)

O script executa 16 fases atômicas:

| Fase | Operação |
|---|---|
| 1 | Verifica idempotência (aborta se Matriz já existe) |
| 2-4 | Renomeia entidade raiz para "Empresa" |
| 5 | Cria Matriz, Filial SP, Filial RJ, Filial MG (filhas de Empresa) |
| 6-9 | Redistribui tickets/usuários/ativos/projetos pelas 4 novas entidades |
| 10-12 | Migra fornecedores, contratos, documentos |
| 13 | Exclui entidades antigas (1, 2, 3) com `FOREIGN_KEY_CHECKS=0` |
| 14-15 | Verifica órfãos residuais |
| 16 | Varredura dinâmica de todas as tabelas com `entities_id` para migrar referências residuais |

### 10.4 Grupos vs. Entidades

| Conceito | Implementação GLPI | Visibilidade |
|---|---|---|
| Divisão geográfica/jurídica | **Entidade** | Controla acesso e isolamento de dados |
| Equipe técnica | **Grupo** (`is_recursive=1`) | Visível em todas as entidades filhas |

Os grupos de suporte (Infraestrutura id=7, Sistemas id=8, Redes id=9) têm
`is_recursive=1` e ficam na Matriz — são, portanto, visíveis e atribuíveis em
qualquer filial, refletindo a realidade de equipes centralizadas que atendem todo o grupo.

### 10.5 Quirks do Schema GLPI (validados)

| Tabela / Coluna | Observação |
|---|---|
| `glpi_entities` | **Não possui** `is_recursive` — recursividade é definida nos itens |
| `glpi_items_racks` | **Não possui** `date_mod` nem `date_creation` |
| `glpi_projects` | Colunas válidas: `code`, `plan_start_date`, `plan_end_date`, `projectstates_id` |
| `glpi_users` | Use `name` (não `login`) para identificar usuários |
| Views SQL | Palavra reservada `year_month` → envolva em backticks |
| MariaDB 10.7 | Não suporta `WITH RECURSIVE`; `GROUP BY` não aceita aliases |

