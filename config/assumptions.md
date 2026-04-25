# Premissas e ConfiguraÃ§Ã£o do Projeto

Este arquivo documenta todas as decisÃµes tÃ©cnicas, configuraÃ§Ãµes de ambiente e
limitaÃ§Ãµes conhecidas do GLPI Analytics Template. Atualize conforme seu ambiente.

---

## 1. Ambiente de Banco de Dados

| ParÃ¢metro | Valor | ObservaÃ§Ã£o |
|---|---|---|
| Engine | **MariaDB 10.7** | GLPI suporta MySQL e MariaDB; este template Ã© testado no 10.7 |
| Schema | `glpi` | Substitua `` `glpi`. `` nos SQLs se seu schema tiver outro nome |
| Host | `localhost` | Container Docker `glpi-mysql` na porta 3306 |
| UsuÃ¡rio (demo) | `glpi` | UsuÃ¡rio com acesso de leitura ao schema `glpi` |
| Senha (demo) | `glpi` | Mude em produÃ§Ã£o â€” use variÃ¡veis de ambiente |
| Charset | `utf8mb4` | Encoding padrÃ£o de todas as tabelas GLPI |
| Prefixo de tabelas | `glpi_` | PadrÃ£o de instalaÃ§Ã£o GLPI â€” ajuste se diferente |

---

## 2. Ambiente Docker (demonstraÃ§Ã£o)

| Container | Imagem | Porta | DescriÃ§Ã£o |
|---|---|---|---|
| `glpi-mysql` | MariaDB 10.7 | 3306 | Banco de dados GLPI |
| `glpi-app` | GLPI 10.x | 8080 | Interface web GLPI |
| `dw-postgres` | PostgreSQL | 5432 | Data Warehouse auxiliar |

```bash
# Subir todos os containers
docker compose up -d

# Verificar se estÃ£o rodando
docker ps
```

---

## 3. Conector Power BI (crÃ­tico)

| ParÃ¢metro | Valor |
|---|---|
| Driver correto | **MySQL Connector/NET 8.0.33** |
| Entrada no Power BI | **Banco de dados MySQL** (nÃ£o MariaDB) |
| URL de download | `https://cdn.mysql.com/archives/mysql-connector-net-8.0/mysql-connector-net-8.0.33.msi` |

> **âš ï¸ AtenÃ§Ã£o**: MySQL Connector/NET 9.x Ã© incompatÃ­vel com o Power BI.
> O conector MariaDB no Power BI requer um driver ODBC separado que nÃ£o estÃ¡
> incluÃ­do neste projeto. Use sempre o MySQL Connector/NET 8.0.33.

---

## 4. Python e Pipeline

| ParÃ¢metro | Valor |
|---|---|
| VersÃ£o Python | 3.11+ |
| Caminho do executÃ¡vel | `.venv\Scripts\python.exe` (sempre caminho completo) |
| Pacote principal | `mysql-connector-python` |
| Deploy das views | `.venv\Scripts\python.exe pipeline/deploy_views.py` |
| Total de views | 33 (`Views aplicadas: 33 | Erros: 0`) |

> **Nunca use** `python -c "..."` para inline code â€” sempre crie arquivos `.py`.

---

## 5. Hierarquia de Entidades GLPI

```
Empresa (id=0)                          â† raiz corporativa
â”œâ”€ Matriz       (id=4, level=2)         â† sede SP â€” TI, infra, ITSM
â”œâ”€ Filial SP    (id=5, level=2)         â† operaÃ§Ãµes regionais SP
â”œâ”€ Filial RJ    (id=6, level=2)         â† operaÃ§Ãµes Rio de Janeiro
â””â”€ Filial MG    (id=7, level=2)         â† operaÃ§Ãµes Belo Horizonte
```

- Grupos de suporte (`is_recursive=1`) ficam na Matriz e sÃ£o visÃ­veis em todas as filiais
- `vw_dim_entity` expÃµe todas as entidades para uso como slicer no Power BI
- `entity_id` foi adicionado a: `vw_fact_tickets`, `vw_glpi_tickets`, `vw_dim_asset`,
  `vw_fact_problems`, `vw_fact_changes`, `vw_fact_projects`

---

## 6. Limiares de SLA

Valores padrÃ£o conforme configuraÃ§Ã£o no dataset de demonstraÃ§Ã£o:

| Prioridade | Alvo de ResoluÃ§Ã£o | Minutos |
|---|---|---|
| 1 â€” Muito Baixa | 5 dias Ãºteis | 7.200 |
| 2 â€” Baixa | 3 dias Ãºteis | 4.320 |
| 3 â€” MÃ©dia | 1 dia Ãºtil | 480 |
| 4 â€” Alta | 4 horas | 240 |
| 5 â€” Muito Alta | 2 horas | 120 |
| 6 â€” CrÃ­tica | 1 hora | 60 |

> As views calculam compliance com base em `glpi_tickets.time_to_resolve` (campo nativo
> do GLPI, que respeita o calendÃ¡rio de horÃ¡rio comercial configurado na interface).
> O campo derivado `resolution_min` usa tempo de parede (wall-clock) para MTTR.

---

## 7. Intervalo de Datas

| ParÃ¢metro | Valor |
|---|---|
| InÃ­cio dos dados histÃ³ricos | Janeiro de 2024 |
| Fim dos dados histÃ³ricos | Dezembro de 2025 |
| DimDate (Power BI) | `CALENDAR(DATE(2024,1,1), DATE(2026,12,31))` |

---

## 8. LimitaÃ§Ãµes do MariaDB 10.7

| LimitaÃ§Ã£o | Workaround aplicado |
|---|---|
| Sem `WITH RECURSIVE` | DimensÃ£o de datas criada via DAX (`CALENDAR()`) no Power BI |
| `GROUP BY` nÃ£o aceita aliases | ExpressÃµes repetidas literalmente no `GROUP BY` |
| `year_month` Ã© palavra reservada | Envolto em backticks: `` `year_month` `` |
| `glpi_entities` sem `is_recursive` | NÃ£o referencie esta coluna em views ou seeds |
| `glpi_items_racks` sem `date_mod`/`date_creation` | NÃ£o use essas colunas em `vw_rack_inventory` |

---

## 9. ExclusÃ£o de Dados

CondiÃ§Ãµes aplicadas em **todas** as SQL views por padrÃ£o:

| CondiÃ§Ã£o | Motivo |
|---|---|
| `glpi_tickets.is_deleted = 1` | Tickets deletados (soft-delete) nÃ£o sÃ£o relevantes |
| `glpi_computers.is_deleted = 0` | Ativos deletados excluÃ­dos do CMDB |
| `glpi_users.is_active = 1` | UsuÃ¡rios inativos excluÃ­dos das dimensÃµes |

---

## 10. LimitaÃ§Ãµes Conhecidas

| LimitaÃ§Ã£o | Detalhe |
|---|---|
| Multi-atribuiÃ§Ã£o | Tickets com mÃºltiplos tÃ©cnicos ou grupos usam `MIN()` â€” apenas o primeiro vÃ­nculo Ã© selecionado |
| ConteÃºdo rico (HTML) | `ticket_title` e campos de descriÃ§Ã£o contÃªm HTML do GLPI â€” use Power Query para limpar se necessÃ¡rio |
| UsuÃ¡rios deletados | Nomes de tÃ©cnicos/solicitantes serÃ£o `NULL` se a conta foi excluÃ­da do GLPI |
| Idioma das categorias | Nomes de categorias ITIL estÃ£o no idioma da instalaÃ§Ã£o GLPI |
| Status/prioridade | Labels (`CASE`) estÃ£o em portuguÃªs â€” ajuste as expressÃµes se precisar de outro idioma |
| Relacionamento `supplier` | `vw_fact_supplier_contracts` e `vw_fact_asset_financials` ligam por texto (`supplier_name`), nÃ£o por ID numÃ©rico |


