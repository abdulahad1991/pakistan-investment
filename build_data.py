#!/usr/bin/env python3
"""Merge the per-fetcher partitions into the single live data.json.

The fetchers (fetchers/*.py) each write a provenance-wrapped partition to
data/partitions/<name>.json. This step OVERLAYS those live values onto the
curated data.json — preserving all the hand-authored content (wizard copy,
stock names/sectors, fund metadata, savings verdicts) and only replacing the
fields a fetcher owns. It then:

  * derives nothing the fetchers can't (units already consistent at source),
  * asserts internal consistency (e.g. gold gram == tola / 11.6638),
  * writes a data_health block + per-field _asof so the UI can render
    'as of <date>' and a 'data delayed' badge when a source goes stale,

so a silent parse miss can never masquerade as fresh, current data.

A MISSING partition (a fetcher not run this cadence) leaves the existing
data.json value untouched — the overlay is additive, never destructive.
"""
import json
import re
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PART_DIR = ROOT / "data" / "partitions"
DATA_JSON = ROOT / "data.json"

# How old (days) a source's own as_of may be before we flag it 'delayed'.
STALE_DAYS = {
    "intraday": 5,    # Fri close + a long weekend/holiday is normal
    "daily": 5,
    "weekly": 12,
    "monthly": 70,    # monthly data is always ~1 month in arrears (May CPI is
                      # the latest until ~1 Jul); only flag once M-2 goes missing
    "event": 240,     # policy/savings/GDP move rarely
}

# data.json scheme name -> CDNS-published name, where they differ.
SAVINGS_ALIAS = {"CDNS Savings Account": "Savings Account"}

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def _to_date(s):
    """Best-effort parse of the many as_of shapes into a date, else None."""
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    # ISO YYYY-MM-DD
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        try:
            return datetime.date(int(m[1]), int(m[2]), int(m[3]))
        except ValueError:
            return None
    # YYYY-MM  (use the 1st)
    m = re.fullmatch(r"(\d{4})-(\d{2})", s)
    if m:
        return datetime.date(int(m[1]), int(m[2]), 1)
    # DD-MM-YYYY (CDNS effective date)
    m = re.fullmatch(r"(\d{1,2})-(\d{1,2})-(\d{4})", s)
    if m:
        try:
            return datetime.date(int(m[3]), int(m[2]), int(m[1]))
        except ValueError:
            return None
    # 'June 18, 2026' / 'Jun 23, 2026'  (time, if any, ignored)
    m = re.search(r"([A-Za-z]{3,9})\s+(\d{1,2}),\s+(\d{4})", s)
    if m and m[1][:3].lower() in _MONTHS:
        try:
            return datetime.date(int(m[3]), _MONTHS[m[1][:3].lower()], int(m[2]))
        except ValueError:
            return None
    # 'FY2025-26'  -> fiscal-year end (30 Jun of the later year)
    m = re.fullmatch(r"FY?\s*(\d{4})-(\d{2,4})", s)
    if m:
        end = m[2]
        yr = int(end) if len(end) == 4 else int(str(m[1])[:2] + end)
        return datetime.date(yr, 6, 30)
    return None


def _load_partitions():
    parts = {}
    if PART_DIR.exists():
        for f in sorted(PART_DIR.glob("*.json")):
            try:
                parts[f.stem] = json.loads(f.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                pass
    return parts


def _staleness(part, today):
    """(is_stale, age_days|None) for a partition given its as_of + cadence."""
    cad = part.get("cadence", "daily")
    limit = STALE_DAYS.get(cad, 7)
    d = _to_date(part.get("as_of"))
    if d is None:
        # No data-date to judge — lean on the ok flag only.
        return (not part.get("ok", True), None)
    age = (today - d).days
    return (age > limit or not part.get("ok", True), age)


def _fmt(s):
    """Normalise any as_of shape to one friendly, consistent display string.

    'YYYY-MM' / 'FY..' -> 'May 2026'; dated values -> '18 Jun 2026'. Unparseable
    strings pass through unchanged.
    """
    d = _to_date(s)
    if not d:
        return s
    if isinstance(s, str) and re.fullmatch(r"\d{4}-\d{2}|FY?\s*\d{4}-\d{2,4}", s.strip()):
        return d.strftime("%b %Y")
    return f"{d.day} {d.strftime('%b %Y')}"


# as_of keys this build owns — popped before re-write so stale/duplicate
# variants (e.g. an earlier '<field>_bn_usd_asof') can never accumulate.
_ASOF_KEYS = ["inflation_cpi_asof", "fx_reserves_asof", "pkr_usd_asof",
              "kse100_asof", "sbp_rate_asof", "gdp_growth_asof", "stocks_asof",
              "fx_reserves_bn_usd_asof", "kse100_level_asof"]


def merge():
    data = json.loads(DATA_JSON.read_text(encoding="utf-8"))
    parts = _load_partitions()
    macro = data.setdefault("macro", {})
    today = datetime.date.today()
    applied = []

    def part(name):
        p = parts.get(name)
        if p and p.get("value") is not None:
            applied.append(name)
            return p
        return None

    # Drop any as_of keys this build owns so duplicates can't accumulate.
    for k in _ASOF_KEYS:
        macro.pop(k, None)

    # ── macro scalars ────────────────────────────────────────────────
    if (p := part("inflation")):
        macro["inflation_cpi"] = p["value"]
        macro["inflation_cpi_asof"] = _fmt(p.get("as_of"))
    if (p := part("reserves")):
        v = p["value"]
        macro["fx_reserves_bn_usd"] = v.get("sbp_bn")
        macro["fx_reserves_total_bn_usd"] = v.get("total_bn")
        macro["fx_reserves_asof"] = _fmt(p.get("as_of"))
    if (p := part("policy")):
        v = p["value"]
        macro["sbp_rate"] = v.get("rate")
        if p.get("sbp_direction"):
            macro["sbp_direction"] = p["sbp_direction"]
        macro["sbp_floor"] = v.get("floor")
        macro["sbp_ceiling"] = v.get("ceiling")
    if (p := part("forex")):
        macro["pkr_usd"] = round(p["value"]["interbank"], 2)
        macro["pkr_usd_asof"] = _fmt(p.get("as_of"))
        # Provenance for the display layer: a crawl_first fallback tagged
        # `approx` means the authoritative SBP interbank M2M rate was
        # unreachable and this is a third-party REFERENCE rate. Surface it so
        # the UI never attributes a non-SBP number to "SBP interbank". An
        # `sbp-home` recrawl is still authoritative SBP, so only `approx` (the
        # er-api tier) trips this — not `failover` in general.
        macro["pkr_usd_approx"] = bool(p.get("approx"))
        macro["pkr_usd_source"] = p.get("source")
    if (p := part("kse")):
        v = p["value"]
        macro["kse100_level"] = round(v["level"])
        macro["kse100_asof"] = _fmt(p.get("as_of"))
        macro["kse100_change"] = v.get("change")
        macro["kse100_change_pct"] = v.get("change_pct")
        if v.get("history"):
            data["kse100_history"] = v["history"]
    if (p := part("macro")):
        v = p["value"]
        if v.get("gdp_growth") is not None:
            macro["gdp_growth_pct"] = v.get("gdp_growth")
        macro["gdp_growth_fy"] = v.get("gdp_fy")
        imf = v.get("imf") or {}
        if imf:
            macro["imf_status"] = (
                f"{imf.get('status', 'Active')} — {imf.get('programme', '')}; "
                f"{imf.get('last_review', '')} "
                f"(~${imf.get('disbursed_usd_bn', '?')}B disbursed)")

    # ── national savings (match by scheme name) ──────────────────────
    # The savings partition value IS the flat {scheme_name: rate} map, and its
    # effective date is the partition as_of. data.json names one scheme
    # "CDNS Savings Account" where CDNS publishes plain "Savings Account".
    if (p := part("savings")):
        schemes = p["value"] if isinstance(p["value"], dict) else {}
        eff = p.get("effective") or p.get("as_of")
        for s in data.get("national_savings", []):
            key = SAVINGS_ALIAS.get(s["name"], s["name"])
            r = schemes.get(key)
            if r is not None:
                s["rate"] = r
                if eff:
                    s["rate_effective"] = eff

    # ── mutual funds (match by fund name) ────────────────────────────
    if (p := part("funds")):
        fmap = p["value"]
        for f in data.get("mutual_funds", []):
            row = fmap.get(f["name"])
            if row:
                f["ret_1y"] = row.get("ret_1y", f.get("ret_1y"))
                f["nav"] = row.get("nav")
                f["return_type"] = row.get("return_type")

    # ── gold ─────────────────────────────────────────────────────────
    if (p := part("gold")):
        g = data.setdefault("gold", {})
        g.update(p["value"])
        if p.get("as_of"):
            g["asof"] = p["as_of"]

    # ── fuel (OGRA-notified retail petrol/HSD/kerosene/LDO, PKR/L) ────
    if (p := part("petrol")):
        fuel = data.setdefault("fuel", {})
        fuel.update(p["value"])                       # petrol/hsd/kerosene/ldo
        if p.get("as_of"):
            fuel["asof"] = _fmt(p.get("as_of"))
        fuel["source"] = p.get("source")

    # ── stocks: prices for all, fundamentals where enriched ──────────
    if (p := part("stocks")):
        prices = p["value"].get("prices", {})
        heads = p["value"].get("headlines", {})
        for s in data.get("stocks", []):
            sym = (s.get("ticker") or "").strip().upper()
            row = prices.get(sym)
            if row and row.get("price") is not None:
                s["price"] = row["price"]
                s["chg"] = row.get("pct")          # daily % change
            h = heads.get(sym)
            if h:
                if h.get("pe_ttm") is not None:
                    s["pe"] = h["pe_ttm"]
                if h.get("eps") is not None:
                    s["eps"] = h["eps"]
                if h.get("wk52_high") is not None:
                    s["hi52"] = h["wk52_high"]
                if h.get("wk52_low") is not None:
                    s["lo52"] = h["wk52_low"]
                if h.get("chg1y") is not None:
                    s["chg1y"] = h["chg1y"]
        if p.get("as_of"):
            # company quote stamp like 'Wed, Jun 24, 2026 3:49 PM' -> '24 Jun 2026'
            macro["stocks_asof"] = _fmt(p["as_of"]) if _to_date(p["as_of"]) else p["as_of"]

    # ── dividends: ttm cash + yield for stocks that pay ──────────────
    if (p := part("dividends")):
        dmap = p["value"]
        for s in data.get("stocks", []):
            sym = (s.get("ticker") or "").strip().upper()
            row = dmap.get(sym)
            if row and row.get("ttm_cash") is not None:
                s["div"] = row["ttm_cash"]
                px = s.get("price")
                s["yield"] = round(row["ttm_cash"] / px * 100, 2) if px else 0
                s["div_latest"] = row.get("latest_cash")
                s["div_asof"] = row.get("announce")

    # ── consistency asserts (fail loud, don't ship garbage) ──────────
    _assert_consistency(data)

    # ── data_health: per-source freshness for the UI + ops ───────────
    health = {}
    for name, pp in parts.items():
        stale, age = _staleness(pp, today)
        health[name] = {
            "ok": bool(pp.get("ok", False)),
            "as_of": pp.get("as_of"),
            "source": pp.get("source"),
            "cadence": pp.get("cadence"),
            "stale": stale,
            "age_days": age,
            "last_error": pp.get("last_error"),
        }
        # Failover provenance: which source in the crawl chain actually served
        # this value, and (when a non-primary won) that the primary was down.
        if pp.get("via"):
            health[name]["via"] = pp["via"]
        if pp.get("failover"):
            health[name]["failover"] = True
            health[name]["primary_errors"] = pp.get("primary_errors")
    data["data_health"] = health
    data["updated"] = datetime.datetime.now(
        datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    DATA_JSON.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    stale_now = [n for n, h in health.items() if h["stale"]]
    print(f"  merged {len(applied)} partitions: {', '.join(sorted(applied)) or 'none'}")
    if stale_now:
        print(f"  ⚠ STALE/degraded: {', '.join(sorted(stale_now))}")
    return data


def _assert_consistency(data):
    """Cheap internal-consistency checks. Raise on anything impossible so a
    parse error fails the build instead of silently shipping garbage."""
    m = data.get("macro", {})
    if "inflation_cpi" in m:
        assert 0 < m["inflation_cpi"] < 60, f"inflation insane: {m['inflation_cpi']}"
    if "sbp_rate" in m:
        assert 3 <= m["sbp_rate"] <= 30, f"policy rate insane: {m['sbp_rate']}"
    if "pkr_usd" in m:
        assert 150 < m["pkr_usd"] < 600, f"PKR/USD insane: {m['pkr_usd']}"
    if "kse100_level" in m:
        assert 50_000 < m["kse100_level"] < 500_000, f"KSE insane: {m['kse100_level']}"
    g = data.get("gold", {})
    if g.get("tola_24k") and g.get("gram_24k"):
        expect = round(g["tola_24k"] / 11.6638)
        assert abs(g["gram_24k"] - expect) <= 2, \
            f"gold gram!=tola/11.6638: {g['gram_24k']} vs {expect}"
    for s in data.get("national_savings", []):
        assert 3 <= s["rate"] <= 25, f"NSS {s['name']} rate insane: {s['rate']}"
    f = data.get("fuel", {})
    for k in ("petrol", "hsd", "kerosene", "ldo"):
        if f.get(k) is not None:
            assert 40 <= f[k] <= 2000, f"fuel {k} insane: {f[k]}"


if __name__ == "__main__":
    merge()
