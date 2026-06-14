---
description: Show and update your portfolio state (positions, cash, open risk).
allowed-tools: Read, Write, Edit, mcp__to-the-moon-data__get_quote
argument-hint: "[e.g. 'add 100 AAPL @ 195 stop 188' or 'close TSLA' — or leave blank to view]"
---

# Portfolio positions

Read `portfolio/positions.json`. Instruction (optional): $ARGUMENTS

- **No instruction** → display a clean table: each position (ticker, side, size, entry, stop, current price via MCP, unrealized P&L, open risk %), plus cash and total open heat vs the 6% limit.
- **Add/update/close instruction** → update `portfolio/positions.json` accordingly, set `last_updated` to today, recompute cash, and confirm the change. Keep the JSON valid. Each position should carry: ticker, side, qty, entry, stop, instrument, opened (date), thesis (short).

Always remind the human this file is the source of truth the daily runs reconcile against — keep it accurate after every real fill.
