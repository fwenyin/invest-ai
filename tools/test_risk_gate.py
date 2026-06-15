"""Tests for the deterministic risk gate — the math the agent must NOT eyeball.

Pure-function tests against the real rule shape; no I/O, no network.
Run:  .venv/bin/python -m pytest tools/test_risk_gate.py -q
"""
from __future__ import annotations

import math

import pytest

import risk_gate

RULES = {
    "account": {"equity": 10000},
    "per_trade": {"max_risk_pct": 1.0, "min_reward_to_risk": 2.0},
    "portfolio": {"max_open_heat_pct": 6.0, "max_position_pct": 20.0,
                  "max_sector_pct": 35.0, "max_correlated_positions": 3},
    "daily": {"max_loss_pct": 3.0, "max_new_trades": 5},
    "instruments": {"options": {"max_pct_of_equity": 5.0}},
}
FLAT = {"cash": 10000, "positions": []}
SAFE_CTX = {"realized_day_pnl_pct": 0.0, "event_blackout_active": False,
            "new_trades_today": 0, "correlated_open_count": 0}


def _checks(res):
    return {c["check"]: c["pass"] for c in res["checks"]}


def test_clean_long_sized_by_risk_when_stop_is_wide_enough():
    # Stop ≥5% away so the 1%-risk notional stays under the 20% position cap → risk binds.
    idea = {"ticker": "X", "side": "long", "entry": 50.0, "stop": 47.0, "target": 59.0}
    res = risk_gate.evaluate(idea, FLAT, RULES, SAFE_CTX)
    assert res["verdict"] == "APPROVED"
    # 1% of 10k = $100 risk / $3 per share = 33 shares (floored); notional $1650 = 16.5% < 20%.
    assert res["size"]["shares"] == math.floor(100 / 3) == 33
    assert res["size"]["capped_by_concentration"] is False
    assert res["size"]["risk_pct_equity"] <= 1.0 + 1e-9
    assert res["size"]["reward_to_risk"] == pytest.approx(3.0, abs=0.01)


def test_tight_stop_on_pricey_name_is_concentration_capped():
    # Real case from the desk's own report: SMCI tight stop wants 125 sh but 20% cap = 64 sh.
    idea = {"ticker": "IWM", "side": "long", "entry": 291.6, "stop": 289.4, "target": 299.0}
    res = risk_gate.evaluate(idea, FLAT, RULES, SAFE_CTX)
    assert res["verdict"] == "APPROVED (reduced size)"
    assert res["size"]["shares"] == math.floor(2000 / 291.6) == 6  # 20% of 10k / price
    assert res["size"]["capped_by_concentration"] is True
    assert res["size"]["risk_pct_equity"] < 1.0  # actual risk well under the 1% cap


def test_missing_stop_is_rejected_outright():
    res = risk_gate.evaluate({"ticker": "X", "side": "long", "entry": 50, "stop": None, "target": 60},
                             FLAT, RULES, SAFE_CTX)
    assert res["verdict"] == "REJECTED"
    assert "no usable stop" in res["reason"]


def test_sub_2to1_rr_fails():
    idea = {"ticker": "X", "side": "long", "entry": 100, "stop": 95, "target": 104}  # R:R 0.8
    res = risk_gate.evaluate(idea, FLAT, RULES, SAFE_CTX)
    assert res["verdict"] == "REJECTED"
    assert "reward_to_risk" in res["failed_checks"]


def test_unknown_context_defaults_to_blackout_active():
    idea = {"ticker": "X", "side": "long", "entry": 100, "stop": 98, "target": 106}
    res = risk_gate.evaluate(idea, FLAT, RULES, context=None)  # no context ⇒ assume blackout
    assert _checks(res)["event_blackout"] is False
    assert res["verdict"] == "REJECTED"
    assert "event_blackout" in res["failed_checks"]


def test_daily_loss_killswitch_blocks_new_trades():
    idea = {"ticker": "X", "side": "long", "entry": 100, "stop": 98, "target": 106}
    ctx = {**SAFE_CTX, "realized_day_pnl_pct": -3.5}
    res = risk_gate.evaluate(idea, FLAT, RULES, ctx)
    assert "daily_loss_killswitch" in res["failed_checks"]


def test_concentration_cap_reduces_size():
    # Cheap stock, tight stop → risk allows a notional above the 20% position cap.
    idea = {"ticker": "PENNY", "side": "long", "entry": 5.0, "stop": 4.99, "target": 5.10}
    res = risk_gate.evaluate(idea, FLAT, RULES, SAFE_CTX)
    # max_notional = 20% of 10k = $2000 → 400 shares cap, below the risk-based size.
    assert res["size"]["shares"] == 400
    assert res["size"]["capped_by_concentration"] is True
    assert res["verdict"] == "APPROVED (reduced size)"


def test_open_heat_cap_blocks_when_book_already_hot():
    # Existing book: 5.8% heat on a modest 10% notional (wide stop), different sector.
    positions = {"cash": 0, "positions": [
        {"ticker": "A", "entry": 20, "stop": 8.4, "shares": 50, "sector": "tech"},  # risk $580=5.8%, $1000 notional
    ]}
    idea = {"ticker": "B", "side": "long", "entry": 100, "stop": 98, "target": 106, "sector": "energy"}
    res = risk_gate.evaluate(idea, positions, RULES, SAFE_CTX)
    assert "open_heat" in res["failed_checks"]            # 5.8% + 0.4% = 6.2% > 6%
    assert "sector_concentration" not in res["failed_checks"]  # different sectors, both under cap
    assert res["book"]["heat_after_pct"] > RULES["portfolio"]["max_open_heat_pct"]


def test_short_side_sizing_is_symmetric():
    # Mirrors the desk's real SMCI short: 0.8 risk/share wants 125 sh, 20% cap → 64 sh.
    idea = {"ticker": "SMCI", "side": "short", "entry": 31.10, "stop": 31.90, "target": 27.50}
    res = risk_gate.evaluate(idea, FLAT, RULES, SAFE_CTX)
    assert res["verdict"] == "APPROVED (reduced size)"
    assert res["size"]["shares"] == math.floor(2000 / 31.10) == 64
    assert res["size"]["reward_to_risk"] == pytest.approx(4.5, abs=0.01)
