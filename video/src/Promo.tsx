import React from "react";
import {
  AbsoluteFill,
  Audio,
  Sequence,
  staticFile,
  useCurrentFrame,
  interpolate,
  spring,
  useVideoConfig,
  Easing,
} from "remotion";
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { loadFont as loadMono } from "@remotion/google-fonts/IBMPlexMono";
import {
  type PromoProps,
  type Cue,
  ColorProvider,
  useColors,
  buildCues,
  sceneStarts,
} from "./schema";
import { PaperBg } from "./components/PaperBg";
import { Counter, reveal, fadeInOut } from "./components/Ledger";

// Load only the weights/subsets the promo actually uses — avoids fetching
// every Inter/Mono weight at render time (was ~120 requests per font).
const { fontFamily: SANS } = loadInter("normal", {
  weights: ["600", "700", "800"],
  subsets: ["latin"],
});
const { fontFamily: MONO } = loadMono("normal", {
  weights: ["600"],
  subsets: ["latin"],
});
const easeOut = Easing.bezier(0.16, 1, 0.3, 1);

const PAD = 96;

// ---- shared bits ----------------------------------------------------------

const Kicker: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({
  children,
  style,
}) => {
  const C = useColors();
  return (
    <div
      style={{
        fontFamily: MONO,
        fontSize: 26,
        letterSpacing: 4,
        textTransform: "uppercase",
        color: C.green,
        display: "flex",
        alignItems: "center",
        gap: 16,
        ...style,
      }}
    >
      <span style={{ width: 40, height: 4, background: C.gold, display: "inline-block" }} />
      {children}
    </div>
  );
};

// =========================================================================
// Scene 1 — Hook
// =========================================================================
const Hook: React.FC<{ data: PromoProps["hook"] }> = ({ data }) => {
  const frame = useCurrentFrame();
  const C = useColors();
  const op = fadeInOut(frame, data.durationInFrames);
  return (
    <AbsoluteFill style={{ opacity: op, padding: PAD, justifyContent: "center" }}>
      <Kicker style={{ ...reveal(frame, 2) }}>{data.kicker}</Kicker>
      <div style={{ height: 48 }} />
      {data.lines.map((l, i) => {
        const r = reveal(frame, 12 + i * 9);
        const gold = i === data.goldLineIndex;
        return (
          <div
            key={i}
            style={{
              fontFamily: SANS,
              fontWeight: 800,
              fontSize: 104,
              lineHeight: 1.04,
              color: C.ink,
              letterSpacing: -2,
              ...r,
            }}
          >
            {gold ? (
              <span style={{ position: "relative" }}>
                {l}
                <span
                  style={{
                    position: "absolute",
                    left: 0,
                    bottom: 6,
                    height: 18,
                    width: `${interpolate(frame, [30, 52], [0, 100], {
                      extrapolateLeft: "clamp",
                      extrapolateRight: "clamp",
                      easing: easeOut,
                    })}%`,
                    background: C.goldPale,
                    opacity: 0.85,
                    zIndex: -1,
                  }}
                />
              </span>
            ) : (
              l
            )}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

// =========================================================================
// Scene 2 — Market snapshot (count-up ledger rows)
// =========================================================================
const Row: React.FC<{
  label: string;
  start: number;
  value: React.ReactNode;
  up?: boolean;
}> = ({ label, start, value, up }) => {
  const frame = useCurrentFrame();
  const C = useColors();
  const r = reveal(frame, start);
  return (
    <div
      style={{
        display: "flex",
        alignItems: "baseline",
        justifyContent: "space-between",
        padding: "26px 0",
        borderBottom: `2px solid ${C.border}`,
        ...r,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 22 }}>
        <span
          style={{
            width: 14,
            height: 14,
            borderRadius: 4,
            background: up ? C.green : C.muted,
          }}
        />
        <span style={{ fontFamily: SANS, fontSize: 40, color: C.ink, fontWeight: 600 }}>
          {label}
        </span>
      </div>
      <span style={{ fontFamily: MONO, fontSize: 56, color: up ? C.green : C.ink, fontWeight: 600 }}>
        {value}
      </span>
    </div>
  );
};

const Market: React.FC<{ data: PromoProps["market"] }> = ({ data }) => {
  const frame = useCurrentFrame();
  const C = useColors();
  const op = fadeInOut(frame, data.durationInFrames);
  return (
    <AbsoluteFill style={{ opacity: op, padding: PAD, justifyContent: "center" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", ...reveal(frame, 0) }}>
        <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 76, color: C.ink, letterSpacing: -1.5 }}>
          {data.heading}
        </div>
      </div>
      <div style={{ fontFamily: MONO, fontSize: 26, color: C.muted, marginTop: 8, ...reveal(frame, 4) }}>
        as of {data.asOf}
      </div>
      <div style={{ height: 40 }} />
      {data.rows.map((row, i) => {
        const start = 14 + i * 12;
        return (
          <Row
            key={i}
            label={row.label}
            start={start}
            up={row.up}
            value={
              <Counter
                to={row.value}
                decimals={row.decimals}
                prefix={row.prefix}
                suffix={row.suffix}
                start={start}
                dur={26}
              />
            }
          />
        );
      })}
    </AbsoluteFill>
  );
};

// =========================================================================
// Scene 3 — Compare 1-year returns (growing bars)
// =========================================================================
const Bar: React.FC<{
  label: string;
  sub: string;
  value: number;
  max: number;
  color: string;
  index: number;
}> = ({ label, sub, value, max, color, index }) => {
  const frame = useCurrentFrame();
  const C = useColors();
  const { fps } = useVideoConfig();
  const start = 22 + index * 8;
  const grow = spring({ frame: frame - start, fps, config: { damping: 200 }, durationInFrames: 34 });
  const fullH = 560;
  const h = fullH * (value / max) * grow;
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", width: 240 }}>
      <div
        style={{
          fontFamily: MONO,
          fontSize: 52,
          fontWeight: 600,
          color,
          opacity: grow,
          marginBottom: 14,
        }}
      >
        <Counter to={value} from={0} decimals={1} suffix="%" prefix="+" start={start} dur={34} />
      </div>
      <div
        style={{
          width: 150,
          height: h,
          background: color,
          borderRadius: "10px 10px 0 0",
          boxShadow: "inset 0 -10px 0 rgba(0,0,0,0.10)",
        }}
      />
      <div style={{ width: 200, height: 3, background: C.ink, opacity: 0.25 }} />
      <div
        style={{
          fontFamily: SANS,
          fontSize: 32,
          fontWeight: 700,
          color: C.ink,
          marginTop: 18,
          textAlign: "center",
          opacity: grow,
        }}
      >
        {label}
      </div>
      <div style={{ fontFamily: SANS, fontSize: 24, color: C.muted, marginTop: 4, opacity: grow }}>
        {sub}
      </div>
    </div>
  );
};

const Compare: React.FC<{ data: PromoProps["compare"] }> = ({ data }) => {
  const frame = useCurrentFrame();
  const C = useColors();
  const op = fadeInOut(frame, data.durationInFrames);
  const max = Math.max(...data.bars.map((b) => b.value), 1);
  return (
    <AbsoluteFill style={{ opacity: op, padding: PAD, justifyContent: "center" }}>
      <Kicker style={{ ...reveal(frame, 0) }}>{data.kicker}</Kicker>
      <div style={{ height: 24 }} />
      <div
        style={{
          fontFamily: SANS,
          fontWeight: 800,
          fontSize: 72,
          color: C.ink,
          letterSpacing: -1.5,
          lineHeight: 1.05,
          ...reveal(frame, 6),
        }}
      >
        {data.headlineLine1}
        <br />
        {data.headlineLine2}
      </div>
      <div style={{ height: 64 }} />
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
        {data.bars.map((b, i) => (
          <Bar key={i} {...b} max={max} index={i} />
        ))}
      </div>
      <div
        style={{
          fontFamily: MONO,
          fontSize: 24,
          color: C.muted,
          marginTop: 36,
          textAlign: "center",
          ...reveal(frame, 70),
        }}
      >
        {data.footnote}
      </div>
    </AbsoluteFill>
  );
};

// =========================================================================
// Scene 4 — Value prop
// =========================================================================
const Value: React.FC<{ data: PromoProps["value"] }> = ({ data }) => {
  const frame = useCurrentFrame();
  const C = useColors();
  const op = fadeInOut(frame, data.durationInFrames);
  return (
    <AbsoluteFill style={{ opacity: op, padding: PAD, justifyContent: "center" }}>
      <div
        style={{
          fontFamily: SANS,
          fontWeight: 800,
          fontSize: 88,
          color: C.ink,
          letterSpacing: -2,
          lineHeight: 1.02,
          ...reveal(frame, 0),
        }}
      >
        {data.headlineTop}
        <br />
        <span style={{ color: C.green }}>{data.headlineBottom}</span>
      </div>
      <div style={{ height: 64 }} />
      {data.items.map((t, i) => {
        const r = reveal(frame, 18 + i * 10);
        return (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 26, marginBottom: 34, ...r }}>
            <div
              style={{
                width: 56,
                height: 56,
                borderRadius: 12,
                background: C.greenLight,
                color: C.green,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 38,
                fontWeight: 800,
                flexShrink: 0,
              }}
            >
              ✓
            </div>
            <div style={{ fontFamily: SANS, fontSize: 44, color: C.ink, fontWeight: 600 }}>{t}</div>
          </div>
        );
      })}
      <div
        style={{
          fontFamily: MONO,
          fontSize: 30,
          color: C.green,
          letterSpacing: 3,
          marginTop: 24,
          ...reveal(frame, 56),
        }}
      >
        {data.badge}
      </div>
    </AbsoluteFill>
  );
};

// =========================================================================
// Scene 5 — CTA
// =========================================================================
const CTA: React.FC<{ data: PromoProps["cta"] }> = ({ data }) => {
  const frame = useCurrentFrame();
  const C = useColors();
  const { fps } = useVideoConfig();
  const op = fadeInOut(frame, data.durationInFrames);
  const pop = spring({ frame: frame - 6, fps, config: { damping: 14 }, durationInFrames: 30 });
  const underline = interpolate(frame, [16, 40], [0, 100], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: easeOut,
  });
  return (
    <AbsoluteFill style={{ opacity: op, padding: PAD, justifyContent: "center", alignItems: "center" }}>
      <div style={{ transform: `scale(${0.9 + pop * 0.1})`, textAlign: "center" }}>
        <div style={{ position: "relative", display: "inline-block" }}>
          <span
            style={{
              fontFamily: SANS,
              fontWeight: 800,
              fontSize: 92,
              color: C.green,
              letterSpacing: -2,
            }}
          >
            {data.brand}
          </span>
          <div
            style={{
              position: "absolute",
              left: 0,
              bottom: -6,
              height: 10,
              width: `${underline}%`,
              background: C.gold,
              borderRadius: 6,
            }}
          />
        </div>
      </div>
      <div style={{ height: 56 }} />
      <div
        style={{
          fontFamily: SANS,
          fontSize: 40,
          color: C.ink,
          fontWeight: 600,
          ...reveal(frame, 26),
        }}
      >
        {data.subtitle}
      </div>
      <div style={{ height: 40 }} />
      <div
        style={{
          fontFamily: MONO,
          fontSize: 46,
          color: C.paper,
          background: C.green,
          padding: "26px 56px",
          borderRadius: 16,
          letterSpacing: 1,
          boxShadow: "0 18px 40px -18px rgba(7,94,75,0.7)",
          ...reveal(frame, 36),
        }}
      >
        {data.button}
      </div>
    </AbsoluteFill>
  );
};

// =========================================================================
// Audio — frame-synced SFX only (built in scripts/gen_audio.py). No music bed.
// Cues are derived from the live scene layout + content (see buildCues), so
// they stay in sync when durations/rows/bars/items change in Studio.
// =========================================================================
const Soundscape: React.FC<{ cues: Cue[]; volume: number }> = ({ cues, volume }) => (
  <>
    {cues.map((c, i) => (
      <Sequence key={i} from={c.at} layout="none">
        <Audio src={staticFile(c.src)} volume={() => c.vol * volume} playbackRate={c.rate ?? 1} />
      </Sequence>
    ))}
  </>
);

// =========================================================================
// Master
// =========================================================================
export const Promo: React.FC<PromoProps> = (props) => {
  const start = sceneStarts(props);
  return (
    <ColorProvider value={props.colors}>
      <AbsoluteFill style={{ backgroundColor: props.colors.paper }}>
        <PaperBg />
        {props.audio.sfx ? <Soundscape cues={buildCues(props)} volume={props.audio.volume} /> : null}
        <Sequence from={start.hook} durationInFrames={props.hook.durationInFrames} layout="none">
          <Hook data={props.hook} />
        </Sequence>
        <Sequence from={start.market} durationInFrames={props.market.durationInFrames} layout="none">
          <Market data={props.market} />
        </Sequence>
        <Sequence from={start.compare} durationInFrames={props.compare.durationInFrames} layout="none">
          <Compare data={props.compare} />
        </Sequence>
        <Sequence from={start.value} durationInFrames={props.value.durationInFrames} layout="none">
          <Value data={props.value} />
        </Sequence>
        <Sequence from={start.cta} durationInFrames={props.cta.durationInFrames} layout="none">
          <CTA data={props.cta} />
        </Sequence>
      </AbsoluteFill>
    </ColorProvider>
  );
};
