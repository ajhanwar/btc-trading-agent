# Leveraged-ETF IBS Portfolio Bot

An autonomous, **long-only** daily trading bot for a [Robinhood Agentic](https://robinhood.com/us/en/support/articles/agentic-trading-overview/)
account. It trades a mean-reversion strategy — **Internal Bar Strength (IBS) + volatility
targeting + an exposure cap** — across five sleeves: three tech-sector 3× ETFs (**SOXL,
SPXL, TQQQ**) plus two near-zero-correlation diversifiers (**GLD, TLT**), rebalanced once
daily. It runs unattended on an always-on host (deployed on an Oracle Cloud free-tier VPS),
firing once each weekday ~15 minutes before the US market close.

## The strategy

For each sleeve, independently:
- **IBS** = `(Close − Low) / (High − Low)` measures where the close sits in the day's range.
- Go **long** when IBS < 0.20 (oversold), exit to **cash** when IBS > 0.80. Never short.
- Size the position to a **20% volatility target** (`target / realized_vol`), **capped at 0.5×**
  of the sleeve — so exposure auto-collapses when volatility spikes (i.e. in crashes).
- **Trim exposure above the long-term trend** (320-day EMA) to 75% on the leveraged tech sleeves:
  the IBS edge is ~2× stronger *below* trend, so de-emphasizing the weak-edge regime lifts Sharpe
  and shaves drawdowns.
- **GLD and TLT run as additional plain-IBS sleeves** funded from otherwise-idle cash — their
  returns are essentially uncorrelated with the tech sleeves (+0.06 / −0.07), a diversification
  free lunch. The 0.55 total-exposure cap clips the rare collisions (~5% of days).

Because it's long-only (bull ETF or cash) it maps natively onto Robinhood's long-only Agentic account.

## How a trading day works

```
cron (weekdays 12:45 PT, ~15 min before close)
  └─ live/run_daily.sh
       ├─ 1. decide.py     pull daily OHLC (yfinance) -> compute target weights
       │                   -> state/targets.json          [pure Python, no Robinhood]
       └─ 2. claude -p EXECUTION_PROMPT.md                [headless Claude + Robinhood MCP]
            ├─ read account equity + positions -> state/account.json
            ├─ reconcile.py  diff targets vs positions -> state/orders.json  [deterministic]
            ├─ gate: kill switch / caps / paper mode
            └─ place exactly orders.json via the Robinhood MCP, log to decisions.log
```

The model never chooses trade sizes: all order math is deterministic Python. Claude's only job
is reading the account and placing the exact dollar orders that `reconcile.py` computed.

## Backtest (2010–2026, incl. real crashes — reproducible)

```bash
python -m research.backtest_ibs
```

| Instrument | CAGR | max drawdown | Sharpe |
|---|--:|--:|--:|
| SOXL | +12% | −21% | 1.00 |
| SPXL | +10% | −22% | 1.00 |
| TQQQ | +10% | −17% | 0.94 |
| GLD sleeve | +2% | −18% | 0.35 |
| TLT sleeve | +2% | −10% | 0.46 |
| **5-sleeve portfolio (clipped)** | **+12%** | **−17%** | **1.18** |

(The GLD/TLT sleeves look weak alone but are near-uncorrelated with the tech sleeves, so
adding them raises portfolio Sharpe from ~1.10 to ~1.18 while putting idle cash to work.)

Beats buy-and-hold **out-of-sample** (walk-forward) at roughly a *quarter* of its drawdown.
Through the March-2020 COVID crash the strategy was **+5 to +7%** while buy-and-hold fell
**−65 to −76%**, because vol-targeting cut exposure to ~5% as volatility exploded.
[`research/backtest_ibs.py`](research/backtest_ibs.py) reuses the *exact* strategy code the
live bot runs ([`live/strategy.py`](live/strategy.py)), so the backtest and live logic can't drift.

## Repository layout

```
live/                 the production bot
  config.py           strategy parameters + guardrails
  strategy.py         IBS + vol-target + trend trim + cap -> target weights (single source of truth)
  data.py             daily OHLC (yfinance)
  decide.py           daily brain: compute targets -> state/targets.json  (no Robinhood needed)
  reconcile.py        deterministic target-vs-account -> exact orders
  guardrails.py       kill-switch, exposure/$ caps, rebalance band
  EXECUTION_PROMPT.md recipe for the headless `claude -p` + Robinhood MCP execution step
  run_daily.sh        daily entrypoint (schedule via cron; com.trading.ibsbot.plist for macOS/launchd)
  ROBINHOOD_SETUP.md  full deployment guide (Agentic account, MCP auth, scheduling)
research/
  backtest_ibs.py     reproducible backtest of the deployed strategy
backtest/, agent.py, indicators.py   legacy research (superseded; kept for reference)
```

## Running it

```bash
python3 -m venv .venv && .venv/bin/pip install -r live/requirements.txt
.venv/bin/python -m research.backtest_ibs      # reproduce the numbers above
.venv/bin/python -m live.decide --equity 1000  # compute today's plan (never places orders)
```

`decide.py` is always safe to run — it computes and logs the plan only. Placing orders
additionally requires the Robinhood MCP connected and authenticated on the host.
**[live/ROBINHOOD_SETUP.md](live/ROBINHOOD_SETUP.md)** covers full deployment: opening and
funding an Agentic account, authenticating Claude + the Robinhood MCP on a headless host,
and scheduling the daily run.

## Safety

- **Kill switch:** `touch live/state/STOP` halts trading instantly (checked before every step).
- **Hard caps:** per-sleeve exposure cap (0.5×), total-exposure cap (0.55 of account), optional
  absolute `$` ceiling (`MAX_DEPLOY_USD`), and a rebalance band to avoid churn on a small account.
- **Deterministic orders:** the model never invents or resizes trades — `orders.json` is computed
  by plain Python and the execution step may place only those exact amounts.
- **`PAPER_MODE`:** set to `True` for a log-only dry run (computes and records the plan, places
  nothing). The deployed bot runs `False` (live).
- Every decision is auditable: `state/targets.json`, `account.json`, `orders.json`, and
  `decisions.log` record each day's inputs, math, and actions.

## Honest caveats

This is a real-money, leveraged strategy, and backtests are not guarantees. The edge is
**tech-concentrated** (it failed validation on small-caps TNA and financials FAS) and is a
mean-reversion premium, not a market-beater in raw return during bull markets — its advantage is
**risk-adjusted** (far shallower drawdowns). It survived every crash in the record, but a novel
gap-crash out of a calm period is the residual tail the exposure cap limits but cannot eliminate.
Start small.
