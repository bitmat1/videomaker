.PHONY: help setup install new video plan assets voice build render still \
        finish demo studio mcp search check clean

# Always the project venv, never the system python (see docs/SETUP.md).
PY := .venv/bin/python
# The project to work on: a folder under projects/.
P ?= demo

help:
	@echo "Videomaker — videos on demand"
	@echo ""
	@echo "  make new PROMPT=\"a 30s explainer about tides\"   → projects/<slug>/brief.json"
	@echo "  make video P=<slug>   every stage after the plan → output/<slug>/"
	@echo "  make demo             offline end-to-end check (mock voice, drawn visuals)"
	@echo ""
	@echo "  Stages, in order. Each reads and writes files, so any one can be re-run:"
	@echo "    make plan P=…     brief → plan.json   (validates an AI-written plan)"
	@echo "    make assets P=…   plan → assets/clips, assets/photos, assets.json"
	@echo "    make voice P=…    narration → voice/*.wav, voice.json (word timings)"
	@echo "    make build P=…    → remotion/public/project.json + staged media"
	@echo "    make render       manifest → work/<slug>/render.mp4"
	@echo "    make finish       → output/<slug>/ master, thumbnail, .srt, credits"
	@echo ""
	@echo "  Faster loops:"
	@echo "    make still F=60   one frame to PNG, seconds not minutes"
	@echo "    make studio       Remotion preview; scrub the video by hand"
	@echo "    make search Q=\"ocean waves\" K=video   what the stock providers have"
	@echo ""
	@echo "    make setup        venv + Python deps (once)"
	@echo "    make install      npm install inside remotion/ (once)"
	@echo "    make mcp          run the MCP server on stdio (clients do this for you)"
	@echo "    make check        ruff + mypy + pytest + tsc"
	@echo "    make clean        scratch, staged media and renders (keeps output/)"

setup:
	python3 -m venv .venv
	$(PY) -m pip install -q --upgrade pip
	$(PY) -m pip install -q -e ".[dev,mcp]"
	@echo "Optional extras: pip install -e '.[tts,captions,fetch]' (docs/SETUP.md)"

install:
	cd remotion && npm install

new:
	$(PY) pipeline/plan.py --new "$(PROMPT)" $(if $(SLUG),--slug $(SLUG))

video: plan assets voice build render finish

plan:
	$(PY) pipeline/plan.py --project $(P)

assets:
	$(PY) pipeline/assets.py --project $(P)

voice:
	$(PY) pipeline/voice.py --project $(P)

build:
	$(PY) pipeline/build.py --project $(P)

render:
	$(PY) pipeline/render.py

F ?= 30
still:
	$(PY) pipeline/render.py --still $(F)

finish:
	$(PY) pipeline/finish.py

# Exercises every stage with no network, no TTS model and no API key.
demo:
	$(PY) pipeline/plan.py --project demo
	$(PY) pipeline/assets.py --project demo --offline
	$(PY) pipeline/voice.py --project demo --backend mock
	$(PY) pipeline/build.py --project demo
	$(PY) pipeline/render.py
	$(PY) pipeline/finish.py

studio:
	cd remotion && npx remotion studio

mcp:
	$(PY) mcp_server/server.py

Q ?= ocean waves
K ?= video
search:
	$(PY) pipeline/assets.py --search "$(Q)" --kind $(K)

check:
	$(PY) -m ruff check pipeline/ mcp_server/ tests/
	$(PY) -m mypy pipeline/ mcp_server/
	$(PY) -m pytest tests/ -q
	cd remotion && npx tsc --noEmit

clean:
	rm -rf work remotion/out remotion/public/media remotion/public/audio
	rm -f remotion/public/project.json
