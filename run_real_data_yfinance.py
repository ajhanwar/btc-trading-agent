import pandas as pd
import yfinance as yf
from backtest_combinations import calculate_indicators, vectorized_backtest

def main():
    print("Fetching real BTC-USD hourly data using yfinance (approx past 730 days limit)...")
    df = yf.download("BTC-USD", interval="1h", period="730d", progress=False)

    # Flatten MultiIndex columns from yfinance
    df.columns = df.columns.get_level_values(0)

    # Ensure volume isn't entirely zeroes (yfinance crypto volume can sometimes be zero for small intervals)
    # If it is, we simulate volume just to allow VWAP to work without division by zero errors.
    if df['Volume'].sum() == 0:
        import numpy as np
        np.random.seed(123)
        print("Warning: yfinance returned 0 volume. Simulating volume for VWAP logic.")
        df['Volume'] = np.random.lognormal(mean=1, sigma=0.5, size=len(df)) * 100
    else:
        # Prevent zero volume candles from causing inf/nan in VWAP calculation
        df['Volume'] = df['Volume'].replace(0, 1)

    print(f"Data fetched! Total rows: {len(df)}")
    print(f"Date range: {df.index[0]} to {df.index[-1]}")

    print("Calculating indicators...")
    df = calculate_indicators(df)

    print("\nRunning backtest on best combination (VWAP, Pivots, Stoch 40/60)...")

    # Best combo parameters
    use_sma200 = False
    use_vwap = True
    use_fib = False
    use_engulfing = False
    use_pivots = True
    use_macd = False
    use_vol_sma = False
    stoch_buy = 40
    stoch_sell = 60

    cum_ret, trades = vectorized_backtest(
        df, use_sma200, use_vwap, use_fib, use_engulfing, use_pivots, use_macd, use_vol_sma, stoch_buy, stoch_sell
    )

    buy_and_hold = (df['Close'].iloc[-1] - df['Close'].iloc[0]) / df['Close'].iloc[0]

    print("\n=== Real Data Backtest Results ===")
    print(f"Strategy Total Return: {cum_ret * 100:.2f}%")
    print(f"Total Trades (approx): {trades}")
    print(f"Buy & Hold Return:     {buy_and_hold * 100:.2f}%")

if __name__ == "__main__":
    main()
