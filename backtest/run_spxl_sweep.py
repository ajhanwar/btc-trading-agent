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

def fetch_data(symbol, period, interval):
    df = yf.download(symbol, interval=interval, period=period, progress=False)
    if df.empty:
        return None
    df.columns = df.columns.get_level_values(0)

    # Filter strictly for regular market hours
    df = df.between_time('09:30', '15:59')

    if df['Volume'].sum() == 0:
        np.random.seed(123)
        df['Volume'] = np.random.lognormal(mean=1, sigma=0.5, size=len(df)) * 100
    else:
        df['Volume'] = df['Volume'].replace(0, 1)

    return df

def run_sweep(period, interval, out_filename):
    print(f"\n--- Running Sweep for SPXL ({interval} Native Candles over {period}) ---")

    asset = "SPXL"
    print(f"Fetching {asset} data...")
    df = fetch_data(asset, period, interval)
    if df is None:
        print("Data failed to fetch.")
        return

    df = calculate_indicators(df)

    filters = [True, False]
    stoch_thresholds = [(20, 80), (30, 70), (40, 60)]
    combinations = list(itertools.product(
        filters, filters, filters, filters, filters, filters, filters, stoch_thresholds
    ))

    print(f"Testing {len(combinations)} indicator subsets for {asset}...")
    results = []

    for combo in combinations:
        use_sma, use_vwap, use_fib, use_eng, use_piv, use_macd, use_vol, (s_buy, s_sell) = combo

        buy, sell = generate_signals(
            df, use_sma, use_vwap, use_fib, use_eng, use_piv, use_macd, use_vol, s_buy, s_sell
        )
        cum_ret, trades = run_vectorized_backtest(df, buy, sell)

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
            'SPXL_Ret_%': cum_ret * 100,
            'Trades': trades
        })

    res_df = pd.DataFrame(results).sort_values(by='SPXL_Ret_%', ascending=False)

    print("\n--- TOP 5 INDICATOR COMBINATIONS FOR SPXL ---")
    print(res_df.head(5)[['VWAP', 'Bullish_Engulfing', 'Vol_SMA', 'Stoch_Buy', 'SPXL_Ret_%']].to_string(index=False))

    res_df.to_csv(out_filename, index=False)
    print(f"\nFull results saved to {out_filename}")

if __name__ == "__main__":
    run_sweep("60d", "15m", "spxl_results_60d_15m.csv")
