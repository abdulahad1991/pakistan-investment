#!/usr/bin/env python3
"""Post-publish quality audit. Flags weak pages and opens a gh issue, but does
NOT unpublish (the engine is auto-publish + post-publish audit by design)."""
import re, sys, subprocess, shutil
from pathlib import Path


def _text(html):
    return re.sub(r"<[^>]+>", " ", html)


def audit(path):
    html = Path(path).read_text(encoding="utf-8")
    slug = Path(path).stem
    words = len(_text(html).split())
    flags = []
    if words < 700:
        flags.append(f"word count low ({words})")
    if "{{" in html:
        flags.append("unfilled template token")
    if "perf-table" not in html and "refreshing" in html:
        flags.append("no live price rows")
    if "not investment advice" not in html.lower():
        flags.append("missing disclaimer")
    for t in ["Article", "FAQPage", "BreadcrumbList"]:
        if t not in html:
            flags.append(f"missing JSON-LD {t}")
    if re.search(r"[—–]", html):
        flags.append("em/en dash present")
    return {"slug": slug, "ok": not flags, "flags": flags, "words": words}


def main(path):
    res = audit(path)
    print(res)
    if not res["ok"] and shutil.which("gh"):
        body = "Automated audit flagged this page:\n\n- " + "\n- ".join(res["flags"])
        subprocess.run(["gh", "issue", "create",
                        "--title", f"audit: {res['slug']} flagged",
                        "--body", body], check=False)
    return 0   # never fail the pipeline


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
