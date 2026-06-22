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
      <Sequence layout="none">
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
          ...reveal(frame, 18),
          transform: `${reveal(frame, 18).transform} scale(${0.9 + pop * 0.1})`,
          transformOrigin: "left center",
          background: trendColor,
          color: C.paper,
          fontFamily: MONO,
          fontSize: 34 * u,
          fontWeight: 600,
          padding: `${14 * u}px ${28 * u}px`,
          borderRadius: 12,
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
