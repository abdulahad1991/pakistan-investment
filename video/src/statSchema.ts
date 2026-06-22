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
