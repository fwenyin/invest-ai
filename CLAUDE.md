# to-the-moon — project guide for Claude

Multi-agent investment desk. Two sleeves: short-term (daily, 5 runs) and long-term (weekly).
The human trades **manually** — never place orders or assume execution. Output = decisions,
sized plans, journals.

## How it fits together
- **Slash commands** (`.claude/commands/`) orchestrate the workflow; they spawn **subagents**
  (`.claude/agents/`) via the Task tool in sequence: analysts → bull/bear debate → trader →
  risk-manager → portfolio-manager → (postmarket) reflection-agent.
- **Skills** (`.claude/skills/`) hold the reusable procedures the agents/commands lean on:
  `position-sizing` (the canonical size/heat/risk-gate math) and `backtest-runner` (how to run
  and honestly read a backtest). Treat these as the single source of truth.
- **Report template** lives at `.claude/templates/report_template.md` (not in `commands/`, so it
  isn't surfaced as a slash command).
- **Data** comes from the `to-the-moon-data` MCP server (`tools/mcp_server.py`) — call those
  `mcp__to-the-moon-data__*` tools, or the equivalent `tools/*.py` CLIs.
- **State**: `portfolio/positions.json` (truth for reconciliation), `portfolio/longterm.json`,
  `portfolio/memory/lessons.json` (reflection memory), `config/risk_rules.yaml` (hard limits),
  `config/universe.json` (what to scan).
- **Reports** go to `reports/daily/<YYYY-MM-DD>/<session>.md` and `reports/weekly/<YYYY-Www>/`.

## Rules that matter
- **Never** approve a trade idea without a stop and an R:R computed from real levels.
- The `risk-manager` can veto; respect `risk_rules.yaml` (1% per trade, 6% heat, 2:1 R:R,
  event blackouts, daily-loss kill switch). Show the position-size math.
- Be selective — "NO TRADE" / "STAND ASIDE" is a valid, valued output.
- Backtest verdicts: distrust edges with <20 trades or big in-sample→out-of-sample decay.
- Always include the **not-financial-advice** framing in user-facing reports.

## Python env
Use `.venv/bin/python` (created by `scripts/install.sh`). Keys load from `.env` (gitignored).
Don't print secret values. Project permissions live in `.claude/settings.json`; personal
overrides go in `.claude/settings.local.json` (gitignored).

## Tests
`.venv/bin/python -m pytest backtest/test_engine.py -q` — pins the engine's no-look-ahead and
trade-accounting guarantees (pure functions, no network). Run after touching `backtest/`.
