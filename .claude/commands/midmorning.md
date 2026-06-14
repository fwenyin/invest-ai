---
description: Mid-morning run (~10:30 ET). Trend confirmation, manage open positions, mid-morning reversal check, new intraday setups.
allowed-tools: Task, Read, Write, Edit, Bash, Glob, mcp__to-the-moon-data__*
---

# Mid-morning run — manage and adapt

You are running the **mid-morning** session (~1h after the open). The opening volatility has settled; now the day's real trend shows. Manage what's on and add only high-quality setups.

## Steps
1. Read today's `open.md` and `premarket.md` reports and `portfolio/positions.json`.
2. **Manage open positions first**: launch `technical-analyst` (intraday) on each open position. For each, recommend HOLD / move stop to breakeven / trim into strength / exit (thesis broken or hit target).
3. **Trend check**: did the opening range break and hold? Is the macro regime from premarket confirming or failing? Note any mid-morning reversal.
4. **New setups**: only if clearly A-quality and regime-aligned — run `trader` → `risk-manager` on at most 1–2 new ideas (respect daily max-trades and remaining heat).
5. Write `reports/daily/<YYYY-MM-DD>/midmorning.md`: position management actions + any new triggers.

TL;DR: position actions (move stops / trim / exit) and any new entry.
