"""Interbank USD/PKR — State Bank of Pakistan (SBP) Mark-to-Market (M2M) page.

SBP publishes the daily interbank M2M revaluation rate (the authoritative
USD/PKR spot used by banks to revalue FX positions) at
https://www.sbp.org.pk/ecodata/rates/m2m/m2m-current.asp.

The page is a legacy Dreamweaver template: the rate board lives in a vertical
ticker whose USD "M2M Revaluation Rate" is the spot. After that come bid/offer
and various forward/auction tenors. We take the FIRST in-band (200-400) decimal
— the spot — NOT the later bid/offer/forward columns.

Open-market (cash) rates are JS-rendered on forex.pk and deliberately NOT
attempted here; the SBP interbank figure is the authoritative number.
"""
import re
from .base import http_get, partition, run, in_band

M2M_URL = "https://www.sbp.org.pk/ecodata/rates/m2m/m2m-current.asp"
NAME = "forex"

# 4-decimal money figures, optionally with thousands separators (e.g. 278.2022).
_NUM = re.compile(r"\d[\d,]*\.\d{4}")
# A "Mon DD, YYYY" date as printed on the page, e.g. 'Jun 23, 2026'.
_DATE = re.compile(r"[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}")


def parse_forex(html):
    """Extract the interbank USD/PKR spot and its date from the SBP M2M page.

    Returns {'interbank': float (4dp), 'as_of': 'Mon DD, YYYY'}.

    Strategy: the spot is the FIRST decimal figure that falls inside the
    plausible USD/PKR band (200-400). Earlier figures on the page (yields,
    index levels, GIS prices near 100) are out of band and skipped; the
    later bid/offer and forward tenors come after the spot, so first-in-band
    is the spot. The date is the first 'Mon DD, YYYY' string on the page.
    """
    interbank = None
    for raw in _NUM.findall(html):
        v = float(raw.replace(",", ""))
        if in_band(v, 200, 400):
            interbank = v
            break
    if interbank is None:
        raise ValueError("no interbank USD/PKR (200-400) figure found on SBP M2M page")

    dm = _DATE.search(html)
    if not dm:
        raise ValueError("no 'Mon DD, YYYY' date found on SBP M2M page")
    as_of = dm.group(0)
    # Normalise internal whitespace (the page sometimes wraps the date).
    as_of = re.sub(r"\s+", " ", as_of).strip()

    return {"interbank": round(interbank, 4), "as_of": as_of}


def fetch():
    parsed = parse_forex(http_get(M2M_URL))
    interbank = parsed["interbank"]
    if not in_band(interbank, 200, 400):
        raise ValueError(f"interbank USD/PKR out of sanity band: {interbank}")
    return partition(
        NAME, {"interbank": interbank}, parsed["as_of"],
        "State Bank of Pakistan (SBP) interbank M2M",
        cadence="intraday", metric="Interbank USD/PKR",
        source_url=M2M_URL)


if __name__ == "__main__":
    run(NAME, fetch)
