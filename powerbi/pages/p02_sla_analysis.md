# Página 2 — Desempenho de SLA

**Pergunta respondida:** "Onde e quando estamos quebrando SLA?"

---

## Layout (Canvas 1280×720)

```
┌────────────────────────────────────────────────────────────────────┐
│  SLA Performance                           [Filtro: Período ▼]    │
├──────────┬──────────┬──────────┬──────────┬────────────────────────┤
│ Conform. │ Violados │ % Viola- │  SLA     │  [Indicador: Tendência │
│ SLA      │          │  ção     │  p/ vencer│   MoM SLA +/- %]      │
├──────────┴──────────┴──────────┴──────────┴────────────────────────┤
│  [Gráfico de área: SLA % ao longo do tempo por filial]             │
│  ─ Matriz  ─ Filial SP  ─ Filial RJ  ─ Filial MG  ─── Meta 90%  │
├────────────────────┬───────────────────────────────────────────────┤
│  [Barras H:        │  [Matriz: SLA % por Prioridade × Grupo]       │
│   SLA% por         │                                               │
│   Categoria        │   Grupo        P1    P2    P3    P4    P5    │
│   (rank pior→melhor│   Infraestr.  95%   88%   72%   91%   60%   │
│   ordenado por %)] │   Sistemas    90%   85%   78%   88%   55%   │
│                    │   Redes       88%   80%   70%   85%   50%   │
└────────────────────┴───────────────────────────────────────────────┘
  [Tabela detalhada: Tickets que violaram SLA — últimos 30 dias]
  ID | Título | Prioridade | Grupo | Data abertura | Tempo excedido
```

---

## Visuais Detalhados

### KPI Cards
| Card | Medida | Meta |
|---|---|---|
| SLA Conformes | `[SLA Compliant Tickets]` | — |
| SLA Violados | `[SLA Breached Tickets]` | 0 |
| % Violação | `1 - [SLA Compliance Rate %]` | < 10% |
| SLA a Vencer (abertos ainda dentro do prazo) | Filtro `sla_status = "At Risk"` | — |

### Gráfico de Área — SLA ao longo do tempo
- **Fonte**: `vw_entity_sla_monthly`
- **Eixo X**: `year_month`
- **Séries**: uma linha por `entity_name` — conformidade mensal
- **Linha de meta**: constante 90% (Reference Line no eixo Y)
- **Cor**: vermelho quando a linha fica abaixo da meta
- **Tooltip**: within_sla, breached_sla, total tickets no mês

### Barras Horizontais — SLA por Categoria
- **Fonte**: `vw_fact_tickets` agrupado por `category_name`
- **Métrica**: `[SLA Compliance Rate %]`
- **Ordenação**: crescente (pior categoria primeiro → facilita priorização)
- **Formatação condicional**: vermelho < 70%, amarelo 70–89%, verde ≥ 90%
- **Drill-through**: clique na categoria → p03 filtrado

### Mapa de Calor — Prioridade × Grupo
- **Visual**: Matrix do Power BI
- **Linhas**: `vw_fact_tickets[group_name]`
- **Colunas**: `vw_fact_tickets[priority_label]`
- **Valor**: `[SLA Compliance Rate %]`
- **Formatação de fundo condicional**: gradiente verde→vermelho
- Permite identificar rapidamente qual grupo tem problema com qual prioridade

### Tabela de Violações Recentes
- **Filtro**: `sla_status IN ("Breached", "Breached (open)")`
- **Colunas**: `ticket_id | title | priority_label | group_name | created_at | resolution_time_minutes`
- **Coluna calculada**: `Excesso (h) = resolution_time_minutes - sla_target_min / 60`
- **Paginação**: top 20 por excesso decrescente

---

## Slicers
| Slicer | Campo |
|---|---|
| Período | `vw_dim_date[date]` |
| Prioridade | `priority_label` |
| Grupo/Equipe | `group_name` |
| Filial | `entity_name` |

---

## Navegação
- **← Overview** → p01
- **→ Operações** → p03
- **Drill-through**: tickets individuais abrem detalhe inline (tooltip)

---

## Medidas DAX utilizadas
```dax
[SLA Compliant Tickets]
[SLA Breached Tickets]
[SLA Compliance Rate %]
[Entity SLA Compliance %]
[Entity SLA Breached]
[Worst SLA Entity]
[MoM Ticket Change %]
```
