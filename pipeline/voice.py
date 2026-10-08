"""Stage 3: narration → speech, with word timings for captions.

    projects/<slug>/plan.json  →  projects/<slug>/voice.json
                                  projects/<slug>/voice/<scene>.wav

TTS backends (config.TTS_BACKEND, or plan.voice.backend):

  kokoro  82M open model, Apache 2.0, good on CPU. `pip install kokoro soundfile`
  piper   fast ONNX voices, MIT, many languages. `pip install piper-tts`
          and set PIPER_MODEL to a downloaded .onnx voice.
  say     macOS built-in. Zero install.
  mock    amplitude-modulated noise, one burst per word. Runs anywhere,
          deterministic; for tests and plumbing.

Every backend yields a mono 16-bit WAV at config.SAMPLE_RATE, so nothing
downstream knows which one ran.

Word timings come from faster-whisper when it is installed, which aligns to
what was actually said; otherwise words are spread over the clip by length.

Usage:
  python pipeline/voice.py --project my-video [--backend mock]
"""

import argparse
import array
import math
import random
import subprocess
import sys
import wave
import zlib
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from common import StageError, ffmpeg, read_json, rel, require, write_json

Word = dict[str, Any]


def _to_wav(src: Path, dst: Path) -> None:
    ffmpeg("-i", str(src), "-ar", str(config.SAMPLE_RATE), "-ac", "1",
           "-c:a", "pcm_s16le", str(dst))


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()


# --- Backends --------------------------------------------------------------


def synth_mock(text: str, out: Path, voice: dict[str, Any]) -> None:
    rate = config.SAMPLE_RATE
    rng = random.Random(zlib.crc32(text.encode()))
    samples = array.array("h")
    for word in text.split():
        n = int(rate * (0.12 + 0.055 * len(word)))
        for i in range(n):
            env = math.sin(math.pi * i / n)
            samples.append(int(rng.uniform(-1, 1) * env * 9000))
        samples.extend([0] * int(rate * 0.08))
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(samples.tobytes())


def synth_kokoro(text: str, out: Path, voice: dict[str, Any]) -> None:
    try:
        import numpy as np
        import soundfile as sf
        from kokoro import KPipeline
    except ImportError as e:
        raise StageError("kokoro not installed: pip install kokoro soundfile") from e
    name = voice.get("voice", config.KOKORO_VOICE)
    # Kokoro voice ids start with their language code: a=US, b=UK, e, f, j, z…
    pipe = KPipeline(lang_code=name[0])
    chunks = [audio for _, _, audio in
              pipe(text, voice=name, speed=voice.get("speed", config.KOKORO_SPEED))]
    raw = out.with_suffix(".24k.wav")
    sf.write(raw, np.concatenate(chunks), 24_000)
    _to_wav(raw, out)
    raw.unlink()


def synth_piper(text: str, out: Path, voice: dict[str, Any]) -> None:
    model = voice.get("model") or config.PIPER_MODEL
    if not model:
        raise StageError("piper needs a voice: set PIPER_MODEL or plan.voice.model")
    raw = out.with_suffix(".piper.wav")
    subprocess.run([sys.executable, "-m", "piper", "-m", model, "-f", str(raw)],
                   input=text, text=True, check=True)
    _to_wav(raw, out)
    raw.unlink()


def synth_say(text: str, out: Path, voice: dict[str, Any]) -> None:
    require("say")
    # Some macOS builds refuse to write WAVE directly; AIFF always works.
    raw = out.with_suffix(".aiff")
    subprocess.run(["say", "-v", voice.get("voice", config.SAY_VOICE), "-o",
                    str(raw), text], check=True)
    _to_wav(raw, out)
    raw.unlink()


BACKENDS = {"mock": synth_mock, "kokoro": synth_kokoro, "piper": synth_piper,
            "say": synth_say}


# --- Word timings ----------------------------------------------------------


def estimate_words(text: str, duration: float) -> list[Word]:
    words = text.split()
    weights = [len(w) + 2 for w in words]
    total = sum(weights) or 1
    cursor, out = 0.0, []
    for word, weight in zip(words, weights):
        span = duration * weight / total
        out.append({"text": word, "start": round(cursor, 3),
                    "end": round(cursor + span, 3)})
        cursor += span
    return out


_whisper: Any = None


def whisper_words(path: Path) -> list[Word] | None:
    global _whisper
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None
    if _whisper is None:
        _whisper = WhisperModel(config.WHISPER_MODEL, compute_type="int8")
    segments, _ = _whisper.transcribe(str(path), word_timestamps=True)
    return [{"text": w.word.strip(), "start": round(w.start, 3),
             "end": round(w.end, 3)}
            for seg in segments for w in (seg.words or [])]


# --- Stage -----------------------------------------------------------------


def run(slug: str, backend: str | None = None) -> Path:
    pdir = config.project_dir(slug)
    plan = read_json(pdir / "plan.json")
    voice = plan.get("voice", {})
    backend = backend or voice.get("backend") or config.TTS_BACKEND
    if backend not in BACKENDS:
        raise StageError(f"unknown TTS backend {backend!r}")
    vdir = pdir / "voice"
    vdir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {"backend": backend, "scenes": {}}
    for scene in plan["scenes"]:
        text = scene["narration"].strip()
        if not text:
            continue
        out = vdir / f"{scene['id']}.wav"
        BACKENDS[backend](text, out, voice)
        dur = wav_duration(out)
        words = None
        if backend != "mock" and config.CAPTION_BACKEND == "whisper":
            words = whisper_words(out)
        result["scenes"][scene["id"]] = {
            "path": rel(out), "duration_s": round(dur, 3),
            "words": words or estimate_words(text, dur),
        }
        print(f"  {scene['id']}: {dur:5.2f}s")
    out_json = pdir / "voice.json"
    write_json(out_json, result)
    return out_json


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    ap.add_argument("--backend", choices=sorted(BACKENDS))
    args = ap.parse_args()
    try:
        out = run(args.project, args.backend)
    except (StageError, subprocess.CalledProcessError) as e:
        print(e, file=sys.stderr)
        return 1
    print(f"→ {out.relative_to(config.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
