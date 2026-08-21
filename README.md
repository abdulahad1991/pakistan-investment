# Pakinvestlysis

**Live site: [pakinvestlysis.com](https://pakinvestlysis.com)**

Independent educational tools, source-led guides and dated datasets about investing and saving in Pakistan. Source dates and failed fetches are exposed; users should verify a figure with the linked publisher before relying on it. Not financial advice.

## What's on the site

- **[Investment comparison](https://pakinvestlysis.com/)** - applies an entered amount to neutral educational categories and links to the underlying source material.
- **[Pakistan tax calculator](https://pakinvestlysis.com/tax-calculator.html)** - Tax Year 2027 income-tax slab arithmetic and a user-rate sales-tax split.
- **[Zakat arithmetic calculator](https://pakinvestlysis.com/zakat-calculator.html)** - applies a common 2.5% arithmetic convention to user-entered assets, liabilities and nisab inputs; it does not issue a religious ruling.
- **[Investment guides](https://pakinvestlysis.com/guides/)** - 12 retained guides covering regulated funds, government instruments, market access, gold and tax processes.
- **[Research notes and datasets](https://pakinvestlysis.com/blog/)** - the enacted Finance Act, a bank-model audit worksheet and a dated PSX dividend-yield screen.

## How it works

A scheduled GitHub Action (`.github/workflows/update-data.yml`) attempts two weekday refreshes and limited weekend gold/FX refreshes:

1. `run_fetchers.py` writes provenance-wrapped source partitions and `build_data.py` merges them into `data.json`. A failed source retains its previous partition and records health/staleness metadata.
2. `scripts/build_manifest.py` includes only indexable guide and research pages in `manifest.json`.
3. `scripts/prerender.py` writes dated values and source notes into static HTML for non-JavaScript clients.
4. Changes commit to `dev`; `.github/workflows/merge-dev-to-main.yml` fast-forwards `main`, submits changed URLs to IndexNow and lets GitHub Pages redeploy.

Static HTML + vanilla JS + Chart.js. No build step, no framework.

## Search controls

- `sitemap.xml` lists only canonical, indexable pages.
- Retired or consolidated pages use `noindex` and point to the retained page.
- Structured data is limited to types supported by the visible page.
- `robots.txt`, `llms.txt`, Open Graph metadata and IndexNow support machine discovery without creating search-only pages.

## Repository layout

| Path | Purpose |
|---|---|
| `index.html` | Educational investment comparison |
| `tax-calculator.html`, `zakat-calculator.html` | Standalone arithmetic tools |
| `guides/`, `blog/` | Educational articles |
| `assets/` | `site.css`, page scripts, calculators, `og/` share images |
| `data.json`, `manifest.json` | Dated data snapshot + content index |
| `fetchers/`, `build_data.py`, `scripts/` | Source fetchers, merger and page builders |
| `social-kit/` | Off-site distribution: Medium exports + social copy (not served) |

## Disclaimer

Educational content only — **not investment, tax, legal, or religious advice**. Rates and rules change; verify with the issuing authority (SBP, FBR, CDNS, SECP, provincial revenue boards) and, for Zakat/Shariah questions, a qualified scholar, before acting.
