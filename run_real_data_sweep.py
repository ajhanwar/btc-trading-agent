import pandas as pd
import yfinance as yf
import itertools
from backtest_combinations import calculate_indicators, vectorized_backtest

def main():
    print("Fetching real BTC-USD hourly data using yfinance (approx past 730 days limit)...")
    df = yf.download("BTC-USD", interval="1h", period="730d", progress=False)

    # Flatten MultiIndex columns from yfinance
    df.columns = df.columns.get_level_values(0)

    if df['Volume'].sum() == 0:
        import numpy as np
        np.random.seed(123)
        print("Warning: yfinance returned 0 volume. Simulating volume for VWAP logic.")
        df['Volume'] = np.random.lognormal(mean=1, sigma=0.5, size=len(df)) * 100
    else:
        df['Volume'] = df['Volume'].replace(0, 1)

    print(f"Data fetched! Total rows: {len(df)}")

    print("Calculating indicators...")
    df = calculate_indicators(df)

    # Define grid
    filters = [True, False]
    stoch_thresholds = [(20, 80), (30, 70), (40, 60)]

    combinations = list(itertools.product(
        filters, filters, filters, filters, filters, filters, filters, stoch_thresholds
    ))

    print(f"Running {len(combinations)} combinations against real data...")

    results = []
    for combo in combinations:
        use_sma200, use_vwap, use_fib, use_engulfing, use_pivots, use_macd, use_vol_sma, (stoch_buy, stoch_sell) = combo

        cum_ret, trades = vectorized_backtest(
            df, use_sma200, use_vwap, use_fib, use_engulfing, use_pivots, use_macd, use_vol_sma, stoch_buy, stoch_sell
        )

        results.append({
            'SMA_200': use_sma200,
            'VWAP': use_vwap,
            'Fib_50': use_fib,
            'Bullish_Engulfing': use_engulfing,
            'Daily_Pivots': use_pivots,
            'MACD': use_macd,
            'Vol_SMA': use_vol_sma,
            'Stoch_Buy': stoch_buy,
            'Stoch_Sell': stoch_sell,
            'Total_Return_%': cum_ret * 100,
            'Trades': trades
        })

    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values(by='Total_Return_%', ascending=False)

    results_df.to_csv('real_data_backtest_results.csv', index=False)

    buy_and_hold = (df['Close'].iloc[-1] - df['Close'].iloc[0]) / df['Close'].iloc[0] * 100

    print("\n=== Top 10 Real Data Combinations ===")
    print(results_df.head(10).to_string())
    print(f"\nBaseline Buy & Hold Return: {buy_and_hold:.2f}%")
    print("Results saved to real_data_backtest_results.csv")

if __name__ == "__main__":
    main()
