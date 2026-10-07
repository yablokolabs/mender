# Plan: Mender demo — a Kubernetes fault goes from failure to verified PR

## Purpose
- Audience: developers evaluating Mender; Nebius/Nemotron + Tavily showcase.
- Takeaway: Mender takes a broken K8s service and returns a verified fix as a PR a human reviews — it never merges.
- Constraints: ≤3 minutes; show real tooling, not just narration; use the repo logo (assets/mender-logo.png); mention Tavily citations and "never merges".

## Style
- Active style: mender (default, from videowright.config.ts)
- Notes: logo colours (navy, steel blue, one green accent); terminal panels; text large and legible.

## Audio intent
- Voiceover: yes (ElevenLabs, voice Lily, British English; audio track v1 is the default track)
- Sound effects: no
- Background music: no
- Notes: keep it short; the demo is a tool walkthrough.

## Segment outline
1. intro — title + what Mender does (logo, one-liner, "never merges")
2. setup — kind cluster + sample checkout service deploys; 21 checks pass
3. fault — inject a fault (low-memory-limit), symptoms appear
4. triage — nano tier reduces evidence to signals/suspects
5. diagnosis — ultra tier + Tavily searches produce a numbered root-cause report
6. patch — super tier writes a patch to the allowed file
7. sandbox — patch tested in Docker (--network none), passes
8. pr — prepared PR with root cause, evidence, diff, tests, Tavily sources
9. outro — results line + "never merges; a human reviews"

## Script
The script is in `voiceover_script/script.md`. It is generated from the `voiceover` field
of each segment: `npx videowright script --write`.

## Log

### 2026-10-07 — Initial scaffold
- Videowright project set up in demo/videos/; default style onme.
- Plan drafted from the live demo (demo/demo.sh, low-memory-limit fault).
- Video folder: videos/demo/. Segment build follows in create_or_edit_video.md flow.

### 2026-10-07 — Rebuild: working segments, mender style, narration
- The first render showed "Segment error: intro — el is not defined" for its whole length
  and had no audio. Cause: `el` used inside `play()`, one timing entry for 3 to 6 beats,
  CSS transitions (the render clock drives only `element.animate()`), a logo URL that
  returned 404.
- Segments moved to `segments/<id>/` (documented layout) and rewritten on shared
  `components/scene.ts` and `components/scene.css`. Timeline entries are `{ id, transition }`.
- All on-screen values come from `results/2026-10-06/cases/low-memory-limit/`.
- Style changed from onme to mender. Fonts come from `@fontsource` packages.
- Narration: `audio/originals/voiceovers/v1/` (Lily). Track v1 is normalised to -16 LUFS.
  Timing is computed from the word timestamps, snapped to 60 fps frames, and written to
  `audio/tracks/v1/track.ts` and to each segment's `advances`.
- A new voice needs: `generate.sh`, a new track, new timing in both places, a new render.
- `npm test` drives the real player in a browser. `videowright render` exits 0 even when a
  segment throws, so run the tests before each render.
- Render: `npx videowright render demo --output ../mender-demo.mp4` (96.4 s).
