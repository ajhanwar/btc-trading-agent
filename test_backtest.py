import numpy as np
import pandas as pd

np.random.seed(123)

df = pd.DataFrame({'Close': [100, 105, 102, 110, 108]})
buy_mask = pd.Series([False, True, False, False, False])
sell_mask = pd.Series([False, False, False, True, False])

event = pd.Series(np.nan, index=df.index)
event.loc[buy_mask] = 1
event.loc[sell_mask] = 0
position = event.ffill().fillna(0)

strat_ret = position.shift(1) * df['Close'].pct_change()
cum_ret = (1 + strat_ret).cumprod()

print(position)
print(cum_ret)
