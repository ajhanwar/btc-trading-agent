"""
Configuration for the live IBS + volatility-target leveraged-ETF portfolio bot.

Strategy (validated over 2010-2026, see backtest research):
  For each ETF: go long (fraction of that sleeve's capital) when Internal Bar
  Strength (IBS = (Close-Low)/(High-Low)) is oversold, size the position to a
  target volatility, cap the leverage exposure, trim exposure above the 320-day
  trend EMA, else hold cash. Three equal sleeves (SOXL / SPXL / TQQQ) diversify.

  Backtest profile (equal-weight 3-ETF portfolio): Sharpe ~1.10, CAGR ~11%/yr,
  max drawdown ~-15%. Long-only (bull ETF or cash) -> fits Robinhood Agentic.

SAFETY: PAPER_MODE=False = ARMED for live. Even so, nothing can place an order until the
Robinhood MCP is connected+authenticated; set PAPER_MODE=True to force a log-only dry run.
"""
from pathlib import Path

# --- Universe: the three tech-sector 3x bull ETFs (validated); each an equal sleeve ---
TICKERS = ["SOXL", "SPXL", "TQQQ"]
SLEEVE_ALLOCATION = {t: 1.0 / len(TICKERS) for t in TICKERS}  # 1/3 of account each

# --- Strategy parameters (do NOT change without re-validating) ---
IBS_ENTRY = 0.20        # buy when IBS < this (oversold)
IBS_EXIT = 0.80         # exit to cash when IBS > this (overbought)
VOL_TARGET = 0.20       # annualized volatility target for position sizing
VOL_WINDOW = 20         # trading days of realized vol
EXPOSURE_CAP = 0.50     # max fraction of a sleeve in its ETF (tail-risk guard)
# Regime-aware sizing (round-9 validated): the IBS edge is ~2x stronger BELOW the long-term
# trend, so trim exposure above it. Robust across EMA lengths 150-450; improves risk-adjusted
# return beyond plain de-risking (+0.03 Sharpe, +1.3% CAGR at equal exposure), maxDD -18%->-15%.
EMA_TREND_LEN = 320     # long-term trend EMA
TREND_ABOVE_MULT = 0.75 # size multiplier when price is ABOVE the trend EMA (edge weaker -> trim)
TREND_BELOW_MULT = 1.00 # size multiplier when price is BELOW the trend EMA (edge strongest)
HISTORY_DAYS = 1500     # calendar days to pull (~1030 bars: EMA320 warmup + vol window)

# --- Guardrails ---
PAPER_MODE = False                # LIVE: places REAL orders once the Robinhood MCP is connected
MAX_TOTAL_EXPOSURE = 0.55         # hard cap: total account fraction in ETFs (rest cash)
MAX_DEPLOY_USD = None             # optional hard $ ceiling on total ETF exposure (None = off)
REBALANCE_BAND_USD = 0.0          # skip an order if |target$ - current$| below this (anti-churn); set per account size
REBALANCE_BAND_FRAC = 0.03        # ...or below this fraction of account equity
MIN_ORDER_USD = 1.0               # Robinhood supports fractional/$-based orders

# --- Paths / state ---
REPO = Path(__file__).resolve().parent.parent
STATE_DIR = REPO / "live" / "state"
TARGETS_FILE = STATE_DIR / "targets.json"     # latest computed target weights
LOG_FILE = STATE_DIR / "decisions.log"        # human-readable daily log
KILL_SWITCH_FILE = STATE_DIR / "STOP"         # if this file exists, the bot halts immediately

# --- Robinhood Agentic ---
# Connection is done by YOU on desktop:  claude mcp add robinhood-trading \
#   --transport http https://agent.robinhood.com/mcp/trading   then  /mcp  -> authenticate.
# The agent trades ONLY in your separate, separately-funded Agentic account.
ROBINHOOD_MCP = "robinhood-trading"
