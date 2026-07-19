import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { loadFont as loadMono } from "@remotion/google-fonts/IBMPlexMono";
import { type WeeklyProps } from "./weeklySchema";
import { ColorProvider, useColors } from "./schema";
import { PaperBg } from "./components/PaperBg";
import { Counter, reveal } from "./components/Ledger";

// Weekly digest still — the FB "Weekly Digest" image post. One dense 1:1 recap:
// KSE + gold week moves, the rate board, current petrol, and the top movers.

const { fontFamily: SANS } = loadInter("normal", {
  weights: ["600", "700", "800"],
  subsets: ["latin"],
});
const { fontFamily: MONO } = loadMono("normal", {
  weights: ["600"],
  subsets: ["latin"],
});
const GOLD_DARK = "#B7791F";

const BigStat: React.FC<{
  label: string;
  close: number;
  pct: number;
  u: number;
  start: number;
  locale?: string;
}> = ({ label, close, pct, u, start, locale }) => {
  const frame = useCurrentFrame();
  const C = useColors();
  const up = pct >= 0;
  return (
    <div style={{ flex: 1, minWidth: 0, background: C.greenLight, borderRadius: 24 * u, padding: 30 * u, ...reveal(frame, start, 12) }}>
      <div style={{ fontFamily: MONO, fontSize: 22 * u, letterSpacing: 1, textTransform: "uppercase", color: GOLD_DARK }}>
        {label}
      </div>
      <div style={{ fontFamily: MONO, fontWeight: 600, fontSize: 66 * u, color: C.ink, marginTop: 6 * u, whiteSpace: "nowrap" }}>
        <Counter to={close} decimals={0} prefix="₨" locale={locale} start={start} dur={26} />
      </div>
      <div style={{ fontFamily: MONO, fontSize: 30 * u, color: up ? C.green : C.red, marginTop: 4 * u }}>
        {up ? "▲" : "▼"} {Math.abs(pct).toFixed(1)}% this week
      </div>
    </div>
  );
};

const MiniPill: React.FC<{ label: string; value: string; u: number; start: number }> = ({ label, value, u, start }) => {
  const frame = useCurrentFrame();
  const C = useColors();
  return (
    <div style={{ flex: 1, minWidth: 0, background: C.paper, border: `2px solid ${C.border}`, borderRadius: 18 * u, padding: `${18 * u}px ${18 * u}px`, ...reveal(frame, start, 12) }}>
      <div style={{ fontFamily: MONO, fontSize: 19 * u, letterSpacing: 1, textTransform: "uppercase", color: C.muted, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
        {label}
      </div>
      <div style={{ fontFamily: MONO, fontWeight: 600, fontSize: 38 * u, color: C.ink, marginTop: 4 * u, whiteSpace: "nowrap" }}>
        {value}
      </div>
    </div>
  );
};

const Card: React.FC<{ data: WeeklyProps }> = ({ data }) => {
  const frame = useCurrentFrame();
  const C = useColors();
  const { width, height } = useVideoConfig();
  const u = Math.min(width, height) / 1080;
  const pad = 60 * u;
  const petrol = data.fuel?.petrol;
  const movers = (data.movers || []).slice(0, 3);

  return (
    <AbsoluteFill style={{ padding: pad, justifyContent: "space-between" }}>
      {/* header */}
      <div style={{ ...reveal(frame, 0, 12) }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 * u }}>
          <span style={{ width: 40 * u, height: 4, background: C.gold, display: "inline-block" }} />
          <span style={{ fontFamily: SANS, fontWeight: 800, fontSize: 54 * u, color: C.ink, letterSpacing: -1 }}>
            Week in Review
          </span>
        </div>
        <div style={{ fontFamily: MONO, fontSize: 30 * u, color: C.muted, marginTop: 10 * u }}>
          Pakistan markets · {data.dateRange}
        </div>
      </div>

      {/* KSE + gold week moves */}
      <div style={{ display: "flex", gap: 20 * u }}>
        <BigStat label="KSE-100 (PSX)" close={data.kse.close} pct={data.kse.chgPct} u={u} start={4} />
        <BigStat label="Gold · 24k / tola" close={data.gold.close} pct={data.gold.chgPct} u={u} start={7} locale="en-IN" />
      </div>

      {/* rate board + petrol */}
      <div style={{ display: "flex", gap: 14 * u }}>
        <MiniPill label="SBP rate" value={`${data.rates.policy.toFixed(2)}%`} u={u} start={10} />
        <MiniPill label="Inflation" value={`${data.rates.inflation.toFixed(1)}%`} u={u} start={12} />
        <MiniPill label="₨ / US$" value={`₨${data.rates.usd.toFixed(2)}`} u={u} start={14} />
        {petrol != null && <MiniPill label="Petrol ₨/L" value={`₨${petrol.toFixed(2)}`} u={u} start={16} />}
      </div>

      {/* top movers this week */}
      {movers.length > 0 && (
        <div style={{ background: C.paper, border: `2px solid ${C.border}`, borderRadius: 22 * u, padding: 26 * u, ...reveal(frame, 18, 12) }}>
          <div style={{ fontFamily: MONO, fontSize: 22 * u, letterSpacing: 1, textTransform: "uppercase", color: C.muted, marginBottom: 10 * u }}>
            Top PSX movers · this week
          </div>
          {movers.map((m, i) => {
            const up = m.chgPct >= 0;
            return (
              <div key={m.sym} style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", padding: `${8 * u}px 0`, ...reveal(frame, 20 + i * 2, 10) }}>
                <span style={{ fontFamily: SANS, fontWeight: 600, fontSize: 32 * u, color: C.ink }}>
                  <span style={{ fontFamily: MONO, color: up ? C.green : C.red, marginRight: 14 * u }}>{m.sym}</span>
                  {m.name}
                </span>
                <span style={{ fontFamily: MONO, fontWeight: 600, fontSize: 32 * u, color: up ? C.green : C.red }}>
                  {up ? "+" : ""}{m.chgPct.toFixed(1)}%
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* footer */}
      <div style={{ display: "flex", justifyContent: "space-between", fontFamily: MONO, fontSize: 26 * u, color: C.muted, ...reveal(frame, 26, 12) }}>
        <span>Not financial advice · educational only</span>
        <span style={{ color: C.green, fontWeight: 600 }}>pakinvestlysis.com</span>
      </div>
    </AbsoluteFill>
  );
};

export const WeeklyCard: React.FC<WeeklyProps> = (props) => (
  <ColorProvider value={props.colors}>
    <AbsoluteFill style={{ backgroundColor: props.colors.paper }}>
      <PaperBg />
      <Card data={props} />
    </AbsoluteFill>
  </ColorProvider>
);
