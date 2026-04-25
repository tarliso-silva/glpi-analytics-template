# Página 5 — Tendências & Padrões

**Pergunta respondida:** "Quando os problemas ocorrem? Há sazonalidade?"

---

## Layout (Canvas 1280×720)

```
┌────────────────────────────────────────────────────────────────────┐
│  Tendências & Padrões                      [Filtro: Período ▼]    │
├──────────┬──────────┬──────────┬──────────┬────────────────────────┤
│ MoM      │ Tickets  │ MoM SLA  │ Média    │  Previsão próx. 30d   │
│ Tickets  │ Prev. Mês│ Variação │ 3 meses  │  (tickets estimados)  │
├──────────┴──────────┴──────────┴──────────┴────────────────────────┤
│  [Gráfico de linha: Volume de tickets + média móvel 3 meses]      │
│  + banda de confiança (desvio padrão)                             │
│  Jan/24 ─────────────────────────────────────── Dez/25            │
├────────────────────┬───────────────────────────────────────────────┤
│  [Barras: Tickets  │  [Heatmap: Tickets por hora do dia × dia da  │
│   por dia da       │   semana — identifica picos de demanda]       │
│   semana]          │   00h 01h ... 08h 09h ... 17h 18h ... 23h   │
│  Seg Ter Qua Qui   │  Seg:  ░░░░▓▓▒▒██████▓▓░░░░                 │
│  Sex Sáb Dom       │  Sáb:  ░░░░░░░░░░▒▒░░░░░░                   │
├────────────────────┴───────────────────────────────────────────────┤
│  [Barras agrupadas: Variação MoM por prioridade]                   │
│  P1 P2 P3 P4 P5 — Mês atual vs. Mês anterior                     │
└────────────────────────────────────────────────────────────────────┘
```

---

## Visuais Detalhados

### KPI Cards de Tendência
| Card | Medida | Contexto |
|---|---|---|
| MoM Tickets | `[MoM Ticket Change %]` | +/- com ícone de seta |
| Tickets Mês Anterior | `[Tickets Created (Prev Month)]` | referência |
| MoM SLA | Variação SLA vs mês anterior | + bom, - ruim |
| Média 3 meses | `AVERAGEX(DATESINPERIOD(..., -3, MONTH), [Tickets Created])` | linha base |

### Gráfico de Linha — Série Temporal + Média Móvel
- **Fonte**: `vw_volume_trend`
- **Série principal**: `tickets_created` por `year_month` (linha sólida azul)
- **Média móvel 3m**: calculada via DAX com DATESINPERIOD (linha tracejada)
- **Banda de variação**: ± 1 desvio padrão (preenchimento transparente)
- **Eventos anotados**: picos anômalos marcados (tooltip explica)
- **Projeção 30d**: linha pontilhada à direita da data atual (LinearRegression com DAX)

```dax
// Média móvel 3 meses
[3M Moving Avg] =
AVERAGEX(
    DATESINPERIOD(vw_volume_trend[period_date], LASTDATE(vw_volume_trend[period_date]), -3, MONTH),
    [Tickets Created]
)

// Crescimento YoY
[YoY Ticket Growth %] =
DIVIDE(
    [Tickets Created] -
    CALCULATE([Tickets Created], DATEADD(vw_volume_trend[period_date], -1, YEAR)),
    CALCULATE([Tickets Created], DATEADD(vw_volume_trend[period_date], -1, YEAR)),
    BLANK()
)
```

### Barras por Dia da Semana
- **Eixo X**: `WEEKDAY(vw_fact_tickets[created_at])`
- **Métrica**: `COUNT(ticket_id)` normalizado por número de semanas no período
- **Cor**: gradiente por volume
- **Insight esperado**: picos na segunda-feira (acúmulo do final de semana)

### Heatmap Hora × Dia da Semana
- **Visual**: Matrix com formatação condicional de fundo
- **Linhas**: dia da semana (Seg–Dom)
- **Colunas**: hora do dia (0–23)
- **Valor**: contagem de tickets criados
- **Cor**: branco (0) → azul escuro (máximo)
- **Uso prático**: escalonar equipes nos horários de pico

### Barras MoM por Prioridade
- **Agrupamento**: `priority_label`
- **Barras**: mês atual vs. mês anterior lado a lado
- **Cor**: azul=atual, cinza=anterior
- **Linha zero**: desvios positivos = crescimento, negativos = redução

---

## Slicers
| Slicer | Campo |
|---|---|
| Intervalo de datas | `'Date'[Date]` |
| Granularidade | Mês / Semana / Dia (botão de seleção) |
| Tipo de ticket | `ticket_type` |

---

## Navegação
- **← Produtividade** → p04
- **→ Filiais** → p06

---

## Medidas DAX adicionais
```dax
[Tickets Created (Prev Month)]
[MoM Ticket Change]
[MoM Ticket Change %]
[3M Moving Avg]      // nova
[YoY Ticket Growth %] // nova

// Dia da semana de pico (texto para card)
[Peak Weekday] =
MAXX(
    TOPN(1,
        ADDCOLUMNS(
            VALUES(vw_fact_tickets[weekday_name]),
            "@cnt", CALCULATE(COUNTROWS(vw_fact_tickets))
        ),
        [@cnt], DESC
    ),
    [weekday_name]
)
```
