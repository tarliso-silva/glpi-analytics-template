# Página 6 — Visão por Filial (Geográfica)

**Pergunta respondida:** "Como cada unidade se compara? Qual filial precisa de atenção?"

---

## Layout (Canvas 1280×720)

```
┌────────────────────────────────────────────────────────────────────┐
│  Visão por Filial / Entidade               [Filtro: Período ▼]    │
├──────────┬──────────┬──────────┬──────────┬────────────────────────┤
│ Empresa  │ Matriz   │ Filial SP│ Filial RJ│  Filial MG             │
│ [SLA%]   │ [SLA%]   │ [SLA%]   │ [SLA%]   │  [SLA%]               │
│          │ ✓/⚠/🔴   │ ✓/⚠/🔴  │ ✓/⚠/🔴  │  ✓/⚠/🔴              │
├──────────┴──────────┴──────────┴──────────┴────────────────────────┤
│  [Gráfico de barras agrupadas: KPIs por filial]                    │
│  Grupos: Tickets | Abertos | SLA% | MTTR(h)                       │
│  Filiais no eixo X                                                 │
├────────────────────────┬───────────────────────────────────────────┤
│  [Gráfico de linha:    │  [Treemap: Ativos por tipo e filial]      │
│   SLA% ao longo do     │   Computadores | Monitores |              │
│   tempo por filial]    │   Impressoras  | Telefones |              │
│   (mesmas cores p/ fil)│   Periféricos  |                          │
│                        │   Tamanho = count, Cor = entity           │
├────────────────────────┴───────────────────────────────────────────┤
│  [Tabela comparativa por filial]                                   │
│  Filial | Tickets | Abertos | SLA% | MTTR(h) | Ativos | Projetos  │
└────────────────────────────────────────────────────────────────────┘
```

---

## Visuais Detalhados

### Cards por Filial (scorecard estilo semáforo)
Um card por entidade. Para cada uma:

| Campo | Fonte |
|---|---|
| Nome da entidade | `entity_name` |
| Total tickets | `[Entity Tickets]` |
| SLA% | `[Entity SLA Compliance %]` |
| Ícone status | Condicional: ≥90%=✓verde, 80–89%=⚠amarelo, <80%=🔴vermelho |

```dax
// Ícone semáforo por filial
[Entity SLA Icon] =
SWITCH(TRUE(),
    [Entity SLA Compliance %] >= 0.90, "✓",
    [Entity SLA Compliance %] >= 0.80, "⚠",
    "🔴"
)
```

### Barras Agrupadas — KPIs por Filial
- **Eixo X**: `entity_name`
- **Grupos de barras** (selecionável via botão): Tickets Total | Abertos | SLA% | MTTR
- **Linha de meta SLA**: 90% (eixo Y secundário)
- Facilita comparação direta entre filiais

### Gráfico de Linha — Evolução SLA por Filial
- **Fonte**: `vw_entity_sla_monthly`
- **Eixo X**: `year_month`
- **Séries**: uma linha por `entity_name` com cor fixa por filial
  - Matriz = azul escuro
  - Filial SP = laranja
  - Filial RJ = verde
  - Filial MG = roxo
- **Linha de meta**: 90% (tracejada cinza)

### Treemap de Ativos por Filial
- **Fonte**: `vw_entity_asset_distribution`
- **Hierarquia**: Filial → Tipo de ativo
- **Tamanho**: `asset_count`
- **Cor**: por `entity_name` (consistente com o gráfico de linhas)
- **Tooltip**: `total_value` (R$), `% do total`

### Tabela Comparativa
- **Fonte**: `vw_entity_overview` (1 linha por filial)
- Colunas: `entity_name | total_tickets | open_tickets | avg_resolution_hours | (join) asset_count | project_count`
- **Ordenação**: por `SLA% ASC` (pior primeiro)
- **Barra de dados**: na coluna tickets (proporcional)
- **Highlight**: linha com pior SLA em fundo vermelho suave

---

## Interações especiais

### Seletor de Filial (filtro de destaque)
- Clique em qualquer filial destaca toda a página para aquela filial
- Os outros visuais ficam em modo "comparison" (filial selecionada em cor sólida, demais em cinza)

### Drill-through para Filial Específica
- Clique com botão direito → "Ver detalhes da filial" → abre p01 filtrado pela filial

---

## Slicers
| Slicer | Campo |
|---|---|
| Período | `'Date'[Date]` |
| Filial | `entity_name` (destaque, não filtro) |

---

## Navegação
- **← Tendências** → p05
- **→ CMDB** → p07

---

## Medidas DAX utilizadas
```dax
[Entity Tickets]
[Entity SLA Compliance %]
[Entity SLA Breached]
[Entity Avg Resolution (hrs)]
[Entity Asset Value]
[Entity Asset Share %]
[Top Entity by Tickets]
[Worst SLA Entity]
[Entity SLA Icon]   // nova
```
