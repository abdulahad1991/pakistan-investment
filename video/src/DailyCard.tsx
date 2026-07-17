import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { loadFont as loadMono } from "@remotion/google-fonts/IBMPlexMono";
import { type DailyProps } from "./dailySchema";
import { ColorProvider, useColors } from "./schema";
import { PaperBg } from "./components/PaperBg";
import { Counter, reveal } from "./components/Ledger";
import { AreaChart, Donut } from "./components/Charts";

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
  const donut = 208 * u;

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

      {/* fuel pills — OGRA retail rates, same weight as the macro row so petrol
          reads as one metric among many, not the headline */}
      {data.fuel && (
        <div style={{ display: "flex", gap: 16 * u }}>
          {(
            [
              ["Petrol ₨/L", data.fuel.petrol],
              ["Diesel HSD", data.fuel.hsd],
              ["Kerosene", data.fuel.kerosene],
              ["LDO", data.fuel.ldo],
            ] as [string, number | null | undefined][]
          )
            .filter(([, v]) => v != null)
            .map(([label, v], i) => (
              <Pill
                key={label}
                label={label}
                u={u}
                start={5 + i}
                accent
                vSize={34}
                value={<Counter to={v as number} decimals={2} prefix="₨" start={5 + i} dur={22} />}
              />
            ))}
        </div>
      )}

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

      {/* gold + dollar | donut */}
      <div style={{ display: "flex", gap: 18 * u, alignItems: "stretch" }}>
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 16 * u }}>
          <div style={{ flex: 1, background: C.greenLight, borderRadius: 20 * u, padding: 22 * u, ...reveal(frame, 20, 12) }}>
            <div style={{ fontFamily: MONO, fontSize: 22 * u, letterSpacing: 1, textTransform: "uppercase", color: GOLD_DARK }}>
              Gold · 24k / tola
            </div>
            <div style={{ fontFamily: MONO, fontWeight: 600, fontSize: 52 * u, color: C.ink, marginTop: 4 * u }}>
              <Counter to={data.gold.tola} decimals={0} prefix="₨" locale="en-IN" start={20} dur={28} />
            </div>
            <div style={{ fontFamily: MONO, fontSize: 28 * u, color: data.gold.change1y >= 0 ? C.green : C.red, marginTop: 4 * u }}>
              {data.gold.change1y >= 0 ? "▲" : "▼"} {data.gold.change1y.toFixed(1)}% · 1 year
            </div>
          </div>
          {/* top movers strip */}
          <div style={{ background: C.paper, border: `2px solid ${C.border}`, borderRadius: 20 * u, padding: 20 * u, ...reveal(frame, 24, 12) }}>
            <div style={{ fontFamily: MONO, fontSize: 20 * u, letterSpacing: 1, textTransform: "uppercase", color: C.muted, marginBottom: 8 * u }}>
              Top PSX movers · 1yr
            </div>
            {data.movers.slice(0, 3).map((m, i) => (
              <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", padding: `${5 * u}px 0` }}>
                <span style={{ fontFamily: SANS, fontWeight: 600, fontSize: 28 * u, color: C.ink }}>
                  <span style={{ fontFamily: MONO, color: C.green, marginRight: 12 * u }}>{m.ticker}</span>
                  {m.name}
                </span>
                <span style={{ fontFamily: MONO, fontWeight: 600, fontSize: 28 * u, color: C.green }}>+{m.change1y.toFixed(1)}%</span>
              </div>
            ))}
          </div>
        </div>

        {/* allocation donut */}
        <div style={{ flex: 1, background: C.paper, border: `2px solid ${C.border}`, borderRadius: 20 * u, padding: 22 * u, display: "flex", gap: 18 * u, alignItems: "center", ...reveal(frame, 22, 12) }}>
          <div style={{ position: "relative", width: donut, height: donut, flexShrink: 0 }}>
            <Donut slices={data.allocation.map((a) => ({ pct: a.pct, color: a.color }))} size={donut} thickness={donut * 0.24} start={22} dur={30} track={C.border} />
            <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: SANS, fontWeight: 800, fontSize: 26 * u, color: C.muted }}>
              MIX
            </div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 * u }}>
            <div style={{ fontFamily: MONO, fontSize: 22 * u, letterSpacing: 1, textTransform: "uppercase", color: C.muted }}>
              Sample balance
            </div>
            {data.allocation.map((a, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 12 * u }}>
                <span style={{ width: 22 * u, height: 22 * u, borderRadius: 6, background: a.color, flexShrink: 0 }} />
                <span style={{ fontFamily: MONO, fontWeight: 600, fontSize: 28 * u, color: C.ink, width: 64 * u }}>{a.pct}%</span>
                <span style={{ fontFamily: SANS, fontWeight: 600, fontSize: 27 * u, color: C.ink }}>{a.label}</span>
              </div>
            ))}
          </div>
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
