"""Pakistan retail fuel prices — OGRA-notified rates (Petrol/HSD/Kerosene/LDO).

Government-set, uniform national rates. Historically revised fortnightly (1st /
16th); as of mid-2026 they move on a rolling ~daily/weekly basis with the oil
market, which is why this is a `daily`-cadence fetcher scraped every run rather
than a hand-curated carry-forward.

No official machine-readable feed exists (OGRA publishes notification PDFs, the
Finance Division a press release), so we scrape, with a crawl_first failover so
one site's redesign can't freeze the number (the SBP-2026-07 lesson):

  primary   PakWheels  — clean HTML table (Fuel | Old | New | Difference),
                         carries all four products + a "w.e.f <date>" stamp.
  fallback  PetrolPrice.com.pk — lead sentence gives the two headline fuels
                         (petrol + HSD) + effective date; a degraded but live
                         backstop. May lag PakWheels by a revision.
  (then)    base.run()  carries the prior partition forward flagged ok=False.

Both parsers are pure (unit-tested against captured fixtures in tests/fixtures/);
fetch() wraps them with http_get + a sanity band and returns a provenance
partition {petrol, hsd, kerosene, ldo} in PKR per litre.
"""
import re

from .base import http_get, partition, crawl_first, in_band, run

NAME = "petrol"
PAKWHEELS_URL = "https://www.pakwheels.com/petroleum-prices-in-pakistan"
PETROLPRICE_URL = "https://petrolprice.com.pk/"

# The four products the site shows, in display order.
FUELS = ("petrol", "hsd", "kerosene", "ldo")

_MONTHS = {}
for _i, _full in enumerate(
    ["january", "february", "march", "april", "may", "june",
     "july", "august", "september", "october", "november", "december"], 1):
    _MONTHS[_full] = _i
    _MONTHS[_full[:3]] = _i


def _to_float(s):
    return float(s.replace(",", "").strip())


def _iso(day, month_name, year):
    """('18','July','2026') -> '2026-07-18'; returns None on an unknown month."""
    mon = _MONTHS.get(str(month_name).strip().lower())
    if not mon:
        return None
    return f"{int(year):04d}-{mon:02d}-{int(day):02d}"


def _classify(label):
    """Map a fuel-row label to our key, or None to skip (LPG, HOBC, CNG …).

    Checked most-specific first so 'Light Speed/Diesel Oil' resolves to LDO and
    'High Speed Diesel' to HSD before the bare 'petrol'/'diesel' catch-alls."""
    lab = label.lower()
    if "kerosene" in lab:
        return "kerosene"
    if "high speed" in lab or "high-speed" in lab or "hsd" in lab:
        return "hsd"
    if ("light" in lab and "diesel" in lab) or "ldo" in lab:
        return "ldo"
    if "petrol" in lab:               # 'Petrol (Super)' — after octane/LPG fall through
        return "petrol"
    return None


def _wef_date(html):
    m = re.search(r"w\.?e\.?f\.?\s*(\d{1,2})[-\s]([A-Za-z]+)[-\s](\d{4})", html, re.I)
    return _iso(*m.groups()) if m else None


def parse_pakwheels(html):
    """PakWheels price table -> {fuel: PKR/L, ..., as_of?}. Pure string->value.

    Reads the *New Price* column (the current rate = last 'PKR <n>' in each row)
    for every fuel row across the page, keying by label. Falls back to the hero
    sentence for petrol+HSD if the table markup changes. Raises if neither the
    petrol nor the HSD rate can be found."""
    out = {}
    for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", html, re.S | re.I):
        cells = re.findall(r"<td\b[^>]*>(.*?)</td>", row, re.S | re.I)
        if not cells:
            continue
        label = re.sub(r"<[^>]+>", "", cells[0]).strip()
        prices = re.findall(r"PKR\s*([\d,]+(?:\.\d+)?)", row, re.I)
        key = _classify(label)
        if key and prices and key not in out:
            out[key] = _to_float(prices[-1])   # New Price column

    if "petrol" not in out or "hsd" not in out:
        hero = re.search(
            r"Petrol Price in Pakistan is Rs\.?\s*([\d,]+(?:\.\d+)?)\s*/?\s*Ltr"
            r".*?High Speed Diesel is Rs\.?\s*([\d,]+(?:\.\d+)?)",
            html, re.I | re.S)
        if hero:
            out.setdefault("petrol", _to_float(hero.group(1)))
            out.setdefault("hsd", _to_float(hero.group(2)))

    if "petrol" not in out or "hsd" not in out:
        raise ValueError("pakwheels: petrol/HSD rate not found on page")
    date = _wef_date(html)
    if date:
        out["as_of"] = date
    return out


def parse_petrolprice(html):
    """PetrolPrice.com.pk fallback -> {petrol, hsd, kerosene?, ldo?, as_of?}.

    The lead sentence carries the two headline fuels + the effective date;
    kerosene/LDO are picked up from the mini-rate tiles when present. Raises if
    the petrol/HSD lead can't be read."""
    lead = re.search(
        r"petrol price in Pakistan today is PKR\s*([\d,]+(?:\.\d+)?)\s*per litre"
        r"\s*and\s*High-?Speed Diesel is PKR\s*([\d,]+(?:\.\d+)?)",
        html, re.I)
    if not lead:
        raise ValueError("petrolprice: lead petrol/HSD sentence not found")
    out = {"petrol": _to_float(lead.group(1)), "hsd": _to_float(lead.group(2))}
    for key, name in (("kerosene", "Kerosene"), ("ldo", "LDO")):
        tile = re.search(rf"<span>\s*{name}\s*</span>\s*<strong>\s*([\d,]+(?:\.\d+)?)",
                         html, re.I)
        if tile:
            out[key] = _to_float(tile.group(1))
    eff = re.search(r"effective from (\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(\d{4})",
                    html, re.I)
    if eff:
        date = _iso(*eff.groups())
        if date:
            out["as_of"] = date
    return out


def _value(parsed):
    """Keep only the four display fuels, rounded to paisa; drop as_of/extras."""
    return {k: round(parsed[k], 2) for k in FUELS if parsed.get(k) is not None}


def _guard(value):
    for k, v in value.items():
        if not in_band(v, 40, 2000):   # PKR/L — well outside any real fuel price
            raise ValueError(f"fuel {k} out of sanity band: {v}")


def _from_pakwheels():
    parsed = parse_pakwheels(http_get(PAKWHEELS_URL))
    value = _value(parsed)
    _guard(value)
    return partition(NAME, value, parsed.get("as_of"),
                     "PakWheels (OGRA-notified rates)", cadence="daily",
                     metric="retail fuel price", unit="PKR/L",
                     source_url=PAKWHEELS_URL)


def _from_petrolprice():
    parsed = parse_petrolprice(http_get(PETROLPRICE_URL))
    value = _value(parsed)
    _guard(value)
    return partition(NAME, value, parsed.get("as_of"),
                     "PetrolPrice.com.pk (OGRA)", cadence="daily",
                     metric="retail fuel price", unit="PKR/L",
                     source_url=PETROLPRICE_URL)


def fetch():
    return crawl_first(NAME, [
        ("pakwheels", _from_pakwheels),
        ("petrolprice.com.pk", _from_petrolprice),
    ])


if __name__ == "__main__":
    run(NAME, fetch)
