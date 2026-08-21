#!/usr/bin/env python3
"""Bake dated data.json values into the static HTML placeholders.

Why: every data figure on the site was authored as `-` and filled in by JS on
load. Anything that reads the HTML without executing JS - the AdSense review
crawler, a first-pass Googlebot fetch, an LLM answer engine, a share preview -
therefore saw pages containing no rates or source dates.

This runs after build_data.py, replaces each placeholder's text with the real
value, and is idempotent (it overwrites whatever is currently there, not just
`-`). The client-side JS still runs and still wins - this only guarantees the
served HTML is never empty.

Usage: python scripts/prerender.py [--check]
  --check  exit 1 if any tracked placeholder would change (CI drift guard)
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data.json"

TOLA_GRAMS = 11.6638


# ── formatters (must match app.js formatPKR / gold.js fmtPKR exactly) ────────
def format_pkr(n) -> str:
    """Pakistani digit grouping: X,XX,XXX. Mirrors formatPKR() in app.js."""
    if n is None:
        return "-"
    neg = float(n) < 0
    raw = str(abs(int(n)) if float(n) == int(float(n)) else abs(float(n)))
    int_raw, _, dec = raw.partition(".")
    out = int_raw
    if len(int_raw) > 3:
        tail, rest = int_raw[-3:], int_raw[:-3]
        while len(rest) > 2:
            tail = rest[-2:] + "," + tail
            rest = rest[:-2]
        out = rest + "," + tail
    if dec:
        out += "." + dec
    return ("-" if neg else "") + out


def rs(n) -> str:
    return "&#8360;" + format_pkr(n) if n is not None else "-"


def pct(n) -> str:
    return f"{n}%" if n is not None else "-"


def long_date(iso: str) -> str:
    """'19 July 2026' - matches toLocaleDateString('en-PK', {day,month,year})."""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return ""
    return f"{dt.day} {dt.strftime('%B')} {dt.year}"


def data_age_label(iso: str) -> str:
    """Absolute, not relative. app.js swaps in the "updated Nh ago" form on load;
    baking a relative age into static HTML would freeze it at build time."""
    when = long_date(iso)
    return f"Data cutoff: {when}" if when else "Data cutoff unavailable"


def chg_badge(pct_val, suffix: str) -> str:
    if pct_val is None:
        return "-"
    arrow = "&#9650; " if pct_val >= 0 else "&#9660; "
    return f"{arrow}{abs(pct_val)}{suffix}"


# ── placeholder map ─────────────────────────────────────────────────────────
def build_values(d: dict) -> dict[str, str]:
    m = d.get("macro") or {}
    g = d.get("gold") or {}
    f = d.get("fuel") or {}
    updated = d.get("updated", "")

    v: dict[str, str] = {}

    # Sitewide ticker (present on all ~40 pages).
    kse = m.get("kse100_level")
    v["tk-kse"] = format_pkr(kse) if kse else "-"
    v["tk-sbp"] = pct(m.get("sbp_rate"))
    v["tk-pkr"] = "&#8360;" + str(m.get("pkr_usd")) if m.get("pkr_usd") else "-"
    v["tk-inf"] = pct(m.get("inflation_cpi"))
    if g.get("tola_24k"):
        v["tk-gold"] = rs(g["tola_24k"])

    # Homepage macro pills + hero stats.
    if kse:
        v["m-kse"] = v["h-kse"] = f"{round(kse / 1000)}K"
    v["m-sbp"] = v["h-sbp"] = v["tk-sbp"]
    v["m-pkr"] = v["h-pkr"] = v["tk-pkr"]
    v["m-inf"] = v["h-inf"] = v["tk-inf"]
    v["data-age"] = data_age_label(updated)
    if long_date(updated):
        v["hero-data-age"] = "Dataset: " + long_date(updated)

    # Homepage gold card.
    if g:
        v["g-tola24"] = rs(g.get("tola_24k"))
        v["g-tola22"] = rs(g.get("tola_22k"))
        v["g-10g24"] = rs(g.get("g10_24k"))
        v["g-gram24"] = rs(g.get("gram_24k"))
        v["gold-chg"] = chg_badge(g.get("chg1y_pct"), "% / 1yr")
        note = ("third-party local-rate reference via gold.pk" if g.get("source_type") == "local"
                else "derived international futures and PKR/USD fallback")
        v["gold-src"] = f"Collected {long_date(updated)} &#183; {note}"

        # gold-rates.html rate grid. 21K/18K are derived from the 24K rate.
        v["gr-tola24"] = v["gr-tola24-m"] = rs(g.get("tola_24k"))
        v["gr-10g24"] = rs(g.get("g10_24k"))
        v["gr-gram24"] = rs(g.get("gram_24k"))
        v["gr-tola22"] = rs(g.get("tola_22k"))
        v["gr-10g22"] = rs(g.get("g10_22k"))
        v["gr-gram22"] = rs(g.get("gram_22k"))
        if g.get("tola_24k"):
            for k in (21, 18):
                tola = round(g["tola_24k"] * k / 24)
                v[f"gr-tola{k}"] = rs(tola)
                v[f"gr-10g{k}"] = rs(round(tola / TOLA_GRAMS * 10))
                v[f"gr-gram{k}"] = rs(round(tola / TOLA_GRAMS))
        v["gr-chg"] = chg_badge(g.get("chg1y_pct"), "% over 1 year")
        src_note = ("Source: gold.pk, a third-party local-rate publisher."
                    if g.get("source_type") == "local"
                    else "Source: a derived international futures and PKR/USD fallback.")
        v["gr-source"] = (
            f"Collected {long_date(updated)}. {src_note} This is not a dealer quote. "
            "21K and 18K are derived from 24K (&#215;87.5% and &#215;75%); shop prices, "
            "spreads and making charges differ."
        )
        v["gold-asof"] = "Collected " + long_date(updated)

    # Homepage fuel card.
    if f:
        px = lambda x: "&#8360;" + f"{float(x):.2f}" if x is not None else "-"
        v["f-petrol"] = px(f.get("petrol"))
        v["f-hsd"] = px(f.get("hsd"))
        v["f-kero"] = px(f.get("kerosene"))
        v["f-ldo"] = px(f.get("ldo"))
        if f.get("asof"):
            v["fuel-asof"] = "w.e.f " + f["asof"]
            v["fuel-src"] = "OGRA-notified retail rates &#183; effective " + f["asof"]

    return {k: val for k, val in v.items() if val and val != "-"}


def apply(html: str, values: dict[str, str]) -> tuple[str, int]:
    """Replace the text node of every `id="<key>"` element we have a value for."""
    hits = 0

    def sub_one(el_id: str, text: str, src: str) -> tuple[str, int]:
        # Matches `id="x" ...>OLD<`. The [^<]* keeps us to text-only elements,
        # so a container with child tags is left alone rather than clobbered.
        pattern = re.compile(r'(id="' + re.escape(el_id) + r'"[^>]*>)[^<]*(?=<)')
        new, n = pattern.subn(lambda mo: mo.group(1) + text, src)
        return new, n

    for el_id, text in values.items():
        html, n = sub_one(el_id, text, html)
        hits += n
    return html, hits


def main() -> int:
    check = "--check" in sys.argv
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    values = build_values(data)

    targets = sorted(
        p for p in ROOT.glob("**/*.html")
        if "tests/fixtures" not in str(p)
        and "node_modules" not in str(p)
        and "social-kit" not in str(p)
    )

    drift, total = [], 0
    for path in targets:
        src = path.read_text(encoding="utf-8")
        out, hits = apply(src, values)
        if out != src:
            drift.append(path.relative_to(ROOT))
            total += hits
            if not check:
                path.write_text(out, encoding="utf-8")

    if check:
        if drift:
            print(f"prerender drift in {len(drift)} file(s):")
            for p in drift:
                print("  ", p)
            return 1
        print("prerender: HTML in sync with data.json")
        return 0

    print(f"prerender: filled {total} placeholder(s) across {len(drift)} file(s)")
    for p in drift:
        print("  ", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
