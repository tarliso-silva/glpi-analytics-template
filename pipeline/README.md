# Pipeline — GLPI → Power BI

Este diretório contém o pipeline de ingestão e atualização automática dos dados do GLPI no Power BI.

---

## Arquivos

| Arquivo | Função |
|---|---|
| `deploy_views.py` | Implanta / atualiza todas as SQL views no banco GLPI |
| `powerbi_refresh.py` | Dispara refresh do dataset via Power BI REST API |

---

## Arquitetura

```
MariaDB/MySQL (GLPI)
        │
        ▼
  [SQL Views] ◄── deploy_views.py (cria/atualiza as views)
        │
        ▼
  Power BI Desktop
  ┌─────────────────────────────────────────────┐
  │  Modo Import         │  Modo DirectQuery     │
  │  • dados em cache    │  • consulta ao vivo   │
  │  • refresh agendado  │  • sem refresh local  │
  │  • powerbi_refresh.py│  • requer Gateway     │
  └─────────────────────────────────────────────┘
        │
        ▼
  Power BI Service (nuvem)
  └─ Dataset refresh agendado → relatórios sempre atualizados
```

---

## Uso Rápido

### 1. Implantar / atualizar as views SQL

```bash
# Aplicar todas as views
python pipeline/deploy_views.py

# Aplicar apenas uma view específica
python pipeline/deploy_views.py --only vw_entity_analytics.sql

# Simular sem executar (dry-run)
python pipeline/deploy_views.py --dry-run
```

### 2. Disparar refresh do Power BI

```bash
# Configurar variáveis de ambiente (copie .env.example para .env)
cp .env.example .env
# Edite .env e preencha as variáveis POWERBI_*

# Disparar uma vez
python pipeline/powerbi_refresh.py --once

# Loop contínuo (padrão: 60s — atenção aos limites da licença)
python pipeline/powerbi_refresh.py --interval 300

# Ver status dos últimos refreshes
python pipeline/powerbi_refresh.py --status
```

---

## Variáveis de Ambiente Necessárias

Adicione ao seu arquivo `.env`:

```env
# Banco de dados
DB_HOST=localhost
DB_PORT=3306
DB_NAME=glpi
DB_USER=glpi_readonly
DB_PASSWORD=sua_senha

# Power BI Service (para powerbi_refresh.py)
POWERBI_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
POWERBI_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
POWERBI_CLIENT_SECRET=seu_client_secret
POWERBI_WORKSPACE_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
POWERBI_DATASET_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
REFRESH_INTERVAL_SEC=300
```

---

## Estratégias de Atualização

| Estratégia | Intervalo | Requisito | Recomendado para |
|---|---|---|---|
| **DirectQuery** | Tempo real | Gateway on-premises | Ambientes de produção GLPI local |
| **Import + REST API** | Mín. 30 min (Premium) | Power BI Service + App no Entra ID | Ambientes de nuvem |
| **Import + Agendado** | Mín. 3h (Pro) | Power BI Service | Uso geral |
| **Streaming Dataset** | < 1 segundo | Push API | Dashboards executivos em tempo real |

> Para atualização a cada minuto consulte `docs/pipeline-guide.md` — seção DirectQuery e Streaming.

---

## Configuração do Service Principal (Power BI REST API)

1. No [portal Azure](https://portal.azure.com) → **App registrations** → New registration
2. Em **API permissions** adicione: `Power BI Service → Dataset.ReadWrite.All`
3. Gere um **Client Secret** em Certificates & secrets
4. No Power BI Service → Workspace → Settings → habilite **Service principals can use Fabric APIs**
5. Adicione o Service Principal como **Member** do workspace
