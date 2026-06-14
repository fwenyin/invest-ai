"""Gap-and-go (daily proxy): enter on an up-gap that holds, exit after N days or on a down day."""
import pandas as pd

NAME = "gap_and_go"
DESCRIPTION = "Long when today gaps up >gap_pct vs prior close AND closes green; time-based exit after hold_days."


def signals(df: pd.DataFrame, gap_pct: float = 2.0, hold_days: int = 3):
    prev_close = df["Close"].shift(1)
    gap = (df["Open"] / prev_close - 1) * 100
    green = df["Close"] > df["Open"]
    entries = (gap > gap_pct) & green
    # exit hold_days after entry (vectorbt handles overlapping via from_signals)
    exits = entries.shift(hold_days).fillna(False)
    return entries.fillna(False), exits
