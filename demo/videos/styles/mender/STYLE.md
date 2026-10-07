---
title: Mender
slug: mender
picker_description: 'Dark navy operations console. Steel-blue type, one green accent, terminal panels, calm motion.'
font_sources:
  - npm:@fontsource/inter (latin 400, 500, 600, 700)
  - npm:@fontsource/jetbrains-mono (latin 400, 500)
---

# Style: Mender

## When to use

Videos about Mender for engineers: demos, walkthroughs, release notes. The look comes
from the logo (`videos/demo/assets/mender-logo.png`) and matches the README diagram.

## Aesthetic rules

- **Colour.** Background `--color-bg` (logo navy). Text `--color-fg`, with `--color-steel`
  and `--color-muted` for secondary text. Green `--color-accent` marks the thing that is
  correct or active: a passed check, the current pipeline stage, an added diff line.
  Use it for one idea in each scene. Red `--color-danger` appears only while the service
  is broken.
- **Type.** Inter for headings and body, JetBrains Mono for commands, file paths, log
  lines and numbers that come from a tool. The fonts are npm packages imported by
  `tokens.css`; `defineScene()` waits for them before a scene plays.
- **Sizes at 1080p.** Headline 72px or more, body 36px or more, terminal text 30px or
  more, small labels 24px or more. No text below 20px.
- **Layout.** One subject in each scene. Content uses the full width inside the safe
  area (`--safe-x`, `--safe-y`). Panels use `--color-surface` with a `--color-border`
  line and `--radius-lg` corners.
- **Real data only.** Each number, command, log line and citation on screen comes from an
  eval run: the committed artefacts in `results/`, and that run's `triage.json` and
  `patch.json` for the triage output and the diff. Do not invent values.
- **Glyphs.** The fonts are the latin subset. Do not type arrows or check marks as
  characters; draw them with CSS or inline SVG.

## Motion vocabulary

- Elements enter with opacity 0 to 1 and a 24px upward move, 500ms, easing
  `cubic-bezier(0.22, 1, 0.36, 1)`, with a 90ms stagger inside a group.
- Animation uses `element.animate()` only. The render clock does not drive CSS
  transitions or CSS keyframes.
- Each reveal that the narration cues is a beat behind `ctx.waitForNext()`.
- Scenes change with `fade`.

## Don'ts

- No bounce, no spin, no slide transitions between scenes.
- No looping animations: the render clock stops them after one iteration.
- No second accent colour. No emoji.
- No `rem`, `vw` or `vh` units: dev and render resolve them differently.
