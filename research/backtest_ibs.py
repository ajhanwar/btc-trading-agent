"""
Reproducible backtest of the deployed strategy on public daily data (yfinance).

Uses the SAME strategy code the live bot runs (live/strategy.py -> weight_series), so what
you backtest here is exactly what trades. Reproduces the headline result over 2010-2026:
equal-weight SOXL/SPXL/TQQQ portfolio, Sharpe ~1.08, CAGR ~13%/yr, max drawdown ~-18%.

Run:  python -m research.backtest_ibs      (from repo root)

Method notes (kept honest):
- Long-only (bull ETF or cash); vol-target + exposure cap sizes each sleeve.
- 3 bps/side slippage; leveraged ETFs are liquid but this keeps it conservative.
- yfinance auto-adjusts splits/dividends; IBS = (C-L)/(H-L) is scale-invariant to that.
- Sample starts ~2010 (ETF inception) and INCLUDES real crashes (Mar-2020 COVID, Q4-2018,
  2011, 2015-16) — vol-targeting collapses exposure into volatility, so the strategy was
  roughly flat-to-positive through them while buy&hold fell 60-90%.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import yfinance as yf

from live import config as C
from live.strategy import weight_series

SLIP = 0.0003


def yf_daily(sym: str) -> pd.DataFrame:
    df = yf.download(sym, period="max", interval="1d", auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df[["Open", "High", "Low", "Close", "Volume"]].dropna()


def sleeve_net(df: pd.DataFrame, trend_trim: bool = True) -> pd.Series:
    w = weight_series(df, backtest=True, trend_trim=trend_trim)   # same logic as live, shifted 1 day
    ret = df["Close"].pct_change().fillna(0.0)
    return w * ret - w.diff().abs().fillna(0.0) * SLIP


def stats(net: pd.Series) -> dict:
    eq = (1 + net).cumprod(); tot = eq.iloc[-1] - 1; yrs = len(net) / 252
    return {"cagr": (1 + tot) ** (1 / yrs) - 1,
            "sharpe": net.mean() / net.std() * np.sqrt(252) if net.std() > 0 else 0.0,
            "maxdd": (eq / eq.cummax() - 1).min()}


def main():
    pct = lambda x: f"{x*100:+.0f}%"
    print(f"Backtesting {C.TICKERS}  (IBS entry<{C.IBS_ENTRY}, vol target {C.VOL_TARGET}, cap {C.EXPOSURE_CAP})\n")
    print(f"{'instrument':<14}{'CAGR':>7}{'maxDD':>7}{'Sharpe':>8}")
    weights, rets = {}, {}
    for t in C.TICKERS:
        df = yf_daily(t)
        trim = t in C.TREND_TRIM_TICKERS
        n = sleeve_net(df, trend_trim=trim); s = stats(n.dropna())
        print(f"{t:<14}{pct(s['cagr']):>7}{pct(s['maxdd']):>7}{s['sharpe']:>8.2f}")
        weights[t] = weight_series(df, backtest=True, trend_trim=trim) * C.SLEEVE_ALLOCATION[t]
        rets[t] = df["Close"].pct_change()

    # additive sleeve construction with the live MAX_TOTAL_EXPOSURE clip (as deployed)
    W = pd.DataFrame(weights).dropna()
    tot = W.sum(axis=1)
    W = W.mul(np.where(tot > C.MAX_TOTAL_EXPOSURE, C.MAX_TOTAL_EXPOSURE / tot, 1.0), axis=0)
    R = pd.DataFrame(rets).reindex(W.index).fillna(0.0)
    port = (W * R).sum(axis=1) - W.diff().abs().sum(axis=1).fillna(0.0) * SLIP
    ps = stats(port)
    print(f"{'PORTFOLIO':<14}{pct(ps['cagr']):>7}{pct(ps['maxdd']):>7}{ps['sharpe']:>8.2f}")

    yr = port.index.year
    print("\nPortfolio return by year:")
    print("  " + "  ".join(f"{y}:{pct((1+port[yr==y]).prod()-1)}" for y in range(port.index.year.min(), 2027)))


if __name__ == "__main__":
    main()
