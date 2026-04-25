"""
powerbi_refresh.py — Dispara refresh do dataset Power BI via REST API.

Suporta dois modos:
  1. SCHEDULED: dispara refresh a cada N segundos (loop contínuo)
  2. ONCE     : dispara um refresh único e sai

Pré-requisitos:
  - App registrada no Microsoft Entra ID (Azure AD) com permissão Dataset.ReadWrite.All
  - Dataset publicado no Power BI Service (workspace + dataset IDs)
  - Variáveis de ambiente definidas (ver .env.example)

Uso:
  python pipeline/powerbi_refresh.py            # loop contínuo (padrão: 60s)
  python pipeline/powerbi_refresh.py --once     # dispara uma vez
  python pipeline/powerbi_refresh.py --interval 300  # a cada 5 minutos

Notas sobre limites do Power BI Service:
  - Pro/Free  : máx 8 refreshes/dia  → intervalo mínimo recomendado ~3h
  - Premium   : máx 48 refreshes/dia → intervalo mínimo recomendado ~30min
  - Para refresh < 1 min use DirectQuery ou Streaming Dataset (ver docs/pipeline-guide.md)
"""

import argparse
import os
import sys
import time
from datetime import datetime

import requests


# ── Config via variáveis de ambiente ─────────────────────────────────────────
TENANT_ID     = os.getenv("POWERBI_TENANT_ID", "")
CLIENT_ID     = os.getenv("POWERBI_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("POWERBI_CLIENT_SECRET", "")
WORKSPACE_ID  = os.getenv("POWERBI_WORKSPACE_ID", "")
DATASET_ID    = os.getenv("POWERBI_DATASET_ID", "")
DEFAULT_INTERVAL = int(os.getenv("REFRESH_INTERVAL_SEC", "60"))


# ── Auth ──────────────────────────────────────────────────────────────────────
def get_access_token() -> str:
    """Obtém token OAuth2 via client_credentials (Service Principal)."""
    if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET]):
        print("ERRO: POWERBI_TENANT_ID, POWERBI_CLIENT_ID e POWERBI_CLIENT_SECRET "
              "devem estar definidos nas variáveis de ambiente.")
        sys.exit(1)

    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    resp = requests.post(url, data={
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "https://analysis.windows.net/powerbi/api/.default",
    }, timeout=30)
    resp.raise_for_status()
    return resp.json()["access_token"]


# ── Refresh ───────────────────────────────────────────────────────────────────
def trigger_refresh(token: str) -> bool:
    """Dispara refresh do dataset. Retorna True em caso de sucesso."""
    url = (
        f"https://api.powerbi.com/v1.0/myorg/groups/{WORKSPACE_ID}"
        f"/datasets/{DATASET_ID}/refreshes"
    )
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}"},
        json={"notifyOption": "NoNotification"},
        timeout=30,
    )

    ts = datetime.now().strftime("%H:%M:%S")
    if resp.status_code == 202:
        print(f"[{ts}] ✓ Refresh agendado com sucesso.")
        return True
    elif resp.status_code == 429:
        retry_after = resp.headers.get("Retry-After", "?")
        print(f"[{ts}] ⚠ Rate limit atingido. Tente novamente em {retry_after}s.")
        return False
    else:
        print(f"[{ts}] ✗ Erro {resp.status_code}: {resp.text[:200]}")
        return False


def get_refresh_status(token: str) -> None:
    """Exibe o status dos últimos refreshes do dataset."""
    url = (
        f"https://api.powerbi.com/v1.0/myorg/groups/{WORKSPACE_ID}"
        f"/datasets/{DATASET_ID}/refreshes?$top=5"
    )
    resp = requests.get(
        url, headers={"Authorization": f"Bearer {token}"}, timeout=30
    )
    if resp.status_code != 200:
        return
    items = resp.json().get("value", [])
    print("\n  Últimos refreshes:")
    for item in items:
        print(f"    {item.get('startTime','?')} | {item.get('status','?')} | "
              f"type={item.get('refreshType','?')}")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Trigger Power BI dataset refresh")
    parser.add_argument("--once", action="store_true", help="Dispara uma vez e sai")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL,
                        help=f"Intervalo em segundos (padrão: {DEFAULT_INTERVAL})")
    parser.add_argument("--status", action="store_true",
                        help="Exibe status dos últimos refreshes e sai")
    args = parser.parse_args()

    if not all([WORKSPACE_ID, DATASET_ID]):
        print("ERRO: POWERBI_WORKSPACE_ID e POWERBI_DATASET_ID devem estar definidos.")
        sys.exit(1)

    token = get_access_token()

    if args.status:
        get_refresh_status(token)
        return

    if args.once:
        trigger_refresh(token)
        return

    # Loop contínuo
    print(f"Iniciando refresh contínuo (intervalo: {args.interval}s). Ctrl+C para parar.")
    consecutive_errors = 0
    while True:
        # Renovar token a cada ciclo para evitar expiração (tokens expiram em ~1h)
        try:
            token = get_access_token()
            success = trigger_refresh(token)
            consecutive_errors = 0 if success else consecutive_errors + 1

            if consecutive_errors >= 5:
                print("5 erros consecutivos — abortando.")
                sys.exit(1)
        except Exception as ex:
            print(f"Exceção inesperada: {ex}")
            consecutive_errors += 1

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
