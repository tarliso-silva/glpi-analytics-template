# Página 3 — Operações de Tickets

**Pergunta respondida:** "O que está gerando volume e como está a fila?"

---

## Layout (Canvas 1280×720)

```
┌────────────────────────────────────────────────────────────────────┐
│  Operações de Tickets                      [Filtro: Período ▼]    │
├──────────┬──────────┬──────────┬──────────┬────────────────────────┤
│ Abertos  │ Novos    │ Resolvidos│ Pend.   │  [Gráfico velocímetro: │
│  hoje    │  hoje    │  hoje    │  hoje   │   Taxa de Resolução]    │
├──────────┴──────────┴──────────┴──────────┴────────────────────────┤
│                                                                    │
│  [Gráfico de barras empilhadas: Tickets por Categoria e Tipo]     │
│  (Incidente / Requisição / Problema / Mudança)                    │
│  Eixo X: categorias | Cores: tipo de ticket                       │
│                                                                    │
├────────────────────────┬───────────────────────────────────────────┤
│  [Funil: Ciclo de vida │  [Histograma: Distribuição de Idade       │
│   do Ticket]           │   do Backlog em dias]                    │
│  Criado→Atribuído      │   0-1d | 2-7d | 8-30d | 31-90d | >90d   │
│  →Resolvido→Fechado    │                                           │
│  (Volume em cada etapa)│                                           │
├────────────────────────┴───────────────────────────────────────────┤
│  [Tabela: Backlog aberto — ordenado por idade]                    │
│  ID | Prioridade | Categoria | Grupo | Solicitante | Dias Aberto  │
└────────────────────────────────────────────────────────────────────┘
```

---

## Visuais Detalhados

### KPI Cards Operacionais
| Card | Cálculo |
|---|---|
| Abertos hoje | `CALCULATE([Open Tickets], 'Date'[Date] = TODAY())` |
| Novos hoje | `CALCULATE([Tickets Created], 'Date'[Date] = TODAY())` |
| Resolvidos hoje | `CALCULATE([Tickets Resolved], 'Date'[Date] = TODAY())` |
| Taxa de resolução | `DIVIDE([Tickets Resolved], [Tickets Created])` em % |

### Barras por Categoria e Tipo
- **Fonte**: `vw_fact_tickets`
- **Eixo X**: `category_name` (top 10)
- **Cores**: `ticket_type` (Incidente=vermelho, Requisição=azul, etc.)
- **Ordenação**: por total decrescente
- **Tooltip**: `avg_resolution_hrs`, `sla_compliance_pct`
- **Drill-through**: clique abre detalhe dos tickets nessa categoria

### Funil do Ciclo de Vida
- Etapas: `Criado → Atribuído → Em andamento → Pendente → Resolvido → Fechado`
- Volume em cada etapa mostra onde há gargalo
- Fonte: `vw_fact_tickets` com `status_label`

### Histograma de Backlog (por faixa de idade)
- **Fonte**: `vw_backlog_open`
- **Faixas calculadas**: 
  ```dax
  Age Bucket = 
  SWITCH(TRUE(),
    vw_backlog_open[age_days] <= 1,   "0-1 dia",
    vw_backlog_open[age_days] <= 7,   "2-7 dias",
    vw_backlog_open[age_days] <= 30,  "8-30 dias",
    vw_backlog_open[age_days] <= 90,  "31-90 dias",
    "> 90 dias"
  )
  ```
- **Cor de alerta**: faixas > 30d em vermelho

### Tabela de Backlog
- **Fonte**: `vw_backlog_open`
- **Ordenação padrão**: `age_days DESC`
- **Formatação condicional**:
  - `age_days > 30` → linha vermelha
  - `age_days > 7` → linha amarela
  - Prioridade 4-5 → ícone de urgência

---

## Também inclui: Problemas e Mudanças Recentes

### Mini-tabela de Problemas Abertos
- **Fonte**: `vw_fact_problems`
- **Filtro**: `status != "Closed"`
- Colunas: `problem_id | title | linked_tickets | status | date_creation`

### Mini-tabela de Mudanças em Andamento  
- **Fonte**: `vw_fact_changes`
- **Filtro**: `status IN ("Processing", "Testing")`
- Colunas: `change_id | title | type_label | status | linked_tickets`

---

## Slicers
| Slicer | Campo |
|---|---|
| Período | `'Date'[Date]` |
| Tipo de Ticket | `vw_fact_tickets[ticket_type]` |
| Prioridade | `priority_label` |
| Grupo | `group_name` |

---

## Navegação
- **← SLA Analysis** → p02
- **→ Produtividade** → p04

---

## Medidas DAX adicionais para esta página
```dax
// Taxa de resolução no dia atual
[Today Resolution Rate] =
DIVIDE(
    CALCULATE([Tickets Resolved], 'Date'[Date] = TODAY()),
    CALCULATE([Tickets Created],  'Date'[Date] = TODAY()),
    BLANK()
)

// Backlog por faixa de idade
[Backlog 0-1d]  = CALCULATE(COUNTROWS(vw_backlog_open), vw_backlog_open[age_days] <= 1)
[Backlog 2-7d]  = CALCULATE(COUNTROWS(vw_backlog_open), vw_backlog_open[age_days] BETWEEN 2 AND 7)
[Backlog 8-30d] = CALCULATE(COUNTROWS(vw_backlog_open), vw_backlog_open[age_days] BETWEEN 8 AND 30)
[Backlog >30d]  = CALCULATE(COUNTROWS(vw_backlog_open), vw_backlog_open[age_days] > 30)
```
