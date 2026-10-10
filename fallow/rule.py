"""The rule: which fields to plant this week, and how much of each."""
import math
import statistics
from dataclasses import dataclass

from . import CRYPTO


@dataclass(frozen=True)
class Rule:
    lookbacks: tuple = (21, 63, 126, 252)  # days
    vol_window: int = 60                   # days
    vol_budget: float = 0.15               # annual, shared equally by the fields
    max_exposure: float = 1.0              # no leverage
    vol_floor: float = 0.03
    use_trend: bool = True
    one_field: bool = False                # ablation: put everything in the single strongest field

    @property
    def warmup(self):
        return max(max(self.lookbacks), self.vol_window) + 1


def trend_score(prices, i, lookbacks):
    """Share of lookbacks over which the price has risen, as of day i."""
    return sum(1 for n in lookbacks if prices[i] > prices[i - n]) / len(lookbacks)


def annual_vol(prices, i, window, symbol):
    """Volatility over the last `window` days, ignoring days the market was shut."""
    rets = [prices[k] / prices[k - 1] - 1 for k in range(i - window + 1, i + 1)]
    moved = [r for r in rets if r != 0.0]
    if len(moved) < 2:
        return None
    return statistics.pstdev(moved) * math.sqrt(365 if symbol in CRYPTO else 252)


def strongest(prices, i, rule):
    """Ablation. All of the account in the one field with the best trend score, or USDT if none is rising.

    Ties go to the field that has gained most over the longest lookback.
    """
    best, best_key = None, (0, 0.0)
    for s in prices:
        score = trend_score(prices[s], i, rule.lookbacks)
        gain = prices[s][i] / prices[s][i - max(rule.lookbacks)] - 1
        if score > 0 and (score, gain) > best_key:
            best, best_key = s, (score, gain)
    return {s: (rule.max_exposure if s == best else 0.0) for s in prices}


def weights(prices, i, rule=Rule()):
    """Target weight per field using prices up to and including day i.

    Each field gets an equal slice of the volatility budget, scaled by its
    trend score. Whatever is left sits in USDT. If the fields together ask for
    more than max_exposure they are scaled down in proportion.
    """
    if rule.one_field:
        return strongest(prices, i, rule)
    fields = list(prices)
    out = {}
    for s in fields:
        score = trend_score(prices[s], i, rule.lookbacks) if rule.use_trend else 1.0
        vol = annual_vol(prices[s], i, rule.vol_window, s)
        if vol is None or score == 0:
            out[s] = 0.0
            continue
        out[s] = score * (rule.vol_budget / len(fields)) / max(vol, rule.vol_floor)
    total = sum(out.values())
    if total > rule.max_exposure:
        out = {s: w * rule.max_exposure / total for s, w in out.items()}
    return out
