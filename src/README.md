# Optional Scripts — `/src`

This folder is reserved for optional helper scripts that support the analytics workflow. These scripts are **not required** for the core template (SQL views + DAX measures + Power BI) but can be useful for automation, testing, or advanced data refresh scenarios.

---

## What Belongs Here

| Type | Example Files | Purpose |
|---|---|---|
| Python scripts | `export_to_csv.py` | Export GLPI data to CSV for offline testing or staging environments |
| PowerShell scripts | `refresh_dataset.ps1` | Trigger a Power BI dataset refresh via the REST API |
| Shell scripts | `deploy_views.sh` | Apply all SQL view scripts to the database in one step |
| Jupyter notebooks | `exploration.ipynb` | Ad-hoc data exploration with pandas/matplotlib |

---

## Conventions

- Scripts must be **read-only** with respect to GLPI data — never write back to the GLPI database.
- Store database credentials in environment variables or a `.env` file (never hardcode them).
- Add a `.env.example` file alongside any script that requires environment variables.
- Include a brief docstring or comment block at the top of every script explaining its purpose and usage.

---

## Example: Deploying SQL Views

```bash
# deploy_views.sh (example — create this file when needed)
#!/usr/bin/env bash
set -euo pipefail

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-3306}"
DB_NAME="${DB_NAME:-glpi}"
DB_USER="${DB_USER:-glpi_readonly}"

for sql_file in ../sql/*.sql; do
    echo "Applying: $sql_file"
    mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p "$DB_NAME" < "$sql_file"
done

echo "All views deployed successfully."
```

---

## Example: Python Environment Setup

If you add Python scripts, create a `requirements.txt` in this folder:

```
mysql-connector-python>=8.0
pandas>=2.0
python-dotenv>=1.0
```

Install with:

```bash
pip install -r src/requirements.txt
```
