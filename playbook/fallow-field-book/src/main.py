"""Fallow: weekly weights for five fields, published as a selection basket.

The same rule as fallow/rule.py in the research repo, written against the
sandbox data SDK. It publishes weights and never places an order.
"""
import math
import statistics
from datetime import datetime, timezone
from decimal import Decimal

from getagent import data, runtime

DAY_MS = 86_400_000
FIELDS = [
    {"symbol": "BTCUSDT", "asset": "BTC", "name": "Bitcoin", "asset_class": "crypto", "days_per_year": 365},
    {"symbol": "ETHUSDT", "asset": "ETH", "name": "Ethereum", "asset_class": "crypto", "days_per_year": 365},
    {"symbol": "RSPYUSDT", "asset": "rSPY", "name": "SPDR S&P 500 ETF Trust", "asset_class": "rwa", "days_per_year": 252},
    {"symbol": "RGLDUSDT", "asset": "rGLD", "name": "SPDR Gold Shares", "asset_class": "rwa", "days_per_year": 252},
    {"symbol": "RTLTUSDT", "asset": "rTLT", "name": "iShares 20+ Year Treasury Bond ETF", "asset_class": "rwa", "days_per_year": 252},
]
LOOKBACKS = (21, 63, 126, 252)
VOL_WINDOW = 60
VOL_FLOOR = 0.03
MAX_EXPOSURE = 1.0
HISTORY_DAYS = 400
PAGE_DAYS = 90  # the kline endpoint returns at most 90 days a call

THESIS = {
    "en": "{name} is higher than it was over {k} of four lookback stretches, so it gets {w}% of the account this week.",
    "zh": "{name} 在四个回看区间中有 {k} 个上涨，本周分配账户的 {w}%。",
    "zh-tw": "{name} 在四個回看區間中有 {k} 個上漲，本週分配帳戶的 {w}%。",
    "es": "{name} está por encima de su precio en {k} de cuatro periodos de referencia, así que recibe el {w}% de la cuenta esta semana.",
    "ja": "{name} は4つの参照期間のうち {k} つで上昇しており、今週は口座の {w}% を配分します。",
    "vi": "{name} cao hơn giá cũ ở {k} trên bốn giai đoạn tham chiếu, nên tuần này nhận {w}% tài khoản.",
}
RISK = {
    "en": "A trend can turn within a week. The weight is recalculated at the next weekly run, and there is no stop order.",
    "zh": "趋势可能在一周内反转。权重在下次每周运行时重新计算，不设止损单。",
    "zh-tw": "趨勢可能在一週內反轉。權重在下次每週運行時重新計算，不設停損單。",
    "es": "Una tendencia puede girar en una semana. El peso se recalcula en la siguiente ejecución semanal y no hay orden de stop.",
    "ja": "トレンドは1週間以内に反転することがあります。ウェイトは次回の週次実行で再計算され、ストップ注文はありません。",
    "vi": "Xu hướng có thể đảo chiều trong một tuần. Tỷ trọng được tính lại ở lần chạy hàng tuần kế tiếp và không có lệnh dừng lỗ.",
}


def bars(symbol):
    """{bar open time: close} for closed daily bars, stitched from 90-day pages."""
    now = int(datetime.now(timezone.utc).timestamp() * 1000)
    out = {}
    end = now
    while end > now - HISTORY_DAYS * DAY_MS:
        start = end - PAGE_DAYS * DAY_MS
        page = data.crypto.spot.kline(
            symbol=symbol, interval="1d", exchange="bitget",
            start_time=start, end_time=end, limit=1000, closed_only=True,
        )
        for row in data.to_records(page):
            stamp, close = row.get("time"), row.get("close")
            if isinstance(stamp, (int, float)) and close not in (None, "") and int(stamp) + DAY_MS <= now:
                out[int(stamp)] = float(close)
        end = start
    return out


def on_calendar(series, calendar):
    """Closes on a shared daily calendar. A day the market was shut carries the last close forward."""
    stamps = sorted(series)
    out, k, last = [], 0, None
    for day in calendar:
        while k < len(stamps) and stamps[k] <= day:
            last = series[stamps[k]]
            k += 1
        out.append(last)
    return out


def trend_count(prices):
    return sum(1 for n in LOOKBACKS if prices[-1] > prices[-1 - n])


def annual_vol(prices, days_per_year):
    """Volatility over the last VOL_WINDOW bars, skipping days the market was shut."""
    window = prices[-VOL_WINDOW - 1:]
    moved = [b / a - 1 for a, b in zip(window, window[1:]) if b != a]
    if len(moved) < 2:
        return None
    return statistics.pstdev(moved) * math.sqrt(days_per_year)


def run() -> None:
    config = runtime.manifest.get("strategy_config", {}) or {}
    budget = max(5, min(int(config.get("swing_budget_pct", 15) or 15), 30)) / 100

    now = int(datetime.now(timezone.utc).timestamp() * 1000)
    series = {f["symbol"]: bars(f["symbol"]) for f in FIELDS}
    # Bitcoin trades every day, so its bars set the calendar the lookbacks are counted on.
    calendar = sorted(series[FIELDS[0]["symbol"]])
    rows, skipped = [], []
    for field in FIELDS:
        own = series[field["symbol"]]
        newest = max(own) if own else None
        stale = newest is None or now - (newest + DAY_MS) > 5 * DAY_MS
        prices = on_calendar(own, calendar)
        if len(prices) <= max(LOOKBACKS) or stale or prices[-1 - max(LOOKBACKS)] is None:
            skipped.append(field["symbol"])  # not enough clean history to judge this field
            continue
        vol = annual_vol(prices, field["days_per_year"])
        count = trend_count(prices)
        weight = 0.0
        if vol is not None and count:
            weight = (count / len(LOOKBACKS)) * (budget / len(FIELDS)) / max(vol, VOL_FLOOR)
        rows.append({**field, "price": prices[-1], "count": count, "weight": weight})

    total = sum(r["weight"] for r in rows)
    if total > MAX_EXPOSURE:
        for r in rows:
            r["weight"] *= MAX_EXPOSURE / total

    basket = []
    for r in sorted(rows, key=lambda r: r["weight"], reverse=True):
        if r["weight"] < 0.005:
            continue
        pct = str(Decimal(str(r["weight"] * 100)).quantize(Decimal("0.1")))
        fill = {"name": r["name"], "k": r["count"], "w": pct}
        basket.append({
            "asset": r["asset"], "symbol": r["symbol"], "market": "spot",
            "name": r["name"], "asset_class": r["asset_class"],
            "reference_price": str(r["price"]),
            "weight_pct": pct,
            "thesis": THESIS["en"].format(**fill),
            "risk": RISK["en"],
            "thesis_i18n": {lang: text.format(**fill) for lang, text in THESIS.items()},
            "risk_i18n": dict(RISK),
        })

    planted = sum(r["weight"] for r in rows if r["weight"] >= 0.005)
    runtime.emit_signal(
        action="watch",
        symbol=basket[0]["symbol"] if basket else FIELDS[0]["symbol"],
        confidence=round(max((r["count"] for r in rows), default=0) / len(LOOKBACKS), 2),
        metrics={
            "basket_size": len(basket),
            "planted_pct": round(planted * 100, 1),
            "usdt_pct": round((1 - planted) * 100, 1),
            "fields_skipped": len(skipped),
        },
        meta={"basket": basket, "skipped": skipped},
    )


if __name__ == "__main__":
    run()
