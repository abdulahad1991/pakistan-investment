import React from "react";
import { useCurrentFrame, interpolate, Easing } from "remotion";

const easeOut = Easing.bezier(0.16, 1, 0.3, 1);

// Count-up number. `decimals` controls precision; `locale` controls digit
// grouping ("en-IN" => Pakistani lakh/crore grouping X,XX,XXX).
export const Counter: React.FC<{
  to: number;
  from?: number;
  start?: number; // local frame to begin
  dur?: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  locale?: string;
  style?: React.CSSProperties;
}> = ({ to, from = 0, start = 0, dur = 30, decimals = 0, prefix = "", suffix = "", locale = "en-US", style }) => {
  const frame = useCurrentFrame();
  const v = interpolate(frame, [start, start + dur], [from, to], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: easeOut,
  });
  const txt = v.toLocaleString(locale, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
  return (
    <span style={style}>
      {prefix}
      {txt}
      {suffix}
    </span>
  );
};

// Slide + fade entrance driven purely by frame (no CSS transitions).
export const reveal = (frame: number, start: number, dur = 18) => {
  const p = interpolate(frame, [start, start + dur], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: easeOut,
  });
  return { opacity: p, transform: `translateY(${(1 - p) * 26}px)` };
};

// Scene-level fade in then out, given the local frame and scene length.
export const fadeInOut = (frame: number, total: number, fade = 14) => {
  return interpolate(frame, [0, fade, total - fade, total], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
};
