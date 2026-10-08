"""Stage 2: plan → media on disk.

    projects/<slug>/plan.json  →  projects/<slug>/assets.json
                                  assets/clips/*.mp4, assets/photos/*

Each scene's visual is resolved one of four ways:

  file    a path already on disk (your own footage, assets/generated/ output)
  url     a direct media link, or a page yt-dlp understands
  query   searched across the providers in config.MEDIA_PROVIDERS
  card    drawn by the renderer; nothing to fetch

Downloads land in the shared library under assets/, named by a hash of their
source URL, so a second video that wants "ocean waves" reuses the clip rather
than fetching it again. Clips are normalised once on the way in (H.264,
muted, bounded length) so the renderer never meets a codec Chrome cannot
play.

Every hit keeps its credit and licence; finish.py writes them next to the
video. If nothing licensed turns up, the scene degrades to a card rather than
failing the whole video.

Usage:
  python pipeline/assets.py --project my-video [--offline]
  python pipeline/assets.py --search "ocean waves" --kind video
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from common import StageError, ffmpeg, read_json, rel, require, write_json

Hit = dict[str, str]
VIDEO_EXT = {".mp4", ".mov", ".webm", ".mkv", ".m4v"}
PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


# --- HTTP ------------------------------------------------------------------


def _get(url: str, headers: dict[str, str] | None = None,
         limit: int | None = None) -> bytes:
    req = urllib.request.Request(
        url, headers={"User-Agent": config.USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(req, timeout=config.FETCH_TIMEOUT_S) as resp:
        length = int(resp.headers.get("Content-Length") or 0)
        if limit and length > limit:
            raise StageError(f"{url} is {length / 1e6:.0f}MB, over the limit")
        data: bytes = resp.read(limit + 1 if limit else -1)
    if limit and len(data) > limit:
        raise StageError(f"{url} exceeds {limit / 1e6:.0f}MB")
    return data


def _json(url: str, headers: dict[str, str] | None = None) -> Any:
    return json.loads(_get(url, headers))


def _strip_html(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text or "")).strip()


# --- Providers -------------------------------------------------------------
# Each returns candidate hits, best first, for one kind ("video" | "photo").


def pexels(query: str, kind: str) -> list[Hit]:
    if not config.PEXELS_API_KEY:
        return []
    auth = {"Authorization": config.PEXELS_API_KEY}
    q = urllib.parse.quote(query)
    if kind == "video":
        data = _json(f"https://api.pexels.com/videos/search?query={q}&per_page=8", auth)
        hits = []
        for v in data.get("videos", []):
            files = [f for f in v.get("video_files", [])
                     if f.get("file_type") == "video/mp4" and (f.get("height") or 0) <= 1080]
            if not files:
                continue
            best = max(files, key=lambda f: f.get("height") or 0)
            hits.append({"url": best["link"], "credit": f"{v['user']['name']} / Pexels",
                         "license": "Pexels License", "page": v["url"]})
        return hits
    data = _json(f"https://api.pexels.com/v1/search?query={q}&per_page=8", auth)
    return [{"url": p["src"]["large2x"], "credit": f"{p['photographer']} / Pexels",
             "license": "Pexels License", "page": p["url"]}
            for p in data.get("photos", [])]


def pixabay(query: str, kind: str) -> list[Hit]:
    if not config.PIXABAY_API_KEY:
        return []
    q = urllib.parse.quote(query)
    key = config.PIXABAY_API_KEY
    if kind == "video":
        data = _json(f"https://pixabay.com/api/videos/?key={key}&q={q}&per_page=8")
        return [{"url": (h["videos"].get("large") or h["videos"]["medium"])["url"],
                 "credit": f"{h['user']} / Pixabay", "license": "Pixabay Content License",
                 "page": h["pageURL"]}
                for h in data.get("hits", []) if h.get("videos")]
    data = _json(f"https://pixabay.com/api/?key={key}&q={q}&image_type=photo&per_page=8")
    return [{"url": h["largeImageURL"], "credit": f"{h['user']} / Pixabay",
             "license": "Pixabay Content License", "page": h["pageURL"]}
            for h in data.get("hits", [])]


def openverse(query: str, kind: str) -> list[Hit]:
    if kind != "photo":
        return []
    q = urllib.parse.quote(query)
    data = _json("https://api.openverse.org/v1/images/?"
                 f"q={q}&license_type=commercial,modification&page_size=8")
    hits = []
    for r in data.get("results", []):
        lic = f"CC {r.get('license', '').upper()} {r.get('license_version', '')}".strip()
        if r.get("license") in {"cc0", "pdm"}:
            lic = "Public domain"
        hits.append({"url": r["url"], "credit": r.get("creator") or "Unknown",
                     "license": lic, "page": r.get("foreign_landing_url", "")})
    return hits


def commons(query: str, kind: str) -> list[Hit]:
    filetype = "video" if kind == "video" else "bitmap"
    params = urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search",
        "gsrnamespace": 6, "gsrlimit": 8, "gsrsearch": f"{query} filetype:{filetype}",
        "prop": "imageinfo", "iiprop": "url|extmetadata|mime|size",
        "iiurlwidth": 1920,
    })
    data = _json(f"https://commons.wikimedia.org/w/api.php?{params}")
    pages = sorted(data.get("query", {}).get("pages", {}).values(),
                   key=lambda p: p.get("index", 0))
    hits = []
    for p in pages:
        info = (p.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {})
        url = info.get("url") if kind == "video" else info.get("thumburl")
        if kind == "video" and info.get("size", 0) > config.VIDEO_MAX_BYTES:
            continue
        if not url:
            continue
        hits.append({
            "url": url,
            "credit": _strip_html(meta.get("Artist", {}).get("value", "")) or "Unknown",
            "license": _strip_html(meta.get("LicenseShortName", {}).get("value", "")),
            "page": info.get("descriptionurl", ""),
        })
    return hits


PROVIDERS: dict[str, Callable[[str, str], list[Hit]]] = {
    "pexels": pexels, "pixabay": pixabay, "openverse": openverse, "commons": commons,
}


def search(query: str, kind: str, providers: list[str] | None = None) -> list[Hit]:
    """All candidates across providers, in provider order. Failures are skipped:
    one provider being down should not sink the video."""
    hits: list[Hit] = []
    for name in providers or config.MEDIA_PROVIDERS:
        try:
            found = PROVIDERS[name](query, kind)
        except (OSError, StageError, ValueError, KeyError) as e:
            print(f"  {name}: {e}", file=sys.stderr)
            continue
        hits.extend({**h, "provider": name, "kind": kind} for h in found)
    return hits


# --- Download and normalise -----------------------------------------------


def _cache_name(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()[:16]


def normalise_clip(src: Path, dst: Path) -> None:
    """H.264, muted, bounded, at most 1920 on the long edge. The renderer
    letterboxes or crops with objectFit, so aspect is kept here."""
    ffmpeg("-i", str(src), "-t", str(config.CLIP_MAX_SECONDS), "-an",
           "-vf", "scale='if(gt(iw,ih),min(1920,iw),-2)':'if(gt(iw,ih),-2,min(1920,ih))'",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(dst))


def download(hit: Hit) -> Path:
    name = _cache_name(hit["url"])
    if hit["kind"] == "video":
        dst = config.CLIPS / f"{name}.mp4"
        if dst.exists():
            return dst
        raw = config.WORK / "downloads" / f"{name}.raw"
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_bytes(_get(hit["url"], limit=config.VIDEO_MAX_BYTES))
        normalise_clip(raw, dst)
        raw.unlink()
        return dst
    ext = Path(urllib.parse.urlparse(hit["url"]).path).suffix.lower()
    dst = config.PHOTOS / f"{name}{ext if ext in PHOTO_EXT else '.jpg'}"
    if not dst.exists():
        dst.write_bytes(_get(hit["url"], limit=config.PHOTO_MAX_BYTES))
    return dst


def fetch_url(url: str) -> tuple[Path, str]:
    """A direct media link, or failing that a page yt-dlp can read."""
    ext = Path(urllib.parse.urlparse(url).path).suffix.lower()
    if ext in PHOTO_EXT or ext in VIDEO_EXT:
        kind = "video" if ext in VIDEO_EXT else "photo"
        return download({"url": url, "kind": kind}), kind
    require("yt-dlp")
    name = _cache_name(url)
    dst = config.CLIPS / f"{name}.mp4"
    if not dst.exists():
        raw = config.WORK / "downloads" / f"{name}.%(ext)s"
        raw.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["yt-dlp", "--no-playlist", "-q", "-f",
                        "bv*[height<=1080]+ba/b[height<=1080]/b",
                        "--max-filesize", str(config.VIDEO_MAX_BYTES), "-o", str(raw), url],
                       check=True)
        got = next(raw.parent.glob(f"{name}.*"))
        normalise_clip(got, dst)
        got.unlink()
    return dst, "video"


# --- Stage -----------------------------------------------------------------


def resolve(visual: dict[str, Any], used: set[str], offline: bool) -> dict[str, Any]:
    kind = visual.get("kind", "card")
    if kind in {"card", "title"}:
        return {"kind": kind}
    if visual.get("file"):
        path = (config.ROOT / visual["file"]).resolve()
        if not path.exists():
            raise StageError(f"visual.file {visual['file']} does not exist")
        kind = "video" if path.suffix.lower() in VIDEO_EXT else "photo"
        return {"kind": kind, "path": rel(path), "credit": visual.get("credit", ""),
                "license": visual.get("license", ""), "provider": "local"}
    if offline:
        return {"kind": "card", "fallback": True}
    if visual.get("url"):
        path, kind = fetch_url(visual["url"])
        return {"kind": kind, "path": rel(path), "credit": visual.get("credit", ""),
                "license": visual.get("license", ""), "page": visual["url"],
                "provider": "url"}
    # Prefer the asked-for kind, but a good photo beats a card.
    for want in [kind] + (["photo"] if kind == "video" else []):
        for hit in search(visual["query"], want):
            if hit["url"] in used:
                continue
            try:
                path = download(hit)
            except (OSError, StageError) as e:
                print(f"  skip {hit['url'][:80]}: {e}", file=sys.stderr)
                continue
            used.add(hit["url"])
            return {"kind": want, "path": rel(path), "credit": hit["credit"],
                    "license": hit["license"], "page": hit.get("page", ""),
                    "provider": hit["provider"]}
    print(f"  nothing licensed for {visual['query']!r}; using a card", file=sys.stderr)
    return {"kind": "card", "fallback": True}


def run(slug: str, offline: bool = False) -> Path:
    config.ensure_tls_certs()
    for d in (config.CLIPS, config.PHOTOS):
        d.mkdir(parents=True, exist_ok=True)
    pdir = config.project_dir(slug)
    plan = read_json(pdir / "plan.json")
    used: set[str] = set()
    resolved = {}
    for scene in plan["scenes"]:
        resolved[scene["id"]] = resolve(scene["visual"], used, offline)
        print(f"  {scene['id']}: {resolved[scene['id']]['kind']}"
              f" {resolved[scene['id']].get('path', '')}")
    out = pdir / "assets.json"
    write_json(out, resolved)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project")
    ap.add_argument("--offline", action="store_true",
                    help="no network: every searched visual becomes a card")
    ap.add_argument("--search", metavar="QUERY", help="list candidates and exit")
    ap.add_argument("--kind", default="video", choices=["video", "photo"])
    args = ap.parse_args()
    try:
        if args.search:
            config.ensure_tls_certs()
            print(json.dumps(search(args.search, args.kind), indent=2))
            return 0
        if not args.project:
            ap.error("--project or --search is required")
        out = run(args.project, args.offline)
    except (StageError, subprocess.CalledProcessError) as e:
        print(e, file=sys.stderr)
        return 1
    print(f"→ {out.relative_to(config.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
