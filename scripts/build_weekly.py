#!/usr/bin/env python3
"""Build the weekly *Week in Review* props + caption (Fridays, after the close).

Outputs:
  <root>/video/weekly-props.json             -> Remotion --props for WeeklyBrief-16x9
  <root>/video/public/voiceover-weekly.mp3   -> ~60-90s Urdu narration (optional)
  <root>/social-kit/weekly/YYYY-MM-DD.json   -> props + "youtube" metadata block
                                                (fed to post_youtube.py --caption)
  <root>/social-kit/weekly/YYYY-MM-DD.md     -> human-readable caption

Sources (all already in the repo — no network except the optional TTS):
  * KSE + gold week series: the Mon-Fri social-kit/daily/*.json payloads of the
    current ISO week (structured `metrics` block, regex fallback for older
    files), with today's live data.json values pinned as the final point.
    data.json's own history arrays are MONTHLY, so they only serve as a
    last-resort fallback series.
  * Weekly movers: data.json stocks[].price (live) vs data/stock_history.json's
    last value — that file is rebuilt every Monday from PSX EOD, so its last
    point is this week's Monday baseline.
  * Rates: data.json macro (policy / inflation / USDPKR).

Graceful degradation everywhere: missing files/deps shrink the output (empty
movers, fallback series, no voiceover prop) but never crash.
Run from repo root: python3 scripts/build_weekly.py
"""
import datetime
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from build_daily import (  # noqa: E402  (path bootstrap above)
    FOOTER, HASHTAGS, VO_RATE_WEEKLY, YT_TAGS, YT_TITLE_MAX,
    _metrics_from_payload, grp, render_voiceover,
)

VO_MAX_SEC_WEEKLY = 92   # target 60-90s; re-render faster past this
MOVERS_TOP_N = 5
MOVER_SANITY_PCT = 80    # a >80% week move in this universe is a data glitch


# ---------------------------------------------------------------------------
# Week window + series
# ---------------------------------------------------------------------------
def week_bounds(today):
    """(monday, friday) of `today`'s ISO week."""
    monday = today - datetime.timedelta(days=today.weekday())
    return monday, monday + datetime.timedelta(days=4)


def date_range_str(monday, friday):
    """'30 Jun – 4 Jul 2026' (contract format), '7–11 Jul 2026' within a month."""
    if monday.month == friday.month:
        return f"{monday.day}–{friday.day} {friday.strftime('%b %Y')}"
    return f"{monday.day} {monday.strftime('%b')} – {friday.day} {friday.strftime('%b %Y')}"


def collect_week_series(daily_dir, monday, friday, today, live_kse, live_gold):
    """(kse_series, gold_series) from this week's daily payloads (Mon → today),
    ending on today's live values. 2-6 points each when the dailies exist."""
    kse, gold = [], []
    d = monday
    last = min(friday, today)
    while d <= last:
        path = os.path.join(daily_dir, f"{d:%Y-%m-%d}.json")
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    met = _metrics_from_payload(json.load(f))
            except Exception:
                met = {}
            if met.get("kse100"):
                kse.append((d, float(met["kse100"])))
            if met.get("gold_tola"):
                gold.append((d, float(met["gold_tola"])))
        d += datetime.timedelta(days=1)
    # Pin the live figure as the final point (replace today's own entry if any),
    # same spirit as build_daily's _series end-pinning.
    for series, live in ((kse, live_kse), (gold, live_gold)):
        if live:
            if series and series[-1][0] == today:
                series[-1] = (today, float(live))
            else:
                series.append((today, float(live)))
    return [v for _, v in kse], [v for _, v in gold]


def fallback_series(hist, take=6):
    """Last `take` points of a {labels,values} history (data.json's arrays are
    monthly — only used when the week's daily payloads are missing)."""
    try:
        return [float(v) for v in (hist.get("values") or [])][-take:]
    except (TypeError, ValueError):
        return []


def series_block(series):
    """Contract shape for kse/gold: {open, close, chgPct, series}."""
    if not series:
        return {"open": 0, "close": 0, "chgPct": 0.0, "series": []}
    o, c = series[0], series[-1]
    pct = (c - o) / o * 100 if o else 0.0
    return {"open": o, "close": c, "chgPct": round(pct, 1), "series": series}


# ---------------------------------------------------------------------------
# Weekly movers
# ---------------------------------------------------------------------------
def weekly_movers(stocks, history, top_n=MOVERS_TOP_N):
    """Top |%| moves this week: live price (data.json) vs the last
    stock_history value (Monday's PSX EOD rebuild = the week's baseline)."""
    out = []
    for s in stocks or []:
        t = s.get("ticker")
        price = s.get("price") or 0
        vals = ((history or {}).get(t) or {}).get("values") or []
        if not t or price <= 0 or not vals:
            continue
        base = vals[-1]
        if not base or base <= 0:
            continue
        pct = (price - base) / base * 100
        if abs(pct) > MOVER_SANITY_PCT:
            continue
        out.append({"sym": t, "name": s.get("name", t), "chgPct": round(pct, 1)})
    out.sort(key=lambda m: abs(m["chgPct"]), reverse=True)
    return out[:top_n]


# ---------------------------------------------------------------------------
# Props + copy
# ---------------------------------------------------------------------------
def build_weekly_props(data, stock_history, daily_dir, today):
    macro = data.get("macro") or {}
    gold = data.get("gold") or {}
    monday, friday = week_bounds(today)

    kse_series, gold_series = collect_week_series(
        daily_dir, monday, friday, today,
        macro.get("kse100_level") or 0, gold.get("tola_24k") or 0)
    if len(kse_series) < 2:
        print("[weekly] WARNING: <2 daily KSE points this week — falling back "
              "to the monthly history tail")
        kse_series = fallback_series(data.get("kse100_history") or {})
    if len(gold_series) < 2:
        print("[weekly] WARNING: <2 daily gold points this week — falling back "
              "to the monthly history tail")
        gold_series = fallback_series(gold.get("history") or {})

    props = {
        "dateRange": date_range_str(monday, friday),
        "kse": series_block(kse_series),
        "gold": series_block(gold_series),
        "movers": weekly_movers(data.get("stocks"), stock_history),
        "rates": {
            "policy": float(macro.get("sbp_rate") or 0),
            "inflation": float(macro.get("inflation_cpi") or 0),
            "usd": float(macro.get("pkr_usd") or 0),
        },
    }
    return props, monday, friday


def youtube_meta(props, friday):
    """Searchable weekly YT title/description/tags (long-form — NO #Shorts)."""
    kse, gold, r = props["kse"], props["gold"], props["rates"]
    day = f"{friday.day} {friday.strftime('%b %Y')}"
    title = (f"Pakistan stock market this week: KSE-100 {kse['chgPct']:+.1f}%, "
             f"gold ₨{grp(gold['close'])} | Week in Review {day}")[:YT_TITLE_MAX]
    mtxt = ", ".join(f"{m['sym']} {m['chgPct']:+.1f}%" for m in props["movers"][:3])
    line1 = (f"KSE 100 this week: {grp(kse['open'], locale_in=False)} → "
             f"{grp(kse['close'], locale_in=False)} ({kse['chgPct']:+.1f}%) · "
             f"gold rate today Pakistan: ₨{grp(gold['close'])}/tola "
             f"({gold['chgPct']:+.1f}% this week).")
    body = (f"Week in review ({props['dateRange']}) — the whole week in under "
            f"3 minutes: the KSE-100 moved {kse['chgPct']:+.1f}% and gold "
            f"{gold['chgPct']:+.1f}%. Notable movers: {mtxt or 'n/a'}. "
            f"Policy rate {r['policy']:.2f}%, inflation {r['inflation']:.1f}%, "
            f"USD/PKR ₨{r['usd']:.2f}.")
    desc = (f"{line1}\n\n{body}\n\n"
            "Weekly Pakistan market review — PSX, gold, rupee, top movers. "
            "Free live tools, daily data and real-return charts: "
            "https://pakinvestlysis.com\n"
            f"{FOOTER}\n\n{HASHTAGS}")
    return {"title": title, "description": desc, "tags": YT_TAGS + ["weekly review"]}


def weekly_vo_script(props):
    """~60-90s spoken-Urdu week recap (digits stay Latin, same as the daily VO).
    Ends on the mandated site + subscribe line."""
    kse, gold, r = props["kse"], props["gold"], props["rates"]
    lines = ["السلام علیکم! یہ ہے اس ہفتے کا پاکستان مارکیٹ ریویو۔"]
    if kse["close"]:
        word = "اوپر" if kse["chgPct"] >= 0 else "نیچے"
        lines.append(f"اس ہفتے کے ایس ای سو انڈیکس {int(round(kse['open']))} سے "
                     f"{int(round(kse['close']))} پوائنٹس پر پہنچا، یعنی "
                     f"{abs(kse['chgPct'])} فیصد {word}۔")
    if gold["close"]:
        word = "بڑھ کر" if gold["chgPct"] >= 0 else "گر کر"
        lines.append(f"سونے کا ریٹ اس ہفتے {abs(gold['chgPct'])} فیصد {word} "
                     f"{int(round(gold['close']))} روپے فی تولہ پر آ گیا۔")
    movers = props["movers"][:2]
    if movers:
        parts = []
        for m in movers:
            word = "اوپر" if m["chgPct"] >= 0 else "نیچے"
            parts.append(f"{m['name']}، {abs(m['chgPct'])} فیصد {word}")
        lines.append("اسٹاکس میں اس ہفتے نمایاں رہے " + "، اور ".join(parts) + "۔")
    lines.append(f"پالیسی ریٹ {r['policy']} فیصد، مہنگائی {r['inflation']} فیصد، "
                 f"اور ڈالر تقریباً {int(round(r['usd']))} روپے پر رہا۔")
    lines.append("اگلے ہفتے نئی شرحیں، سونے کا رجحان اور مارکیٹ کی سمت، سب کچھ "
                 "روزانہ اپڈیٹ ہوتا ہے۔")
    lines.append("یاد رہے، یہ صرف تعلیمی جائزہ ہے، مالی مشورہ نہیں۔")
    lines.append("Poori tafseel pakinvestlysis dot com par. Subscribe zaroor karein.")
    return " ".join(lines)


def caption_md(file_str, props, meta):
    return f"""# {file_str} · Pakistan week in review ({props['dateRange']})

## YouTube
**Title:** {meta['title']}
**Description:** {meta['description']}
"""


def main():
    today = datetime.date.today()
    file_str = today.strftime("%Y-%m-%d")

    with open(os.path.join(ROOT, "data.json"), encoding="utf-8") as f:
        data = json.load(f)
    try:
        with open(os.path.join(ROOT, "data", "stock_history.json"), encoding="utf-8") as f:
            stock_history = json.load(f)
    except Exception as e:
        print(f"[weekly] WARNING: no stock history ({e}) — movers will be empty")
        stock_history = {}

    daily_dir = os.path.join(ROOT, "social-kit", "daily")
    props, monday, friday = build_weekly_props(data, stock_history, daily_dir, today)

    # Optional narration — omit the prop entirely when TTS is unavailable.
    vo_path = os.path.join(ROOT, "video", "public", "voiceover-weekly.mp3")
    vo_dur = render_voiceover(weekly_vo_script(props), vo_path,
                              VO_MAX_SEC_WEEKLY, rate=VO_RATE_WEEKLY)
    if vo_dur:
        props["voiceover"] = {"file": "voiceover-weekly.mp3", "enabled": True}

    props_path = os.path.join(ROOT, "video", "weekly-props.json")
    with open(props_path, "w", encoding="utf-8") as f:
        json.dump(props, f, ensure_ascii=False, indent=2)

    meta = youtube_meta(props, friday)
    weekly_dir = os.path.join(ROOT, "social-kit", "weekly")
    os.makedirs(weekly_dir, exist_ok=True)

    payload = dict(props)
    payload["date"] = file_str
    payload["youtube"] = meta
    payload_path = os.path.join(weekly_dir, f"{file_str}.json")
    with open(payload_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    cap_path = os.path.join(weekly_dir, f"{file_str}.md")
    with open(cap_path, "w", encoding="utf-8") as f:
        f.write(caption_md(file_str, props, meta))

    print(f"  props:   {os.path.relpath(props_path, ROOT)}")
    print(f"  payload: {os.path.relpath(payload_path, ROOT)}")
    print(f"  range:   {props['dateRange']}  kse {props['kse']['chgPct']:+.1f}%  "
          f"gold {props['gold']['chgPct']:+.1f}%")
    print(f"  movers:  {', '.join(m['sym'] for m in props['movers']) or '(none)'}")
    print(f"  voiceover: {f'{vo_dur:.1f}s' if vo_dur else '(skipped)'}")


if __name__ == "__main__":
    main()
