# CLAUDE.md

Videos on demand. Someone asks for a video; the AI driving this repo writes a
plan; open-source tools find the footage, speak the narration, render the
film and hand back an MP4. Python prepares everything, Remotion draws it,
ffmpeg finishes it. Built on the same shape as `robot-reporter`.

To make a video, follow `.claude/skills/make-video/SKILL.md`. The plan format
is `docs/PLAN_SCHEMA.md`. What each tool is for is in `TOOLS.md`.

---

## Commands

```bash
make new PROMPT="…" [SLUG=…]   # → projects/<slug>/brief.json
make video P=<slug>            # every stage after the plan → output/<slug>/
make demo                      # offline end-to-end check, ~40s
```

Six stages, each reading and writing files, so any one can be re-run alone:

```bash
make plan P=…     # brief → plan.json            (validates an AI-written plan)
make assets P=…   # plan → assets/clips, assets/photos, projects/<slug>/assets.json
make voice P=…    # narration → projects/<slug>/voice/*.wav + voice.json
make build P=…    # → remotion/public/project.json + staged media and audio
make render       # → work/<slug>/render.mp4
make finish       # → output/<slug>/{<slug>.mp4, thumbnail.jpg, .srt, credits.txt}
```

Fast loops: `make still F=60` (one frame, seconds), `make studio` (scrub by
hand), `make search Q="…"` (what the stock sites have). Prefer these to a
full render while iterating.

`make check` runs ruff + mypy + pytest + tsc. Run it before committing.

---

## Layout

```
briefs/            Example briefs (checked in)
projects/<slug>/   One folder per video: brief, plan, assets, voice (gitignored
                   except projects/demo)
assets/            Shared media library, reused across videos (gitignored)
  clips/ photos/   downloaded, normalised, hashed by source URL
  generated/       AI-generated media from any tool
  audio/music/ audio/sfx/
output/<slug>/     Finished deliverables (gitignored)
work/              Scratch: renders, stills, raw downloads (gitignored)
pipeline/          Python stages. config.py holds every setting.
mcp_server/        The pipeline as MCP tools (registered in .mcp.json)
remotion/src/      Compositions. Video.tsx, scenes/, Captions.tsx
docs/              PLAN_SCHEMA.md, SETUP.md
```

---

## Architecture invariants

Carried over from robot-reporter, where each was learned the hard way.

1. **No model inference at render time.** LLM, TTS and alignment happen in
   Python and land on disk. Remotion only draws.
2. **No network at render time.** Media is downloaded by `assets.py` and
   staged into `remotion/public/` by `build.py`. A component that fetches a
   URL works in the studio and fails in a headless render.
3. **No blur, no CSS filters**, no large box-shadows. They make headless
   Chrome an order of magnitude slower. Fake glow with translucent shapes.
4. **Deterministic rendering.** No `Math.random()` or `Date.now()` in
   `remotion/src/`; use the seeded LCG in `CardScene.tsx`.
5. **Stages communicate through files, never through imports.** `common.py`,
   `config.py` and `manifest.py` are shared utilities, not stages. The MCP
   server runs stages as subprocesses.
6. **The manifest is the contract.** `remotion/src/types.ts` and
   `pipeline/manifest.py` describe the same structure; change both in one
   commit and bump `MANIFEST_VERSION`.
7. **A video always completes.** A failed search or download degrades the
   scene to a drawn card with a warning; it never sinks the request.
8. **Credit everything.** Every downloaded asset carries credit and licence
   through to `output/<slug>/credits.txt`.

---

## Conventions

- Python runs in `.venv/` (`make setup`). Never install into system Python.
- The pipeline core is standard library only. Heavier tools (Kokoro, Piper,
  faster-whisper, yt-dlp) are optional extras in `pyproject.toml`, imported
  lazily inside the backend that needs them.
- Type hints on public functions; ruff and mypy clean. Comments say *why*.
- TypeScript: `strict`, no `any`, components are pure functions of
  `(props, frame)`, inline styles only.
- Remotion packages are pinned to one exact version; they must all match.

## Gotchas

- `calculateMetadata` runs in the browser: `staticFile()` works, Node `fs`
  does not.
- Clips shorter than their scene are looped (`<Loop>`), so `build.py` records
  each clip's length in the manifest.
- `say` on some macOS builds will not write WAVE; `voice.py` goes via AIFF.
- Kokoro emits 24kHz; `voice.py` resamples everything to `SAMPLE_RATE`.
- Pin `num_ctx` on Ollama calls (see `config.OLLAMA_NUM_CTX`).
- In containers, set `REMOTION_BROWSER` to an installed Chromium headless
  shell instead of letting Remotion download one.
