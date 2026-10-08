"""Central configuration for the Videomaker pipeline.

One file, so there is exactly one place to look. Anything a brief or plan can
override is a default here, not a constant.
"""

import os
from pathlib import Path

# --- Paths -----------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
PROJECTS = ROOT / "projects"  # one folder per video: brief, plan, assets, voice
BRIEFS = ROOT / "briefs"  # example and template briefs, checked in
OUTPUT = ROOT / "output"  # finished videos, one folder per project
WORK = ROOT / "work"  # scratch: intermediate renders, temp audio

ASSETS = ROOT / "assets"  # shared media library, reused across projects
CLIPS = ASSETS / "clips"  # downloaded video, normalised to H.264 muted
PHOTOS = ASSETS / "photos"  # downloaded stills
GENERATED = ASSETS / "generated"  # AI-generated images/clips (ComfyUI etc.)
MUSIC = ASSETS / "audio" / "music"
SFX = ASSETS / "audio" / "sfx"

REMOTION = ROOT / "remotion"
PUBLIC = REMOTION / "public"  # what the renderer may load; rebuilt per video
PUBLIC_MEDIA = PUBLIC / "media"
PUBLIC_AUDIO = PUBLIC / "audio"
MANIFEST = PUBLIC / "project.json"


def project_dir(slug: str) -> Path:
    return PROJECTS / slug


def output_dir(slug: str) -> Path:
    return OUTPUT / slug


def ensure_tls_certs() -> None:
    """Point urllib at certifi's CA bundle when it is installed.

    macOS pythons often ship without a system CA path wired up, and every
    network stage dies with CERTIFICATE_VERIFY_FAILED without this.
    """
    try:
        import certifi
    except ImportError:
        return
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())


# --- Video -----------------------------------------------------------------

FORMATS = {
    "landscape": (1920, 1080),  # YouTube, presentations
    "portrait": (1080, 1920),  # Shorts, Reels, TikTok
    "square": (1080, 1080),  # feeds
}
DEFAULT_FORMAT = "landscape"
DEFAULT_FPS = 30

# Breathing room after each scene's narration, so cuts don't clip a word.
SCENE_TAIL_S = 0.4
MIN_SCENE_S = 2.0
# A scene with no narration still needs to be on screen long enough to read.
SILENT_SCENE_S = 3.0

# --- Planning --------------------------------------------------------------

# "agent": the AI driving the repo writes plan.json itself (the normal path).
# "ollama": a local model writes it, for unattended runs.
# "mock": one card per sentence of the prompt; offline and deterministic.
PLAN_BACKEND = os.environ.get("VM_PLAN_BACKEND", "agent")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
# Pin the context: left to the server default an 8B model can load at 14GB
# and spill onto the CPU (the same lesson as robot-reporter).
OLLAMA_NUM_CTX = 8192
WORDS_PER_MINUTE = 150

# --- Assets ----------------------------------------------------------------

# Searched in this order; providers without an API key are skipped.
# Openverse and Wikimedia Commons need no key and are openly licensed.
MEDIA_PROVIDERS = ["pexels", "pixabay", "openverse", "commons"]
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "")
USER_AGENT = "videomaker/0.1 (https://github.com/bitmat1/videomaker)"

FETCH_TIMEOUT_S = 20
# Bounded hard: an unbounded download stalls an on-demand request.
VIDEO_MAX_BYTES = 80_000_000
PHOTO_MAX_BYTES = 15_000_000
CLIP_MAX_SECONDS = 20

# --- Voice -----------------------------------------------------------------

# kokoro | piper | say | mock
TTS_BACKEND = os.environ.get("VM_TTS_BACKEND", "mock")
SAMPLE_RATE = 48_000
KOKORO_VOICE = "af_heart"
KOKORO_SPEED = 1.0
PIPER_MODEL = os.environ.get("PIPER_MODEL", "")  # path to a .onnx voice
SAY_VOICE = "Samantha"

# --- Captions --------------------------------------------------------------

# "whisper" aligns words with faster-whisper when installed; "estimate"
# spreads words across the clip by length. Mock voice always estimates.
CAPTION_BACKEND = os.environ.get("VM_CAPTION_BACKEND", "whisper")
WHISPER_MODEL = "base.en"
CAPTION_MAX_WORDS = 6

# --- Finish ----------------------------------------------------------------

# -14 LUFS integrated is what YouTube, Spotify and most socials normalise to.
LOUDNESS_LUFS = -14
TRUE_PEAK_DB = -1.5
MUSIC_VOLUME = 0.12  # under narration
