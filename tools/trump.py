"""Trump / Truth Social posts via the free, auto-updating GitHub archive.

Source: https://github.com/stiles/trump-truth-social-archive  (no auth, no key).
Returns the most recent posts (sorted newest-first) with an age note, and flags
how many fall inside the requested `hours` window — so the agent always gets the
latest available context even if the archive lags.
CLI:  python tools/trump.py            # latest posts
      python tools/trump.py --hours 24
"""
from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone

import requests

from common import cache_get, cache_set, emit, err, ok

ARCHIVE_JSON = "https://raw.githubusercontent.com/stiles/trump-truth-social-archive/main/data/truth_archive.json"


def recent(hours: int = 24, limit: int = 25) -> dict:
    cached = cache_get(f"trump_{hours}_{limit}", ttl_seconds=900)
    if cached:
        return cached

    try:
        r = requests.get(ARCHIVE_JSON, timeout=25)
        if r.status_code != 200:
            return err(f"Truth Social archive returned HTTP {r.status_code}")
        data = r.json()
    except Exception as e:
        return err(f"could not fetch Truth Social archive: {e}")

    posts = data if isinstance(data, list) else data.get("posts", data.get("data", []))

    parsed = []
    for p in posts:
        text = p.get("content") or p.get("text") or p.get("body") or ""
        ts = p.get("created_at") or p.get("date") or p.get("timestamp") or ""
        when = _parse(ts)
        parsed.append((when, ts, _strip_html(text), p.get("favourites_count"), p.get("url")))

    # newest first (posts with no parseable date sink to the bottom)
    parsed.sort(key=lambda x: x[0] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    now = datetime.now(timezone.utc)
    cutoff_count = sum(1 for w, *_ in parsed if w and (now - w).total_seconds() <= hours * 3600)

    out_posts = []
    for when, ts, text, likes, url in parsed[:limit]:
        age_h = round((now - when).total_seconds() / 3600, 1) if when else None
        out_posts.append({"datetime": ts, "age_hours": age_h, "text": text[:600],
                          "likes": likes, "url": url})

    note = None
    if cutoff_count == 0 and out_posts:
        newest_age = out_posts[0]["age_hours"]
        note = (f"No posts within the last {hours}h — archive's newest post is ~{newest_age}h old. "
                "Returning latest available; treat as possibly stale.")

    out = ok({"hours": hours, "in_window": cutoff_count, "count": len(out_posts),
              "posts": out_posts, "note": note})
    cache_set(f"trump_{hours}_{limit}", out)
    return out


def _parse(ts: str):
    if not ts:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(ts, fmt)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return None


def _strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s or "").replace("&amp;", "&").replace("&#39;", "'").strip()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--hours", type=int, default=24)
    p.add_argument("--limit", type=int, default=25)
    a = p.parse_args()
    emit(recent(a.hours, a.limit))
