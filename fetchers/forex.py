"""Interbank USD/PKR — State Bank of Pakistan (SBP) Mark-to-Market (M2M) page.

SBP publishes the daily interbank M2M revaluation rate (the authoritative
USD/PKR spot used by banks to revalue FX positions) at
https://www.sbp.org.pk/ecodata/rates/m2m/m2m-current.asp.

The page has worn two skins:

* 2026-07 redesign — a "USD/ PKR Rates" card: "As on 03- Jul - 2026", a
  labelled "M2M Revaluation Rate" figure (now 3 decimals), then a Weighted
  Average BID/Offer block. We anchor on the label so we never pick the
  bid/offer, and read the date from the card's "As on" line.
* legacy Dreamweaver template — a vertical ticker whose USD "M2M Revaluation
  Rate" is the FIRST in-band (200-400) 4-decimal figure, before bid/offer and
  forward/auction tenors; the date is the first 'Mon DD, YYYY' on the page.

Open-market (cash) rates are JS-rendered on forex.pk and deliberately NOT
attempted here; the SBP interbank figure is the authoritative number.
"""
import json as _json
import re
from .base import http_get, partition, run, in_band, crawl_first

M2M_URL = "https://www.sbp.org.pk/ecodata/rates/m2m/m2m-current.asp"
# Recrawl target: the identical Economic Data snapshot is server-rendered on
# the SBP homepage, so if the M2M page moves/dies we re-parse the homepage
# with the very same parser before reaching for a non-SBP provider.
HOME_URL = "https://www.sbp.org.pk/"
# Cross-provider last resort: a keyless reference USD/PKR (open.er-api.com),
# used only when EVERY SBP endpoint is unreachable/unparseable.
ERAPI_URL = "https://open.er-api.com/v6/latest/USD"
NAME = "forex"

# Primary anchor (2026-07 redesign): the figure right after the
# "M2M Revaluation Rate" label (2-4 decimals; tags/whitespace between).
_M2M_LABELLED = re.compile(
    r"M2M\s*Revaluation\s*Rate\s*(?:</[^>]+>|<[^>]+>|\s)*(\d[\d,]*\.\d{2,4})",
    re.I | re.S,
)
# The card's own date: 'As on 03- Jul - 2026' (spacing varies).
_AS_ON = re.compile(
    r"As\s+on\s+(\d{1,2})\s*-\s*([A-Za-z]{3})\s*-\s*(\d{4})", re.I)

# Legacy fallbacks: 4-decimal money figures (e.g. 278.2022) and a
# 'Mon DD, YYYY' date, e.g. 'Jun 23, 2026'.
_NUM = re.compile(r"\d[\d,]*\.\d{4}")
_DATE = re.compile(r"[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}")


def parse_forex(html):
    """Extract the interbank USD/PKR spot and its date from the SBP M2M page.

    Returns {'interbank': float (4dp), 'as_of': 'Mon DD, YYYY'}.

    Strategy: prefer the explicitly labelled "M2M Revaluation Rate" figure
    with its card's "As on DD-Mon-YYYY" date (2026-07 redesign). Fall back to
    the legacy layout: FIRST decimal figure inside the plausible USD/PKR band
    (200-400) — earlier figures (yields, index levels, GIS prices near 100)
    are out of band, and bid/offer/forward tenors come after the spot — with
    the first 'Mon DD, YYYY' string as the date. Either way the date is
    normalised to 'Mon DD, YYYY' (what build_data._to_date understands).
    """
    interbank = None
    redesign = False
    m = _M2M_LABELLED.search(html)
    if m:
        v = float(m.group(1).replace(",", ""))
        if in_band(v, 200, 400):
            interbank = v
            redesign = True
    if interbank is None:
        for raw in _NUM.findall(html):
            v = float(raw.replace(",", ""))
            if in_band(v, 200, 400):
                interbank = v
                break
    if interbank is None:
        raise ValueError("no interbank USD/PKR (200-400) figure found on SBP M2M page")

    # Only trust 'As on' on the redesigned card — the legacy template also
    # carries unrelated stale 'As on DD-Mon-YYYY' strings elsewhere on the page.
    dm = _AS_ON.search(html) if redesign else None
    if dm:
        day, mon, year = dm.groups()
        as_of = f"{mon.capitalize()} {int(day):02d}, {year}"
    else:
        dm = _DATE.search(html)
        if not dm:
            raise ValueError("no 'As on DD-Mon-YYYY' or 'Mon DD, YYYY' date "
                             "found on SBP M2M page")
        # Normalise internal whitespace (the page sometimes wraps the date).
        as_of = re.sub(r"\s+", " ", dm.group(0)).strip()

    return {"interbank": round(interbank, 4), "as_of": as_of}


def parse_erapi(text):
    """USD->PKR from an open.er-api.com ``/v6/latest/USD`` JSON response.

    A keyless REFERENCE rate (not the SBP interbank M2M) — a deliberately
    degraded cross-provider fallback for when every SBP endpoint is down. It
    tracks the interbank rate to well within a percent. Returns
    {'interbank': float(4dp), 'as_of': 'Mon DD, YYYY'|None}; raises ValueError
    on any wrong-shape / wrong-base / missing-PKR response.
    """
    try:
        j = _json.loads(text)
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"er-api: response is not JSON: {e}")
    if not isinstance(j, dict):
        raise ValueError(f"er-api: response is not a JSON object ({type(j).__name__})")
    if j.get("result") != "success":
        raise ValueError(f"er-api: result={j.get('result')!r} (not 'success')")
    if j.get("base_code") != "USD":
        raise ValueError(f"er-api: base_code={j.get('base_code')!r}, expected USD")
    pkr = (j.get("rates") or {}).get("PKR")
    if pkr is None:
        raise ValueError("er-api: no PKR rate in response")
    # 'Sun, 05 Jul 2026 00:02:31 +0000' -> 'Jul 05, 2026' (what _to_date reads).
    as_of = None
    dm = re.search(r",\s*(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})",
                   j.get("time_last_update_utc") or "")
    if dm:
        as_of = f"{dm.group(2)} {int(dm.group(1)):02d}, {dm.group(3)}"
    return {"interbank": round(float(pkr), 4), "as_of": as_of}


def _from_sbp(url, source_label):
    """A crawl_first thunk: fetch an SBP page, parse the M2M spot, sanity-check."""
    def _thunk():
        parsed = parse_forex(http_get(url))
        interbank = parsed["interbank"]
        if not in_band(interbank, 200, 400):
            raise ValueError(f"interbank USD/PKR out of sanity band: {interbank}")
        return partition(
            NAME, {"interbank": interbank}, parsed["as_of"], source_label,
            cadence="intraday", metric="Interbank USD/PKR", source_url=url)
    return _thunk


def _from_erapi():
    parsed = parse_erapi(http_get(ERAPI_URL))
    interbank = parsed["interbank"]
    if not in_band(interbank, 200, 400):
        raise ValueError(f"er-api USD/PKR out of sanity band: {interbank}")
    return partition(
        NAME, {"interbank": interbank}, parsed["as_of"],
        "open.er-api.com (reference rate — SBP unavailable)",
        cadence="intraday", metric="USD/PKR (reference)",
        source_url=ERAPI_URL, approx=True)


def fetch():
    # Priority: SBP M2M page -> recrawl SBP homepage (same snapshot) ->
    # keyless cross-provider reference rate. crawl_first tags the winner with
    # `via`/`failover`; if ALL fail it raises AllSourcesFailed and run() carries
    # the prior value forward flagged ok=False.
    return crawl_first(NAME, [
        ("sbp-m2m", _from_sbp(M2M_URL, "State Bank of Pakistan (SBP) interbank M2M")),
        ("sbp-home", _from_sbp(HOME_URL, "State Bank of Pakistan (SBP) homepage snapshot")),
        ("er-api", _from_erapi),
    ])


if __name__ == "__main__":
    run(NAME, fetch)
