# Página 7 — CMDB & Ativos

**Pergunta respondida:** "Quais ativos estão causando incidentes? Como está meu patrimônio de TI?"

---

## Layout (Canvas 1280×720)

```
┌────────────────────────────────────────────────────────────────────┐
│  CMDB & Ativos de TI                       [Filtro: Período ▼]    │
├──────────┬──────────┬──────────┬──────────┬────────────────────────┤
│ Total    │ Serv.    │ Desktops │ Rede     │  Valor Total Patrimônio│
│ Ativos   │ Críticos │          │          │  R$ ___.___.___        │
├──────────┴──────────┴──────────┴──────────┴────────────────────────┤
│                                                                    │
│  [Barras: Top 10 ativos com mais incidentes vinculados]           │
│  Ativo (nome) | # Incidentes | Tipo | Filial | MTTR médio        │
│                                                                    │
├────────────────────────┬───────────────────────────────────────────┤
│  [Rosca: Distribuição  │  [Inventário de Racks (tabela/matriz)]    │
│   de ativos por tipo]  │   Rack | U | Ativo | Tipo | Serial |     │
│   Computador           │   Incidentes | SN-001, SN-002...         │
│   Servidor             │                                           │
│   Rede                 │   RACK-DC-01 ▒▒▒▒▒▒▒▒▒▒ (SRV-001~005)  │
│   Monitor              │   RACK-DC-02 ▒▒▒▒▒▒▒▒▒▒ (SRV-006~010)  │
│   Impressora           │   RACK-DC-03 ▒▒▒▒▒▒▒▒▒▒ (SRV-011~015)  │
├────────────────────────┴───────────────────────────────────────────┤
│  [Tabela: Softwares — licenças vs. instalações]                   │
│  Software | Licenças | Instalações | % Uso | Vencimento          │
└────────────────────────────────────────────────────────────────────┘
```

---

## Visuais Detalhados

### KPI Cards de Patrimônio
| Card | Fonte |
|---|---|
| Total Ativos | `COUNT(vw_dim_asset[asset_id])` |
| Servidores Críticos | `CALCULATE(COUNT(...), asset_type = "Computer" && asset_name LIKE "SRV-%")` |
| Desktops | `CALCULATE(COUNT(...), asset_name LIKE "WS-%")` |
| Equipamentos de Rede | `CALCULATE(COUNT(...), asset_type = "NetworkEquipment")` |
| Valor Total | `SUM(vw_fact_asset_financials[value])` formatado em R$ |

### Barras — Top 10 Ativos por Incidentes
- **Fonte**: `vw_fact_asset_incidents`
- **Ordenação**: por `incident_count DESC`
- **Colunas**: `asset_name | incident_count | asset_type | entity_name | avg_resolution_hrs`
- **Cor**: por `asset_type`
- **Insight**: identifica ativos "hot spots" que precisam de manutenção preventiva
- **Drill-through**: clique → detalhe dos tickets vinculados ao ativo

### Rosca de Distribuição
- **Fonte**: `vw_cmdb_summary`
- **Segmentos**: Computer (servidor + desktop), NetworkEquipment, Monitor, Printer, Phone, Peripheral
- **Tooltip**: contagem, % do total, valor total R$
- **Clique**: filtra toda a página pelo tipo selecionado

### Inventário de Racks
- **Fonte**: `vw_rack_inventory`
- **Visual**: Matrix aninhada (Rack → Posição U → Ativo)
- **Colunas**: `rack_name | position_u | asset_name | asset_type | serial | incident_count`
- **Formatação**: posições com `incident_count > 0` destacadas em laranja
- **Alternativa visual**: usar visual customizado "Rack View" (AppSource) se disponível

```dax
[Rack Items]
[Rack Linked Incidents]
[Rack Utilisation]
```

### Tabela de Licenças de Software
- **Fonte**: `vw_fact_software_licenses`
- **Colunas**: `software_name | license_count | install_count | utilization_pct | expire_date`
- **Coluna calculada**:
  ```dax
  [License Utilization %] = DIVIDE([install_count], [license_count])
  ```
- **Formatação condicional**:
  - > 100% = vermelho (over-licensed — risco de auditoria)
  - < 50% = amarelo (sub-utilizado — desperdício)
  - 50–100% = verde
- **Alerta de vencimento**: `expire_date < TODAY() + 30` → ícone de relógio

---

## Sub-página: Detalhe de Ativo (Drill-through)

Ao fazer drill-through em qualquer ativo:
- Histórico de tickets vinculados ao ativo
- Linha do tempo de incidentes
- Contratos de manutenção associados (via `vw_fact_supplier_contracts`)
- Custo acumulado de suporte (estimativa baseada em MTTR × custo/hora)

---

## Slicers
| Slicer | Campo |
|---|---|
| Tipo de ativo | `asset_type` |
| Filial | `entity_name` |
| Rack | `rack_name` |
| Período | `'Date'[Date]` |

---

## Navegação
- **← Filiais** → p06
- **→ Visão Executiva** → p08

---

## Medidas DAX adicionais para CMDB
```dax
// Percentual de ativos com incidente no período
[Assets with Incidents %] =
DIVIDE(
    CALCULATE(DISTINCTCOUNT(vw_fact_asset_incidents[asset_id])),
    DISTINCTCOUNT(vw_dim_asset[asset_id]),
    BLANK()
)

// Valor total do patrimônio
[Total Asset Value] =
SUM(vw_fact_asset_financials[value])

// Ativos com licença expirada ou prestes a expirar (30d)
[Expiring Licenses] =
CALCULATE(
    COUNTROWS(vw_fact_software_licenses),
    vw_fact_software_licenses[expire_date] <= TODAY() + 30
)
```
