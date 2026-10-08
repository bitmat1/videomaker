"""Manifest v1: the contract between Python and Remotion.

remotion/src/types.ts describes the same structure; change one and you must
change the other in the same commit, and bump MANIFEST_VERSION on any
breaking change. The renderer checks the version so a stale build fails
loudly instead of drawing nonsense.

The plan schema lives here too, because the plan is the other contract: the
one the AI writes. validate_plan() is what turns a hand-written or
model-written plan into something the later stages can trust.
"""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config

MANIFEST_VERSION = 1

SCENE_KINDS = {"title", "media", "card"}
VISUAL_KINDS = {"video", "photo", "card", "title"}
MOTIONS = {"none", "zoom-in", "zoom-out", "pan-left", "pan-right"}
TRANSITIONS = {"cut", "fade"}


class ManifestError(ValueError):
    pass


# --- Plan ------------------------------------------------------------------


def validate_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Check a plan and fill in defaults. Returns the normalised plan."""
    errors: list[str] = []
    if not isinstance(plan.get("title"), str) or not plan["title"].strip():
        errors.append("plan.title must be a non-empty string")
    fmt = plan.setdefault("format", config.DEFAULT_FORMAT)
    if fmt not in config.FORMATS:
        errors.append(f"plan.format must be one of {sorted(config.FORMATS)}")
    fps = plan.setdefault("fps", config.DEFAULT_FPS)
    if not isinstance(fps, int) or not 12 <= fps <= 60:
        errors.append("plan.fps must be an integer 12–60")
    plan.setdefault("style", {})
    plan.setdefault("voice", {})
    plan.setdefault("music", {})

    scenes = plan.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        errors.append("plan.scenes must be a non-empty list")
        scenes = []
    for i, scene in enumerate(scenes):
        where = f"scenes[{i}]"
        if not isinstance(scene, dict):
            errors.append(f"{where} must be an object")
            continue
        scene.setdefault("id", f"s{i + 1:02d}")
        scene.setdefault("narration", "")
        scene.setdefault("onscreen", "")
        scene.setdefault("motion", "zoom-in")
        scene.setdefault("transition", "fade" if i else "cut")
        visual = scene.setdefault("visual", {"kind": "card"})
        if visual.get("kind") not in VISUAL_KINDS:
            errors.append(f"{where}.visual.kind must be one of {sorted(VISUAL_KINDS)}")
        if visual.get("kind") in {"video", "photo"} and not (
            visual.get("query") or visual.get("url") or visual.get("file")
        ):
            errors.append(f"{where}.visual needs a query, url or file")
        if scene["motion"] not in MOTIONS:
            errors.append(f"{where}.motion must be one of {sorted(MOTIONS)}")
        if scene["transition"] not in TRANSITIONS:
            errors.append(f"{where}.transition must be one of {sorted(TRANSITIONS)}")
        if not scene["narration"] and not scene["onscreen"] and visual.get(
            "kind"
        ) in {"card", "title"}:
            errors.append(f"{where}: a card with no narration and no text is empty")
    ids = [s.get("id") for s in scenes if isinstance(s, dict)]
    if len(ids) != len(set(ids)):
        errors.append("scene ids must be unique")
    if errors:
        raise ManifestError("invalid plan:\n  " + "\n  ".join(errors))
    return plan


# --- Manifest --------------------------------------------------------------


def build_manifest(
    *,
    slug: str,
    title: str,
    fps: int,
    width: int,
    height: int,
    duration_in_frames: int,
    scenes: list[dict[str, Any]],
    captions: list[dict[str, Any]],
    audio: dict[str, Any],
    style: dict[str, Any],
    credits: list[str],
) -> dict[str, Any]:
    return {
        "manifestVersion": MANIFEST_VERSION,
        "slug": slug,
        "title": title,
        "fps": fps,
        "width": width,
        "height": height,
        "durationInFrames": duration_in_frames,
        "scenes": scenes,
        "captions": captions,
        "audio": audio,
        "style": style,
        "credits": credits,
    }


def validate_manifest(m: dict[str, Any], public: Path = config.PUBLIC) -> None:
    errors: list[str] = []
    if m.get("manifestVersion") != MANIFEST_VERSION:
        errors.append(f"manifestVersion must be {MANIFEST_VERSION}")
    total = m.get("durationInFrames", 0)
    if total <= 0:
        errors.append("durationInFrames must be positive")
    cursor = 0
    for i, s in enumerate(m.get("scenes", [])):
        if s["kind"] not in SCENE_KINDS:
            errors.append(f"scenes[{i}].kind {s['kind']!r} unknown")
        if s["startFrame"] != cursor:
            errors.append(f"scenes[{i}] starts at {s['startFrame']}, expected {cursor}")
        if s["endFrame"] <= s["startFrame"]:
            errors.append(f"scenes[{i}] has no duration")
        cursor = s["endFrame"]
        media = s.get("media")
        if media and not (public / media["src"]).exists():
            errors.append(f"scenes[{i}].media.src {media['src']} missing from public/")
    if cursor != total:
        errors.append(f"scenes end at {cursor}, durationInFrames is {total}")
    for key in ("narration", "music"):
        src = m.get("audio", {}).get(key)
        if src and not (public / src).exists():
            errors.append(f"audio.{key} {src} missing from public/")
    for i, c in enumerate(m.get("captions", [])):
        if not 0 <= c["startFrame"] < c["endFrame"] <= total:
            errors.append(f"captions[{i}] out of range")
    if errors:
        raise ManifestError("invalid manifest:\n  " + "\n  ".join(errors))
