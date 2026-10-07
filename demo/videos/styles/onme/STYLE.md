---
title: OnMe
slug: onme
picker_description: 'Deep-indigo fitting room. Lilac type, one magenta accent, soft rounded surfaces, calm motion.'
font_sources:
  - https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700&display=swap
  - https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap
  - https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap
mood: [calm, nocturnal, tactile, intimate, precise]
good_for:
  - OnMe itself — app demos, walkthroughs, launches
  - Consumer apps that want to feel like a mirror, not a machine
  - Fashion, beauty, personal styling
  - Anything that should let one colour carry the emotion
bad_for:
  - Technical/infra audiences
  - Anything that needs bright, daylight energy
  - Enterprise B2B
tags: [dark-mode, fashion, calm, rounded, magenta, product-demo]
references: [OnMe app itself (src/constants/theme.ts), fitting-room mirrors, soft neon in dark retail]
---

# OnMe — STYLE.md

## Identity

A fitting room at night. The surface is the logo's deep indigo taken to near-black, the
type is light lilac, and there is exactly one warm colour in the room: magenta, and it
belongs to the outfit — never to the software. Rounded surfaces, soft halos, calm motion.
The viewer should feel like they are standing in front of a mirror, not operating a tool.

**Mood:** calm, nocturnal, tactile, intimate, precise.

## When to use

- OnMe itself — demos, walkthroughs, feature intros, launches
- Consumer apps that want to feel like a mirror, not a machine
- Fashion, beauty, personal styling

## When to avoid

- Technical/infra audiences that expect mono type and grids
- Anything needing bright, daylight energy

## Layout principles

- **One subject per frame.** A phone mock, a garment card, a single sentence. Never a busy slide.
- **The surface is a stage.** Background stays near-black (`--color-bg`); elevated panels
  (`--color-bg-elevated`, `--color-bg-element`) lift content without brightening the room.
- **Phone mocks are the hero prop.** Portrait frames use `--portrait-ratio` (3/4); give them
  soft magenta halos rather than hard shadows.
- **Big, calm type.** Headlines own their frame; supporting copy is quiet, never crowded.
- **Generous but deliberate space.** This style breathes like a fitting room, but content
  still fills 80–90% of the frame width. A small card floating in empty space is wrong.

## Color application

- Background `#0B0620`; panels step up through `--color-bg-elevated` → `--color-bg-element`
  → `--color-bg-selected` as they come forward.
- Text is `--color-fg` (#F6F1FF); secondary is `--color-muted` (#B3A4DC); faint labels use
  `--color-faint` (#8E7CC4).
- **Magenta is the outfit.** Use `--color-accent` (#E860B0) for one thing per scene — the
  button, the result, the key number. `--color-accent-strong`/`-soft` for its lighter
  steps, `--color-accent-wash` for a filled accent panel. `--color-on-accent` is the only
  text colour that sits on magenta.
- Success/warning/danger exist but are used sparingly and softly.
- Borders are quiet hairlines (`--color-border`), `--color-border-strong` only to divide.

## Type rules

- **Display:** Sora, 64–160px, weight 600, tracking −0.02em. Headlines are short.
- **Body:** Inter, 36px minimum at 1080p. Never smaller for anything that must be read.
- **Mono:** JetBrains Mono only for tiny technical captions (URLs, versions) at 20–24px.
- Labels may be uppercase with 0.12em tracking, but only when large enough to read.
- One accent word per headline is allowed — colour it magenta, nothing else.

## Motion principles

- **Calm, smooth, no bounce.** Easing is `--ease-out` (soft cubic-bezier). Nothing snaps.
- **Fade + gentle rise.** Elements enter with opacity 0→1 and translateY(20–32px)→0 over
  400–600ms, staggered ~80–120ms. Exits are simple fades.
- **Halo pulses, never flashes.** Accent glows may breathe slowly (2–3s) but never blink.
- **The reveal is the moment.** When a try-on result appears, it is the only thing that
  moves: a soft scale 0.98→1 with the magenta halo fading in around it.
- **Forbidden:** bounce, elastic, steps/glitch easing, hard cuts inside a scene, spin.

## Pacing

Unhurried. Scenes hold 4–6s. Reveals get a beat of stillness after them — the mirror
doesn't rush. Beat boundaries belong to `waitForNext()` (voiceover sync), never hardcoded
timing.

## Per-scene recipes

| Scene | Recipe |
|---|---|
| **Title** | `OnMe` in large Sora, tagline underneath, magenta underline that draws in. |
| **Section** | Small uppercase label, then the section name large. No decoration. |
| **Feature** | One sentence per row, numbered with magenta numerals; rows fade-rise in sequence. |
| **Stat** | Number in accent-strong, large; caption in muted below. Halo pulses slowly. |
| **UI showcase** | Phone mock with the app's real screens: rounded cards, magenta pill button, soft halo. |
| **Content** | One idea per scene, short lines, generous leading. |
| **CTA** | App name + one instruction ("Upload a photo. Pick an outfit.") + magenta pill. |

### Connective elements

- **Lower third:** a small faint label (`--color-faint`) with the current step name.
- **Scene transition:** `fade` — this style never slides or wipes.
- **Ambient:** a very slow magenta halo drift behind the subject; never distracting.

## Pitfalls

- **Don't brighten the background.** The room stays dark; only the outfit has colour.
- **Don't use more than one accent gesture per scene.**
- **Don't use tech blue or neutral grey** — not a tech product palette.
- **Don't shrink text below 36px** to fit more in. Remove content instead.
- **Don't bounce, flash, or glitch.** Calm is the whole point.
- **No emoji.** Use the app's own shapes: pills, rounded cards, soft halos.
