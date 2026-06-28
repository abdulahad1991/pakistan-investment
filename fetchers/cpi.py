"""CPI / headline inflation — Pakistan Bureau of Statistics (PBS), the official source.

The old site hardcoded inflation_cpi=7.0 forever (no code ever fetched it) while
real CPI was 11.7% — a 4.7pp error that poisoned every real-return figure.

PBS publishes a machine-readable SDMX-ML feed at /cpi containing ~26 series.
We use the HEADLINE General CPI index, INDICATOR="PCPI_IX" (base 2015/2016), and
compute YoY ourselves from the latest month vs the same month a year earlier.
CPI is MONTHLY (next month prints ~1st), so this fetcher runs monthly, not daily.
"""
import re
from .base import http_get, partition, run, in_band

CPI_URL = "https://www.pbs.gov.pk/cpi"
NAME = "inflation"

# Match a whole <Obs .../> element, then pull each attribute out independently —
# robust to attribute ORDER and to extra SDMX attributes (OBS_STATUS/OBS_CONF)
# the publisher may add. A regex requiring the two attrs adjacent would silently
# drop the latest month if PBS ever inserted a status flag between them, shipping
# a stale headline with ok=True (the anti-staleness flag would never fire).
_OBS_EL = re.compile(r'<(?:\w+:)?Obs\b[^>]*?/?>')
_TP = re.compile(r'TIME_PERIOD="([\d-]+)"')
_OV = re.compile(r'OBS_VALUE="([\d.]+)"')


def parse_cpi(xml):
    """(yoy_pct, as_of 'YYYY-MM', index_latest, index_year_ago) from PBS SDMX.

    Selects ONLY the headline General CPI index series (PCPI_IX) — the file also
    contains 12 sub-group indices (PCPI_CP_NN_IX) and weights (PCPI_*_WT); a
    naive 'grab any OBS_VALUE' picks a weight and returns garbage.
    """
    m = re.search(r'<(?:\w+:)?Series\b[^>]*INDICATOR="PCPI_IX"[^>]*>(.*?)</(?:\w+:)?Series>',
                  xml, re.S)
    if not m:
        raise ValueError("headline PCPI_IX series not found in PBS SDMX")
    body = m.group(1)
    obs = {}
    for el in _OBS_EL.finditer(body):
        tp = _TP.search(el.group())
        ov = _OV.search(el.group())
        if tp and ov:
            obs[tp.group(1)] = float(ov.group(1))
    if not obs:
        raise ValueError("no observations in PCPI_IX series")
    months = sorted(obs)
    latest = months[-1]
    yr, mo = latest.split("-")[:2]
    prior_key = f"{int(yr) - 1}-{mo}"
    if prior_key not in obs:
        raise ValueError(f"no year-ago observation for {latest}")
    yoy = round((obs[latest] / obs[prior_key] - 1) * 100, 1)
    return yoy, latest, obs[latest], obs[prior_key]


def fetch():
    yoy, as_of, ix_now, ix_prev = parse_cpi(http_get(CPI_URL))
    if not in_band(yoy, 0, 60):  # Pakistan CPI realistically 0-60%
        raise ValueError(f"CPI YoY out of sanity band: {yoy}")
    return partition(
        NAME, yoy, as_of, "Pakistan Bureau of Statistics (PBS)",
        cadence="monthly", metric="CPI inflation YoY %",
        index_latest=round(ix_now, 4), index_year_ago=round(ix_prev, 4),
        source_url=CPI_URL)


if __name__ == "__main__":
    run(NAME, fetch)
