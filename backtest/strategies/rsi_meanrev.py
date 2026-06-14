"""RSI mean-reversion (buy oversold, exit on normalization)."""
import numpy as np
import pandas as pd

NAME = "rsi_meanrev"
DESCRIPTION = "Long when RSI(14) < 30 (oversold); exit when RSI > 55. Mean reversion."


def _rsi(series: pd.Series, n: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(n).mean()
    loss = (-delta.clip(upper=0)).rolling(n).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def signals(df: pd.DataFrame, low: int = 30, high: int = 55):
    rsi = _rsi(df["Close"])
    entries = (rsi < low) & (rsi.shift(1) >= low)
    exits = (rsi > high) & (rsi.shift(1) <= high)
    return entries.fillna(False), exits.fillna(False)
