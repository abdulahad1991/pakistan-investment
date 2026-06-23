import React from "react";
import { useCurrentFrame, interpolate, Easing } from "remotion";

const easeOut = Easing.bezier(0.16, 1, 0.3, 1);

// --------------------------------------------------------------------------
// AreaChart — an animated line + soft area fill, drawn left-to-right via a
// growing clip rect (no DOM measurement needed). Pure SVG so it renders
// deterministically in Remotion. The end-point dot fades in as the line lands.
// --------------------------------------------------------------------------
export const AreaChart: React.FC<{
  values: number[];
  width: number;
  height: number;
  color: string;
  fill: string;
  start?: number; // local frame to begin drawing
  dur?: number;
  strokeWidth?: number;
}> = ({ values, width, height, color, fill, start = 0, dur = 40, strokeWidth = 6 }) => {
  const frame = useCurrentFrame();
  const pad = strokeWidth + 2;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const n = values.length;

  const x = (i: number) => pad + (i / (n - 1)) * (width - pad * 2);
  const y = (v: number) => pad + (1 - (v - min) / span) * (height - pad * 2);

  const pts = values.map((v, i) => [x(i), y(v)] as const);
  const line = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p[0]},${p[1]}`).join(" ");
  const area = `${line} L${pts[n - 1][0]},${height - pad} L${pts[0][0]},${height - pad} Z`;

  const p = interpolate(frame, [start, start + dur], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: easeOut,
  });
  const revealW = (width - pad * 2) * p + pad;
  const dotOp = interpolate(frame, [start + dur - 8, start + dur], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const clipId = `clip-${values.length}-${Math.round(values[0])}`;

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      <defs>
        <clipPath id={clipId}>
          <rect x={0} y={0} width={revealW} height={height} />
        </clipPath>
      </defs>
      {/* baseline */}
      <line x1={pad} y1={height - pad} x2={width - pad} y2={height - pad} stroke={color} strokeOpacity={0.18} strokeWidth={2} />
      <g clipPath={`url(#${clipId})`}>
        <path d={area} fill={fill} />
        <path d={line} fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinejoin="round" strokeLinecap="round" />
      </g>
      <circle cx={pts[n - 1][0]} cy={pts[n - 1][1]} r={strokeWidth + 4} fill={color} opacity={dotOp} />
      <circle cx={pts[n - 1][0]} cy={pts[n - 1][1]} r={strokeWidth + 12} fill={color} opacity={dotOp * 0.18} />
    </svg>
  );
};

// --------------------------------------------------------------------------
// Donut — animated clockwise sweep of proportional slices via stroke-dasharray.
// `slices` are {pct,color}; pct values should sum to ~100.
// --------------------------------------------------------------------------
export const Donut: React.FC<{
  slices: { pct: number; color: string }[];
  size: number;
  thickness?: number;
  start?: number;
  dur?: number;
  track?: string;
}> = ({ slices, size, thickness = 46, start = 0, dur = 44, track = "#DDE3EA" }) => {
  const frame = useCurrentFrame();
  const r = (size - thickness) / 2;
  const C = 2 * Math.PI * r;
  const total = slices.reduce((s, x) => s + x.pct, 0) || 1;

  const sweep = interpolate(frame, [start, start + dur], [0, C], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: easeOut,
  });

  let cum = 0;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <g transform={`rotate(-90 ${size / 2} ${size / 2})`}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={track} strokeOpacity={0.5} strokeWidth={thickness} />
        {slices.map((s, i) => {
          const len = (s.pct / total) * C;
          const drawn = Math.max(0, Math.min(len, sweep - cum));
          const offset = -cum;
          cum += len;
          return (
            <circle
              key={i}
              cx={size / 2}
              cy={size / 2}
              r={r}
              fill="none"
              stroke={s.color}
              strokeWidth={thickness}
              strokeDasharray={`${drawn} ${C}`}
              strokeDashoffset={offset}
              strokeLinecap="butt"
            />
          );
        })}
      </g>
    </svg>
  );
};
