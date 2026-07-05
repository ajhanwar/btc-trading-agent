import pandas as pd
from backtest_combinations import simulate_bitcoin_data_65min, calculate_indicators, vectorized_backtest

def main():
    print("Simulating 1 year (365 days) of data...")
    df = simulate_bitcoin_data_65min(days=365)

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

    print("\n=== 1-Year Backtest Results ===")
    print(f"Total Return: {cum_ret * 100:.2f}%")
    print(f"Total Trades (approx): {trades}")

if __name__ == "__main__":
    main()
