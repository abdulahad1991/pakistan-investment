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
import re
from .base import http_get, partition, run, in_band

M2M_URL = "https://www.sbp.org.pk/ecodata/rates/m2m/m2m-current.asp"
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
