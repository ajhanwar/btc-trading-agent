import yfinance as yf
import pandas as pd
import numpy as np
import itertools
from indicators import calculate_indicators
from agent import generate_signals
from backtest_engine import run_vectorized_backtest

def fetch_data(symbol, period):
    df = yf.download(symbol, interval="1h", period=period, progress=False)
    if df.empty:
        return None
    df.columns = df.columns.get_level_values(0)

    if df['Volume'].sum() == 0:
        np.random.seed(123)
        df['Volume'] = np.random.lognormal(mean=1, sigma=0.5, size=len(df)) * 100
    else:
        df['Volume'] = df['Volume'].replace(0, 1)

    return df

def run_sweep(period, out_filename):
    print(f"\n--- Running Sweep for Period: {period} ---")
    assets = ["BTC-USD", "ETH-USD", "SOL-USD"]
    data = {}

    for asset in assets:
        print(f"Fetching {asset} data...")
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
            'BTC_Ret': returns[0]*100,
            'ETH_Ret': returns[1]*100,
            'SOL_Ret': returns[2]*100
        })

    res_df = pd.DataFrame(results).sort_values(by='Avg_Return_%', ascending=False)
    res_df.to_csv(out_filename, index=False)

    print(f"Top 5 Suites ({period}):")
    print(res_df.head(5)[['SMA_200', 'VWAP', 'Bullish_Engulfing', 'Vol_SMA', 'Stoch_Buy', 'Stoch_Sell', 'Avg_Return_%']].to_string(index=False))
    print(f"Saved to {out_filename}")

if __name__ == "__main__":
    run_sweep("180d", "multi_asset_results_6mo.csv")
    run_sweep("365d", "multi_asset_results_1yr.csv")
