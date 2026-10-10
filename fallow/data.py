"""Daily candles from Bitget's public spot API, cached as CSV under data/."""
import csv
import json
import os
import time
import urllib.request

API = "https://api.bitget.com/api/v2/spot/market/history-candles"
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DAY_MS = 86_400_000
EARLIEST = 1_483_228_800_000  # 2017-01-01


def _get(url):
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "fallow/1.0"})
            return json.load(urllib.request.urlopen(req, timeout=25))
        except Exception as err:  # the API drops the odd request
            last = err
            time.sleep(1 + attempt)
    raise RuntimeError(f"Bitget did not answer: {url}") from last


def fetch(symbol):
    """All daily bars for one symbol, oldest first. Bars open at 16:00 UTC."""
    bars, end = {}, int(time.time() * 1000)
    while True:
        page = _get(f"{API}?symbol={symbol}&granularity=1day&endTime={end}&limit=200").get("data") or []
        if not page:
            break
        for row in page:
            bars[int(row[0])] = [float(x) for x in row[1:5]] + [float(row[6])]
        first = int(page[0][0])
        if first >= end or len(page) < 2 or first < EARLIEST:
            break
        end = first - 1
        time.sleep(0.08)
    # Drop the bar that is still forming.
    now = int(time.time() * 1000)
    return [(ts, *bars[ts]) for ts in sorted(bars) if ts + DAY_MS <= now]


def path(symbol):
    return os.path.join(DATA_DIR, f"{symbol}.csv")


def save(symbol, rows):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(path(symbol), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["open_time_ms", "date", "open", "high", "low", "close", "usdt_volume"])
        for ts, o, h, l, c, v in rows:
            w.writerow([ts, time.strftime("%Y-%m-%d", time.gmtime(ts / 1000)), o, h, l, c, round(v, 2)])


def load(symbol):
    """{open_time_ms: close} from the cached CSV."""
    with open(path(symbol)) as f:
        return {int(r["open_time_ms"]): float(r["close"]) for r in csv.DictReader(f)}


def refresh(symbols):
    for s in symbols:
        rows = fetch(s)
        save(s, rows)
        print(f"{s}: {len(rows)} days, {time.strftime('%Y-%m-%d', time.gmtime(rows[0][0] / 1000))} "
              f"to {time.strftime('%Y-%m-%d', time.gmtime(rows[-1][0] / 1000))}")


def panel(symbols):
    """Closes for every symbol on bitcoin's calendar.

    Bitcoin trades every day and the rTokens' underlying markets do not, so a
    closed day carries the last close forward. The panel starts on the first
    day every symbol has a price.
    """
    closes = {s: load(s) for s in symbols}
    days = sorted(closes["BTCUSDT"] if "BTCUSDT" in closes else load("BTCUSDT"))
    filled = {}
    for s in symbols:
        last, col = None, []
        for d in days:
            last = closes[s].get(d, last)
            col.append(last)
        filled[s] = col
    start = max(next(i for i, v in enumerate(filled[s]) if v is not None) for s in symbols)
    return days[start:], {s: filled[s][start:] for s in symbols}
