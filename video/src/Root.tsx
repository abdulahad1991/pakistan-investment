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

// Total duration is derived from the per-scene durations in the props, so
// editing any scene length in Studio reflows the timeline automatically.
const calculateMetadata: CalculateMetadataFunction<PromoProps> = ({ props }) => ({
  durationInFrames: totalDuration(props),
  fps: FPS,
  width: 1080,
  height: 1920,
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
        calculateMetadata={calculateMetadata}
      />
    </>
  );
};
