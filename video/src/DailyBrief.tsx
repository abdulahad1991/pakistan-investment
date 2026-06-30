import React from "react";
import {
  AbsoluteFill,
  Audio,
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
import { AreaChart, Donut } from "./components/Charts";

// Daily market brief — one short walks through the whole day's snapshot:
// macro board → PSX trend → gold trend → top movers → a sample allocation.
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
const easeOut = Easing.bezier(0.16, 1, 0.3, 1);
const GOLD_DARK = "#B7791F"; // matches site --gold2 (not in the shared palette)

// Fixed scene lengths (frames @30fps). Total drives calculateMetadata.
export const SCENES = {
  title: 66,
  board: 126,
  psx: 102,
  gold: 102,
  movers: 108,
  pie: 114,
  cta: 72,
  outro: 84,
} as const;
type SceneKey = keyof typeof SCENES;
const ORDER: SceneKey[] = ["title", "board", "psx", "gold", "movers", "pie", "cta", "outro"];

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
const useU = () => {
  const { width, height } = useVideoConfig();
  return { u: Math.min(width, height) / 1080, width, height };
};

const Kicker: React.FC<{ children: React.ReactNode; u: number; style?: React.CSSProperties }> = ({
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

const Scene: React.FC<{ dur: number; u: number; children: React.ReactNode }> = ({
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
// 1 — Title
// =========================================================================
const Title: React.FC<{ data: DailyProps }> = ({ data }) => {
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

// =========================================================================
// 2 — Macro board (PSX, dollar, gold, policy rate)
// =========================================================================
const BoardRow: React.FC<{
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
const TrendScene: React.FC<{
  dur: number;
  kicker: string;
  heading: string;
  value: React.ReactNode;
  chip?: { text: string; color: string };
  series: DailyProps["kseSeries"];
  color: string;
  fill: string;
}> = ({ dur, kicker, heading, value, chip, series, color, fill }) => {
  const frame = useCurrentFrame();
  const C = useColors();
  const { u, width } = useU();
  const chartW = width - 168 * u;
  const chartH = 360 * u;
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
        <AreaChart values={series.values} width={chartW} height={chartH} color={color} fill={fill} start={16} dur={42} strokeWidth={7 * u} />
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
// 5 — PSX top movers (horizontal bars)
// =========================================================================
const Movers: React.FC<{ data: DailyProps }> = ({ data }) => {
  const frame = useCurrentFrame();
  const C = useColors();
  const { u, fps } = { ...useU(), fps: useVideoConfig().fps };
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
      {data.movers.map((m, i) => {
        const start = 14 + i * 8;
        const grow = spring({ frame: frame - start, fps, config: { damping: 200 }, durationInFrames: 32 });
        const color = palette[i % palette.length];
        return (
          <div key={i} style={{ marginBottom: 26 * u, ...reveal(frame, start) }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 8 * u }}>
              <span style={{ fontFamily: SANS, fontWeight: 700, fontSize: 40 * u, color: C.ink }}>
                <span style={{ fontFamily: MONO, color, marginRight: 14 * u }}>{m.ticker}</span>
                {m.name}
              </span>
              <span style={{ fontFamily: MONO, fontWeight: 600, fontSize: 44 * u, color }}>
                <Counter to={m.change1y} from={0} decimals={1} prefix="+" suffix="%" start={start} dur={32} />
              </span>
            </div>
            <div style={{ height: 22 * u, background: C.border, borderRadius: 8, overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${(Math.abs(m.change1y) / max) * 100 * grow}%`, background: color, borderRadius: 8 }} />
            </div>
          </div>
        );
      })}
    </Scene>
  );
};

// =========================================================================
// 6 — Allocation donut
// =========================================================================
const Pie: React.FC<{ data: DailyProps }> = ({ data }) => {
  const frame = useCurrentFrame();
  const C = useColors();
  const { u, width, height } = useU();
  const size = Math.min(width, height) * 0.5;
  const vertical = height > width * 1.2; // 9:16 -> stack donut over legend
  return (
    <Scene dur={SCENES.pie} u={u}>
      <div style={{ ...reveal(frame, 0) }}>
        <Kicker u={u}>One way to split a rupee</Kicker>
      </div>
      <div style={{ height: 14 * u }} />
      <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 64 * u, color: C.ink, letterSpacing: -1.5, ...reveal(frame, 4) }}>
        A balanced mix.
      </div>
      <div style={{ height: 36 * u }} />
      <div
        style={{
          display: "flex",
          flexDirection: vertical ? "column" : "row",
          alignItems: "center",
          justifyContent: "center",
          gap: 48 * u,
          ...reveal(frame, 10),
        }}
      >
        <div style={{ position: "relative", width: size, height: size, flexShrink: 0 }}>
          <Donut
            slices={data.allocation.map((a) => ({ pct: a.pct, color: a.color }))}
            size={size}
            thickness={size * 0.22}
            start={14}
            dur={46}
            track={C.border}
          />
          <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
            <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 30 * u, color: C.muted }}>SAMPLE</div>
            <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 26 * u, color: C.muted }}>mix</div>
          </div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 18 * u }}>
          {data.allocation.map((a, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 16 * u, ...reveal(frame, 22 + i * 5) }}>
              <span style={{ width: 26 * u, height: 26 * u, borderRadius: 6, background: a.color, flexShrink: 0 }} />
              <span style={{ fontFamily: MONO, fontWeight: 600, fontSize: 38 * u, color: C.ink, minWidth: 90 * u }}>{a.pct}%</span>
              <span style={{ fontFamily: SANS, fontWeight: 600, fontSize: 36 * u, color: C.ink }}>{a.label}</span>
            </div>
          ))}
        </div>
      </div>
      <div style={{ fontFamily: MONO, fontSize: 24 * u, color: C.muted, textAlign: "center", marginTop: 32 * u, ...reveal(frame, 50) }}>
        Illustrative only · not financial advice
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
          <span style={{ fontFamily: SANS, fontWeight: 800, fontSize: 92 * u, color: C.green, letterSpacing: -2 }}>
            Pakinvestlysis
          </span>
          <div style={{ position: "absolute", left: 0, bottom: -6 * u, height: 10 * u, width: `${underline}%`, background: C.gold, borderRadius: 6 }} />
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
// so it renders identically in headless CI; no narration on these briefs.
// =========================================================================
const Outro: React.FC<{ data: DailyProps }> = ({ data }) => {
  const frame = useCurrentFrame();
  const C = useColors();
  const { u } = useU();
  const open = data.session === "Market open";
  const pills = ["Like", "Subscribe", "Share"];
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
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          gap: 22 * u,
          flexWrap: "wrap",
          ...reveal(frame, 22),
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
  // board rows: ticks, gold row a chime
  [14, 26, 38, 50, 62].forEach((f, i) => cues.push({ at: s.board + f, src: i === 2 ? "chime.wav" : "tick.wav", vol: i === 2 ? 0.4 : 0.3 }));
  // charts sweep
  cues.push({ at: s.psx + 16, src: "sweep.wav", vol: 0.5 });
  cues.push({ at: s.gold + 16, src: "sweep.wav", vol: 0.5 });
  // movers ticks
  data.movers.forEach((_, i) => cues.push({ at: s.movers + 14 + i * 8, src: "tick.wav", vol: 0.3, rate: 1 + i * 0.06 }));
  // pie sweep + slice clicks
  cues.push({ at: s.pie + 14, src: "sweep.wav", vol: 0.45 });
  data.allocation.forEach((_, i) => cues.push({ at: s.pie + 22 + i * 5, src: "click.wav", vol: 0.4, rate: 1 + i * 0.08 }));
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
const MUSIC_BASE = 0.14;
const MusicBed: React.FC<{ volume: number }> = ({ volume }) => {
  const total = dailyTotal();
  return (
    <Audio
      src={staticFile("music.mp3")}
      volume={(f) =>
        MUSIC_BASE *
        volume *
        interpolate(f, [0, 18, total - 30, total], [0, 1, 1, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        })
      }
    />
  );
};

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
        {scene("pie", <Pie data={props} />)}
        {scene("cta", <Cta data={props} />)}
        {scene("outro", <Outro data={props} />)}
      </AbsoluteFill>
    </ColorProvider>
  );
};
