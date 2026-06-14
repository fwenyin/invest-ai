"""Strategy registry. Each strategy module exposes:

    NAME: str
    DESCRIPTION: str
    def signals(df) -> (entries: pd.Series[bool], exits: pd.Series[bool])

Register new strategies by importing them and adding to REGISTRY.
"""
from . import breakout, gap_and_go, ma_cross, rsi_meanrev

REGISTRY = {
    ma_cross.NAME: ma_cross,
    rsi_meanrev.NAME: rsi_meanrev,
    breakout.NAME: breakout,
    gap_and_go.NAME: gap_and_go,
}


def get(name: str):
    if name not in REGISTRY:
        raise KeyError(f"unknown strategy '{name}'. Available: {', '.join(REGISTRY)}")
    return REGISTRY[name]
