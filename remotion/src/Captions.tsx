import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import type { Caption, Style } from "./types";

/** Burnt-in captions. Most social video is watched muted; the .srt sidecar
 * from finish.py covers platforms that render their own. */
export const Captions: React.FC<{ captions: Caption[]; style: Style }> = ({
  captions,
  style,
}) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const active = captions.find(
    (c) => frame >= c.startFrame && frame < c.endFrame
  );
  if (!active) {
    return null;
  }
  const portrait = height > width;
  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom: portrait ? height * 0.22 : height * 0.08,
      }}
    >
      <div
        style={{
          maxWidth: width * 0.84,
          padding: "0.25em 0.6em",
          borderRadius: 12,
          backgroundColor: "rgba(0, 0, 0, 0.62)",
          color: style.text,
          fontFamily: style.font,
          fontWeight: 700,
          fontSize: Math.round(Math.min(width, height) * 0.05),
          lineHeight: 1.25,
          textAlign: "center",
        }}
      >
        {active.text}
      </div>
    </AbsoluteFill>
  );
};
