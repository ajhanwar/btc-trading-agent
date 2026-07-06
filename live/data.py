"""Daily OHLC data for the live decision. Uses yfinance (consolidated OHLC — the same
source the 16-year validation ran on, so live IBS matches the backtest)."""
import warnings
warnings.filterwarnings("ignore")
import pandas as pd
import yfinance as yf

from . import config as C


def fetch_daily(ticker: str, days: int = C.HISTORY_DAYS) -> pd.DataFrame:
    df = yf.download(ticker, period=f"{days}d", interval="1d",
                     auto_adjust=True, progress=False)
    if df is None or df.empty:
        raise RuntimeError(f"No data returned for {ticker}")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    if len(df) < C.VOL_WINDOW + 5:
        raise RuntimeError(f"Insufficient history for {ticker}: {len(df)} rows")
    return df


def fetch_all(tickers=None) -> dict:
    tickers = tickers or C.TICKERS
    return {t: fetch_daily(t) for t in tickers}
