"""Run with: python3 -m unittest discover tests"""
import math
import unittest

from fallow.backtest import Costs, max_drawdown, run, sharpe
from fallow.rule import Rule, annual_vol, trend_score, weights

DAY = 86_400_000
SUNDAY = 1_704_038_400_000 - 0  # 2023-12-31 16:00 UTC is a Sunday


def calendar(n):
    return [SUNDAY + i * DAY for i in range(n)]


def rising(n, step=0.001, start=100.0):
    return [start * (1 + step) ** i for i in range(n)]


def wobble(n, drift, amp=0.01, start=100.0):
    """A path with a steady drift and an alternating daily wobble, so volatility is not zero."""
    out, p = [], start
    for i in range(n):
        p *= 1 + drift + (amp if i % 2 else -amp)
        out.append(p)
    return out


class TrendScore(unittest.TestCase):
    def test_rising_price_scores_one(self):
        self.assertEqual(trend_score(rising(300), 299, (21, 63, 126, 252)), 1.0)

    def test_falling_price_scores_zero(self):
        self.assertEqual(trend_score(rising(300, -0.001), 299, (21, 63, 126, 252)), 0.0)

    def test_mixed_lookbacks_score_a_fraction(self):
        prices = rising(280) + rising(20, -0.01, start=rising(280)[-1])
        self.assertEqual(trend_score(prices, 299, (10, 252)), 0.5)


class Weights(unittest.TestCase):
    def setUp(self):
        self.prices = {"BTCUSDT": wobble(400, 0.002, 0.03), "RSPYUSDT": wobble(400, 0.0005, 0.005),
                       "RTLTUSDT": wobble(400, -0.001, 0.005)}

    def test_falling_field_is_left_fallow(self):
        self.assertEqual(weights(self.prices, 399)["RTLTUSDT"], 0.0)

    def test_exposure_never_exceeds_the_cap(self):
        w = weights(self.prices, 399, Rule(vol_budget=5.0))
        self.assertAlmostEqual(sum(w.values()), 1.0)

    def test_quieter_field_gets_the_larger_weight(self):
        w = weights(self.prices, 399)
        self.assertGreater(w["RSPYUSDT"], w["BTCUSDT"])

    def test_weights_ignore_the_future(self):
        before = weights(self.prices, 300)
        changed = {s: p[:301] + [x * 3 for x in p[301:]] for s, p in self.prices.items()}
        self.assertEqual(before, weights(changed, 300))

    def test_closed_days_do_not_shrink_volatility(self):
        open_only = wobble(200, 0.0, 0.01)
        with_gaps = []
        for p in open_only:  # repeat every close, as a shut market does
            with_gaps += [p, p]
        a = annual_vol(open_only, 199, 60, "RSPYUSDT")
        b = annual_vol(with_gaps, 399, 120, "RSPYUSDT")
        self.assertAlmostEqual(a, b, places=6)


class Backtest(unittest.TestCase):
    def setUp(self):
        self.days = calendar(500)
        self.prices = {"BTCUSDT": wobble(500, 0.002, 0.02), "RSPYUSDT": wobble(500, 0.0005, 0.004)}

    def test_fixed_full_weight_matches_the_asset(self):
        r = run(self.days, {"BTCUSDT": self.prices["BTCUSDT"]}, fixed={"BTCUSDT": 1.0}, costs=Costs(0.0))
        start = len(self.days) - len(r["returns"])
        want = self.prices["BTCUSDT"][-1] / self.prices["BTCUSDT"][start - 1] - 1
        got = math.prod(1 + x for x in r["returns"]) - 1
        self.assertAlmostEqual(got, want, places=9)

    def test_costs_reduce_returns(self):
        free = run(self.days, self.prices, costs=Costs(0.0))
        paid = run(self.days, self.prices, costs=Costs(0.01))
        self.assertLess(sum(paid["returns"]), sum(free["returns"]))

    def test_returns_before_a_day_do_not_depend_on_later_prices(self):
        k = 420
        altered = {s: p[:k] + [x * 1.5 for x in p[k:]] for s, p in self.prices.items()}
        a = run(self.days, self.prices)
        b = run(self.days, altered)
        offset = len(self.days) - len(a["returns"])
        self.assertEqual(a["returns"][:k - offset], b["returns"][:k - offset])

    def test_weights_traded_on_a_day_use_prices_two_bars_old(self):
        k = 420
        altered = {s: p[:k] + [x * 1.5 for x in p[k:]] for s, p in self.prices.items()}
        a = {d: w for d, w in run(self.days, self.prices)["log"]}
        b = {d: w for d, w in run(self.days, altered)["log"]}
        # a trade logged on day k (index k, traded at that close) was decided on day k-1
        for d in a:
            if d <= self.days[k]:
                self.assertEqual(a[d], b[d])

    def test_rebalances_happen_weekly(self):
        r = run(self.days, self.prices)
        gaps = {(b[0] - a[0]) // DAY for a, b in zip(r["log"][1:], r["log"][2:])}
        self.assertEqual(gaps, {7})


class Metrics(unittest.TestCase):
    def test_drawdown_of_a_halving(self):
        self.assertAlmostEqual(max_drawdown([0.1, -0.5, 0.2]), -0.5)

    def test_sharpe_of_constant_returns_is_zero_by_convention(self):
        self.assertEqual(sharpe([0.01] * 50), 0.0)


if __name__ == "__main__":
    unittest.main()
