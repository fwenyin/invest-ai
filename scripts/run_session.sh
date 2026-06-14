#!/usr/bin/env bash
# Run one desk session headlessly via Claude Code. Used by launchd / cron.
# Usage: scripts/run_session.sh premarket|open|midmorning|powerhour|postmarket|weekly-longterm
set -euo pipefail

SESSION="${1:?usage: run_session.sh <session>}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

# Load env (.env) if present so headless runs have keys.
[ -f .env ] && set -a && . ./.env && set +a

LOG_DIR="$REPO_DIR/reports/logs"
mkdir -p "$LOG_DIR"
STAMP="$(date +%Y-%m-%d_%H%M%S)"

# Resolve claude binary (launchd has a minimal PATH).
CLAUDE_BIN="$(command -v claude || echo "$HOME/.claude/local/claude")"

echo "[$(date)] running /$SESSION" >> "$LOG_DIR/$SESSION.log"
"$CLAUDE_BIN" -p "/$SESSION" \
  --permission-mode acceptEdits \
  >> "$LOG_DIR/${SESSION}_${STAMP}.out" 2>> "$LOG_DIR/$SESSION.log" || \
  echo "[$(date)] /$SESSION FAILED (see logs)" >> "$LOG_DIR/$SESSION.log"
