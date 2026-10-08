import React, { useMemo } from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import type { Scene, Style } from "../types";

/** Seeded LCG: the same scene id always draws the same shapes, so renders
 * are byte-identical and cacheable. Never Math.random() in a component. */
const lcg = (seed: number) => {
  let s = seed >>> 0;
  return () => {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
    return s / 4294967296;
  };
};

const hash = (text: string): number =>
  [...text].reduce((h, c) => Math.imul(h ^ c.charCodeAt(0), 16777619), 2166136261);

/** The fallback visual: drifting translucent discs behind optional text.
 * Stacked translucent shapes stand in for glow; no blur. */
export const CardScene: React.FC<{ scene: Scene; style: Style }> = ({
  scene,
  style,
}) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const discs = useMemo(() => {
    const rand = lcg(hash(scene.id));
    return Array.from({ length: 7 }, () => ({
      x: rand() * width,
      y: rand() * height,
      r: (0.15 + rand() * 0.35) * Math.min(width, height),
      dx: (rand() - 0.5) * 1.2,
      dy: (rand() - 0.5) * 1.2,
    }));
  }, [scene.id, width, height]);
  return (
    <AbsoluteFill style={{ backgroundColor: style.background, overflow: "hidden" }}>
      <svg width={width} height={height}>
        {discs.map((d, i) => (
          <circle
            key={i}
            cx={d.x + d.dx * frame}
            cy={d.y + d.dy * frame}
            r={d.r}
            fill={style.accent}
            opacity={0.07}
          />
        ))}
      </svg>
      {scene.text ? (
        <AbsoluteFill
          style={{ justifyContent: "center", alignItems: "center", padding: "10%" }}
        >
          <div
            style={{
              color: style.text,
              fontFamily: style.font,
              fontWeight: 700,
              fontSize: Math.round(Math.min(width, height) * 0.07),
              textAlign: "center",
              lineHeight: 1.2,
            }}
          >
            {scene.text}
          </div>
        </AbsoluteFill>
      ) : null}
    </AbsoluteFill>
  );
};
