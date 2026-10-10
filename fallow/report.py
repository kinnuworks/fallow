"""Rebuild every number in the write-up and the site from the cached candles."""
import itertools
import json
import os
import statistics
import time

from . import FIELDS, NINE_FIELDS, NAMES, HOLDOUT_START, RTOKEN_LISTING
from . import data
from .backtest import Costs, equity, index_of, rolling_sharpe, run, summary, weekday
from .rule import Rule, weights

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "reports")


def iso(ms):
    return time.strftime("%Y-%m-%d", time.gmtime(ms / 1000))


def rounded(obj, places=4):
    if isinstance(obj, float):
        return round(obj, places)
    if isinstance(obj, dict):
        return {k: rounded(v, places) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [rounded(v, places) for v in obj]
    return obj


def periods(days, prices, **kw):
    """Full period, the part the rule was written on, the held-out part, and the live rToken era."""
    cut = index_of(days, HOLDOUT_START)
    live = index_of(days, RTOKEN_LISTING)
    return {
        "full": summary(run(days, prices, **kw)),
        "in_sample": summary(run(days, prices, end=cut, **kw)),
        "held_out": summary(run(days, prices, start=cut, **kw)),
        "rtoken_era": summary(run(days, prices, start=live, **kw)),
        "last_year": summary(run(days, prices, start=len(days) - 365, **kw)),
    }


def subset(prices, fields):
    return {s: prices[s] for s in fields}


def yearly(result):
    by_year = {}
    for d, r in zip(result["dates"], result["returns"]):
        y = iso(d)[:4]
        by_year[y] = by_year.get(y, 1.0) * (1 + r)
    return {y: v - 1 for y, v in by_year.items()}


def worst_drawdowns(dates, returns, top=5):
    """Peak-to-trough falls, deepest first, with the dates they ran between."""
    curve = equity(returns)
    out, peak, peak_i, trough, trough_i = [], 1.0, -1, 1.0, -1
    for i, level in enumerate(curve):
        if level >= peak:
            if trough < peak:
                out.append({"depth": trough / peak - 1, "from": iso(dates[max(peak_i, 0)]), "to": iso(dates[trough_i])})
            peak, peak_i, trough, trough_i = level, i, level, i
        elif level < trough:
            trough, trough_i = level, i
    if trough < peak:
        out.append({"depth": trough / peak - 1, "from": iso(dates[max(peak_i, 0)]), "to": iso(dates[trough_i])})
    return sorted(out, key=lambda d: d["depth"])[:top]


def holding_periods(returns, days=365):
    """Outcome of every possible holding period of `days`: start any day, hold, look at the result."""
    level, curve = 1.0, [1.0]
    for r in returns:
        level *= 1 + r
        curve.append(level)
    outcomes = sorted(curve[i + days] / curve[i] - 1 for i in range(len(curve) - days))
    n = len(outcomes)
    return {
        "periods": n,
        "share_positive": sum(1 for x in outcomes if x > 0) / n,
        "worst": outcomes[0],
        "tenth_percentile": outcomes[n // 10],
        "median": outcomes[n // 2],
        "best": outcomes[-1],
    }


def through(dates, returns, start, end):
    """Compounded return between two ISO dates, inclusive."""
    level = 1.0
    for d, r in zip(dates, returns):
        if start <= iso(d) <= end:
            level *= 1 + r
    return level - 1


def build(reuse_grid=False):
    os.makedirs(OUT, exist_ok=True)
    days, nine = data.panel(NINE_FIELDS)
    five = subset(nine, FIELDS)
    crypto = subset(nine, FIELDS[:2])
    report = {
        "built": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
        "first_day": iso(days[0]), "last_day": iso(days[-1]),
        "holdout_start": HOLDOUT_START, "rtoken_listing": RTOKEN_LISTING,
        "fields": [{"symbol": s, "name": NAMES[s]} for s in FIELDS],
    }

    # The rule itself.
    report["fallow"] = periods(days, five)
    held = report["fallow"]["held_out"]["sharpe"]
    report["fallow"]["decay_ratio"] = held / report["fallow"]["in_sample"]["sharpe"]

    # What it is compared against.
    hold = lambda mix: dict(fixed=mix)
    report["benchmarks"] = {
        "btc_hold": periods(days, five, fixed={**{s: 0.0 for s in FIELDS}, "BTCUSDT": 1.0}),
        "btc_eth_hold": periods(days, five, fixed={**{s: 0.0 for s in FIELDS}, "BTCUSDT": 0.5, "ETHUSDT": 0.5}),
        "equal_fifths": periods(days, five, fixed={s: 0.2 for s in FIELDS}),
        "browne_static": periods(days, five, fixed={"BTCUSDT": 0.0, "ETHUSDT": 0.0, "RSPYUSDT": 0.25, "RGLDUSDT": 0.25, "RTLTUSDT": 0.25}),
    }

    # Ablations: what each piece contributes.
    report["ablations"] = {
        "crypto_only_trend": periods(days, crypto),
        "no_trend_filter": periods(days, five, rule=Rule(use_trend=False)),
        "nine_fields": periods(days, nine),
        "one_field_at_a_time": periods(days, five, rule=Rule(one_field=True)),
    }
    for s in FIELDS:
        rest = subset(five, [x for x in FIELDS if x != s])
        report["ablations"]["without_" + s] = periods(days, rest)

    # Costs.
    report["cost_sensitivity"] = {
        f"{bp}bp": periods(days, five, costs=Costs(bp / 10000)) for bp in (0, 5, 15, 30, 60)
    }

    # Parameter grid on the five fields. The default is one point in it.
    # It takes most of the run time, so `report --reuse-grid` keeps the last one.
    grid_path = os.path.join(OUT, "grid.json")
    if reuse_grid and os.path.exists(grid_path):
        grid = json.load(open(grid_path))
    else:
        grid = []
        lookback_sets = [(21, 63, 126, 252), (63, 126, 252), (21, 63, 126), (126, 252), (252,), (42, 84, 168, 252)]
        for lb, vw, vb, wd in itertools.product(lookback_sets, (20, 40, 60, 90, 120), (0.10, 0.15, 0.20, 0.30), (0, 2, 4, 6)):
            p = periods(days, five, rule=Rule(lookbacks=lb, vol_window=vw, vol_budget=vb), signal_weekday=wd)
            grid.append({"lookbacks": lb, "vol_window": vw, "vol_budget": vb, "signal_weekday": wd,
                         "full": p["full"]["sharpe"], "in_sample": p["in_sample"]["sharpe"], "held_out": p["held_out"]["sharpe"],
                         "max_drawdown": p["full"]["max_drawdown"]})
    full = sorted(g["full"] for g in grid)
    out = sorted(g["held_out"] for g in grid)
    default_full = report["fallow"]["full"]["sharpe"]
    report["grid"] = {
        "variants": len(grid),
        "full_sharpe": {"min": full[0], "median": statistics.median(full), "max": full[-1]},
        "held_out_sharpe": {"min": out[0], "median": statistics.median(out), "max": out[-1]},
        "default_percentile_full": sum(1 for x in full if x <= default_full) / len(full),
        "default_percentile_held_out": sum(1 for x in out if x <= held) / len(out),
        "share_held_out_above_half_of_in_sample": sum(1 for g in grid if g["held_out"] > 0.5 * g["in_sample"]) / len(grid),
    }

    # Curves for the charts.
    main = run(days, five)
    btc = run(days, five, fixed={**{s: 0.0 for s in FIELDS}, "BTCUSDT": 1.0})
    report["yearly"] = {"fallow": yearly(main), "btc_hold": yearly(btc)}
    report["worst_drawdowns"] = {"fallow": worst_drawdowns(main["dates"], main["returns"]),
                                 "btc_hold": worst_drawdowns(btc["dates"], btc["returns"])}
    roll = rolling_sharpe(main["returns"])
    curves = {
        "dates": [iso(d) for d in main["dates"]],
        "fallow": equity(main["returns"]), "btc_hold": equity(btc["returns"]),
        "exposure": main["exposure"],
        "rolling30": [None] * 29 + roll,
        "weights": [{"date": iso(d), **w} for d, w in main["log"]],
    }

    # Start on any day and hold a year: how often did that work out?
    report["one_year_holds"] = {"fallow": holding_periods(main["returns"]), "btc_hold": holding_periods(btc["returns"])}

    # Bitcoin's five deepest falls, and what Fallow did between the same dates.
    report["storms"] = [
        {**d, "btc": d["depth"], "fallow": through(main["dates"], main["returns"], d["from"], d["to"])}
        for d in report["worst_drawdowns"]["btc_hold"]
    ]

    # The risk dial: the same rule at other volatility budgets.
    last = len(days) - 1
    report["dial"] = {}
    for pct in (5, 10, 15, 20, 25, 30):
        rule = Rule(vol_budget=pct / 100)
        m = summary(run(days, five, rule=rule))
        w = weights(five, last, rule)
        report["dial"][str(pct)] = {
            "weights": w, "usdt": 1 - sum(w.values()),
            "sharpe": m["sharpe"], "max_drawdown": m["max_drawdown"], "cagr": m["cagr"], "avg_exposure": m["avg_exposure"],
        }

    # This week's plan. It is set on the latest bar that opened on a Sunday, which closes at midday on Monday in
    # New York, and it is dated by that Monday to match the backtest's log.
    signal = next(i for i in range(last, 0, -1) if weekday(days[i]) == 6)
    plan = weights(five, signal)
    report["plan"] = {
        "as_of": iso(days[signal] + 86_400_000),
        "weights": plan,
        "usdt": 1 - sum(plan.values()),
        "trend": {s: sum(1 for n in Rule().lookbacks if five[s][signal] > five[s][signal - n]) for s in FIELDS},
    }

    with open(os.path.join(OUT, "report.json"), "w") as f:
        json.dump(rounded(report), f, indent=1)
    with open(os.path.join(OUT, "curves.json"), "w") as f:
        json.dump(rounded(curves, 5), f)
    with open(os.path.join(OUT, "grid.json"), "w") as f:
        json.dump(rounded(grid), f)
    return report


def publish():
    """Copy what the site needs from reports/ into site/data/, thinned to weekly points."""
    site = os.path.join(ROOT, "site", "data")
    os.makedirs(site, exist_ok=True)
    report = json.load(open(os.path.join(OUT, "report.json")))
    curves = json.load(open(os.path.join(OUT, "curves.json")))
    grid = json.load(open(os.path.join(OUT, "grid.json")))
    keep = [i for i in range(len(curves["dates"])) if i % 3 == 0 or i == len(curves["dates"]) - 1]
    slim = {k: [curves[k][i] for i in keep] for k in ("dates", "fallow", "btc_hold")}
    slim["weights"] = curves["weights"]
    payload = {"report": report, "curves": slim, "grid_held_out": sorted(g["held_out"] for g in grid)}
    with open(os.path.join(site, "fallow.json"), "w") as f:
        json.dump(payload, f, separators=(",", ":"))
    print("wrote site/data/fallow.json")


def show(report):
    def row(label, p, key="full"):
        m = p[key]
        print(f"{label:34} Sharpe {m['sharpe']:5.2f}  Sortino {m['sortino']:5.2f}  maxDD {m['max_drawdown']*100:6.1f}%  "
              f"CAGR {m['cagr']*100:6.1f}%  turnover {m['turnover_per_year']:4.1f}x")
    print(f"Data {report['first_day']} to {report['last_day']}\n")
    for key in ("full", "in_sample", "held_out", "rtoken_era", "last_year"):
        print(key)
        row("  Fallow", report["fallow"], key)
        row("  BTC buy and hold", report["benchmarks"]["btc_hold"], key)
        row("  Crypto-only trend rule", report["ablations"]["crypto_only_trend"], key)
        row("  Nine fields", report["ablations"]["nine_fields"], key)
        row("  One field at a time", report["ablations"]["one_field_at_a_time"], key)
    f = report["fallow"]
    print(f"\nHeld-out / in-sample Sharpe: {f['decay_ratio']:.2f}")
    print(f"Sharpe standard error, held out: {f['held_out']['sharpe_stderr']:.2f}")
    print(f"Rolling 30-day Sharpe above zero: {f['full']['rolling30_share_positive']*100:.0f}% of windows, "
          f"median {f['full']['rolling30_median']:.2f}, worst {f['full']['rolling30_min']:.2f}")
    g = report["grid"]
    print(f"Grid of {g['variants']} variants: held-out Sharpe {g['held_out_sharpe']['min']:.2f} to "
          f"{g['held_out_sharpe']['max']:.2f}, median {g['held_out_sharpe']['median']:.2f}; "
          f"the default sits at the {g['default_percentile_held_out']*100:.0f}th percentile")
    h = report["one_year_holds"]
    print(f"Any one-year hold: Fallow ended up in {h['fallow']['share_positive']*100:.0f}% of {h['fallow']['periods']} periods "
          f"(worst {h['fallow']['worst']*100:.1f}%); bitcoin {h['btc_hold']['share_positive']*100:.0f}% (worst {h['btc_hold']['worst']*100:.1f}%)")
    for st in report["storms"]:
        print(f"  storm {st['from']} to {st['to']}: bitcoin {st['btc']*100:6.1f}%  Fallow {st['fallow']*100:6.1f}%")
    print("\nThis week:", {k: round(v, 3) for k, v in report["plan"]["weights"].items()}, "USDT", round(report["plan"]["usdt"], 3))
