# to-the-moon — project guide for Claude

Multi-agent investment desk. Two sleeves: short-term (daily, 5 runs) and long-term (weekly).
The human trades **manually** — never place orders or assume execution. Output = decisions,
sized plans, journals.

## How it fits together
- **Slash commands** (`.claude/commands/`) orchestrate the workflow; they spawn **subagents**
  (`.claude/agents/`) via the Task tool in sequence: analysts → bull/bear debate → trader →
  risk-manager → portfolio-manager → (postmarket) reflection-agent.
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
Don't print secret values.
