"""Self-contained backtest engine (pandas/numpy only — no vectorbt/numba).

Validates a strategy's edge BEFORE you trade it. Long-only, one position at a
time, next-bar fills with fees + slippage. Point-in-time: strategy signals use
shift(1) lookbacks and positions are shifted one bar, so there is no look-ahead.
A 70/30 walk-forward split exposes overfitting.

CLI:
    python backtest/engine.py SPY ma_cross
    python backtest/engine.py AAPL rsi_meanrev --years 5 --fees 0.0005 --slippage 0.0005
    python backtest/engine.py --list
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "backtest" / "results"
RESULTS.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "backtest"))

import strategies  # noqa: E402

TRADING_DAYS = 252


def _load_prices(ticker: str, years: int) -> pd.DataFrame:
    import yfinance as yf

    df = yf.Ticker(ticker).history(period=f"{years}y", interval="1d", auto_adjust=False)
    if df is None or df.empty:
        raise ValueError(f"no price data for {ticker}")
    return df


def _positions(entries: pd.Series, exits: pd.Series) -> pd.Series:
    """Long-only state machine: enter on entry when flat, exit on exit when long."""
    pos = np.zeros(len(entries), dtype=float)
    holding = 0.0
    e = entries.to_numpy()
    x = exits.to_numpy()
    for i in range(len(e)):
        if holding == 0.0 and e[i]:
            holding = 1.0
        elif holding == 1.0 and x[i]:
            holding = 0.0
        pos[i] = holding
    return pd.Series(pos, index=entries.index)


def _trades(close: pd.Series, pos: pd.Series, cost: float) -> list[float]:
    """Per-trade net returns from position transitions (for win rate / profit factor)."""
    changes = pos.diff().fillna(pos.iloc[0])
    entry_idx = list(pos.index[changes == 1.0])
    exit_idx = list(pos.index[changes == -1.0])
    if len(exit_idx) < len(entry_idx):  # still open at the end → close on last bar
        exit_idx.append(pos.index[-1])
    rets = []
    for en, ex in zip(entry_idx, exit_idx):
        gross = close.loc[ex] / close.loc[en] - 1
        rets.append(gross - 2 * cost)  # entry + exit cost
    return rets


def _simulate(close: pd.Series, entries: pd.Series, exits: pd.Series,
              fees: float, slippage: float, init_cash: float) -> dict:
    cost = fees + slippage
    pos = _positions(entries, exits)
    daily_ret = close.pct_change().fillna(0.0)
    gross = daily_ret * pos.shift(1).fillna(0.0)          # act next bar (no look-ahead)
    turnover = pos.diff().abs().fillna(0.0)               # 1 on each entry/exit
    net = gross - turnover * cost
    equity = (1 + net).cumprod() * init_cash

    trades = _trades(close, pos, cost)
    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t <= 0]
    downside = net[net < 0]

    def safe(x, d=0.0):
        return float(x) if np.isfinite(x) else d

    sharpe = safe(net.mean() / net.std() * np.sqrt(TRADING_DAYS)) if net.std() else 0.0
    sortino = (safe(net.mean() / downside.std() * np.sqrt(TRADING_DAYS))
               if len(downside) and downside.std() else 0.0)
    max_dd = safe((equity / equity.cummax() - 1).min()) * 100
    pf = safe(sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else (
        float("inf") if wins else 0.0)

    return {
        "stats": {
            "total_return_pct": round(safe(equity.iloc[-1] / init_cash - 1) * 100, 2),
            "sharpe": round(sharpe, 2),
            "sortino": round(sortino, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "win_rate_pct": round(100 * len(wins) / len(trades), 2) if trades else 0.0,
            "profit_factor": round(pf, 2) if np.isfinite(pf) else 999.0,
            "num_trades": len(trades),
            "avg_trade_pct": round(100 * np.mean(trades), 2) if trades else 0.0,
        },
        "equity": equity,
    }


def run(ticker: str, strategy: str, years: int = 5, fees: float = 0.0005,
        slippage: float = 0.0005, cash: float = 10000, tearsheet: bool = False) -> dict:
    strat = strategies.get(strategy)
    df = _load_prices(ticker, years)
    entries, exits = strat.signals(df)
    close = df["Close"]
    split = int(len(df) * 0.7)

    full = _simulate(close, entries, exits, fees, slippage, cash)
    is_ = _simulate(close.iloc[:split], entries.iloc[:split], exits.iloc[:split], fees, slippage, cash)
    oos = _simulate(close.iloc[split:], entries.iloc[split:], exits.iloc[split:], fees, slippage, cash)
    bh = round(float((close.iloc[-1] / close.iloc[0] - 1) * 100), 2)

    result = {
        "ticker": ticker.upper(),
        "strategy": strategy,
        "description": strat.DESCRIPTION,
        "params": {"years": years, "fees": fees, "slippage": slippage, "cash": cash},
        "full_period": full["stats"],
        "in_sample": is_["stats"],
        "out_of_sample": oos["stats"],
        "buy_hold_return_pct": bh,
        "verdict": _verdict(full["stats"], oos["stats"], bh),
    }

    out_path = RESULTS / f"{ticker.upper()}_{strategy}.json"
    out_path.write_text(json.dumps(result, indent=2))
    result["saved_to"] = str(out_path)

    if tearsheet:
        try:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(10, 5))
            full["equity"].plot(ax=ax, label=f"{strategy}")
            (close / close.iloc[0] * cash).plot(ax=ax, label="buy & hold", alpha=0.6)
            ax.set_title(f"{ticker.upper()} — {strategy}  (equity curve)")
            ax.legend()
            ax.grid(alpha=0.3)
            png = RESULTS / f"{ticker.upper()}_{strategy}_equity.png"
            fig.savefig(png, dpi=110, bbox_inches="tight")
            plt.close(fig)
            result["chart"] = str(png)
        except Exception as e:
            result["chart_error"] = str(e)

    return result


def _verdict(full: dict, oos: dict, bh: float) -> str:
    reasons = []
    edge = full["total_return_pct"] > bh
    robust = oos["sharpe"] > 0.5 and oos["profit_factor"] > 1.1
    enough = full["num_trades"] >= 20
    if not enough:
        reasons.append("too few trades to trust (<20)")
    if not edge:
        reasons.append("underperforms buy & hold")
    if not robust:
        reasons.append("weak out-of-sample (likely overfit)")
    if edge and robust and enough:
        return "TRADEABLE EDGE: beats B&H, holds out-of-sample, enough trades."
    return "NOT VALIDATED — " + "; ".join(reasons)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("ticker", nargs="?")
    p.add_argument("strategy", nargs="?")
    p.add_argument("--years", type=int, default=5)
    p.add_argument("--fees", type=float, default=0.0005)
    p.add_argument("--slippage", type=float, default=0.0005)
    p.add_argument("--cash", type=float, default=10000)
    p.add_argument("--tearsheet", action="store_true")
    p.add_argument("--list", action="store_true")
    a = p.parse_args()

    if a.list or not a.ticker:
        print(json.dumps({n: m.DESCRIPTION for n, m in strategies.REGISTRY.items()}, indent=2))
        sys.exit(0)
    print(json.dumps(run(a.ticker, a.strategy or "ma_cross", a.years, a.fees,
                         a.slippage, a.cash, a.tearsheet), indent=2))
