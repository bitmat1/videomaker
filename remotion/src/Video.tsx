import React from "react";
import {
  AbsoluteFill,
  Audio,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { Captions } from "./Captions";
import { CardScene } from "./scenes/CardScene";
import { MediaScene } from "./scenes/MediaScene";
import { TitleScene } from "./scenes/TitleScene";
import type { Project, Scene, VideoProps } from "./types";

/** Crossfade length. The incoming scene starts this many frames early and
 * fades in over the outgoing one, so no frame is ever empty. */
const FADE = 12;

const SceneBody: React.FC<{ scene: Scene; project: Project }> = ({
  scene,
  project,
}) => {
  switch (scene.kind) {
    case "title":
      return <TitleScene scene={scene} style={project.style} />;
    case "media":
      return (
        <MediaScene scene={scene} style={project.style} fps={project.fps} />
      );
    default:
      return <CardScene scene={scene} style={project.style} />;
  }
};

const Faded: React.FC<{ lead: number; children: React.ReactNode }> = ({
  lead,
  children,
}) => {
  const frame = useCurrentFrame();
  const opacity =
    lead > 0
      ? interpolate(frame, [0, lead], [0, 1], { extrapolateRight: "clamp" })
      : 1;
  return <AbsoluteFill style={{ opacity }}>{children}</AbsoluteFill>;
};

export const Video: React.FC<VideoProps> = ({ project }) => {
  if (!project) {
    return <AbsoluteFill style={{ backgroundColor: "black" }} />;
  }
  const { audio, style, durationInFrames } = project;
  return (
    <AbsoluteFill style={{ backgroundColor: style.background }}>
      {project.scenes.map((scene) => {
        const lead =
          scene.transition === "fade" ? Math.min(FADE, scene.startFrame) : 0;
        return (
          <Sequence
            key={scene.id}
            from={scene.startFrame - lead}
            durationInFrames={scene.endFrame - scene.startFrame + lead}
          >
            <Faded lead={lead}>
              <SceneBody scene={scene} project={project} />
            </Faded>
          </Sequence>
        );
      })}
      {style.captions ? <Captions captions={project.captions} style={style} /> : null}
      {audio.narration ? <Audio src={staticFile(audio.narration)} /> : null}
      {audio.music ? (
        <Audio
          src={staticFile(audio.music)}
          loop
          volume={(f) =>
            audio.musicVolume *
            interpolate(
              f,
              [0, 15, durationInFrames - 45, durationInFrames],
              [0, 1, 1, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            )
          }
        />
      ) : null}
    </AbsoluteFill>
  );
};
