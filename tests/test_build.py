"""The pipeline from plan to manifest, offline, with the mock voice."""

import json
import shutil
from pathlib import Path

import pytest

import assets
import build
import config
import voice
from finish import to_srt
from manifest import validate_manifest


@pytest.fixture
def sandbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point every path in config at a temporary tree."""
    root = tmp_path
    monkeypatch.setattr(config, "ROOT", root)
    monkeypatch.setattr(config, "PROJECTS", root / "projects")
    monkeypatch.setattr(config, "CLIPS", root / "assets" / "clips")
    monkeypatch.setattr(config, "PHOTOS", root / "assets" / "photos")
    monkeypatch.setattr(config, "PUBLIC", root / "public")
    monkeypatch.setattr(config, "PUBLIC_MEDIA", root / "public" / "media")
    monkeypatch.setattr(config, "PUBLIC_AUDIO", root / "public" / "audio")
    monkeypatch.setattr(config, "MANIFEST", root / "public" / "project.json")
    monkeypatch.setattr(config, "CAPTION_BACKEND", "estimate")
    # validate_manifest's default argument was bound at import time.
    real = validate_manifest
    monkeypatch.setattr(build, "validate_manifest",
                        lambda m: real(m, root / "public"))
    pdir = root / "projects" / "demo"
    pdir.mkdir(parents=True)
    src = Path(__file__).resolve().parent.parent / "projects" / "demo" / "plan.json"
    shutil.copy(src, pdir / "plan.json")
    return root


def test_offline_build(sandbox: Path) -> None:
    assets.run("demo", offline=True)
    voice.run("demo", "mock")
    build.run("demo")
    m = json.loads((sandbox / "public" / "project.json").read_text())

    assert (m["width"], m["height"]) == (1920, 1080)
    assert [s["kind"] for s in m["scenes"]] == ["title", "card", "card", "card"]
    # The title has a forced length; the rest follow their narration.
    assert m["scenes"][0]["endFrame"] == 75
    assert m["scenes"][-1]["endFrame"] == m["durationInFrames"]
    assert m["audio"]["narration"] == "audio/narration.wav"
    assert m["captions"] and all(
        c["endFrame"] <= m["durationInFrames"] for c in m["captions"])
    # Captions break at punctuation: no line runs across a sentence end.
    assert all("." not in c["text"][:-1] for c in m["captions"])


def test_mock_voice_is_deterministic(sandbox: Path) -> None:
    voice.run("demo", "mock")
    first = (sandbox / "projects/demo/voice/s02.wav").read_bytes()
    voice.run("demo", "mock")
    assert (sandbox / "projects/demo/voice/s02.wav").read_bytes() == first


def test_estimated_words_cover_the_clip() -> None:
    words = voice.estimate_words("one two three", 3.0)
    assert words[0]["start"] == 0
    assert words[-1]["end"] == pytest.approx(3.0, abs=0.01)


def test_srt_timestamps() -> None:
    srt = to_srt([{"startFrame": 0, "endFrame": 45, "text": "Hi"}], 30)
    assert srt == "1\n00:00:00,000 --> 00:00:01,500\nHi\n"
