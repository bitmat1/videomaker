"""Helpers every stage uses: JSON on disk, ffmpeg, slugs.

Shared utilities, not a stage, so importing this does not break the rule that
stages talk only through files.
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config


class StageError(RuntimeError):
    pass


def read_json(path: Path) -> Any:
    if not path.exists():
        raise StageError(f"{path.relative_to(config.ROOT)} is missing; run the "
                         "previous stage first")
    return json.loads(path.read_text())


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write then rename, so a crash never leaves a half-written contract file
    # for the next stage to choke on.
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(path)


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:48] or "video"


def require(tool: str) -> str:
    path = shutil.which(tool)
    if not path:
        raise StageError(f"`{tool}` not found on PATH (see docs/SETUP.md)")
    return path


def ffmpeg(*args: str) -> None:
    require("ffmpeg")
    proc = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                           *args], capture_output=True, text=True,
                          check=False)
    if proc.returncode:
        raise StageError(f"ffmpeg failed: {proc.stderr.strip()[-600:]}")


def probe(path: Path) -> dict[str, Any]:
    require("ffprobe")
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format",
         "-show_streams", str(path)],
        capture_output=True, text=True, check=False,
    )
    if proc.returncode:
        raise StageError(f"ffprobe could not read {path}: {proc.stderr.strip()}")
    result: dict[str, Any] = json.loads(proc.stdout)
    return result


def duration_s(path: Path) -> float:
    return float(probe(path)["format"].get("duration", 0.0))


def rel(path: Path) -> str:
    return str(path.relative_to(config.ROOT))
