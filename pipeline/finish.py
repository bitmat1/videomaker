"""Stage 6: render → deliverable.

    work/<slug>/render.mp4 + remotion/public/project.json
        →  output/<slug>/<slug>.mp4      loudness-normalised master
           output/<slug>/thumbnail.jpg
           output/<slug>/<slug>.srt      sidecar captions
           output/<slug>/credits.txt     every licensed asset, with its licence
           output/<slug>/plan.json       how it was made, for re-runs

The renderer mixes audio but does not know about loudness targets; this stage
brings the master to config.LOUDNESS_LUFS so it plays at the same level as
everything else on the platform it is posted to.

Usage:
  python pipeline/finish.py
"""

import argparse
import shutil
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from common import StageError, ffmpeg, probe, read_json


def _srt_time(frame: int, fps: int) -> str:
    ms = round(frame * 1000 / fps)
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def to_srt(captions: list[dict[str, Any]], fps: int) -> str:
    return "\n".join(
        f"{i}\n{_srt_time(c['startFrame'], fps)} --> {_srt_time(c['endFrame'], fps)}"
        f"\n{c['text']}\n"
        for i, c in enumerate(captions, start=1))


def run() -> Path:
    manifest = read_json(config.MANIFEST)
    slug, fps = manifest["slug"], manifest["fps"]
    render = config.WORK / slug / "render.mp4"
    if not render.exists():
        raise StageError(f"{render.relative_to(config.ROOT)} missing; run the render")
    out_dir = config.output_dir(slug)
    out_dir.mkdir(parents=True, exist_ok=True)
    master = out_dir / f"{slug}.mp4"

    has_audio = any(s["codec_type"] == "audio" for s in probe(render)["streams"])
    if has_audio:
        ffmpeg("-i", str(render), "-c:v", "copy",
               "-af", f"loudnorm=I={config.LOUDNESS_LUFS}:TP={config.TRUE_PEAK_DB}:LRA=11",
               "-ar", str(config.SAMPLE_RATE), "-c:a", "aac", "-b:a", "192k",
               "-movflags", "+faststart", str(master))
    else:
        shutil.copy2(render, master)

    thumb_s = min(1.0, manifest["durationInFrames"] / fps / 2)
    ffmpeg("-ss", f"{thumb_s:.2f}", "-i", str(master), "-frames:v", "1",
           "-q:v", "3", str(out_dir / "thumbnail.jpg"))
    if manifest["captions"]:
        (out_dir / f"{slug}.srt").write_text(to_srt(manifest["captions"], fps))
    credits = manifest["credits"] or ["All visuals drawn; no third-party media."]
    (out_dir / "credits.txt").write_text("\n".join(credits) + "\n")
    plan = config.project_dir(slug) / "plan.json"
    if plan.exists():
        shutil.copy2(plan, out_dir / "plan.json")
    return master


def main() -> int:
    argparse.ArgumentParser(description=__doc__,
                            formatter_class=argparse.RawDescriptionHelpFormatter
                            ).parse_args()
    try:
        out = run()
    except StageError as e:
        print(e, file=sys.stderr)
        return 1
    print(f"→ {out.relative_to(config.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
