"""Videomaker MCP server: the pipeline as tools an AI model can call.

Any MCP client (Claude Code, Claude Desktop, others) can then make a video on
request: create a brief, write the plan, search and preview stock media, run
the stages and hand back the finished file.

It drives the stages as subprocesses, exactly as `make` does, so the rule
that stages talk only through files holds here too. Registered in .mcp.json;
run by hand with:

  .venv/bin/python mcp_server/server.py
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

from mcp.server.mcpserver import MCPServer

import config
from common import probe as ffprobe
from common import slugify
from manifest import ManifestError, validate_plan

PY = sys.executable
STAGES = ["plan", "assets", "voice", "build", "render", "finish"]

server = MCPServer(
    "videomaker",
    instructions=(
        "Make videos on demand. Typical flow: new_project → read plan_schema → "
        "write_plan → make_video. Use search_media to check footage exists "
        "before committing a scene to it. Finished files land in output/<slug>/."
    ),
)


def _stage(name: str, slug: str, *extra: str) -> str:
    args = [PY, str(ROOT / "pipeline" / f"{name}.py")]
    if name in {"plan", "assets", "voice", "build"}:
        args += ["--project", slug]
    proc = subprocess.run([*args, *extra], cwd=ROOT, capture_output=True, text=True,
                          check=False)
    log = (proc.stdout + proc.stderr).strip()
    if proc.returncode:
        raise RuntimeError(f"{name} failed:\n{log[-3000:]}")
    return log[-3000:]


@server.tool()
def new_project(prompt: str, slug: str = "", duration_s: int = 30,
                format: str = "landscape", tone: str = "clear, warm") -> str:
    """Create projects/<slug>/brief.json from a request. format is landscape,
    portrait or square. Returns the slug."""
    if format not in config.FORMATS:
        raise ValueError(f"format must be one of {sorted(config.FORMATS)}")
    slug = slugify(slug or prompt)
    pdir = config.project_dir(slug)
    pdir.mkdir(parents=True, exist_ok=True)
    (pdir / "brief.json").write_text(json.dumps({
        "slug": slug, "prompt": prompt, "duration_s": duration_s,
        "format": format, "tone": tone}, indent=2) + "\n")
    return slug


@server.tool()
def plan_schema() -> str:
    """The plan.json format, with an example. Read before write_plan."""
    return (ROOT / "docs" / "PLAN_SCHEMA.md").read_text()


@server.tool()
def write_plan(slug: str, plan: dict[str, Any]) -> str:
    """Validate a plan and save it as projects/<slug>/plan.json."""
    try:
        normalised = validate_plan(plan)
    except ManifestError as e:
        return str(e)
    path = config.project_dir(slug) / "plan.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(normalised, indent=2) + "\n")
    return f"saved {path.relative_to(ROOT)} ({len(normalised['scenes'])} scenes)"


@server.tool()
def read_project(slug: str) -> dict[str, Any]:
    """Every JSON file in a project folder: brief, plan, assets, voice."""
    pdir = config.project_dir(slug)
    return {p.stem: json.loads(p.read_text()) for p in sorted(pdir.glob("*.json"))}


@server.tool()
def search_media(query: str, kind: str = "video", limit: int = 8) -> list[dict[str, str]]:
    """Search stock providers for licensed footage ("video") or stills
    ("photo") without downloading. Use 2–4 concrete, filmable words."""
    out = subprocess.run([PY, str(ROOT / "pipeline" / "assets.py"), "--search",
                          query, "--kind", kind], cwd=ROOT, capture_output=True,
                         text=True, check=True).stdout
    hits: list[dict[str, str]] = json.loads(out)
    return hits[:limit]


@server.tool()
def run_stage(slug: str, stage: str, options: list[str] | None = None) -> str:
    """Run one stage: plan, assets, voice, build, render or finish. options
    are extra CLI flags, e.g. ["--backend", "mock"] or ["--offline"]."""
    if stage not in STAGES:
        raise ValueError(f"stage must be one of {STAGES}")
    return _stage(stage, slug, *(options or []))


@server.tool()
def make_video(slug: str, tts: str = "", offline: bool = False) -> dict[str, Any]:
    """Run every stage after the plan and return the finished files. tts
    overrides the voice backend (kokoro, piper, say, mock)."""
    _stage("plan", slug)
    _stage("assets", slug, *(["--offline"] if offline else []))
    _stage("voice", slug, *(["--backend", tts] if tts else []))
    _stage("build", slug)
    _stage("render", slug)
    _stage("finish", slug)
    return list_outputs(slug)


@server.tool()
def preview_frame(slug: str, frame: int = 30) -> str:
    """Render a single frame to PNG (seconds, not minutes) to check a look
    before the full render. Builds the project first."""
    _stage("build", slug)
    _stage("render", slug, "--still", str(frame))
    return str(config.WORK / slug / f"frame-{frame}.png")


@server.tool()
def probe_media(path: str) -> dict[str, Any]:
    """ffprobe a media file: duration, codecs, size, frame rate."""
    target = (ROOT / path).resolve()
    if not target.is_relative_to(ROOT):
        raise ValueError("path must be inside the repository")
    return ffprobe(target)


@server.tool()
def list_library() -> dict[str, list[str]]:
    """Media already on disk, reusable in any plan via visual.file."""
    dirs = {"clips": config.CLIPS, "photos": config.PHOTOS,
            "generated": config.GENERATED, "music": config.MUSIC, "sfx": config.SFX}
    return {k: sorted(str(p.relative_to(ROOT)) for p in d.iterdir()
                      if p.is_file() and p.name != ".gitkeep")
            for k, d in dirs.items() if d.exists()}


@server.tool()
def list_outputs(slug: str = "") -> dict[str, Any]:
    """Finished videos in output/, or the files for one slug."""
    if slug:
        d = config.output_dir(slug)
        return {"slug": slug, "files": sorted(str(p.relative_to(ROOT))
                                              for p in d.glob("*"))}
    return {"videos": sorted(str(p.relative_to(ROOT))
                             for p in config.OUTPUT.glob("*/*.mp4"))}


if __name__ == "__main__":
    server.run("stdio")
