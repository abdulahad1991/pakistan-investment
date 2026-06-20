# Social kit

Off-site distribution assets. Not part of the live site (disallowed in robots.txt).

## Contents
- **`posts.md`** — ready-to-post LinkedIn / Facebook / WhatsApp / X copy for the flagship pages.
- **`medium/`** — Markdown exports of every guide and blog post, for republishing.

## How to republish on Medium (do this — don't just paste)
The best method keeps SEO credit on your own site:
1. On Medium, click your avatar → **Stories** → **Import a story**.
2. Paste the **live URL** of the guide (e.g. `https://pakinvestlysis.com/guides/prize-bonds-pakistan.html`).
3. Medium imports the content and automatically sets `rel="canonical"` back to your URL — so Google still credits the original and you avoid duplicate-content issues.
4. Add 4–5 tags (Pakistan, Investing, Personal Finance, Taxes, Stock Market) and submit to a finance publication if you can.

Use the files in `medium/` only if you want to hand-edit before posting (they won't carry the canonical automatically — set it yourself if Medium lets you).

## OG / share images
Branded 1200×630 share images live in `/assets/og/` and are wired into every page's `og:image` / `twitter:image`. Re-generate them by editing titles and re-running the build (see repo history).

## Distribution priority (highest impact first)
1. Reddit (r/pakistan, r/PakStockExchange, r/PakistaniInvestor) + Facebook groups — answer questions first, link when genuinely useful.
2. Medium (import-from-URL as above).
3. LinkedIn — build Abdul Ahad as the author/expert; 2–3 posts/week.
4. Facebook page — lead with the calculators (tools get shared most).
