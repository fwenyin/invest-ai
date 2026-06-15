---
description: Post-market run (~16:15 ET). P&L review, journal + reflection (updates memory), after-hours earnings, tomorrow's bias.
allowed-tools: Task, Read, Write, Edit, Bash, Glob, mcp__to-the-moon-data__*
---

# Post-market run — review, journal, and learn

You are running the **post-market** session. This is where the desk's edge compounds: honest review feeds tomorrow's plan.

## Steps
1. Read all of today's `reports/daily/<YYYY-MM-DD>/*.md` and `portfolio/positions.json`.
2. **P&L & outcome review**: for each trade taken today, pull the close and compute result (P&L, R multiple). For trades planned but not taken, note whether they would have worked.
3. **Score the forward ledger** (this is what turns calls into evidence): run
   `.venv/bin/python tools/ledger.py score` to mark every open ledger entry against the actual price
   path (realized R, win/loss, what it hit), then `.venv/bin/python tools/ledger.py report` for the
   running forward scorecard (hit rate, avg R, expectancy, profit factor). Include the scorecard in
   today's report. Remember: only **scored forward** calls count — the report says how many more are
   needed before the edge is judgeable.
4. **Reflection (the important part)**: launch the `reflection-agent` to:
   - write the journal entry to `portfolio/journal/<YYYY-MM-DD>.md`, and
   - append durable lessons to `portfolio/memory/lessons.json` (referencing the ledger scorecard).
5. **After-hours / overnight setup**: launch `news-catalyst-analyst` for AMC earnings reactions and tomorrow's pre-open catalysts; have `macro-strategist` give a one-line bias for tomorrow.
6. **Remind the human** to update `portfolio/positions.json` with any fills/exits they executed today (the desk can only reconcile what's recorded).
7. Write `reports/daily/<YYYY-MM-DD>/postmarket.md`: P&L summary, the ledger scorecard, key lessons learned today, tomorrow's bias & watch items.

TL;DR: today's P&L, the single biggest lesson, and tomorrow's one-line bias.
