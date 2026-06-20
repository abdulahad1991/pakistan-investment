# Pakistan Investment Advisor

**Live site: [pakinvestlysis.com](https://pakinvestlysis.com)**

Free, daily-updated tools and guides for investing and saving money in Pakistan. Compare National Savings, mutual funds and PSX dividend stocks, calculate your tax and Zakat, and learn the how-to — with every figure traceable to a primary source (SBP, FBR, CDNS, MUFAP, PSX). Educational only; not financial advice.

## What's on the site

- **[Investment Analyzer](https://pakinvestlysis.com/)** — enter an amount, get a personalised allocation across safe income, funds and stocks using today's live rates.
- **[Pakistan Tax Calculator](https://pakinvestlysis.com/tax-calculator.html)** — income tax (salaried + business/AOP, FY2026-27 slabs), GST, provincial sales tax on services, and restaurant bill tax (card vs cash), with a year-on-year comparison chart.
- **[Zakat Calculator](https://pakinvestlysis.com/zakat-calculator.html)** — 2.5% of net zakatable wealth (cash, gold, silver, investments, business assets − debts), with the nisab set from the current gold or silver price.
- **[14 in-depth guides](https://pakinvestlysis.com/guides/)** — National Savings, mutual funds, PSX dividend stocks, T-bills via IPS, gold, halal investing, investment tax (filer vs non-filer), how to become a filer, freelancer/IT-export tax, prize bonds, brokerage account opening, Roshan Digital Account, the SBP policy rate.
- **[Analysis & blog](https://pakinvestlysis.com/blog/)** — Budget 2026-27 breakdowns, PSX bull/bear cases, salaried-class action plans, and a bank-valuation walkthrough.
- **[FAQ hub](https://pakinvestlysis.com/faq.html)** — 223 searchable, topic-filtered answers, each linking to its full guide.

## How it works

A scheduled GitHub Action (`.github/workflows/update-data.yml`) runs every morning (~06:00 PKT):

1. `fetch_data.py` pulls live figures into `data.json` — SBP policy rate, CPI inflation, PKR/USD, KSE-100 (scraped from PSX), National Savings rates (CDNS), stock prices & dividend yields (Yahoo Finance), and mutual-fund 1y/3y/5y returns (finhisaab).
2. `scripts/build_manifest.py` rebuilds `manifest.json` from `guides/` and `blog/`, so new articles list and become searchable automatically.
3. Changes commit to `dev`; `.github/workflows/merge-dev-to-main.yml` fast-forwards `main` and pings **IndexNow** with any changed pages; GitHub Pages redeploys.

Static HTML + vanilla JS + Chart.js. No build step, no framework.

## Built for discoverability (SEO / GEO / AEO)

- JSON-LD on every page (Article / SoftwareApplication / HowTo / FAQPage / BreadcrumbList) and a site-wide Organization entity.
- Answer-first "quick answer" leads and ~10 FAQs per page, kept exactly in sync between visible accordions and FAQPage schema.
- `llms.txt`, branded Open Graph / Twitter share images, an explicit AI-crawler allowlist in `robots.txt`, and automatic IndexNow submission on deploy.

## Repository layout

| Path | Purpose |
|---|---|
| `index.html` | Investment Analyzer (homepage app) |
| `tax-calculator.html`, `zakat-calculator.html`, `faq.html` | Standalone tools + FAQ hub |
| `guides/`, `blog/` | Educational articles |
| `assets/` | `site.css`, page scripts, calculators, `og/` share images |
| `data.json`, `manifest.json` | Daily-refreshed data + content index |
| `fetch_data.py`, `scripts/` | Data scraper and manifest builder |
| `social-kit/` | Off-site distribution: Medium exports + social copy (not served) |

## Disclaimer

Educational content only — **not investment, tax, legal, or religious advice**. Rates and rules change; verify with the issuing authority (SBP, FBR, CDNS, SECP, provincial revenue boards) and, for Zakat/Shariah questions, a qualified scholar, before acting.
