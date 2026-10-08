import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setJpegQuality(85);
Config.setOverwriteOutput(true);

// Each unit is a headless Chrome. Past roughly half the cores, memory
// pressure costs more than the parallelism gains.
Config.setConcurrency(Number(process.env.REMOTION_CONCURRENCY ?? 3));

// Use an already-installed Chromium (CI, containers) instead of letting
// Remotion download its own headless shell on first render.
if (process.env.REMOTION_BROWSER) {
  Config.setBrowserExecutable(process.env.REMOTION_BROWSER);
}
