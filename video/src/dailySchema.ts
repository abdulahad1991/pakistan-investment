// Schema for the daily market brief — the multi-insight successor to the single
// StatCard. One props object carries the whole day's snapshot (macro board, PSX
// + gold trend series, top movers, a sample allocation) and drives three
// compositions: DailyBrief-9x16, DailyBrief-1x1 (videos) and DailyCard-1x1 (the
// still image). build_daily.py emits this shape from data.json.
import { z } from "zod";
import { colorsSchema, audioSchema, segmentedVoiceoverSchema, defaultColors } from "./schema";

const series = z.object({
  values: z.array(z.number()),
  firstLabel: z.string(),
  lastLabel: z.string(),
});

const mover = z.object({
  ticker: z.string(),
  name: z.string(),
  change1y: z.number(),
});

const slice = z.object({
  label: z.string(),
  pct: z.number(),
  color: z.string(),
});

export const dailySchema = z.object({
  colors: colorsSchema,
  audio: audioSchema,
  date: z.string(),
  session: z.string(), // "Market open" (morning run) or "Market close" (evening)
  footer: z.string(),

  macro: z.object({
    kse100: z.number(),
    pkrUsd: z.number(),
    sbpRate: z.number(),
    inflation: z.number(),
  }),

  gold: z.object({
    tola: z.number(), // 24k per tola, PKR
    change1y: z.number(), // %
  }),

  kseSeries: series,
  goldSeries: series,

  movers: z.array(mover), // top PSX 1-year movers
  allocation: z.array(slice), // illustrative balanced mix (not advice)

  // Optional (build_daily.py emits these since 2026-07; older props files
  // lack them and must render exactly as before — hence .optional()).
  // headline: turns scene 1 into a full-bleed hook (kicker chip + huge
  // count-up number + sub line). Absent -> classic title scene.
  headline: z
    .object({
      text: z.string(), // e.g. "GOLD ₨4,33,300" — numeric part counts up
      kicker: z.string(), // e.g. "+2.1% TODAY"
      sub: z.string(), // e.g. "2 Jul · Market close"
    })
    .optional(),
  // voiceover: per-scene narration segments (vo-<scene>.mp3, each cued to its
  // scene's first frame) or a legacy single `file` laid from frame 0; either
  // way the music bed ducks while narration is enabled.
  voiceover: segmentedVoiceoverSchema.optional(),
});

export type DailyProps = z.infer<typeof dailySchema>;

export const defaultDailyProps: DailyProps = {
  colors: defaultColors,
  audio: { sfx: true, volume: 1 },
  date: "22 Jun 2026",
  session: "Market open",
  footer: "Not financial advice · pakinvestlysis.com",
  macro: { kse100: 178471, pkrUsd: 277.9, sbpRate: 11.5, inflation: 7.0 },
  gold: { tola: 448000, change1y: 34.7 },
  kseSeries: {
    values: [115000, 170000, 167360, 162994, 173001, 178471],
    firstLabel: "Jan'25",
    lastLabel: "Jun'26",
  },
  goldSeries: {
    values: [332000, 348000, 360000, 372000, 410000, 432000, 448000],
    firstLabel: "Jul'25",
    lastLabel: "Jun'26",
  },
  movers: [
    { ticker: "FFC", name: "Fauji Fertilizer", change1y: 56.8 },
    { ticker: "MCB", name: "MCB Bank", change1y: 55.8 },
    { ticker: "HUBC", name: "Hub Power", change1y: 44.2 },
    { ticker: "OGDC", name: "Oil & Gas Dev", change1y: 38.1 },
  ],
  allocation: [
    { label: "National Savings", pct: 30, color: "#075E4B" },
    { label: "Income funds", pct: 20, color: "#2854C5" },
    { label: "Equity / stocks", pct: 30, color: "#F2B94B" },
    { label: "Gold", pct: 20, color: "#B7791F" },
  ],
};
