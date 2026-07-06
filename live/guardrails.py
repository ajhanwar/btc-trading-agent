"""Safety layer applied between 'what the strategy wants' and 'what gets ordered'.
Every rule here is designed to fail safe (toward cash / no trade)."""
from . import config as C


def kill_switch_active() -> bool:
    """If the STOP file exists, the bot halts (no new orders). Create it to stop trading:
       touch live/state/STOP"""
    return C.KILL_SWITCH_FILE.exists()


def dollar_targets(target_fractions: dict, account_equity: float) -> dict:
    """Convert account-fraction targets into target $ per ETF, honoring the hard $ ceiling."""
    total_frac = min(sum(target_fractions.values()), C.MAX_TOTAL_EXPOSURE)
    deploy = account_equity * total_frac
    if C.MAX_DEPLOY_USD is not None and deploy > C.MAX_DEPLOY_USD:
        scale = C.MAX_DEPLOY_USD / deploy if deploy > 0 else 0.0
        target_fractions = {t: f * scale for t, f in target_fractions.items()}
    return {t: round(account_equity * f, 2) for t, f in target_fractions.items()}


def build_orders(target_usd: dict, current_usd: dict, account_equity: float) -> list:
    """
    Diff target vs current positions into a list of orders. Applies the rebalance band
    (skip tiny adjustments) and the minimum order size.
    current_usd: current $ held per ticker (0 if not held).
    """
    band = max(C.REBALANCE_BAND_USD, C.REBALANCE_BAND_FRAC * account_equity)
    orders = []
    for t, tgt in target_usd.items():
        cur = current_usd.get(t, 0.0)
        delta = round(tgt - cur, 2)
        if abs(delta) < max(band, C.MIN_ORDER_USD):
            continue
        orders.append({"ticker": t, "side": "buy" if delta > 0 else "sell",
                       "usd": abs(delta), "target_usd": tgt, "current_usd": round(cur, 2)})
    return orders


def preflight(orders: list, account_equity: float) -> tuple:
    """Final sanity checks before any execution. Returns (ok, reasons)."""
    reasons = []
    if kill_switch_active():
        reasons.append("KILL SWITCH active (live/state/STOP exists)")
    total_buy = sum(o["usd"] for o in orders if o["side"] == "buy")
    if total_buy > account_equity * C.MAX_TOTAL_EXPOSURE + 1:
        reasons.append(f"total buys ${total_buy:.0f} exceed max exposure")
    return (len(reasons) == 0, reasons)
