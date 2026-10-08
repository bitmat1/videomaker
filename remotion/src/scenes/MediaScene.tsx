import React from "react";
import {
  AbsoluteFill,
  Img,
  Loop,
  OffthreadVideo,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";
import type { Motion, Scene, Style } from "../types";

/** Slow camera move over a still or clip. Transforms only: filters and blur
 * are an order of magnitude slower in headless Chrome. */
export const motionTransform = (
  motion: Motion,
  frame: number,
  length: number
): string => {
  const t = interpolate(frame, [0, Math.max(1, length)], [0, 1], {
    extrapolateRight: "clamp",
  });
  switch (motion) {
    case "zoom-in":
      return `scale(${1.04 + 0.1 * t})`;
    case "zoom-out":
      return `scale(${1.14 - 0.1 * t})`;
    case "pan-left":
      return `scale(1.15) translateX(${4 - 8 * t}%)`;
    case "pan-right":
      return `scale(1.15) translateX(${-4 + 8 * t}%)`;
    default:
      return "none";
  }
};

export const MediaScene: React.FC<{
  scene: Scene;
  style: Style;
  fps: number;
}> = ({ scene, style }) => {
  const frame = useCurrentFrame();
  const media = scene.media;
  if (!media) {
    return null;
  }
  const length = scene.endFrame - scene.startFrame;
  const fill: React.CSSProperties = {
    width: "100%",
    height: "100%",
    objectFit: "cover",
    transform: motionTransform(scene.motion, frame, length),
  };
  return (
    <AbsoluteFill style={{ backgroundColor: style.background, overflow: "hidden" }}>
      {media.kind === "video" ? (
        <Loop durationInFrames={media.durationInFrames ?? length}>
          <OffthreadVideo src={staticFile(media.src)} muted style={fill} />
        </Loop>
      ) : (
        <Img src={staticFile(media.src)} style={fill} />
      )}
      {scene.text ? <Overlay text={scene.text} style={style} /> : null}
      {scene.credit ? <Credit text={scene.credit} style={style} /> : null}
    </AbsoluteFill>
  );
};

const Overlay: React.FC<{ text: string; style: Style }> = ({ text, style }) => (
  <AbsoluteFill style={{ justifyContent: "flex-start", padding: "6%" }}>
    <div
      style={{
        alignSelf: "flex-start",
        padding: "0.3em 0.6em",
        backgroundColor: "rgba(0, 0, 0, 0.55)",
        borderLeft: `0.25em solid ${style.accent}`,
        color: style.text,
        fontFamily: style.font,
        fontWeight: 800,
        fontSize: 64,
      }}
    >
      {text}
    </div>
  </AbsoluteFill>
);

const Credit: React.FC<{ text: string; style: Style }> = ({ text, style }) => (
  <AbsoluteFill
    style={{ justifyContent: "flex-start", alignItems: "flex-end", padding: 18 }}
  >
    <div
      style={{
        color: style.text,
        opacity: 0.7,
        fontFamily: style.font,
        fontSize: 18,
        backgroundColor: "rgba(0, 0, 0, 0.35)",
        padding: "2px 8px",
        borderRadius: 4,
      }}
    >
      {text}
    </div>
  </AbsoluteFill>
);
