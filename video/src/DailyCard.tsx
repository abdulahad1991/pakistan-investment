import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { loadFont as loadMono } from "@remotion/google-fonts/IBMPlexMono";
import { type DailyProps } from "./dailySchema";
import { ColorProvider, useColors } from "./schema";
import { PaperBg } from "./components/PaperBg";
import { Counter, reveal } from "./components/Ledger";
import { AreaChart } from "./components/Charts";

// Single dense "everything at a glance" frame — the daily LinkedIn/image card.
// Packs the macro board, the PSX trend graph, gold + dollar, an allocation donut
// and top movers into one square. Reveals finish by ~frame 45, so render the
// still at frame 60 (see package.json) for a fully settled image.

const { fontFamily: SANS } = loadInter("normal", {
  weights: ["600", "700", "800"],
  subsets: ["latin"],
});
const { fontFamily: MONO } = loadMono("normal", {
  weights: ["600"],
  subsets: ["latin"],
});
const GOLD_DARK = "#B7791F";

const Pill: React.FC<{
  label: string;
  value: React.ReactNode;
  u: number;
  start: number;
  accent?: boolean;
  vSize?: number;
}> = ({ label, value, u, start, accent, vSize = 42 }) => {
  const frame = useCurrentFrame();
  const C = useColors();
  return (
    <div
      style={{
        flex: 1,
        minWidth: 0, // let the flex item shrink instead of overflowing the card
        background: C.paper,
        border: `2px solid ${C.border}`,
        borderRadius: 16 * u,
        padding: `${16 * u}px ${20 * u}px`,
        ...reveal(frame, start, 12),
      }}
    >
      <div
        style={{
          fontFamily: MONO,
          fontSize: 20 * u,
          letterSpacing: 1,
          textTransform: "uppercase",
          color: C.muted,
          whiteSpace: "nowrap",
          overflow: "hidden",
          textOverflow: "ellipsis",
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontFamily: MONO,
          fontWeight: 600,
          fontSize: vSize * u,
          color: accent ? C.green : C.ink,
          marginTop: 6 * u,
          whiteSpace: "nowrap",
        }}
      >
        {value}
      </div>
    </div>
  );
};

const Card: React.FC<{ data: DailyProps }> = ({ data }) => {
  const frame = useCurrentFrame();
  const C = useColors();
  const { width, height } = useVideoConfig();
  const u = Math.min(width, height) / 1080;
  const pad = 56 * u;
  const innerW = width - pad * 2;

  return (
    <AbsoluteFill style={{ padding: pad, justifyContent: "space-between" }}>
      {/* header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", ...reveal(frame, 0, 12) }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 * u }}>
          <span style={{ width: 40 * u, height: 4, background: C.gold, display: "inline-block" }} />
          <span style={{ fontFamily: SANS, fontWeight: 800, fontSize: 50 * u, color: C.ink, letterSpacing: -1 }}>
            Pakistan Market Brief
          </span>
        </div>
        <span style={{ fontFamily: MONO, fontSize: 30 * u, color: C.muted }}>{data.date}</span>
      </div>

      {/* macro pills */}
      <div style={{ display: "flex", gap: 16 * u }}>
        <Pill label="KSE-100" u={u} start={4} value={<Counter to={data.macro.kse100} decimals={0} start={4} dur={26} />} />
        <Pill label="₨ / US$" u={u} start={7} value={<Counter to={data.macro.pkrUsd} decimals={2} prefix="₨" start={7} dur={26} />} />
        <Pill label="SBP rate" u={u} start={10} value={<Counter to={data.macro.sbpRate} decimals={2} suffix="%" start={10} dur={26} />} />
        <Pill label="Inflation" u={u} start={13} value={<Counter to={data.macro.inflation} decimals={1} suffix="%" start={13} dur={26} />} />
      </div>

      {/* PSX trend graph */}
      <div style={{ background: C.paper, border: `2px solid ${C.border}`, borderRadius: 20 * u, padding: 24 * u, ...reveal(frame, 16, 12) }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <span style={{ fontFamily: SANS, fontWeight: 700, fontSize: 34 * u, color: C.ink }}>PSX · KSE-100 trend</span>
          <span style={{ fontFamily: MONO, fontSize: 26 * u, color: C.muted }}>
            {data.kseSeries.firstLabel} → {data.kseSeries.lastLabel}
          </span>
        </div>
        <div style={{ height: 12 * u }} />
        <AreaChart values={data.kseSeries.values} width={innerW - 48 * u} height={150 * u} color={C.green} fill={C.greenLight} start={18} dur={30} strokeWidth={6 * u} />
      </div>

      {/* gold — full width */}
      <div style={{ background: C.greenLight, borderRadius: 20 * u, padding: 30 * u, ...reveal(frame, 20, 12) }}>
        <div style={{ fontFamily: MONO, fontSize: 24 * u, letterSpacing: 1, textTransform: "uppercase", color: GOLD_DARK }}>
          Gold · 24k / tola
        </div>
        <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginTop: 8 * u }}>
          <span style={{ fontFamily: MONO, fontWeight: 600, fontSize: 84 * u, color: C.ink }}>
            <Counter to={data.gold.tola} decimals={0} prefix="₨" locale="en-IN" start={20} dur={28} />
          </span>
          <span style={{ fontFamily: MONO, fontSize: 34 * u, color: data.gold.change1y >= 0 ? C.green : C.red }}>
            {data.gold.change1y >= 0 ? "▲" : "▼"} {data.gold.change1y.toFixed(1)}% · 1 year
          </span>
        </div>
      </div>

      {/* footer */}
      <div style={{ display: "flex", justifyContent: "space-between", fontFamily: MONO, fontSize: 26 * u, color: C.muted, ...reveal(frame, 28, 12) }}>
        <span>{data.footer}</span>
        <span style={{ color: C.green, fontWeight: 600 }}>pakinvestlysis.com</span>
      </div>
    </AbsoluteFill>
  );
};

export const DailyCard: React.FC<DailyProps> = (props) => (
  <ColorProvider value={props.colors}>
    <AbsoluteFill style={{ backgroundColor: props.colors.paper }}>
      <PaperBg />
      <Card data={props} />
    </AbsoluteFill>
  </ColorProvider>
);
