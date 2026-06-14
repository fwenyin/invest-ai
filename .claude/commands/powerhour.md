---
description: Power-hour run (~15:00 ET). EOD positioning, close day-trades, MOC imbalance, swing hold/exit decisions.
allowed-tools: Task, Read, Write, Edit, Bash, Glob, mcp__to-the-moon-data__*
---

# Power-hour run — position into the close

You are running the **power hour** (last hour). Volume and decisiveness pick up. Decide what closes today vs holds overnight.

## Steps
1. Read today's prior reports and `portfolio/positions.json`.
2. Launch `technical-analyst` (intraday) on open positions: where is price vs VWAP and the day's range into the close?
3. For each open trade decide:
   - **DAY TRADES**: close before the bell unless explicitly converting to a swing (state why and re-check the stop).
   - **SWINGS**: hold if thesis intact and within risk; tighten stop if extended. Flag **overnight event risk** (earnings AMC, data tomorrow AM).
4. Note any late-day catalyst, reversal, or MOC-imbalance-driven move.
5. Run a quick `risk-manager` pass on overnight exposure (total heat held overnight).
6. Write `reports/daily/<YYYY-MM-DD>/powerhour.md`: close-now list, hold-overnight list (with overnight risk noted), tightened stops.

TL;DR: what to close before the bell, what to hold, stops to adjust.
