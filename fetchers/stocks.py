"""PSX equities fetcher — one bulk price feed for the whole market.

The PSX Data Portal market-watch page (https://dps.psx.com.pk/market-watch)
lists EVERY actively-traded symbol in a single HTML table. Parsing it once
replaces ~117 per-symbol yfinance round-trips. Delisted tickers (e.g. ENGRO
after its scheme of arrangement) are simply ABSENT from market-watch, so the
page itself is the delisted filter — we never special-case them.

For the handful of headline stocks the homepage displays, ``fetch()`` also
pulls the per-symbol company page to enrich price with fundamentals
(P/E TTM, annual EPS, 52-week range).

Pure stdlib + re. The ``parse_*`` functions take a string and return values —
no network, no import-time side effects — so the unit tests run on fixtures
with zero third-party deps.
"""
import re
import json
import time
import datetime
import html as _html

from .base import http_get, partition, run, in_band, ROOT

NAME = "stocks"

MARKET_WATCH_URL = "https://dps.psx.com.pk/market-watch"
COMPANY_URL = "https://dps.psx.com.pk/company/{sym}"
EOD_URL = "https://dps.psx.com.pk/timeseries/eod/{sym}"

# Headline stocks the homepage surfaces with fundamentals. Any that are absent
# from market-watch (delisted) or fail to fetch are skipped silently.
HEADLINE_SYMBOLS = ["OGDC", "LUCK", "HBL", "MEBL", "PSO", "FFC", "MARI", "UBL"]

# ---------------------------------------------------------------------------
# Pure parsers (what the tests call)
# ---------------------------------------------------------------------------

_TAG = re.compile(r"<[^>]+>")
_ROW = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.S | re.I)
_CELL = re.compile(r"<td\b[^>]*>(.*?)</td>", re.S | re.I)


def _text(fragment):
    """Visible text of an HTML fragment: strip tags, unescape entities."""
    return _html.unescape(_TAG.sub("", fragment)).strip()


def _num(s):
    """First signed decimal in a string (drops commas, %, and leading icons)."""
    s = s.replace(",", "").replace("%", "")
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None


def parse_market_watch(html):
    """Parse the PSX market-watch table.

    Returns ``{symbol: {price, ldcp, change, pct, volume}}`` for every traded
    row. Columns (per the <thead>): SYMBOL, SECTOR, LISTED IN, LDCP, OPEN,
    HIGH, LOW, CURRENT, CHANGE, CHANGE (%), VOLUME. HIGH/LOW here are INTRADAY,
    not 52-week. ``price`` is CURRENT (last traded). Absent symbols are absent
    (the natural delisted filter).
    """
    out = {}
    for rowhtml in _ROW.findall(html):
        if "data-search=" not in rowhtml:
            continue  # header / non-data row
        cells = _CELL.findall(rowhtml)
        if len(cells) < 11:
            continue
        m = re.search(r'data-search="([^"]+)"', rowhtml)
        symbol = (m.group(1) if m else _text(cells[0])).strip().upper()
        if not symbol:
            continue
        vol_txt = _text(cells[10]).replace(",", "")
        vm = re.search(r"-?\d+", vol_txt)
        out[symbol] = {
            "price": _num(_text(cells[7])),   # CURRENT (last price)
            "ldcp": _num(_text(cells[3])),    # last day close price
            "change": _num(_text(cells[8])),  # signed change
            "pct": _num(_text(cells[9])),     # % change
            "volume": int(vm.group()) if vm else None,
        }
    return out


def parse_company(html):
    """Parse a PSX per-symbol company page for headline fundamentals.

    Returns ``{pe_ttm, eps, wk52_low, wk52_high, as_of}``. EPS is the most
    recent ANNUAL value. The 52-week range is read from the numRange data
    attributes that follow the '52-WEEK RANGE' label (the intraday range
    precedes it and is ignored).
    """
    m = re.search(
        r'P/E Ratio \(TTM\)[^<]*</div>\s*<div class="stats_value">\s*([0-9.]+)',
        html)
    pe_ttm = float(m.group(1)) if m else None

    seg = html[html.find("52-WEEK RANGE"):]
    mr = re.search(r'data-low="([0-9.]+)"\s+data-high="([0-9.]+)"', seg)
    wk52_low = float(mr.group(1)) if mr else None
    wk52_high = float(mr.group(2)) if mr else None

    m = re.search(
        r'<td>\s*EPS\s*</td>\s*<td[^>]*>\s*<span[^>]*>\s*([0-9.]+)', html)
    eps = float(m.group(1)) if m else None

    m = re.search(r'As of\s*([^<]+?)\s*</div>', html)
    as_of = m.group(1).strip() if m else None

    # 1-Year Change — magnitude is in the value, sign is carried by the
    # change__text--pos / --neg CSS class (the page renders an up/down icon, not
    # a minus sign), e.g. '1-Year Change ... change__text--pos ... 56.45%'.
    chg1y = None
    m = re.search(
        r'1-Year Change[^<]*</div>\s*<div class="stats_value\s+change__text--(\w+)'
        r'[^>]*>(?:\s*<i[^>]*></i>)?\s*([0-9.]+)\s*%', html)
    if m:
        chg1y = float(m.group(2))
        if m.group(1).startswith("neg"):
            chg1y = -chg1y

    return {
        "pe_ttm": pe_ttm,
        "eps": eps,
        "wk52_low": wk52_low,
        "wk52_high": wk52_high,
        "chg1y": chg1y,
        "as_of": as_of,
    }


def parse_eod_monthly(json_text, months=37):
    """Monthly last-close series from a PSX EOD payload.

    EOD rows are ``[unix_ts, open, volume, CLOSE]`` (close is index 3). Returns
    ``{labels: ['YYYY-MM', ...], values: [close, ...]}`` for the last ``months``
    calendar months — the shape the dividend page's sparklines expect.
    """
    d = json.loads(json_text)
    rows = d.get("data") if isinstance(d, dict) else d
    by_month = {}
    for r in sorted(rows or [], key=lambda x: x[0]):
        ts, close = r[0], r[3]
        key = datetime.datetime.fromtimestamp(
            ts, datetime.timezone.utc).strftime("%Y-%m")
        by_month[key] = round(float(close), 2)
    keys = sorted(by_month)[-months:]
    return {"labels": keys, "values": [by_month[k] for k in keys]}


# ---------------------------------------------------------------------------
# Network fetch (CI only)
# ---------------------------------------------------------------------------

def fetch_history(symbols, throttle=0.3, months=37):
    """Write data/stock_history.json (monthly closes per symbol) from PSX EOD.

    Replaces the old yfinance-sourced history that fed the dividend page and the
    backtester. Heavy (one EOD call per symbol) — the orchestrator runs it on a
    weekly cadence, not every refresh.
    """
    out = {}
    syms = [s.strip().upper() for s in symbols if s]
    for i, sym in enumerate(syms):
        try:
            h = parse_eod_monthly(http_get(EOD_URL.format(sym=sym)), months)
            if len(h["values"]) >= 2:
                out[sym] = h
        except Exception:  # noqa: BLE001 - one symbol must not sink the run
            pass
        if throttle and i < len(syms) - 1:
            time.sleep(throttle)
    if out:
        (ROOT / "data" / "stock_history.json").write_text(
            json.dumps(out, ensure_ascii=False), encoding="utf-8")
        print(f"  ✓ stock_history.json: {len(out)}/{len(syms)} tickers")
    return out


def fetch(enrich=None, throttle=0.3):
    html = http_get(MARKET_WATCH_URL)
    prices = parse_market_watch(html)

    if len(prices) < 50 or "OGDC" not in prices:
        raise ValueError(
            f"market-watch parse looks wrong: {len(prices)} symbols, "
            f"OGDC present={'OGDC' in prices}")

    # Sanity-band a couple of liquid blue chips before trusting the feed.
    for sym in ("OGDC", "HBL"):
        px = prices.get(sym, {}).get("price")
        if px is None or not in_band(px, 1, 100000):
            raise ValueError(f"{sym} price out of band: {px!r}")

    # Enrich displayed stocks with fundamentals (P/E, EPS, 52w, 1y change) from
    # their per-symbol company pages (static HTML — no JS). ``enrich`` is the
    # full displayed universe passed by the orchestrator; defaults to headlines.
    # Per-symbol failures are skipped so one bad page never sinks the feed.
    enrich_list = [s.strip().upper() for s in (enrich or HEADLINE_SYMBOLS) if s]
    headlines = {}
    for i, sym in enumerate(enrich_list):
        if sym not in prices:
            continue  # delisted / not trading today — no request made, no throttle
        try:
            fundamentals = parse_company(http_get(COMPANY_URL.format(sym=sym)))
            headlines[sym] = {**prices[sym], **fundamentals}
        except Exception:  # noqa: BLE001 - per-symbol enrichment is optional
            pass
        # Throttle after EVERY company-page request (success or failure) so a run
        # of failing requests can't machine-gun PSX.
        if throttle and i < len(enrich_list) - 1:
            time.sleep(throttle)

    # The data's own timestamp comes from a company page's quote date when we
    # have one (e.g. 'Wed, Jun 24, 2026 3:49 PM'); else fall back to today.
    as_of = next(
        (h["as_of"] for h in headlines.values() if h.get("as_of")), None)
    if not as_of:
        as_of = datetime.date.today().isoformat()

    value = {
        "count": len(prices),
        "prices": prices,
        "headlines": headlines,
    }
    return partition(NAME, value, as_of, MARKET_WATCH_URL, cadence="intraday")


if __name__ == "__main__":
    run(NAME, fetch)
