#!/usr/bin/env python3
"""Build a 60-second Urdu audio explainer for a blog page. No API key.

Pipeline (all keyless):
  1. Extract a short English summary from the blog HTML (lead + "At a glance"
     bullets + a disclaimer outro).
  2. Translate each line EN -> UR with deep-translator (free Google endpoint).
  3. Voice each line with edge-tts (ur-PK neural), measure durations.
  4. Concatenate to assets/blog-audio/<slug>.mp3 and write <slug>.json (the
     manifest the in-page interactive player reads: chapters + timings).

Deps (install in CI / a venv): edge-tts deep-translator mutagen  (+ ffmpeg)
Usage: python scripts/build_explainer.py <slug-or-blog-path> [--voice ur-PK-AsadNeural]
"""
import os, re, sys, json, html as _html, subprocess, asyncio, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTDIR = ROOT / "assets" / "blog-audio"
VOICE = "ur-PK-AsadNeural"
MAX_LINES = 7
MAX_WORDS = 22


def _clean(text):
    text = re.sub(r"<[^>]+>", " ", text)
    text = (text.replace("&#8360;", "Rs ").replace("₨", "Rs ")
                .replace("&amp;", "and").replace("&nbsp;", " ")
                .replace("&#x27;", "'").replace("&quot;", '"'))
    text = _html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip(" .·-")
    return text


ABBREV = [
    (r"\bDBR\b", "debt-burden ratio"), (r"\bLTV\b", "loan-to-value ratio"),
    (r"\bP/E\b", "price-to-earnings ratio"), (r"\bPSX\b", "Pakistan Stock Exchange"),
    (r"\bSBP\b", "State Bank of Pakistan"), (r"\bNPC[s]?\b", "Naya Pakistan Certificates"),
    (r"\bATL\b", "Active Taxpayer List"), (r"\bFY\b", "fiscal year"),
]
URDU_NUM = {"0": "۰", "1": "۱", "2": "۲", "3": "۳", "4": "۴",
            "5": "۵", "6": "۶", "7": "۷", "8": "۸", "9": "۹"}


def _normalize(s):
    for pat, rep in ABBREV:
        s = re.sub(pat, rep, s)
    s = re.sub(r"\s*\([^)]*\)", "", s)          # drop parentheticals
    return re.sub(r"\s+", " ", s).strip(" .,;-")


def _first_sentence(s, n=26):
    s = re.split(r"(?<=[.!?;])\s", s)[0]        # first clause/sentence
    s = s.rstrip(" .,;-")
    w = s.split()
    return (" ".join(w[:n]) if len(w) > n else s) + "."


def extract_lines(htmltext):
    """Return ordered list of short English narration lines."""
    lines = []
    m = re.search(r'<p class="lead">(.*?)</p>', htmltext, re.S)
    if not m:
        m = re.search(r'class="head-r">.*?<p>(.*?)</p>', htmltext, re.S)
    if not m:
        m = re.search(r'<meta name="description" content="([^"]+)"', htmltext)
    if m:
        lead = _normalize(_clean(m.group(1)).replace("In one line:", ""))
        if lead:
            lines.append(_first_sentence(lead, 28))
    g = re.search(r'<div class="cl-key">.*?<ul>(.*?)</ul>', htmltext, re.S)
    if g:
        for li in re.findall(r"<li>(.*?)</li>", g.group(1), re.S):
            t = _normalize(_clean(li))
            if len(t) > 8:
                lines.append(_first_sentence(t))
    if len(lines) < 3:
        for h in re.findall(r"<h2[^>]*>(.*?)</h2>", htmltext, re.S):
            t = _normalize(_clean(re.sub(r'<span class="sn">.*?</span>', "", h, flags=re.S)))
            if t and "frequently asked" not in t.lower():
                lines.append(t + ".")
    lines = lines[:MAX_LINES - 1]
    lines.append("Read the full guide on Pakinvestlysis. This is educational, "
                 "not financial advice.")
    return lines


def chip_labels(n):
    """Clean fixed Urdu chapter labels (no translation risk)."""
    labels = ["تعارف"]                                    # intro
    mids = n - 2
    for k in range(mids):
        labels.append("نکتہ " + URDU_NUM[str(k + 1)])      # "Point N"
    labels.append("اختتام")                               # outro
    return labels[:n]


def og_title(htmltext):
    m = re.search(r'<meta property="og:title" content="([^"]+)"', htmltext)
    if not m:
        m = re.search(r"<title>([^<]+)</title>", htmltext)
    return _html.unescape(m.group(1)).strip() if m else "Pakinvestlysis"


def _leaky(s):
    """True if the 'Urdu' still has a run of English words (translation failed)."""
    return len(re.findall(r"[A-Za-z]{3,}", s)) >= 3


def translate(texts):
    from deep_translator import GoogleTranslator
    tr = GoogleTranslator(source="en", target="ur")
    out = []
    for t in texts:
        res = t
        for _ in range(2):
            try:
                res = tr.translate(t) or t
                if not _leaky(res):
                    break
            except Exception:
                pass
        out.append(res)
    return out


async def _tts(text, path, voice):
    import edge_tts
    await edge_tts.Communicate(text, voice=voice).save(str(path))


def _dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def build(slug, voice=VOICE):
    page = ROOT / "blog" / f"{slug}.html"
    htmltext = page.read_text(encoding="utf-8")
    title = og_title(htmltext)
    en = extract_lines(htmltext)
    ur = translate(en)
    labels = chip_labels(len(en))

    OUTDIR.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp())
    chapters, parts, start = [], [], 0.0
    for i, (u, e) in enumerate(zip(ur, en)):
        clip = tmp / f"l{i:02d}.mp3"
        asyncio.run(_tts(u, clip, voice))
        d = _dur(clip)
        chapters.append({"i": i, "label": labels[i], "ur": u, "en": e,
                         "start": round(start, 2), "dur": round(d, 2)})
        parts.append(clip)
        start += d

    listf = tmp / "list.txt"
    listf.write_text("".join(f"file '{p}'\n" for p in parts))
    out_mp3 = OUTDIR / f"{slug}.mp3"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listf),
                    "-c:a", "libmp3lame", "-b:a", "96k", str(out_mp3)],
                   check=True, capture_output=True)
    total = round(_dur(out_mp3), 2)

    manifest = {"slug": slug, "title": title, "lang": "ur", "voice": voice,
                "total": total, "chapters": chapters}
    (OUTDIR / f"{slug}.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1),
                                         encoding="utf-8")
    for p in parts:
        p.unlink(missing_ok=True)
    listf.unlink(missing_ok=True)
    os.rmdir(tmp)
    print(f"explainer: {slug} -> {total:.0f}s, {len(chapters)} chapters")
    return out_mp3


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: build_explainer.py <slug-or-blog-path> [--voice NAME]", file=sys.stderr)
        sys.exit(2)
    arg = sys.argv[1]
    slug = Path(arg).stem if arg.endswith(".html") else arg
    voice = VOICE
    if "--voice" in sys.argv:
        voice = sys.argv[sys.argv.index("--voice") + 1]
    build(slug, voice)
