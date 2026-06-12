#!/usr/bin/env python3
"""Scan guides/ and blog/ and write manifest.json.

Runs in the daily GitHub Action after fetch_data.py, so any new guide or
blog post dropped into those folders appears on the listing pages the next
morning without editing the index HTML by hand.
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def extract(path: Path, section: str):
    html = path.read_text(encoding="utf-8")
    title = re.search(r"<title>(.*?)</title>", html, re.S)
    desc = re.search(r'<meta name="description" content="(.*?)"', html, re.S)
    modified = re.search(r'"dateModified":\s*"([^"]+)"', html)
    published = re.search(r'"datePublished":\s*"([^"]+)"', html)
    t = title.group(1) if title else path.stem
    t = re.sub(r"\s*[—|–]\s*Pakistan Investment Advisor\s*$", "", t.strip())
    return {
        "url": f"/{section}/{path.name}",
        "title": t,
        "description": (desc.group(1).strip() if desc else ""),
        "published": published.group(1) if published else "",
        "modified": modified.group(1) if modified else "",
    }


def scan(section: str):
    items = []
    for f in sorted((ROOT / section).glob("*.html")):
        if f.name == "index.html":
            continue
        try:
            items.append(extract(f, section))
        except Exception as e:  # never let one bad file kill the daily run
            print(f"WARN: skipped {f}: {e}", file=sys.stderr)
    items.sort(key=lambda x: (x["published"] or "0000"), reverse=True)
    return items


def main():
    manifest = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "guides": scan("guides"),
        "posts": scan("blog"),
    }
    out = ROOT / "manifest.json"
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"manifest.json: {len(manifest['guides'])} guides, {len(manifest['posts'])} posts")


if __name__ == "__main__":
    main()
