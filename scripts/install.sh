#!/usr/bin/env bash
# One-shot installer: venv + deps + .env scaffold. Run from repo root.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "▸ Creating virtualenv (.venv)…"
python3 -m venv .venv

echo "▸ Installing dependencies (this pulls vectorbt/numpy/etc — a few minutes)…"
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt

if [ ! -f .env ]; then
  cp config/.env.example .env
  echo "▸ Created .env from template — edit it and add your FINNHUB_API_KEY and SUBSTACK_PRIVATE_RSS."
fi

echo "▸ Smoke-testing the data layer…"
./.venv/bin/python tools/prices.py AAPL || echo "  (price test failed — check network)"

echo
echo "✅ Done. Next:"
echo "   1) Edit .env with your keys."
echo "   2) Try a backtest:   ./.venv/bin/python backtest/engine.py SPY ma_cross"
echo "   3) Schedule runs:    python scripts/gen_schedule.py --install"
