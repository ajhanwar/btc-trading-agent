# Going live on Robinhood Agentic — setup guide

The bot trades a validated strategy (IBS mean-reversion + volatility targeting + exposure cap
across SOXL / SPXL / TQQQ). Backtest 2010–2026: Sharpe ~1.08, CAGR ~13%/yr, max drawdown ~−18%.
It is **long-only** (each ETF or cash), which fits Robinhood's long-only Agentic account.

> **Start in paper mode. Watch it for a few weeks before risking a cent.** `PAPER_MODE = True`
> in `config.py` guarantees no order is ever placed — the bot only computes and logs a plan.

## 0. One-time environment setup
```bash
cd /Users/ajhanwar/Documents/btc-trading-agent
python3 -m venv .venv
.venv/bin/pip install -r live/requirements.txt
.venv/bin/python -m live.decide --equity 500      # sanity check: prints today's plan
```

## 1. Open + fund the Agentic account (desktop, once)
- In the Robinhood app/site, open an **Agentic Trading account**. It is separate from your main
  account — the agent can only ever trade here. Fund it with the *small* amount you're willing to risk.

## 2. Connect Claude Code to Robinhood (desktop, once — OAuth cannot be done headless)
```bash
claude mcp add robinhood-trading --transport http https://agent.robinhood.com/mcp/trading
```
Then in Claude Code run `/mcp`, select `robinhood-trading`, and complete the OAuth login +
onboarding that opens. Confirm it can read your Agentic account and that **SOXL/SPXL/TQQQ are
tradable** there (leveraged ETFs sometimes need a risk acknowledgment).

## 3. Paper-run it daily (recommended: 2–4 weeks)
- Edit `run_daily.sh` → point `PY` at `.venv/bin/python`.
- Install the scheduler (runs ~15 min before the close, weekdays):
  ```bash
  cp live/com.trading.ibsbot.plist ~/Library/LaunchAgents/
  launchctl load ~/Library/LaunchAgents/com.trading.ibsbot.plist
  ```
  Adjust the time in the plist to **15:45 ET in your local timezone** (it's set to 12:45 for US/Pacific).
- Each day, review `live/state/decisions.log` and `targets.json`. Confirm the weights/exposure look sane.

## 4. Arm live trading (only when you're satisfied)
1. Set `PAPER_MODE = False` in `config.py`.
2. Uncomment the `claude -p ...` block in `run_daily.sh`.
3. Tighten guardrails for your account size in `config.py` (see below).

The daily live flow then is: `decide.py` computes weights → Claude reads your Agentic account
via the MCP → `reconcile.py` computes exact orders deterministically → Claude places only those
orders. Robinhood pushes you a notification for every trade; you can one-tap disconnect anytime.

## Guardrails (in `config.py`)
| Knob | Default | Meaning |
|---|---|---|
| `PAPER_MODE` | `True` | log-only; no orders until you set `False` |
| `EXPOSURE_CAP` | `0.50` | max fraction of a sleeve in its ETF (tail guard) |
| `MAX_TOTAL_EXPOSURE` | `0.55` | hard cap on total account % in ETFs |
| `MAX_DEPLOY_USD` | `None` | optional hard $ ceiling regardless of equity |
| `REBALANCE_BAND_FRAC` | `0.03` | skip trades smaller than 3% of equity (anti-churn) |
| `VOL_TARGET` | `0.20` | risk dial — raise for more return + more drawdown |

## KILL SWITCH — stop all trading instantly
```bash
touch live/state/STOP      # bot halts on next run; resume by deleting the file
```
Also: one-tap "disconnect agent" in the Robinhood app, and/or `launchctl unload` the plist.

## Honest reminders
- This is a real-money, leveraged strategy. Backtests are not guarantees.
- The edge is **tech-concentrated** and mean-reversion based; it survived every crash in the
  record but a novel gap-crash is the residual risk (the exposure cap limits, not eliminates, it).
- Keep the account small until you've seen it behave live across a few different market weeks.
