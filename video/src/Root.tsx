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
