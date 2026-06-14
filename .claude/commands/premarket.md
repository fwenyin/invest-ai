---
description: Pre-market run (~08:30 ET). Builds the day's game plan, watchlist with levels, and pre-planned trades.
allowed-tools: Task, Read, Write, Edit, Bash, Glob, mcp__to-the-moon-data__*
argument-hint: "[optional extra tickers to include]"
---

# Pre-market run — build today's game plan

You are running the short-term desk's **pre-market** session. Goal: a concrete, risk-checked game plan the human can act on at the open. Today's date is the system date.

## Steps
1. **Load context**: Read `config/universe.json`, `config/risk_rules.yaml`, `portfolio/positions.json`, and the most recent `portfolio/journal/*.md` + relevant entries from `portfolio/memory/lessons.json`. Fold yesterday's lessons into today's thinking. Include any extra tickers from: $ARGUMENTS.

2. **Macro first**: Launch the `macro-strategist` subagent to set today's regime/bias and flag event blackouts.

3. **Scan for candidates**: Use the data MCP to scan overnight gaps across the universe, top market news, the economic + earnings calendars, recent Trump posts, and Reddit sentiment. From this, assemble a focused **watchlist (5–10 names)** of the day's best opportunities. Don't analyze the whole universe — concentrate.

4. **Deep-dive the watchlist** (run these subagents on the watchlist; you may run analysts in parallel):
   - `technical-analyst` → exact levels per name
   - `news-catalyst-analyst` → catalysts
   - `sentiment-analyst` → flow/positioning
   - `fundamentals-analyst` → fundamental risk (earnings landmines)

5. **Debate** the top 3–5 candidates: run `bull-researcher` and `bear-researcher`.

6. **Decide**: run `trader` → ideas with entry/stop/target/R:R.

7. **Risk gate**: run `risk-manager` → size & approve/veto against the rules.

8. **Plan**: run `portfolio-manager` → the final action list (reconciled with current positions).

9. **Write the report** to `reports/daily/<YYYY-MM-DD>/premarket.md` using the template in `.claude/templates/report_template.md`. Keep it scannable — the human reads this in 2 minutes before the open.

End your message with a 5-line TL;DR: regime, bias, top 3 trade ideas (with entry/stop), and any event blackout warning.
