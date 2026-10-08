# Tools, and why each is here

Every tool earns its place by doing one job the pipeline needs. Core tools
are required; the rest are opt-in and the pipeline runs without them.

## Core

| Tool | Licence | Job | Why this one |
|---|---|---|---|
| **Remotion** 4.0.534 | Remotion Licence (free for individuals and companies ≤3 people; paid above) | Draws every frame from `project.json` | Video as React: layouts, text, motion and captions are code an AI can write and reason about. Deterministic, renders headless, parallel. Same renderer as robot-reporter. |
| **ffmpeg / ffprobe** | LGPL/GPL | Normalises clips, converts audio, loudness-normalises the master, grabs the thumbnail, probes media | The universal media tool; every other option wraps it. |
| **Python 3.11+ standard library** | PSF | The pipeline itself: HTTP, WAV, JSON | Zero dependencies to break; heavy tools stay optional. |
| **Node 18+ / TypeScript** | MIT / Apache-2.0 | Runs Remotion; `tsc` checks the renderer | Required by Remotion. |

## Planning (the "AI model" part)

| Tool | Job | Why |
|---|---|---|
| **The driving agent** (Claude Code, or any MCP client) | Writes `plan.json` | The plan is the creative work. The model already in the conversation writes better plans than a small local model, and needs no extra install. |
| **Ollama** (optional) | Writes the plan unattended (`--backend ollama`) | Local, free, offline; for scheduled or batch runs with no agent present. Same setup as robot-reporter. |

## Footage and images

| Tool | Key needed | Job | Why |
|---|---|---|---|
| **Pexels API** | free key | Stock video and photos | Large, high-quality library of real HD video; free licence, attribution appreciated not required. |
| **Pixabay API** | free key | Stock video and photos | Second large free library; widens the chance a query hits. |
| **Openverse API** | none | CC-licensed photos | Aggregates 800M+ openly licensed images; filtered to commercial-and-modify licences. Works with no setup. |
| **Wikimedia Commons API** | none | CC photos and video | Strong on real places, objects, history and science; works with no setup. |
| **yt-dlp** (optional) | none | Fetch a clip from a video page URL | Handles hundreds of sites. Only for footage you have rights to. |
| **PySceneDetect** (optional) | none | Split long footage into individual shots | Turns a long source video into usable cutaways. |

## Voice and captions

| Tool | Licence | Job | Why |
|---|---|---|---|
| **Kokoro** (optional, recommended) | Apache-2.0 | Neural narration | 82M params, near-commercial quality, runs on CPU. Already proven in robot-reporter. |
| **Piper** (optional) | MIT | Neural narration | Very fast ONNX voices in dozens of languages; good for non-English. |
| **macOS `say`** | built in | Narration | Zero install on a Mac. |
| **Mock voice** | — | Synthetic speech-shaped noise | Tests and CI with no model. |
| **faster-whisper** (optional) | MIT | Word-level timings for captions | Aligns captions to what was actually said, not an estimate. CTranslate2 makes it fast on CPU. |

## MCP servers (`.mcp.json`)

| Server | Job | Why |
|---|---|---|
| **videomaker** (this repo, `mcp_server/server.py`) | `new_project`, `plan_schema`, `write_plan`, `search_media`, `run_stage`, `make_video`, `preview_frame`, `probe_media`, `list_library`, `list_outputs` | Lets any MCP client — not just Claude Code in this folder — make a video by calling tools. Built on the official `mcp` Python SDK. |
| **@remotion/mcp** | Searches the Remotion documentation | When the AI extends the renderer (new scene types, transitions), it can look up the real API rather than guess. |
| **@playwright/mcp** | Drives a headless browser: screenshots, page recordings | Captures websites, dashboards and UI as visuals for explainers and product videos; screenshots go in `assets/generated/` and into a plan via `visual.file`. |
| **elevenlabs-mcp** (optional, paid, cloud) | Premium TTS, voice design, sound effects, music | For when local voices are not enough, and for sound effects nothing local generates well. Writes into `assets/generated/`. Needs `ELEVENLABS_API_KEY`; Claude Code asks before enabling it. |

## Recommended, not wired in

These are worth adding when the need arrives; each plugs in by writing files
into `assets/generated/` and referencing them with `visual.file`, so nothing
in the pipeline has to change.

| Tool | For |
|---|---|
| **ComfyUI** (GPL-3.0) | Local image and video generation (FLUX, SDXL, Wan, LTX-Video) through node workflows; has an HTTP API and community MCP servers. Needs a GPU. |
| **MusicGen / Stable Audio Open** | Generated music beds and sound effects, locally. |
| **Whisper / WhisperX** | Transcribing user-supplied footage to cut it by what is said. |
| **Real-ESRGAN** | Upscaling low-resolution stock or generated stills. |
| **Shotcut / Kdenlive / DaVinci Resolve** | Human finishing passes; `make` produces an MP4 and `.srt` they import directly. |
