---
description: Weekly long-term (buy-and-hold) research run. Scans themes + Bottom Up Bulletin, deep-dives candidates, applies a valuation gate, updates conviction list.
allowed-tools: Task, Read, Write, Edit, Bash, Glob, mcp__to-the-moon-data__*, WebSearch
argument-hint: "[optional: specific ticker or theme to research]"
---

# Weekly long-term research run

You are running the **buy-and-hold sleeve**. Horizon: years. Goal: a high-conviction list of quality businesses to accumulate at sensible prices — updated in `portfolio/longterm.json`. Focus: $ARGUMENTS (or run the full process if blank).

## Steps
1. **Context**: Read `portfolio/longterm.json` and `config/universe.json`. Review existing convictions and watch list.
2. **Checkpoint existing picks vs QQQ (do this first — it's the feedback loop)**: run
   `.venv/bin/python tools/lt_ledger.py checkpoint` to mark every logged pick against live prices and
   QQQ, then `.venv/bin/python tools/lt_ledger.py report`. This tells you whether the desk's past
   long-term calls are actually **beating the index** and whether each thesis's leading indicators are
   tracking. Fold the result into today's thinking — a pick badly lagging QQQ with a broken assumption
   is a sell candidate, not a hold.
3. **Macro backdrop**: `macro-strategist` for the multi-month regime (rates, cycle) — affects what to favor and required margin of safety.
4. **Idea sourcing**: `secular-trend-analyst` (pulls Bottom Up Bulletin + validates themes) → surface 3–6 candidate themes and the best-positioned names. Treat the newsletter as an idea source, not gospel — its picks may already be priced in. Add any user-specified ticker/theme.
5. **Quality**: `moat-quality-analyst` on each candidate → moat & business quality.
6. **Numbers**: `fundamentals-analyst` (long-term mode) on survivors.
7. **Valuation gate**: `valuation-analyst` → runs the deterministic DCF (`tools/valuation.py`) and applies the **QQQ hurdle** → BUY NOW / ACCUMULATE ON DIPS / WATCH / AVOID + entry zone. A name that can't plausibly beat QQQ is WATCH, not BUY.
8. **Debate** the top names: `bull-researcher` vs `bear-researcher`.
9. **Decide & record**: update `portfolio/longterm.json` AND log each new conviction pick to the long-term ledger so it gets graded over time:
   ```bash
   .venv/bin/python tools/lt_ledger.py log --ticker NVDA --verdict "ACCUMULATE ON DIPS" \
     --thesis "AI compute compounder" --fair-low 140 --fair-high 200 \
     --key-assumption "data-center rev sustains >25% CAGR" \
     --indicator "datacenter_rev_growth:baseline=40:target=>25"
   ```
   (entry price + QQQ price are auto-fetched; or use the `lt_ledger_log` MCP tool.) In `longterm.json`, keep `holdings`, `conviction_watchlist` (with target entry zones), `themes` — each with ticker, thesis, quality verdict, fair-value range, entry zone, verdict, date.
10. Write `reports/weekly/<YYYY-Www>/longterm.md`: the **QQQ scorecard** (from step 2), theme map, candidate table (quality + valuation + QQQ-hurdle + verdict + entry zone), and a clear **"buy now vs wait"** list. Not financial advice.

TL;DR: how the existing picks are doing **vs QQQ**, top 3 buy-now names with entry zones, and the strongest theme. Remember: quality + a sensible price + beats-the-index are ALL required — a great business at a rich price, or one that can't beat QQQ, is WATCH, not BUY.
