# Página 1 — Overview Executivo

**Pergunta respondida:** "Como está nossa operação de TI hoje?"

---

## Layout (Canvas 1280×720)

```
┌────────────────────────────────────────────────────────────────────┐
│  [Logo] GLPI Service Desk — Overview         [Filtro: Período ▼]  │
├──────────┬──────────┬──────────┬──────────┬──────────┬────────────┤
│ Total    │  Abertos │  SLA %   │  MTTR    │  Backlog │  Satisfação│
│ Tickets  │          │          │  (horas) │  > 7d    │  Média     │
│  1.071   │   88     │  84,2%   │  18,3h   │   12     │   4,1/5    │
├──────────┴──────────┴──────────┴──────────┴──────────┴────────────┤
│                                                                    │
│  [Gráfico de barras: Volume de Tickets por Mês]                   │
│  ← Jan/24 ─────────────────────────────── Dez/25 →               │
│                                                                    │
├────────────────────────────┬───────────────────────────────────────┤
│  [Rosca: Status dos Tickets│  [Mapa/Treemap: Tickets por Filial]  │
│   Aberto | Resolvido |     │   Matriz | Filial SP |               │
│   Fechado | Pendente]      │   Filial RJ | Filial MG              │
├────────────────────────────┴───────────────────────────────────────┤
│  [Tabela: Top 5 Categorias com mais tickets no período]            │
│  Categoria | Abertos | Fechados | SLA% | MTTR(h) | Tendência ↑↓  │
└────────────────────────────────────────────────────────────────────┘
```

---

## Visuais Detalhados

### KPI Cards (linha superior — 6 cartões)
| Card | Medida DAX | Formato | Meta (linha ref.) |
|---|---|---|---|
| Total Tickets | `[Total Tickets]` | Número | — |
| Tickets Abertos | `[Open Tickets]` | Número | Alerta se > 100 |
| Conformidade SLA | `[SLA Compliance Rate %]` | % | 90% (linha vermelha) |
| MTTR | `[Avg Resolution Time (hrs)]` | horas | 24h |
| Backlog > 7d | `[Aged Tickets (> 7 days)]` | Número | 0 (meta) |
| Satisfação Média | `AVG(vw_fact_satisfaction_summary[avg_score])` | 1 decimal | 4,0 |

**Formatação condicional dos cards:**
- SLA < 80% → fundo vermelho
- SLA 80–90% → fundo amarelo
- SLA ≥ 90% → fundo verde
- MTTR > 48h → fundo vermelho

### Gráfico de Volume por Mês (barras agrupadas)
- **Eixo X**: `vw_volume_trend[year_month]`
- **Barras**: `vw_volume_trend[tickets_created]` (azul) + `vw_volume_trend[tickets_resolved]` (verde)
- **Linha overlay**: `vw_volume_trend[sla_compliance_pct]` (eixo secundário Y)
- **Interação**: clique em uma barra filtra o cartão KPI e a tabela inferior
- **Tooltip**: `avg_resolution_hrs`, total por prioridade

### Rosca de Status
- Segmentos: New / Processing / Pending / Solved / Closed
- Filtro de detalhe: clique → drill-through para p03 (Operações)
- Legenda colorida: vermelho=aberto, amarelo=pendente, verde=resolvido/fechado

### Treemap de Filiais
- Grupo: `vw_fact_tickets[entity_name]`
- Tamanho: `[Total Tickets]`
- Cor: `[SLA Compliance Rate %]` (divergente: vermelho → verde)
- Clique → filtra toda a página pela filial selecionada
- Tooltip: tickets abertos, MTTR, SLA%

### Tabela Top 5 Categorias
- Colunas: `category_name | total_tickets | open_tickets | sla_pct | avg_resolution_hrs`
- Ordenação padrão: por `total_tickets DESC`
- Ícones de tendência (calculados com DATEADD MoM)
- Drill-through para p03 ao clicar na categoria

---

## Slicers (Filtros)
| Slicer | Campo | Tipo | Posição |
|---|---|---|---|
| Período | `vw_dim_date[date]` | Intervalo de datas | Canto superior direito |
| Entidade/Filial | `vw_fact_tickets[entity_name]` | Lista | Lateral esquerda (recolhível) |
| Prioridade | `vw_fact_tickets[priority_label]` | Caixa de seleção múltipla | Lateral esquerda |

---

## Navegação
- Botão **"→ Análise de SLA"** (canto inferior direito) → p02
- Botão **"↗ Produtividade"** → p04

---

## Medidas DAX utilizadas
```dax
[Total Tickets]
[Open Tickets]
[SLA Compliance Rate %]
[Avg Resolution Time (hrs)]
[Aged Tickets (> 7 days)]
[Tickets Created]
[MoM Ticket Change %]
```
