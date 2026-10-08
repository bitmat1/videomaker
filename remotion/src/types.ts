/**
 * Manifest v1 — mirrors pipeline/manifest.py. Change one, change the other in
 * the same commit, and bump MANIFEST_VERSION.
 */
export const MANIFEST_VERSION = 1;

export type SceneKind = "title" | "media" | "card";
export type Motion = "none" | "zoom-in" | "zoom-out" | "pan-left" | "pan-right";
export type Transition = "cut" | "fade";

export type Media = {
  kind: "video" | "photo";
  src: string;
  /** Clip length; the renderer loops a clip shorter than its scene. */
  durationInFrames?: number;
};

export type Scene = {
  id: string;
  kind: SceneKind;
  startFrame: number;
  endFrame: number;
  text: string;
  motion: Motion;
  transition: Transition;
  media?: Media;
  credit?: string;
};

export type Caption = {
  startFrame: number;
  endFrame: number;
  text: string;
};

export type Style = {
  background: string;
  text: string;
  accent: string;
  font: string;
  captions: boolean;
};

export type Project = {
  manifestVersion: number;
  slug: string;
  title: string;
  fps: number;
  width: number;
  height: number;
  durationInFrames: number;
  scenes: Scene[];
  captions: Caption[];
  audio: {
    narration: string | null;
    music: string | null;
    musicVolume: number;
  };
  style: Style;
  credits: string[];
};

export type VideoProps = {
  project: Project | null;
};
