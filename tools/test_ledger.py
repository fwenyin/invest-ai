"""Tests for the forward decision ledger's pure scoring/reporting logic.

No I/O — exercises score_entry / report directly.
Run:  .venv/bin/python -m pytest tools/test_ledger.py -q
"""
from __future__ import annotations

import pytest

import ledger


def _rec(side="long", entry=100.0, stop=95.0, target=115.0):
    return {"ticker": "X", "side": side, "entry": entry, "stop": stop, "target": target}


def test_long_winner_realized_r_and_hit_target():
    out = ledger.score_entry(_rec(), exit_price=115.0)  # +15 / 5 risk = 3R
    assert out["realized_r"] == pytest.approx(3.0)
    assert out["result"] == "win"
    assert out["hit"] == "target"


def test_long_loser_hits_stop():
    out = ledger.score_entry(_rec(), exit_price=95.0)  # -5 / 5 = -1R
    assert out["realized_r"] == pytest.approx(-1.0)
    assert out["result"] == "loss"
    assert out["hit"] == "stop"


def test_short_winner_is_sign_correct():
    out = ledger.score_entry(_rec(side="short", entry=31.1, stop=31.9, target=27.5), exit_price=27.5)
    # short: (entry-exit)/risk = (31.1-27.5)/0.8 = 4.5R
    assert out["realized_r"] == pytest.approx(4.5, abs=0.01)
    assert out["result"] == "win"
    assert out["hit"] == "target"


def test_scratch_band_near_entry():
    out = ledger.score_entry(_rec(), exit_price=100.1)  # ~0.02R
    assert out["result"] == "scratch"


def test_report_counts_only_scored_and_flags_small_sample():
    entries = [
        {"session": "premarket", "outcome": {"realized_r": 3.0}},
        {"session": "premarket", "outcome": {"realized_r": -1.0}},
        {"session": "open", "status": "open", "outcome": None},
    ]
    rep = ledger.report(entries)
    assert rep["total_logged"] == 3
    assert rep["scored"] == 2
    assert rep["open_unscored"] == 1
    assert rep["win_rate_pct"] == 50.0
    assert rep["avg_r"] == pytest.approx(1.0)
    assert "NOT ENOUGH" in rep["evidence_note"]


def test_report_empty_is_safe():
    rep = ledger.report([])
    assert rep["scored"] == 0
    assert rep["win_rate_pct"] == 0.0
