"""
deploy_views.py — Implanta todas as SQL views do projeto no banco GLPI.

Aplica os 5 arquivos SQL em ordem correta de dependência:
  1. vw_glpi_tickets.sql      (view principal de tickets)
  2. vw_star_schema.sql       (star schema: fact + dims)
  3. vw_extended_analytics.sql (CMDB, problemas, mudanças, projetos)
  4. vw_analytics_v2.sql      (SW, contratos, financeiro, KB, satisfação)
  5. vw_entity_analytics.sql  (entidades geográficas + racks)

Uso:
  python pipeline/deploy_views.py
  python pipeline/deploy_views.py --only vw_entity_analytics.sql
  python pipeline/deploy_views.py --dry-run
"""

import argparse
import os
import re
import sys
import mysql.connector
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
DB = dict(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", 3306)),
    database=os.getenv("DB_NAME", "glpi"),
    user=os.getenv("DB_USER", "glpi"),
    password=os.getenv("DB_PASSWORD", "glpi"),
)

SQL_DIR = Path(__file__).parent.parent / "sql"

# Ordem de aplicação (dependência: tickets antes do star schema, etc.)
SQL_FILES = [
    "vw_glpi_tickets.sql",
    "vw_star_schema.sql",
    "vw_extended_analytics.sql",
    "vw_analytics_v2.sql",
    "vw_entity_analytics.sql",
]


# ── Helpers ───────────────────────────────────────────────────────────────────
def parse_statements(sql_text: str) -> list[str]:
    """Split SQL file into individual CREATE OR REPLACE VIEW statements."""
    # Remove single-line comments
    sql_text = re.sub(r"--[^\n]*", "", sql_text)
    parts = sql_text.split(";")
    return [
        s.strip() for s in parts
        if re.search(r"CREATE\s+(OR\s+REPLACE\s+)?VIEW", s, re.IGNORECASE)
    ]


def extract_view_name(stmt: str) -> str:
    m = re.search(r"VIEW\s+`?(\w+)`?", stmt, re.IGNORECASE)
    return m.group(1) if m else "?"


def apply_file(cur, sql_file: Path, dry_run: bool) -> tuple[int, int]:
    """Apply one SQL file. Returns (ok, errors)."""
    text = sql_file.read_text(encoding="utf-8")
    statements = parse_statements(text)
    ok = errors = 0
    for stmt in statements:
        name = extract_view_name(stmt)
        if dry_run:
            print(f"  [DRY-RUN] would apply: {name}")
            ok += 1
            continue
        try:
            cur.execute(stmt)
            print(f"  [OK]  {name}")
            ok += 1
        except Exception as ex:
            print(f"  [ERR] {name}: {ex}")
            errors += 1
    return ok, errors


def verify_views(cur):
    """Print row counts for all deployed views."""
    cur.execute("""
        SELECT table_name
        FROM information_schema.views
        WHERE table_schema = DATABASE()
          AND table_name LIKE 'vw_%'
        ORDER BY table_name
    """)
    views = [r[0] for r in cur.fetchall()]
    print(f"\n{'View':<40} {'Linhas':>8}")
    print("-" * 50)
    for v in views:
        try:
            cur.execute(f"SELECT COUNT(*) FROM `{v}`")
            n = cur.fetchone()[0]
            print(f"  {v:<38} {n:>8,}")
        except Exception as ex:
            print(f"  {v:<38}  ERRO: {ex}")
    print(f"\n  Total de views: {len(views)}")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Deploy GLPI analytics SQL views")
    parser.add_argument("--only", metavar="FILE", help="Apply only this SQL file")
    parser.add_argument("--dry-run", action="store_true", help="Parse only, do not execute")
    parser.add_argument("--verify", action="store_true", default=True,
                        help="Show row counts after deploy (default: on)")
    parser.add_argument("--no-verify", dest="verify", action="store_false")
    args = parser.parse_args()

    files = [SQL_DIR / args.only] if args.only else [SQL_DIR / f for f in SQL_FILES]
    missing = [f for f in files if not f.exists()]
    if missing:
        print(f"ERRO: arquivos não encontrados: {[str(f) for f in missing]}")
        sys.exit(1)

    print("=" * 60)
    print("  GLPI Analytics — Deploy de Views SQL")
    print("=" * 60)
    if args.dry_run:
        print("  *** MODO DRY-RUN — nenhuma alteração será feita ***\n")

    conn = mysql.connector.connect(**DB)
    conn.autocommit = True
    cur = conn.cursor(buffered=True)

    total_ok = total_err = 0
    for sql_file in files:
        print(f"\n[{sql_file.name}]")
        ok, err = apply_file(cur, sql_file, args.dry_run)
        total_ok += ok
        total_err += err

    print(f"\n{'='*60}")
    print(f"  Views aplicadas: {total_ok}  |  Erros: {total_err}")

    if args.verify and not args.dry_run:
        print("\n--- Verificação de views ---")
        verify_views(cur)

    cur.close()
    conn.close()
    sys.exit(1 if total_err > 0 else 0)


if __name__ == "__main__":
    main()
