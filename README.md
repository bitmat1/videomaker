# Videomaker 🎬

Videos on demand. Describe the video you want; an AI writes the plan; open
tools find the footage, speak the narration, add captions and music, render
it and hand back an MP4.

```bash
make new PROMPT="a 30 second vertical explainer on why there are two tides a day"
# the AI (or you) writes projects/<slug>/plan.json — see docs/PLAN_SCHEMA.md
make video P=<slug>
# → output/<slug>/<slug>.mp4, thumbnail.jpg, <slug>.srt, credits.txt
```

It is the shape of [robot-reporter](https://github.com/bitmat1/robot-reporter)
generalised: Python stages that read and write files, Remotion to draw, ffmpeg
to finish. Instead of a fixed nightly programme, every run is a new request.

---

## Quick start

```bash
make setup      # venv + Python deps (once)
make install    # Remotion into remotion/node_modules (once)
make demo       # offline end-to-end check: no keys, no models, ~40s
```

`docs/SETUP.md` covers the optional extras: neural voices, caption alignment,
stock-media keys, the MCP servers.

## Asking an AI for a video

**In Claude Code**, in this folder: *"make me a 45-second landscape video
about the history of the bicycle"*. `CLAUDE.md` and the `make-video` skill
tell it what to do.

**From any MCP client** (Claude Desktop, other agents): the `videomaker`
server in `.mcp.json` exposes the pipeline as tools — `new_project`,
`write_plan`, `search_media`, `make_video`, `preview_frame` and more.

## The six stages

| Stage | Command | Reads | Writes |
|---|---|---|---|
| Plan | `make plan P=…` | `brief.json` | `plan.json` (validated) |
| Assets | `make assets P=…` | the plan | `assets/clips/`, `assets/photos/`, `assets.json` |
| Voice | `make voice P=…` | the plan | `voice/*.wav`, `voice.json` (word timings) |
| Build | `make build P=…` | plan + assets + voice | `remotion/public/project.json` + media |
| Render | `make render` | the manifest | `work/<slug>/render.mp4` |
| Finish | `make finish` | the render | `output/<slug>/` |

Each stage can be re-run alone. Changing a scene's words re-runs voice and
build, not the downloads; changing the look re-runs build and render only.
`make still F=60` renders one frame in seconds — use it before a full render.

## Folders

```
briefs/      example requests
projects/    one folder per video: brief → plan → assets → voice
assets/      shared media library: clips/, photos/, generated/, audio/music/, audio/sfx/
output/      finished videos, one folder each
work/        scratch: renders, stills, raw downloads
pipeline/    the Python stages
mcp_server/  the pipeline as MCP tools
remotion/    the renderer
```

## What's in the box

See **[TOOLS.md](TOOLS.md)** for every tool and MCP server, and why each is
included.
