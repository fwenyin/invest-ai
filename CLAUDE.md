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
  `portfolio/memory/lessons.json` (reflection memory), `portfolio/ledger.json` (short-term forward
  decision log), `portfolio/lt_ledger.json` (long-term picks graded vs QQQ), `config/risk_rules.yaml`
  (hard limits), `config/universe.json` (what to scan).
- **Enforcement tools** (run them, don't reason them by hand): `tools/risk_gate.py` deterministically
  sizes and PASS/FAILs an idea against `risk_rules.yaml`; `tools/ledger.py` logs/scores every
  short-term decision; `tools/valuation.py` is the deterministic two-stage DCF / reverse-DCF for the
  long-term sleeve (the LLM picks the inputs, the code does the math); `tools/lt_ledger.py` logs each
  long-term pick and grades it **vs QQQ** over time with thesis-indicator tracking. All are also MCP
  tools (`risk_gate_check`, `ledger_*`, `valuation_assess`, `lt_ledger_*`).
- **Edge thesis & validation bar**: `docs/EDGE.md` — the falsifiable edge hypothesis and the two
  gates (cross-universe backtest + forward ledger) it must clear before real capital.
- **Reports** go to `reports/daily/<YYYY-MM-DD>/<session>.md` and `reports/weekly/<YYYY-Www>/`.

## Rules that matter
- **Never** approve a trade idea without a stop and an R:R computed from real levels.
- Size and risk-check via `tools/risk_gate.py` (or the `risk_gate_check` MCP tool) — the math is
  **code-enforced**, not eyeballed. The `risk-manager` can veto but may NOT approve an idea the
  gate REJECTED. Respect `risk_rules.yaml` (1% per trade, 6% heat, 2:1 R:R, event blackouts,
  daily-loss kill switch).
- **Fail loud, never guess**: if a thesis-critical feed (quotes, econ calendar) errors, do not fall
  back to model memory — mark it UNVERIFIED, keep the blackout active, and abort rather than
  fabricate. The gate's blackout flag defaults to ON unless the calendar is verified clear.
- **Log every decision** (taken AND vetoed) to the forward ledger; score it at postmarket. Only
  *scored forward* calls are evidence of edge — historical/backfilled calls are tainted by LLM
  hindsight and don't count.
- Be selective — "NO TRADE" / "STAND ASIDE" is a valid, valued output.
- Backtest verdicts: distrust edges with <20 trades or big in-sample→out-of-sample decay; prefer
  `--universe` over single-ticker; remember results are an upper bound (survivorship).
- Always include the **not-financial-advice** framing in user-facing reports.

## Python env
Use `.venv/bin/python` (created by `scripts/install.sh`). Keys load from `.env` (gitignored).
Don't print secret values. Project permissions live in `.claude/settings.json`; personal
overrides go in `.claude/settings.local.json` (gitignored).

## Tests
`.venv/bin/python -m pytest backtest/test_engine.py -q` — pins the engine's no-look-ahead,
trade-accounting, and `max_hold` (fill-relative time exit) guarantees. Run after touching `backtest/`.
`.venv/bin/python -m pytest tools/test_risk_gate.py tools/test_ledger.py -q` — pins the
deterministic risk-gate math and the ledger's forward scoring. Run after touching `tools/risk_gate.py`
or `tools/ledger.py`. All are pure functions — no network.
