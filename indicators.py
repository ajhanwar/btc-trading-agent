import pandas as pd

def calculate_indicators(df):
    """
    Calculates 200 SMA, VWAP, Fibonacci, Bullish Engulfing, Pivots, MACD, Volume SMA, and Stochastic.
    """
    # 200 SMA
    df['SMA_200'] = df['Close'].rolling(window=200).mean()

    # VWAP (resets daily)
    df['Date'] = df.index.date
    df['Typical_Price'] = (df['High'] + df['Low'] + df['Close']) / 3
    df['VWAP'] = df.groupby('Date').apply(lambda x: (x['Typical_Price'] * x['Volume']).cumsum() / x['Volume'].cumsum()).reset_index(level=0, drop=True)

    # Fibonacci (50% level of rolling 30-day ~ 210 hours for equities)
    periods_30d = 210
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
    daily_data = daily_data[['Pivot', 'R1', 'S1']].shift(1) # Shift to use previous day's data

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
