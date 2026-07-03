import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  Sequence,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Easing,
} from "remotion";
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { loadFont as loadMono } from "@remotion/google-fonts/IBMPlexMono";
import { type DailyProps } from "./dailySchema";
import { ColorProvider, useColors } from "./schema";
import { PaperBg } from "./components/PaperBg";
import { Counter, reveal, fadeInOut } from "./components/Ledger";
import { AreaChart } from "./components/Charts";

// Daily market brief — one short walks through the whole day's snapshot:
// macro board → PSX trend → gold trend → top movers → spotlight → CTA → outro.
// Music/SFX only — no narration (the TTS voiceover was removed 2026-07-03).
// The spotlight is a rotating bonus scene (tool promo / rate check / comment
// question) that replaced the "sample mix" allocation donut, which now lives
// only on the DailyCard still.
// Responsive: the same component renders 9:16 (Shorts) and 1:1 (LinkedIn); all
// sizes scale off u = min(w,h)/1080, and every scene is laid out to fit the
// tighter square frame, then centered (so it just breathes more when vertical).

const { fontFamily: SANS } = loadInter("normal", {
  weights: ["600", "700", "800"],
  subsets: ["latin"],
});
const { fontFamily: MONO } = loadMono("normal", {
  weights: ["600"],
  subsets: ["latin"],
});
export { SANS, MONO };
const easeOut = Easing.bezier(0.16, 1, 0.3, 1);
export const GOLD_DARK = "#B7791F"; // matches site --gold2 (not in the shared palette)

// Fixed scene lengths (frames @30fps). Total drives calculateMetadata.
export const SCENES = {
  title: 66,
  board: 126,
  psx: 102,
  gold: 102,
  movers: 108,
  spot: 114,
  cta: 72,
  outro: 84,
} as const;
type SceneKey = keyof typeof SCENES;
const ORDER: SceneKey[] = ["title", "board", "psx", "gold", "movers", "spot", "cta", "outro"];

export const dailyTotal = () => ORDER.reduce((s, k) => s + SCENES[k], 0);
const starts = (): Record<SceneKey, number> => {
  let acc = 0;
  const o = {} as Record<SceneKey, number>;
  for (const k of ORDER) {
    o[k] = acc;
    acc += SCENES[k];
  }
  return o;
};

// --------------------------------------------------------------------------
// scaling + shared bits
// --------------------------------------------------------------------------
export const useU = () => {
  const { width, height } = useVideoConfig();
  return { u: Math.min(width, height) / 1080, width, height };
};

export const Kicker: React.FC<{ children: React.ReactNode; u: number; style?: React.CSSProperties }> = ({
  children,
  u,
  style,
}) => {
  const C = useColors();
  return (
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
        ...style,
      }}
    >
      <span style={{ width: 40 * u, height: 4, background: C.gold, display: "inline-block" }} />
      {children}
    </div>
  );
};

export const Scene: React.FC<{ dur: number; u: number; children: React.ReactNode }> = ({
  dur,
  u,
  children,
}) => {
  const frame = useCurrentFrame();
  const op = fadeInOut(frame, dur);
  return (
    <AbsoluteFill
      style={{ opacity: op, padding: 84 * u, justifyContent: "center", alignItems: "stretch" }}
    >
      {children}
    </AbsoluteFill>
  );
};

// =========================================================================
// 1 — Title. Two modes, same slot + duration (CI guards the total):
//  - headline present (new optional prop) -> full-bleed hook: loud kicker
//    chip, huge count-up headline with a spring punch-in, sub line beneath.
//  - headline absent (all pre-existing props files) -> the classic title,
//    byte-for-byte the old markup.
// =========================================================================

// Find the first number in the headline text so the hook can count it up.
// The locale is re-derived from the digit grouping of the source string
// (en-IN => "4,33,300") so the Counter lands on exactly the emitted text;
// if neither locale reproduces it, fall back to static text (no counter).
const splitHeadline = (text: string) => {
  const m = /\d[\d,]*(?:\.\d+)?/.exec(text);
  if (!m) return null;
  const raw = m[0];
  const value = Number(raw.replace(/,/g, ""));
  if (!Number.isFinite(value)) return null;
  const decimals = raw.includes(".") ? raw.length - raw.indexOf(".") - 1 : 0;
  const fmt = { minimumFractionDigits: decimals, maximumFractionDigits: decimals };
  const locale = ["en-IN", "en-US"].find((l) => value.toLocaleString(l, fmt) === raw);
  if (!locale) return null;
  return {
    prefix: text.slice(0, m.index),
    value,
    decimals,
    locale,
    suffix: text.slice(m.index + raw.length),
  };
};

type Headline = NonNullable<DailyProps["headline"]>;

const HookTitle: React.FC<{ headline: Headline }> = ({ headline }) => {
  const frame = useCurrentFrame();
  const C = useColors();
  const { u, width } = useU();
  const { fps } = useVideoConfig();
  const down = /[-−▼]/.test(headline.kicker);
  const accent = down ? C.red : C.green;
  const pop = spring({ frame: frame - 8, fps, config: { damping: 14 }, durationInFrames: 30 });
  const num = splitHeadline(headline.text);
  // Size off the longest word so the lockup wraps at spaces, never clips.
  const usable = width - 168 * u; // Scene padding
  const maxWord = Math.max(...headline.text.split(/\s+/).map((w) => w.length), 1);
  const fs = Math.min(168 * u, usable / (0.62 * maxWord));
  return (
    <Scene dur={SCENES.title} u={u}>
      <div style={{ display: "flex", justifyContent: "center", ...reveal(frame, 2) }}>
        <div
          style={{
            fontFamily: MONO,
            fontWeight: 600,
            fontSize: 40 * u,
            letterSpacing: 3,
            textTransform: "uppercase",
            color: C.paper,
            background: accent,
            padding: `${12 * u}px ${28 * u}px`,
            borderRadius: 12,
            boxShadow: `0 14px 32px -16px ${accent}B0`,
          }}
        >
          {headline.kicker}
        </div>
      </div>
      <div style={{ height: 44 * u }} />
      <div
        style={{
          fontFamily: SANS,
          fontWeight: 800,
          fontSize: fs,
          lineHeight: 1.04,
          letterSpacing: -2,
          color: C.ink,
          textAlign: "center",
          opacity: Math.min(1, pop * 1.6),
          transform: `scale(${0.82 + pop * 0.18})`,
        }}
      >
        {num ? (
          <>
            {num.prefix}
            <span style={{ color: accent }}>
              <Counter to={num.value} decimals={num.decimals} locale={num.locale} start={12} dur={30} />
            </span>
            {num.suffix}
          </>
        ) : (
          headline.text
        )}
      </div>
      <div
        style={{
          fontFamily: MONO,
          fontSize: 36 * u,
          color: C.muted,
          textAlign: "center",
          marginTop: 30 * u,
          ...reveal(frame, 26),
        }}
      >
        {headline.sub}
      </div>
    </Scene>
  );
};

const ClassicTitle: React.FC<{ data: DailyProps }> = ({ data }) => {
  const frame = useCurrentFrame();
  const C = useColors();
  const { u } = useU();
  return (
    <Scene dur={SCENES.title} u={u}>
      <div style={{ ...reveal(frame, 2), display: "flex", justifyContent: "center" }}>
        <Kicker u={u}>Pakistan · {data.session}</Kicker>
      </div>
      <div style={{ height: 36 * u }} />
      <div
        style={{
          fontFamily: SANS,
          fontWeight: 800,
          fontSize: 116 * u,
          lineHeight: 1.02,
          letterSpacing: -2,
          color: C.ink,
          textAlign: "center",
          ...reveal(frame, 10),
        }}
      >
        Market <span style={{ color: C.green }}>brief</span>
      </div>
      <div
        style={{
          fontFamily: MONO,
          fontSize: 40 * u,
          color: C.muted,
          textAlign: "center",
          marginTop: 18 * u,
          ...reveal(frame, 18),
        }}
      >
        {data.date}
      </div>
    </Scene>
  );
};

const Title: React.FC<{ data: DailyProps }> = ({ data }) =>
  data.headline ? <HookTitle headline={data.headline} /> : <ClassicTitle data={data} />;

// =========================================================================
// 2 — Macro board (PSX, dollar, gold, policy rate)
// =========================================================================
export const BoardRow: React.FC<{
  label: string;
  start: number;
  u: number;
  value: React.ReactNode;
  up?: boolean;
}> = ({ label, start, u, value, up }) => {
  const frame = useCurrentFrame();
  const C = useColors();
  return (
    <div
      style={{
        display: "flex",
        alignItems: "baseline",
        justifyContent: "space-between",
        padding: `${22 * u}px 0`,
        borderBottom: `2px solid ${C.border}`,
        ...reveal(frame, start),
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 18 * u }}>
        <span style={{ width: 14 * u, height: 14 * u, borderRadius: 4, background: up ? C.green : C.muted }} />
        <span style={{ fontFamily: SANS, fontSize: 44 * u, color: C.ink, fontWeight: 600 }}>{label}</span>
      </div>
      <span style={{ fontFamily: MONO, fontSize: 56 * u, color: up ? C.green : C.ink, fontWeight: 600 }}>
        {value}
      </span>
    </div>
  );
};

const Board: React.FC<{ data: DailyProps }> = ({ data }) => {
  const frame = useCurrentFrame();
  const C = useColors();
  const { u } = useU();
  return (
    <Scene dur={SCENES.board} u={u}>
      <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 72 * u, color: C.ink, letterSpacing: -1.5, ...reveal(frame, 0) }}>
        The board, today.
      </div>
      <div style={{ fontFamily: MONO, fontSize: 26 * u, color: C.muted, marginTop: 6 * u, ...reveal(frame, 4) }}>
        as of {data.date}
      </div>
      <div style={{ height: 24 * u }} />
      <BoardRow label="KSE-100 (PSX)" start={14} u={u}
        value={<Counter to={data.macro.kse100} decimals={0} start={14} dur={26} />} />
      <BoardRow label="Rupee / US$" start={26} u={u}
        value={<Counter to={data.macro.pkrUsd} decimals={2} prefix="₨" start={26} dur={26} />} />
      <BoardRow label="Gold · 24k/tola" start={38} u={u} up
        value={<Counter to={data.gold.tola} decimals={0} prefix="₨" locale="en-IN" start={38} dur={26} />} />
      <BoardRow label="SBP policy rate" start={50} u={u}
        value={<Counter to={data.macro.sbpRate} decimals={2} suffix="%" start={50} dur={26} />} />
      <BoardRow label="CPI inflation" start={62} u={u}
        value={<Counter to={data.macro.inflation} decimals={1} suffix="%" start={62} dur={26} />} />
    </Scene>
  );
};

// =========================================================================
// 3 / 4 — Trend line charts (PSX + gold share one layout)
// =========================================================================
export const TrendScene: React.FC<{
  dur: number;
  kicker: string;
  heading: string;
  value: React.ReactNode;
  chip?: { text: string; color: string };
  series: DailyProps["kseSeries"];
  color: string;
  fill: string;
  // Optional pacing/size overrides for long-form reuse (WeeklyBrief); the
  // defaults reproduce the daily brief exactly.
  chartStart?: number;
  chartDur?: number;
  chartHeight?: number;
}> = ({ dur, kicker, heading, value, chip, series, color, fill, chartStart = 16, chartDur = 42, chartHeight = 360 }) => {
  const frame = useCurrentFrame();
  const C = useColors();
  const { u, width } = useU();
  const chartW = width - 168 * u;
  const chartH = chartHeight * u;
  return (
    <Scene dur={dur} u={u}>
      <div style={{ ...reveal(frame, 0) }}>
        <Kicker u={u}>{kicker}</Kicker>
      </div>
      <div style={{ height: 18 * u }} />
      <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", ...reveal(frame, 6) }}>
        <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 96 * u, color: C.ink, letterSpacing: -2, lineHeight: 1 }}>
          {value}
        </div>
        {chip ? (
          <div
            style={{
              fontFamily: MONO,
              fontSize: 34 * u,
              fontWeight: 600,
              color: C.paper,
              background: chip.color,
              padding: `${10 * u}px ${20 * u}px`,
              borderRadius: 12,
              marginBottom: 8 * u,
            }}
          >
            {chip.text}
          </div>
        ) : null}
      </div>
      <div style={{ fontFamily: SANS, fontSize: 40 * u, color: C.ink, fontWeight: 600, marginTop: 8 * u, ...reveal(frame, 10) }}>
        {heading}
      </div>
      <div style={{ height: 28 * u }} />
      <div style={{ ...reveal(frame, 14) }}>
        <AreaChart values={series.values} width={chartW} height={chartH} color={color} fill={fill} start={chartStart} dur={chartDur} strokeWidth={7 * u} />
        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8 * u, fontFamily: MONO, fontSize: 26 * u, color: C.muted }}>
          <span>{series.firstLabel}</span>
          <span>{series.lastLabel}</span>
        </div>
      </div>
    </Scene>
  );
};

const Psx: React.FC<{ data: DailyProps }> = ({ data }) => {
  const C = useColors();
  return (
    <TrendScene
      dur={SCENES.psx}
      kicker="PSX · KSE-100"
      heading="The benchmark, over time."
      value={<Counter to={data.macro.kse100} decimals={0} start={6} dur={30} />}
      series={data.kseSeries}
      color={C.green}
      fill={C.greenLight}
    />
  );
};

const Gold: React.FC<{ data: DailyProps }> = ({ data }) => {
  const C = useColors();
  return (
    <TrendScene
      dur={SCENES.gold}
      kicker="Gold · 24k per tola"
      heading="A hedge against a weak rupee."
      value={<Counter to={data.gold.tola} decimals={0} prefix="₨" locale="en-IN" start={6} dur={30} />}
      chip={{ text: `${data.gold.change1y >= 0 ? "▲" : "▼"} ${data.gold.change1y.toFixed(1)}% · 1yr`, color: data.gold.change1y >= 0 ? C.green : C.red }}
      series={data.goldSeries}
      color={GOLD_DARK}
      fill={C.goldPale}
    />
  );
};

// =========================================================================
// 5 — PSX top movers (horizontal bars). MoverBar is the single animated row,
// shared with WeeklyBrief (which also has negative weekly movers — the sign
// drives the prefix; daily's all-positive data renders exactly as before).
// =========================================================================
export const MoverBar: React.FC<{
  ticker: string;
  name: string;
  pct: number;
  color: string;
  max: number;
  start: number;
  u: number;
  dur?: number;
}> = ({ ticker, name, pct, color, max, start, u, dur = 32 }) => {
  const frame = useCurrentFrame();
  const C = useColors();
  const { fps } = useVideoConfig();
  const grow = spring({ frame: frame - start, fps, config: { damping: 200 }, durationInFrames: dur });
  return (
    <div style={{ marginBottom: 26 * u, ...reveal(frame, start) }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 8 * u }}>
        <span style={{ fontFamily: SANS, fontWeight: 700, fontSize: 40 * u, color: C.ink }}>
          <span style={{ fontFamily: MONO, color, marginRight: 14 * u }}>{ticker}</span>
          {name}
        </span>
        <span style={{ fontFamily: MONO, fontWeight: 600, fontSize: 44 * u, color }}>
          <Counter to={pct} from={0} decimals={1} prefix={pct >= 0 ? "+" : ""} suffix="%" start={start} dur={dur} />
        </span>
      </div>
      <div style={{ height: 22 * u, background: C.border, borderRadius: 8, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${(Math.abs(pct) / max) * 100 * grow}%`, background: color, borderRadius: 8 }} />
      </div>
    </div>
  );
};

const Movers: React.FC<{ data: DailyProps }> = ({ data }) => {
  const frame = useCurrentFrame();
  const C = useColors();
  const { u } = useU();
  const max = Math.max(...data.movers.map((m) => Math.abs(m.change1y)), 1);
  const palette = [C.green, C.navy, GOLD_DARK, C.ink];
  return (
    <Scene dur={SCENES.movers} u={u}>
      <div style={{ ...reveal(frame, 0) }}>
        <Kicker u={u}>PSX · Top movers · 1 year</Kicker>
      </div>
      <div style={{ height: 14 * u }} />
      <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 64 * u, color: C.ink, letterSpacing: -1.5, ...reveal(frame, 4) }}>
        Who ran this year.
      </div>
      <div style={{ height: 34 * u }} />
      {data.movers.map((m, i) => (
        <MoverBar
          key={i}
          ticker={m.ticker}
          name={m.name}
          pct={m.change1y}
          color={palette[i % palette.length]}
          max={max}
          start={14 + i * 8}
          u={u}
        />
      ))}
    </Scene>
  );
};

// =========================================================================
// 6 — Spotlight (rotating bonus scene: tool promo / rate check / question)
// One uniform layout for all three kinds — kicker, big heading with a spring
// punch-in, one body line, a CTA chip. The chip goes gold for `question`
// (comment prompt) and green for the site-link kinds. Falls back to a default
// tool promo when the prop is absent (older props files must never leave a
// blank 3.8s hole).
// =========================================================================
const SPOT_FALLBACK: NonNullable<DailyProps["spotlight"]> = {
  kind: "tool",
  kicker: "Free tool",
  heading: "SIP Calculator",
  body: "Monthly bachat, 10 saal — kitna banega?",
  cta: "pakinvestlysis.com/sip-calculator",
};

const Spotlight: React.FC<{ data: DailyProps }> = ({ data }) => {
  const frame = useCurrentFrame();
  const C = useColors();
  const { u } = useU();
  const { fps } = useVideoConfig();
  const s = data.spotlight ?? SPOT_FALLBACK;
  const gold = s.kind === "question";
  const pop = spring({ frame: frame - 8, fps, config: { damping: 14 }, durationInFrames: 30 });
  return (
    <Scene dur={SCENES.spot} u={u}>
      <div style={{ display: "flex", justifyContent: "center", ...reveal(frame, 0) }}>
        <Kicker u={u}>{s.kicker}</Kicker>
      </div>
      <div style={{ height: 36 * u }} />
      <div
        style={{
          fontFamily: SANS,
          fontWeight: 800,
          fontSize: 96 * u,
          lineHeight: 1.04,
          letterSpacing: -2,
          color: C.ink,
          textAlign: "center",
          opacity: Math.min(1, pop * 1.6),
          transform: `scale(${0.85 + pop * 0.15})`,
        }}
      >
        {s.heading}
      </div>
      <div
        style={{
          fontFamily: SANS,
          fontWeight: 600,
          fontSize: 42 * u,
          color: C.ink,
          textAlign: "center",
          marginTop: 30 * u,
          ...reveal(frame, 24),
        }}
      >
        {s.body}
      </div>
      <div style={{ display: "flex", justifyContent: "center", marginTop: 40 * u, ...reveal(frame, 38) }}>
        <div
          style={{
            fontFamily: MONO,
            fontWeight: 600,
            fontSize: 38 * u,
            color: gold ? C.ink : C.paper,
            background: gold ? C.gold : C.green,
            padding: `${18 * u}px ${44 * u}px`,
            borderRadius: 14,
            letterSpacing: 1,
            boxShadow: gold
              ? "0 16px 36px -18px rgba(242,185,75,0.9)"
              : "0 16px 36px -18px rgba(7,94,75,0.7)",
          }}
        >
          {s.cta}
        </div>
      </div>
    </Scene>
  );
};

// =========================================================================
// 7 — CTA
// =========================================================================
const Cta: React.FC<{ data: DailyProps }> = ({ data }) => {
  const frame = useCurrentFrame();
  const C = useColors();
  const { u, fps } = { ...useU(), fps: useVideoConfig().fps };
  const pop = spring({ frame: frame - 6, fps, config: { damping: 14 }, durationInFrames: 30 });
  const underline = interpolate(frame, [16, 40], [0, 100], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOut });
  return (
    <Scene dur={SCENES.cta} u={u}>
      <div style={{ transform: `scale(${0.9 + pop * 0.1})`, textAlign: "center" }}>
        <div style={{ position: "relative", display: "inline-block" }}>
          <Img src={staticFile("logo.png")} style={{ height: 132 * u, display: "block" }} />
          <div style={{ position: "absolute", left: 0, bottom: -14 * u, height: 10 * u, width: `${underline}%`, background: C.gold, borderRadius: 6 }} />
        </div>
      </div>
      <div style={{ fontFamily: SANS, fontSize: 40 * u, color: C.ink, fontWeight: 600, textAlign: "center", marginTop: 48 * u, ...reveal(frame, 26) }}>
        Compare savings, funds, stocks & gold
      </div>
      <div style={{ display: "flex", justifyContent: "center", marginTop: 36 * u, ...reveal(frame, 36) }}>
        <div
          style={{
            fontFamily: MONO,
            fontSize: 44 * u,
            color: C.paper,
            background: C.green,
            padding: `${24 * u}px ${52 * u}px`,
            borderRadius: 16,
            letterSpacing: 1,
            boxShadow: "0 18px 40px -18px rgba(7,94,75,0.7)",
          }}
        >
          pakinvestlysis.com →
        </div>
      </div>
      <div style={{ fontFamily: MONO, fontSize: 24 * u, color: C.muted, textAlign: "center", marginTop: 40 * u, ...reveal(frame, 48) }}>
        {data.footer}
      </div>
    </Scene>
  );
};

// =========================================================================
// 8 — Outro (engagement + next-session teaser)
// Session teaser is keyed off data.session ("Market open" -> tease the close,
// "Market close" -> tease the next open). Pure text + styled pills (no emoji),
// so it renders identically in headless CI.
// =========================================================================
// Engagement pill row (Like / Subscribe / Share) — shared with WeeklyBrief.
export const EngagePills: React.FC<{ u: number; start: number }> = ({ u, start }) => {
  const frame = useCurrentFrame();
  const C = useColors();
  const pills = ["Like", "Subscribe", "Share"];
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        gap: 22 * u,
        flexWrap: "wrap",
        ...reveal(frame, start),
      }}
    >
      {pills.map((p, i) => (
        <div
          key={p}
          style={{
            fontFamily: MONO,
            fontWeight: 600,
            fontSize: 42 * u,
            color: i === 1 ? C.paper : C.green,
            background: i === 1 ? C.green : "transparent",
            border: `3px solid ${C.green}`,
            padding: `${16 * u}px ${36 * u}px`,
            borderRadius: 14,
            letterSpacing: 1,
            boxShadow: i === 1 ? "0 14px 32px -16px rgba(7,94,75,0.7)" : "none",
          }}
        >
          {p}
        </div>
      ))}
    </div>
  );
};

const Outro: React.FC<{ data: DailyProps }> = ({ data }) => {
  const frame = useCurrentFrame();
  const C = useColors();
  const { u } = useU();
  const open = data.session === "Market open";
  return (
    <Scene dur={SCENES.outro} u={u}>
      <div style={{ display: "flex", justifyContent: "center", ...reveal(frame, 0) }}>
        <Kicker u={u}>{open ? "Coming up next" : "Same time tomorrow"}</Kicker>
      </div>
      <div style={{ height: 40 * u }} />
      <div
        style={{
          fontFamily: SANS,
          fontWeight: 800,
          fontSize: 80 * u,
          lineHeight: 1.05,
          letterSpacing: -2,
          color: C.ink,
          textAlign: "center",
          ...reveal(frame, 8),
        }}
      >
        {open ? (
          <>
            Stay tuned for the
            <br />
            <span style={{ color: C.green }}>market close</span>.
          </>
        ) : (
          <>
            Back for the next
            <br />
            <span style={{ color: C.green }}>market open</span>.
          </>
        )}
      </div>
      <div style={{ height: 56 * u }} />
      <EngagePills u={u} start={22} />
      <div
        style={{
          fontFamily: MONO,
          fontSize: 28 * u,
          color: C.muted,
          textAlign: "center",
          marginTop: 44 * u,
          letterSpacing: 3,
          ...reveal(frame, 34),
        }}
      >
        SUBSCRIBE FOR MORE · PAKINVESTLYSIS.COM
      </div>
    </Scene>
  );
};

// =========================================================================
// Audio — frame-synced SFX, reusing the shared kit.
// =========================================================================
const Sfx: React.FC<{ data: DailyProps }> = ({ data }) => {
  if (!data.audio.sfx) return null;
  const v = data.audio.volume;
  const s = starts();
  const cues: { at: number; src: string; vol: number; rate?: number }[] = [];
  // whoosh into each scene after the first
  ORDER.slice(1).forEach((k) => cues.push({ at: Math.max(0, s[k] - 2), src: "whoosh.wav", vol: 0.4 }));
  // hook headline (optional): pop on the punch-in, chime as the count-up lands
  if (data.headline) {
    cues.push({ at: 8, src: "pop.wav", vol: 0.5 });
    cues.push({ at: 44, src: "chime.wav", vol: 0.4 });
  }
  // board rows: ticks, gold row a chime
  [14, 26, 38, 50, 62].forEach((f, i) => cues.push({ at: s.board + f, src: i === 2 ? "chime.wav" : "tick.wav", vol: i === 2 ? 0.4 : 0.3 }));
  // charts sweep
  cues.push({ at: s.psx + 16, src: "sweep.wav", vol: 0.5 });
  cues.push({ at: s.gold + 16, src: "sweep.wav", vol: 0.5 });
  // movers ticks
  data.movers.forEach((_, i) => cues.push({ at: s.movers + 14 + i * 8, src: "tick.wav", vol: 0.3, rate: 1 + i * 0.06 }));
  // spotlight: heading pops in, chip lands with a click
  cues.push({ at: s.spot + 8, src: "pop.wav", vol: 0.5 });
  cues.push({ at: s.spot + 38, src: "click.wav", vol: 0.5 });
  // cta pop + payoff
  cues.push({ at: s.cta + 6, src: "pop.wav", vol: 0.55 });
  cues.push({ at: s.cta + 40, src: "chime.wav", vol: 0.45 });
  // outro: engagement pills land with a pop
  cues.push({ at: s.outro + 22, src: "pop.wav", vol: 0.5 });
  return (
    <>
      {cues.map((c, i) => (
        <Sequence key={i} from={c.at} layout="none">
          <Audio src={staticFile(c.src)} volume={() => c.vol * v} playbackRate={c.rate ?? 1} />
        </Sequence>
      ))}
    </>
  );
};

// Low background music bed under the SFX. Trimmed clip in public/music.mp3
// (24s, pre-faded); a frame envelope adds clean in/out and keeps it well below
// the SFX so counters/ticks stay legible. Gated on the same audio toggle.
// `total`/`loop` let WeeklyBrief (160s) reuse it — tiles the clip end-to-end
// with the volume callback re-offset per tile so one global envelope applies.
// Defaults reproduce the daily brief exactly (single un-looped clip).
const MUSIC_BASE = 0.14;
const MUSIC_CLIP_FRAMES = 720; // public/music.mp3 ≈ 24.0s @ 30fps
export const MusicBed: React.FC<{ volume: number; total?: number; loop?: boolean }> = ({
  volume,
  total,
  loop = false,
}) => {
  const t = total ?? dailyTotal();
  const env = (f: number) =>
    MUSIC_BASE *
    volume *
    interpolate(f, [0, 18, t - 30, t], [0, 1, 1, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
  if (!loop) {
    return <Audio src={staticFile("music.mp3")} volume={(f) => env(f)} />;
  }
  const tiles = Math.ceil(t / MUSIC_CLIP_FRAMES);
  return (
    <>
      {Array.from({ length: tiles }, (_, i) => (
        <Sequence
          key={i}
          from={i * MUSIC_CLIP_FRAMES}
          durationInFrames={Math.min(MUSIC_CLIP_FRAMES, t - i * MUSIC_CLIP_FRAMES)}
          layout="none"
        >
          <Audio src={staticFile("music.mp3")} volume={(f) => env(f + i * MUSIC_CLIP_FRAMES)} />
        </Sequence>
      ))}
    </>
  );
};

// =========================================================================
// Brand mark — the site logo (public/logo.png, copied from assets/logo.png),
// pinned top-center for the whole video so every frame is branded. Shared
// with WeeklyBrief. `h` is the logo height in u-units.
// =========================================================================
export const BrandMark: React.FC<{ u: number; h?: number }> = ({ u, h = 44 }) => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-start", pointerEvents: "none" }}>
    <Img
      src={staticFile("logo.png")}
      style={{ height: h * u, marginTop: 36 * u, opacity: 0.95 }}
    />
  </AbsoluteFill>
);

// =========================================================================
// Master
// =========================================================================
export const DailyBrief: React.FC<DailyProps> = (props) => {
  const s = starts();
  const scene = (k: SceneKey, node: React.ReactNode) => (
    <Sequence from={s[k]} durationInFrames={SCENES[k]} layout="none">
      {node}
    </Sequence>
  );
  return (
    <ColorProvider value={props.colors}>
      <AbsoluteFill style={{ backgroundColor: props.colors.paper }}>
        <PaperBg />
        {props.audio.sfx ? <MusicBed volume={props.audio.volume} /> : null}
        <Sfx data={props} />
        {scene("title", <Title data={props} />)}
        {scene("board", <Board data={props} />)}
        {scene("psx", <Psx data={props} />)}
        {scene("gold", <Gold data={props} />)}
        {scene("movers", <Movers data={props} />)}
        {scene("spot", <Spotlight data={props} />)}
        {scene("cta", <Cta data={props} />)}
        {scene("outro", <Outro data={props} />)}
        <BrandMarkAuto />
      </AbsoluteFill>
    </ColorProvider>
  );
};

// u depends on useVideoConfig, which needs a component inside the tree.
// Hidden during the CTA scene — that scene shows the logo full-size already.
const BrandMarkAuto: React.FC = () => {
  const { u } = useU();
  const frame = useCurrentFrame();
  const s = starts();
  if (frame >= s.cta && frame < s.cta + SCENES.cta) return null;
  return <BrandMark u={u} />;
};
