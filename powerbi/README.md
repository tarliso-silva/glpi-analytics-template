# Power BI — Guia Completo de Configuração

Este guia documenta todo o processo para conectar o Power BI ao GLPI Analytics Template,
criar os 24 relacionamentos, configurar a tabela de datas e construir os 8 dashboards.

---

## Pré-requisitos

| Requisito | Detalhe |
|---|---|
| Power BI Desktop | Gratuito em [microsoft.com/powerbi](https://powerbi.microsoft.com/desktop/) |
| MySQL Connector/NET | **Versão 8.0.33** obrigatória — 9.x é incompatível |
| Docker rodando | Containers `glpi-mysql` (3306), `glpi-app` (8080) ativos |
| Views deployadas | `python .venv\Scripts\python.exe pipeline/deploy_views.py` (33 views) |

### Instalar o MySQL Connector/NET 8.0.33

1. Baixe: [mysql-connector-net-8.0.33.msi](https://cdn.mysql.com/archives/mysql-connector-net-8.0/mysql-connector-net-8.0.33.msi)
2. Execute o instalador
3. **Reinicie o Power BI Desktop** após a instalação

> **Não use** o conector MariaDB (requer driver ODBC separado) nem versões 9.x do MySQL Connector/NET.

---

## 1. Conectar ao Banco de Dados

1. **Obter Dados → Banco de dados MySQL**
2. Preencha:
   - Servidor: `localhost`
   - Base de dados: `glpi`
3. Clique em **OK**
4. Usuário: `glpi` · Senha: `glpi` · Nível: `Base de dados`
5. No navegador, selecione **todas as 33 views** `vw_*` e clique em **Carregar**

---

## 2. Criar a Tabela de Datas (DimDate)

O MariaDB 10.7 não suporta `WITH RECURSIVE` — crie a tabela via DAX:

1. **Modelagem → Nova Tabela**
2. Cole o DAX abaixo e pressione Enter:

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

3. Clique com o botão direito em `DimDate` → **Marcar como Tabela de Data** → coluna `Date`

---

## 3. Criar os 24 Relacionamentos

Vá em **Modelagem → Gerenciar Relacionamentos → Novo**.

Cardinalidade padrão: **Muitos para um (\*:1)** · Direção padrão: **Único** · todos Ativos.

### 3.1 Star Schema de Tickets (#1–6)

| # | Da tabela (muitos) | Coluna | Para tabela (um) | Coluna |
|---|---|---|---|---|
| 1 | `glpi vw_fact_tickets` | `created_date` | `DimDate` | `Date` |
| 2 | `glpi vw_fact_tickets` | `category_id` | `glpi vw_dim_category` | `id` |
| 3 | `glpi vw_fact_tickets` | `technician_id` | `glpi vw_dim_technician` | `id` |
| 4 | `glpi vw_fact_tickets` | `group_id` | `glpi vw_dim_group` | `id` |
| 5 | `glpi vw_fact_tickets` | `sla_id` | `glpi vw_dim_sla` | `id` |
| 6 | `glpi vw_fact_tickets` | `ticket_id` | `glpi vw_fact_ticket_enrichment` | `ticket_id` |

> Relacionamento #6: mude a cardinalidade para **Um para um (1:1)**.

### 3.2 CMDB (#7–9)

| # | Da tabela (muitos) | Coluna | Para tabela (um) | Coluna | Atenção |
|---|---|---|---|---|---|
| 7 | `glpi vw_fact_asset_incidents` | `asset_key` | `glpi vw_dim_asset` | `asset_key` | — |
| 8 | `glpi vw_fact_asset_tickets` | `asset_key` | `glpi vw_dim_asset` | `asset_key` | **Bidirecional** ⚠️ |
| 9 | `glpi vw_fact_asset_tickets` | `ticket_id` | `glpi vw_fact_tickets` | `ticket_id` | — |

> **⚠️ Relacionamento #8**: mude **Direção do filtro cruzado** para **Ambos**.
> Isso é necessário para evitar o erro de "caminho ambíguo" entre `vw_fact_asset_tickets`
> e `vw_dim_entity` que ocorreria com filtro único.

### 3.3 Projetos e Produtividade (#10–11)

| # | Da tabela (muitos) | Coluna | Para tabela (um) | Coluna |
|---|---|---|---|---|
| 10 | `glpi vw_fact_project_tasks` | `project_id` | `glpi vw_fact_projects` | `project_id` |
| 11 | `glpi vw_tech_productivity` | `technician_id` | `glpi vw_dim_technician` | `id` |

### 3.4 Backlog e Analytics v2 (#12–15)

| # | Da tabela (muitos) | Coluna | Para tabela (um) | Coluna |
|---|---|---|---|---|
| 12 | `glpi vw_backlog_open` | `ticket_id` | `glpi vw_fact_tickets` | `ticket_id` |
| 13 | `glpi vw_fact_software_licenses` | `software_id` | `glpi vw_dim_software` | `software_id` |
| 14 | `glpi vw_fact_supplier_contracts` | `supplier` | `glpi vw_dim_supplier` | `supplier_name` |
| 15 | `glpi vw_fact_asset_financials` | `supplier` | `glpi vw_dim_supplier` | `supplier_name` |

### 3.5 Datas em Problemas, Mudanças e Projetos (#16–18)

| # | Da tabela (muitos) | Coluna | Para tabela (um) | Coluna |
|---|---|---|---|---|
| 16 | `glpi vw_fact_problems` | `open_date` | `DimDate` | `Date` |
| 17 | `glpi vw_fact_changes` | `open_date` | `DimDate` | `Date` |
| 18 | `glpi vw_entity_project_performance` | `project_id` | `glpi vw_fact_projects` | `project_id` |

### 3.6 Entidade / Filial — Slicer Central (#19–24)

| # | Da tabela (muitos) | Coluna | Para tabela (um) | Coluna |
|---|---|---|---|---|
| 19 | `glpi vw_fact_tickets` | `entity_id` | `glpi vw_dim_entity` | `entity_id` |
| 20 | `glpi vw_glpi_tickets` | `entity_id` | `glpi vw_dim_entity` | `entity_id` |
| 21 | `glpi vw_dim_asset` | `entity_id` | `glpi vw_dim_entity` | `entity_id` |
| 22 | `glpi vw_fact_problems` | `entity_id` | `glpi vw_dim_entity` | `entity_id` |
| 23 | `glpi vw_fact_changes` | `entity_id` | `glpi vw_dim_entity` | `entity_id` |
| 24 | `glpi vw_fact_projects` | `entity_id` | `glpi vw_dim_entity` | `entity_id` |

> Com esses 6 relacionamentos, um único slicer com `vw_dim_entity[entity_name]` filtra
> simultaneamente tickets, ativos, problemas, mudanças e projetos em todas as páginas.

---

## 4. Views sem relacionamento (standalone)

Estas views são usadas diretamente em visuais sem precisar de relacionamento:

| View | Uso recomendado |
|---|---|
| `vw_sla_monthly` | Gráfico de linha SLA compliance % por mês |
| `vw_volume_trend` | Gráfico de barras volume mensal |
| `vw_cmdb_summary` | Tabela/treemap de inventário por tipo |
| `vw_entity_overview` | Cartões KPI por filial |
| `vw_entity_sla_monthly` | Gráfico SLA por entidade |
| `vw_entity_asset_distribution` | Donut de ativos por filial |
| `vw_rack_inventory` | Tabela de inventário de racks |
| `vw_fact_satisfaction_summary` | Gauge NPS por mês |
| `vw_fact_kb_usage` | Top artigos KB |

---

## 5. Estrutura dos 8 Dashboards

| Página | Título | Audiência | Views principais |
|---|---|---|---|
| p01 | Overview Executivo | C-Level | `vw_fact_tickets`, `DimDate`, `vw_volume_trend` |
| p02 | Desempenho de SLA | Gestores de TI | `vw_fact_tickets`, `vw_dim_sla`, `vw_sla_monthly` |
| p03 | Operações de Tickets | Coordenadores | `vw_fact_tickets`, `vw_backlog_open`, `vw_dim_category` |
| p04 | Produtividade | Supervisores | `vw_dim_technician`, `vw_tech_productivity` |
| p05 | Tendências & Padrões | Analistas | `vw_volume_trend`, `vw_fact_tickets` |
| p06 | Visão por Filial | Diretores regionais | `vw_dim_entity`, `vw_entity_overview`, `vw_entity_sla_monthly` |
| p07 | CMDB & Ativos | Especialistas | `vw_dim_asset`, `vw_fact_asset_tickets`, `vw_cmdb_summary` |
| p08 | Storytelling Flow | Todos | Mapa de relacionamentos + guia narrativo |

Especificações completas de cada página em `powerbi/pages/`.

---

## 6. Dicas de Performance

- Use **Import Mode** (padrão) — dados em cache, renderização rápida
- **Não use DirectQuery** com este dataset de demonstração — o banco não está otimizado para queries ad-hoc
- Configure refresh agendado via **Power BI Service + On-Premises Data Gateway** para produção
- O dataset de demonstração tem ~1.071 tickets e carrega em < 5 segundos

---

## 7. Arquivo .pbit (Template)

Para exportar o relatório como template reutilizável:

1. **Arquivo → Exportar → Modelo do Power BI (.pbit)**
2. Adicione uma descrição e salve como `powerbi/glpi_analytics.pbit`
3. Outros analistas abrem o `.pbit`, informam servidor/credenciais e os dados são carregados frescos

> O arquivo `.pbit` contém o modelo, medidas DAX e visuais, mas **não contém dados**.


