---
description: Market-open run (~09:30 ET). Reads the open, confirms which pre-planned setups are triggering, anti-chase checklist.
allowed-tools: Task, Read, Write, Edit, Bash, Glob, mcp__to-the-moon-data__*
---

# Market-open run — execute the plan, don't improvise

You are running the **opening** session. The plan was already made pre-market; your job is execution discipline, not new ideas.

## Steps
1. Read today's `reports/daily/<YYYY-MM-DD>/premarket.md` and `portfolio/positions.json`. If no premarket report exists, say so and do a fast version of the premarket scan first.
2. Launch `technical-analyst` on the watchlist/planned trades in **intraday mode** (opening-range high/low, VWAP, first 5–15 min action). Avoid acting in the first 1–5 minutes of chop.
3. For each pre-planned idea, classify:
   - **TRIGGERED** — entry condition met → confirm size from the premarket risk sizing.
   - **ARMED** — close but not triggered → keep the alert.
   - **VOID** — gapped past entry / thesis broken → stand aside (do NOT chase).
4. Quick `risk-manager` check on anything newly triggered (heat/blackout still valid?).
5. Write `reports/daily/<YYYY-MM-DD>/open.md`: triggered list (act now), armed list (alerts), voided list, and an explicit **anti-chase reminder**.

TL;DR at the end: what to execute now, what to wait on, what to drop.
