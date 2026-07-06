"""
The validated strategy logic: IBS mean-reversion + volatility targeting + exposure cap.
Pure functions over daily OHLC -> target sleeve weight per ETF. Mirrors the backtest
(scratchpad round7/round8) exactly, minus the backtest's shift(1) — here we compute the
weight to ESTABLISH now (at today's close) and hold, so the last row is today's target.
"""
import numpy as np
import pandas as pd
from . import config as C


def ibs(df: pd.DataFrame) -> pd.Series:
    """Internal Bar Strength: where the close sits within the day's range, in [0,1]."""
    rng = (df["High"] - df["Low"]).replace(0, np.nan)
    return ((df["Close"] - df["Low"]) / rng).clip(0, 1)


def ibs_position(df: pd.DataFrame, entry=C.IBS_ENTRY, exit=C.IBS_EXIT) -> pd.Series:
    """Stateful long/cash position: enter (1) on IBS<entry, exit (0) on IBS>exit, hold between."""
    b = ibs(df)
    ev = pd.Series(np.nan, index=df.index)
    ev[b < entry] = 1.0
    ev[b > exit] = 0.0
    return ev.ffill().fillna(0.0)


def realized_vol(df: pd.DataFrame, window=C.VOL_WINDOW) -> pd.Series:
    """Annualized trailing realized volatility of daily close-to-close returns."""
    return df["Close"].pct_change().rolling(window).std() * np.sqrt(252)


def weight_series(df: pd.DataFrame, backtest: bool = False) -> pd.Series:
    """
    Full time series of the sleeve weight in [0, EXPOSURE_CAP]:
        position (IBS state) * clip(VOL_TARGET / realized_vol, 0, EXPOSURE_CAP)
    Live uses the last value (establish now). Backtest passes backtest=True to shift by one
    day (the weight decided at today's close earns the next day's return). This is the single
    source of truth shared by the live bot (sleeve_weight) and research/backtest_ibs.py.
    """
    frac = np.clip(C.VOL_TARGET / realized_vol(df), 0, C.EXPOSURE_CAP)
    w = ibs_position(df) * frac
    return w.shift(1).fillna(0.0) if backtest else w


def sleeve_weight(df: pd.DataFrame) -> dict:
    """
    Today's target weight for one ETF sleeve, in [0, EXPOSURE_CAP].
    Returns the weight plus diagnostics for logging/transparency.
    """
    pos = ibs_position(df)
    vol = realized_vol(df)
    frac = np.clip(C.VOL_TARGET / vol, 0, C.EXPOSURE_CAP)
    weight = float(weight_series(df).iloc[-1])
    return {
        "weight": weight,
        "ibs": round(float(ibs(df).iloc[-1]), 3),
        "position": int(pos.iloc[-1]),
        "ann_vol": round(float(vol.iloc[-1]), 3),
        "raw_frac": round(float(frac.iloc[-1]), 3),
        "close": round(float(df["Close"].iloc[-1]), 2),
        "asof": str(df.index[-1].date()),
    }


def portfolio_targets(history: dict) -> dict:
    """
    Given {ticker: daily_ohlc_df}, return target account-fraction per ETF.
    Each ETF is one equal sleeve: account_fraction = sleeve_allocation * sleeve_weight.
    Total is clamped to MAX_TOTAL_EXPOSURE.
    """
    sleeves = {t: sleeve_weight(df) for t, df in history.items()}
    targets = {t: C.SLEEVE_ALLOCATION[t] * s["weight"] for t, s in sleeves.items()}
    total = sum(targets.values())
    if total > C.MAX_TOTAL_EXPOSURE and total > 0:
        scale = C.MAX_TOTAL_EXPOSURE / total
        targets = {t: w * scale for t, w in targets.items()}
    return {"targets": targets, "diagnostics": sleeves,
            "total_exposure": round(sum(targets.values()), 4),
            "cash_fraction": round(1 - sum(targets.values()), 4)}
