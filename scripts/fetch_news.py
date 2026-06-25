#!/usr/bin/env python3
"""Fetch fresh sector headlines from Google News RSS into data/news_queue.json.

Stdlib parser (xml.etree) so importing this module needs no third-party deps -
`requests` is imported lazily only when a network fetch actually runs, which
keeps parse_rss() unit-testable offline. Best-effort: on any failure the
previous queue file is kept (graceful fallback, like fetch_data.py).
"""
import json, sys, urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "data" / "news_queue.json"
UA = {"User-Agent": "Mozilla/5.0 (pakinvestlysis news bot)"}


def _requests():
    try:
        import requests
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install",
                               "-q", "--break-system-packages", "requests"])
        import requests
    return requests


def parse_rss(xml_text, limit=6):
    root = ET.fromstring(xml_text)
    out = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        src_el = item.find("source")
        source = (src_el.text.strip() if src_el is not None and src_el.text else "")
        if not source and " - " in title:        # Google appends " - Source"
            source = title.rsplit(" - ", 1)[-1].strip()
        if title and link:
            out.append({"title": title, "url": link, "source": source, "published": pub})
        if len(out) >= limit:
            break
    return out


def fetch_sector_news(query, limit=6):
    requests = _requests()
    q = urllib.parse.quote(f"{query} when:14d")
    url = f"https://news.google.com/rss/search?q={q}&hl=en-PK&gl=PK&ceid=PK:en"
    r = requests.get(url, headers=UA, timeout=20)
    r.raise_for_status()
    return parse_rss(r.text, limit=limit)


def main():
    cfg = json.loads((ROOT / "scripts/sectors.json").read_text())
    queue = {}
    if QUEUE.exists():
        try:
            queue = json.loads(QUEUE.read_text())
        except Exception:
            queue = {}
    for s in cfg:
        try:
            items = fetch_sector_news(s["news_query"])
            if items:
                queue[s["slug"]] = {
                    "fetched": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "items": items,
                }
                print(f"news {s['slug']}: {len(items)}")
        except Exception as e:
            print(f"news {s['slug']} failed (keep old): {e}", file=sys.stderr)
    QUEUE.parent.mkdir(exist_ok=True)
    QUEUE.write_text(json.dumps(queue, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
