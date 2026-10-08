"""Stage 1: brief → plan.

    projects/<slug>/brief.json  →  projects/<slug>/plan.json

The brief is what someone asked for. The plan is the shot list: scenes, each
with narration, an on-screen line and a visual to find. It is the creative
heart of the video and the one file worth an AI's full attention.

Backends:
  agent   the AI driving this repo (Claude Code, an MCP client) writes
          plan.json itself, following docs/PLAN_SCHEMA.md. This stage then
          only validates it. The normal path.
  ollama  a local model writes it, for unattended runs.
  mock    one card per sentence of the prompt. Offline and deterministic,
          for tests and for checking the plumbing.

Usage:
  python pipeline/plan.py --project my-video [--backend mock]
  python pipeline/plan.py --new "a 30 second explainer about tides" [--slug tides]
"""

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from common import StageError, read_json, slugify, write_json
from manifest import ManifestError, validate_plan


def new_brief(prompt: str, *, slug: str | None = None, duration_s: int = 30,
              fmt: str = config.DEFAULT_FORMAT, tone: str = "clear, warm") -> Path:
    slug = slug or slugify(prompt)
    brief = {"slug": slug, "prompt": prompt, "duration_s": duration_s,
             "format": fmt, "tone": tone}
    path = config.project_dir(slug) / "brief.json"
    write_json(path, brief)
    return path


# --- Backend: mock ---------------------------------------------------------


def plan_mock(brief: dict[str, Any]) -> dict[str, Any]:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", brief["prompt"])
                 if s.strip()]
    title = sentences[0].rstrip(".!?")[:60] if sentences else brief["slug"]
    scenes: list[dict[str, Any]] = [{
        "id": "s01", "narration": "", "onscreen": title,
        "visual": {"kind": "title"}, "motion": "none", "transition": "cut",
    }]
    for i, sentence in enumerate(sentences, start=2):
        scenes.append({
            "id": f"s{i:02d}", "narration": sentence,
            "onscreen": "", "visual": {"kind": "card"},
            "motion": "zoom-in", "transition": "fade",
        })
    return {"title": title, "format": brief.get("format", config.DEFAULT_FORMAT),
            "fps": config.DEFAULT_FPS, "scenes": scenes}


# --- Backend: ollama -------------------------------------------------------

SCHEMA_DOC = config.ROOT / "docs" / "PLAN_SCHEMA.md"


def plan_ollama(brief: dict[str, Any]) -> dict[str, Any]:
    words = int(brief.get("duration_s", 30) / 60 * config.WORDS_PER_MINUTE)
    prompt = (
        "You are a video producer. Write a plan for the video described below "
        "as a single JSON object following this schema exactly.\n\n"
        f"{SCHEMA_DOC.read_text()}\n\n"
        f"Brief: {brief['prompt']}\nTone: {brief.get('tone', '')}\n"
        f"Format: {brief.get('format', config.DEFAULT_FORMAT)}\n"
        f"Total narration: about {words} words. Use stock-footage search "
        "queries of 2–4 concrete, filmable words.\nReturn only JSON."
    )
    body = json.dumps({
        "model": config.OLLAMA_MODEL, "prompt": prompt, "stream": False,
        "format": "json", "options": {"num_ctx": config.OLLAMA_NUM_CTX},
    }).encode()
    req = urllib.request.Request(f"{config.OLLAMA_URL}/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            reply = json.loads(resp.read())["response"]
    except OSError as e:
        raise StageError(f"Ollama unreachable at {config.OLLAMA_URL}: {e}") from e
    plan: dict[str, Any] = json.loads(reply)
    return plan


BACKENDS = {"mock": plan_mock, "ollama": plan_ollama}


def run(slug: str, backend: str) -> Path:
    pdir = config.project_dir(slug)
    out = pdir / "plan.json"
    if backend == "agent":
        if not out.exists():
            raise StageError(
                f"{out.relative_to(config.ROOT)} not written yet. With the agent "
                "backend the AI writes it (docs/PLAN_SCHEMA.md); or pass "
                "--backend ollama / mock."
            )
        plan = read_json(out)
    else:
        plan = BACKENDS[backend](read_json(pdir / "brief.json"))
    write_json(out, validate_plan(plan))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", help="project slug under projects/")
    ap.add_argument("--new", metavar="PROMPT", help="create a brief from a prompt")
    ap.add_argument("--slug")
    ap.add_argument("--duration", type=int, default=30)
    ap.add_argument("--format", default=config.DEFAULT_FORMAT,
                    choices=sorted(config.FORMATS))
    ap.add_argument("--backend", default=config.PLAN_BACKEND,
                    choices=["agent", *BACKENDS])
    args = ap.parse_args()
    try:
        if args.new:
            path = new_brief(args.new, slug=args.slug, duration_s=args.duration,
                             fmt=args.format)
            print(f"→ {path.relative_to(config.ROOT)}")
            if args.backend == "agent":
                return 0
            args.project = path.parent.name
        if not args.project:
            ap.error("--project or --new is required")
        out = run(args.project, args.backend)
    except (StageError, ManifestError) as e:
        print(e, file=sys.stderr)
        return 1
    print(f"→ {out.relative_to(config.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
