"""
Daily decision step (the 'brain'). Runs as plain Python — needs NO Robinhood connection.
Pulls data, computes today's target weights, writes state/targets.json, logs, prints a plan.

Run:   python -m live.decide            (weights only)
       python -m live.decide --equity 500   (also show $ targets for a $500 account)

The execution step (Claude + Robinhood MCP) reads state/targets.json and reconciles the
account to these weights — see ROBINHOOD_SETUP.md. In PAPER_MODE nothing is ever ordered.
"""
import os
import json
import argparse
import datetime

from . import config as C
from . import data, strategy, guardrails


def _log(line: str):
    os.makedirs(C.STATE_DIR, exist_ok=True)
    with open(C.LOG_FILE, "a") as f:
        f.write(line.rstrip() + "\n")


def run(equity: float = None) -> dict:
    ts = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    os.makedirs(C.STATE_DIR, exist_ok=True)

    if guardrails.kill_switch_active():
        payload = {"timestamp": ts, "halted": True, "reason": "kill switch active"}
        _log(f"{ts}  HALTED: kill switch active (remove live/state/STOP to resume)")
        print(json.dumps(payload, indent=2))
        return payload

    history = data.fetch_all()
    result = strategy.portfolio_targets(history)

    payload = {"timestamp": ts, "paper_mode": C.PAPER_MODE, "tickers": C.TICKERS, **result}
    if equity is not None:
        payload["account_equity"] = equity
        payload["target_usd"] = guardrails.dollar_targets(result["targets"], equity)

    with open(C.TARGETS_FILE, "w") as f:
        json.dump(payload, f, indent=2)

    # human-readable log line
    tgt = result["targets"]
    parts = "  ".join(f"{t}={tgt[t]*100:.1f}%(IBS{result['diagnostics'][t]['ibs']})" for t in C.TICKERS)
    _log(f"{ts}  {'PAPER' if C.PAPER_MODE else 'LIVE'}  exposure={result['total_exposure']*100:.1f}% "
         f"cash={result['cash_fraction']*100:.1f}%  {parts}")

    _print_summary(payload)
    return payload


def _print_summary(p: dict):
    print(f"\n=== Daily targets  ({p['timestamp']})  mode={'PAPER' if C.PAPER_MODE else 'LIVE'} ===")
    print(f"{'ETF':<6}{'IBS':>6}{'pos':>5}{'annVol':>8}{'trend':>7}{'weight%':>9}", end="")
    print(f"{'  $target' if 'target_usd' in p else ''}")
    for t in C.TICKERS:
        d = p["diagnostics"][t]; w = p["targets"][t]
        tr = "below" if d.get("below_trend") else "above"
        line = f"{t:<6}{d['ibs']:>6}{d['position']:>5}{d['ann_vol']:>8.2f}{tr:>7}{w*100:>8.1f}%"
        if "target_usd" in p:
            line += f"{'  $'+format(p['target_usd'][t], '.2f'):>10}"
        print(line)
    print(f"total ETF exposure: {p['total_exposure']*100:.1f}%   cash: {p['cash_fraction']*100:.1f}%")
    if C.PAPER_MODE:
        print("PAPER_MODE: this is a plan only — no orders placed.")
    print(f"targets written to {C.TARGETS_FILE}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--equity", type=float, default=None, help="account equity ($) to size a dollar plan")
    args = ap.parse_args()
    run(args.equity)
