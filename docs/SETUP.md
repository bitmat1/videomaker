# Setup

Everything beyond the first block is optional; the pipeline degrades to
drawn cards and a synthetic voice without it.

## 1. Required

| Need | macOS | Debian/Ubuntu |
|---|---|---|
| Python 3.11+ | `brew install python` | `apt install python3 python3-venv` |
| Node 18+ | `brew install node` | `apt install nodejs npm` |
| ffmpeg | `brew install ffmpeg` | `apt install ffmpeg` |

```bash
make setup      # .venv with dev tools and the MCP SDK
make install    # Remotion
make demo       # prove it works: output/demo/demo.mp4
```

The first render downloads Remotion's headless Chrome (once). In a container
with Chromium already installed, point at it instead:
`export REMOTION_BROWSER=/path/to/chrome-headless-shell`.

## 2. Better voices

```bash
.venv/bin/pip install -e ".[tts]"
export VM_TTS_BACKEND=kokoro          # or set plan.voice.backend
```

Kokoro downloads its weights (~330MB) on first use. For Piper, download a
voice (`.onnx` + `.onnx.json`) from https://huggingface.co/rhasspy/piper-voices
and `export PIPER_MODEL=/path/to/voice.onnx`.

## 3. Caption alignment

```bash
.venv/bin/pip install -e ".[captions]"
```

With faster-whisper installed, captions follow the words as spoken; without
it they are spread by word length, which is close but drifts on long scenes.

## 4. Stock footage

Openverse and Wikimedia Commons work with no setup. For far more video, get
free keys and put them in your shell or `.env` (see `.env.example`):

- Pexels: https://www.pexels.com/api/
- Pixabay: https://pixabay.com/api/docs/

`make search Q="city at night"` shows what each provider returns.

For page URLs (`visual.url`) and shot splitting: `.venv/bin/pip install -e ".[fetch]"`.

## 5. Unattended planning (optional)

For runs with no AI agent present: install Ollama, `ollama pull llama3.1:8b`,
then `make new PROMPT="…"` followed by
`.venv/bin/python pipeline/plan.py --project <slug> --backend ollama`.

## 6. MCP servers

`.mcp.json` registers four servers. Claude Code asks before starting each
project server; approve the ones you want.

- `videomaker` — needs `make setup` (it runs from `.venv`).
- `remotion-docs`, `playwright` — fetched by `npx` on first use.
- `elevenlabs` — needs `uv` (`brew install uv`) and `ELEVENLABS_API_KEY`.
  Paid, cloud. Skip it to stay fully local.

For Claude Desktop, copy the `videomaker` entry into its config with absolute
paths for `command` and `args`.
