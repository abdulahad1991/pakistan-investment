// Schema for the long-form WeeklyBrief (16:9, ~160s) — "Pakistan Market —
// Week in Review". A weekly sibling of build_daily.py emits this shape once a
// week. colors/audio reuse the shared schemas (same contract as the daily
// brief). `series` are plain number arrays (5-6 daily points); if fewer than
// 2 points arrive the scenes fall back to a straight [open, close] line.
import { z } from "zod";
import { colorsSchema, audioSchema, defaultColors } from "./schema";

const weekSeries = z.object({
  open: z.number(),
  close: z.number(),
  chgPct: z.number(), // % change over the week
  series: z.array(z.number()).min(1),
});

const weeklyMover = z.object({
  sym: z.string(),
  name: z.string(),
  chgPct: z.number(), // weekly %, may be negative
});

export const weeklySchema = z.object({
  colors: colorsSchema.default(defaultColors),
  audio: audioSchema.default({ sfx: true, volume: 1 }),

  dateRange: z.string(), // "30 Jun – 4 Jul 2026" (en dash splits the labels)
  kse: weekSeries,
  gold: weekSeries, // 24k per tola, PKR
  movers: z.array(weeklyMover), // top-5 weekly PSX movers
  rates: z.object({
    policy: z.number(), // SBP policy rate %
    inflation: z.number(), // CPI YoY %
    usd: z.number(), // PKR per USD
  }),
});

export type WeeklyProps = z.infer<typeof weeklySchema>;

export const defaultWeeklyProps: WeeklyProps = {
  colors: defaultColors,
  audio: { sfx: true, volume: 1 },
  dateRange: "30 Jun – 4 Jul 2026",
  kse: {
    open: 180733,
    close: 184841,
    chgPct: 2.27,
    series: [180733, 181420, 182960, 182210, 183904, 184841],
  },
  gold: {
    open: 430000,
    close: 433300,
    chgPct: 0.77,
    series: [430000, 431200, 430600, 432400, 433000, 433300],
  },
  movers: [
    { sym: "TPLI", name: "TPL Insurance", chgPct: 12.4 },
    { sym: "BOP", name: "Bank of Punjab", chgPct: 9.8 },
    { sym: "FFC", name: "Fauji Fertilizer", chgPct: 7.5 },
    { sym: "HUBC", name: "Hub Power", chgPct: 6.1 },
    { sym: "OGDC", name: "Oil & Gas Dev", chgPct: -2.4 },
  ],
  rates: { policy: 11.5, inflation: 11.7, usd: 278.15 },
};
