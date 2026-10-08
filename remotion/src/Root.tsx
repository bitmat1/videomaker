import React from "react";
import { CalculateMetadataFunction, Composition, staticFile } from "remotion";
import { Video } from "./Video";
import { MANIFEST_VERSION } from "./types";
import type { Project, VideoProps } from "./types";

/**
 * Duration, frame rate and size all come from project.json, so a new plan
 * changes the video with no edit to any TypeScript. calculateMetadata runs in
 * the browser: staticFile() works here, Node fs does not.
 */
const loadProject = async (): Promise<Project> => {
  const response = await fetch(staticFile("project.json"));
  if (!response.ok) {
    throw new Error(
      "public/project.json is missing. Run: make build P=<slug> (or make demo)"
    );
  }
  const project = (await response.json()) as Project;
  if (project.manifestVersion !== MANIFEST_VERSION) {
    throw new Error(
      `project.json is manifestVersion ${project.manifestVersion}, this ` +
        `renderer expects ${MANIFEST_VERSION}. Re-run pipeline/build.py.`
    );
  }
  return project;
};

const calculateMetadata: CalculateMetadataFunction<VideoProps> = async ({
  props,
}) => {
  const project = await loadProject();
  return {
    durationInFrames: project.durationInFrames,
    fps: project.fps,
    width: project.width,
    height: project.height,
    props: { ...props, project },
  };
};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="Video"
    component={Video}
    calculateMetadata={calculateMetadata}
    defaultProps={{ project: null }}
    durationInFrames={90}
    fps={30}
    width={1920}
    height={1080}
  />
);
