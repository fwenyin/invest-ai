"""Economic calendar (FOMC/CPI/NFP/PCE...) + earnings calendar.

The risk-manager uses this for event blackouts; macro-strategist uses it for
the day's catalysts. Econ events try Finnhub first, then fall back to Nasdaq's
keyless calendar (Finnhub's /calendar/economic is a PREMIUM endpoint — free-tier
keys get a 403, so the fallback is the normal path on a free plan). Earnings use
Finnhub (free tier). Degrades gracefully to an empty list with a note otherwise.

CLI:  python tools/calendar_econ.py            # next 7 days of econ events
      python tools/calendar_econ.py --earnings  # upcoming earnings
"""
from __future__ import annotations

import argparse
import re
from datetime import datetime, timedelta

import requests

from common import cache_get, cache_set, emit, env, err, ok

UA = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Accept": "application/json",
}

# Events that trigger the risk-manager's blackout (config/risk_rules.yaml).
# Used to tag "high" impact when the source doesn't provide a rating (Nasdaq).
HIGH_IMPACT = [
    "fomc", "fed interest rate", "interest rate decision", "federal funds",
    "cpi", "consumer price", "nonfarm", "non-farm", "payroll", "unemployment rate",
    "pce", "ppi", "producer price", "retail sales", "gdp",
]


def _finnhub():
    key = env("FINNHUB_API_KEY")
    if not key:
        return None
    try:
        import finnhub

        return finnhub.Client(api_key=key)
    except Exception:
        return None


def _clean(s) -> str | None:
    """Nasdaq fills blanks with '&nbsp;' / whitespace — normalise those to None."""
    if s is None:
        return None
    t = re.sub(r"<[^>]+>", "", str(s)).replace("\xa0", " ").replace("&nbsp;", " ").strip()
    return t or None


def _impact(name: str | None) -> str:
    low = (name or "").lower()
    return "high" if any(k in low for k in HIGH_IMPACT) else "medium"


def _nasdaq_econ(days_ahead: int) -> list[dict]:
    """Keyless fallback: Nasdaq's economic-events API, one call per day."""
    out: list[dict] = []
    today = datetime.utcnow().date()
    for i in range(days_ahead + 1):
        day = today + timedelta(days=i)
        ds = day.strftime("%Y-%m-%d")
        try:
            r = requests.get(
                "https://api.nasdaq.com/api/calendar/economicevents",
                params={"date": ds}, headers=UA, timeout=20,
            )
            rows = ((r.json() or {}).get("data") or {}).get("rows") or []
        except Exception:
            continue
        for row in rows:
            if row.get("country") not in ("United States", "US"):
                continue
            name = _clean(row.get("eventName"))
            out.append({
                "date": ds,
                "event": name,
                "time": _clean(row.get("gmt")) or _clean(row.get("time")),
                "impact": _impact(name),
                "actual": _clean(row.get("actual")),
                "estimate": _clean(row.get("consensus")),
                "prev": _clean(row.get("previous")),
            })
    # high-impact first, then chronological — what the risk-manager scans for.
    out.sort(key=lambda e: (0 if e["impact"] == "high" else 1, e["date"]))
    return out


def economic(days_ahead: int = 7) -> dict:
    cached = cache_get("econ_calendar", ttl_seconds=3600)
    if cached:
        return cached

    # 1) Finnhub if entitled (premium endpoint — usually 403 on free tier).
    client = _finnhub()
    if client:
        try:
            frm = datetime.utcnow().strftime("%Y-%m-%d")
            to = (datetime.utcnow() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
            raw = client.calendar_economic(_from=frm, to=to)
            events = (raw.get("economicCalendar") or raw.get("data") or []) if isinstance(raw, dict) else []
            us = [e for e in events if e.get("country") in ("US", "United States")]
            us.sort(key=lambda e: ({"high": 0, "medium": 1, "low": 2}.get(str(e.get("impact")).lower(), 3)))
            if us:
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
                out = ok({"events": slim, "count": len(slim), "source": "finnhub"})
                cache_set("econ_calendar", out)
                return out
        except Exception:
            # Premium-gated (403) or transient — fall through to the keyless source.
            pass

    # 2) Keyless Nasdaq fallback — the normal path on a free Finnhub plan.
    try:
        events = _nasdaq_econ(days_ahead)
        if events:
            out = ok({"events": events[:40], "count": len(events), "source": "nasdaq"})
            cache_set("econ_calendar", out)
            return out
        return ok({"events": [], "count": 0, "source": "nasdaq",
                   "note": "no US economic events returned for the window."})
    except Exception as e:
        return err(f"economic calendar failed (finnhub premium-gated, nasdaq fallback errored): {e}")


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
