---
name: fallow
description: >-
  Reads this week's Fallow plan (weights for BTCUSDT, ETHUSDT, RSPYUSDT,
  RGLDUSDT and RTLTUSDT on Bitget spot, with the rest in USDT) and turns it
  into a list of spot trades for the user to confirm. Use when the user asks
  what Fallow holds this week, how to rebalance to it, or what it would cost.
---

# Fallow

Fallow is a weekly rotation across five Bitget spot markets. It is long only and never borrows.

## Get the plan

```bash
python3 -m fallow plan --fresh --json
```

`--fresh` downloads the latest daily candles from Bitget's public API. No key is needed. The output lists a weight for each symbol and a share to keep in USDT. Pass `--budget 0.10` to `--budget 0.30` to change the yearly swing budget. The default is 0.15.

## Turn it into trades

1. Read the user's spot balances with a read-only tool, for example `bgc` from Bitget Agent Hub started with `--read-only`.
2. For each symbol, the target value is `weight × total account value in USDT`. The trade is target minus what is held.
3. Skip any trade under 5 USDT.
4. Show the full list to the user and wait for a clear yes before placing anything.

## Rules for the agent

- Spot orders only. Never open a perpetual or use leverage for Fallow.
- Do not place rToken orders while New York is closed. The books are thin and the gold rToken's book can be empty.
- A field with weight 0 is sold in full.
- Fallow sets its plan once a week. Do not rebalance more often than that.
- Placing orders has not been tested end to end with a funded account. Use Agent Hub's `--paper-trading` mode first.
