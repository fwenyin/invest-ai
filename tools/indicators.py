"""Technical indicators computed from a price history DataFrame.

Pure-pandas so it has no heavy deps beyond pandas/numpy. Used by prices.py and
the backtester. All functions take/return plain Python where sensible so the
output is JSON-serialisable for the agents.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def sma(series: pd.Series, n: int) -> pd.Series:
    return series.rolling(n).mean()


def ema(series: pd.Series, n: int) -> pd.Series:
    return series.ewm(span=n, adjust=False).mean()


def rsi(series: pd.Series, n: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(n).mean()
    loss = (-delta.clip(upper=0)).rolling(n).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    macd_line = ema(series, fast) - ema(series, slow)
    signal_line = ema(macd_line, signal)
    return macd_line, signal_line, macd_line - signal_line


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(n).mean()


def vwap(df: pd.DataFrame) -> pd.Series:
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    return (tp * df["Volume"]).cumsum() / df["Volume"].cumsum().replace(0, np.nan)


def support_resistance(df: pd.DataFrame, lookback: int = 60, n_levels: int = 3):
    """Naive S/R via recent swing highs/lows clustered to round levels."""
    recent = df.tail(lookback)
    highs = recent["High"].nlargest(n_levels).round(2).tolist()
    lows = recent["Low"].nsmallest(n_levels).round(2).tolist()
    return {"resistance": sorted(set(highs), reverse=True), "support": sorted(set(lows))}


def snapshot(df: pd.DataFrame) -> dict:
    """A compact, JSON-friendly indicator snapshot for the latest bar."""
    if df is None or len(df) < 30:
        return {"error": "insufficient history for indicators"}
    close = df["Close"]
    macd_line, signal_line, hist = macd(close)
    last = -1

    def f(x):
        try:
            v = float(x)
            return round(v, 4) if not np.isnan(v) else None
        except Exception:
            return None

    return {
        "price": f(close.iloc[last]),
        "sma20": f(sma(close, 20).iloc[last]),
        "sma50": f(sma(close, 50).iloc[last]),
        "sma200": f(sma(close, 200).iloc[last]) if len(df) >= 200 else None,
        "ema9": f(ema(close, 9).iloc[last]),
        "rsi14": f(rsi(close).iloc[last]),
        "macd": f(macd_line.iloc[last]),
        "macd_signal": f(signal_line.iloc[last]),
        "macd_hist": f(hist.iloc[last]),
        "atr14": f(atr(df).iloc[last]),
        "vwap": f(vwap(df).iloc[last]),
        "levels": support_resistance(df),
        "trend": _trend_label(close),
    }


def _trend_label(close: pd.Series) -> str:
    if len(close) < 50:
        return "unknown"
    s20, s50 = sma(close, 20).iloc[-1], sma(close, 50).iloc[-1]
    price = close.iloc[-1]
    if price > s20 > s50:
        return "uptrend"
    if price < s20 < s50:
        return "downtrend"
    return "sideways"
