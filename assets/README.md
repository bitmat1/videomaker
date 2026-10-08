# assets/

The shared media library. Everything here is reused across projects and is
gitignored except the folder structure.

| Folder | What goes here | Written by |
|---|---|---|
| `clips/` | Downloaded video, normalised to H.264, muted, ≤20s | `pipeline/assets.py` |
| `photos/` | Downloaded stills | `pipeline/assets.py` |
| `generated/` | AI-generated images, clips, voice or sfx (ComfyUI, ElevenLabs MCP, …) | you / other tools |
| `audio/music/` | Music beds. Reference with `plan.music.file` | you |
| `audio/sfx/` | Sound effects | you |

Downloaded files are named by a hash of their source URL, so the same clip is
never fetched twice. Credits and licences live in each project's
`assets.json` and are written to `output/<slug>/credits.txt`.

**Rights.** Pexels and Pixabay content is free to use under their own
licences; Openverse and Wikimedia Commons results are filtered to licences
that allow commercial use and modification, but most CC licences still need
attribution — which is why `credits.txt` exists. Anything fetched by `url`
(including via yt-dlp) is your responsibility: only use footage you have the
right to use.
