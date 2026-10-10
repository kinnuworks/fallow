# Fallow: submission text

Everything below is ready to paste into the Google Form. Items in [square brackets] are yours to fill in.

## Form fields

| Field | Value |
|---|---|
| Project name | Fallow |
| Track | Alpha Factory |
| Sub-theme | Cross-Asset Allocation / Rotation |
| Submission materials link | Code: https://github.com/kinnuworks/fallow · Site: https://kinnuworks.github.io/fallow/ |
| X promotional post link | [your post URL] |
| University name | [full official name] |
| Apply for Demo Day | Yes |
| Apply for K3 Token Subsidy | Yes |
| Open to Playbook review and listing discussion | Yes |

## Project description

### 1. Thesis

Since June 2026 a Bitget user can hold the S&P 500, gold and long Treasuries as rTokens in the same account as bitcoin and ether. Before that, a crypto holder who wanted out of crypto had one place to go on the exchange, which was USDT. Fallow asks what the extra fields are worth.

The signal is price trend. For each of five fields (BTCUSDT, ETHUSDT, RSPYUSDT, RGLDUSDT, RTLTUSDT) the rule counts how many of four lookbacks, 21, 63, 126 and 252 days, show a higher price today. That count out of four is the field's trend score.

The decision is a risk budget. Each field gets one fifth of a 15% yearly volatility budget, scaled by its trend score and divided by its own 60-day volatility. A field that has fallen over all four lookbacks gets nothing. Whatever is not planted sits in USDT.

The risk controls are structural. Total exposure is capped at 100%, so there is no leverage. There are no shorts. Volatile fields get small weights by construction, which is why bitcoin rarely exceeds 10% of the account. The rule trades once a week, one daily bar after its signal, at midday New York time when the underlying markets are open.

Fallow holds spot only. It uses no perpetual contracts, so there is no leverage, no funding and nothing to liquidate. We looked through all 2,261 Playbooks listed on GetAgent Studio on 10 October 2026 (observed). None combines BTC or ETH with an rToken for the S&P 500, gold or Treasuries. Only two hold a Treasury rToken at all, and neither has placed a trade. The cross-asset rotation Playbooks we found there trade perpetuals, and several hold no US stocks.

The five fields were fixed before any testing. They are Harry Browne's permanent portfolio of stocks, long bonds, gold and cash, with two coins added. The lookbacks, volatility window and budget are common textbook values and were not fitted.

### 2. Target user and product value

Fallow is for a Bitget spot user with 2,000 to 50,000 USDT who holds at least 70% of it in BTC and ETH, checks the account about once a week, and has already sat through one fall of 50% or more. They do not use leverage. They have started buying rTokens since June because the tokens were there, without a plan for how much or when.

This user does not need a higher return than bitcoin. They need to stay invested without being wiped out, and they need a rule simple enough to follow by hand on a Monday. Fallow gives them one list of five weights a week.

The size range is set by what the books can take. A 50,000 USDT account following Fallow moves at most a few thousand USDT per field in a normal week.

### 3. Validation data and key metrics

All figures are observed backtest results on Bitget's own daily candles after 15 bp per unit of turnover, unless marked otherwise.

Test period: April 2019 to October 2026, 2,730 days. The rule was written on data to December 2023. January 2024 onward, 1,007 days, was held back and run once.

| | Sharpe | Sortino | Max drawdown | CAGR | Turnover a year |
|---|---|---|---|---|---|
| Whole period | 1.39 | 2.02 | −10.2% | 9.9% | 6.4× |
| In sample (to December 2023) | 1.46 | 2.13 | −10.2% | 10.4% | 6.3× |
| Out of sample (January 2024 on) | 1.26 | 1.81 | −5.4% | 8.9% | 6.8× |
| Holding bitcoin, whole period | 0.93 | 1.37 | −76.4% | 45.2% | |

- Out-of-sample Sharpe is 0.86 of in-sample. The handbook's alert is below 0.5.
- Rolling 30-day Sharpe is positive in 61% of windows, median 1.14.
- The same rule limited to crypto and USDT scores 0.52 out of sample. Adding the three rTokens takes it to 1.26.
- Putting everything in the one strongest field each week, instead of sharing the risk, scores 0.96 over the whole period with a 70.6% max drawdown and 33× yearly turnover.
- Start on any day and hold a year: Fallow ended up in 83% of 2,366 such periods, with a worst year of −9.4%. Holding bitcoin ended up in 64%, with a worst year of −75.3%.
- Across bitcoin's five deepest falls (−76%, −60%, −53%, −53%, −28%), Fallow returned −9.6%, +2.8%, −2.8%, +0.9% and −2.4% over the same dates.
- Across 480 variants of the settings, out-of-sample Sharpe runs from 1.02 to 1.56. The submitted version is at the 27th percentile.
- Cost sensitivity, out of sample: 1.35 at 5 bp, 1.26 at 15 bp, 1.11 at 30 bp, 0.82 at 60 bp. The 15 bp figure is an estimate of taker fee plus half the spread.

What weakens the case:

- Over the most recent 365 days Fallow is down 4.1%, with a Sharpe of −0.65 and a max drawdown of −5.4%. Holding bitcoin lost 32.3% over the same year, with a 52.3% drawdown. Bitget's official Cross-Asset Momentum Rotation Spot Playbook returned −0.32% over its first 82 live days (observed on its public page, 10 October 2026).
- In the 129 days since rTokens listed, Fallow is down 1.1% (Sharpe −0.56) while bitcoin rose 23%.
- Without gold the out-of-sample Sharpe is 0.48.
- A static quarter each in the S&P 500, gold, Treasuries and cash scored 1.21 out of sample, so the trend filter added little after 2024. Over the whole period that static mix scored 0.82.
- A nine-field version scores 0.89 out of sample.
- The out-of-sample Sharpe has a standard error of 0.60.
- rToken candles before 2 June 2026 are the underlying fund's price without dividends.
- Depth in New York hours is not yet measured. A Friday after-hours reading showed a 10,000 USDT buy of the Treasury rToken costing 20 bp, and the gold rToken's book empty.

How usage would be shown: Fallow is deterministic, so it can be listed on Playbook as a subscribable strategy with one setting, the volatility budget. The measures would be subscribers who keep it running for four weeks or more, USDT following it, and how closely subscriber fills match the backtest's assumed cost. [Targeted: add your own numbers here if you want to commit to any.]

### 4. Progress

Built:

- The rule, a backtest engine with costs, and the metrics, in about 500 lines of Python with no dependencies.
- 15 unit tests, two of which change future prices and check that past returns and past trades do not move.
- A report that rebuilds every figure: four periods, four benchmarks, eight ablations, five cost levels and a 480-variant grid.
- A site that works the plan out live in the browser from Bitget's public candles, with no server and no key. It matches the Python weights.
- A Monday list on the site: enter an account size, a risk setting and current holdings, and it gives the trades to make, each priced against Bitget's live order book. On Saturday 10 October it priced a 3,923 USDT purchase of the S&P 500 rToken at 4.6 bp and reported the gold rToken's book as too thin to fill.
- A planting calendar that shows every weekly plan since 2019, and the record against bitcoin, what the rTokens add, and a section on where it loses.
- A command that prints the week's plan as JSON, and a skill file telling an AI agent how to turn it into spot trades for the user to confirm.
- An order book snapshot tool.

Not built:

- The Playbook package (`playbook/fallow-field-book`) passes Bitget's local validator and reproduces the research weights. [It is not yet uploaded. Update this line once you have published it.]
- Depth measurements during New York hours. The weekend fell inside the build window.
- Live or paper trading. The record is a backtest.

Problems met: the first idea for this hackathon was a weekend catch-up trade between bitcoin and crypto-linked stock perps. It looked strong over 55 weekends. Splitting the sample at Bitget's February 2026 perp relaunch showed that the effect lived almost entirely before that date, so it was dropped.

Next: publish to Playbook, record depth through a full New York week, and run the rule on paper for a quarter before anyone puts money behind it.

Tools: Python standard library, Bitget public spot API, GetAgent Skill 0.6.4 for the Playbook package format and validator.

### 5. Deliverables

- Code, data and reports: https://github.com/kinnuworks/fallow
- Site: https://kinnuworks.github.io/fallow/
- Results as data: `reports/report.json`, `reports/curves.json`, `reports/grid.json`
- Rule: `fallow/rule.py`
- Reproduce: `python3 -m fallow fetch && python3 -m fallow report`
- [Playbook link, once published]
- [Video link]

### 6. Our take on AI trading

The most useful thing the tooling did here was kill our first idea quickly. A catch-up trade that won nine weekends out of nine turned out to describe a product Bitget had already changed. Getting from hunch to honest answer in a few hours is worth more than any one strategy.

One request for Bitget: the candle endpoint serves pre-listing history for rTokens without saying so. A field marking those bars as reference prices would stop people mistaking them for traded ones.

## Role of the LLM in the project

No model runs inside the strategy. The rule is deterministic and every weight can be checked by hand.

An AI coding assistant was used during development to write and test the code, run the parameter grid, find the regime break that killed the first idea, and draft this text. [Name the model here if the form requires it.] We did not receive Qwen credits.

## X post draft

Quote https://x.com/Bitget_AI/status/2100519318824055159 and post:

> For seven years, holding bitcoin on Bitget meant sitting through a 76% fall. I tested a weekly rotation across BTC, ETH and three rTokens (S&P 500, gold, Treasuries). Worst fall: 10%. It has also lost money since June, and the page says so.
>
> https://kinnuworks.github.io/fallow/
>
> #BitgetHackathon @Bitget_AI

## Video script, three minutes

| Time | On screen | Say |
|---|---|---|
| 0:00 | The site's headline | "Fallow is a weekly rotation across five things you can hold on Bitget. The idea is a farmer's: rest a field when it stops giving." |
| 0:20 | This week's planting | "Each field is checked over a month, a quarter, half a year and a year. This week the S&P 500 is rising over all four, so it gets the most ground. Gold and Treasuries have fallen over all four and are resting. Over half the account is in USDT." |
| 0:50 | Underwater chart | "This is seven years of Bitget candles. The dark line is holding bitcoin, which went 76% under. The wheat line is Fallow. Its worst was 10%." |
| 1:15 | Growth chart | "The cost is growth. Bitcoin made sixteen times your money and Fallow doubled it. This is for someone who would have sold at the bottom." |
| 1:35 | Metrics table | "Sharpe 1.39 over the whole period. The rule was written on data to 2023, and the years after score 1.26." |
| 1:55 | What the rTokens add | "Run the same rule with only crypto and USDT and the held-back Sharpe is 0.52. The three rTokens take it to 1.26." |
| 2:10 | Where it loses | "Now the bad news. Since rTokens went live in June it has lost 1%. Take out gold and most of the recent result goes. A plain static mix did about as well after 2024." |
| 2:35 | The grid | "We ran 480 versions. Three quarters of them beat the one on this page. We kept the textbook settings." |
| 2:50 | Terminal running the report | "Two commands rebuild every number, with no key and no packages." |
