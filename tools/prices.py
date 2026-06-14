"""Price data: quotes, intraday, daily history, overnight gaps, indicator snapshot.

Primary source is yfinance (free). Returns are JSON-serialisable dicts.
CLI:  python tools/prices.py AAPL
      python tools/prices.py SPY --intraday
      python tools/prices.py NVDA AMD MSFT --snapshot
"""
from __future__ import annotations

import argparse

import pandas as pd

from common import cache_get, cache_set, emit, err, ok
from indicators import snapshot as indicator_snapshot


def _history(ticker: str, period: str, interval: str) -> pd.DataFrame:
    import yfinance as yf

    df = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=False)
    if df is None or df.empty:
        raise ValueError(f"no data for {ticker}")
    return df


def quote(ticker: str) -> dict:
    """Latest price + previous close + intraday/overnight gap."""
    cached = cache_get(f"quote_{ticker}", ttl_seconds=60)
    if cached:
        return cached
    try:
        df = _history(ticker, period="5d", interval="1d")
        last = df.iloc[-1]
        prev = df.iloc[-2] if len(df) >= 2 else last
        price = float(last["Close"])
        prev_close = float(prev["Close"])
        today_open = float(last["Open"])
        out = ok(
            {
                "ticker": ticker.upper(),
                "price": round(price, 4),
                "prev_close": round(prev_close, 4),
                "open": round(today_open, 4),
                "day_change_pct": round((price / prev_close - 1) * 100, 2),
                "gap_pct": round((today_open / prev_close - 1) * 100, 2),
                "day_high": round(float(last["High"]), 4),
                "day_low": round(float(last["Low"]), 4),
                "volume": int(last["Volume"]),
            }
        )
        cache_set(f"quote_{ticker}", out)
        return out
    except Exception as e:
        return err(f"quote failed for {ticker}: {e}")


def snapshot(ticker: str, period: str = "1y", interval: str = "1d") -> dict:
    """Full technical snapshot (indicators + levels + trend)."""
    try:
        df = _history(ticker, period=period, interval=interval)
        snap = indicator_snapshot(df)
        snap["ticker"] = ticker.upper()
        snap["interval"] = interval
        return ok(snap)
    except Exception as e:
        return err(f"snapshot failed for {ticker}: {e}")


def intraday(ticker: str, interval: str = "5m") -> dict:
    """Today's intraday bars + opening-range (first 30m) high/low."""
    try:
        df = _history(ticker, period="1d", interval=interval)
        first30 = df.between_time("09:30", "10:00")
        or_high = float(first30["High"].max()) if not first30.empty else None
        or_low = float(first30["Low"].min()) if not first30.empty else None
        return ok(
            {
                "ticker": ticker.upper(),
                "interval": interval,
                "bars": len(df),
                "last": round(float(df["Close"].iloc[-1]), 4),
                "session_high": round(float(df["High"].max()), 4),
                "session_low": round(float(df["Low"].min()), 4),
                "opening_range_high": round(or_high, 4) if or_high else None,
                "opening_range_low": round(or_low, 4) if or_low else None,
                "vwap": round(
                    float(
                        ((df["High"] + df["Low"] + df["Close"]) / 3 * df["Volume"]).sum()
                        / max(df["Volume"].sum(), 1)
                    ),
                    4,
                ),
            }
        )
    except Exception as e:
        return err(f"intraday failed for {ticker}: {e}")


def gaps(tickers: list[str]) -> dict:
    """Overnight gap scan across a list — useful for /premarket."""
    rows = []
    for t in tickers:
        q = quote(t)
        if q.get("ok"):
            d = q["data"]
            rows.append({"ticker": d["ticker"], "gap_pct": d["gap_pct"], "price": d["price"]})
    rows.sort(key=lambda r: abs(r["gap_pct"]), reverse=True)
    return ok({"gaps": rows})


def history(ticker: str, period: str = "6mo", interval: str = "1d") -> dict:
    """Raw OHLCV as records (for the agents to reason over recent action)."""
    try:
        df = _history(ticker, period=period, interval=interval).tail(120)
        df = df.reset_index()
        df.columns = [str(c) for c in df.columns]
        return ok({"ticker": ticker.upper(), "rows": df.round(4).to_dict("records")})
    except Exception as e:
        return err(f"history failed for {ticker}: {e}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("tickers", nargs="+")
    p.add_argument("--intraday", action="store_true")
    p.add_argument("--snapshot", action="store_true")
    p.add_argument("--gaps", action="store_true")
    p.add_argument("--history", action="store_true")
    a = p.parse_args()

    if a.gaps:
        emit(gaps(a.tickers))
    elif a.intraday:
        emit({t: intraday(t) for t in a.tickers} if len(a.tickers) > 1 else intraday(a.tickers[0]))
    elif a.snapshot:
        emit({t: snapshot(t) for t in a.tickers} if len(a.tickers) > 1 else snapshot(a.tickers[0]))
    elif a.history:
        emit(history(a.tickers[0]))
    else:
        emit({t: quote(t) for t in a.tickers} if len(a.tickers) > 1 else quote(a.tickers[0]))
