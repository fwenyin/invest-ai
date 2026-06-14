---
description: One-time setup — install Python deps, configure API keys, verify the data layer, and (optionally) schedule the daily runs.
allowed-tools: Bash, Read, Edit, Write
---

# Setup the to-the-moon desk

Walk the human through first-time setup. Be interactive and check each step.

## Steps
1. **Disk check**: `df -h /System/Volumes/Data | tail -1`. Warn if < 3 GB free (deps need room).
2. **Install**: run `bash scripts/install.sh` (creates `.venv`, installs `requirements.txt`, copies `.env`). Report any failures plainly.
3. **Keys**: confirm `.env` exists. Tell the human exactly what to fill in:
   - `FINNHUB_API_KEY` — free at https://finnhub.io/register
   - `SUBSTACK_PRIVATE_RSS` — Bottom Up Bulletin → Substack account → Settings → your private RSS feed URL (contains a secret token)
   - `ACCOUNT_EQUITY` — your starting capital (also set `account.equity` in `config/risk_rules.yaml`)
   Do NOT print secret values back to the chat.
4. **Verify data layer** (run a few, report JSON sanity):
   - `.venv/bin/python tools/prices.py AAPL`
   - `.venv/bin/python tools/news.py --market`
   - `.venv/bin/python tools/trump.py`
   - `.venv/bin/python tools/substack.py` (only meaningful after the RSS URL is set)
   - `.venv/bin/python tools/calendar_econ.py` (needs Finnhub key)
5. **Verify backtest**: `.venv/bin/python backtest/engine.py SPY ma_cross` → confirm stats come back.
6. **MCP**: confirm `.mcp.json` points at `.venv/bin/python`. The data tools are exposed to the agents via the `to-the-moon-data` MCP server once the project is trusted.
7. **Schedule (optional)**: `python scripts/gen_schedule.py` to preview local times, then `--install` to activate launchd jobs. Explain the Mac-must-be-awake caveat and the cloud `/schedule` alternative.

Finish with a short checklist of what's done and what the human still needs to do (mainly: paste keys into `.env`).
