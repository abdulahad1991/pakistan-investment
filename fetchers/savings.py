"""CDNS National Savings — latest profit rates (NSS schemes).

Source: Central Directorate of National Savings, savings.gov.pk/latest-profit-rates.
The headline live rates are NOT in a <table>. They sit in a single-line ticker
"Latest profit rates:" banner (and again in the ticker link's title attr). After
stripping tags + unescaping entities + collapsing whitespace the banner reads,
e.g.:

  Latest profit rates: 10-06-2026 Bahbood Savings Certificates 13.20%,
  Defence Savings Certificates 10.44%, Special Savings Certificates:
  First 5 profits =12.4%, 6th Profit = 13.6%, Regular Income Certificates 11.82%,
  Short Term Savings Certificates 3M=11.4%,6M=11.66% & 1Year=11.77%,
  Savings Account 10.00%, Special Savings Account: First 5 profits 12.4%,
  6th Profit= 13.6%, ...

So we anchor each scheme name to the % value that follows it, tolerating the
'=', '&' and ':' separators and the SSC/SSA tiered (first-5 vs 6th) layout. The
source misspells 'Bahbood' — we map it to the conventional 'Behbood'. The
banner's leading date is the data's own effective date (as_of). EVENT cadence:
NSS rates change irregularly (after T-bill/PIB auctions), not on a calendar.
"""
import re
import html as _html

from .base import http_get, partition, run, in_band

NAME = "savings"
SOURCE = "Central Directorate of National Savings (CDNS)"
SOURCE_URL = "https://savings.gov.pk/latest-profit-rates/"


def _plain(html_text):
    """HTML -> tag-free, entity-decoded, single-spaced plain text (banner line)."""
    t = re.sub(r"<[^>]+>", " ", html_text)   # strip tags
    t = _html.unescape(t)                     # &amp; -> &, &#038; -> & ...
    t = t.replace("\xa0", " ")
    t = re.sub(r"\s+", " ", t).strip()        # collapse whitespace
    return t


def parse_savings(html_text):
    """Pure parser: HTML string -> {'effective': 'DD-MM-YYYY', 'schemes': {...}}.

    No network, no import-time side effects. Raises ValueError if the banner /
    its date is absent.
    """
    text = _plain(html_text)

    m_date = re.search(r"Latest profit rates:\s*(\d{1,2}-\d{1,2}-\d{4})", text)
    if not m_date:
        raise ValueError("CDNS 'Latest profit rates:' banner not found")
    effective = m_date.group(1)

    def grab(pattern):
        m = re.search(pattern, text)
        return round(float(m.group(1)), 4) if m else None

    schemes = {}

    # 'Bahbood Savings Certificates 13.20%' (source spelling -> 'Behbood')
    schemes["Behbood Savings Certificate"] = grab(
        r"Bahbood Savings Certificates?\s*=?\s*([\d.]+)\s*%")
    # 'Defence Savings Certificates 10.44%'
    schemes["Defence Savings Certificate"] = grab(
        r"Defence Savings Certificates?\s*=?\s*([\d.]+)\s*%")
    # 'Regular Income Certificates 11.82%'
    schemes["Regular Income Certificate"] = grab(
        r"Regular Income Certificates?\s*=?\s*([\d.]+)\s*%")
    # 'Savings Account 10.00%' — guard against 'Special'/'Islamic Savings Account'
    schemes["Savings Account"] = grab(
        r"(?<!Special )(?<!Islamic )Savings Account\s*=?\s*([\d.]+)\s*%")

    # SSC is tiered. Anchor on the *Certificate* (not the *Account*) variant:
    # 'Special Savings Certificates: First 5 profits =12.4%, 6th Profit = 13.6%'
    m_ssc = re.search(
        r"Special Savings Certificates?:?\s*First 5 profits\s*=?\s*([\d.]+)\s*%"
        r"\s*,?\s*6th Profit\s*=?\s*([\d.]+)\s*%",
        text)
    if m_ssc:
        schemes["Special Savings Certificate"] = round(float(m_ssc.group(1)), 4)
        schemes["Special Savings Certificate 6th"] = round(float(m_ssc.group(2)), 4)

    missing = [k for k, v in schemes.items() if v is None]
    if missing or "Special Savings Certificate" not in schemes:
        raise ValueError(f"CDNS banner missing scheme rates: {missing or 'SSC tiers'}")

    return {"effective": effective, "schemes": schemes}


def fetch():
    parsed = parse_savings(http_get(SOURCE_URL))
    schemes = parsed["schemes"]
    for k, v in schemes.items():
        if not in_band(v, 3, 25):   # NSS profit rates realistically 3-25% p.a.
            raise ValueError(f"CDNS rate out of sanity band: {k}={v}")
    return partition(
        NAME, schemes, as_of=parsed["effective"], source=SOURCE,
        cadence="event", effective=parsed["effective"], source_url=SOURCE_URL)


if __name__ == "__main__":
    run(NAME, fetch)
