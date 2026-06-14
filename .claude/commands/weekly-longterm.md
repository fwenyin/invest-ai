---
description: Weekly long-term (buy-and-hold) research run. Scans themes + Bottom Up Bulletin, deep-dives candidates, applies a valuation gate, updates conviction list.
allowed-tools: Task, Read, Write, Edit, Bash, Glob, mcp__to-the-moon-data__*, WebSearch
argument-hint: "[optional: specific ticker or theme to research]"
---

# Weekly long-term research run

You are running the **buy-and-hold sleeve**. Horizon: years. Goal: a high-conviction list of quality businesses to accumulate at sensible prices — updated in `portfolio/longterm.json`. Focus: $ARGUMENTS (or run the full process if blank).

## Steps
1. **Context**: Read `portfolio/longterm.json` and `config/universe.json`. Review existing convictions and watch list.
2. **Macro backdrop**: `macro-strategist` for the multi-month regime (rates, cycle) — affects what to favor and required margin of safety.
3. **Idea sourcing**: `secular-trend-analyst` (pulls Bottom Up Bulletin + validates themes) → surface 3–6 candidate themes and the best-positioned names. Add any user-specified ticker/theme.
4. **Quality**: `moat-quality-analyst` on each candidate → moat & business quality.
5. **Numbers**: `fundamentals-analyst` (long-term mode) on survivors.
6. **Valuation gate**: `valuation-analyst` → BUY NOW / ACCUMULATE ON DIPS / WATCH / AVOID + entry zone.
7. **Debate** the top names: `bull-researcher` vs `bear-researcher`.
8. **Decide & record**: update `portfolio/longterm.json`:
   - `holdings` (own), `conviction_watchlist` (want, with target entry zones), `themes`.
   - For each: ticker, thesis (2-3 lines), quality verdict, fair-value range, entry zone, verdict, date.
9. Write `reports/weekly/<YYYY-Www>/longterm.md`: theme map, candidate table (quality + valuation + verdict + entry zone), and a clear **"buy now vs wait"** list.

TL;DR: top 3 buy-now names with entry zones, and the strongest theme this week. Remember: quality + price both required — a great business at a rich price is WATCH, not BUY.
