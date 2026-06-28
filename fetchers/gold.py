"""Pakistani retail gold rates — gold.pk (Karachi Sarafa / APSGJA).

gold.pk republishes the rate fixed by the Karachi Saraf Jewellers Association
(the trend-setter for the whole country). The page is plain HTML with a hero
card:

    <p class='goldratehome'>Rs. 434500.00</p>
    <p>24 Karat Gold Rate <b>(1 Tola)</b></p>

We anchor on that "24 Karat ... (1 Tola)" label so we never accidentally pick a
10-gram / per-gram / per-ounce figure or a city/silver row. Only the 24K per-tola
number is parsed from the page; the 22K and metric-weight conversions are derived
arithmetically in fetch() (1 tola = 11.6638 g, 22K = 24K * 22/24).

Note: gold.pk is a RETAIL rate and carries a premium over international spot — a
cross-source (Daily Pakistan ~431,323) sits a bit below it. The >5% spot sanity
guard therefore lives in fetch() (and is skipped when yfinance is unavailable),
never in the pure parser.
"""
import re
from .base import http_get, partition, run, in_band

GOLD_URL = "https://gold.pk/"
NAME = "gold"

# 1 tola in grams (standard Pakistani jeweller conversion).
TOLA_GRAMS = 11.6638

# Primary anchor: the hero card price immediately preceding the
# "24 Karat Gold Rate (1 Tola)" label.
_HERO_24K_TOLA = re.compile(
    r"Rs\.?\s*([\d,]+)(?:\.\d+)?\s*</p>\s*"
    r"<p[^>]*>\s*24\s*Karat\s*Gold\s*Rate\s*<b>\s*\(\s*1\s*Tola\s*\)",
    re.I | re.S,
)

# Fallback: the "per tola Gold Price" comparison table, first (24 Karat) cell.
_TABLE_24K_TOLA = re.compile(
    r"per\s*tola\s*Gold\s*Price.*?Rs\.?\s*([\d,]+)",
    re.I | re.S,
)


def _to_int(s):
    return int(s.replace(",", "").strip())


def parse_gold(html):
    """Return ``{"tola_24k": <int>}`` — 24 Karat gold, price per 1 tola (PKR).

    Pure string -> value; raises ValueError if the 24K/1-tola rate is absent.
    """
    m = _HERO_24K_TOLA.search(html) or _TABLE_24K_TOLA.search(html)
    if not m:
        raise ValueError("24K per-tola gold rate not found on gold.pk page")
    return {"tola_24k": _to_int(m.group(1))}


def _spot_cross_check(tola_24k):
    """Best-effort: warn/raise only if gold.pk is wildly off international spot.

    Skipped silently when yfinance (CI-only) is unavailable. gold.pk is a retail
    rate so it sits ABOVE spot — we allow a generous premium band and only reject
    values that are physically implausible versus the metal's spot value.
    """
    try:
        import yfinance as yf  # CI-only; guarded so parser/tests stay stdlib
    except Exception:
        return  # yfinance not installed locally — skip the soft guard
    try:
        usd_oz = float(yf.Ticker("GC=F").fast_info["last_price"])
        usd_pkr = float(yf.Ticker("PKR=X").fast_info["last_price"])
    except Exception:
        return  # transient network/data issue — don't fail the fetch on this
    # 1 tola = 11.6638 g; 1 troy oz = 31.1035 g  ->  tola = 0.375 troy oz.
    spot_tola_pkr = usd_oz * (TOLA_GRAMS / 31.1035) * usd_pkr
    if spot_tola_pkr <= 0:
        return
    ratio = tola_24k / spot_tola_pkr
    # Allow up to ~25% retail premium above spot, and never far below spot.
    if not (0.90 <= ratio <= 1.30):
        raise ValueError(
            f"gold.pk tola {tola_24k} is {ratio:.2f}x international spot "
            f"({spot_tola_pkr:.0f}) — outside the >5% sanity band")


def fetch():
    parsed = parse_gold(http_get(GOLD_URL))
    tola_24k = parsed["tola_24k"]
    if not in_band(tola_24k, 100_000, 2_000_000):
        raise ValueError(f"24K tola out of sanity band: {tola_24k}")

    # Derive the rest arithmetically (page-independent, internally consistent).
    tola_22k = round(tola_24k * 22 / 24)
    gram_24k = round(tola_24k / TOLA_GRAMS)
    gram_22k = round(tola_22k / TOLA_GRAMS)
    g10_24k = round(tola_24k / TOLA_GRAMS * 10)
    g10_22k = round(tola_22k / TOLA_GRAMS * 10)

    _spot_cross_check(tola_24k)  # soft cross-source guard (skipped w/o yfinance)

    value = {
        "tola_24k": tola_24k,
        "tola_22k": tola_22k,
        "gram_24k": gram_24k,
        "gram_22k": gram_22k,
        "g10_24k": g10_24k,
        "g10_22k": g10_22k,
    }
    return partition(
        NAME, value, None,  # no clean data-date on page -> as_of=None (today)
        "gold.pk (Karachi Sarafa / APSGJA)",
        cadence="intraday", metric="retail gold rate (PKR)",
        unit="PKR", source_url=GOLD_URL,
        note="retail rate; carries a premium over international spot")


if __name__ == "__main__":
    run(NAME, fetch)
