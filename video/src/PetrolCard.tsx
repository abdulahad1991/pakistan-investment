import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { loadFont as loadMono } from "@remotion/google-fonts/IBMPlexMono";
import { type DailyProps } from "./dailySchema";
import { ColorProvider, useColors } from "./schema";
import { PaperBg } from "./components/PaperBg";
import { Counter, reveal } from "./components/Ledger";

// Dedicated PETROL PRICES still — the FB "Petrol Prices" post image. Petrol is
// the hero (fuel-price search intent); HSD / Kerosene / LDO sit below it.

const { fontFamily: SANS } = loadInter("normal", {
  weights: ["600", "700", "800"],
  subsets: ["latin"],
});
const { fontFamily: MONO } = loadMono("normal", {
  weights: ["600"],
  subsets: ["latin"],
});
const GOLD_DARK = "#B7791F";

const Card: React.FC<{ data: DailyProps }> = ({ data }) => {
  const frame = useCurrentFrame();
  const C = useColors();
  const { width, height } = useVideoConfig();
  const u = Math.min(width, height) / 1080;
  const pad = 64 * u;
  const f = data.fuel || {};
  const secondary = (
    [
      ["Diesel · HSD", f.hsd],
      ["Kerosene", f.kerosene],
      ["LDO", f.ldo],
    ] as [string, number | null | undefined][]
  ).filter(([, v]) => v != null) as [string, number][];

  return (
    <AbsoluteFill style={{ padding: pad, justifyContent: "space-between" }}>
      {/* header */}
      <div style={{ ...reveal(frame, 0, 12) }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 16 * u }}>
            <span style={{ width: 40 * u, height: 4, background: C.gold, display: "inline-block" }} />
            <span style={{ fontFamily: SANS, fontWeight: 800, fontSize: 56 * u, color: C.ink, letterSpacing: -1 }}>
              Petrol Price · Pakistan
            </span>
          </div>
          <span style={{ fontFamily: MONO, fontSize: 30 * u, color: C.muted }}>{data.date}</span>
        </div>
        <div style={{ fontFamily: MONO, fontSize: 26 * u, color: C.muted, marginTop: 12 * u }}>
          OGRA-notified retail rates · per litre{f.asof ? ` · effective ${f.asof}` : ""}
        </div>
      </div>

      {/* petrol hero */}
      {f.petrol != null && (
        <div style={{ background: C.greenLight, borderRadius: 28 * u, padding: `${40 * u}px ${44 * u}px`, ...reveal(frame, 6, 14) }}>
          <div style={{ fontFamily: MONO, fontSize: 30 * u, letterSpacing: 2, textTransform: "uppercase", color: GOLD_DARK }}>
            ⛽ Petrol (MS)
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 18 * u, marginTop: 8 * u }}>
            <span style={{ fontFamily: MONO, fontWeight: 600, fontSize: 140 * u, color: C.green, lineHeight: 1 }}>
              <Counter to={f.petrol} decimals={2} prefix="₨" start={6} dur={28} />
            </span>
            <span style={{ fontFamily: SANS, fontWeight: 700, fontSize: 40 * u, color: C.muted }}>/ litre</span>
          </div>
        </div>
      )}

      {/* secondary fuels */}
      {secondary.length > 0 && (
        <div style={{ display: "flex", gap: 20 * u }}>
          {secondary.map(([label, v], i) => (
            <div
              key={label}
              style={{
                flex: 1,
                minWidth: 0,
                background: C.paper,
                border: `2px solid ${C.border}`,
                borderRadius: 22 * u,
                padding: `${26 * u}px ${24 * u}px`,
                ...reveal(frame, 12 + i * 3, 12),
              }}
            >
              <div style={{ fontFamily: MONO, fontSize: 24 * u, letterSpacing: 1, textTransform: "uppercase", color: C.muted, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                {label}
              </div>
              <div style={{ fontFamily: MONO, fontWeight: 600, fontSize: 52 * u, color: C.ink, marginTop: 8 * u, whiteSpace: "nowrap" }}>
                <Counter to={v} decimals={2} prefix="₨" start={12 + i * 3} dur={24} />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* footer */}
      <div style={{ display: "flex", justifyContent: "space-between", fontFamily: MONO, fontSize: 26 * u, color: C.muted, ...reveal(frame, 20, 12) }}>
        <span>{data.footer}</span>
        <span style={{ color: C.green, fontWeight: 600 }}>pakinvestlysis.com</span>
      </div>
    </AbsoluteFill>
  );
};

export const PetrolCard: React.FC<DailyProps> = (props) => (
  <ColorProvider value={props.colors}>
    <AbsoluteFill style={{ backgroundColor: props.colors.paper }}>
      <PaperBg />
      <Card data={props} />
    </AbsoluteFill>
  </ColorProvider>
);
