# Daily Social Engine — Design Spec

**Date:** 2026-06-22
**Status:** Approved (pending spec review)
**Goal:** Produce one fresh, low-effort social asset per day for **LinkedIn** (square video + still) and **YouTube Shorts** (vertical video), driven by the live `data.json` numbers the site already fetches daily. No posting automation — assets + caption are generated; the user posts manually in ~3 minutes.

---

## 1. Decisions (locked)

| Decision | Choice | Why |
|---|---|---|
| Posting | **Generate, user posts** | No LinkedIn/YouTube API auth, app review, secrets, or breakage. Full control; can skip a bad day. |
| Daily angle | **Stat-of-the-day rotation** (5 metrics) | Variety from data already fetched; not the same card every day. |
| LinkedIn format | **Square 1:1 video** + still PNG backup | Autoplays muted in feed, big real estate, strong reach. |
| Shorts format | **9:16 vertical video** | Required Shorts format. |
| Caption | **Auto-written, committed to repo** | Permanent searchable log in `social-kit/daily/`. |
| Video delivery | **GitHub Actions artifact (14-day retention)** | Zero repo binary bloat; caption text (tiny) is committed instead. |

**Explicitly out of scope (YAGNI):** auto-posting to any platform; "biggest mover" logic (needs day-over-day history not stored); committing video binaries to git; new SFX work.

---

## 2. Daily outputs

Per run, from that day's `data.json`:

- `short.mp4` — 1080×1920, ~10s — YouTube Shorts
- `linkedin.mp4` — 1080×1080, ~10s — LinkedIn feed
- `card.png` — 1080×1080, single final frame — still backup / thumbnail
- `social-kit/daily/YYYY-MM-DD.md` — ready-to-paste caption: LinkedIn body copy + Shorts title + hashtags

The three media files are uploaded as a GitHub Actions artifact. The caption `.md` is committed to `dev`.

---

## 3. Stat rotation

Deterministic pick: `index = day_of_year % len(METRICS)`. Cycles evenly, predictable, no state needed.

| idx | Metric | data.json source field(s) | On-card takeaway template (honest, not advice) |
|---|---|---|---|
| 0 | Gold per tola | gold rate (PKR/tola) + 1-yr % | "₨{X} today · {±Y}% in a year. A hedge, not a jackpot." |
| 1 | KSE-100 index | kse100 | "Index at {X}. A long-term game, not a daily one." |
| 2 | SBP policy rate | policyRate | "Held at {X}%. Your savings & fund yields track this." |
| 3 | PKR / USD | usd/pkr | "₨{X} per $1. Check it before parking money abroad." |
| 4 | NSS savings rate | nssBehbood / savings rate | "Behbood at {X}%. Safe, fixed, taxable — know the real return." |

Notes:
- Exact `data.json` field names confirmed during implementation against the live file; any metric whose field is missing falls back to the next metric in rotation (graceful, mirrors `fetch_data.py` best-effort ethos).
- Each card shows: metric label, big animated number (reuse `Counter`), trend arrow + color (up = green, down = red, flat = muted), "as of {date}", the takeaway line, and a footer `Not financial advice · pakinvestlysis.com`.
- Takeaway copy is honest and educational; never a price target or buy/sell call (CLAUDE.md tone rule).

---

## 4. Components & data flow

```
data.json ──> scripts/build_daily.py ──> video/daily-props.json   (render input)
                                     └──> social-kit/daily/YYYY-MM-DD.md (caption, committed)

video/daily-props.json ──> remotion render StatCard-9x16 ──> short.mp4
                       ──> remotion render StatCard-1x1  ──> linkedin.mp4
                       ──> remotion still  StatCard-1x1  ──> card.png
```

### 4a. `StatCard` Remotion composition (new)
- One React component, parametrized with a **Zod schema** (same Studio-editable pattern as `Promo`; reuses `schema.ts` conventions, palette, `ColorProvider`, `PaperBg`, `Counter`, fonts).
- Schema props (single object): `metricKey`, `label`, `value` (number), `valuePrefix`, `valueSuffix`, `decimals`, `trend` (`"up" | "down" | "flat"`), `changeLabel` (e.g. "+23.7% / 1yr"), `asOf`, `takeaway`, `footer`, `colors`, `audio` (sfx on/off + volume), `durationInFrames`.
- Lays out responsively from `useVideoConfig()` width/height so the **same component** works at both 9:16 and 1:1.
- Registered as **two compositions** in `Root.tsx`: `StatCard-9x16` (1080×1920) and `StatCard-1x1` (1080×1080), same `schema` + `defaultProps`, differing only in dimensions.
- Duration ~10s (≈300 frames @ 30fps). Light reused SFX from existing kit (whoosh in, tick on count-up, chime on land), gated by the `audio.sfx` toggle. No music.

### 4b. `scripts/build_daily.py` (new)
- Reads root `data.json`.
- Computes today's metric via day-of-year rotation; builds the metric's value/trend/takeaway.
- Writes `video/daily-props.json` (the `--props` input, matching the `StatCard` schema shape).
- Writes `social-kit/daily/YYYY-MM-DD.md` with LinkedIn caption + Shorts title + hashtags, numbers slotted in.
- Pure stdlib Python 3.12 (consistent with `fetch_data.py`); deterministic given a date (date is injectable for local/testing).

### 4c. Local on-demand
- `video/package.json` gets `"daily": "..."` script: runs `build_daily.py` then renders both videos + still into `video/out/daily/`. Lets the user produce today's asset manually anytime (out/ already gitignored).

---

## 5. CI integration

Extend `.github/workflows/update-data.yml` with a new job that runs **after** the data scrape (so numbers are fresh):

1. Checkout `dev`.
2. Setup Node (cache npm) + Python 3.12.
3. `cd video && npm ci`.
4. `python scripts/build_daily.py` → writes `video/daily-props.json` + `social-kit/daily/YYYY-MM-DD.md`.
5. Render: `npx remotion render StatCard-9x16 --props=daily-props.json out/short.mp4`, same for `StatCard-1x1` → `linkedin.mp4`, and `remotion still StatCard-1x1` → `card.png`.
6. `actions/upload-artifact` (short.mp4, linkedin.mp4, card.png; retention 14 days).
7. Commit `social-kit/daily/*.md` to `dev` (skip cleanly if no change), which flows to `main` via the existing merge workflow.

The daily caption commit is small text, consistent with the existing daily `data.json` commit. No `.html` changes, so IndexNow is unaffected.

---

## 6. Posting workflow (the user's 3 minutes)
1. Open the day's `Update Investment Data` Actions run → download the artifact (2 videos + still).
2. Open `social-kit/daily/YYYY-MM-DD.md` for the caption.
3. LinkedIn: upload `linkedin.mp4` (or `card.png`), paste caption.
4. YouTube: upload `short.mp4` as a Short, paste title + hashtags.

---

## 7. Files touched

- **New:** `video/src/StatCard.tsx`, `video/src/statSchema.ts` (or extend `schema.ts`), `scripts/build_daily.py`, `social-kit/daily/` (folder + first dated `.md`).
- **Edit:** `video/src/Root.tsx` (register two `StatCard` compositions), `video/package.json` (`daily` script), `.github/workflows/update-data.yml` (render+caption job).
- **Reuse, unchanged:** `video/src/components/PaperBg.tsx`, `video/src/components/Ledger.tsx`, palette/`ColorProvider` from `schema.ts`, existing SFX in `video/public/`.

---

## 8. Risks / open items
- **`data.json` field names** for gold-per-tola, USD/PKR, and savings rate must be confirmed against the live file during build; rotation skips a metric whose source is missing.
- **CI render time:** `npm ci` + Remotion Chromium download adds ~2-4 min/day to the workflow; acceptable, npm cache mitigates.
- **Takeaway copy** is templated per metric and must stay honest/non-advisory — reviewed at implementation.
