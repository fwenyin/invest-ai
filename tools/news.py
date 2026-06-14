"""Market & company news. Finnhub if a key is present, else free RSS (no key needed).

Free fallbacks fetch with a browser User-Agent (feeds block default agents) and
parse with feedparser:
  - market news : CNBC Markets + Yahoo Finance + MarketWatch (merged)
  - company news: Google News RSS search for the ticker

CLI:  python tools/news.py AAPL
      python tools/news.py --market
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta

import requests

from common import cache_get, cache_set, emit, env, err, ok

UA = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
}
MARKET_FEEDS = [
    "https://www.cnbc.com/id/20910258/device/rss/rss.html",   # CNBC Markets
    "https://finance.yahoo.com/news/rssindex",                # Yahoo Finance
    "https://feeds.content.dowjones.io/public/rss/mw_topstories",  # MarketWatch
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


def _fetch_feed(url: str, limit: int) -> list[dict]:
    import feedparser

    r = requests.get(url, headers=UA, timeout=20)
    feed = feedparser.parse(r.content)
    return [
        {
            "headline": e.get("title"),
            "summary": _clean(e.get("summary", ""))[:280],
            "source": (e.get("source", {}) or {}).get("title") or feed.feed.get("title", "rss"),
            "url": e.get("link"),
            "datetime": e.get("published", ""),
        }
        for e in feed.entries[:limit]
    ]


def _clean(s: str) -> str:
    import re

    return re.sub(r"<[^>]+>", "", s or "").replace("&nbsp;", " ").strip()


def company_news(ticker: str, days: int = 5, limit: int = 15) -> dict:
    cache_key = f"news_{ticker}_{days}"
    cached = cache_get(cache_key, ttl_seconds=900)
    if cached:
        return cached

    client = _finnhub()
    try:
        if client:
            frm = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
            to = datetime.utcnow().strftime("%Y-%m-%d")
            raw = client.company_news(ticker.upper(), _from=frm, to=to)[:limit]
            items = [
                {
                    "headline": n.get("headline"),
                    "summary": (n.get("summary") or "")[:280],
                    "source": n.get("source"),
                    "url": n.get("url"),
                    "datetime": datetime.utcfromtimestamp(n.get("datetime", 0)).isoformat(),
                }
                for n in raw
            ]
            src = "finnhub"
        else:
            url = (f"https://news.google.com/rss/search?q={ticker}+stock+when:{days}d"
                   "&hl=en-US&gl=US&ceid=US:en")
            items = _fetch_feed(url, limit)
            src = "google_news_rss"
        out = ok({"ticker": ticker.upper(), "count": len(items), "items": items, "source": src})
        cache_set(cache_key, out)
        return out
    except Exception as e:
        return err(f"company_news failed for {ticker}: {e}")


def market_news(limit: int = 20) -> dict:
    cached = cache_get("news_market", ttl_seconds=900)
    if cached:
        return cached
    client = _finnhub()
    try:
        if client:
            raw = client.general_news("general")[:limit]
            items = [
                {
                    "headline": n.get("headline"),
                    "summary": (n.get("summary") or "")[:280],
                    "source": n.get("source"),
                    "url": n.get("url"),
                    "datetime": datetime.utcfromtimestamp(n.get("datetime", 0)).isoformat(),
                }
                for n in raw
            ]
            src = "finnhub"
        else:
            items = []
            per = max(limit // len(MARKET_FEEDS) + 2, 5)
            for f in MARKET_FEEDS:
                try:
                    items.extend(_fetch_feed(f, per))
                except Exception:
                    continue
            items = items[:limit]
            src = "rss"
        out = ok({"count": len(items), "items": items, "source": src})
        cache_set("news_market", out)
        return out
    except Exception as e:
        return err(f"market_news failed: {e}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("ticker", nargs="?")
    p.add_argument("--market", action="store_true")
    a = p.parse_args()
    emit(market_news() if a.market or not a.ticker else company_news(a.ticker))
