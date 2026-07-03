#!/usr/bin/env python3
"""Build the daily *market brief* props + social caption from data.json.

Reads <root>/data.json and writes one rich snapshot (NOT a single rotating
stat) that drives all three daily renders:
  <root>/video/daily-props.json          -> Remotion --props for DailyBrief / DailyCard
  <root>/social-kit/daily/YYYY-MM-DD.md  -> LinkedIn + YouTube Short caption

The props carry the whole day at a glance: the macro board (KSE-100, PKR/USD,
gold, policy rate, inflation), the PSX + gold trend series (for the line graphs),
the top PSX 1-year movers, and an illustrative allocation (for the donut).

Also emitted (all optional, graceful when data is missing):
  * `headline` prop — the day's biggest % move (KSE-100 / gold / USDPKR) as a
    hook card: {"text","kicker","sub"} per the Remotion contract.
  * a `metrics` block in the social-kit JSON so the NEXT run (and the weekly
    review) can derive day/week changes without re-parsing copy text.

No narration: the briefs are music/SFX only (the robotic TTS voiceover was
removed 2026-07-03; blog explainers keep theirs — see build_explainer.py).

Stdlib only. Deterministic for a given date. Honest, non-advisory copy: never
a buy/sell call, price target, or first-hand investing claim.
Re-run: python3 scripts/build_daily.py
"""
import datetime
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOOTER = "Not financial advice · pakinvestlysis.com"
HASHTAGS = "#Pakistan #Investing #PSX #Gold #PersonalFinance"
# YouTube keyword tags (the API takes a flat list, no '#').
YT_TAGS = ["Pakistan", "investing", "PSX", "KSE-100", "gold",
           "mutual funds", "national savings", "personal finance"]
YT_TITLE_MAX = 100  # YouTube hard limit on snippet.title

# Headline (hook) selection: a move under this |%| on every metric = "FLAT DAY".
FLAT_EPS = 0.15

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


# ---------------------------------------------------------------------------
# Headline (hook) selection — pure, never raises.
# ---------------------------------------------------------------------------
# Fallback parsers for pre-`metrics` social-kit payloads: we control both the
# hook format and these regexes, so this only ever parses our own output.
_RX_KSE = re.compile(r"KSE-100 at ([\d,]+)")
_RX_GOLD = re.compile(r"gold ₨([\d,]+)/tola")
_RX_USD = re.compile(r"₨([\d.]+)/\$")


def _short_date(date_str):
    """'2 Jul 2026' -> '2 Jul' (drop a trailing 4-digit year token)."""
    parts = str(date_str or "").split()
    if len(parts) >= 2 and parts[-1].isdigit() and len(parts[-1]) == 4:
        return " ".join(parts[:-1])
    return str(date_str or "")


def _metrics_from_payload(payload):
    """Raw {kse100, gold_tola, pkr_usd} numbers from a prior day's social-kit
    JSON. Prefers the structured `metrics` block (emitted since 2026-07-03),
    falls back to regex-parsing our own hook copy for older files."""
    if not isinstance(payload, dict):
        return {}
    met = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
    hook = str(payload.get("hook", "") or "")
    out = {}
    for key, rx in (("kse100", _RX_KSE), ("gold_tola", _RX_GOLD), ("pkr_usd", _RX_USD)):
        v = met.get(key)
        if not v:
            m = rx.search(hook)
            v = m.group(1).replace(",", "") if m else None
        try:
            v = float(v)
        except (TypeError, ValueError):
            v = None
        if v:
            out[key] = v
    return out


def day_candidates(data, prev_props=None):
    """Day-change candidates [{metric, value, pct}] for KSE-100 / gold / USDPKR.
    KSE uses data.json's own kse100_change_pct; gold + USD (no day-change field
    and only monthly history in data.json) diff against the previous trading
    day's social-kit payload. Underivable metrics are skipped; never raises."""
    try:
        macro = data.get("macro") or {}
        gold = data.get("gold") or {}
        prev = _metrics_from_payload(prev_props)
        out = []

        kse = macro.get("kse100_level") or 0
        pct = macro.get("kse100_change_pct")
        if pct is None and kse and prev.get("kse100"):
            pct = (kse - prev["kse100"]) / prev["kse100"] * 100
        if kse and pct is not None:
            out.append({"metric": "kse", "value": kse, "pct": float(pct)})

        tola = gold.get("tola_24k") or 0
        if tola and prev.get("gold_tola"):
            out.append({"metric": "gold", "value": tola,
                        "pct": (tola - prev["gold_tola"]) / prev["gold_tola"] * 100})

        usd = macro.get("pkr_usd") or 0
        if usd and prev.get("pkr_usd"):
            out.append({"metric": "usd", "value": usd,
                        "pct": (usd - prev["pkr_usd"]) / prev["pkr_usd"] * 100})
        return out
    except Exception as e:  # never let the hook sink the brief
        print(f"[headline] WARNING: candidates failed ({e})")
        return []


def pick_headline(data, prev_props=None, date_str="", session=""):
    """The day's biggest |%| move as the Remotion `headline` prop:
    {"text": "GOLD ₨4,33,300", "kicker": "+2.1% TODAY", "sub": "2 Jul · Market close"}
    Returns None (prop omitted) when no day change is derivable. Never raises."""
    try:
        cands = day_candidates(data, prev_props)
        if not cands:
            return None
        top = max(cands, key=lambda c: abs(c["pct"]))
        if top["metric"] == "gold":
            text = f"GOLD ₨{grp(top['value'])}"
        elif top["metric"] == "usd":
            text = f"USD/PKR ₨{top['value']:.2f}"
        else:
            text = f"KSE-100 {grp(top['value'], locale_in=False)}"
        if all(abs(c["pct"]) < FLAT_EPS for c in cands):
            kicker = "FLAT DAY"
        else:
            kicker = f"{top['pct']:+.1f}% TODAY"
        sub = " · ".join(x for x in (_short_date(date_str), str(session or "")) if x)
        return {"text": text, "kicker": kicker, "sub": sub}
    except Exception as e:
        print(f"[headline] WARNING: skipped ({e})")
        return None


def build_yt_title(p, cands=None, date_str=None):
    """Searchable, story-first YouTube title, hard-capped at YT_TITLE_MAX.
    Leads with whichever metric moved most today (falls back to KSE-100)."""
    m, g = p["macro"], p["gold"]
    sess = "close" if "close" in str(p.get("session", "")).lower() else "open"
    day = _short_date(date_str or p.get("date", ""))
    by = {c["metric"]: c for c in (cands or [])}
    lead = max(cands, key=lambda c: abs(c["pct"]))["metric"] if cands else "kse"

    def pctp(metric):
        c = by.get(metric)
        return f" ({c['pct']:+.1f}%)" if c else ""

    kse_txt = grp(m["kse100"], locale_in=False)
    gold_txt = f"₨{grp(g['tola'])}"
    if lead == "gold":
        title = (f"Gold rate today {gold_txt}{pctp('gold')} — "
                 f"KSE-100 {kse_txt}{pctp('kse')} | {day} {sess} brief")
    elif lead == "usd":
        title = (f"USD/PKR today ₨{m['pkrUsd']:.2f}{pctp('usd')} — "
                 f"KSE-100 {kse_txt} | {day} {sess} brief")
    else:
        title = (f"KSE-100 today {kse_txt}{pctp('kse')} — "
                 f"gold rate {gold_txt}/tola | {day} {sess} brief")
    return title[:YT_TITLE_MAX]


def build_yt_description(p, body, cands=None):
    """First line carries the search phrases ("KSE 100 today", "gold rate today
    Pakistan") with the day's numbers, then the unique daily story line, then
    the existing static snapshot/disclaimer block."""
    m, g = p["macro"], p["gold"]
    by = {c["metric"]: c for c in (cands or [])}
    kse_pct = f" ({by['kse']['pct']:+.1f}%)" if "kse" in by else ""
    line1 = (f"KSE 100 today: {grp(m['kse100'], locale_in=False)}{kse_pct} · "
             f"gold rate today Pakistan: ₨{grp(g['tola'])}/tola 24k "
             f"({str(p.get('session', '')).lower()}).")
    return (
        f"{line1}\n\n{body}\n\n"
        "Daily Pakistan market snapshot — PSX, rupee, gold, top movers. "
        "Educational, not financial advice. pakinvestlysis.com\n\n"
        f"#Shorts {HASHTAGS}"
    )


def load_prev_daily_payload(daily_dir, today_file_str):
    """Most recent social-kit/daily/YYYY-MM-DD.json strictly before today
    (Friday's file on a Monday). None when absent/unreadable."""
    try:
        names = [n for n in os.listdir(daily_dir)
                 if n.endswith(".json") and len(n) == 15 and n[:10] < today_file_str]
        if not names:
            return None
        with open(os.path.join(daily_dir, sorted(names)[-1]), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


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


def social_payload(date_str, p, cands=None):
    """Single source of truth for the day's copy. Both the human-readable .md
    and the machine-readable .json (consumed by the auto-post scripts) derive
    from this, so LinkedIn/YouTube never re-parse markdown. `cands` (from
    day_candidates) makes the YouTube title/description story-first; LinkedIn
    copy is unchanged. The `metrics` block is what tomorrow's run (and the
    weekly review) diff against."""
    m, g = p["macro"], p["gold"]
    top = p["movers"][0] if p["movers"] else {"ticker": "", "name": "", "change1y": 0}
    hook = (
        f"Pakistan market brief — {date_str} ({p['session']}): KSE-100 at {grp(m['kse100'], locale_in=False)}, "
        f"the rupee at ₨{m['pkrUsd']:.2f}/$, gold ₨{grp(g['tola'])}/tola ({g['change1y']:+.1f}% in a year)."
    )
    body = (
        f"On the board today: policy rate {m['sbpRate']:.2f}%, inflation {m['inflation']:.1f}%. "
        f"PSX's biggest 1-year mover here is {top['ticker']} ({top['name']}) at {top['change1y']:+.1f}%. "
        "The full brief — your market day in under 60 seconds — walks the PSX and gold "
        "trends and the top movers. "
        "Compare every option with daily data and real-return charts on the site."
    )
    linkedin_text = f"{hook}\n\n{body}\n\n{FOOTER} — free live tools at pakinvestlysis.com\n\n{HASHTAGS}"

    return {
        "date": date_str,
        "session": p["session"],
        "hook": hook,
        "body": body,
        "metrics": {"kse100": m["kse100"], "gold_tola": g["tola"], "pkr_usd": m["pkrUsd"]},
        "linkedin": {"text": linkedin_text},
        "youtube": {
            "title": build_yt_title(p, cands, date_str),
            "description": build_yt_description(p, body, cands),
            "tags": YT_TAGS,
        },
    }


def caption_md(date_str, p, cands=None):
    s = social_payload(date_str, p, cands)
    headline = f"Pakistan market brief · {p['session']}"
    return f"""# {date_str} · {headline}

## LinkedIn
{s['linkedin']['text']}

## YouTube Short
**Title:** {s['youtube']['title']}
**Description:** {s['youtube']['description']}
"""


def main():
    today = datetime.date.today()
    date_str = today.strftime("%-d %b %Y")
    file_str = today.strftime("%Y-%m-%d")

    # Two runs a day: morning (cron hour 04 UTC, just after the PSX 9:30 PKT open)
    # and evening (cron hour 11 UTC, ~1h after the 15:30 close). Tag the brief by
    # session so the two daily videos read as distinct posts, not duplicates.
    # Derive the session from the *scheduled* cron (TRIGGER_CRON, "min hour ..."),
    # NOT wall-clock: GitHub Actions can delay a scheduled run by hours, which
    # would otherwise mislabel a delayed morning brief as "Market close". Fall
    # back to wall-clock for manual workflow_dispatch runs (no schedule set).
    cron = os.environ.get("TRIGGER_CRON", "").split()
    cron_hour = cron[1] if len(cron) >= 2 else None
    if cron_hour is not None and cron_hour.isdigit():
        session = "Market open" if int(cron_hour) < 9 else "Market close"
    else:
        utc_hour = datetime.datetime.now(datetime.timezone.utc).hour
        session = "Market open" if utc_hour < 9 else "Market close"

    with open(os.path.join(ROOT, "data.json"), encoding="utf-8") as f:
        data = json.load(f)

    daily_dir = os.path.join(ROOT, "social-kit", "daily")
    os.makedirs(daily_dir, exist_ok=True)

    # Day changes: KSE from data.json itself; gold/USD by diffing the previous
    # trading day's payload. Feeds the headline hook + the searchable YT copy.
    prev_payload = load_prev_daily_payload(daily_dir, file_str)
    cands = day_candidates(data, prev_payload)

    props = build_props(data, date_str, session)
    headline = pick_headline(data, prev_payload, date_str=date_str, session=session)
    if headline:
        props["headline"] = headline

    props_path = os.path.join(ROOT, "video", "daily-props.json")
    with open(props_path, "w", encoding="utf-8") as f:
        json.dump(props, f, ensure_ascii=False, indent=2)

    cap_path = os.path.join(daily_dir, f"{file_str}.md")
    with open(cap_path, "w", encoding="utf-8") as f:
        f.write(caption_md(date_str, props, cands))

    # Structured copy for the auto-post scripts (post_youtube.py / post_linkedin.py).
    payload_path = os.path.join(daily_dir, f"{file_str}.json")
    with open(payload_path, "w", encoding="utf-8") as f:
        json.dump(social_payload(date_str, props, cands), f, ensure_ascii=False, indent=2)

    print(f"  props:   {os.path.relpath(props_path, ROOT)}")
    print(f"  caption: {os.path.relpath(cap_path, ROOT)}")
    print(f"  movers:  {', '.join(m['ticker'] for m in props['movers'])}")
    print(f"  headline: {headline if headline else '(omitted — no day change derivable)'}")


if __name__ == "__main__":
    main()
