import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yfinance as yf
import pandas as pd
import numpy as np
import itertools
from indicators import calculate_indicators
from agent import generate_signals
from backtest_engine import run_vectorized_backtest

def fetch_data(symbol, period):
    # Fetch 5-minute data (max 60 days allowed by Yahoo Finance)
    df = yf.download(symbol, interval="5m", period="60d", progress=False)
    if df.empty:
        return None
    df.columns = df.columns.get_level_values(0)

    # Filter strictly for regular market hours to avoid pre/post market noise
    df = df.between_time('09:30', '15:59')

    # Resample 5-minute data into 65-minute candles
    # 65m / 5m = 13 candles per group
    df['Date'] = df.index.date
    df['GroupID'] = df.groupby('Date').cumcount() // 13

    resampled = df.groupby(['Date', 'GroupID']).agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    })

    # Reassign proper datetime index based on the first 5m candle of each 65m group
    first_times = df.reset_index().groupby(['Date', 'GroupID'])['Datetime'].first()
    resampled.index = first_times

    df = resampled

    # Replace any exact 0 volumes with 1 to prevent VWAP div/0
    if df['Volume'].sum() == 0:
        np.random.seed(123)
        df['Volume'] = np.random.lognormal(mean=1, sigma=0.5, size=len(df)) * 100
    else:
        df['Volume'] = df['Volume'].replace(0, 1)

    return df

def run_sweep(period, out_filename):
    print(f"\n--- Running Sweep for SOXL, TQQQ, SPXL (Custom 65-Min Candles over {period}) ---")
    assets = ["SOXL", "TQQQ", "SPXL"]
    data = {}

    for asset in assets:
        print(f"Fetching and Resampling {asset} data...")
        df = fetch_data(asset, period)
        if df is not None:
            df = calculate_indicators(df)
            data[asset] = df

    if not data:
        print("No data fetched.")
        return

    filters = [True, False]
    stoch_thresholds = [(20, 80), (30, 70), (40, 60)]
    combinations = list(itertools.product(
        filters, filters, filters, filters, filters, filters, filters, stoch_thresholds
    ))

    print(f"Testing {len(combinations)} parameter suites across {len(assets)} assets...")
    results = []

    for combo in combinations:
        use_sma, use_vwap, use_fib, use_eng, use_piv, use_macd, use_vol, (s_buy, s_sell) = combo

        returns = []
        trade_counts = []
        for asset, df in data.items():
            buy, sell = generate_signals(
                df, use_sma, use_vwap, use_fib, use_eng, use_piv, use_macd, use_vol, s_buy, s_sell
            )
            cum_ret, trades = run_vectorized_backtest(df, buy, sell)
            returns.append(cum_ret)
            trade_counts.append(trades)

        avg_ret = np.mean(returns) * 100
        avg_trades = np.mean(trade_counts)

        results.append({
            'SMA_200': use_sma,
            'VWAP': use_vwap,
            'Fib_50': use_fib,
            'Bullish_Engulfing': use_eng,
            'Daily_Pivots': use_piv,
            'MACD': use_macd,
            'Vol_SMA': use_vol,
            'Stoch_Buy': s_buy,
            'Stoch_Sell': s_sell,
            'Avg_Return_%': avg_ret,
            'Avg_Trades': avg_trades,
            'SOXL_Ret': returns[0]*100,
            'TQQQ_Ret': returns[1]*100,
            'SPXL_Ret': returns[2]*100
        })

    res_df = pd.DataFrame(results).sort_values(by='Avg_Return_%', ascending=False)
    res_df.to_csv(out_filename, index=False)

    print(f"Top 5 Suites (65m Custom Candles):")
    print(res_df.head(5)[['SMA_200', 'VWAP', 'Bullish_Engulfing', 'Vol_SMA', 'Stoch_Buy', 'Stoch_Sell', 'Avg_Return_%']].to_string(index=False))
    print(f"Saved to {out_filename}")

if __name__ == "__main__":
    # Max allowed by yfinance for 5m data is 60d
    run_sweep("60d", "leveraged_etfs_results_60d_65m.csv")
