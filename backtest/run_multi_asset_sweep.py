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

    if interval == "5m":
        df['Date'] = df.index.date
        df['GroupID'] = df.groupby('Date').cumcount() // 13

        resampled = df.groupby(['Date', 'GroupID']).agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        })

        first_times = df.reset_index().groupby(['Date', 'GroupID'])['Datetime'].first()
        resampled.index = first_times
        df = resampled

    if df['Volume'].sum() == 0:
        np.random.seed(123)
        df['Volume'] = np.random.lognormal(mean=1, sigma=0.5, size=len(df)) * 100
    else:
        df['Volume'] = df['Volume'].replace(0, 1)

    return df

def run_sweep(period, interval, out_filename):
    if interval == "5m":
        desc = "65m Custom Candles"
    else:
        desc = f"{interval} Native Candles"

    print(f"\n--- Running Sweep for SPXL & SPXS ({desc} over {period}) ---")

    bull_assets = ["SPXL"]
    bear_assets = ["SPXS"]
    all_assets = bull_assets + bear_assets

    data = {}
    for asset in all_assets:
        print(f"Fetching {asset} data...")
        df = fetch_data(asset, period, interval)
        if df is not None:
            df = calculate_indicators(df)
            data[asset] = df

    if len(data) != len(all_assets):
        print("Warning: Some data failed to fetch.")

    filters = [True, False]
    stoch_thresholds = [(20, 80), (30, 70), (40, 60)]
    combinations = list(itertools.product(
        filters, filters, filters, filters, filters, filters, filters, stoch_thresholds
    ))

    print(f"Testing {len(combinations)} indicator subsets across {len(all_assets)} assets...")
    results = []

    for combo in combinations:
        use_sma, use_vwap, use_fib, use_eng, use_piv, use_macd, use_vol, (s_buy, s_sell) = combo

        returns_dict = {}
        for asset, df in data.items():
            buy, sell = generate_signals(
                df, use_sma, use_vwap, use_fib, use_eng, use_piv, use_macd, use_vol, s_buy, s_sell
            )
            cum_ret, trades = run_vectorized_backtest(df, buy, sell)
            returns_dict[asset] = cum_ret * 100

        bull_ret = np.mean([returns_dict[a] for a in bull_assets])
        bear_ret = np.mean([returns_dict[a] for a in bear_assets])
        all_ret = np.mean([returns_dict[a] for a in all_assets])

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
            'Avg_Overall_%': all_ret,
            'Avg_Bull_%': bull_ret,
            'Avg_Bear_%': bear_ret,
            'SPXL': returns_dict['SPXL'],
            'SPXS': returns_dict['SPXS']
        })

    res_df = pd.DataFrame(results)

    print("\n--- TOP 3 INDICATOR COMBINATIONS FOR ALL STOCKS OVERALL ---")
    res_df_all = res_df.sort_values(by='Avg_Overall_%', ascending=False)
    print(res_df_all.head(3)[['VWAP', 'Bullish_Engulfing', 'Vol_SMA', 'Stoch_Buy', 'Avg_Overall_%']].to_string(index=False))

    print("\n--- TOP 3 INDICATOR COMBINATIONS FOR SPXL (BULL) ---")
    res_df_bull = res_df.sort_values(by='Avg_Bull_%', ascending=False)
    print(res_df_bull.head(3)[['VWAP', 'Bullish_Engulfing', 'Vol_SMA', 'Stoch_Buy', 'Avg_Bull_%']].to_string(index=False))

    print("\n--- TOP 3 INDICATOR COMBINATIONS FOR SPXS (BEAR) ---")
    res_df_bear = res_df.sort_values(by='Avg_Bear_%', ascending=False)
    print(res_df_bear.head(3)[['VWAP', 'Bullish_Engulfing', 'Vol_SMA', 'Stoch_Buy', 'Avg_Bear_%']].to_string(index=False))

    res_df_all.to_csv(out_filename, index=False)
    print(f"\nFull results saved to {out_filename}")

if __name__ == "__main__":
    run_sweep("60d", "15m", "spxl_spxs_results_60d_15m_stoch1433.csv")
