See CLAUDE.md at the repo root for the full project guide — it applies here too.

## Workflow commands

To run a workflow (e.g. premarket), ask: "run the premarket workflow" — the agent
will read `.claude/commands/premarket.md` and execute the pipeline using the
subagents in `.claude/agents/`.

Available workflows: premarket, open, midmorning, powerhour, postmarket, weekly-longterm, backtest, positions, setup.
