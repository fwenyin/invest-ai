"""Economic calendar (FOMC/CPI/NFP/PCE...) + earnings calendar via Finnhub.

The risk-manager uses this for event blackouts; macro-strategist uses it for
the day's catalysts. Degrades gracefully to an empty list with a note if no key.
CLI:  python tools/calendar_econ.py            # next 7 days of econ events
      python tools/calendar_econ.py --earnings  # upcoming earnings
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta

from common import cache_get, cache_set, emit, env, err, ok


def _finnhub():
    key = env("FINNHUB_API_KEY")
    if not key:
        return None
    try:
        import finnhub

        return finnhub.Client(api_key=key)
    except Exception:
        return None


def economic(days_ahead: int = 7) -> dict:
    cached = cache_get("econ_calendar", ttl_seconds=3600)
    if cached:
        return cached
    client = _finnhub()
    if not client:
        return ok({"events": [], "note": "no FINNHUB_API_KEY — econ calendar unavailable; "
                                          "check a free source manually (e.g. forexfactory)."})
    try:
        frm = datetime.utcnow().strftime("%Y-%m-%d")
        to = (datetime.utcnow() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        # finnhub-python renamed this to calendar_economic (>=2.4.x).
        raw = client.calendar_economic(_from=frm, to=to)
        events = (raw.get("economicCalendar") or raw.get("data") or []) if isinstance(raw, dict) else []
        # keep US, sorted by impact
        us = [e for e in events if e.get("country") in ("US", "United States")]
        us.sort(key=lambda e: ({"high": 0, "medium": 1, "low": 2}.get(str(e.get("impact")).lower(), 3)))
        slim = [
            {
                "event": e.get("event"),
                "time": e.get("time"),
                "impact": e.get("impact"),
                "actual": e.get("actual"),
                "estimate": e.get("estimate"),
                "prev": e.get("prev"),
            }
            for e in us[:30]
        ]
        out = ok({"events": slim, "count": len(slim)})
        cache_set("econ_calendar", out)
        return out
    except Exception as e:
        return err(f"economic calendar failed: {e}")


def earnings(days_ahead: int = 7) -> dict:
    client = _finnhub()
    if not client:
        return ok({"earnings": [], "note": "no FINNHUB_API_KEY — earnings calendar unavailable."})
    try:
        frm = datetime.utcnow().strftime("%Y-%m-%d")
        to = (datetime.utcnow() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        raw = client.earnings_calendar(_from=frm, to=to, symbol="")
        cal = raw.get("earningsCalendar", []) if isinstance(raw, dict) else []
        slim = [
            {
                "symbol": e.get("symbol"),
                "date": e.get("date"),
                "hour": e.get("hour"),
                "eps_estimate": e.get("epsEstimate"),
                "revenue_estimate": e.get("revenueEstimate"),
            }
            for e in cal[:60]
        ]
        return ok({"earnings": slim, "count": len(slim)})
    except Exception as e:
        return err(f"earnings calendar failed: {e}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--earnings", action="store_true")
    a = p.parse_args()
    emit(earnings() if a.earnings else economic())
