import pandas as pd
import numpy as np

def run_vectorized_backtest(df, buy_signal, sell_signal):
    """
    Simulates trades and calculates returns based on boolean signal series.
    """
    event = pd.Series(np.nan, index=df.index)
    event.loc[buy_signal] = 1
    event.loc[sell_signal] = 0

    # Forward fill positions
    position = event.ffill().fillna(0)

    # Calculate returns (shift 1 to avoid look-ahead bias)
    strat_ret = position.shift(1) * df['Close'].pct_change()

    cum_ret = (1 + strat_ret).prod() - 1
    trades = event.dropna().diff().abs().sum() / 2 # Approx round trip trades

    return cum_ret, trades
