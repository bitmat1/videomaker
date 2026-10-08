# plan.json

The plan is the shot list for one video. The AI writes it; every later stage
reads it. `pipeline/manifest.py:validate_plan` is the authority — this page
describes what it accepts.

```json
{
  "title": "Why the Tides Turn",
  "format": "landscape",
  "fps": 30,
  "style": { "accent": "#3fb6ff", "background": "#07131f" },
  "voice": { "backend": "kokoro", "voice": "af_heart", "speed": 1.0 },
  "music": { "file": "assets/audio/music/calm.mp3", "volume": 0.12,
             "credit": "Artist — CC BY 4.0" },
  "scenes": [
    {
      "id": "s01",
      "narration": "",
      "onscreen": "Why the Tides Turn",
      "visual": { "kind": "title" }
    },
    {
      "id": "s02",
      "narration": "Twice a day, the sea climbs the beach and slips away again.",
      "visual": { "kind": "video", "query": "ocean waves beach" },
      "motion": "zoom-in",
      "transition": "fade"
    },
    {
      "id": "s03",
      "narration": "The Moon is pulling on the whole planet.",
      "onscreen": "Gravity",
      "visual": { "kind": "photo", "query": "full moon night" },
      "motion": "pan-left"
    }
  ]
}
```

## Top level

| Field | Required | Meaning |
|---|---|---|
| `title` | yes | Shown nowhere unless a scene uses it; names the video |
| `format` | no | `landscape` 1920×1080, `portrait` 1080×1920, `square` 1080×1080 |
| `fps` | no | 12–60, default 30 |
| `style` | no | `background`, `text`, `accent` colours; `font`; `captions` true/false |
| `voice` | no | `backend` (kokoro, piper, say, mock), `voice`, `speed`, `model` (piper) |
| `music` | no | `file` (repo-relative), `volume` 0–1, `credit` |

## Scenes

| Field | Default | Meaning |
|---|---|---|
| `id` | `s01`… | Unique; names the voice file |
| `narration` | `""` | Spoken text. Sets the scene's length |
| `onscreen` | `""` | Short overlay text (a few words, not the narration) |
| `visual` | card | See below |
| `motion` | `zoom-in` | `none`, `zoom-in`, `zoom-out`, `pan-left`, `pan-right` |
| `transition` | `fade` | `cut` or `fade` into this scene |
| `seconds` | from voice | Force a length; otherwise narration + 0.4s |

### visual

| `kind` | Also needs | Resolved by |
|---|---|---|
| `title` | `onscreen` text | Drawn title card |
| `card` | narration or `onscreen` | Drawn animated background |
| `video` / `photo` | one of `query`, `url`, `file` | `assets.py` |

- `query` — 2–4 concrete, filmable words ("city traffic night", not
  "urban energy"). Searched on Pexels, Pixabay, Openverse, Wikimedia Commons.
- `url` — a direct media link, or a page `yt-dlp` can read. Only use footage
  you have the right to use; set `credit` and `license` on the visual.
- `file` — repo-relative path, e.g. `assets/generated/hero.png` or
  `assets/clips/abc123.mp4`. Use for AI-generated images, the user's own
  footage, or a clip already in the library.

If a search finds nothing licensed, the scene falls back to a card, so a
video always completes.

## Writing a good plan

- ~150 spoken words per minute. A 30-second video is ~75 words.
- One idea per scene; 1–2 sentences of narration each.
- Open with a title or a striking visual, close with a clear last line.
- Vary motion between neighbouring scenes.
- Portrait videos: keep `onscreen` text very short; captions take the lower
  third.
