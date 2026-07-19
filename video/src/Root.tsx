import "./index.css";
import { Composition, type CalculateMetadataFunction } from "remotion";
import { Promo } from "./Promo";
import { PromoWide } from "./PromoWide";
import {
  FPS,
  promoSchema,
  defaultPromoProps,
  totalDuration,
  type PromoProps,
} from "./schema";
import { StatCard } from "./StatCard";
import { statCardSchema, defaultStatProps, type StatCardProps } from "./statSchema";
import { DailyBrief, dailyTotal } from "./DailyBrief";
import { DailyCard } from "./DailyCard";
import { PetrolCard } from "./PetrolCard";
import { dailySchema, defaultDailyProps } from "./dailySchema";
import { WeeklyBrief, weeklyTotal } from "./WeeklyBrief";
import { WeeklyCard } from "./WeeklyCard";
import { weeklySchema, defaultWeeklyProps } from "./weeklySchema";

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

      {/* Landscape 16:9 — embedded on the website home page. Same content/
          schema/audio as the vertical Promo, re-laid-out for a wide frame. */}
      <Composition
        id="PromoWide"
        component={PromoWide}
        fps={FPS}
        width={1920}
        height={1080}
        schema={promoSchema}
        defaultProps={defaultPromoProps}
        calculateMetadata={({ props }) => ({
          durationInFrames: totalDuration(props),
          fps: FPS,
          width: 1920,
          height: 1080,
        })}
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

      {/* Daily market brief — multi-insight successor to StatCard. One props
          object (built by scripts/build_daily.py) drives all three: the 9:16
          Short, the 1:1 LinkedIn video, and the 1:1 still image card. */}
      <Composition
        id="DailyBrief-9x16"
        component={DailyBrief}
        fps={FPS}
        width={1080}
        height={1920}
        durationInFrames={dailyTotal()}
        schema={dailySchema}
        defaultProps={defaultDailyProps}
      />
      <Composition
        id="DailyBrief-1x1"
        component={DailyBrief}
        fps={FPS}
        width={1080}
        height={1080}
        durationInFrames={dailyTotal()}
        schema={dailySchema}
        defaultProps={defaultDailyProps}
      />
      {/* 16:9 — embedded on the website home page. Doubles as the promo: it
          opens on the brand, walks every live rate, and closes on the CTA. */}
      <Composition
        id="DailyBrief-16x9"
        component={DailyBrief}
        fps={FPS}
        width={1920}
        height={1080}
        durationInFrames={dailyTotal()}
        schema={dailySchema}
        defaultProps={defaultDailyProps}
      />
      <Composition
        id="DailyCard-1x1"
        component={DailyCard}
        fps={FPS}
        width={1080}
        height={1080}
        durationInFrames={90}
        schema={dailySchema}
        defaultProps={defaultDailyProps}
      />
      {/* Dedicated Petrol Prices still — the FB "Petrol Prices" post image. */}
      <Composition
        id="PetrolCard-1x1"
        component={PetrolCard}
        fps={FPS}
        width={1080}
        height={1080}
        durationInFrames={90}
        schema={dailySchema}
        defaultProps={defaultDailyProps}
      />

      {/* Weekly market review — 16:9 (~45s) for YouTube proper.
          Reuses the DailyBrief building blocks at a slower pace; props come
          from the weekly props file (see weeklySchema.ts for the contract). */}
      <Composition
        id="WeeklyBrief-16x9"
        component={WeeklyBrief}
        fps={FPS}
        width={1920}
        height={1080}
        durationInFrames={weeklyTotal()}
        schema={weeklySchema}
        defaultProps={defaultWeeklyProps}
      />
      {/* Weekly digest still — the FB "Weekly Digest" image post. */}
      <Composition
        id="WeeklyCard-1x1"
        component={WeeklyCard}
        fps={FPS}
        width={1080}
        height={1080}
        durationInFrames={90}
        schema={weeklySchema}
        defaultProps={defaultWeeklyProps}
      />
    </>
  );
};
