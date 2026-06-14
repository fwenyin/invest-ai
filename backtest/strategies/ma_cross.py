"""Moving-average crossover (trend following)."""
import pandas as pd

NAME = "ma_cross"
DESCRIPTION = "Long when fast SMA crosses above slow SMA; exit on cross back down. Trend following."


def signals(df: pd.DataFrame, fast: int = 20, slow: int = 50):
    close = df["Close"]
    f = close.rolling(fast).mean()
    s = close.rolling(slow).mean()
    cross_up = (f > s) & (f.shift(1) <= s.shift(1))
    cross_dn = (f < s) & (f.shift(1) >= s.shift(1))
    return cross_up.fillna(False), cross_dn.fillna(False)
