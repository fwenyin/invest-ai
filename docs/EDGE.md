# Edge hypothesis — what this desk is actually betting on

A review flagged that the desk had **no stated source of edge**: it reads free, delayed,
public data with an LLM at 08:30 ET and trades it by hand, against a market that already
priced the same headlines overnight. Until there is a specific, *falsifiable* edge thesis —
and forward evidence that it holds — no real capital should be risked. This file is the thesis
and the bar it must clear. If it can't be met, the honest answer is "no edge, don't trade."

## The hypothesis (falsifiable)

> **H1 — Intraday continuation of fresh, single-name catalysts.** When a liquid universe name
> gaps up ≥2% on a *same-session* catalyst (earnings, upgrade, deal, named headline) and holds
> green into/after the open, it continues for 1–3 days often enough that a stop-defined long has
> positive expectancy **net of costs**. The claimed edge is not information (that's priced) but
> *disciplined participation + risk sizing* in a behaviourally sticky move that retail/algos
> chase. This is the codified proxy for the discretionary intraday process — strategy
> `gap_and_go` in `backtest/strategies/`.

This is deliberately narrow and testable. It is **not** "the LLM reads news better than the
market." If you cannot state your edge this concretely, you do not have one you can verify.

## How it gets tested (two gates, both required)

1. **Historical, cross-universe (necessary, not sufficient).** A rule that only works on one
   cherry-picked ticker is curve-fit. Run it across the whole scan universe and demand breadth:
   ```bash
   .venv/bin/python backtest/engine.py --universe gap_and_go --years 5
   ```
   Bar: beats buy-&-hold on a majority of names AND passes the full verdict (edge + robust
   out-of-sample + ≥20 trades) on a meaningful share. Read `out_of_sample` vs `in_sample` — large
   decay = overfit. **Caveat (survivorship):** the universe is today's survivors; historical
   numbers are an *upper* bound (see `SURVIVORSHIP_WARNING` in `engine.py`).

2. **Forward, out-of-sample-in-time (the real test).** A historical backtest of a rule the desk
   trades is still contaminated when an LLM is in the loop: the model knows past outcomes within
   its training window (look-ahead by memory). The only clean evidence is **forward**: log every
   call *before* the outcome is known and score it later.
   ```bash
   tools/ledger.py log ...     # at decision time, in /premarket (taken AND vetoed ideas)
   tools/ledger.py score       # in /postmarket, against the actual path
   tools/ledger.py report      # running scorecard
   ```
   Bar: ≥30–50 **scored forward** calls with positive expectancy (avg R > 0 after costs) and a
   profit factor > 1.2. Backfilled/historical "what would it have said" calls **do not count**.

## Kill criteria (when to abandon the thesis)

- `--universe` shows no broad edge (curve-fit to a few names) → H1 is dead as written.
- After ~50 forward calls, expectancy ≤ 0 net of costs → stop trading it; the edge isn't real.
- The forward win/R distribution diverges sharply from the backtest → the backtest was a mirage
  (slippage, thin premarket liquidity, or hindsight); re-examine costs before continuing.

## H2 — Long-term sleeve (the more plausible edge)

> **H2 — Quality at a reasonable price, held with discipline, beats the index net of behaviour.**
> The long-term sleeve's edge is NOT "we pick better growth stocks" — quality and growth are
> crowded, well-arbitraged factors, and Bottom Up Bulletin is a published newsletter. The edge is
> *structural/behavioural*: a multi-year horizon removes the latency problem that kills the intraday
> desk; low turnover removes most costs; and temperament (holding through drawdowns, not chasing)
> beats the median investor. The stock-picking is just the entry filter — **price discipline + the
> QQQ hurdle** is the actual lever.

Why this is more defensible than H1: being a week late on a multi-year theme is irrelevant, so the
"already priced in" objection mostly dissolves. But two honest constraints:

- **It must beat QQQ, not cash.** A growth/quality pick that can't plausibly beat just owning the
  index is a WATCH, not a BUY — own the index instead. Enforced by the QQQ hurdle in the
  `valuation-analyst` and graded forward by `tools/lt_ledger.py` (every checkpoint records the pick's
  return AND QQQ's over the same window → excess).
- **Valuation is the fragile input, so it's pinned in code.** `tools/valuation.py` does the two-stage
  DCF, reverse-DCF (what growth the price implies), FCF yield, and margin-of-safety verdict. The LLM
  chooses and *defends* the inputs (sourced FCF, growth, discount, net debt, shares); it does not do
  the arithmetic — an LLM-estimated intrinsic value is the least trustworthy number in the system.

**Validation horizon (the hard part).** Long-term theses resolve over *years*, and LLM hindsight
contaminates any backtest of long-term picks worse than intraday (the model knows the run-ups). So
the only evidence is forward, and it's slow. Mitigation: grade the **thesis**, not just the price —
each pick logs the leading indicators it rides on (revenue growth, margins, ROIC) with a baseline and
target; weekly `lt_ledger.py checkpoint` updates them, giving feedback in quarters. Kill a pick when
it lags QQQ AND its key assumption breaks. Over a full cycle, if the basket can't beat QQQ on
average, the honest answer is to just own QQQ.

This is likely the **primary** sleeve (more plausible edge, lower cost); the intraday desk is the
experiment to paper-trade.

## Why the rest of the system exists

The risk gate (`tools/risk_gate.py`) and ledger (`tools/ledger.py`) are what make this honest:
the gate enforces that a losing streak can't blow up the account while the thesis is being
proven; the ledger is what *proves or kills* the thesis. Sophisticated risk plumbing on top of an
unproven edge just loses money slowly — so the ledger comes first. Paper-trade until both gates
above are cleared.

*Not financial advice. Base rate: most backtested strategies lose money live once costs, bias, and
regime shifts are accounted for — hold this thesis to that standard.*
