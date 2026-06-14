---
name: trump-source-stale
description: trump.py's Truth Social archive source is stale (newest post 2026-05-02); CNN live mirror unverified
metadata:
  type: project
---

`tools/trump.py` reads a community Truth Social archive. As of 2026-06-14 the GitHub raw
source (`stiles/trump-truth-social-archive`) returns 200 with ~29k posts but its **newest post
is dated 2026-05-02 — ~6 weeks stale** (the scraper stopped updating). `trump.py` now prefers a
live mirror at `ix.cnn.io/data/truth-social/truth_archive.json`, but that host is **blocked by the
user's corporate proxy** ([[corp-laptop-tls]]) so it always falls back to the stale GitHub file —
meaning the user currently gets ~6-week-old Trump posts, not live.

**Why:** matters because the user explicitly wants *live* Trump/Truth Social posts + rally/speech
news for catalyst trading. **How to apply:** the Trump feed is NOT reliably live yet. To truly fix,
either get the CNN mirror reachable (un-inspected proxy route) or repoint to another actively
maintained source (e.g. trumpstruth.org). The tool's `note`/`age_hours` fields flag staleness —
trust them. Rally/speech coverage was added to the news-catalyst-analyst agent via WebSearch.
