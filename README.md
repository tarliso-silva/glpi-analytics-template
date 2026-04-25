# GLPI Analytics Template

Template completo para análise de dados do **GLPI** (IT Service Management) no **Power BI** — cobrindo todos os domínios ITSM com indicadores, medidas DAX, especificações de dashboards com storytelling e pipeline de atualização automática.

> **Stack**: MariaDB 10.7 (Docker) · GLPI 10.x · Python 3.11+ · Power BI Desktop
>
> **Conector Power BI**: MySQL Connector/NET **8.0.33** (obrigatório — veja seção 4)

---

## Estrutura do projeto

```
glpi-analytics-template/
│
├── sql/              # 33 SQL views — camada analítica sobre o GLPI
├── dax/              # Medidas DAX organizadas por domínio (85+ medidas)
├── powerbi/          # Especificações completas de dashboards (storytelling)
│   └── pages/        # 8 páginas com layout, visuais, DAX e navegação
├── pipeline/         # Pipeline de deploy e refresh automático
├── seed/             # Scripts Python para dataset de demonstração
├── docs/             # Documentação do modelo de dados e relacionamentos
└── config/           # Configuração, premissas e limitações do ambiente
```

---

## O que este template entrega

### 33 SQL Views prontas
Organizadas em 5 grupos de dependência — do ticket base ao inventário de racks:
- **Core**: `vw_glpi_tickets`, `vw_fact_tickets`
- **Star Schema**: dims de categoria, técnico, grupo, SLA, ativo
- **CMDB & ITIL**: problemas, mudanças, projetos, ativos
- **Financeiro & SW**: licenças, contratos, infocoms, KB, satisfação
- **Entidades & DC**: `vw_dim_entity` + visão por filial + inventário de racks

### 85+ Medidas DAX
| Arquivo | Domínio |
|---|---|
| `dax/01_core_measures.dax` | Tickets, SLA, MTTR, Backlog, Produtividade, Tendências |
| `dax/02_entity_measures.dax` | Filiais geográficas, Racks/DC |
| `dax/03_cmdb_measures.dax` | CMDB, Financeiro, Softwares, KB, Satisfação, ITIL, Projetos |

### 8 Páginas de Dashboard (storytelling completo)
Fluxo narrativo: **Situação → Complicação → Diagnóstico → Contexto**

| Página | Foco | Audiência |
|---|---|---|
| p01 Overview Executivo | KPIs globais + tendência de volume | C-Level |
| p02 Desempenho de SLA | Violações por categoria, grupo, filial | Gestores de TI |
| p03 Operações de Tickets | Backlog, ciclo de vida, funil | Coordenadores |
| p04 Produtividade | Ranking de técnicos, scatter carga×MTTR | Supervisores |
| p05 Tendências & Padrões | Série temporal, heatmap hora×dia, MoM | Analistas |
| p06 Visão por Filial | Scorecard semáforo por entidade | Diretores regionais |
| p07 CMDB & Ativos | Top ativos com incidentes, racks, licenças | Especialistas |
| p08 Storytelling Flow | Guia narrativo + mapa de relacionamentos | Todos |

### Pipeline de atualização
```bash
# Implantar todas as views no banco
python pipeline/deploy_views.py

# Disparar refresh do dataset no Power BI Service
python pipeline/powerbi_refresh.py --interval 300
```

---

## Início rápido

### Pré-requisitos
- Docker Desktop (para rodar GLPI + MariaDB em containers)
- Python 3.11+ com `mysql-connector-python`
- Power BI Desktop (gratuito)

### 1. Subir o ambiente

```bash
git clone https://github.com/tarliso-silva/glpi-analytics-template
cd glpi-analytics-template
cp .env.example .env   # ajuste as credenciais

docker compose up -d   # sobe GLPI + MariaDB + PostgreSQL(DW)
```

### 2. Popular com dados de demonstração

```bash
python -m venv .venv ; .venv\Scripts\activate
pip install mysql-connector-python

python seed/seed_glpi.py
python seed/seed_extended.py
python seed/seed_expansion_1.py
python seed/seed_expansion_2.py
python seed/seed_expansion_3.py
python seed/seed_expansion_4.py
python seed/seed_racks.py
python seed/refactor_entities.py
python seed/validate_integrity.py   # deve reportar 0 erros
```

### 3. Implantar as views SQL

```bash
.venv\Scripts\python.exe pipeline/deploy_views.py
# → 33 views criadas/atualizadas | Erros: 0
```

### 4. Instalar o conector MySQL para Power BI

> **Atenção**: Power BI requer o **MySQL Connector/NET versão 8.0.x**.
> A versão 9.x é incompatível. O conector MariaDB ODBC exige driver separado — não use.

1. Baixe e instale: [mysql-connector-net-8.0.33.msi](https://cdn.mysql.com/archives/mysql-connector-net-8.0/mysql-connector-net-8.0.33.msi)
2. Reinicie o Power BI Desktop após a instalação.

### 5. Conectar o Power BI ao banco de dados

1. Abra o Power BI Desktop
2. **Obter Dados → Banco de dados MySQL** *(não use MariaDB)*
3. Servidor: `localhost` · Database: `glpi`
4. Usuário: `glpi` · Senha: `glpi`
5. Importe **todas** as views `vw_*` (33 no total)
6. Veja `powerbi/README.md` para criar todos os relacionamentos e medidas DAX

---

## Dataset de demonstração

| Categoria | Volume |
|---|---|
| Tickets (Jan/2024 – Dez/2025) | 1.071 |
| Entidades geográficas | 5 (Empresa id=0, Matriz id=4, Filial SP id=5, Filial RJ id=6, Filial MG id=7) |
| Usuários | 62 |
| Ativos CMDB | 65 computadores + 12 rede + 30 monitores + 8 impressoras |
| Racks / Servidores | 3 racks × 42U no DC São Paulo |
| Problemas / Mudanças | 25 / 18 |
| Projetos | 6 (36 tarefas) |

---

## Roadmap

- [x] Dataset de demonstração (1.071 tickets, estrutura ITIL)
- [x] 33 SQL views cobrindo todos os domínios GLPI
- [x] `vw_dim_entity` + `entity_id` em todas as views de fato (filtragem por filial)
- [x] 24 relacionamentos configurados no Power BI
- [x] 85+ medidas DAX organizadas por domínio
- [x] 8 especificações de página com storytelling
- [x] Pipeline `deploy_views.py` + `powerbi_refresh.py`
- [ ] Arquivo `.pbit` Power BI Template pronto para usar
- [ ] Streaming Dataset (push em tempo real < 1 min)
- [ ] DirectQuery setup guide com On-Premises Gateway
- [ ] RLS (Row-Level Security) por filial
- [ ] Tema customizado Power BI (JSON)

---

## Contribuindo

1. Fork o repositório
2. Crie uma branch: `git checkout -b feature/nome-da-feature`
3. Commit: `git commit -m "feat: descrição"`
4. Push: `git push origin feature/nome-da-feature`
5. Abra um Pull Request

---

## Licença

MIT — veja [LICENSE](LICENSE) para detalhes.

