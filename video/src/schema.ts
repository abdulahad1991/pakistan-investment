// Single source of truth for everything the Promo exposes to Remotion Studio.
// The Zod schema below drives the editable props panel in the sidebar; every
// field here shows up as a control you can tweak and re-render live.
import { createContext, useContext } from "react";
import { z } from "zod";
import { zColor } from "@remotion/zod-types";

// 30fps. The reveal/counter timing constants in the scenes are tuned for this,
// so it is intentionally NOT exposed as an editable prop.
export const FPS = 30;

// --------------------------------------------------------------------------
// Schema — grouped so Studio renders collapsible sections per concern.
// --------------------------------------------------------------------------
const sceneDuration = z.number().int().min(15).max(600);

const marketRow = z.object({
  label: z.string(),
  value: z.number(),
  decimals: z.number().int().min(0).max(4),
  prefix: z.string(),
  suffix: z.string(),
  up: z.boolean(), // green "positive" styling + payoff chime instead of a tick
});

const compareBar = z.object({
  label: z.string(),
  sub: z.string(),
  value: z.number(),
  color: zColor(),
});

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

export const promoSchema = z.object({
  // ---- Brand palette (live-editable color pickers) --------------------
  colors: colorsSchema,

  // ---- Audio ----------------------------------------------------------
  audio: audioSchema,

  // ---- Scene 1 · Hook -------------------------------------------------
  hook: z.object({
    durationInFrames: sceneDuration,
    kicker: z.string(),
    lines: z.array(z.string()),
    goldLineIndex: z.number().int().min(-1), // which line gets the gold marker (-1 = none)
  }),

  // ---- Scene 2 · Market snapshot --------------------------------------
  market: z.object({
    durationInFrames: sceneDuration,
    heading: z.string(),
    asOf: z.string(),
    rows: z.array(marketRow),
  }),

  // ---- Scene 3 · 1-year comparison ------------------------------------
  compare: z.object({
    durationInFrames: sceneDuration,
    kicker: z.string(),
    headlineLine1: z.string(),
    headlineLine2: z.string(),
    footnote: z.string(),
    bars: z.array(compareBar),
  }),

  // ---- Scene 4 · Value prop -------------------------------------------
  value: z.object({
    durationInFrames: sceneDuration,
    headlineTop: z.string(),
    headlineBottom: z.string(), // rendered in green
    items: z.array(z.string()),
    badge: z.string(),
  }),

  // ---- Scene 5 · CTA --------------------------------------------------
  cta: z.object({
    durationInFrames: sceneDuration,
    brand: z.string(),
    subtitle: z.string(),
    button: z.string(),
  }),
});

export type PromoProps = z.infer<typeof promoSchema>;

// --------------------------------------------------------------------------
// Defaults — reproduce the original hard-coded promo exactly. These are the
// values Studio loads first; everything is overridable from the panel.
// Numbers mirror data.json as of 20 Jun 2026 (promo, not advice).
// --------------------------------------------------------------------------
export const defaultPromoProps: PromoProps = {
  colors: defaultColors,
  audio: { sfx: true, volume: 1 },
  hook: {
    durationInFrames: 90,
    kicker: "Pakinvestlysis · Market Brief",
    lines: ["Where should a", "Pakistani rupee", "go in 2026?"],
    goldLineIndex: 1,
  },
  market: {
    durationInFrames: 138,
    heading: "The board, today.",
    asOf: "22 Jun 2026",
    rows: [
      { label: "SBP policy rate", value: 11.5, decimals: 1, prefix: "", suffix: "%", up: false },
      { label: "Inflation (CPI)", value: 7.0, decimals: 1, prefix: "", suffix: "%", up: false },
      { label: "KSE-100 index", value: 178471, decimals: 0, prefix: "", suffix: "", up: false },
      { label: "Gold · 1-year", value: 34.7, decimals: 1, prefix: "+", suffix: "%", up: true },
    ],
  },
  compare: {
    durationInFrames: 162,
    kicker: "1-Year Returns",
    headlineLine1: "Same rupee.",
    headlineLine2: "Very different years.",
    footnote: "Past performance ≠ future returns.",
    bars: [
      { label: "Islamic Income", sub: "low risk", value: 8.4, color: "#075E4B" },
      { label: "National Savings", sub: "Behbood", value: 12.72, color: "#2854C5" },
      { label: "Islamic Equity", sub: "Al Meezan", value: 33.7, color: "#F2B94B" },
    ],
  },
  value: {
    durationInFrames: 120,
    headlineTop: "Stop guessing.",
    headlineBottom: "Start comparing.",
    items: [
      "Daily market & macro data",
      "Real-return charts, not headline %",
      "A portfolio score in under a minute",
    ],
    badge: "FREE · NO SIGNUP",
  },
  cta: {
    durationInFrames: 120,
    brand: "Pakinvestlysis",
    subtitle: "Build your 2026 portfolio",
    button: "pakinvestlysis.com →",
  },
};

// --------------------------------------------------------------------------
// Color context — so scenes/components read the live palette without threading
// `colors` through every prop.
// --------------------------------------------------------------------------
const ColorContext = createContext<Colors>(defaultColors);
export const ColorProvider = ColorContext.Provider;
export const useColors = () => useContext(ColorContext);

// --------------------------------------------------------------------------
// Layout — scene start frames are derived from the editable per-scene
// durations, so shortening/lengthening any scene reflows the rest.
// --------------------------------------------------------------------------
export const SCENE_ORDER = ["hook", "market", "compare", "value", "cta"] as const;
export type SceneKey = (typeof SCENE_ORDER)[number];

export const sceneStarts = (props: PromoProps): Record<SceneKey, number> => {
  let acc = 0;
  const out = {} as Record<SceneKey, number>;
  for (const k of SCENE_ORDER) {
    out[k] = acc;
    acc += props[k].durationInFrames;
  }
  return out;
};

export const totalDuration = (props: PromoProps): number =>
  SCENE_ORDER.reduce((sum, k) => sum + props[k].durationInFrames, 0);

// --------------------------------------------------------------------------
// SFX cues — built from the live scene layout + content so the soundtrack
// stays synced when durations/rows/bars/items are edited in Studio.
// --------------------------------------------------------------------------
export type Cue = { at: number; src: string; vol: number; rate?: number };

export const buildCues = (props: PromoProps): Cue[] => {
  const start = sceneStarts(props);
  const cues: Cue[] = [];

  // whoosh leads every cut into a new scene
  (["market", "compare", "value", "cta"] as SceneKey[]).forEach((k) => {
    cues.push({ at: Math.max(0, start[k] - 2), src: "whoosh.wav", vol: 0.45 });
  });

  // market rows: tick as each row reveals; the "up" row lands a chime instead
  props.market.rows.forEach((row, i) => {
    const at = start.market + 14 + i * 12;
    cues.push(row.up ? { at, src: "chime.wav", vol: 0.4 } : { at, src: "tick.wav", vol: 0.3 });
  });

  // comparison bars draw in (sweep) then tick per bar as its counter climbs
  cues.push({ at: start.compare + 18, src: "sweep.wav", vol: 0.5 });
  props.compare.bars.forEach((_, i) => {
    cues.push({ at: start.compare + 22 + i * 8, src: "tick.wav", vol: 0.3 });
  });

  // value checklist items flip on (click), pitched up slightly per item
  props.value.items.forEach((_, i) => {
    cues.push({ at: start.value + 18 + i * 10, src: "click.wav", vol: 0.5, rate: 1 + i * 0.08 });
  });

  // CTA: logo pop, button click, final payoff chime
  cues.push({ at: start.cta + 6, src: "pop.wav", vol: 0.55 });
  cues.push({ at: start.cta + 36, src: "click.wav", vol: 0.6, rate: 0.9 });
  cues.push({
    at: start.cta + Math.min(90, Math.max(0, props.cta.durationInFrames - 30)),
    src: "chime.wav",
    vol: 0.45,
  });

  return cues;
};
