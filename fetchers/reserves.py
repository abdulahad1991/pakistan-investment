"""FX reserves — State Bank of Pakistan (SBP), the official source.

SBP publishes the weekly foreign-exchange reserves position on the Foreign
Exchange Reserves / Management page (dfmd/ferm.asp). The headline table reports
three lines in US$ MILLIONS:

    SBP's Reserves      17,221.0   (the SBP-held reserves — the number markets watch)
    Bank's Reserves      5,520.7   (commercial banks' FX holdings)
    Total Reserves      22,741.7   (the two added together)

We divide by 1000 to express each in US$ BILLIONS, and read the week-ended
"Date Updated" off the Foreign Exchange Reserves row (e.g. 'June 18, 2026').
Reserves are WEEKLY (typically printed Thursday/Friday), so this runs weekly.
"""
import re
from .base import http_get, partition, run, in_band

URL = "https://www.sbp.org.pk/dfmd/ferm.asp"
NAME = "reserves"

# A money figure like 17,221.0 or 5,520.7 or 22,741.7
_NUM = r"([\d][\d,]*\.\d+)"


def _strip(html):
    """Tags out, common entities normalised, whitespace collapsed."""
    txt = (html.replace("&rsquo;", "'").replace("&lsquo;", "'")
               .replace("&nbsp;", " ").replace("&amp;", "&"))
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = re.sub(r"\s+", " ", txt)
    return txt.strip()


def _to_num(s):
    return float(s.replace(",", ""))


def parse_reserves(html):
    """{sbp_bn, banks_bn, total_bn, as_of} from the SBP ferm.asp page.

    Values are reported in US$ MILLIONS on the page; we return BILLIONS
    (millions / 1000, rounded to 2dp). ``as_of`` is the week-ended date string
    taken from the 'Foreign Exchange Reserves' row's Date Updated cell
    (e.g. 'June 18, 2026'), NOT fetch time.
    """
    txt = _strip(html)

    # Each line is "<Label> Reserves <number>" once tags are stripped, e.g.
    # "SBP's Reserves 17,221.0" / "Bank's Reserves 5,520.7" / "Total Reserves 22,741.7".
    m_sbp = re.search(r"SBP'?s?\s+Reserves\s+" + _NUM, txt)
    m_banks = re.search(r"Bank'?s?\s+Reserves\s+" + _NUM, txt)
    m_total = re.search(r"Total\s+Reserves\s+" + _NUM, txt)
    if not (m_sbp and m_banks and m_total):
        raise ValueError("SBP reserves table not found on ferm.asp")

    sbp = _to_num(m_sbp.group(1))
    banks = _to_num(m_banks.group(1))
    total = _to_num(m_total.group(1))

    # Week-ended date: anchor on the Foreign Exchange Reserves / Archive row so we
    # pick its 'Date Updated' (June 18, 2026), not the ticker's "As on" date.
    m_date = re.search(
        r"Foreign\s+Exchange\s+Reserves\s+Archive\s+"
        r"([A-Z][a-z]+\.?\s+\d{1,2},\s*\d{4})", txt)
    if not m_date:
        # Fallback: first "Month DD, YYYY" anywhere on the page.
        m_date = re.search(r"([A-Z][a-z]+\.?\s+\d{1,2},\s*\d{4})", txt)
    as_of = re.sub(r"\s+", " ", m_date.group(1)).strip() if m_date else None

    return {
        "sbp_bn": round(sbp / 1000, 2),
        "banks_bn": round(banks / 1000, 2),
        "total_bn": round(total / 1000, 2),
        "as_of": as_of,
    }


def fetch():
    d = parse_reserves(http_get(URL))
    if not in_band(d["sbp_bn"], 1, 80):  # PK SBP reserves realistically 1-80 bn
        raise ValueError(f"SBP reserves out of sanity band: {d['sbp_bn']}")
    return partition(
        NAME,
        {"sbp_bn": d["sbp_bn"], "total_bn": d["total_bn"]},
        d["as_of"],
        "State Bank of Pakistan (SBP)",
        cadence="weekly",
        metric="FX reserves (US$ bn)",
        banks_bn=d["banks_bn"],
        source_url=URL)


if __name__ == "__main__":
    run(NAME, fetch)
