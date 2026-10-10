# Fallow: Five-Field Rotation

A weekly allocation basket. It publishes weights for five Bitget spot markets and never places orders.

## 策略 / Strategy

Five fields: BTCUSDT, ETHUSDT, RSPYUSDT, RGLDUSDT and RTLTUSDT. Each week the package reads daily closes, counts over how many of four lookback stretches each field has risen, and gives rising fields a share of a yearly volatility budget. Calmer fields get larger shares. Whatever is not allocated is meant to sit in USDT.

## 开仓 / Entry

There is no order. A field appears in the basket when it has risen over at least one lookback stretch, with a weight that grows as more stretches agree.

## 平仓 / Exit

There is no close order and no stop. A field drops out at the next weekly run once it has fallen over every stretch. Each run replaces the previous basket.

## 风险 / Risk

Trends reverse, and the basket trails badly in sharp rallies because much of the account is usually resting. The research backtest lost money over the four months after rTokens listed and leaned heavily on gold before that. rToken books are thin outside New York hours. A field with missing or stale price history is skipped and listed under `meta.skipped`. This is research, and it is not advice.

## Setting

`swing_budget_pct` is the yearly volatility budget for the whole basket, from 5 to 30. Higher means larger weights and less USDT.

## Validate

```bash
python3 scripts/validate.py path/to/fallow-field-book
```

The research code, backtest and results are in the Fallow repository.
