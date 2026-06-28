"""Macro snapshot — real GDP growth (Pakistan Bureau of Statistics) + IMF programme status.

GDP growth is the official PBS *provisional* full-year national-accounts figure.
PBS publishes it as prose on /national-accounts-2 (e.g. "provisional growth rate
of GDP for FY 2025-26 is 3.70%"), so we strip tags and regex the sentence out.
National accounts are an EVENT release (annual headline, occasional revisions),
not a daily/monthly print, hence cadence='event'.

The IMF programme status is NOT scraped: the IMF DataMapper / country pages 403
from CI and have no stable machine endpoint for "is the programme on track". It is
maintained here as a curated constant (IMF_STATUS), updated by hand each review.
"""
import re
from .base import http_get, partition, run, in_band

GDP_URL = "https://www.pbs.gov.pk/national-accounts-2"
NAME = "macro"

# Curated, hand-maintained IMF programme status (see module docstring for why it
# is not scraped). Update after each EFF/RSF review.
IMF_STATUS = {
    "status": "Active",
    "programme": "$7B Extended Fund Facility + $1.4B Resilience & Sustainability Facility",
    "last_review": "3rd EFF / 2nd RSF review completed 8 May 2026",
    "disbursed_usd_bn": 4.8,
}

_TAG = re.compile(r"<[^>]+>")
_GDP = re.compile(r"provisional growth rate of GDP for FY ?([\d-]+) is ([\d.]+)")


def parse_gdp(html):
    """(fy, growth_pct) from the PBS national-accounts prose.

    Strips HTML tags first, then matches the official provisional-GDP sentence.
    e.g. 'provisional growth rate of GDP for FY 2025-26 is 3.70%' -> ('2025-26', 3.70).
    Whitespace is collapsed so an inline tag (<strong>/<a>) inside the sentence
    can't break the match and silently freeze GDP at the prior value.
    """
    text = re.sub(r"\s+", " ", _TAG.sub(" ", html))
    m = _GDP.search(text)
    if not m:
        raise ValueError("provisional GDP growth sentence not found on PBS page")
    fy = m.group(1)
    growth = float(m.group(2))
    return fy, growth


def fetch():
    fy, growth = parse_gdp(http_get(GDP_URL))
    if not in_band(growth, 0, 15):  # Pakistan real GDP growth realistically 0-15%
        raise ValueError(f"GDP growth out of sanity band: {growth}")
    value = {
        "gdp_growth": growth,
        "gdp_fy": fy,
        "imf": IMF_STATUS,
    }
    return partition(
        NAME, value, f"FY{fy}",
        "Pakistan Bureau of Statistics (PBS) + IMF",
        cadence="event", metric="Real GDP growth % (provisional) + IMF status",
        source_url=GDP_URL)


if __name__ == "__main__":
    run(NAME, fetch)
