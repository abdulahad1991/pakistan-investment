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
- Cron `.github/workflows/update-data.yml` runs **twice a day, every day**:
  **04:37 UTC / 09:37 PKT** ("Market open", after the 09:30 PSX open) and
  **11:41 UTC / 16:41 PKT** ("Market close", ~1h after the 15:30 close). Weekday runs:
  `run_fetchers.py open|close` + `build_manifest.py` on `dev`, commits `data.json`/`manifest.json`,
  merges to `main`, then the `social` job runs `build_daily.py` and re-renders the
  DailyBrief videos (Short 9:16, LinkedIn 1:1, still card, homepage 16:9). The video
  is labelled by `session` ("Market open"/"Market close") so the two daily posts differ.
  **Weekend runs (Sat/Sun)** use the `weekend` fetcher group (gold + fx only — Sarafa
  fixes gold on Saturday) and skip the `social` job entirely (data-only, no posts).
- User works autonomously with skip-permissions; pushing to deploy is expected.

## Data pipeline (rebuilt 2026-06-28 — single-responsibility fetchers + merge)
- **`fetchers/*.py`** — one module per data category, each from the AUTHORITATIVE source:
  `cpi`→PBS SDMX (real CPI YoY, was a hardcoded 7.0 seed), `stocks`+`kse`+`dividends`→**PSX Data
  Portal** (dps.psx.com.pk; replaces unreliable yfinance — fixes 0.0 dividends, garbage P/E,
  the open-vs-close KSE bug), `reserves`/`forex`/`policy`→SBP, `savings`→CDNS banner,
  `funds`→MUFAP (tags income=annualized vs equity=absolute), `gold`→gold.pk, `macro`→PBS GDP + curated IMF.
  Each exposes a **pure `parse_*`** (unit-tested against real captured responses in `tests/fixtures/`,
  run via `pytest`) and a `fetch()` that writes a provenance partition to `data/partitions/<name>.json`
  `{value, as_of, source, ok, fetched_at, cadence}`. Graceful fallback: a failure keeps the prior
  partition flagged `ok:false` (never silently serves stale as current).
- **Failover crawl (`base.crawl_first`)** — the three SBP-sourced fetchers (`forex`/`policy`/`reserves`)
  all read ONE SBP page (`ecodata/rates/m2m/m2m-current.asp`, the "Economic Data snapshot"), so a single
  SBP redesign froze all three (see the 2026-07 incident). `crawl_first(name, [(label, thunk), ...])` tries
  an ordered source chain and returns the FIRST valid partition, tagging it `via`/`failover`/`primary_errors`:
  **forex** = SBP m2m → recrawl SBP homepage (same snapshot) → `open.er-api.com` keyless USD/PKR (tagged
  `approx`); **policy**/**reserves** = SBP m2m → recrawl SBP homepage (no clean non-SBP source, and their
  event/weekly cadence makes carry-forward correct). Only when EVERY source fails does it raise
  `AllSourcesFailed` → `run()` carries the prior value forward `ok:false`. `data_health[name]` surfaces
  `via`/`failover` so the UI can show "primary down, served via <fallback>".
- **`run_fetchers.py [open|close|history|all]`** — orchestrator (cadence groups), then **`build_data.py`**
  overlays partitions onto the curated **`data.json`** (preserving hand-authored content), adds `_asof`
  fields + a `data_health` block + staleness flags, and asserts consistency (e.g. gold gram==tola/11.6638).
  `fetch_data.py` is now a deprecation shim → `run_fetchers`.
- `data/partitions/*.json` are **committed** (audit trail + lets `policy.py` derive the rate STANCE by
  diffing against the prior run — stance was previously hardcoded "Holding").
- CI (`update-data.yml`): 04:45 UTC run = `open` (fast prices), 11:30 UTC = `close` (full incl. per-stock
  fundamentals + dividends); Mondays also `run_fetchers.py history` (rebuilds `data/stock_history.json`
  from PSX EOD for the dividend page + backtester).
- `data.json` is fetched client-side by `app.js` (homepage) and `assets/gold.js` (gold page); committed
  with seed values so the site works before the next cron run.
- `scripts/build_manifest.py` → **`manifest.json`** (auto-listing of `guides/` + `blog/` for
  the index pages and site search). New guide/blog HTML files appear automatically next run.
- **When adding a live metric:** add a `fetchers/<x>.py` (pure parser + fixture test), map it in
  `build_data.py`, seed `data.json`, render it (with its `_asof`) in the page JS.

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
