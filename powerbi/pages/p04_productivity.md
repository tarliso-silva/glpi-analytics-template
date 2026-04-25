# Página 4 — Produtividade das Equipes

**Pergunta respondida:** "Quem está performando e onde está a carga desbalanceada?"

---

## Layout (Canvas 1280×720)

```
┌────────────────────────────────────────────────────────────────────┐
│  Produtividade das Equipes                 [Filtro: Período ▼]    │
├──────────┬──────────┬──────────┬──────────┬────────────────────────┤
│ Técnicos │ Média    │ Técnico  │ Maior    │  Técnico com pior SLA  │
│ Ativos   │ Tickets/ │ Top      │ MTTR     │  (nome + %)            │
│          │ Técnico  │ (Nome)   │ (Nome)   │                        │
├──────────┴──────────┴──────────┴──────────┴────────────────────────┤
│  [Gráfico de barras: Tickets fechados por técnico no período]      │
│  Ordenado por volume DESC — linha horizontal = média do grupo     │
├────────────────────────┬───────────────────────────────────────────┤
│  [Scatter Plot:        │  [Mapa de calor semanal:                  │
│   Volume × MTTR        │   Técnico × Dia da semana                 │
│   por técnico]         │   (Heatmap de tickets fechados)]          │
│  X=tickets, Y=MTTR    │   Seg | Ter | Qua | Qui | Sex | Sáb | Dom │
│  Tamanho=SLA%          │                                           │
│  Cor=grupo             │                                           │
├────────────────────────┴───────────────────────────────────────────┘
│  [Tabela: Ranking completo de técnicos]                            │
│  Técnico | Grupo | Fechados | Abertos | MTTR(h) | SLA% | Reabertos│
└────────────────────────────────────────────────────────────────────┘
```

---

## Visuais Detalhados

### KPI Cards de Equipe
| Card | Cálculo |
|---|---|
| Técnicos Ativos | `[Active Technicians]` |
| Tickets por Técnico | `[Tickets per Technician]` |
| Top Performer | `MAXX(TOPN(1, vw_tech_productivity, [closed_tickets], DESC), [technician_name])` |
| Maior MTTR (técnico com problema) | `MAXX(TOPN(1, vw_tech_productivity, [avg_resolution_min], DESC), [technician_name])` |

### Barras por Técnico
- **Fonte**: `vw_tech_productivity`
- **Eixo Y**: `technician_name`
- **Barras**: `closed_tickets` (azul) + `open_tickets` (laranja, empilhado)
- **Linha de referência**: `[Tickets per Technician]` (média)
- **Técnicos muito acima**: possível sobrecarga
- **Técnicos muito abaixo**: possível gargalo de atribuição
- Ordenação: por `closed_tickets DESC`

### Scatter Plot: Volume × MTTR
- **Eixo X**: `closed_tickets`
- **Eixo Y**: `avg_resolution_min / 60` (em horas)
- **Tamanho do ponto**: `sla_compliance_pct`
- **Cor**: `group_name`
- **Quadrantes interpretativos**:
  - Alto volume + Baixo MTTR = ✓ Eficientes
  - Baixo volume + Alto MTTR = ⚠ Precisam de apoio
  - Alto volume + Alto MTTR = 🔴 Sobrecarregados
  - Baixo volume + Baixo MTTR = Ø Subutilizados

### Heatmap Semanal
- **Linhas**: `technician_name`
- **Colunas**: `day_of_week` (Seg–Dom)
- **Valor**: contagem de tickets fechados
- **Cor**: gradiente azul claro → azul escuro
- Identifica padrões de trabalho (picos às sextas? fins de semana?)

### Tabela Ranking
- **Fonte**: `vw_tech_productivity`
- **Colunas**: técnico | grupo | fechados | abertos | MTTR(h) | SLA% | reabertos
- **Coluna de reabertos**: `CALCULATE(COUNTROWS(...), ticket reaberto = 1)` — mede qualidade
- **Destaque condicional**: técnicos com SLA% < 70% em vermelho

---

## Slicers
| Slicer | Campo |
|---|---|
| Período | `'Date'[Date]` |
| Grupo/Equipe | `group_name` |
| Filial | `entity_name` |

---

## Navegação
- **← Operações** → p03
- **→ Tendências** → p05

---

## Medidas DAX adicionais
```dax
[Active Technicians]
[Tickets per Technician]

// Técnico com mais reaberturas (indicador de qualidade)
[Reopen Rate] =
DIVIDE(
    CALCULATE(COUNTROWS(vw_fact_tickets), vw_fact_tickets[reopen_count] > 0),
    [Total Tickets],
    BLANK()
)

// Carga balanceada (desvio padrão de tickets por técnico — quanto menor melhor)
[Workload Std Dev] =
STDEV.P(
    ADDCOLUMNS(
        VALUES(vw_tech_productivity[technician_name]),
        "@tickets", CALCULATE(SUM(vw_tech_productivity[closed_tickets]))
    )[@tickets]
)
```
