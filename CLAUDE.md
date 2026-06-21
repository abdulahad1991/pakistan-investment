# CLAUDE.md — pakinvestlysis.com

Read this first. It maps the project so you don't have to read every file.

## What this is
Static website for **pakinvestlysis.com** — free, daily-updated Pakistan investing
tools and guides (National Savings, mutual funds, PSX stocks, gold, tax, zakat).
Educational only; **never financial advice**. Audience: Pakistani retail savers.

## Stack & build
- **No build step, no framework.** Plain HTML + vanilla JS + CSS, served as-is by GitHub Pages.
- Charts: **Chart.js 4.4.1** via CDN (loaded `defer` in each page).
- Styles: single stylesheet `assets/site.css` (design tokens in `:root`).
- Fonts: Inter + IBM Plex Mono (Google Fonts); CSS also references Proxima Nova.
- Data tooling: **Python 3.12** (`fetch_data.py`, `scripts/build_manifest.py`), run in CI only.
- Host: GitHub Pages, custom domain via `CNAME` (pakinvestlysis.com).

## Branch & deploy flow (important)
- Work on **`dev`**. Pushing to `dev` triggers `.github/workflows/merge-dev-to-main.yml`,
  which **fast-forwards `main`** and pings IndexNow for changed `.html` pages. Pages serves `main`.
- So: **commit to `dev`, that's the deploy.** Don't push straight to `main`.
- Daily cron `.github/workflows/update-data.yml` (01:00 UTC / 06:00 PKT): runs
  `fetch_data.py` + `build_manifest.py` on `dev`, commits `data.json`/`manifest.json`, merges to `main`.
- User works autonomously with skip-permissions; pushing to deploy is expected.

## Data pipeline
- `fetch_data.py` → writes **`data.json`** (the single live dataset). Sources: yfinance
  (PKR/USD, PSX stock prices, gold spot GC=F + PKR=X history), and HTML scrapes
  (PSX KSE-100, CDNS savings rates, SBP policy rate, finhisaab fund returns, **gold.pk** gold rates).
  Every section is best-effort: on failure it keeps the existing `data.json` value (graceful fallback).
- `data.json` is fetched client-side by `app.js` (homepage) and `assets/gold.js` (gold page).
  It is committed with **seed values** so the site works before the next cron run.
- `scripts/build_manifest.py` → **`manifest.json`** (auto-listing of `guides/` + `blog/` for
  the index pages and site search). New guide/blog HTML files appear automatically next run.

## Key files
- `index.html` — homepage: 5-step investment wizard (pages 0–4) + static SEO section + **live gold card**.
- `app.js` — homepage logic: loads `data.json`, renders macro pills, charts, wizard, portfolio, gold card.
- `gold-rates.html` + `assets/gold.js` — **dedicated gold page**: live rates, 6-yr history chart, forecast calculator.
- `tax-calculator.html` + `assets/tax-calculator.js` — income/GST/restaurant tax calculator.
- `zakat-calculator.html` + `assets/zakat-calculator.js` — zakat calculator (nisab from gold/silver).
- `guides/*.html`, `blog/*.html` — content pages (+ `assets/article.js`, `assets/listing.js`).
- `assets/search.js` — site search **and** binds the mobile `.nav-toggle` + `/` search shortcut (every page needs it).
- `assets/share.js`, `assets/analytics.js` — share buttons, GA4 + `window.pkTrack` events.
- `methodology.html`, `about.html` — trust pages. `faq.html` — searchable FAQ hub.
- `sitemap.xml`, `llms.txt`, `robots.txt`, `manifest.json`, `ads.txt` — SEO/discovery.
- `social-kit/` — Medium exports + share copy (manual).

## Design system (the "ledger" look)
- Tokens in `assets/site.css` `:root`: `--green #075E4B`, `--gold #F2B94B`, `--gold2 #B7791F`,
  `--navy #2854C5`, `--red #C24132`, `--paper`, `--ink`, etc. Mirrored as `LEDGER` object in `app.js`.
- Money: **Pakistani digit grouping** `X,XX,XXX` — use `formatPKR()` (app.js) / `fmtPKR()` (gold.js). Prefix `₨`.
- Reusable classes: `.card`, `.dashboard-card`, `.macro-grid`/`.macro-pill`, `.stat-card`/`.summary-grid`,
  `.chart-wrap`(-sm), `.chart-card`, `.section-kicker`/`.section-title`/`.section-sub`, `.faq-section`/`.faq-item`,
  `.related-links`, `.cta-btns`/`.btn-cta`(`.btn-primary`/`.btn-gold`/`.btn-navy`), `.ad-slot`, `.breadcrumb`.
  Calculator pages use a self-contained cream `<style>` block (`#FDFBF4`, gold accent `#B98A2F`).

## No templating — header/nav is duplicated in every HTML file
There is no include system. The `<header>`/`<nav id="site-nav">` and footer are copied into all ~30 pages.
To change nav sitewide, use a careful `perl -0pi -e` across `*.html` (anchor on stable text and preserve
indentation). Active page uses `aria-current="page"` on its nav link. `.nav-toggle` is wired by `search.js`.

## Conventions
- Every page: OG + Twitter meta, JSON-LD (WebSite/SoftwareApplication/FAQPage/BreadcrumbList), `<link rel=canonical>`.
- OG images are **pre-generated PNGs** in `assets/og/` — reuse an existing one; don't expect a generator.
- Tone: honest. Author **Abdul Ahad is a software engineer, not an investment professional** — never claim
  first-hand investing experience or personal returns. Show "as of" dates. Always include a not-advice disclaimer.
- When adding a new live metric: (1) add a section to `fetch_data.py` that writes into the `data` dict,
  (2) add seed values to `data.json`, (3) render it in `app.js`/page JS, (4) add the page to `sitemap.xml` + `llms.txt`.

## Gotchas
- AdSense: homepage inits the visible page's ad at load; hidden wizard pages init lazily via `initPageAd()` in `goPage()`.
- Chart.js instances are tracked in `chartInstances`/`gCharts`; always `destroy()` before re-rendering an id.
- yfinance/scrapes are **not installed locally** (CI installs them) — test data-dependent UI against the seed `data.json`.
- `data.json` cache-busted with `?v=Date.now()` on fetch.
