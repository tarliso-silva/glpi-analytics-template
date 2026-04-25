# Página 8 — Fluxo Narrativo (Storytelling Guide)

**Propósito:** Documenta a lógica de navegação entre páginas e os roteiros de apresentação para cada audiência.

---

## 1. O Conceito de Storytelling no Power BI

Dashboards eficazes não exibem dados — eles **respondem perguntas** e **guiam decisões**.

Cada página deste relatório foi projetada como um capítulo de uma história:

```
SITUAÇÃO → COMPLICAÇÃO → RESOLUÇÃO
(p01-02)    (p03-05)      (p06-07)
```

| Fase | Páginas | Pergunta central |
|---|---|---|
| **Situação** | p01 Overview | Onde estamos? |
| **Complicação** | p02 SLA, p03 Ops | O que está errado? |
| **Diagnóstico** | p04 Produtividade, p05 Tendências | Por quê está acontecendo? |
| **Contexto** | p06 Filiais, p07 CMDB | Onde e com o quê? |
| **Síntese** | p08 (esta página) | O que fazer? |

---

## 2. Mapa de Navegação Entre Páginas

```
┌─────────────────────────────────────────────────────────┐
│                    p01 OVERVIEW                         │
│                  (ponto de entrada)                     │
└──────┬──────────────────┬────────────────┬──────────────┘
       │                  │                │
       ▼                  ▼                ▼
  p02 SLA           p03 OPERAÇÕES    p06 FILIAIS
       │                  │                │
       ▼                  ▼                ▼
  (drill p03)       p04 PRODUTIV.   p07 CMDB
                         │
                         ▼
                    p05 TENDÊNCIAS
                         │
                         ▼
                    p06 FILIAIS ────► p07 CMDB
```

### Conexões Drill-Through (contextuais)
| De | Para | Gatilho |
|---|---|---|
| p01 (categoria) | p03 | Clique na categoria na tabela |
| p02 (ticket violado) | Detalhe inline | Hover/tooltip |
| p03 (ativo vinculado) | p07 | Ctrl+clique no nome do ativo |
| p06 (filial) | p01 filtrado | Botão "Ver detalhes" |
| p07 (ativo) | Sub-página de detalhe | Botão direito → drill-through |

---

## 3. Roteiros de Apresentação por Audiência

### 3.1 Para C-Level / Diretoria (15 minutos)

**Roteiro:**
1. **p01** → "Temos X tickets este mês, SLA em Y% — nossa meta é 90%"
2. **p02** → "O problema está concentrado nas prioridades 4-5 e na categoria [X]"
3. **p06** → "A Filial RJ está com pior SLA — 72% — requer atenção imediata"
4. **p01** → "Ação proposta: reforçar equipe na Filial RJ nas categorias [X,Y]"

**Visuais principais:** Cards de KPI + Treemap de Filiais + Gráfico SLA mensal

---

### 3.2 Para Gestores de TI (30 minutos)

**Roteiro:**
1. **p01** → Visão geral do período
2. **p02** → Drill nas violações de SLA por grupo
3. **p04** → Análise de carga por técnico
4. **p05** → Padrões sazonais (picos às segundas?)
5. **p03** → Backlog atual e tickets críticos

**Foco:** Scatter Volume×MTTR (p04) + Heatmap horário (p05)

---

### 3.3 Para Técnicos / Analistas (self-service)

**Acesso livre** a todas as páginas com filtros ativos.

**Percurso sugerido:**
- Começa em p03 (operações do dia a dia)
- Usa p05 (tendências) para antecipar volume
- Consulta p07 (CMDB) para identificar ativos problemáticos

---

## 4. Princípios de Design Aplicados

### Consistência Visual
| Elemento | Padrão adotado |
|---|---|
| Paleta primária | Azul #1A73E8 (dados), Vermelho #EA4335 (alertas), Verde #34A853 (metas) |
| Fonte | Segoe UI 10pt padrão, 12pt títulos |
| Fundo | Branco #FFFFFF com painéis cinza claro #F8F9FA |
| Filtro de período | Sempre no canto superior direito, todas as páginas |
| Botões de navegação | Canto inferior direito, sempre visíveis |

### Hierarquia de Informação
1. **Primário** (topo): KPIs mais críticos — lidos em 3 segundos
2. **Secundário** (meio): gráficos de análise — contexto em 10 segundos
3. **Terciário** (baixo): tabelas de detalhe — para investigação

### Regras de Formatação Condicional
| Indicador | Verde | Amarelo | Vermelho |
|---|---|---|---|
| SLA% | ≥ 90% | 80–89% | < 80% |
| MTTR | ≤ 24h | 24–48h | > 48h |
| Backlog (dias) | ≤ 7d | 7–30d | > 30d |
| Licenças (uso%) | 50–100% | > 100% | < 30% |
| Tickets/Técnico | próximo à média | > 1.5× média | > 2× média |

---

## 5. Estrutura de Relacionamentos do Modelo Power BI

```
vw_dim_date (Date)
  │  [date] ──────────────────────────────────────────┐
  │                                                   │
  │  1:N                                              │ 1:N
  ▼                                                   ▼
vw_fact_tickets ──────────────────► vw_glpi_tickets
  │ [ticket_id]                      (espelho enriquecido)
  │
  ├──[sla_id]──────── vw_dim_sla
  ├──[category_id]─── vw_dim_category
  ├──[group_id]─────── vw_dim_group
  ├──[technician_id]── vw_dim_technician
  └──[asset_id]─────── vw_dim_asset
                          │
                          ├── vw_fact_asset_incidents
                          ├── vw_fact_asset_financials
                          └── vw_rack_inventory

vw_entity_overview ──────── vw_entity_sla_monthly
                    └─────── vw_entity_asset_distribution
                    └─────── vw_entity_project_performance

vw_fact_problems ──────────── (via ticket) vw_fact_tickets
vw_fact_changes  ──────────── (via ticket) vw_fact_tickets
vw_fact_projects ──────────── vw_fact_project_tasks
```

### Tipo de relacionamento recomendado
- Todas as relações são **1:N** (dimensão:fato)
- Cross-filter direction: **Single** (dimensão → fato)
- Exceção: `vw_dim_date` ↔ `vw_fact_tickets` usa **USERELATIONSHIP** no DAX para múltiplas datas

---

## 6. Checklist de Publicação

Antes de publicar no Power BI Service:

- [ ] Dataset configurado com credenciais do usuário read-only (`glpi_readonly`)
- [ ] Agendamento de refresh configurado (mín. diário)
- [ ] RLS (Row-Level Security) configurado se houver restrição por filial
- [ ] Todos os visuais testados com filtros de data extremos
- [ ] Tooltip personalizado validado em todos os gráficos
- [ ] Navegação entre páginas testada em modo apresentação (F11)
- [ ] Relatório exportado como `.pbit` e salvo em `powerbi/`
