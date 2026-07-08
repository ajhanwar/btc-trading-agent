# Leveraged-ETF IBS Portfolio Bot

An autonomous, **long-only** daily trading bot for a [Robinhood Agentic](https://robinhood.com/us/en/support/articles/agentic-trading-overview/)
account. It trades a mean-reversion strategy — **Internal Bar Strength (IBS) + volatility
targeting + an exposure cap** — across three tech-sector 3× ETFs (**SOXL, SPXL, TQQQ**),
rebalanced once daily.

> This repo began as a Bitcoin stochastic-crossover experiment, then briefly detoured into an
> SPY/VOO index sweep. Rigorous backtesting showed **neither had an out-of-sample edge**, and
> Robinhood Agentic supports equities only (not crypto), so it was rebuilt around a strategy that
> actually validates. The earlier BTC and SPY/VOO code is kept under [`backtest/`](backtest/) +
> [`agent.py`](agent.py) as superseded legacy research.

## The strategy

For each ETF, independently:
- **IBS** = `(Close − Low) / (High − Low)` measures where the close sits in the day's range.
- Go **long** when IBS < 0.20 (oversold), exit to **cash** when IBS > 0.80. Never short.
- Size the position to a **20% volatility target** (`target / realized_vol`), **capped at 0.5×**
  of the sleeve — so exposure auto-collapses when volatility spikes (i.e. in crashes).
- **Trim exposure above the long-term trend** (320-day EMA) to 75%: the IBS edge is ~2× stronger
  *below* trend, so de-emphasizing the weak-edge regime lifts Sharpe and shaves drawdowns.
- Three equal-weight sleeves diversify the portfolio.

Because it's long-only (bull ETF or cash) it maps natively onto Robinhood's long-only Agentic account.

## Backtest (2010–2026, incl. real crashes — reproducible)

```bash
python -m research.backtest_ibs
```

| Instrument | CAGR | max drawdown | Sharpe |
|---|--:|--:|--:|
| SOXL | +12% | −21% | 1.00 |
| SPXL | +10% | −22% | 1.00 |
| TQQQ | +10% | −17% | 0.94 |
| **Equal-weight portfolio** | **+11%** | **−15%** | **1.10** |

Beats buy-and-hold **out-of-sample** (walk-forward) at roughly a *quarter* of its drawdown.
Through the March-2020 COVID crash the strategy was **+5 to +7%** while buy-and-hold fell
**−65 to −76%**, because vol-targeting cut exposure to ~5% as volatility exploded.
[`research/backtest_ibs.py`](research/backtest_ibs.py) reuses the *exact* strategy code the
live bot runs ([`live/strategy.py`](live/strategy.py)), so the backtest and live logic can't drift.

## Repository layout

```
live/                 the production bot (paper-mode by default)
  config.py           parameters + guardrails
  strategy.py         IBS + vol-target + cap  -> target weights (single source of truth)
  data.py             daily OHLC (yfinance)
  decide.py           daily brain: compute targets -> state/targets.json  (no Robinhood needed)
  reconcile.py        deterministic target-vs-account -> exact orders
  guardrails.py       kill-switch, exposure/$ caps, rebalance band
  EXECUTION_PROMPT.md recipe for the live `claude -p` + Robinhood MCP step
  run_daily.sh + com.trading.ibsbot.plist   scheduler (weekdays, ~15 min pre-close)
  ROBINHOOD_SETUP.md  full go-live guide
research/
  backtest_ibs.py     reproducible backtest of the deployed strategy
backtest/, agent.py, indicators.py   legacy research — BTC + SPY/VOO sweeps (superseded)
```

## Quickstart

```bash
python3 -m venv .venv && .venv/bin/pip install -r live/requirements.txt
.venv/bin/python -m research.backtest_ibs     # reproduce the numbers above
.venv/bin/python -m live.decide --equity 500  # today's paper plan
```

Then follow **[live/ROBINHOOD_SETUP.md](live/ROBINHOOD_SETUP.md)** to open + fund an Agentic
account, connect the Robinhood MCP, paper-watch it, and (only when satisfied) arm live trading.

## Safety

- **`PAPER_MODE = True`** by default — computes and logs a plan, places nothing.
- **Kill switch:** `touch live/state/STOP` halts trading instantly.
- Hard caps on per-sleeve and total exposure, an optional absolute `$` ceiling, and a rebalance
  band to avoid churn on a small account. Order math is deterministic Python, not model discretion.

## Honest caveats

This is a real-money, leveraged strategy, and backtests are not guarantees. The edge is
**tech-concentrated** (it failed validation on small-caps TNA and financials FAS) and is a
mean-reversion premium, not a market-beater in raw return during bull markets — its advantage is
**risk-adjusted** (far shallower drawdowns). It survived every crash in the record, but a novel
gap-crash out of a calm period is the residual tail the exposure cap limits but cannot eliminate.
Start small; paper-watch first.
