"""Gap-and-go (daily proxy): enter on an up-gap that holds, exit on a down day
or after a max hold.

The time-based exit is enforced by the engine via ``MAX_HOLD`` — it counts bars
from the ACTUAL entry fill. Do NOT express it as ``entries.shift(hold_days)``:
that ties the exit to the entry *signal*, so it misfires whenever entries cluster
or are ignored while already long, producing exits with no matching open position.
"""
import pandas as pd

NAME = "gap_and_go"
DESCRIPTION = "Long when today gaps up >gap_pct vs prior close AND closes green; exit on a red day or after MAX_HOLD bars."
HOLD_DAYS = 3
MAX_HOLD = HOLD_DAYS  # engine forces exit this many bars after the realized fill


def signals(df: pd.DataFrame, gap_pct: float = 2.0):
    prev_close = df["Close"].shift(1)
    gap = (df["Open"] / prev_close - 1) * 100
    green = df["Close"] > df["Open"]
    entries = (gap > gap_pct) & green
    # Discretionary exit signal: first red (down) day. The MAX_HOLD timer (handled
    # by the engine from the actual fill) is the backstop time-based exit.
    exits = df["Close"] < df["Open"]
    return entries.fillna(False), exits.fillna(False)
