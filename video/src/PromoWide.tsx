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

// 16:9 landscape promo for the website home page (1920×1080). Same five-scene
// narrative + brand system as the vertical Promo, re-laid-out for a wide frame:
// the bars/checklist run horizontally and the heavier scenes use a left/right
// split so the screen never feels empty. All timing constants are frame-based
// and shared, so the SFX cues (buildCues) stay perfectly in sync.

const { fontFamily: SANS } = loadInter("normal", {
  weights: ["600", "700", "800"],
  subsets: ["latin"],
});
const { fontFamily: MONO } = loadMono("normal", {
  weights: ["600"],
  subsets: ["latin"],
});
const easeOut = Easing.bezier(0.16, 1, 0.3, 1);

const PAD = 120;

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
        fontSize: 28,
        letterSpacing: 5,
        textTransform: "uppercase",
        color: C.green,
        display: "flex",
        alignItems: "center",
        gap: 18,
        ...style,
      }}
    >
      <span style={{ width: 44, height: 4, background: C.gold, display: "inline-block" }} />
      {children}
    </div>
  );
};

// =========================================================================
// Scene 1 — Hook (centered)
// =========================================================================
const Hook: React.FC<{ data: PromoProps["hook"] }> = ({ data }) => {
  const frame = useCurrentFrame();
  const C = useColors();
  const op = fadeInOut(frame, data.durationInFrames);
  return (
    <AbsoluteFill
      style={{ opacity: op, padding: PAD, justifyContent: "center", alignItems: "center" }}
    >
      <Kicker style={{ ...reveal(frame, 2) }}>{data.kicker}</Kicker>
      <div style={{ height: 44 }} />
      <div style={{ textAlign: "center" }}>
        {data.lines.map((l, i) => {
          const r = reveal(frame, 12 + i * 9);
          const gold = i === data.goldLineIndex;
          return (
            <div
              key={i}
              style={{
                fontFamily: SANS,
                fontWeight: 800,
                fontSize: 138,
                lineHeight: 1.04,
                color: C.ink,
                letterSpacing: -3,
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
                      bottom: 8,
                      height: 22,
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
      </div>
    </AbsoluteFill>
  );
};

// =========================================================================
// Scene 2 — Market snapshot (count-up ledger rows, full width)
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
        padding: "30px 0",
        borderBottom: `2px solid ${C.border}`,
        ...r,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 26 }}>
        <span
          style={{
            width: 16,
            height: 16,
            borderRadius: 4,
            background: up ? C.green : C.muted,
          }}
        />
        <span style={{ fontFamily: SANS, fontSize: 50, color: C.ink, fontWeight: 600 }}>
          {label}
        </span>
      </div>
      <span
        style={{ fontFamily: MONO, fontSize: 68, color: up ? C.green : C.ink, fontWeight: 600 }}
      >
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
      <div style={{ maxWidth: 1440, width: "100%", margin: "0 auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
          <div
            style={{
              fontFamily: SANS,
              fontWeight: 800,
              fontSize: 88,
              color: C.ink,
              letterSpacing: -2,
              ...reveal(frame, 0),
            }}
          >
            {data.heading}
          </div>
          <div
            style={{
              fontFamily: MONO,
              fontSize: 28,
              color: C.muted,
              paddingBottom: 12,
              ...reveal(frame, 4),
            }}
          >
            as of {data.asOf}
          </div>
        </div>
        <div style={{ height: 36 }} />
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
      </div>
    </AbsoluteFill>
  );
};

// =========================================================================
// Scene 3 — Compare 1-year returns (headline left, growing bars right)
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
  const fullH = 470;
  const h = fullH * (value / max) * grow;
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", width: 230 }}>
      <div
        style={{
          fontFamily: MONO,
          fontSize: 56,
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
      <div style={{ width: 196, height: 3, background: C.ink, opacity: 0.25 }} />
      <div
        style={{
          fontFamily: SANS,
          fontSize: 34,
          fontWeight: 700,
          color: C.ink,
          marginTop: 18,
          textAlign: "center",
          opacity: grow,
        }}
      >
        {label}
      </div>
      <div style={{ fontFamily: SANS, fontSize: 26, color: C.muted, marginTop: 4, opacity: grow }}>
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
      <div style={{ display: "flex", alignItems: "center", gap: 80 }}>
        {/* left — headline */}
        <div style={{ flex: "0 0 620px" }}>
          <Kicker style={{ ...reveal(frame, 0) }}>{data.kicker}</Kicker>
          <div style={{ height: 28 }} />
          <div
            style={{
              fontFamily: SANS,
              fontWeight: 800,
              fontSize: 92,
              color: C.ink,
              letterSpacing: -2,
              lineHeight: 1.04,
              ...reveal(frame, 6),
            }}
          >
            {data.headlineLine1}
            <br />
            {data.headlineLine2}
          </div>
          <div
            style={{
              fontFamily: MONO,
              fontSize: 26,
              color: C.muted,
              marginTop: 40,
              ...reveal(frame, 70),
            }}
          >
            {data.footnote}
          </div>
        </div>
        {/* right — bars */}
        <div
          style={{
            flex: 1,
            display: "flex",
            justifyContent: "space-around",
            alignItems: "flex-end",
          }}
        >
          {data.bars.map((b, i) => (
            <Bar key={i} {...b} max={max} index={i} />
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// =========================================================================
// Scene 4 — Value prop (headline top, checklist as a row of cards)
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
          fontSize: 96,
          color: C.ink,
          letterSpacing: -2,
          lineHeight: 1.0,
          ...reveal(frame, 0),
        }}
      >
        {data.headlineTop} <span style={{ color: C.green }}>{data.headlineBottom}</span>
      </div>
      <div style={{ height: 72 }} />
      <div style={{ display: "flex", gap: 32 }}>
        {data.items.map((t, i) => {
          const r = reveal(frame, 18 + i * 10);
          return (
            <div
              key={i}
              style={{
                flex: 1,
                background: C.paper,
                border: `2px solid ${C.border}`,
                borderRadius: 20,
                padding: "40px 36px",
                boxShadow: "0 18px 40px -28px rgba(16,24,40,0.45)",
                ...r,
              }}
            >
              <div
                style={{
                  width: 64,
                  height: 64,
                  borderRadius: 14,
                  background: C.greenLight,
                  color: C.green,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 42,
                  fontWeight: 800,
                  marginBottom: 26,
                }}
              >
                ✓
              </div>
              <div
                style={{ fontFamily: SANS, fontSize: 40, color: C.ink, fontWeight: 700, lineHeight: 1.2 }}
              >
                {t}
              </div>
            </div>
          );
        })}
      </div>
      <div
        style={{
          fontFamily: MONO,
          fontSize: 32,
          color: C.green,
          letterSpacing: 3,
          marginTop: 56,
          ...reveal(frame, 56),
        }}
      >
        {data.badge}
      </div>
    </AbsoluteFill>
  );
};

// =========================================================================
// Scene 5 — CTA (centered)
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
    <AbsoluteFill
      style={{ opacity: op, padding: PAD, justifyContent: "center", alignItems: "center" }}
    >
      <div style={{ transform: `scale(${0.9 + pop * 0.1})`, textAlign: "center" }}>
        <div style={{ position: "relative", display: "inline-block" }}>
          <span
            style={{
              fontFamily: SANS,
              fontWeight: 800,
              fontSize: 124,
              color: C.green,
              letterSpacing: -3,
            }}
          >
            {data.brand}
          </span>
          <div
            style={{
              position: "absolute",
              left: 0,
              bottom: -8,
              height: 12,
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
          fontSize: 46,
          color: C.ink,
          fontWeight: 600,
          ...reveal(frame, 26),
        }}
      >
        {data.subtitle}
      </div>
      <div style={{ height: 44 }} />
      <div
        style={{
          fontFamily: MONO,
          fontSize: 50,
          color: C.paper,
          background: C.green,
          padding: "28px 64px",
          borderRadius: 18,
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
// Audio — same frame-synced SFX kit + cue builder as the vertical Promo.
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
export const PromoWide: React.FC<PromoProps> = (props) => {
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
