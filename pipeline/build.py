"""Stage 4: plan + assets + voice → the render manifest.

    projects/<slug>/{plan,assets,voice}.json
        →  remotion/public/project.json
           remotion/public/media/*        (only what this video uses)
           remotion/public/audio/narration.wav, music.*

This is where time is decided. Each scene lasts as long as its narration plus
a short tail (or plan.scene.seconds if given); a scene with nothing to say
gets long enough to read. The narration is laid into one WAV with silence
between scenes so the renderer plays a single track in sync.

remotion/public/ is rebuilt from scratch every time: the renderer can only
see what this stage put there, which is what keeps renders repeatable and
offline.

Usage:
  python pipeline/build.py --project my-video
"""

import argparse
import array
import re
import shutil
import sys
import wave
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from common import StageError, duration_s, read_json, write_json
from manifest import ManifestError, build_manifest, validate_manifest

DEFAULT_STYLE = {
    "background": "#0e1116",
    "text": "#ffffff",
    "accent": "#ffb000",
    "font": "Inter, Helvetica Neue, Arial, sans-serif",
    "captions": True,
}


def scene_seconds(scene: dict[str, Any], voice: dict[str, Any] | None) -> float:
    if scene.get("seconds"):
        return float(scene["seconds"])
    if voice:
        return max(config.MIN_SCENE_S, voice["duration_s"] + config.SCENE_TAIL_S)
    return config.SILENT_SCENE_S


def caption_chunks(words: list[dict[str, Any]], offset: float,
                   fps: int) -> list[dict[str, Any]]:
    """Group words into short lines, breaking early at punctuation so a line
    reads as a phrase rather than an arbitrary run of words."""
    chunks, current = [], []
    for w in words:
        current.append(w)
        if len(current) >= config.CAPTION_MAX_WORDS or re.search(r"[.,!?;:]$", w["text"]):
            chunks.append(current)
            current = []
    if current:
        chunks.append(current)
    return [{
        "startFrame": round((offset + c[0]["start"]) * fps),
        "endFrame": max(round((offset + c[0]["start"]) * fps) + 1,
                        round((offset + c[-1]["end"]) * fps)),
        "text": " ".join(w["text"] for w in c),
    } for c in chunks]


def lay_narration(placements: list[tuple[float, Path]], total_s: float,
                  out: Path) -> None:
    rate = config.SAMPLE_RATE
    track = array.array("h", bytes(2 * int(total_s * rate)))
    for start, path in placements:
        with wave.open(str(path), "rb") as w:
            if w.getframerate() != rate or w.getnchannels() != 1:
                raise StageError(f"{path}: expected mono {rate}Hz")
            clip = array.array("h")
            clip.frombytes(w.readframes(w.getnframes()))
        at = int(start * rate)
        clip = clip[: len(track) - at]
        track[at: at + len(clip)] = clip
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(track.tobytes())


def stage_media(src: Path) -> str:
    dst = config.PUBLIC_MEDIA / src.name
    if not dst.exists():
        shutil.copy2(src, dst)
    return f"media/{src.name}"


def reset_public() -> None:
    for d in (config.PUBLIC_MEDIA, config.PUBLIC_AUDIO):
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True)
    config.MANIFEST.unlink(missing_ok=True)


def run(slug: str) -> Path:
    pdir = config.project_dir(slug)
    plan = read_json(pdir / "plan.json")
    assets = read_json(pdir / "assets.json")
    voice_path = pdir / "voice.json"
    voices = read_json(voice_path)["scenes"] if voice_path.exists() else {}

    fps = plan["fps"]
    width, height = config.FORMATS[plan["format"]]
    reset_public()

    scenes, captions, credits, placements = [], [], [], []
    cursor = 0
    for scene in plan["scenes"]:
        sid = scene["id"]
        voice = voices.get(sid)
        start_s = cursor / fps
        frames = max(1, round(scene_seconds(scene, voice) * fps))
        asset = assets.get(sid, {"kind": "card"})
        entry: dict[str, Any] = {
            "id": sid,
            "kind": "title" if asset["kind"] == "title" else
                    "media" if asset["kind"] in {"video", "photo"} else "card",
            "startFrame": cursor, "endFrame": cursor + frames,
            "text": scene.get("onscreen", ""),
            "motion": scene["motion"], "transition": scene["transition"],
        }
        if entry["kind"] == "media":
            src = config.ROOT / asset["path"]
            media: dict[str, Any] = {"kind": asset["kind"], "src": stage_media(src)}
            if asset["kind"] == "video":
                media["durationInFrames"] = max(1, int(duration_s(src) * fps))
            entry["media"] = media
            if asset.get("credit"):
                entry["credit"] = asset["credit"]
                credits.append(" — ".join(x for x in (
                    asset["credit"], asset.get("license", ""), asset.get("page", "")) if x))
        if voice:
            placements.append((start_s, config.ROOT / voice["path"]))
            captions += caption_chunks(voice["words"], start_s, fps)
        scenes.append(entry)
        cursor += frames

    total_s = cursor / fps
    audio: dict[str, Any] = {"narration": None, "music": None,
                             "musicVolume": plan["music"].get("volume", config.MUSIC_VOLUME)}
    if placements:
        lay_narration(placements, total_s, config.PUBLIC_AUDIO / "narration.wav")
        audio["narration"] = "audio/narration.wav"
    if plan["music"].get("file"):
        music = config.ROOT / plan["music"]["file"]
        if not music.exists():
            raise StageError(f"plan.music.file {plan['music']['file']} does not exist")
        shutil.copy2(music, config.PUBLIC_AUDIO / f"music{music.suffix}")
        audio["music"] = f"audio/music{music.suffix}"
        if plan["music"].get("credit"):
            credits.append(f"Music: {plan['music']['credit']}")

    for c in captions:
        c["endFrame"] = min(c["endFrame"], cursor)
        c["startFrame"] = min(c["startFrame"], c["endFrame"] - 1)

    manifest = build_manifest(
        slug=slug, title=plan["title"], fps=fps, width=width, height=height,
        duration_in_frames=cursor, scenes=scenes, captions=captions, audio=audio,
        style={**DEFAULT_STYLE, **plan.get("style", {})}, credits=credits,
    )
    validate_manifest(manifest)
    write_json(config.MANIFEST, manifest)
    print(f"  {len(scenes)} scenes, {total_s:.1f}s, {width}x{height}@{fps}")
    return config.MANIFEST


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    args = ap.parse_args()
    try:
        out = run(args.project)
    except (StageError, ManifestError) as e:
        print(e, file=sys.stderr)
        return 1
    print(f"→ {out.relative_to(config.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
