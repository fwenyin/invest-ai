"""Donchian breakout (N-day high breakout, momentum)."""
import pandas as pd

NAME = "breakout"
DESCRIPTION = "Long on close above the prior N-day high; exit on close below the prior M-day low. Momentum."


def signals(df: pd.DataFrame, entry_lookback: int = 20, exit_lookback: int = 10):
    high_n = df["High"].rolling(entry_lookback).max().shift(1)
    low_m = df["Low"].rolling(exit_lookback).min().shift(1)
    entries = df["Close"] > high_n
    exits = df["Close"] < low_m
    return entries.fillna(False), exits.fillna(False)
