"""This week's plan on its own, without rebuilding the whole report."""
import time

from . import FIELDS, NAMES, data
from .backtest import weekday
from .rule import Rule, weights

DAY_MS = 86_400_000


def current(swing_budget=0.15, refresh=False):
    """Weights from the latest weekly signal bar: the one that opens Sunday 16:00 UTC and closes at midday on Monday in New York."""
    if refresh:
        data.refresh(FIELDS)
    days, prices = data.panel(FIELDS)
    rule = Rule(vol_budget=swing_budget)
    signal = next(i for i in range(len(days) - 1, 0, -1) if weekday(days[i]) == 6)
    w = weights(prices, signal, rule)
    return {
        "week_of": time.strftime("%Y-%m-%d", time.gmtime((days[signal] + DAY_MS) / 1000)),
        "swing_budget": swing_budget,
        "hold": [
            {"symbol": s, "name": NAMES[s], "weight": round(w[s], 4),
             "trend": sum(1 for n in rule.lookbacks if prices[s][signal] > prices[s][signal - n])}
            for s in FIELDS
        ],
        "usdt": round(1 - sum(w.values()), 4),
        "market": "spot",
        "note": "Weights are shares of the account to hold. Trade while New York is open. This is not advice.",
    }
