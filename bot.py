import numpy as np
import pandas as pd

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
    # Decrease the inner volatility to match shorter timeframes
    vol_adj = 0.005
    for i in range(periods):
        o = df['Open'].iloc[i]
        c = df['Close'].iloc[i]
        high = max(o, c) * (1 + abs(np.random.normal(0, vol_adj)))
        low = min(o, c) * (1 - abs(np.random.normal(0, vol_adj)))
        highs.append(high)
        lows.append(low)

    df['High'] = highs
    df['Low'] = lows

    return df

df = simulate_bitcoin_data_65min(180)

# Calculate Full Stochastic (14, 5, 5)
low14 = df['Low'].rolling(window=14).min()
high14 = df['High'].rolling(window=14).max()
df['Fast_K'] = 100 * ((df['Close'] - low14) / (high14 - low14))

# Full %K = SMA(Fast %K, 5)
df['Full_K'] = df['Fast_K'].rolling(window=5).mean()

# Full %D = SMA(Full %K, 5)
df['Full_D'] = df['Full_K'].rolling(window=5).mean()

# Implement Trading Algorithm with Full Stochastic only
initial_cash = 100000.0
cash = initial_cash
btc_held = 0.0

print("=== Ledger of Trades ===")

prev_full_k = None
prev_full_d = None

for date, row in df.iterrows():
    if pd.isna(row['Full_D']):
        prev_full_k = row['Full_K']
        prev_full_d = row['Full_D']
        continue

    price = row['Close']
    full_k = row['Full_K']
    full_d = row['Full_D']

    stoch_bull_cross = (prev_full_k <= prev_full_d) and (full_k > full_d)
    stoch_bear_cross = (prev_full_k >= prev_full_d) and (full_k < full_d)

    # Buy if Stochastic crosses up from oversold (<30)
    buy_signal = stoch_bull_cross and full_k < 30

    # Sell if Stochastic crosses down from overbought (>70)
    sell_signal = stoch_bear_cross and full_k > 70

    if buy_signal and cash > 0:
        btc_bought = cash / price
        print(f"[{date}] BUY  {btc_bought:.4f} BTC at ${price:,.2f}")
        btc_held += btc_bought
        cash = 0
    elif sell_signal and btc_held > 0:
        cash_gained = btc_held * price
        print(f"[{date}] SELL {btc_held:.4f} BTC at ${price:,.2f}")
        cash += cash_gained
        btc_held = 0

    prev_full_k = full_k
    prev_full_d = full_d

if btc_held == 0 and cash == initial_cash:
    print("No trades were executed.")

final_value = cash if cash > 0 else btc_held * df['Close'].iloc[-1]
print("\n=== Final Portfolio Performance ===")
print(f"Initial Portfolio Value: ${initial_cash:,.2f}")
print(f"Final Portfolio Value:   ${final_value:,.2f}")
print(f"Total Return:            {((final_value - initial_cash) / initial_cash) * 100:.2f}%")
