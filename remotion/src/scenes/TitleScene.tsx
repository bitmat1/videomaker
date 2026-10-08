import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import type { Scene, Style } from "../types";

export const TitleScene: React.FC<{ scene: Scene; style: Style }> = ({
  scene,
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const enter = spring({ frame, fps, config: { damping: 200 } });
  const bar = interpolate(frame, [6, 26], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill
      style={{
        backgroundColor: style.background,
        justifyContent: "center",
        alignItems: "center",
        padding: "8%",
      }}
    >
      <div
        style={{
          color: style.text,
          fontFamily: style.font,
          fontWeight: 800,
          fontSize: Math.round(Math.min(width, height) * 0.09),
          lineHeight: 1.1,
          textAlign: "center",
          opacity: enter,
          transform: `translateY(${(1 - enter) * 40}px)`,
        }}
      >
        {scene.text}
      </div>
      <div
        style={{
          marginTop: 36,
          height: 10,
          width: Math.round(width * 0.25 * bar),
          backgroundColor: style.accent,
          borderRadius: 5,
        }}
      />
    </AbsoluteFill>
  );
};
