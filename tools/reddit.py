"""Retail sentiment from public Reddit JSON (no auth needed).

Scans r/wallstreetbets, r/stocks, r/options for hot posts and crude
ticker-mention counts. A contrarian/confirmation signal for sentiment-analyst.
CLI:  python tools/reddit.py                  # hot across default subs
      python tools/reddit.py --tickers AAPL NVDA TSLA
"""
from __future__ import annotations

import argparse
import re
from collections import Counter

import requests

from common import cache_get, cache_set, emit, err, ok

DEFAULT_SUBS = ["wallstreetbets", "stocks", "options"]
HEADERS = {"User-Agent": "to-the-moon/0.1 (sentiment scan)"}
# crude ticker regex; filter against common false positives
_TICKER_RE = re.compile(r"\b([A-Z]{2,5})\b")
_STOP = {"THE", "AND", "FOR", "YOLO", "CEO", "USA", "FDA", "DD", "WSB", "ATH", "IPO",
         "ETF", "USD", "GDP", "CPI", "FOMC", "EPS", "PE", "YOU", "ALL", "ARE", "NOT",
         "BUY", "SELL", "PUT", "CALL", "ITM", "OTM", "EOD", "AMA", "TLDR", "IMO"}


def hot(subs: list[str] | None = None, limit: int = 15) -> dict:
    subs = subs or DEFAULT_SUBS
    cache_key = f"reddit_{'_'.join(subs)}"
    cached = cache_get(cache_key, ttl_seconds=900)
    if cached:
        return cached

    mentions: Counter = Counter()
    top_posts = []
    try:
        for sub in subs:
            url = f"https://www.reddit.com/r/{sub}/hot.json?limit={limit}"
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code != 200:
                continue
            for child in r.json().get("data", {}).get("children", []):
                d = child.get("data", {})
                title = d.get("title", "")
                top_posts.append(
                    {
                        "sub": sub,
                        "title": title[:160],
                        "score": d.get("score"),
                        "comments": d.get("num_comments"),
                        "url": "https://reddit.com" + d.get("permalink", ""),
                    }
                )
                for m in _TICKER_RE.findall(title):
                    if m not in _STOP:
                        mentions[m] += 1
        top_posts.sort(key=lambda p: p.get("score") or 0, reverse=True)
        out = ok(
            {
                "subs": subs,
                "top_mentions": [{"ticker": t, "mentions": c} for t, c in mentions.most_common(15)],
                "top_posts": top_posts[:15],
            }
        )
        cache_set(cache_key, out)
        return out
    except Exception as e:
        return err(f"reddit scan failed: {e}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--subs", nargs="*", default=None)
    a = p.parse_args()
    emit(hot(a.subs))
