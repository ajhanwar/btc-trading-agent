import numpy as np
import pandas as pd
import itertools

# Set seed for reproducibility
np.random.seed(123)

def simulate_bitcoin_data_65min(days=180, initial_price=60000, mu=0.5, sigma=0.8):
    """
    Simulates 65-minute OHLCV Bitcoin data using Geometric Brownian Motion.
    """
    minutes_per_period = 65
    periods = int(days * 24 * 60 / minutes_per_period)
    dt = minutes_per_period / (365 * 24 * 60) # dt in years

    prices = [initial_price]
    for _ in range(periods - 1):
        drift = (mu - 0.5 * sigma**2) * dt
        shock = sigma * np.sqrt(dt) * np.random.normal()
        price = prices[-1] * np.exp(drift + shock)
        prices.append(price)

    df = pd.DataFrame(index=pd.date_range(start='2023-01-01', periods=periods, freq='65min'))
    df['Close'] = prices

    opens = [initial_price]
    for i in range(1, periods):
        opens.append(prices[i-1])
    df['Open'] = opens

    highs = []
    lows = []
    volumes = []
    # Decrease the inner volatility to match shorter timeframes
    vol_adj = 0.005
    for i in range(periods):
        o = df['Open'].iloc[i]
        c = df['Close'].iloc[i]
        high = max(o, c) * (1 + abs(np.random.normal(0, vol_adj)))
        low = min(o, c) * (1 - abs(np.random.normal(0, vol_adj)))
        highs.append(high)
        lows.append(low)
        volumes.append(np.random.lognormal(mean=1, sigma=0.5) * 100) # Base volume

    df['High'] = highs
    df['Low'] = lows
    df['Volume'] = volumes

    return df

def calculate_indicators(df):
    """
    Calculates 200 SMA, VWAP, Fibonacci, Bullish Engulfing, Pivots, MACD, Volume SMA, and Stochastic.
    """
    # 200 SMA
    df['SMA_200'] = df['Close'].rolling(window=200).mean()

    # VWAP (resets daily)
    # 65 min periods per day = ~22.15. We'll group by date.
    df['Date'] = df.index.date
    df['Typical_Price'] = (df['High'] + df['Low'] + df['Close']) / 3
    df['VWAP'] = df.groupby('Date').apply(lambda x: (x['Typical_Price'] * x['Volume']).cumsum() / x['Volume'].cumsum()).reset_index(level=0, drop=True)

    # Fibonacci (50% level of rolling 30-day ~ 664 periods)
    periods_30d = int(30 * 24 * 60 / 65)
    rolling_high = df['High'].rolling(window=periods_30d).max()
    rolling_low = df['Low'].rolling(window=periods_30d).min()
    df['Fib_50'] = rolling_low + (rolling_high - rolling_low) * 0.5

    # Bullish Engulfing Pattern
    df['Prev_Open'] = df['Open'].shift(1)
    df['Prev_Close'] = df['Close'].shift(1)
    df['Bullish_Engulfing'] = (df['Prev_Close'] < df['Prev_Open']) & \
                              (df['Open'] < df['Prev_Close']) & \
                              (df['Close'] > df['Prev_Open'])

    # Daily Pivots (using previous day's High, Low, Close)
    daily_data = df.groupby('Date').agg({'High': 'max', 'Low': 'min', 'Close': 'last'})
    daily_data['Pivot'] = (daily_data['High'] + daily_data['Low'] + daily_data['Close']) / 3
    daily_data['R1'] = (2 * daily_data['Pivot']) - daily_data['Low']
    daily_data['S1'] = (2 * daily_data['Pivot']) - daily_data['High']
    daily_data = daily_data[['Pivot', 'R1', 'S1']].shift(1) # Shift to use previous day's data for current day

    df = df.merge(daily_data, left_on='Date', right_index=True, how='left')

    # MACD (12, 26, 9)
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()

    # Volume SMA (20 periods)
    df['Volume_SMA'] = df['Volume'].rolling(window=20).mean()

    # Full Stochastic (14, 5, 5)
    low14 = df['Low'].rolling(window=14).min()
    high14 = df['High'].rolling(window=14).max()
    df['Fast_K'] = 100 * ((df['Close'] - low14) / (high14 - low14))
    df['Full_K'] = df['Fast_K'].rolling(window=5).mean()
    df['Full_D'] = df['Full_K'].rolling(window=5).mean()

    # Pre-compute cross logic for Stochastic
    df['Prev_Full_K'] = df['Full_K'].shift(1)
    df['Prev_Full_D'] = df['Full_D'].shift(1)
    df['Stoch_Bull_Cross'] = (df['Prev_Full_K'] <= df['Prev_Full_D']) & (df['Full_K'] > df['Full_D'])
    df['Stoch_Bear_Cross'] = (df['Prev_Full_K'] >= df['Prev_Full_D']) & (df['Full_K'] < df['Full_D'])

    return df

def vectorized_backtest(df, use_sma200, use_vwap, use_fib, use_engulfing, use_pivots, use_macd, use_vol_sma, stoch_buy_thresh, stoch_sell_thresh):
    """
    Runs a vectorized backtest for a specific combination of parameters.
    """
    # Start with stochastic signals
    buy_signal = df['Stoch_Bull_Cross'] & (df['Full_K'] < stoch_buy_thresh)
    sell_signal = df['Stoch_Bear_Cross'] & (df['Full_K'] > stoch_sell_thresh)

    # Apply filters
    if use_sma200:
        buy_signal = buy_signal & (df['Close'] > df['SMA_200'])
        sell_signal = sell_signal & (df['Close'] < df['SMA_200'])

    if use_vwap:
        buy_signal = buy_signal & (df['Close'] > df['VWAP'])
        sell_signal = sell_signal & (df['Close'] < df['VWAP'])

    if use_fib:
        buy_signal = buy_signal & (df['Close'] > df['Fib_50'])
        sell_signal = sell_signal & (df['Close'] < df['Fib_50'])

    if use_engulfing:
        # Bullish engulfing is typically a buy signal
        buy_signal = buy_signal & df['Bullish_Engulfing']

    if use_pivots:
        # Simple pivot logic: Buy if above Daily Pivot, Sell if below
        buy_signal = buy_signal & (df['Close'] > df['Pivot'])
        sell_signal = sell_signal & (df['Close'] < df['Pivot'])

    if use_macd:
        # Buy if MACD is above Signal Line
        buy_signal = buy_signal & (df['MACD'] > df['Signal_Line'])
        sell_signal = sell_signal & (df['MACD'] < df['Signal_Line'])

    if use_vol_sma:
        # Require higher than average volume for signals
        buy_signal = buy_signal & (df['Volume'] > df['Volume_SMA'])
        sell_signal = sell_signal & (df['Volume'] > df['Volume_SMA'])

    # Create position array (1 = long, 0 = neutral)
    event = pd.Series(np.nan, index=df.index)
    event.loc[buy_signal] = 1
    event.loc[sell_signal] = 0

    # Forward fill positions
    position = event.ffill().fillna(0)

    # Calculate returns
    strat_ret = position.shift(1) * df['Close'].pct_change()

    # Cumulative return
    cum_ret = (1 + strat_ret).prod() - 1

    # Count trades
    trades = event.dropna().diff().abs().sum() / 2 # Approx round trip trades

    return cum_ret, trades

def run_all_combinations():
    print("Simulating data...")
    df = simulate_bitcoin_data_65min(days=180)

    print("Calculating indicators...")
    df = calculate_indicators(df)

    # Define grid
    filters = [True, False]
    stoch_thresholds = [(20, 80), (30, 70), (40, 60)]

    combinations = list(itertools.product(
        filters, filters, filters, filters, filters, filters, filters, stoch_thresholds
    ))

    print(f"Running {len(combinations)} combinations...")

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

    results_df.to_csv('backtest_results.csv', index=False)

    print("\n=== Top 10 Combinations ===")
    print(results_df.head(10).to_string())
    print("\nResults saved to backtest_results.csv")

if __name__ == "__main__":
    run_all_combinations()
