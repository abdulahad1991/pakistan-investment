# Pakistan Investment Advisor

**Live site: [pakinvestlysis.com](https://pakinvestlysis.com)**

Free, daily-updated investment analysis for Pakistani investors. Compare National Savings certificates, SECP-regulated mutual funds, and PSX dividend stocks — personalised to your budget, with every figure traceable to a primary source (SBP, CDNS, MUFAP, PSX).

## What's on the site

- **[Investment Analyzer](https://pakinvestlysis.com/)** — enter an amount, get a personalised allocation across safe income, funds and stocks using today's live rates
- **[11 in-depth guides](https://pakinvestlysis.com/guides/)** — National Savings, mutual funds, PSX dividend stocks, T-bills via IPS accounts, gold, halal investing, investment taxation (filer vs non-filer), brokerage account opening, Roshan Digital Account
- **[Analysis & blog](https://pakinvestlysis.com/blog/)** — Budget 2026-27 breakdown for investors, PSX bull/bear cases, action plans for the salaried class
- **[Methodology](https://pakinvestlysis.com/methodology.html)** — how the data pipeline sources and verifies every number

## How it works

A scheduled GitHub Action (`.github/workflows/update-data.yml`) runs every morning at 06:00 PKT:

1. `fetch_data.py` pulls live figures — SBP policy rate, CPI inflation, PKR/USD, KSE-100, National Savings profit rates, mutual fund returns, stock prices and dividend yields — into `data.json`
2. `scripts/build_manifest.py` scans `guides/` and `blog/` and rebuilds `manifest.json`, so new articles list themselves automatically
3. Changes commit to `dev`, fast-forward merge to `main`, and GitHub Pages redeploys

Static HTML + vanilla JS + Chart.js. No build step, no framework.

## Disclaimer

Educational content only — not financial advice. Verify every rate with the issuing institution before investing.
