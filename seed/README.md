# Seed — Dataset de Demonstração

Scripts Python para popular o banco GLPI com dados sintéticos realistas para desenvolvimento e testes.

**Atenção**: estes scripts modificam o banco de dados. Use exclusivamente em ambientes de desenvolvimento/demonstração, nunca em produção.

---

## Pré-requisitos

```bash
# Banco GLPI rodando (Docker)
docker compose up -d

# Ambiente Python
python -m venv .venv
.venv/Scripts/activate   # Windows
pip install mysql-connector-python
```

---

## Ordem de execução

Execute nesta sequência — cada script é idempotente (aborta se os dados já existem):

```bash
PYTHON=.venv/Scripts/python.exe

# 1. Base: tickets, usuários, grupos, categorias, SLAs
$PYTHON seed/seed_glpi.py

# 2. CMDB: computadores, rede, problemas, mudanças, projetos
$PYTHON seed/seed_extended.py

# 3. Softwares, licenças, instalações, sistemas operacionais
$PYTHON seed/seed_expansion_1.py

# 4. Fornecedores, contratos, infocoms (financeiro)
$PYTHON seed/seed_expansion_2.py

# 5. Documentos, KB, telefones, periféricos
$PYTHON seed/seed_expansion_3.py

# 6. Follow-ups, tarefas, satisfação, vínculos problema-mudança
$PYTHON seed/seed_expansion_4.py

# 7. Infraestrutura de racks (DC São Paulo — Matriz)
$PYTHON seed/seed_racks.py

# 8. Migração para modelo geográfico (Empresa/Matriz/Filiais)
$PYTHON seed/refactor_entities.py

# 9. Validação final de integridade referencial
$PYTHON seed/validate_integrity.py
```

---

## Inventário de scripts

| Script | O que cria | Idempotente? |
|---|---|---|
| `seed_glpi.py` | 1.071 tickets (Jan/24–Dez/25), 62 usuários, 3 grupos, 26 categorias, 6 SLAs | ✅ |
| `seed_extended.py` | 65 computadores (15 SRV + 50 WS), 12 equipamentos de rede, 25 problemas, 18 mudanças, 6 projetos | ✅ |
| `seed_expansion_1.py` | 28 softwares, 28 versões, 28 licenças, 608 instalações, 65 vínculos com OS | ✅ |
| `seed_expansion_2.py` | 8 fornecedores (4 globais + 4 Matriz), 8 contratos, 77 infocoms | ✅ |
| `seed_expansion_3.py` | 18 documentos, 18 artigos KB, 30 telefones, 168 periféricos | ✅ |
| `seed_expansion_4.py` | 444 follow-ups, 178 tarefas de ticket, 712 avaliações de satisfação, 60 tarefas de problema, 30 vínculos mudança-problema | ✅ |
| `seed_racks.py` | 2 tipos de rack, 1 sala DC, 3 racks (42U), 27 itens instalados | ✅ (aborta se racks existem) |
| `seed_multi_entity.py` | ⚠️ **OBSOLETO** — criava entidades funcionais (TI/Ops/Fin). Substituído por `refactor_entities.py`. Não re-executar. | ✅ (aborta se >1 entidade) |
| `refactor_entities.py` | Migra para modelo geográfico: Empresa(0) → Matriz(4), Filial SP(5), Filial RJ(6), Filial MG(7) | ✅ (aborta se Matriz existe) |
| `audit_schemas.py` | Inspeciona schema do banco (diagnóstico — sem modificações) | — |
| `validate_integrity.py` | Valida integridade referencial de todos os 14 tipos de ativo | — |

---

## Volumes do dataset após seed completo

| Categoria | Qtde |
|---|---|
| Entidades | 5 (Empresa + Matriz + 3 Filiais) |
| Usuários | 62 (1 admin + 11 técnicos + 50 solicitantes) |
| Tickets | 1.071 |
| Computadores | 65 (15 SRV + 50 WS) |
| Equipamentos de rede | 12 |
| Racks | 3 (42U, DC São Paulo) |
| Monitores | 30 |
| Impressoras | 8 |
| Telefones | 30 |
| Periféricos | 168 |
| Problemas | 25 |
| Mudanças | 18 |
| Projetos | 6 |
| Softwares | 28 |
| Instalações de SW | 608 |
| Fornecedores | 8 |
| Contratos | 8 |
| Infocoms | 77 |
| Artigos KB | 18 |
| Follow-ups | 444 |
| Tarefas de tickets | 178 |
| Avaliações de satisfação | 712 |
| **Views SQL totais** | **32** |
