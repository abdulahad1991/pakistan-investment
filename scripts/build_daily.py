#!/usr/bin/env python3
"""Build the daily stat-of-the-day card props + social caption from data.json.

Reads <root>/data.json, picks ONE metric by day-of-year rotation, and writes:
  <root>/video/daily-props.json          -> Remotion --props input for StatCard
  <root>/social-kit/daily/YYYY-MM-DD.md  -> LinkedIn + YouTube Short caption

Stdlib only. Deterministic for a given date. Honest, non-advisory copy:
never a buy/sell call, price target, or first-hand investing claim.
Re-run: python3 scripts/build_daily.py
"""
import datetime
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOOTER = "Not financial advice · pakinvestlysis.com"

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
HASHTAGS = "#Pakistan #Investing #PSX #Finance #PersonalFinance"


def grp(n, decimals=0, locale_in=True):
    """Format a number as a string with thousands grouping for caption text.
    locale_in=True => Pakistani lakh/crore grouping (X,XX,XXX)."""
    neg = n < 0
    n = abs(n)
    whole = int(round(n)) if decimals == 0 else None
    if decimals == 0:
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


def _props(**over):
    p = {
        "colors": DEFAULT_COLORS,
        "audio": {"sfx": True, "volume": 1},
        "durationInFrames": 300,
        "kicker": "",
        "label": "",
        "value": 0,
        "valuePrefix": "",
        "valueSuffix": "",
        "decimals": 0,
        "locale": "en-US",
        "trend": "flat",
        "changeLabel": "",
        "asOf": "",
        "takeaway": "",
        "footer": FOOTER,
    }
    p.update(over)
    return p


def _find_nss(data, name):
    for c in data.get("national_savings", []):
        if c.get("name") == name:
            return c
    return None


def build_metrics(data, as_of):
    """Return the rotation list. Order is fixed: gold, kse100, policy, fx, nss."""
    macro = data.get("macro", {})
    gold = data.get("gold", {})
    metrics = []

    # 0 — Gold per tola (24k)
    chg = gold.get("chg1y_pct", 0.0)
    gtrend = "up" if chg >= 0 else "down"
    metrics.append({
        "key": "gold",
        "props": _props(
            kicker="Gold · 24k per tola",
            label="Gold price today",
            value=gold.get("tola_24k", 0),
            valuePrefix="₨",
            decimals=0,
            locale="en-IN",
            trend=gtrend,
            changeLabel=f"{chg:+.1f}% · 1 year",
            asOf=as_of,
            takeaway="A hedge against a weak rupee — not a get-rich-quick play.",
        ),
        "caption": {
            "headline": "Gold today",
            "hook": f"Gold (24k) is ₨{grp(gold.get('tola_24k', 0))} per tola in Pakistan today.",
            "body": (
                f"That's {chg:+.1f}% over the past year. Gold tends to hold value when "
                "the rupee slips — useful as a small hedge, not a quick flip. Track the "
                "live rate and a plain-language history on the site."
            ),
            "yt_title": f"Gold price today: ₨{grp(gold.get('tola_24k', 0))}/tola ({chg:+.1f}% in a year)",
            "yt_desc": "Daily Pakistan gold rate. Educational, not financial advice.",
        },
    })

    # 1 — KSE-100 (trend from the last two history points)
    hist = data.get("kse100_history", {}).get("values", [])
    ktrend, kchg = "flat", ""
    if len(hist) >= 2 and hist[-2]:
        pct = (hist[-1] - hist[-2]) / hist[-2] * 100
        ktrend = "up" if pct >= 0 else "down"
        kchg = f"{pct:+.1f}% · recent"
    metrics.append({
        "key": "kse100",
        "props": _props(
            kicker="PSX · KSE-100 index",
            label="The market today",
            value=macro.get("kse100_level", 0),
            decimals=0,
            locale="en-US",
            trend=ktrend,
            changeLabel=kchg or "index level",
            asOf=as_of,
            takeaway="Stocks are a long-term game — zoom out before you react.",
        ),
        "caption": {
            "headline": "KSE-100 today",
            "hook": f"The KSE-100 sits at {grp(macro.get('kse100_level', 0), locale_in=False)} today.",
            "body": (
                "Day-to-day moves are noise; the long-run trend is what compounds. "
                "Compare index history against gold and savings on the site before deciding "
                "where a rupee should go."
            ),
            "yt_title": f"KSE-100 today: {grp(macro.get('kse100_level', 0), locale_in=False)}",
            "yt_desc": "Daily PSX KSE-100 snapshot. Educational, not financial advice.",
        },
    })

    # 2 — SBP policy rate
    direction = macro.get("sbp_direction", "Holding")
    dl = direction.lower()
    ptrend = "up" if ("hik" in dl or "rais" in dl) else "down" if "cut" in dl else "flat"
    metrics.append({
        "key": "policy",
        "props": _props(
            kicker="SBP · policy rate",
            label="The benchmark rate",
            value=macro.get("sbp_rate", 0),
            valueSuffix="%",
            decimals=2,
            locale="en-US",
            trend=ptrend,
            changeLabel=direction,
            asOf=as_of,
            takeaway="Savings certificate and money-market yields track this rate.",
        ),
        "caption": {
            "headline": "SBP policy rate",
            "hook": f"State Bank's policy rate is {macro.get('sbp_rate', 0):.2f}% ({direction.lower()}).",
            "body": (
                "This sets the tone for what your savings, T-bills and money-market funds pay. "
                "When it moves, fixed-income returns follow. See how today's rate compares to "
                "recent history on the site."
            ),
            "yt_title": f"SBP policy rate: {macro.get('sbp_rate', 0):.2f}% ({direction})",
            "yt_desc": "Daily SBP policy rate. Educational, not financial advice.",
        },
    })

    # 3 — PKR / USD (no daily history stored -> neutral framing)
    metrics.append({
        "key": "fx",
        "props": _props(
            kicker="Rupee · USD",
            label="The exchange rate",
            value=macro.get("pkr_usd", 0),
            valuePrefix="₨",
            decimals=2,
            locale="en-US",
            trend="flat",
            changeLabel="per US dollar",
            asOf=as_of,
            takeaway="A weaker rupee quietly raises the cost of imported everything.",
        ),
        "caption": {
            "headline": "PKR/USD today",
            "hook": f"The rupee is ₨{macro.get('pkr_usd', 0):.2f} to the US dollar today.",
            "body": (
                "The exchange rate shapes inflation, fuel and the real value of your savings. "
                "Worth a glance before parking money in foreign assets. Live rate on the site."
            ),
            "yt_title": f"PKR to USD today: ₨{macro.get('pkr_usd', 0):.2f}",
            "yt_desc": "Daily PKR/USD rate. Educational, not financial advice.",
        },
    })

    # 4 — National Savings (Behbood rate)
    beh = _find_nss(data, "Behbood Savings Certificate") or {}
    metrics.append({
        "key": "nss",
        "props": _props(
            kicker="National Savings · Behbood",
            label="A fixed, govt-backed rate",
            value=beh.get("rate", 0),
            valueSuffix="%",
            decimals=2,
            locale="en-US",
            trend="flat",
            changeLabel="3-yr · paid monthly",
            asOf=as_of,
            takeaway="Safe and fixed — but it's for widows and seniors (60+) only.",
        ),
        "caption": {
            "headline": "Behbood Savings",
            "hook": f"Behbood Savings Certificates pay {beh.get('rate', 0):.2f}% — government-backed and fixed.",
            "body": (
                "Among the highest National Savings rates, paid monthly over 3 years. Note the "
                "catch: eligibility is widows and senior citizens (60+) only. Compare every "
                "savings option side by side on the site."
            ),
            "yt_title": f"Behbood Savings rate: {beh.get('rate', 0):.2f}% (who qualifies)",
            "yt_desc": "Daily National Savings snapshot. Educational, not financial advice.",
        },
    })

    return metrics


def pick(metrics, yday):
    return metrics[yday % len(metrics)]


def caption_md(date_str, metric):
    c = metric["caption"]
    return f"""# {date_str} · {c['headline']}

## LinkedIn
{c['hook']}

{c['body']}

{FOOTER} — free live tools at pakinvestlysis.com

{HASHTAGS}

## YouTube Short
**Title:** {c['yt_title']}
**Description:** {c['yt_desc']} pakinvestlysis.com
**Hashtags:** #Shorts {HASHTAGS}
"""


def main():
    today = datetime.date.today()
    as_of = today.strftime("%-d %b %Y")
    date_str = today.strftime("%Y-%m-%d")

    with open(os.path.join(ROOT, "data.json"), encoding="utf-8") as f:
        data = json.load(f)

    metrics = build_metrics(data, as_of)
    metric = pick(metrics, today.timetuple().tm_yday)

    props_path = os.path.join(ROOT, "video", "daily-props.json")
    with open(props_path, "w", encoding="utf-8") as f:
        json.dump(metric["props"], f, ensure_ascii=False, indent=2)

    daily_dir = os.path.join(ROOT, "social-kit", "daily")
    os.makedirs(daily_dir, exist_ok=True)
    cap_path = os.path.join(daily_dir, f"{date_str}.md")
    with open(cap_path, "w", encoding="utf-8") as f:
        f.write(caption_md(date_str, metric))

    print(f"  metric:  {metric['key']}")
    print(f"  props:   {os.path.relpath(props_path, ROOT)}")
    print(f"  caption: {os.path.relpath(cap_path, ROOT)}")


if __name__ == "__main__":
    main()
