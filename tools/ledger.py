"""Forward decision ledger — the thing that lets the desk grade itself.

Every idea the desk emits (taken OR vetoed) is logged here at the moment of
decision, with its plan. Later, each open entry is scored against the actual
price path → realized R multiple, win/loss, what it hit. Until ~30-50 *forward*
(post-decision, out of any model's training window) calls are scored, the desk
has no evidence of edge — only a backtest of strategies it doesn't trade.

This is deliberately separate from `portfolio/positions.json` (the human's real
book): the ledger records what the desk *recommended*, so we can measure the
recommendations regardless of what the human chose to execute.

CLI:
    python tools/ledger.py log --session premarket --ticker SMCI --side short \
        --entry 31.10 --stop 31.90 --target 27.50 --conviction med --thesis "fade bounce" --vetoed
    python tools/ledger.py score                # mark-to-market every open entry off live quotes
    python tools/ledger.py score --id <id> --exit 27.90
    python tools/ledger.py report               # hit rate, avg R, forward-only scorecard
    python tools/ledger.py list
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from common import ROOT, emit, err, ok

LEDGER = ROOT / "portfolio" / "ledger.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load() -> dict:
    if not LEDGER.exists():
        return {"_comment": ("Forward decision ledger. /premarket logs every idea (taken or "
                             "vetoed) at decision time; /postmarket scores open entries against "
                             "the actual price path. Only SCORED FORWARD calls are evidence of edge."),
                "entries": []}
    return json.loads(LEDGER.read_text())


def _save(data: dict) -> None:
    LEDGER.write_text(json.dumps(data, indent=2))


def _gen_id(ticker: str) -> str:
    return f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-{ticker.upper()}"


def log_idea(idea: dict) -> dict:
    """Append one decision to the ledger. Returns the stored entry."""
    entry = float(idea["entry"])
    stop = float(idea["stop"])
    target = idea.get("target")
    side = (idea.get("side") or "long").lower()
    risk_per_share = abs(entry - stop)
    rr = (abs(float(target) - entry) / risk_per_share) if (target is not None and risk_per_share) else None

    rec = {
        "id": _gen_id(idea["ticker"]),
        "logged_at": _now(),
        "session": idea.get("session", "unknown"),
        "ticker": idea["ticker"].upper(),
        "side": side,
        "instrument": idea.get("instrument", "stock"),
        "entry": entry,
        "stop": stop,
        "target": float(target) if target is not None else None,
        "reward_to_risk": round(rr, 2) if rr is not None else None,
        "conviction": idea.get("conviction", "med"),
        "thesis": idea.get("thesis", ""),
        "approved": bool(idea.get("approved", False)),
        "vetoed": bool(idea.get("vetoed", False)),
        "status": "open",
        "outcome": None,
    }
    data = _load()
    data["entries"].append(rec)
    _save(data)
    return rec


def score_entry(rec: dict, exit_price: float) -> dict:
    """Pure scoring: compute realized R, return %, result, and what it hit."""
    entry, stop = float(rec["entry"]), float(rec["stop"])
    target = rec.get("target")
    risk_per_share = abs(entry - stop)
    sign = 1.0 if rec["side"] == "long" else -1.0
    realized_r = (sign * (exit_price - entry) / risk_per_share) if risk_per_share else 0.0
    return_pct = sign * (exit_price / entry - 1) * 100

    # What did the path resolve to (using the marked exit as the resolution price)?
    if rec["side"] == "long":
        hit_stop = exit_price <= stop
        hit_target = target is not None and exit_price >= target
    else:
        hit_stop = exit_price >= stop
        hit_target = target is not None and exit_price <= target
    hit = "stop" if hit_stop else "target" if hit_target else "open/timeout"
    result = "win" if realized_r > 0.05 else "loss" if realized_r < -0.05 else "scratch"

    return {
        "scored_at": _now(),
        "exit_price": round(float(exit_price), 4),
        "realized_r": round(realized_r, 2),
        "return_pct": round(return_pct, 2),
        "result": result,
        "hit": hit,
    }


def report(entries: list[dict]) -> dict:
    """Aggregate scorecard. Counts only SCORED entries as evidence."""
    scored = [e for e in entries if e.get("outcome")]
    rs = [e["outcome"]["realized_r"] for e in scored]
    wins = [r for r in rs if r > 0.05]
    losses = [r for r in rs if r < -0.05]

    def avg(xs):
        return round(sum(xs) / len(xs), 2) if xs else 0.0

    by_setup: dict[str, list[float]] = {}
    for e in scored:
        by_setup.setdefault(e.get("session", "unknown"), []).append(e["outcome"]["realized_r"])

    enough = len(scored) >= 30
    return {
        "total_logged": len(entries),
        "scored": len(scored),
        "open_unscored": len(entries) - len(scored),
        "win_rate_pct": round(100 * len(wins) / len(scored), 1) if scored else 0.0,
        "avg_r": avg(rs),
        "sum_r": round(sum(rs), 2),
        "expectancy_r": avg(rs),
        "avg_win_r": avg(wins),
        "avg_loss_r": avg(losses),
        "profit_factor": round(sum(wins) / abs(sum(losses)), 2) if losses else (float("inf") if wins else 0.0),
        "by_session": {k: {"n": len(v), "avg_r": avg(v)} for k, v in by_setup.items()},
        "evidence_note": (
            f"{len(scored)} scored forward calls. "
            + ("Sample is large enough to start trusting the expectancy."
               if enough else
               f"NOT ENOUGH to judge edge — need ~{max(0, 30 - len(scored))} more scored calls. "
               "These must be FORWARD (logged before the outcome was known); historical/backfilled "
               "calls are tainted by hindsight and do not count.")),
    }


# ── CLI plumbing ─────────────────────────────────────────────────────
def _cmd_log(a) -> dict:
    return ok(log_idea({
        "session": a.session, "ticker": a.ticker, "side": a.side, "instrument": a.instrument,
        "entry": a.entry, "stop": a.stop, "target": a.target, "conviction": a.conviction,
        "thesis": a.thesis, "approved": a.approved, "vetoed": a.vetoed,
    }))


def _cmd_score(a) -> dict:
    import prices

    data = _load()
    targets = [e for e in data["entries"] if e["status"] == "open" and (not a.id or e["id"] == a.id)]
    if not targets:
        return err("no matching open ledger entries to score")
    scored = []
    for e in targets:
        if a.exit is not None:
            px = a.exit
        else:
            q = prices.quote(e["ticker"])
            if not q.get("ok"):
                return err(f"could not fetch price to score {e['id']}: {q.get('error')}")
            px = q["data"]["price"]
        e["outcome"] = score_entry(e, px)
        e["status"] = "scored"
        scored.append(e["id"])
    _save(data)
    return ok({"scored": scored, "scorecard": report(data["entries"])})


def _cmd_report(_a) -> dict:
    return ok(report(_load()["entries"]))


def _cmd_list(_a) -> dict:
    return ok({"entries": _load()["entries"]})


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Forward decision ledger.")
    sub = p.add_subparsers(dest="cmd", required=True)

    lg = sub.add_parser("log")
    lg.add_argument("--session", default="unknown")
    lg.add_argument("--ticker", required=True)
    lg.add_argument("--side", default="long", choices=["long", "short"])
    lg.add_argument("--instrument", default="stock")
    lg.add_argument("--entry", type=float, required=True)
    lg.add_argument("--stop", type=float, required=True)
    lg.add_argument("--target", type=float)
    lg.add_argument("--conviction", default="med")
    lg.add_argument("--thesis", default="")
    lg.add_argument("--approved", action="store_true")
    lg.add_argument("--vetoed", action="store_true")
    lg.set_defaults(func=_cmd_log)

    sc = sub.add_parser("score")
    sc.add_argument("--id", default=None)
    sc.add_argument("--exit", type=float, default=None)
    sc.set_defaults(func=_cmd_score)

    sub.add_parser("report").set_defaults(func=_cmd_report)
    sub.add_parser("list").set_defaults(func=_cmd_list)

    args = p.parse_args()
    emit(args.func(args))
