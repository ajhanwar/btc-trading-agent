# LEGACY / SUPERSEDED: the original Bitcoin stochastic-crossover signal generator.
# Backtesting showed this approach had no out-of-sample edge. The deployed strategy is
# IBS mean-reversion in live/strategy.py. Kept for historical reference only.

def generate_signals(df, use_sma200, use_vwap, use_fib, use_engulfing, use_pivots, use_macd, use_vol_sma, stoch_buy_thresh, stoch_sell_thresh):
    """
    Evaluates piece/indicator combinations and triggers boolean buy/sell signals.
    """
    # Base entry/exit strictly off Stochastic Crossovers
    buy_signal = df['Stoch_Bull_Cross'] & (df['Full_K'] < stoch_buy_thresh)
    sell_signal = df['Stoch_Bear_Cross'] & (df['Full_K'] > stoch_sell_thresh)

    # Apply indicator filters (AND conditions)
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
        buy_signal = buy_signal & df['Bullish_Engulfing']

    if use_pivots:
        buy_signal = buy_signal & (df['Close'] > df['Pivot'])
        sell_signal = sell_signal & (df['Close'] < df['Pivot'])

    if use_macd:
        buy_signal = buy_signal & (df['MACD'] > df['Signal_Line'])
        sell_signal = sell_signal & (df['MACD'] < df['Signal_Line'])

    if use_vol_sma:
        buy_signal = buy_signal & (df['Volume'] > df['Volume_SMA'])
        sell_signal = sell_signal & (df['Volume'] > df['Volume_SMA'])

    return buy_signal, sell_signal
