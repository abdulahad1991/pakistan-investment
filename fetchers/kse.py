"""KSE-100 index level — Pakistan Stock Exchange (PSX Data Portal).

The PSX EOD time-series endpoint returns JSON with a NON-STANDARD row order:
    [unix_ts, OPEN, VOLUME, CLOSE]
i.e. index 1 is the OPEN, index 2 is VOLUME, and index 3 is the *CLOSE*.

CRITICAL BUG THIS FIXES: the old site read index 1 (the OPEN of the most recent
bar) and showed 179,571 as the "KSE-100 level". The real closing level is index 3
(~178,115). The series can arrive newest-first or unsorted, so we SORT by ts
ascending before picking the latest / previous bar.

Besides the headline level we resample the full series to a last-close-per-
calendar-month history (~last 72 months) for the homepage chart.
"""
import json
from datetime import datetime, timezone

from .base import http_get, partition, run, in_band

NAME = "kse"
KSE_URL = "https://dps.psx.com.pk/timeseries/eod/KSE100"
SOURCE = "Pakistan Stock Exchange (PSX Data Portal)"

# Row index map for the PSX EOD payload (non-standard order).
TS, OPEN, VOLUME, CLOSE = 0, 1, 2, 3


def _ts_date(ts):
    """Unix seconds -> a UTC calendar date (matches PSX's own EOD dating)."""
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).date()


def parse_kse(text_or_json):
    """Parse the KSE-100 EOD JSON into headline + monthly history.

    Pure: accepts the raw response body (str) or an already-decoded dict/list.
    Returns {level, as_of, prev_close, change, change_pct, history{labels,values}}.
    """
    if isinstance(text_or_json, (dict, list)):
        payload = text_or_json
    else:
        payload = json.loads(text_or_json)

    rows = payload["data"] if isinstance(payload, dict) else payload
    if not rows:
        raise ValueError("KSE-100 payload has no data rows")

    # (ts, close) using the CLOSE column (index 3), sorted oldest -> newest.
    bars = sorted(
        ((int(r[TS]), float(r[CLOSE])) for r in rows),
        key=lambda b: b[0],
    )

    latest_ts, latest_close = bars[-1]
    if len(bars) < 2:
        raise ValueError("KSE-100 series too short for a previous close")
    prev_close_raw = bars[-2][1]

    level = round(latest_close, 2)
    prev_close = round(prev_close_raw, 2)
    as_of = _ts_date(latest_ts).isoformat()
    change = round(level - prev_close, 2)
    change_pct = round((level - prev_close) / prev_close * 100, 2)

    # Resample to the last close of each calendar month.
    monthly = {}  # (year, month) -> (ts, close)
    for ts, close in bars:
        d = _ts_date(ts)
        key = (d.year, d.month)
        cur = monthly.get(key)
        if cur is None or ts > cur[0]:
            monthly[key] = (ts, close)

    ordered = sorted(monthly.items(), key=lambda kv: kv[0])[-72:]
    labels = [_ts_date(ts).strftime("%b'%y") for _, (ts, _c) in ordered]
    values = [round(close, 2) for _, (_ts, close) in ordered]

    return {
        "level": level,
        "as_of": as_of,
        "prev_close": prev_close,
        "change": change,
        "change_pct": change_pct,
        "history": {"labels": labels, "values": values},
    }


def fetch():
    parsed = parse_kse(http_get(KSE_URL))
    level = parsed["level"]
    if not in_band(level, 50000, 500000):  # KSE-100 realistic band
        raise ValueError(f"KSE-100 level out of sanity band: {level}")
    return partition(
        NAME,
        {
            "level": parsed["level"],
            "prev_close": parsed["prev_close"],
            "change": parsed["change"],
            "change_pct": parsed["change_pct"],
            "history": parsed["history"],
        },
        parsed["as_of"],
        SOURCE,
        cadence="intraday",
        metric="KSE-100 index level (close)",
        source_url=KSE_URL,
    )


if __name__ == "__main__":
    run(NAME, fetch)
