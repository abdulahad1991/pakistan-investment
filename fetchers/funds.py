"""Mutual fund NAVs + trailing returns — Mutual Funds Association of Pakistan (MUFAP).

MUFAP publishes one very wide HTML table ("NAV Returns Performance Summary
Report") with every open-end fund's NAV plus a row of trailing-return columns
(YTD, MTD, 1/15/30/90/180/270/365 days, 2/3 years).

Two things the OLD site got wrong, fixed here:

1. COLUMN DRIFT. The 1-year figure is the '365 Days' column. We PIN it by its
   header NAME (locate the '365 Days' <th>, use that column index) instead of a
   hard-coded position — MUFAP reorders/adds columns and a fixed index silently
   reads the wrong number.

2. RETURN TYPE. MUFAP tags every fund's category as either '(Annualized Return)'
   (income / money-market / fixed-income funds) or '(Absolute Return)'
   (equity / stock funds). The old site labelled equity ABSOLUTE returns as
   'annualized', which is flatly wrong (a +37% 1-yr equity number is cumulative,
   not annualized). We read each fund's category cell and carry the real
   return_type so downstream copy can't mislabel it.

The data's own date is each row's Validity Date (NAVs lag ~1 business day and
differ per fund); the only single page-level stamp is "Report Date: <date>",
which we use as the partition ``as_of``.
"""
import re
from .base import http_get, partition, run, in_band

NAME = "funds"
URL = "https://www.mufap.com.pk/Industry/IndustryStatDaily?tab=1"

# Funds we surface on the site. Matched by EXACT (cleaned) fund-name cell so a
# fund isn't confused with a near-namesake (e.g. "... Fund" vs "... Fund - II").
TARGETS = [
    "Meezan Islamic Income Fund",
    "Al Meezan Mutual Fund",
    "NBP Islamic Stock Fund",
    "NBP Savings Fund",
    "JS Islamic Fund",
]

# \b after 'th'/'td' so we never accidentally swallow '<thead>'/'<tbody>'.
_TH = re.compile(r"<th\b[^>]*>(.*?)</th>", re.S | re.I)
_TD = re.compile(r"<td\b[^>]*>(.*?)</td>", re.S | re.I)
_TR = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.S | re.I)
_TAG = re.compile(r"<[^>]+>")

_MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def _clean(s):
    """Strip tags/entities, collapse whitespace."""
    s = _TAG.sub(" ", s)
    s = s.replace("&amp;", "&").replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", s).strip()


def _iso_date(s):
    """'Jun 28, 2026' -> '2026-06-28' (leave unrecognised strings untouched)."""
    m = re.search(r"([A-Z][a-z]{2})\s+(\d{1,2}),\s+(\d{4})", s)
    if not m:
        return s.strip()
    mon, day, yr = m.group(1), int(m.group(2)), int(m.group(3))
    return f"{yr:04d}-{_MONTHS[mon]:02d}-{day:02d}"


def _num(s):
    """Parse a NAV / return cell to float; '' / 'N/A' / '-' -> None."""
    t = _clean(s).replace(",", "")
    if not re.search(r"\d", t):
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", t)
    return float(m.group(0)) if m else None


def parse_funds(html):
    """Pure parser over the MUFAP Performance Summary HTML.

    Returns ``{'as_of': 'YYYY-MM-DD', 'funds': [
        {'name', 'nav': float, 'ret_1y': float,
         'return_type': 'annualized'|'absolute'}, ...]}``.
    """
    # ---- page-level "as of" (Report Date) ----
    rd = re.search(r"Report Date:\s*([A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})", html)
    as_of = _iso_date(rd.group(1)) if rd else None

    # ---- resolve column indices BY HEADER NAME (no fixed positions) ----
    thead = re.search(r"<thead\b.*?</thead>", html, re.S | re.I)
    if not thead:
        raise ValueError("MUFAP thead not found")
    headers = [_clean(h) for h in _TH.findall(thead.group(0))]

    def col(name):
        for i, h in enumerate(headers):
            if h.lower() == name.lower():
                return i
        raise ValueError(f"header {name!r} not found in {headers!r}")

    i_cat = col("Category")
    i_name = col("Fund Name")
    i_nav = col("NAV")
    i_1y = col("365 Days")
    need = max(i_cat, i_name, i_nav, i_1y)

    # ---- scan body rows, keep target funds (first occurrence) ----
    found = {}
    for body in _TR.findall(html):
        tds = _TD.findall(body)
        if len(tds) <= need:
            continue
        name = _clean(tds[i_name])
        if name not in TARGETS or name in found:
            continue
        category = _clean(tds[i_cat])
        if "Annualized" in category:
            return_type = "annualized"
        elif "Absolute" in category:
            return_type = "absolute"
        else:
            return_type = "unknown"
        found[name] = {
            "name": name,
            "nav": _num(tds[i_nav]),
            "ret_1y": _num(tds[i_1y]),
            "return_type": return_type,
        }

    funds = [found[n] for n in TARGETS if n in found]
    if not funds:
        raise ValueError("no target funds found in MUFAP table")
    return {"as_of": as_of, "funds": funds}


def fetch():
    parsed = parse_funds(http_get(URL))
    funds = parsed["funds"]
    if len(funds) < 3:
        raise ValueError(f"only {len(funds)} MUFAP funds parsed (<3)")
    for f in funds:
        if not in_band(f["nav"], 1, 100000):
            raise ValueError(f"{f['name']} NAV out of band: {f['nav']}")
        if not in_band(f["ret_1y"], -99, 500):
            raise ValueError(f"{f['name']} 1Y out of band: {f['ret_1y']}")
        if f["return_type"] not in ("annualized", "absolute"):
            raise ValueError(f"{f['name']} unknown return_type")
    value = {f["name"]: {"nav": f["nav"], "ret_1y": f["ret_1y"],
                         "return_type": f["return_type"]} for f in funds}
    return partition(
        NAME, value, parsed["as_of"],
        "Mutual Funds Association of Pakistan (MUFAP)",
        cadence="daily", count=len(funds), source_url=URL)


if __name__ == "__main__":
    run(NAME, fetch)
