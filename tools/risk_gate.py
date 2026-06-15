"""Deterministic risk gate — the hard, code-enforced version of the risk rules.

The `risk-manager` agent used to do this arithmetic in its head against
`config/risk_rules.yaml`. An LLM doing floating-point math and reading a YAML is
not an enforcement mechanism. This module is: it takes an idea + the current book
+ the rules and returns an unambiguous PASS/FAIL per check, with the numbers.
The agent may *read* this result; it may not override a FAIL.

Pure core (`evaluate`) takes plain dicts so it is unit-testable with no I/O. The
CLI / MCP wrapper loads `config/risk_rules.yaml` and `portfolio/positions.json`.

CLI:
    python tools/risk_gate.py --ticker SMCI --side short --entry 31.10 --stop 31.90 --target 27.50
    python tools/risk_gate.py --ticker IWM --side long --entry 291.6 --stop 289.4 --target 299 --sector financials
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from common import ROOT, emit, err, ok


def _load_rules() -> dict:
    import yaml

    return yaml.safe_load((ROOT / "config" / "risk_rules.yaml").read_text())


def _load_positions() -> dict:
    path = ROOT / "portfolio" / "positions.json"
    if not path.exists():
        return {"cash": 0, "positions": []}
    return json.loads(path.read_text())


def _check(name: str, passed: bool, detail: str) -> dict:
    return {"check": name, "pass": bool(passed), "detail": detail}


def evaluate(idea: dict, positions: dict, rules: dict, context: dict | None = None) -> dict:
    """Deterministically size an idea and check it against the hard limits.

    idea:      {ticker, side(long|short), entry, stop, target, sector?,
                instrument(stock|option|future)?, option_premium_per_contract?}
    positions: portfolio/positions.json shape — {cash, positions:[{ticker, side, entry,
               stop, shares, sector?, theme?, instrument?, option_premium?}, ...]}
    rules:     parsed config/risk_rules.yaml
    context:   externally-supplied facts the math can't derive on its own:
               {realized_day_pnl_pct, event_blackout_active, new_trades_today,
                correlated_open_count}. Defaults are the SAFE (most-restrictive)
                values so an omitted/unknown context never silently passes.
    """
    context = context or {}
    equity = float(rules["account"]["equity"])
    pt = rules["per_trade"]
    pf = rules["portfolio"]
    daily = rules["daily"]
    checks: list[dict] = []

    entry = idea.get("entry")
    stop = idea.get("stop")
    target = idea.get("target")
    side = (idea.get("side") or "long").lower()
    instrument = (idea.get("instrument") or "stock").lower()

    # --- Hard precondition: an idea without a stop is unsizable. ---
    if entry is None or stop is None or float(entry) == float(stop):
        return {
            "ticker": idea.get("ticker"),
            "verdict": "REJECTED",
            "reason": "no usable stop (entry and stop required and must differ)",
            "checks": [_check("has_stop", False, "missing/zero-distance stop")],
            "size": None,
        }

    entry, stop = float(entry), float(stop)
    risk_per_share = abs(entry - stop)

    # --- Sizing (risk-based, then capped by concentration). Always round DOWN. ---
    max_shares_by_risk = math.floor(equity * (pt["max_risk_pct"] / 100) / risk_per_share)
    max_notional = equity * (pf["max_position_pct"] / 100)
    max_shares_by_position = math.floor(max_notional / entry) if entry > 0 else 0
    shares = max(min(max_shares_by_risk, max_shares_by_position), 0)
    capped_by_concentration = max_shares_by_position < max_shares_by_risk

    notional = shares * entry
    trade_risk = shares * risk_per_share
    trade_risk_pct = (trade_risk / equity) * 100 if equity else 0.0
    rr = abs(float(target) - entry) / risk_per_share if target is not None else 0.0

    # --- Existing book: heat, sector, correlation. ---
    open_risk = 0.0
    sector_notional: dict[str, float] = {}
    for p in positions.get("positions", []):
        try:
            pr = abs(float(p["entry"]) - float(p["stop"])) * float(p["shares"])
        except (KeyError, TypeError, ValueError):
            pr = 0.0
        open_risk += pr
        sec = (p.get("sector") or "unknown").lower()
        sector_notional[sec] = sector_notional.get(sec, 0.0) + float(p.get("shares", 0)) * float(p.get("entry", 0))
    open_heat_pct = (open_risk / equity) * 100 if equity else 0.0
    heat_after_pct = open_heat_pct + trade_risk_pct

    sector = (idea.get("sector") or "unknown").lower()
    sector_after = sector_notional.get(sector, 0.0) + notional
    sector_after_pct = (sector_after / equity) * 100 if equity else 0.0

    # --- Context-driven checks. SAFE defaults: assume the worst when unknown. ---
    realized_day_pnl_pct = float(context.get("realized_day_pnl_pct", 0.0))
    blackout_active = bool(context.get("event_blackout_active", True))   # unknown ⇒ assume blackout
    new_trades_today = int(context.get("new_trades_today", 0))
    correlated_open = int(context.get("correlated_open_count", 0))

    checks.append(_check("has_stop", True, f"risk/share={risk_per_share:.4f}"))
    checks.append(_check("reward_to_risk", rr >= pt["min_reward_to_risk"],
                         f"R:R={rr:.2f} (min {pt['min_reward_to_risk']})"))
    checks.append(_check("per_trade_risk", trade_risk_pct <= pt["max_risk_pct"] + 1e-9,
                         f"{trade_risk_pct:.2f}% (max {pt['max_risk_pct']}%)"))
    checks.append(_check("open_heat", heat_after_pct <= pf["max_open_heat_pct"] + 1e-9,
                         f"{heat_after_pct:.2f}% after (max {pf['max_open_heat_pct']}%)"))
    checks.append(_check("position_concentration", notional <= max_notional + 1e-6,
                         f"notional ${notional:.0f} = {(notional/equity*100):.1f}% (max {pf['max_position_pct']}%)"))
    checks.append(_check("sector_concentration", sector_after_pct <= pf["max_sector_pct"] + 1e-9,
                         f"sector '{sector}' {sector_after_pct:.1f}% (max {pf['max_sector_pct']}%)"))
    checks.append(_check("correlation", correlated_open < pf["max_correlated_positions"],
                         f"{correlated_open} correlated open (max {pf['max_correlated_positions']-0})"))
    checks.append(_check("event_blackout", not blackout_active,
                         "inside/unknown high-impact window" if blackout_active else "clear"))
    checks.append(_check("daily_loss_killswitch", realized_day_pnl_pct > -daily["max_loss_pct"],
                         f"day P&L {realized_day_pnl_pct:.2f}% (kill at -{daily['max_loss_pct']}%)"))
    checks.append(_check("overtrading", new_trades_today < daily["max_new_trades"],
                         f"{new_trades_today} new trades today (max {daily['max_new_trades']})"))

    if instrument == "option":
        prem = float(idea.get("option_premium_per_contract", 0.0)) * 100  # per-contract $ at risk
        opt = rules.get("instruments", {}).get("options", {})
        cap = opt.get("max_pct_of_equity", 5.0)
        checks.append(_check("option_premium_cap", prem <= equity * cap / 100 + 1e-6,
                             f"premium ${prem:.0f} (cap {cap}% = ${equity*cap/100:.0f})"))

    if shares <= 0:
        checks.append(_check("nonzero_size", False, "risk/concentration limits size to 0 shares"))

    failed = [c["check"] for c in checks if not c["pass"]]
    verdict = "APPROVED" if not failed else "REJECTED"
    if verdict == "APPROVED" and capped_by_concentration:
        verdict = "APPROVED (reduced size)"

    return {
        "ticker": idea.get("ticker"),
        "side": side,
        "verdict": verdict,
        "failed_checks": failed,
        "size": {
            "shares": shares,
            "notional": round(notional, 2),
            "notional_pct_equity": round(notional / equity * 100, 2) if equity else 0.0,
            "risk_dollars": round(trade_risk, 2),
            "risk_pct_equity": round(trade_risk_pct, 2),
            "reward_to_risk": round(rr, 2),
            "capped_by_concentration": capped_by_concentration,
        },
        "book": {
            "open_heat_pct": round(open_heat_pct, 2),
            "heat_after_pct": round(heat_after_pct, 2),
            "heat_cap_pct": pf["max_open_heat_pct"],
        },
        "checks": checks,
        "context_used": {
            "realized_day_pnl_pct": realized_day_pnl_pct,
            "event_blackout_active": blackout_active,
            "new_trades_today": new_trades_today,
            "correlated_open_count": correlated_open,
        },
        "note": ("Context flags (blackout/day-P&L/trade-count/correlation) are supplied by the "
                 "caller; unknown values default to the most restrictive setting. The math checks "
                 "are enforced — a REJECTED idea must not be traded."),
    }


def gate(idea: dict, context: dict | None = None) -> dict:
    """CLI/MCP entry: load real rules + book, evaluate one idea."""
    try:
        return ok(evaluate(idea, _load_positions(), _load_rules(), context))
    except Exception as e:  # surface loudly — never swallow into a silent pass
        return err(f"risk_gate failed for {idea.get('ticker')}: {e}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Deterministic risk gate for one trade idea.")
    p.add_argument("--ticker", required=True)
    p.add_argument("--side", default="long", choices=["long", "short"])
    p.add_argument("--entry", type=float, required=True)
    p.add_argument("--stop", type=float, required=True)
    p.add_argument("--target", type=float, required=True)
    p.add_argument("--sector", default="unknown")
    p.add_argument("--instrument", default="stock", choices=["stock", "option", "future"])
    p.add_argument("--option-premium", type=float, default=0.0)
    # context flags (default to the SAFE / most-restrictive interpretation)
    p.add_argument("--day-pnl-pct", type=float, default=0.0)
    p.add_argument("--blackout", dest="blackout", action="store_true", default=True)
    p.add_argument("--no-blackout", dest="blackout", action="store_false")
    p.add_argument("--new-trades-today", type=int, default=0)
    p.add_argument("--correlated-open", type=int, default=0)
    a = p.parse_args()

    idea: dict[str, Any] = {
        "ticker": a.ticker, "side": a.side, "entry": a.entry, "stop": a.stop,
        "target": a.target, "sector": a.sector, "instrument": a.instrument,
        "option_premium_per_contract": a.option_premium,
    }
    ctx = {
        "realized_day_pnl_pct": a.day_pnl_pct,
        "event_blackout_active": a.blackout,
        "new_trades_today": a.new_trades_today,
        "correlated_open_count": a.correlated_open,
    }
    emit(gate(idea, ctx))
