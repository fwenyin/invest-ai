"""Bottom Up Bulletin (and any Substack) via your logged-in session cookie.

Substack has no usable private RSS feed for paid text newsletters, so we read the
publication's JSON API authenticated as you. Set in .env:

    SUBSTACK_PUBLICATION=thepopularinvestor      # the <name> in <name>.substack.com
    SUBSTACK_SESSION_COOKIE=<value of substack.sid cookie from your browser>

Get the cookie: log into the publication, open DevTools -> Application -> Cookies
-> substack.com, copy the VALUE of `substack.sid`. It expires every few weeks; when
it does, paid posts come back as previews and this tool warns you to refresh it.

CLI:  python tools/substack.py             # latest posts (full text if cookie valid)
      python tools/substack.py --limit 5
"""
from __future__ import annotations

import argparse

from common import cache_get, cache_set, emit, env, err, ok

_UA = "Mozilla/5.0 (compatible; to-the-moon/0.1)"


def latest(limit: int = 8, publication: str | None = None) -> dict:
    import requests

    pub = publication or env("SUBSTACK_PUBLICATION")
    cookie = env("SUBSTACK_SESSION_COOKIE")
    if not pub:
        return err(
            "SUBSTACK_PUBLICATION not set. Add the publication subdomain "
            "(e.g. thepopularinvestor) to .env."
        )
    if not cookie:
        return err(
            "SUBSTACK_SESSION_COOKIE not set. Paid posts need your logged-in "
            "`substack.sid` cookie — see tools/substack.py header for how to get it."
        )

    cached = cache_get("substack", ttl_seconds=3600)
    if cached:
        return cached

    base = f"https://{pub}.substack.com"
    session = requests.Session()
    session.headers["User-Agent"] = _UA
    session.cookies.set("substack.sid", cookie, domain="substack.com")

    # One-time auth check: the subscription endpoint returns 200 +
    # membership_state="subscribed" only when the cookie is valid; a missing or
    # expired cookie 404s. Paid post bodies arrive as short previews otherwise.
    authenticated = False
    try:
        sub = session.get(f"{base}/api/v1/subscription", timeout=20)
        authenticated = sub.status_code == 200 and sub.json().get("membership_state") == "subscribed"
    except Exception:
        authenticated = False

    try:
        archive = session.get(
            f"{base}/api/v1/archive",
            params={"sort": "new", "limit": limit},
            timeout=20,
        )
        archive.raise_for_status()
        entries = archive.json()
    except Exception as e:
        return err(f"substack archive fetch failed: {e}")

    if not isinstance(entries, list) or not entries:
        return err("substack archive returned no posts — check SUBSTACK_PUBLICATION")

    posts = []
    for entry in entries[:limit]:
        slug = entry.get("slug")
        if not slug:
            continue
        try:
            resp = session.get(f"{base}/api/v1/posts/{slug}", timeout=20)
            resp.raise_for_status()
            post = resp.json()
        except Exception:
            post = entry  # fall back to archive metadata (no body)

        # Without a valid session, paid posts return only a short preview body.
        preview_only = post.get("audience") == "only_paid" and not authenticated
        posts.append(
            {
                "title": post.get("title"),
                "published": post.get("post_date", ""),
                "url": post.get("canonical_url") or entry.get("canonical_url"),
                "audience": post.get("audience"),
                "preview_only": preview_only,
                "text": _strip_html(post.get("body_html") or "")[:8000],
            }
        )

    out = ok({"publication": pub, "count": len(posts), "posts": posts})
    if not authenticated:
        out["warning"] = (
            "⚠️ Substack cookie expired — paid posts are previews only. "
            "Fix: log into Substack, copy a fresh `substack.sid` cookie "
            "(DevTools → Application → Cookies → substack.com), and update "
            "SUBSTACK_SESSION_COOKIE in .env."
        )
    cache_set("substack", out)
    return out


def _strip_html(s: str) -> str:
    import re

    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", s, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text).replace("&amp;", "&")
    return re.sub(r"\s+", " ", text).strip()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=8)
    p.add_argument("--publication", default=None)
    a = p.parse_args()
    emit(latest(a.limit, a.publication))
