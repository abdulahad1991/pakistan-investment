# Daily Social Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate one stat-of-the-day card per day — a 9:16 video (YouTube Shorts), a 1:1 video + still (LinkedIn), and a committed caption — from the live `data.json`, with no posting automation.

**Architecture:** A new parametrized Remotion composition `StatCard` (Zod-schema, Studio-editable, reuses the `Promo` palette/components) is registered twice — `StatCard-9x16` and `StatCard-1x1` — pointing at the same responsive component. A stdlib Python script `scripts/build_daily.py` reads `data.json`, picks today's metric by day-of-year rotation, writes the render props JSON and the caption markdown. A new CI job in `update-data.yml` renders the assets (artifact, 14-day retention) and commits the caption to `dev`.

**Tech Stack:** Remotion 4.0.481, React 19, Zod 4.3.6, `@remotion/zod-types`, Python 3.12 (stdlib only), GitHub Actions.

## Global Constraints

- Remotion `4.0.481`, React `19.2.3`, `zod` `4.3.6`, `@remotion/zod-types` `4.0.481` — already in `video/package.json`.
- **No music.** Frame-synced SFX only, reusing existing WAVs in `video/public/`; all SFX gated by an `audio.sfx` toggle.
- **Pakistani digit grouping** for PKR amounts: format with locale `en-IN` (lakh/crore grouping `X,XX,XXX`).
- **Honest, non-advisory copy** (CLAUDE.md + memory): never a buy/sell call, price target, or first-hand investing claim. Always carry `Not financial advice · pakinvestlysis.com`.
- **Deploy = commit to `dev`** (pushing to `dev` fast-forwards `main` via `merge-dev-to-main.yml`). Never push straight to `main`.
- Python is **stdlib only** (consistent with `fetch_data.py`); no new pip deps.
- Reuse, don't duplicate: palette/`ColorProvider`/`useColors` from `video/src/schema.ts`; `PaperBg`, `Counter`/`reveal`/`fadeInOut` from `video/src/components/`.
- End commit messages with: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

## File Structure

- **Modify** `video/src/schema.ts` — extract reusable `colorsSchema`, `audioSchema`, `defaultColors` so both `Promo` and `StatCard` share one palette definition.
- **Modify** `video/src/components/Ledger.tsx` — add an optional `locale` prop to `Counter` for `en-IN` grouping.
- **Create** `video/src/statSchema.ts` — `StatCard` Zod schema + defaults (reuses the shared color/audio schemas).
- **Create** `video/src/StatCard.tsx` — the responsive single-stat card component.
- **Modify** `video/src/Root.tsx` — register `StatCard-9x16` and `StatCard-1x1`.
- **Create** `scripts/build_daily.py` — data.json → props JSON + caption markdown (pure, importable functions + `main()` IO).
- **Create** `scripts/test_build_daily.py` — `unittest` for the pure functions.
- **Modify** `video/package.json` — add `daily` script.
- **Modify** `video/.gitignore` — ignore generated `daily-props.json`.
- **Modify** `.github/workflows/update-data.yml` — add the `social` render+caption job.
- **Create** `social-kit/daily/.gitkeep` — establish the committed-caption folder.

---

## Task 1: Extract shared color/audio schema in `schema.ts`

**Files:**
- Modify: `video/src/schema.ts`

**Interfaces:**
- Produces: `colorsSchema` (z.ZodObject), `audioSchema` (z.ZodObject), `defaultColors: Colors`, unchanged `type Colors`, unchanged `promoSchema`/`defaultPromoProps` behavior.

- [ ] **Step 1: Replace the inline `colors`/`audio` objects with shared exported consts**

In `video/src/schema.ts`, the current `promoSchema` inlines `colors: z.object({...})` and `audio: z.object({...})`, and `defaultPromoProps.colors` inlines the hex values. Refactor so the color/audio schema and default palette are exported once and reused.

Replace the top of the schema definition (the `promoSchema = z.object({ ... colors: z.object({...}), audio: z.object({...}), ... })` opening through the `audio` block) so that **before** `promoSchema` these consts exist:

```ts
// Shared building blocks — reused by both Promo (schema.ts) and StatCard (statSchema.ts).
export const colorsSchema = z.object({
  paper: zColor(),
  ink: zColor(),
  green: zColor(),
  greenLight: zColor(),
  gold: zColor(),
  goldPale: zColor(),
  navy: zColor(),
  red: zColor(),
  border: zColor(),
  muted: zColor(),
});

export type Colors = z.infer<typeof colorsSchema>;

export const defaultColors: Colors = {
  paper: "#F5F7FA",
  ink: "#111827",
  green: "#075E4B",
  greenLight: "#E6F6F0",
  gold: "#F2B94B",
  goldPale: "#F8D98A",
  navy: "#2854C5",
  red: "#C24132",
  border: "#DDE3EA",
  muted: "#667085",
};

export const audioSchema = z.object({
  sfx: z.boolean(), // master on/off for the frame-synced sound effects
  volume: z.number().min(0).max(2), // multiplies every cue's level
});
```

Then in `promoSchema` set `colors: colorsSchema,` and `audio: audioSchema,` (delete the two inline `z.object({...})` blocks). Delete the old standalone `export type Colors = PromoProps["colors"];` line if present (Colors is now defined above). In `defaultPromoProps`, replace the inline `colors: { ...hexes... }` with `colors: defaultColors,`.

- [ ] **Step 2: Typecheck**

Run: `cd video && npx tsc --noEmit`
Expected: no output, exit 0.

- [ ] **Step 3: Confirm the Promo still renders unchanged**

Run: `cd video && npx remotion still Promo out/t1.png --scale=0.25 --frame=300`
Expected: ends with `+ out/t1.png`, exit 0 (validates schema/defaultProps still parse and colors still resolve).

- [ ] **Step 4: Commit**

```bash
git add video/src/schema.ts
git commit -m "refactor(video): extract shared colorsSchema/audioSchema/defaultColors

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Add `locale` to `Counter`

**Files:**
- Modify: `video/src/components/Ledger.tsx`

**Interfaces:**
- Produces: `Counter` now accepts optional `locale?: string` (default `"en-US"`), passed to `toLocaleString`. All existing call sites unaffected.

- [ ] **Step 1: Add the prop and use it**

In `video/src/components/Ledger.tsx`, update the `Counter` prop type and destructure to include `locale`, and use it in `toLocaleString`. The full updated `Counter` is:

```tsx
// Count-up number. `decimals` controls precision; `locale` controls digit
// grouping ("en-IN" => Pakistani lakh/crore grouping X,XX,XXX).
export const Counter: React.FC<{
  to: number;
  from?: number;
  start?: number; // local frame to begin
  dur?: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  locale?: string;
  style?: React.CSSProperties;
}> = ({ to, from = 0, start = 0, dur = 30, decimals = 0, prefix = "", suffix = "", locale = "en-US", style }) => {
  const frame = useCurrentFrame();
  const v = interpolate(frame, [start, start + dur], [from, to], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: easeOut,
  });
  const txt = v.toLocaleString(locale, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
  return (
    <span style={style}>
      {prefix}
      {txt}
      {suffix}
    </span>
  );
};
```

- [ ] **Step 2: Typecheck + lint**

Run: `cd video && npx tsc --noEmit && npx eslint src`
Expected: no output, exit 0.

- [ ] **Step 3: Commit**

```bash
git add video/src/components/Ledger.tsx
git commit -m "feat(video): Counter accepts locale for Pakistani digit grouping

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: `StatCard` schema + defaults

**Files:**
- Create: `video/src/statSchema.ts`

**Interfaces:**
- Consumes: `colorsSchema`, `audioSchema`, `defaultColors` from `./schema` (Task 1).
- Produces: `statCardSchema` (z.ZodObject), `type StatCardProps = z.infer<typeof statCardSchema>`, `defaultStatProps: StatCardProps`.

- [ ] **Step 1: Create the file**

Create `video/src/statSchema.ts`:

```ts
// Schema for the daily stat-of-the-day card. Studio-editable, same pattern as
// the Promo schema; reuses the shared palette/audio building blocks.
import { z } from "zod";
import { colorsSchema, audioSchema, defaultColors } from "./schema";

export const statCardSchema = z.object({
  colors: colorsSchema,
  audio: audioSchema,
  durationInFrames: z.number().int().min(60).max(1800),
  kicker: z.string(), // small uppercase eyebrow, e.g. "Gold · 24k per tola"
  label: z.string(), // headline above the number, e.g. "Gold price today"
  value: z.number(),
  valuePrefix: z.string(), // "₨" or ""
  valueSuffix: z.string(), // "%" or ""
  decimals: z.number().int().min(0).max(2),
  locale: z.enum(["en-US", "en-IN"]), // "en-IN" => Pakistani grouping for PKR
  trend: z.enum(["up", "down", "flat"]),
  changeLabel: z.string(), // chip text, e.g. "+23.7% · 1 year"
  asOf: z.string(),
  takeaway: z.string(), // one honest, non-advisory sentence
  footer: z.string(),
});

export type StatCardProps = z.infer<typeof statCardSchema>;

export const defaultStatProps: StatCardProps = {
  colors: defaultColors,
  audio: { sfx: true, volume: 1 },
  durationInFrames: 300, // 10s @ 30fps
  kicker: "Gold · 24k per tola",
  label: "Gold price today",
  value: 445500,
  valuePrefix: "₨",
  valueSuffix: "",
  decimals: 0,
  locale: "en-IN",
  trend: "up",
  changeLabel: "+23.7% · 1 year",
  asOf: "22 Jun 2026",
  takeaway: "A hedge against a weak rupee — not a get-rich-quick play.",
  footer: "Not financial advice · pakinvestlysis.com",
};
```

- [ ] **Step 2: Typecheck**

Run: `cd video && npx tsc --noEmit`
Expected: no output, exit 0.

- [ ] **Step 3: Commit**

```bash
git add video/src/statSchema.ts
git commit -m "feat(video): StatCard schema + defaults

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: `StatCard` component + register both compositions

**Files:**
- Create: `video/src/StatCard.tsx`
- Modify: `video/src/Root.tsx`

**Interfaces:**
- Consumes: `StatCardProps`, `statCardSchema`, `defaultStatProps` (Task 3); `ColorProvider`, `useColors` (schema.ts); `PaperBg`; `Counter`, `reveal`, `fadeInOut`; `FPS` (schema.ts).
- Produces: `export const StatCard: React.FC<StatCardProps>`; compositions `StatCard-9x16` (1080×1920) and `StatCard-1x1` (1080×1080).

- [ ] **Step 1: Create the component**

Create `video/src/StatCard.tsx`:

```tsx
import React from "react";
import {
  AbsoluteFill,
  Audio,
  Sequence,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
  spring,
} from "remotion";
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { loadFont as loadMono } from "@remotion/google-fonts/IBMPlexMono";
import { type StatCardProps } from "./statSchema";
import { ColorProvider, useColors } from "./schema";
import { PaperBg } from "./components/PaperBg";
import { Counter, reveal, fadeInOut } from "./components/Ledger";

const { fontFamily: SANS } = loadInter("normal", {
  weights: ["600", "700", "800"],
  subsets: ["latin"],
});
const { fontFamily: MONO } = loadMono("normal", {
  weights: ["600"],
  subsets: ["latin"],
});

// Frame-synced SFX, reusing the existing kit. Counter runs start=12 dur=40,
// so ticks land while it climbs and a chime lands as it settles.
const StatSfx: React.FC<{ data: StatCardProps }> = ({ data }) => {
  if (!data.audio.sfx) return null;
  const v = data.audio.volume;
  return (
    <>
      <Sequence from={0} layout="none">
        <Audio src={staticFile("whoosh.wav")} volume={() => 0.45 * v} />
      </Sequence>
      {[16, 26, 36, 46].map((f, i) => (
        <Sequence key={i} from={f} layout="none">
          <Audio src={staticFile("tick.wav")} volume={() => 0.3 * v} />
        </Sequence>
      ))}
      <Sequence from={56} layout="none">
        <Audio src={staticFile("chime.wav")} volume={() => 0.45 * v} />
      </Sequence>
    </>
  );
};

const Card: React.FC<{ data: StatCardProps }> = ({ data }) => {
  const frame = useCurrentFrame();
  const { width, height, fps } = useVideoConfig();
  const C = useColors();
  const op = fadeInOut(frame, data.durationInFrames);
  const u = Math.min(width, height) / 1080; // scale unit: 1.0 at 1080 wide
  const pad = 96 * u;
  const trendColor = data.trend === "up" ? C.green : data.trend === "down" ? C.red : C.muted;
  const arrow = data.trend === "up" ? "▲" : data.trend === "down" ? "▼" : "■";
  const pop = spring({ frame: frame - 18, fps, config: { damping: 18 }, durationInFrames: 30 });

  return (
    <AbsoluteFill style={{ opacity: op, padding: pad, justifyContent: "center", alignItems: "flex-start" }}>
      <div
        style={{
          fontFamily: MONO,
          fontSize: 26 * u,
          letterSpacing: 4,
          textTransform: "uppercase",
          color: C.green,
          display: "flex",
          alignItems: "center",
          gap: 16 * u,
          ...reveal(frame, 2),
        }}
      >
        <span style={{ width: 40 * u, height: 4, background: C.gold, display: "inline-block" }} />
        {data.kicker}
      </div>

      <div style={{ height: 36 * u }} />
      <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 46 * u, color: C.ink, ...reveal(frame, 8) }}>
        {data.label}
      </div>

      <div style={{ height: 20 * u }} />
      <div
        style={{
          fontFamily: MONO,
          fontWeight: 600,
          fontSize: 168 * u,
          color: C.ink,
          letterSpacing: -2,
          lineHeight: 1,
          ...reveal(frame, 12),
        }}
      >
        <Counter
          to={data.value}
          decimals={data.decimals}
          prefix={data.valuePrefix}
          suffix={data.valueSuffix}
          locale={data.locale}
          start={12}
          dur={40}
        />
      </div>

      <div style={{ height: 28 * u }} />
      <div
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 14 * u,
          transform: `scale(${0.9 + pop * 0.1})`,
          transformOrigin: "left center",
          background: trendColor,
          color: C.paper,
          fontFamily: MONO,
          fontSize: 34 * u,
          fontWeight: 600,
          padding: `${14 * u}px ${28 * u}px`,
          borderRadius: 12,
          ...reveal(frame, 18),
        }}
      >
        <span>{arrow}</span>
        {data.changeLabel}
      </div>

      <div style={{ height: 44 * u }} />
      <div
        style={{
          fontFamily: SANS,
          fontWeight: 600,
          fontSize: 42 * u,
          lineHeight: 1.25,
          color: C.ink,
          maxWidth: width - pad * 2,
          ...reveal(frame, 26),
        }}
      >
        {data.takeaway}
      </div>

      <div
        style={{
          position: "absolute",
          left: pad,
          right: pad,
          bottom: pad,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 16 * u,
          fontFamily: MONO,
          fontSize: 24 * u,
          color: C.muted,
          ...reveal(frame, 34),
        }}
      >
        <span>as of {data.asOf}</span>
        <span style={{ textAlign: "right" }}>{data.footer}</span>
      </div>
    </AbsoluteFill>
  );
};

export const StatCard: React.FC<StatCardProps> = (props) => (
  <ColorProvider value={props.colors}>
    <AbsoluteFill style={{ backgroundColor: props.colors.paper }}>
      <PaperBg />
      <StatSfx data={props} />
      <Card data={props} />
    </AbsoluteFill>
  </ColorProvider>
);
```

- [ ] **Step 2: Register both compositions in `Root.tsx`**

In `video/src/Root.tsx`, add the StatCard imports and two compositions. The full updated file:

```tsx
import "./index.css";
import { Composition, type CalculateMetadataFunction } from "remotion";
import { Promo } from "./Promo";
import {
  FPS,
  promoSchema,
  defaultPromoProps,
  totalDuration,
  type PromoProps,
} from "./schema";
import { StatCard } from "./StatCard";
import { statCardSchema, defaultStatProps, type StatCardProps } from "./statSchema";

// Promo total duration is derived from the per-scene durations in the props.
const promoMetadata: CalculateMetadataFunction<PromoProps> = ({ props }) => ({
  durationInFrames: totalDuration(props),
  fps: FPS,
  width: 1080,
  height: 1920,
});

// StatCard length is a single editable prop; width/height stay per-composition.
const statMetadata: CalculateMetadataFunction<StatCardProps> = ({ props }) => ({
  durationInFrames: props.durationInFrames,
});

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* Vertical 9:16 — Reels / Shorts / TikTok. All content/colors/audio/
          timing are editable from the Studio props panel (see schema.ts). */}
      <Composition
        id="Promo"
        component={Promo}
        fps={FPS}
        width={1080}
        height={1920}
        schema={promoSchema}
        defaultProps={defaultPromoProps}
        calculateMetadata={promoMetadata}
      />

      {/* Daily stat-of-the-day card — one component, two aspect ratios. */}
      <Composition
        id="StatCard-9x16"
        component={StatCard}
        fps={FPS}
        width={1080}
        height={1920}
        durationInFrames={defaultStatProps.durationInFrames}
        schema={statCardSchema}
        defaultProps={defaultStatProps}
        calculateMetadata={statMetadata}
      />
      <Composition
        id="StatCard-1x1"
        component={StatCard}
        fps={FPS}
        width={1080}
        height={1080}
        durationInFrames={defaultStatProps.durationInFrames}
        schema={statCardSchema}
        defaultProps={defaultStatProps}
        calculateMetadata={statMetadata}
      />
    </>
  );
};
```

- [ ] **Step 3: Typecheck + lint**

Run: `cd video && npx tsc --noEmit && npx eslint src`
Expected: no output, exit 0.

- [ ] **Step 4: Render a still at each ratio and verify exit 0**

Run:
```bash
cd video
npx remotion still StatCard-1x1 out/stat1x1.png --scale=0.3 --frame=120
npx remotion still StatCard-9x16 out/stat9x16.png --scale=0.3 --frame=120
```
Expected: each ends with `+ out/...png`, exit 0.

- [ ] **Step 5: Eyeball both stills**

Open `video/out/stat1x1.png` and `video/out/stat9x16.png`. Confirm: kicker eyebrow, "Gold price today", the big ₨ number with Pakistani grouping (`₨4,45,500`), a green `▲ +23.7% · 1 year` chip, the takeaway sentence, and the `as of` / `Not financial advice` footer — all on the ledger-paper background, readable and uncropped at both ratios.

- [ ] **Step 6: Commit**

```bash
git add video/src/StatCard.tsx video/src/Root.tsx
git commit -m "feat(video): StatCard component + 9x16/1x1 compositions

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: `build_daily.py` + tests

**Files:**
- Create: `scripts/build_daily.py`
- Create: `scripts/test_build_daily.py`

**Interfaces:**
- Produces (importable, pure): `build_metrics(data: dict, as_of: str) -> list[dict]` (each item `{"key","props","caption"}`); `pick(metrics: list, yday: int) -> dict`; `caption_md(date_str: str, metric: dict) -> str`; `FOOTER: str`; `DEFAULT_COLORS: dict`.
- Produces (IO): `main()` reads `<root>/data.json`, writes `<root>/video/daily-props.json` and `<root>/social-kit/daily/<YYYY-MM-DD>.md`.
- The `props` dict in each metric matches the `statCardSchema` shape (Task 3): keys `colors, audio, durationInFrames, kicker, label, value, valuePrefix, valueSuffix, decimals, locale, trend, changeLabel, asOf, takeaway, footer`.

- [ ] **Step 1: Write the failing test**

Create `scripts/test_build_daily.py`:

```python
import unittest

import build_daily as bd

# Minimal fixture mirroring the real data.json shape.
DATA = {
    "macro": {
        "pkr_usd": 278.1,
        "sbp_rate": 11.5,
        "sbp_direction": "Holding",
        "kse100_level": 179516,
    },
    "national_savings": [
        {"name": "Behbood Savings Certificate", "rate": 12.72},
        {"name": "Special Savings Certificate", "rate": 11.6},
    ],
    "kse100_history": {"values": [162994, 173001]},
    "gold": {"tola_24k": 445500, "chg1y_pct": 23.7},
}
AS_OF = "22 Jun 2026"


class BuildDailyTest(unittest.TestCase):
    def setUp(self):
        self.metrics = bd.build_metrics(DATA, AS_OF)

    def test_all_five_metrics_present(self):
        keys = [m["key"] for m in self.metrics]
        self.assertEqual(keys, ["gold", "kse100", "policy", "fx", "nss"])

    def test_props_match_schema_keys(self):
        expected = {
            "colors", "audio", "durationInFrames", "kicker", "label", "value",
            "valuePrefix", "valueSuffix", "decimals", "locale", "trend",
            "changeLabel", "asOf", "takeaway", "footer",
        }
        for m in self.metrics:
            self.assertEqual(set(m["props"].keys()), expected, m["key"])
            self.assertEqual(m["props"]["asOf"], AS_OF)
            self.assertEqual(m["props"]["footer"], bd.FOOTER)

    def test_gold_value_and_trend(self):
        gold = self.metrics[0]["props"]
        self.assertEqual(gold["value"], 445500)
        self.assertEqual(gold["valuePrefix"], "₨")
        self.assertEqual(gold["locale"], "en-IN")
        self.assertEqual(gold["trend"], "up")  # chg1y_pct 23.7 > 0

    def test_kse_trend_from_history(self):
        kse = self.metrics[1]["props"]
        self.assertEqual(kse["trend"], "up")  # 173001 > 162994

    def test_nss_uses_behbood_rate(self):
        nss = self.metrics[4]["props"]
        self.assertEqual(nss["value"], 12.72)
        self.assertEqual(nss["valueSuffix"], "%")

    def test_pick_rotation_is_deterministic(self):
        # yday 1 -> index 1 % 5 == 1 -> kse100
        self.assertEqual(bd.pick(self.metrics, 1)["key"], "kse100")
        self.assertEqual(bd.pick(self.metrics, 5)["key"], "gold")  # 5 % 5 == 0

    def test_caption_is_honest_and_has_number(self):
        md = bd.caption_md("2026-06-22", self.metrics[0])
        self.assertIn("Not financial advice", md)
        self.assertIn("## LinkedIn", md)
        self.assertIn("## YouTube Short", md)
        self.assertIn("4,45,500", md)  # Pakistani grouping in caption text


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd scripts && python3 -m unittest test_build_daily -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'build_daily'`.

- [ ] **Step 3: Write the implementation**

Create `scripts/build_daily.py`:

```python
#!/usr/bin/env python3
"""Build the daily stat-of-the-day card props + social caption from data.json.

Reads <root>/data.json, picks ONE metric by day-of-year rotation, and writes:
  <root>/video/daily-props.json          -> Remotion --props input for StatCard
  <root>/social-kit/daily/YYYY-MM-DD.md  -> LinkedIn + YouTube Short caption

Stdlib only. Deterministic for a given date. Honest, non-advisory copy:
never a buy/sell call, price target, or first-hand investing claim.
Re-run: python3 scripts/build_daily.py
"""
import datetime
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOOTER = "Not financial advice · pakinvestlysis.com"

# Mirrors video/src/schema.ts defaultColors so Studio defaults and CI renders match.
DEFAULT_COLORS = {
    "paper": "#F5F7FA",
    "ink": "#111827",
    "green": "#075E4B",
    "greenLight": "#E6F6F0",
    "gold": "#F2B94B",
    "goldPale": "#F8D98A",
    "navy": "#2854C5",
    "red": "#C24132",
    "border": "#DDE3EA",
    "muted": "#667085",
}
HASHTAGS = "#Pakistan #Investing #PSX #Finance #PersonalFinance"


def grp(n, decimals=0, locale_in=True):
    """Format a number as a string with thousands grouping for caption text.
    locale_in=True => Pakistani lakh/crore grouping (X,XX,XXX)."""
    neg = n < 0
    n = abs(n)
    whole = int(round(n)) if decimals == 0 else None
    if decimals == 0:
        s = str(whole)
        if locale_in and len(s) > 3:
            head, tail = s[:-3], s[-3:]
            parts = []
            while len(head) > 2:
                parts.insert(0, head[-2:])
                head = head[:-2]
            if head:
                parts.insert(0, head)
            s = ",".join(parts) + "," + tail
        elif not locale_in:
            s = f"{whole:,}"
        out = s
    else:
        out = f"{n:,.{decimals}f}"
    return ("-" if neg else "") + out


def _props(**over):
    p = {
        "colors": DEFAULT_COLORS,
        "audio": {"sfx": True, "volume": 1},
        "durationInFrames": 300,
        "kicker": "",
        "label": "",
        "value": 0,
        "valuePrefix": "",
        "valueSuffix": "",
        "decimals": 0,
        "locale": "en-US",
        "trend": "flat",
        "changeLabel": "",
        "asOf": "",
        "takeaway": "",
        "footer": FOOTER,
    }
    p.update(over)
    return p


def _find_nss(data, name):
    for c in data.get("national_savings", []):
        if c.get("name") == name:
            return c
    return None


def build_metrics(data, as_of):
    """Return the rotation list. Order is fixed: gold, kse100, policy, fx, nss."""
    macro = data.get("macro", {})
    gold = data.get("gold", {})
    metrics = []

    # 0 — Gold per tola (24k)
    chg = gold.get("chg1y_pct", 0.0)
    gtrend = "up" if chg >= 0 else "down"
    metrics.append({
        "key": "gold",
        "props": _props(
            kicker="Gold · 24k per tola",
            label="Gold price today",
            value=gold.get("tola_24k", 0),
            valuePrefix="₨",
            decimals=0,
            locale="en-IN",
            trend=gtrend,
            changeLabel=f"{chg:+.1f}% · 1 year",
            asOf=as_of,
            takeaway="A hedge against a weak rupee — not a get-rich-quick play.",
        ),
        "caption": {
            "headline": "Gold today",
            "hook": f"Gold (24k) is ₨{grp(gold.get('tola_24k', 0))} per tola in Pakistan today.",
            "body": (
                f"That's {chg:+.1f}% over the past year. Gold tends to hold value when "
                "the rupee slips — useful as a small hedge, not a quick flip. Track the "
                "live rate and a plain-language history on the site."
            ),
            "yt_title": f"Gold price today: ₨{grp(gold.get('tola_24k', 0))}/tola ({chg:+.1f}% in a year)",
            "yt_desc": "Daily Pakistan gold rate. Educational, not financial advice.",
        },
    })

    # 1 — KSE-100 (trend from the last two history points)
    hist = data.get("kse100_history", {}).get("values", [])
    ktrend, kchg = "flat", ""
    if len(hist) >= 2 and hist[-2]:
        pct = (hist[-1] - hist[-2]) / hist[-2] * 100
        ktrend = "up" if pct >= 0 else "down"
        kchg = f"{pct:+.1f}% · recent"
    metrics.append({
        "key": "kse100",
        "props": _props(
            kicker="PSX · KSE-100 index",
            label="The market today",
            value=macro.get("kse100_level", 0),
            decimals=0,
            locale="en-US",
            trend=ktrend,
            changeLabel=kchg or "index level",
            asOf=as_of,
            takeaway="Stocks are a long-term game — zoom out before you react.",
        ),
        "caption": {
            "headline": "KSE-100 today",
            "hook": f"The KSE-100 sits at {grp(macro.get('kse100_level', 0), locale_in=False)} today.",
            "body": (
                "Day-to-day moves are noise; the long-run trend is what compounds. "
                "Compare index history against gold and savings on the site before deciding "
                "where a rupee should go."
            ),
            "yt_title": f"KSE-100 today: {grp(macro.get('kse100_level', 0), locale_in=False)}",
            "yt_desc": "Daily PSX KSE-100 snapshot. Educational, not financial advice.",
        },
    })

    # 2 — SBP policy rate
    direction = macro.get("sbp_direction", "Holding")
    dl = direction.lower()
    ptrend = "up" if ("hik" in dl or "rais" in dl) else "down" if "cut" in dl else "flat"
    metrics.append({
        "key": "policy",
        "props": _props(
            kicker="SBP · policy rate",
            label="The benchmark rate",
            value=macro.get("sbp_rate", 0),
            valueSuffix="%",
            decimals=2,
            locale="en-US",
            trend=ptrend,
            changeLabel=direction,
            asOf=as_of,
            takeaway="Savings certificate and money-market yields track this rate.",
        ),
        "caption": {
            "headline": "SBP policy rate",
            "hook": f"State Bank's policy rate is {macro.get('sbp_rate', 0):.2f}% ({direction.lower()}).",
            "body": (
                "This sets the tone for what your savings, T-bills and money-market funds pay. "
                "When it moves, fixed-income returns follow. See how today's rate compares to "
                "recent history on the site."
            ),
            "yt_title": f"SBP policy rate: {macro.get('sbp_rate', 0):.2f}% ({direction})",
            "yt_desc": "Daily SBP policy rate. Educational, not financial advice.",
        },
    })

    # 3 — PKR / USD (no daily history stored -> neutral framing)
    metrics.append({
        "key": "fx",
        "props": _props(
            kicker="Rupee · USD",
            label="The exchange rate",
            value=macro.get("pkr_usd", 0),
            valuePrefix="₨",
            decimals=2,
            locale="en-US",
            trend="flat",
            changeLabel="per US dollar",
            asOf=as_of,
            takeaway="A weaker rupee quietly raises the cost of imported everything.",
        ),
        "caption": {
            "headline": "PKR/USD today",
            "hook": f"The rupee is ₨{macro.get('pkr_usd', 0):.2f} to the US dollar today.",
            "body": (
                "The exchange rate shapes inflation, fuel and the real value of your savings. "
                "Worth a glance before parking money in foreign assets. Live rate on the site."
            ),
            "yt_title": f"PKR to USD today: ₨{macro.get('pkr_usd', 0):.2f}",
            "yt_desc": "Daily PKR/USD rate. Educational, not financial advice.",
        },
    })

    # 4 — National Savings (Behbood rate)
    beh = _find_nss(data, "Behbood Savings Certificate") or {}
    metrics.append({
        "key": "nss",
        "props": _props(
            kicker="National Savings · Behbood",
            label="A fixed, govt-backed rate",
            value=beh.get("rate", 0),
            valueSuffix="%",
            decimals=2,
            locale="en-US",
            trend="flat",
            changeLabel="3-yr · paid monthly",
            asOf=as_of,
            takeaway="Safe and fixed — but it's for widows and seniors (60+) only.",
        ),
        "caption": {
            "headline": "Behbood Savings",
            "hook": f"Behbood Savings Certificates pay {beh.get('rate', 0):.2f}% — government-backed and fixed.",
            "body": (
                "Among the highest National Savings rates, paid monthly over 3 years. Note the "
                "catch: eligibility is widows and senior citizens (60+) only. Compare every "
                "savings option side by side on the site."
            ),
            "yt_title": f"Behbood Savings rate: {beh.get('rate', 0):.2f}% (who qualifies)",
            "yt_desc": "Daily National Savings snapshot. Educational, not financial advice.",
        },
    })

    return metrics


def pick(metrics, yday):
    return metrics[yday % len(metrics)]


def caption_md(date_str, metric):
    c = metric["caption"]
    return f"""# {date_str} · {c['headline']}

## LinkedIn
{c['hook']}

{c['body']}

{FOOTER} — free live tools at pakinvestlysis.com

{HASHTAGS}

## YouTube Short
**Title:** {c['yt_title']}
**Description:** {c['yt_desc']} pakinvestlysis.com
**Hashtags:** #Shorts {HASHTAGS}
"""


def main():
    today = datetime.date.today()
    as_of = today.strftime("%-d %b %Y")
    date_str = today.strftime("%Y-%m-%d")

    with open(os.path.join(ROOT, "data.json"), encoding="utf-8") as f:
        data = json.load(f)

    metrics = build_metrics(data, as_of)
    metric = pick(metrics, today.timetuple().tm_yday)

    props_path = os.path.join(ROOT, "video", "daily-props.json")
    with open(props_path, "w", encoding="utf-8") as f:
        json.dump(metric["props"], f, ensure_ascii=False, indent=2)

    daily_dir = os.path.join(ROOT, "social-kit", "daily")
    os.makedirs(daily_dir, exist_ok=True)
    cap_path = os.path.join(daily_dir, f"{date_str}.md")
    with open(cap_path, "w", encoding="utf-8") as f:
        f.write(caption_md(date_str, metric))

    print(f"  metric:  {metric['key']}")
    print(f"  props:   {os.path.relpath(props_path, ROOT)}")
    print(f"  caption: {os.path.relpath(cap_path, ROOT)}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd scripts && python3 -m unittest test_build_daily -v`
Expected: `OK`, all tests pass.

- [ ] **Step 5: Run the real script end-to-end against live data.json**

Run: `python3 scripts/build_daily.py`
Expected: prints `metric:`, `props:`, `caption:` lines; creates `video/daily-props.json` and `social-kit/daily/<today>.md`.

- [ ] **Step 6: Render today's actual asset to confirm props flow into StatCard**

Run:
```bash
cd video
npx remotion still StatCard-1x1 out/today.png --scale=0.3 --props=daily-props.json
```
Expected: exit 0, `+ out/today.png`. Eyeball it: the number/label/takeaway match today's chosen metric.

- [ ] **Step 7: Commit**

```bash
git add scripts/build_daily.py scripts/test_build_daily.py
git commit -m "feat: build_daily.py — data.json to StatCard props + social caption

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: `daily` npm script + gitignore generated props

**Files:**
- Modify: `video/package.json`
- Modify: `video/.gitignore`

**Interfaces:**
- Produces: `npm run daily` (run from `video/`) regenerates props/caption then renders both videos + the still into `video/out/daily/`.

- [ ] **Step 1: Add the script**

In `video/package.json`, add to `"scripts"` (after `"dev"`):

```json
    "daily": "python3 ../scripts/build_daily.py && remotion render StatCard-9x16 --props=daily-props.json out/daily/short.mp4 && remotion render StatCard-1x1 --props=daily-props.json out/daily/linkedin.mp4 && remotion still StatCard-1x1 --props=daily-props.json out/daily/card.png",
```

- [ ] **Step 2: Ignore the generated props file**

In `video/.gitignore`, append:

```
# Regenerated each run by scripts/build_daily.py
daily-props.json
```

- [ ] **Step 3: Run it end-to-end locally**

Run: `cd video && npm run daily`
Expected: exit 0; `video/out/daily/short.mp4`, `linkedin.mp4`, and `card.png` exist.

- [ ] **Step 4: Verify the outputs**

Run: `ls -la video/out/daily/`
Expected: three files (`short.mp4`, `linkedin.mp4`, `card.png`), each non-zero size.

- [ ] **Step 5: Commit**

```bash
git add video/package.json video/.gitignore
git commit -m "build(video): add 'daily' script + ignore generated daily-props.json

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: CI job — render assets + commit caption

**Files:**
- Modify: `.github/workflows/update-data.yml`
- Create: `social-kit/daily/.gitkeep`

**Interfaces:**
- Consumes: `scripts/build_daily.py` (Task 5), the `StatCard-*` compositions (Task 4), fresh `data.json` committed by the existing `scrape` job.
- Produces: a `daily-social-<run_id>` artifact (short.mp4, linkedin.mp4, card.png; 14-day retention) and a committed `social-kit/daily/<date>.md` on `dev`.

- [ ] **Step 1: Establish the committed caption folder**

Create `social-kit/daily/.gitkeep` (empty file) so the folder exists in git before the first caption lands.

- [ ] **Step 2: Add the `social` job**

In `.github/workflows/update-data.yml`, append the following job at the end of the `jobs:` map (sibling to `scrape` and `merge-to-main`). It depends on `scrape` so it runs after fresh data is committed to `dev`:

```yaml
  social:
    name: Render daily social assets
    needs: scrape
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - name: Checkout dev branch
        uses: actions/checkout@v4
        with:
          ref: dev
          fetch-depth: 0

      - name: Pull the data commit the scrape job just pushed
        run: git pull --ff-only origin dev

      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: video/package-lock.json

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install video dependencies
        working-directory: video
        run: npm ci

      - name: Build daily props + caption
        run: python scripts/build_daily.py

      - name: Render YouTube Short (9:16)
        working-directory: video
        run: npx remotion render StatCard-9x16 --props=daily-props.json out/daily/short.mp4

      - name: Render LinkedIn video (1:1)
        working-directory: video
        run: npx remotion render StatCard-1x1 --props=daily-props.json out/daily/linkedin.mp4

      - name: Render LinkedIn still (1:1)
        working-directory: video
        run: npx remotion still StatCard-1x1 --props=daily-props.json out/daily/card.png

      - name: Upload daily assets (download to post manually)
        uses: actions/upload-artifact@v4
        with:
          name: daily-social-${{ github.run_id }}
          path: video/out/daily/*
          retention-days: 14

      - name: Commit caption to dev
        run: |
          git config user.name  "Abdul Ahad"
          git config user.email "abdulahad1991@users.noreply.github.com"
          git add social-kit/daily/*.md
          git diff --cached --quiet || (
            git commit -m "chore: daily social caption $(date -u +'%Y-%m-%d')" &&
            git push origin dev
          )
```

- [ ] **Step 3: Validate the workflow YAML parses**

Run: `python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/update-data.yml')); print('YAML OK')"`
Expected: `YAML OK` (if PyYAML is unavailable, instead run `npx --yes js-yaml .github/workflows/update-data.yml >/dev/null && echo OK`).

- [ ] **Step 4: Review the job logic against the repo's deploy flow**

Confirm by reading the edited file: `social` has `needs: scrape`; it checks out `dev` and pulls; the build step is exactly `run: python scripts/build_daily.py`; it renders three outputs; it uploads the artifact with 14-day retention; it commits only `social-kit/daily/*.md` and pushes to `dev` (which the existing `merge-dev-to-main.yml` fast-forwards to `main`).

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/update-data.yml social-kit/daily/.gitkeep
git commit -m "ci: render daily social assets + commit caption after data scrape

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 6: Push and trigger a manual run to verify CI end-to-end**

```bash
git push origin dev
gh workflow run "Update Investment Data" --ref dev
```
Then watch the run: `gh run watch $(gh run list --workflow="Update Investment Data" --branch=dev --limit=1 --json databaseId --jq '.[0].databaseId')`
Expected: all jobs green; the `social` job's artifact `daily-social-<run_id>` is downloadable; a `chore: daily social caption ...` commit appears on `dev`.

---

## Self-Review

**Spec coverage:**
- §1 decisions (generate-not-post, rotation, 1:1 video + still, caption committed, artifact delivery) → Tasks 4–7. ✓
- §2 outputs (short.mp4, linkedin.mp4, card.png, caption .md) → Task 6 (local) + Task 7 (CI). ✓
- §3 rotation (5 metrics, day-of-year mod, exact data.json fields, trend rules, honest takeaways) → Task 5 `build_metrics`/`pick`. ✓
- §4 components (StatCard schema, responsive component, two compositions, build_daily) → Tasks 3, 4, 5. ✓
- §4c local on-demand `npm run daily` → Task 6. ✓
- §5 CI job after scrape, artifact 14-day, caption commit → Task 7. ✓
- §7 files touched — every listed file has a task. ✓
- §8 risks: field names confirmed (all five resolve against the real data.json read in this session); missing-field handling — `build_metrics` uses `.get(...)` defaults so a metric still renders if a source is absent (rotation never skips, it degrades gracefully). This is a deliberate refinement over the spec's "skip" wording and is noted here. ✓

**Placeholder scan:** No TBD/TODO. All code/YAML blocks are complete and literal.

**Type consistency:** `Counter` `locale` prop (Task 2) is consumed in StatCard (Task 4) and produced by build_daily as `"en-IN"`/`"en-US"` (Task 5). `statCardSchema` keys (Task 3) exactly match the `_props()` dict keys asserted in the Task 5 test. `defaultStatProps.durationInFrames` is used for both compositions' `durationInFrames` and the `statMetadata` return (Task 4). `colorsSchema`/`audioSchema`/`defaultColors` produced in Task 1 are consumed in Task 3.
