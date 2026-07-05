"""FX reserves — State Bank of Pakistan (SBP), the official source.

SBP's 2026-07 site redesign emptied the old Foreign Exchange Reserves page
(dfmd/ferm.asp now serves a generic shell). The weekly position now ships in
the server-rendered "Economic Data snapshot" on the M2M page
(ecodata/rates/m2m/m2m-current.asp), in US$ MILLIONS:

    Liquid Foreign Exchange Reserves (USD million)  As on 24- June - 2026
    SBP's Reserves      16,527.2   (the SBP-held reserves — the number markets watch)
    Bank's Reserves      5,517.4   (commercial banks' FX holdings)
    Total Reserves      22,044.6   (the two added together)

We divide by 1000 to express each in US$ BILLIONS, and read the card's own
"As on" date (normalised to 'Month DD, YYYY'). The legacy ferm.asp layout
(labels + 'Foreign Exchange Reserves Archive <date>' row) is kept as a
fallback. Reserves are WEEKLY, so this runs weekly.
"""
import re
from .base import http_get, partition, run, in_band, crawl_first

URL = "https://www.sbp.org.pk/ecodata/rates/m2m/m2m-current.asp"
# Recrawl target: the same Economic Data snapshot (reserves card included) is
# server-rendered on the SBP homepage — the failover when the M2M path dies.
HOME_URL = "https://www.sbp.org.pk/"
NAME = "reserves"

# A money figure like 17,221.0 or 5,520.7 or 22,741.7
_NUM = r"([\d][\d,]*\.\d+)"


def _strip(html):
    """Tags out, common entities normalised, whitespace collapsed."""
    txt = (html.replace("&rsquo;", "'").replace("&lsquo;", "'")
               .replace("’", "'").replace("‘", "'")
               .replace("&nbsp;", " ").replace("\xa0", " ")
               .replace("&amp;", "&"))
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

    # Date, newest layout first: the 2026-07 snapshot card's own "As on
    # 24- June - 2026" (anchored on the card title so we can't pick up the
    # USD/PKR or KIBOR cards' "As on" dates elsewhere on the page).
    as_of = None
    m_date = re.search(
        r"Liquid\s+Foreign\s+Exchange\s+Reserves\s*\(USD\s*million\)\s*"
        r"As\s+on\s+(\d{1,2})\s*-\s*([A-Za-z]+)\s*-\s*(\d{4})", txt, re.I)
    if m_date:
        day, mon, year = m_date.groups()
        as_of = f"{mon.capitalize()} {int(day):02d}, {year}"
    if not as_of:
        # Legacy ferm.asp: the Foreign Exchange Reserves / Archive row's
        # 'Date Updated' (June 18, 2026), not the ticker's "As on" date.
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


def _reserves_from(url, label):
    """A crawl_first thunk: fetch an SBP page, parse + sanity-check reserves."""
    def _thunk():
        d = parse_reserves(http_get(url))
        if not in_band(d["sbp_bn"], 1, 80):  # PK SBP reserves realistically 1-80 bn
            raise ValueError(f"SBP reserves out of sanity band: {d['sbp_bn']}")
        return partition(
            NAME,
            {"sbp_bn": d["sbp_bn"], "total_bn": d["total_bn"]},
            d["as_of"], label,
            cadence="weekly", metric="FX reserves (US$ bn)",
            banks_bn=d["banks_bn"], source_url=url)
    return _thunk


def fetch():
    # Priority: SBP M2M snapshot -> recrawl SBP homepage (same reserves card).
    # If both are down crawl_first raises and run() carries the last weekly
    # figure forward flagged ok=False.
    return crawl_first(NAME, [
        ("sbp-m2m", _reserves_from(URL, "State Bank of Pakistan (SBP)")),
        ("sbp-home", _reserves_from(HOME_URL,
                                    "State Bank of Pakistan (SBP) homepage snapshot")),
    ])


if __name__ == "__main__":
    run(NAME, fetch)
