---
description: Pre-market run (~08:30 ET). Builds the day's game plan, watchlist with levels, and pre-planned trades.
allowed-tools: Task, Read, Write, Edit, Bash, Glob, mcp__to-the-moon-data__*
argument-hint: "[optional extra tickers to include]"
---

# Pre-market run — build today's game plan

You are running the short-term desk's **pre-market** session. Goal: a concrete, risk-checked game plan the human can act on at the open. Today's date is the system date.

## Steps
1. **Load context**: Read `config/universe.json`, `config/risk_rules.yaml`, `portfolio/positions.json`, and the most recent `portfolio/journal/*.md` + relevant entries from `portfolio/memory/lessons.json`. Fold yesterday's lessons into today's thinking. Include any extra tickers from: $ARGUMENTS.

2. **Data integrity gate (fail loud, never guess)**: before any analysis, verify the thesis-critical feeds actually returned data:
   - live quotes for the index ETFs + any watchlist names,
   - the **economic calendar** (needed to clear or confirm the event blackout).
   If a thesis-critical feed errors or returns empty (e.g. the econ calendar 403s), **do not fabricate or fall back to model memory.** Either retry, or mark that input UNVERIFIED and treat its risk as ACTIVE — specifically, leave the risk gate's blackout flag ON (no `--no-blackout`) so no swing is approved through an unconfirmed window. If quotes for a name fail, drop it from the watchlist rather than guessing levels. If the macro/quote layer is broadly down, abort: write a short "NO PLAN — data layer down" report instead of a fabricated one.

3. **Macro first**: Launch the `macro-strategist` subagent to set today's regime/bias and flag event blackouts.

4. **Scan for candidates**: Use the data MCP to scan overnight gaps across the universe, top market news, the economic + earnings calendars, and recent Trump posts. From this, assemble a focused **watchlist (5–10 names)** of the day's best opportunities. Don't analyze the whole universe — concentrate.

5. **Deep-dive the watchlist** (run these subagents on the watchlist; you may run analysts in parallel):
   - `technical-analyst` → exact levels per name
   - `news-catalyst-analyst` → catalysts
   - `sentiment-analyst` → flow/positioning
   - `fundamentals-analyst` → fundamental risk (earnings landmines)

6. **Debate** the top 3–5 candidates: run `bull-researcher` and `bear-researcher`.

7. **Decide**: run `trader` → ideas with entry/stop/target/R:R.

8. **Risk gate**: run `risk-manager` → size & approve/veto against the rules.

9. **Plan**: run `portfolio-manager` → the final action list (reconciled with current positions).

10. **Log every decision to the forward ledger** — this is how the desk later grades itself. For each idea the trader proposed (whether APPROVED or VETOED), append it with its plan:
   ```bash
   .venv/bin/python tools/ledger.py log --session premarket --ticker SMCI --side short \
     --entry 31.10 --stop 31.90 --target 27.50 --conviction med --thesis "fade bounce, fundamentals weak" --vetoed
   ```
   Use `--approved` for ideas that passed the risk gate, `--vetoed` for rejected ones. Log them all — vetoed calls are evidence too. (Or use the `ledger_log` MCP tool.)

11. **Write the report** to `reports/daily/<YYYY-MM-DD>/premarket.md` using the template in `.claude/templates/report_template.md`. Keep it scannable — the human reads this in 2 minutes before the open.

End your message with a 5-line TL;DR: regime, bias, top 3 trade ideas (with entry/stop), and any event blackout warning.
