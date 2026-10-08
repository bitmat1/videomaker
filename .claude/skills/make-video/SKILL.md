---
name: make-video
description: Make a video on demand in this repo, from a one-line request to a finished MP4 in output/. Use when the user asks for a video, short, explainer, reel or clip.
---

# Make a video

1. **Brief.** `make new PROMPT="<the request>" SLUG=<short-slug>` (or the
   `new_project` MCP tool). Pick `--format portrait` for Shorts/Reels/TikTok.
2. **Plan.** Read `docs/PLAN_SCHEMA.md`, then write
   `projects/<slug>/plan.json` yourself. ~150 words of narration per minute.
   Before committing a scene to a search query, try `make search Q="…"`
   (or `search_media`) and prefer queries that return results.
3. **Validate.** `make plan P=<slug>`. Fix anything it reports.
4. **Look before you render.** `make assets voice build P=<slug>` then
   `make still F=<frame>` for one or two frames; open the PNGs in
   `work/<slug>/`. Adjust the plan and repeat; each step is cheap.
5. **Render.** `make render finish` (or `make video P=<slug>` for all of it).
6. **Hand back** `output/<slug>/<slug>.mp4`, and mention `credits.txt` if
   any third-party media was used.

No network? `make assets` falls back to drawn cards; `--offline` forces it.
No TTS installed? `VM_TTS_BACKEND=mock` proves the plumbing.
