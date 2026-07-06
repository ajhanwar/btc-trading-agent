"""
Deterministic order builder. Given the target weights (state/targets.json) and the current
account (state/account.json, written by the execution step from Robinhood), compute the exact
buy/sell orders. Keeping this in Python — not in the model — makes execution reproducible.

account.json format (written by the Claude execution step from Robinhood MCP reads):
  {"equity": 512.34, "positions": {"SOXL": 10.10, "SPXL": 0.0, "TQQQ": 33.00}}
  (equity = total account value incl. cash; positions = current market value $ per ticker)
"""
import json

from . import config as C
from . import guardrails


def run() -> dict:
    if not C.TARGETS_FILE.exists():
        raise RuntimeError("targets.json missing — run `python -m live.decide` first")
    if not (C.STATE_DIR / "account.json").exists():
        raise RuntimeError("account.json missing — the execution step must write current account state")

    targets = json.loads(C.TARGETS_FILE.read_text())
    account = json.loads((C.STATE_DIR / "account.json").read_text())
    equity = float(account["equity"])
    positions = {t: float(account.get("positions", {}).get(t, 0.0)) for t in C.TICKERS}

    target_usd = guardrails.dollar_targets(targets["targets"], equity)
    orders = guardrails.build_orders(target_usd, positions, equity)
    ok, reasons = guardrails.preflight(orders, equity)

    plan = {"paper_mode": C.PAPER_MODE, "equity": equity, "target_usd": target_usd,
            "current_usd": positions, "orders": orders, "approved": ok, "blocked_reasons": reasons}
    (C.STATE_DIR / "orders.json").write_text(json.dumps(plan, indent=2))
    return plan


if __name__ == "__main__":
    plan = run()
    print(json.dumps(plan, indent=2))
    if not plan["approved"]:
        print("\nORDERS BLOCKED:", "; ".join(plan["blocked_reasons"]))
    elif C.PAPER_MODE:
        print("\nPAPER_MODE: orders computed but NOT sent. Flip PAPER_MODE=False in config.py to arm.")
