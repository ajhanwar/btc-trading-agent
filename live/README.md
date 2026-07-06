# live/ — leveraged-ETF IBS portfolio bot

Daily, long-only strategy (IBS mean-reversion + vol targeting + exposure cap) across
SOXL / SPXL / TQQQ, for a Robinhood Agentic account. **Paper-mode by default.**

**Setup + how to go live: [ROBINHOOD_SETUP.md](ROBINHOOD_SETUP.md)**

## Daily flow
```
decide.py   → pulls daily data (yfinance), computes target weights → state/targets.json   [no Robinhood needed]
              ↓  (live only, via Claude + Robinhood MCP; see EXECUTION_PROMPT.md)
account.json ← Claude reads Agentic account equity + positions from Robinhood
reconcile.py → diffs targets vs account → exact buy/sell orders → state/orders.json        [deterministic]
              ↓
Claude places ONLY those orders via the Robinhood MCP (skipped entirely in PAPER_MODE)
```

## Modules
| File | Role |
|---|---|
| `config.py` | all parameters + guardrails (start here) |
| `strategy.py` | the validated logic → target weight per ETF |
| `data.py` | daily OHLC via yfinance |
| `decide.py` | orchestrates the daily decision, writes `targets.json`, logs |
| `guardrails.py` | kill-switch, exposure/$ caps, rebalance band, order builder |
| `reconcile.py` | deterministic target-vs-current → orders |
| `EXECUTION_PROMPT.md` | recipe the live `claude -p` step follows |
| `run_daily.sh` / `com.trading.ibsbot.plist` | scheduler (weekdays ~15 min before close) |

## Controls
- Stop instantly: `touch live/state/STOP`  (delete to resume)
- Risk dial: `VOL_TARGET` in `config.py` (0.20 = validated; higher = more return + drawdown)
- Arm live: `PAPER_MODE = False` + uncomment the exec block in `run_daily.sh`
