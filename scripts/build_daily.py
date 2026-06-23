#!/usr/bin/env python3
"""Build the daily *market brief* props + social caption from data.json.

Reads <root>/data.json and writes one rich snapshot (NOT a single rotating
stat) that drives all three daily renders:
  <root>/video/daily-props.json          -> Remotion --props for DailyBrief / DailyCard
  <root>/social-kit/daily/YYYY-MM-DD.md  -> LinkedIn + YouTube Short caption

The props carry the whole day at a glance: the macro board (KSE-100, PKR/USD,
gold, policy rate, inflation), the PSX + gold trend series (for the line graphs),
the top PSX 1-year movers, and an illustrative allocation (for the donut).

Stdlib only. Deterministic for a given date. Honest, non-advisory copy:
never a buy/sell call, price target, or first-hand investing claim.
Re-run: python3 scripts/build_daily.py
"""
import datetime
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOOTER = "Not financial advice · pakinvestlysis.com"
HASHTAGS = "#Pakistan #Investing #PSX #Gold #PersonalFinance"

# Mirrors video/src/schema.ts defaultColors so Studio defaults and CI renders match.
DEFAULT_COLORS = {
    "paper": "#F5F7FA",
    "ink": "#111827",
    "green": "#075E4B",
    "greenLight": "#E6F6F0",
    "gold": "#F2B94B",
    "goldPale": "#F8D98A",
    "navy": "#2854C5",
    "red": "#C24132",
    "border": "#DDE3EA",
    "muted": "#667085",
}
GOLD_DARK = "#B7791F"  # site --gold2; used for the gold trend + allocation slice

# Illustrative, clearly-labelled "balanced" split shown in the donut. Educational
# only — deliberately generic so it is never read as personalised advice.
ALLOCATION = [
    {"label": "National Savings", "pct": 30, "color": DEFAULT_COLORS["green"]},
    {"label": "Income funds", "pct": 20, "color": DEFAULT_COLORS["navy"]},
    {"label": "Equity / stocks", "pct": 30, "color": DEFAULT_COLORS["gold"]},
    {"label": "Gold", "pct": 20, "color": GOLD_DARK},
]


def grp(n, decimals=0, locale_in=True):
    """Format a number with thousands grouping for caption text.
    locale_in=True => Pakistani lakh/crore grouping (X,XX,XXX)."""
    neg = n < 0
    n = abs(n)
    if decimals == 0:
        whole = int(round(n))
        s = str(whole)
        if locale_in and len(s) > 3:
            head, tail = s[:-3], s[-3:]
            parts = []
            while len(head) > 2:
                parts.insert(0, head[-2:])
                head = head[:-2]
            if head:
                parts.insert(0, head)
            s = ",".join(parts) + "," + tail
        elif not locale_in:
            s = f"{whole:,}"
        out = s
    else:
        out = f"{n:,.{decimals}f}"
    return ("-" if neg else "") + out


def _series(hist, take, end_value=None):
    """Take the last `take` points of a {labels,values} history, optionally
    pinning the final value to the live figure so the line ends on the headline."""
    labels = hist.get("labels", []) or [""]
    values = [float(v) for v in (hist.get("values", []) or [0])]
    values = values[-take:]
    labels = labels[-take:]
    if end_value is not None and values:
        values[-1] = float(end_value)
    return {
        "values": values,
        "firstLabel": labels[0] if labels else "",
        "lastLabel": labels[-1] if labels else "",
    }


def build_props(data, date_str, session):
    macro = data.get("macro", {})
    gold = data.get("gold", {})
    stocks = data.get("stocks", []) or []

    kse100 = macro.get("kse100_level", 0)
    tola = gold.get("tola_24k", 0)

    movers = sorted(stocks, key=lambda s: s.get("chg1y", 0), reverse=True)[:4]
    movers_out = [
        {"ticker": s.get("ticker", ""), "name": s.get("name", ""), "change1y": round(s.get("chg1y", 0), 1)}
        for s in movers
    ]

    return {
        "colors": DEFAULT_COLORS,
        "audio": {"sfx": True, "volume": 1},
        "date": date_str,
        "session": session,
        "footer": FOOTER,
        "macro": {
            "kse100": kse100,
            "pkrUsd": macro.get("pkr_usd", 0),
            "sbpRate": macro.get("sbp_rate", 0),
            "inflation": macro.get("inflation_cpi", 0),
        },
        "gold": {"tola": tola, "change1y": round(gold.get("chg1y_pct", 0), 1)},
        "kseSeries": _series(data.get("kse100_history", {}), 6, end_value=kse100),
        "goldSeries": _series(gold.get("history", {}), 7, end_value=tola),
        "movers": movers_out,
        "allocation": ALLOCATION,
    }


def caption_md(date_str, p):
    m, g = p["macro"], p["gold"]
    top = p["movers"][0] if p["movers"] else {"ticker": "", "name": "", "change1y": 0}
    headline = f"Pakistan market brief · {p['session']}"
    hook = (
        f"Pakistan market brief — {date_str}: KSE-100 at {grp(m['kse100'], locale_in=False)}, "
        f"the rupee at ₨{m['pkrUsd']:.2f}/$, gold ₨{grp(g['tola'])}/tola ({g['change1y']:+.1f}% in a year)."
    )
    body = (
        f"On the board today: policy rate {m['sbpRate']:.2f}%, inflation {m['inflation']:.1f}%. "
        f"PSX's biggest 1-year mover here is {top['ticker']} ({top['name']}) at {top['change1y']:+.1f}%. "
        "The full 60-second brief walks the PSX and gold trends, the top movers, and one "
        "illustrative way to split a rupee across savings, funds, stocks and gold. "
        "Compare every option with daily data and real-return charts on the site."
    )
    yt_title = f"Pakistan market brief {date_str}: KSE-100 {grp(m['kse100'], locale_in=False)}, gold ₨{grp(g['tola'])}/tola"
    yt_desc = "Daily Pakistan market snapshot — PSX, rupee, gold, top movers. Educational, not financial advice."
    return f"""# {date_str} · {headline}

## LinkedIn
{hook}

{body}

{FOOTER} — free live tools at pakinvestlysis.com

{HASHTAGS}

## YouTube Short
**Title:** {yt_title}
**Description:** {yt_desc} pakinvestlysis.com
**Hashtags:** #Shorts {HASHTAGS}
"""


def main():
    today = datetime.date.today()
    date_str = today.strftime("%-d %b %Y")
    file_str = today.strftime("%Y-%m-%d")

    # Two runs a day: morning (~04:45 UTC, just after the PSX 9:30 PKT open) and
    # evening (~11:30 UTC, an hour after the 15:30 close). Tag the brief by
    # session so the two daily videos read as distinct posts, not duplicates.
    utc_hour = datetime.datetime.now(datetime.timezone.utc).hour
    session = "Market open" if utc_hour < 9 else "Market close"

    with open(os.path.join(ROOT, "data.json"), encoding="utf-8") as f:
        data = json.load(f)

    props = build_props(data, date_str, session)

    props_path = os.path.join(ROOT, "video", "daily-props.json")
    with open(props_path, "w", encoding="utf-8") as f:
        json.dump(props, f, ensure_ascii=False, indent=2)

    daily_dir = os.path.join(ROOT, "social-kit", "daily")
    os.makedirs(daily_dir, exist_ok=True)
    cap_path = os.path.join(daily_dir, f"{file_str}.md")
    with open(cap_path, "w", encoding="utf-8") as f:
        f.write(caption_md(date_str, props))

    print(f"  props:   {os.path.relpath(props_path, ROOT)}")
    print(f"  caption: {os.path.relpath(cap_path, ROOT)}")
    print(f"  movers:  {', '.join(m['ticker'] for m in props['movers'])}")


if __name__ == "__main__":
    main()
