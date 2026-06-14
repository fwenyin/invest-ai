"""Options data via yfinance (free, delayed): chain, IV, put/call ratio, ATM.

For live greeks/flow, upgrade to Polygon or Tradier later (keys in .env).
CLI:  python tools/options.py AAPL
      python tools/options.py AAPL --expiry 2026-07-17
"""
from __future__ import annotations

import argparse

from common import emit, err, ok


def expiries(ticker: str) -> dict:
    import yfinance as yf

    try:
        exp = list(yf.Ticker(ticker).options)
        return ok({"ticker": ticker.upper(), "expiries": exp})
    except Exception as e:
        return err(f"expiries failed for {ticker}: {e}")


def chain(ticker: str, expiry: str | None = None) -> dict:
    """Summarised chain for one expiry: ATM strikes, IV, put/call ratio."""
    import yfinance as yf

    try:
        tk = yf.Ticker(ticker)
        exps = list(tk.options)
        if not exps:
            return err(f"no options listed for {ticker}")
        expiry = expiry or exps[0]
        oc = tk.option_chain(expiry)
        spot = float(tk.history(period="1d")["Close"].iloc[-1])

        calls, puts = oc.calls, oc.puts
        call_oi = int(calls["openInterest"].fillna(0).sum())
        put_oi = int(puts["openInterest"].fillna(0).sum())
        call_vol = int(calls["volume"].fillna(0).sum())
        put_vol = int(puts["volume"].fillna(0).sum())

        # nearest-the-money rows
        calls["dist"] = (calls["strike"] - spot).abs()
        puts["dist"] = (puts["strike"] - spot).abs()
        atm_call = calls.nsmallest(1, "dist").iloc[0]
        atm_put = puts.nsmallest(1, "dist").iloc[0]

        def row(r):
            return {
                "strike": float(r["strike"]),
                "last": float(r.get("lastPrice", 0) or 0),
                "bid": float(r.get("bid", 0) or 0),
                "ask": float(r.get("ask", 0) or 0),
                "iv": round(float(r.get("impliedVolatility", 0) or 0), 4),
                "oi": int(r.get("openInterest", 0) or 0),
                "volume": int(r.get("volume", 0) or 0),
            }

        return ok(
            {
                "ticker": ticker.upper(),
                "spot": round(spot, 4),
                "expiry": expiry,
                "put_call_oi_ratio": round(put_oi / max(call_oi, 1), 3),
                "put_call_vol_ratio": round(put_vol / max(call_vol, 1), 3),
                "atm_iv": round(
                    (float(atm_call["impliedVolatility"] or 0) + float(atm_put["impliedVolatility"] or 0)) / 2,
                    4,
                ),
                "atm_call": row(atm_call),
                "atm_put": row(atm_put),
            }
        )
    except Exception as e:
        return err(f"chain failed for {ticker}: {e}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("ticker")
    p.add_argument("--expiry", default=None)
    p.add_argument("--expiries", action="store_true")
    a = p.parse_args()
    emit(expiries(a.ticker) if a.expiries else chain(a.ticker, a.expiry))
