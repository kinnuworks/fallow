"""Fallow: a weekly rotation across five things you can hold on Bitget."""

FIELDS = ["BTCUSDT", "ETHUSDT", "RSPYUSDT", "RGLDUSDT", "RTLTUSDT"]
NAMES = {
    "BTCUSDT": "Bitcoin", "ETHUSDT": "Ether", "RSPYUSDT": "S&P 500",
    "RGLDUSDT": "Gold", "RTLTUSDT": "Long Treasuries",
    "REFAUSDT": "Developed ex-US", "REEMUSDT": "Emerging markets",
    "RIEFUSDT": "Mid Treasuries", "RUSOUSDT": "Oil",
}
# The wider universe used only as a robustness check.
NINE_FIELDS = FIELDS + ["REFAUSDT", "REEMUSDT", "RIEFUSDT", "RUSOUSDT"]
CRYPTO = {"BTCUSDT", "ETHUSDT"}

# Bitget listed rToken spot pairs on this day. Earlier rToken candles are the
# underlying ETF's price as Bitget serves it.
RTOKEN_LISTING = "2026-06-02"
# Everything from this day on was held out when the rule was written down.
HOLDOUT_START = "2024-01-01"
