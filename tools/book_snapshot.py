"""Record spot order book depth for the five fields. Public endpoints, no key."""
import json
import os
import time
import urllib.request

from fallow import FIELDS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIZES = (1_000, 10_000, 50_000, 250_000)


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "fallow/1.0"})
    return json.load(urllib.request.urlopen(req, timeout=20))["data"]


def cost_bp(levels, mid, usd):
    left, qty = usd, 0.0
    for price, size in levels:
        price, size = float(price), float(size)
        take = min(left, price * size)
        qty += take / price
        left -= take
        if left <= 1e-9:
            return round(abs(usd / qty / mid - 1) * 1e4, 1)
    return None  # the book cannot fill this size


def main():
    books = {}
    for s in FIELDS:
        book = get(f"https://api.bitget.com/api/v2/spot/market/orderbook?symbol={s}&type=step0&limit=150")
        if not book.get("bids") or not book.get("asks"):
            books[s] = {"empty": True}
            continue
        bid, ask = float(book["bids"][0][0]), float(book["asks"][0][0])
        mid = (bid + ask) / 2
        books[s] = {
            "spread_bp": round((ask - bid) / mid * 1e4, 1),
            "ask_side_usd": round(sum(float(p) * float(q) for p, q in book["asks"])),
            **{f"buy_{k // 1000}k_bp": cost_bp(book["asks"], mid, k) for k in SIZES},
        }
    stamp = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    path = os.path.join(ROOT, "reports", "book_snapshots.jsonl")
    with open(path, "a") as f:
        f.write(json.dumps({"taken": stamp, "books": books}) + "\n")
    print(stamp)
    for s, b in books.items():
        print(f"  {s:9} {b}")


if __name__ == "__main__":
    main()
