import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { useColors } from "../schema";

// Ledger paper: faint horizontal rules, a red margin rule down the left,
// and a slow vignette drift so static scenes never feel dead.
export const PaperBg: React.FC<{ tint?: string }> = ({ tint }) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const C = useColors();
  const drift = interpolate(frame, [0, 200], [0, -24], {
    extrapolateRight: "extend",
  });

  const rows = Math.ceil(height / 64) + 2;

  return (
    <AbsoluteFill style={{ backgroundColor: tint ?? C.paper, overflow: "hidden" }}>
      {/* horizontal ledger rules */}
      <AbsoluteFill style={{ transform: `translateY(${drift}px)` }}>
        {Array.from({ length: rows }).map((_, i) => (
          <div
            key={i}
            style={{
              position: "absolute",
              top: i * 64,
              left: 0,
              width,
              height: 1,
              backgroundColor: C.border,
              opacity: 0.5,
            }}
          />
        ))}
      </AbsoluteFill>

      {/* left margin rule */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 96,
          width: 2,
          height,
          backgroundColor: C.red,
          opacity: 0.35,
        }}
      />

      {/* corner registration marks for the "printed brief" feel */}
      {[
        { top: 56, left: 56 },
        { top: 56, right: 56 },
        { bottom: 56, left: 56 },
        { bottom: 56, right: 56 },
      ].map((pos, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            ...pos,
            width: 26,
            height: 26,
            border: `2px solid ${C.ink}`,
            opacity: 0.12,
          }}
        />
      ))}

      {/* soft vignette */}
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(120% 80% at 50% 30%, rgba(0,0,0,0) 55%, rgba(16,24,40,0.10) 100%)",
        }}
      />
    </AbsoluteFill>
  );
};
