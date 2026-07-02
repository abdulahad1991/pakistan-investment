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
import { type WeeklyProps } from "./weeklySchema";
import { ColorProvider, useColors } from "./schema";
import { PaperBg } from "./components/PaperBg";
import { Counter, reveal } from "./components/Ledger";
import {
  SANS,
  MONO,
  GOLD_DARK,
  VOICE_DUCK,
  useU,
  Kicker,
  Scene,
  BoardRow,
  TrendScene,
  MoverBar,
  EngagePills,
  MusicBed,
} from "./DailyBrief";

// Weekly market review — the long-form 16:9 sibling of the DailyBrief Short.
// Same design language and building blocks (Scene wrapper, TrendScene charts,
// board rows, mover bars, outro pills all imported from DailyBrief), paced
// much slower: six scenes over 160s so a voiceover can talk through each one.

// Fixed scene lengths (frames @30fps). Total = 4800 = 160s.
export const WEEKLY_SCENES = {
  title: 450, // 15s
  kse: 900, // 30s
  gold: 900, // 30s
  movers: 1050, // 35s
  board: 900, // 30s
  outro: 600, // 20s
} as const;
type WSceneKey = keyof typeof WEEKLY_SCENES;
const WORDER: WSceneKey[] = ["title", "kse", "gold", "movers", "board", "outro"];

export const weeklyTotal = () => WORDER.reduce((s, k) => s + WEEKLY_SCENES[k], 0);
const wStarts = (): Record<WSceneKey, number> => {
  let acc = 0;
  const o = {} as Record<WSceneKey, number>;
  for (const k of WORDER) {
    o[k] = acc;
    acc += WEEKLY_SCENES[k];
  }
  return o;
};

// "30 Jun – 4 Jul 2026" -> chart end labels ["30 Jun", "4 Jul 2026"].
const rangeLabels = (dateRange: string): [string, string] => {
  const parts = dateRange
    .split(/[–—]/)
    .map((p) => p.trim())
    .filter(Boolean);
  if (parts.length >= 2) return [parts[0], parts[parts.length - 1]];
  return ["", dateRange];
};

// Fall back to a straight open->close line when fewer than 2 points arrive.
const seriesVals = (s: WeeklyProps["kse"]) => (s.series.length >= 2 ? s.series : [s.open, s.close]);

const chipFor = (chgPct: number, green: string, red: string) => ({
  text: `${chgPct >= 0 ? "▲" : "▼"} ${Math.abs(chgPct).toFixed(2)}% · week`,
  color: chgPct >= 0 ? green : red,
});

// =========================================================================
// a — Title: brand kicker, "Week in Review", date range, KSE weekly % hero.
// =========================================================================
const WTitle: React.FC<{ data: WeeklyProps }> = ({ data }) => {
  const frame = useCurrentFrame();
  const C = useColors();
  const { u } = useU();
  const { fps } = useVideoConfig();
  const up = data.kse.chgPct >= 0;
  const accent = up ? C.green : C.red;
  const pop = spring({ frame: frame - 40, fps, config: { damping: 14 }, durationInFrames: 34 });
  return (
    <Scene dur={WEEKLY_SCENES.title} u={u}>
      <div style={{ display: "flex", justifyContent: "center", ...reveal(frame, 6) }}>
        <Kicker u={u}>Pakinvestlysis · Weekly</Kicker>
      </div>
      <div style={{ height: 30 * u }} />
      <div
        style={{
          fontFamily: SANS,
          fontWeight: 800,
          fontSize: 96 * u,
          lineHeight: 1.04,
          letterSpacing: -2,
          color: C.ink,
          textAlign: "center",
          ...reveal(frame, 16),
        }}
      >
        Pakistan Market — <span style={{ color: C.green }}>Week in Review</span>
      </div>
      <div
        style={{
          fontFamily: MONO,
          fontSize: 38 * u,
          color: C.muted,
          textAlign: "center",
          marginTop: 20 * u,
          ...reveal(frame, 28),
        }}
      >
        {data.dateRange}
      </div>
      <div style={{ height: 56 * u }} />
      <div
        style={{
          textAlign: "center",
          opacity: Math.min(1, pop * 1.6),
          transform: `scale(${0.82 + pop * 0.18})`,
        }}
      >
        <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 170 * u, lineHeight: 1, letterSpacing: -3, color: accent }}>
          <Counter to={data.kse.chgPct} decimals={2} prefix={up ? "+" : ""} suffix="%" start={44} dur={70} />
        </div>
        <div
          style={{
            fontFamily: MONO,
            fontSize: 30 * u,
            color: C.muted,
            letterSpacing: 3,
            textTransform: "uppercase",
            marginTop: 18 * u,
          }}
        >
          KSE-100 · this week
        </div>
      </div>
    </Scene>
  );
};

// =========================================================================
// b / c — Week trend charts (reuse TrendScene, slower chart draw).
// =========================================================================
const WKse: React.FC<{ data: WeeklyProps }> = ({ data }) => {
  const C = useColors();
  const [first, last] = rangeLabels(data.dateRange);
  return (
    <TrendScene
      dur={WEEKLY_SCENES.kse}
      kicker="PSX · KSE-100 · This week"
      heading="The benchmark, day by day."
      value={<Counter to={data.kse.close} decimals={0} start={10} dur={60} />}
      chip={chipFor(data.kse.chgPct, C.green, C.red)}
      series={{ values: seriesVals(data.kse), firstLabel: first, lastLabel: last }}
      color={C.green}
      fill={C.greenLight}
      chartStart={26}
      chartDur={110}
      chartHeight={430}
    />
  );
};

const WGold: React.FC<{ data: WeeklyProps }> = ({ data }) => {
  const C = useColors();
  const [first, last] = rangeLabels(data.dateRange);
  return (
    <TrendScene
      dur={WEEKLY_SCENES.gold}
      kicker="Gold · 24k per tola · This week"
      heading="A hedge against a weak rupee."
      value={<Counter to={data.gold.close} decimals={0} prefix="₨" locale="en-IN" start={10} dur={60} />}
      chip={chipFor(data.gold.chgPct, C.green, C.red)}
      series={{ values: seriesVals(data.gold), firstLabel: first, lastLabel: last }}
      color={GOLD_DARK}
      fill={C.goldPale}
      chartStart={26}
      chartDur={110}
      chartHeight={430}
    />
  );
};

// =========================================================================
// d — Top-5 weekly movers (reuse MoverBar; losers turn red).
// =========================================================================
const MOVER_STEP = 40; // frames between rows (slower than the Short's 8)

const WMovers: React.FC<{ data: WeeklyProps }> = ({ data }) => {
  const frame = useCurrentFrame();
  const C = useColors();
  const { u } = useU();
  const movers = data.movers.slice(0, 5);
  const max = Math.max(...movers.map((m) => Math.abs(m.chgPct)), 1);
  const palette = [C.green, C.navy, GOLD_DARK, C.ink, C.green];
  return (
    <Scene dur={WEEKLY_SCENES.movers} u={u}>
      <div style={{ ...reveal(frame, 0) }}>
        <Kicker u={u}>PSX · Top movers · This week</Kicker>
      </div>
      <div style={{ height: 14 * u }} />
      <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 64 * u, color: C.ink, letterSpacing: -1.5, ...reveal(frame, 8) }}>
        Who moved the market this week.
      </div>
      <div style={{ height: 34 * u }} />
      {movers.map((m, i) => (
        <MoverBar
          key={i}
          ticker={m.sym}
          name={m.name}
          pct={m.chgPct}
          color={m.chgPct >= 0 ? palette[i % palette.length] : C.red}
          max={max}
          start={20 + i * MOVER_STEP}
          dur={50}
          u={u}
        />
      ))}
    </Scene>
  );
};

// =========================================================================
// e — Rates board (reuse BoardRow; slower stagger).
// =========================================================================
const BOARD_STEPS = [20, 45, 70, 95, 120];

const WBoard: React.FC<{ data: WeeklyProps }> = ({ data }) => {
  const frame = useCurrentFrame();
  const C = useColors();
  const { u } = useU();
  return (
    <Scene dur={WEEKLY_SCENES.board} u={u}>
      <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 72 * u, color: C.ink, letterSpacing: -1.5, ...reveal(frame, 0) }}>
        The board, this week.
      </div>
      <div style={{ fontFamily: MONO, fontSize: 26 * u, color: C.muted, marginTop: 6 * u, ...reveal(frame, 6) }}>
        {data.dateRange}
      </div>
      <div style={{ height: 24 * u }} />
      <BoardRow label="KSE-100 (PSX)" start={BOARD_STEPS[0]} u={u}
        value={<Counter to={data.kse.close} decimals={0} start={BOARD_STEPS[0]} dur={50} />} />
      <BoardRow label="Rupee / US$" start={BOARD_STEPS[1]} u={u}
        value={<Counter to={data.rates.usd} decimals={2} prefix="₨" start={BOARD_STEPS[1]} dur={50} />} />
      <BoardRow label="Gold · 24k/tola" start={BOARD_STEPS[2]} u={u} up
        value={<Counter to={data.gold.close} decimals={0} prefix="₨" locale="en-IN" start={BOARD_STEPS[2]} dur={50} />} />
      <BoardRow label="SBP policy rate" start={BOARD_STEPS[3]} u={u}
        value={<Counter to={data.rates.policy} decimals={2} suffix="%" start={BOARD_STEPS[3]} dur={50} />} />
      <BoardRow label="CPI inflation" start={BOARD_STEPS[4]} u={u}
        value={<Counter to={data.rates.inflation} decimals={1} suffix="%" start={BOARD_STEPS[4]} dur={50} />} />
    </Scene>
  );
};

// =========================================================================
// f — Outro CTA (reuse the engagement pills; tease the daily cadence).
// =========================================================================
const WOutro: React.FC = () => {
  const frame = useCurrentFrame();
  const C = useColors();
  const { u } = useU();
  return (
    <Scene dur={WEEKLY_SCENES.outro} u={u}>
      <div style={{ display: "flex", justifyContent: "center", ...reveal(frame, 0) }}>
        <Kicker u={u}>Every trading day</Kicker>
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
          ...reveal(frame, 10),
        }}
      >
        Daily briefs, <span style={{ color: C.green }}>twice</span> every
        <br />
        trading day.
      </div>
      <div
        style={{
          fontFamily: SANS,
          fontSize: 40 * u,
          color: C.ink,
          fontWeight: 600,
          textAlign: "center",
          marginTop: 36 * u,
          ...reveal(frame, 24),
        }}
      >
        Compare savings, funds, stocks & gold — free at pakinvestlysis.com
      </div>
      <div style={{ height: 52 * u }} />
      <EngagePills u={u} start={38} />
      <div
        style={{
          fontFamily: MONO,
          fontSize: 28 * u,
          color: C.muted,
          textAlign: "center",
          marginTop: 44 * u,
          letterSpacing: 3,
          ...reveal(frame, 52),
        }}
      >
        SUBSCRIBE FOR MORE · PAKINVESTLYSIS.COM
      </div>
    </Scene>
  );
};

// =========================================================================
// Audio — frame-synced SFX, same kit + rules as the daily brief.
// =========================================================================
const WSfx: React.FC<{ data: WeeklyProps }> = ({ data }) => {
  if (!data.audio.sfx) return null;
  const v = data.audio.volume;
  const s = wStarts();
  const cues: { at: number; src: string; vol: number; rate?: number }[] = [];
  // whoosh into each scene after the first
  WORDER.slice(1).forEach((k) => cues.push({ at: Math.max(0, s[k] - 2), src: "whoosh.wav", vol: 0.4 }));
  // title: hero % pops in, chime as the count-up lands
  cues.push({ at: s.title + 40, src: "pop.wav", vol: 0.5 });
  cues.push({ at: s.title + 114, src: "chime.wav", vol: 0.4 });
  // charts sweep
  cues.push({ at: s.kse + 26, src: "sweep.wav", vol: 0.5 });
  cues.push({ at: s.gold + 26, src: "sweep.wav", vol: 0.5 });
  // movers ticks
  data.movers.slice(0, 5).forEach((_, i) =>
    cues.push({ at: s.movers + 20 + i * MOVER_STEP, src: "tick.wav", vol: 0.3, rate: 1 + i * 0.06 }),
  );
  // board rows: ticks, gold row a chime
  BOARD_STEPS.forEach((f, i) =>
    cues.push({ at: s.board + f, src: i === 2 ? "chime.wav" : "tick.wav", vol: i === 2 ? 0.4 : 0.3 }),
  );
  // outro: engagement pills land with a pop
  cues.push({ at: s.outro + 38, src: "pop.wav", vol: 0.5 });
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

// =========================================================================
// Master
// =========================================================================
export const WeeklyBrief: React.FC<WeeklyProps> = (props) => {
  const s = wStarts();
  const scene = (k: WSceneKey, node: React.ReactNode) => (
    <Sequence from={s[k]} durationInFrames={WEEKLY_SCENES[k]} layout="none">
      {node}
    </Sequence>
  );
  // Same narration contract as the daily brief: full-length track + a
  // constant duck on the music bed. SFX are untouched.
  const vo = props.voiceover?.enabled ? props.voiceover : null;
  return (
    <ColorProvider value={props.colors}>
      <AbsoluteFill style={{ backgroundColor: props.colors.paper }}>
        <PaperBg />
        {props.audio.sfx ? (
          <MusicBed volume={props.audio.volume * (vo ? VOICE_DUCK : 1)} total={weeklyTotal()} loop />
        ) : null}
        {vo ? <Audio src={staticFile(vo.file)} /> : null}
        <WSfx data={props} />
        {scene("title", <WTitle data={props} />)}
        {scene("kse", <WKse data={props} />)}
        {scene("gold", <WGold data={props} />)}
        {scene("movers", <WMovers data={props} />)}
        {scene("board", <WBoard data={props} />)}
        {scene("outro", <WOutro />)}
      </AbsoluteFill>
    </ColorProvider>
  );
};
