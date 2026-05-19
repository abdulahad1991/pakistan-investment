# Guide Content Upgrade — Design Spec
**Date:** 2026-05-20
**Trigger:** Google Search Console manual action "Low value content" (18 May 2026)
**Goal:** Pass Google's manual reconsideration review by making all guide pages authoritative, deep, and E-E-A-T compliant.

---

## Problem Summary

pakinvestlysis.com received a "Low value content" manual penalty. Root causes:
1. Guide pages 129–260 lines = ~500–800 words of prose — too thin for competitive finance queries
2. Generic AI-summarized content, no original analysis or author credentials
3. High ad density (3+ slots) on thin pages
4. No `<noscript>` fallback — main tool invisible to crawlers
5. Shallow internal linking

---

## Approach

**Option A — Full rewrite, one guide at a time, thinnest first.** Each guide becomes a standalone authoritative resource with layered content (beginner intro → deep analysis), author bio, live data widget, 2 ad slots, inline citations, and internal links.

---

## Page Structure (all 5 guides)

```
<header>                          shared nav
<article>
  [Ad slot 1 — top banner]
  <h1> + author byline + date
  <author-bio-card>
  [Quick summary box — 3 bullet TL;DR]
  [Section: Beginner intro — 200-300 words]
  [Section: How it works — 300-400 words]
  [Section: Live data widget — pulls from data.json]
  [Section: Comparison table — static, dated "Last verified: DD Mon YYYY"]
  [Section: Step-by-step guide — actionable how-to]
  [Section: Risks & what to watch — 200 words]
  [Section: Expert tips — 3-5 tips from builder's experience]
  [FAQ — 4-6 questions with FAQ schema]
  [Related guides — 2 links to other guides]
  [Ad slot 2 — bottom]
</article>
<footer>
```

**Target word count:** 1,500–2,000 words of prose per guide (excluding HTML markup).

---

## E-E-A-T Signals

### Author Bio Card
Appears after H1 on every guide page:
```
Abdul Ahad — Software engineer & Pakistani investor
Built pakinvestlysis.com | Personally invested in PSX & Al Meezan funds
[LinkedIn ↗]  |  Last updated: May 2026
```

### Inline Citations
Every factual claim links to primary source:
- SBP policy rate → sbp.org.pk
- CDNS rates → savings.gov.pk
- Mutual fund data → mufap.com.pk
- PSX data → psx.com.pk

### JSON-LD
Each guide's existing Article schema gets:
- `dateModified` kept current
- `author.sameAs` pointing to LinkedIn URL

### "Last verified" Notice
Appears above every comparison table:
> Last verified: 20 May 2026 — rates change monthly, confirm before investing

### Disclaimer Placement
Short disclaimer moved next to live data widget (contextually relevant), not buried in footer only.

---

## Live Data Widget

One widget per guide pulling relevant slice from existing `data.json`. Rendered by a small inline `<script>` (20–40 lines) at page bottom — no new dependencies.

| Guide | Widget shows |
|-------|-------------|
| national-savings-vs-mutual-funds | Current CDNS rates vs top money-market fund return |
| how-to-invest-mutual-funds | Top 3 funds by 1-year return |
| best-dividend-stocks-psx | Top 5 dividend yields + last closing price |
| sbp-policy-rate-investments | Current SBP rate + trend vs 6 months ago |
| roshan-digital-account-guide | RDA profit rates for USD/GBP/EUR |

`<noscript>` fallback: static table with last-known values + "Enable JS for live rates" notice. Fixes crawler gap.

---

## Ad Placement

**2 ad slots per guide, no exceptions:**
- Slot 1: After author bio card, before first content section
- Slot 2: After FAQ, before footer

**guides/index.html (hub page):** No ads. Keep clean — it's a navigation/hub page.

---

## Rewrite Order (thinnest first)

| Priority | File | Current lines | Target words |
|----------|------|--------------|-------------|
| 1 | `guides/index.html` | 129 | Hub page: 300-word intro + cards linking all 5 guides |
| 2 | `guides/national-savings-vs-mutual-funds.html` | 222 | 1,800 words |
| 3 | `guides/sbp-policy-rate-investments.html` | 233 | 1,600 words |
| 4 | `guides/best-dividend-stocks-psx.html` | 253 | 1,800 words |
| 5 | `guides/how-to-invest-mutual-funds-pakistan.html` | 257 | 1,700 words |
| 6 | `guides/roshan-digital-account-guide.html` | 260 | 1,700 words |

---

## Internal Linking

Each guide links to:
- 2 related guides (bottom "Related guides" section)
- Main tool (pakinvestlysis.com)

Hub page (`guides/index.html`) links to all 5 guides with description cards.

---

## Author Bio Details

- **Name:** Abdul Ahad
- **Role:** Software engineer, personal investor
- **Investments:** PSX stocks, Al Meezan mutual funds
- **LinkedIn:** https://www.linkedin.com/in/abdulahad1991/
- **Site:** pakinvestlysis.com (built by author)

---

## Success Criteria

- All 6 guide files rewritten and committed
- Every guide: 1,500+ words prose, author bio, 2 ad slots, 1 live widget, `<noscript>` fallback, inline citations, FAQ schema
- Google reconsideration request submitted after deployment
