# Plan: Mender demo — a Kubernetes fault goes from failure to verified PR

## Purpose
- Audience: developers evaluating Mender; Nebius/Nemotron + Tavily showcase.
- Takeaway: Mender takes a broken K8s service and returns a verified fix as a PR a human reviews — it never merges.
- Constraints: ≤3 minutes; show real tooling, not just narration; use the repo logo (assets/mender-logo.png); mention Tavily citations and "never merges".

## Style
- Active style: onme (default, from videowright.config.ts)
- Notes: clean tech-explainer look; keep text large and legible.

## Audio intent
- Voiceover: yes (ElevenLabs if GEMINI_API_KEY/ELEVENLABS_API_KEY available; otherwise silent pacing + on-screen text)
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

## Script (voiceover, if available)
Mender takes a broken Kubernetes service and returns a verified fix.
Triage, root cause, patch, sandbox test, and a pull request a human reviews.
Mender never merges anything itself.

We start from a kind cluster running the sample checkout service — 21 invariant checks pass.

Then we inject a fault: a memory limit too low for the heap. Pods start OOM-killing.

Mender collects the evidence and triage — the nano tier — cuts the noise down to signals and suspects.

The ultra tier proposes web searches, runs them through Tavily, and writes a numbered root-cause report. Each citation is a real link a reviewer can check.

The super tier writes a patch to the one file Mender is allowed to change.

Before anything is committed, the patch is tested in an isolated Docker container with no network. The tests pass.

Mender opens a pull request: root cause, evidence, the diff, the test results, and the Tavily sources. A human reviews and merges. Mender never merges.

Mender — from broken service to verified fix, in minutes, with evidence.

## Log

### 2026-10-07 — Initial scaffold
- Videowright project set up in demo/videos/; default style onme.
- Plan drafted from the live demo (demo/demo.sh, low-memory-limit fault).
- Video folder: videos/demo/. Segment build follows in create_or_edit_video.md flow.
