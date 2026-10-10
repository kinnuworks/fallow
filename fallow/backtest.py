"""Backtest engine and the metrics the hackathon scores on."""
import calendar
import math
import statistics
import time
from dataclasses import dataclass

from .rule import Rule, weights

YEAR = 365  # the portfolio is marked every calendar day


@dataclass(frozen=True)
class Costs:
    per_turnover: float = 0.0015  # 15 bp per unit traded: taker fee plus spread
    no_trade_band: float = 0.0    # leave a field alone if its weight is within this of target


def weekday(ms):
    return time.gmtime(ms / 1000).tm_wday


def run(days, prices, rule=Rule(), costs=Costs(), signal_weekday=6, start=None, end=None, fixed=None):
    """Daily returns of the rule between day indexes [start, end).

    Timing: the signal uses the close of a bar that opened on `signal_weekday`
    (6 = the bar from Sunday 16:00 UTC to Monday 16:00 UTC). The trade happens
    one bar later, at the next close. Nothing earned on day i uses a price from
    day i-1 or later to decide.

    `fixed` holds a static mix that is rebalanced on the same schedule.
    """
    fields = list(prices)
    start = max(start or 0, rule.warmup + 2)
    end = end or len(days)
    held = {s: 0.0 for s in fields}  # weights at the start of each day, drifted
    rets, dates, turnover, exposure, log = [], [], 0.0, [], []
    for i in range(start, end):
        target = None
        if weekday(days[i - 2]) == signal_weekday or i == start:
            target = dict(fixed) if fixed else weights(prices, i - 2, rule)
        cost = 0.0
        if target is not None:
            if costs.no_trade_band:
                # Small drifts are not worth a trade. A field being rested is always sold in full.
                target = {s: (target[s] if abs(target[s] - held[s]) > costs.no_trade_band or target[s] == 0 else held[s])
                          for s in fields}
            traded = sum(abs(target[s] - held[s]) for s in fields)
            cost = traded * costs.per_turnover
            turnover += traded
            held = target
            log.append((days[i - 1], dict(target)))
        day_ret = {s: prices[s][i] / prices[s][i - 1] - 1 for s in fields}
        gross = sum(held[s] * day_ret[s] for s in fields)
        net = gross - cost
        rets.append(net)
        dates.append(days[i])
        exposure.append(sum(held.values()))
        # let the weights drift with prices until the next rebalance
        grown = 1 + gross
        held = {s: held[s] * (1 + day_ret[s]) / grown for s in fields}
    return {"dates": dates, "returns": rets, "turnover": turnover, "exposure": exposure, "log": log}


def equity(returns):
    curve, level = [], 1.0
    for r in returns:
        level *= 1 + r
        curve.append(level)
    return curve


def max_drawdown(returns):
    peak, level, worst = 1.0, 1.0, 0.0
    for r in returns:
        level *= 1 + r
        peak = max(peak, level)
        worst = min(worst, level / peak - 1)
    return worst


def sharpe(returns):
    sd = statistics.pstdev(returns)
    return statistics.mean(returns) / sd * math.sqrt(YEAR) if sd else 0.0


def sortino(returns):
    downside = math.sqrt(sum(min(r, 0.0) ** 2 for r in returns) / len(returns))
    return statistics.mean(returns) / downside * math.sqrt(YEAR) if downside else 0.0


def sharpe_stderr(returns):
    """Lo (2002) standard error of an annualised Sharpe, assuming iid returns."""
    daily = sharpe(returns) / math.sqrt(YEAR)
    return math.sqrt((1 + 0.5 * daily ** 2) / len(returns)) * math.sqrt(YEAR)


def rolling_sharpe(returns, window=30, step=1):
    out = []
    for j in range(window, len(returns) + 1, step):
        chunk = returns[j - window:j]
        sd = statistics.pstdev(chunk)
        if sd:
            out.append(statistics.mean(chunk) / sd * math.sqrt(YEAR))
    return out


def summary(result):
    r = result["returns"]
    years = len(r) / YEAR
    roll = rolling_sharpe(r)
    return {
        "days": len(r),
        "years": round(years, 2),
        "total_return": equity(r)[-1] - 1,
        "cagr": equity(r)[-1] ** (1 / years) - 1,
        "sharpe": sharpe(r),
        "sharpe_stderr": sharpe_stderr(r),
        "sortino": sortino(r),
        "max_drawdown": max_drawdown(r),
        "turnover_per_year": result["turnover"] / years,
        "avg_exposure": statistics.mean(result["exposure"]),
        "rolling30_share_positive": sum(1 for x in roll if x > 0) / len(roll) if roll else None,
        "rolling30_median": statistics.median(roll) if roll else None,
        "rolling30_min": min(roll) if roll else None,
    }


def index_of(days, date):
    """First day index on or after an ISO date."""
    ms = calendar.timegm(time.strptime(date, "%Y-%m-%d")) * 1000
    return next((i for i, d in enumerate(days) if d >= ms), len(days))
