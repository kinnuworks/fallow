# Fallow

A weekly rotation across five things you can hold on Bitget: bitcoin, ether, the S&P 500, gold and long Treasuries. Each week it plants the fields that are trending and rests the others in USDT.

Live page: https://kinnuworks.github.io/fallow/

Bitget AI Base Camp Hackathon, Season 2. Track: Alpha Factory. Sub-theme: Cross-Asset Allocation / Rotation.

## Results

Bitget daily candles, April 2019 to October 2026, after 15 bp costs. All figures are observed backtest results.

| | Sharpe | Sortino | Worst fall | Yearly growth | Turnover a year |
|---|---|---|---|---|---|
| Fallow, whole period (7.5 years) | 1.39 | 2.02 | −10.2% | 9.9% | 6.4× |
| Fallow, written on (to December 2023) | 1.46 | 2.13 | −10.2% | 10.4% | 6.3× |
| Fallow, held back (January 2024 on, 2.8 years) | 1.26 | 1.81 | −5.4% | 8.9% | 6.8× |
| Holding bitcoin, whole period | 0.93 | 1.37 | −76.4% | 45.2% | |
| Holding bitcoin, held back | 0.77 | 1.12 | −53.3% | 27.0% | |

The held-back Sharpe is 0.86 of the earlier one. The handbook's warning line is 0.5.

Rolling 30-day Sharpe is above zero in 61% of windows, with a median of 1.14.

## Read this before you believe it

- Since rTokens went live on 2 June 2026, Fallow is down 1.1% over 129 days (Sharpe −0.56). Bitcoin rose 23% in that time. This is the only stretch that used real rToken prices.
- Over the most recent 365 days Fallow is down 4.1%, with a Sharpe of −0.65. A one-year backtest would make it look bad. Holding bitcoin lost 32% over the same year.
- Take gold out and the held-back Sharpe falls from 1.26 to 0.48.
- A static mix of a quarter each in the S&P 500, gold, Treasuries and cash, with no crypto and no trend filter, scored 1.21 on the held-back years. Over the whole period it scored 0.82. The trend filter earned its keep in 2022 and added little after 2024.
- Putting everything in the single strongest field each week grows faster (42% a year) and falls 71% at its worst, for a Sharpe of 0.96. Sharing the risk across five fields is what keeps the worst fall near 10%.
- A nine-field version (adding developed and emerging shares, mid Treasuries and oil) scores 1.00 over the whole period and 0.89 held back. The five fields were fixed in advance, and they flatter the result.
- At 30 bp costs the held-back Sharpe is 1.11. At 60 bp it is 0.82.
- The held-back Sharpe has a standard error of 0.60.
- Average exposure is 52%, so Fallow trails bitcoin badly in a bull run.
- The worst dry spell ran from November 2021 to September 2023.
- Order book depth in New York hours has not been measured. A Friday after-hours reading on 9 October 2026 showed the Treasury rToken costing 20 bp for a 10,000 USDT buy, and the gold rToken's book empty. See `reports/book_snapshots.jsonl`.

## The rule

1. For each field, count how many of four lookbacks (21, 63, 126 and 252 days) show a higher price today. That count out of four is the trend score.
2. Give each field one fifth of a 15% yearly volatility budget, scaled by its trend score and divided by its own 60-day volatility.
3. If the five weights add to more than 100%, scale them down together. Whatever is left sits in USDT. No leverage and no shorts.
4. Do this once a week on the daily bar that opens Sunday 16:00 UTC and closes at midday on Monday in New York. Trade at the close of the next bar.

The five fields are Harry Browne's permanent portfolio (stocks, long bonds, gold, cash) with bitcoin and ether added. The lookbacks, the volatility window and the budget are common textbook values. None was fitted. Across 480 variants of these settings the held-back Sharpe ranges from 1.02 to 1.56, and the version here sits at the 27th percentile.

The rule is in [`fallow/rule.py`](fallow/rule.py), about 60 lines.

## Run it

Python 3.9 or later. No packages to install and no API key.

```bash
python3 -m fallow fetch     # daily candles from Bitget's public API into data/
python3 -m fallow report    # every number above, written to reports/ (about 4 minutes)
python3 -m fallow report --reuse-grid   # the same, keeping the last parameter grid (about 2 minutes)
python3 -m fallow plan --fresh          # this week's weights from today's candles
python3 -m fallow plan --json           # the same, for an agent or a script
python3 -m fallow site      # refresh the site's data file
python3 -m unittest discover tests
```

To see the site locally:

```bash
python3 -m http.server 8765 --directory site
```

## The site

The page works the plan out again in your browser each time it loads, from Bitget's public candle API. It then reads Bitget's public order books and prices the trades for whatever account size you type in. If Bitget does not answer, it falls back to the plan it shipped with and says so.

- **This week's planting** shows the five fields and their weights.
- **Your Monday list** turns an account size, a risk setting and what you already hold into the trades to make, with the cost of each at that moment.
- **Seven years of planting** is every weekly plan since 2019 in one picture.

## What is here

| Path | Contents |
|---|---|
| `fallow/rule.py` | Trend score, volatility, weights |
| `fallow/backtest.py` | Engine, costs, Sharpe, Sortino, drawdown, rolling Sharpe |
| `fallow/report.py` | Periods, benchmarks, ablations, cost sensitivity, the 480-variant grid |
| `fallow/data.py` | Candle download and cache |
| `tests/` | 15 tests, including two that check the rule cannot see the future |
| `data/` | The candles the results were built from |
| `reports/` | `report.json`, `curves.json`, `grid.json`, order book snapshots |
| `fallow/plan.py` | This week's plan on its own, for the command line |
| `site/` | The field book page. `live.js` is the rule again in JavaScript, checked against the Python weights |
| `skill/SKILL.md` | Instructions for an AI agent to read the plan and prepare trades for the user to confirm |
| `playbook/fallow-field-book/` | The same rule as a Bitget Playbook basket. Passes the GetAgent validator and matches the research weights |
| `tools/book_snapshot.py` | Order book depth reading for the five fields |
| `SUBMISSION.md` | The hackathon project description |

## About the data

- Bitcoin and ether are Bitget spot candles from July 2018.
- rToken spot pairs listed on 2 June 2026. Bitget's candle endpoint returns earlier bars for the same symbols. Those are the underlying fund's price, and they leave out dividends, which understates the stock and bond fields.
- Daily bars open at 16:00 UTC, which is midday in New York. A day when New York is shut carries the last price forward, and those days are left out of the volatility estimate.
- USDT earns nothing.
- The first 253 days are warm-up, so results start in April 2019.

## Licence

MIT. This is research, and it is not financial advice.
