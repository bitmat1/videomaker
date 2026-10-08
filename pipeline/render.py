"""Stage 5: manifest → pixels.

    remotion/public/project.json  →  work/<slug>/render.mp4

A thin wrapper over `npx remotion render`, so the Makefile, the MCP server and
a human all invoke the renderer the same way. The slug is read from the
manifest, so this renders whatever build.py last staged.

Usage:
  python pipeline/render.py [--still FRAME] [--composition Video]
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from common import StageError, read_json, require


def run(still: int | None = None, composition: str = "Video") -> Path:
    require("npx")
    if not (config.REMOTION / "node_modules").exists():
        raise StageError("Remotion is not installed: run `make install`")
    slug = read_json(config.MANIFEST)["slug"]
    out_dir = config.WORK / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    if still is not None:
        out = out_dir / f"frame-{still}.png"
        cmd = ["npx", "remotion", "still", composition, str(out), f"--frame={still}"]
    else:
        out = out_dir / "render.mp4"
        cmd = ["npx", "remotion", "render", composition, str(out)]
    subprocess.run(cmd, cwd=config.REMOTION, check=True, env=os.environ)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--still", type=int, metavar="FRAME",
                    help="render one frame to PNG instead of the video")
    ap.add_argument("--composition", default="Video")
    args = ap.parse_args()
    try:
        out = run(args.still, args.composition)
    except (StageError, subprocess.CalledProcessError) as e:
        print(e, file=sys.stderr)
        return 1
    print(f"→ {out.relative_to(config.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
