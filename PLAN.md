# Mender — Plan

**Mender: Kubernetes Incident-to-Fix Agent.** Broken Kubernetes service → root cause → patch → tested in an isolated sandbox → PR with evidence. A human reviews and merges. Mender never merges.

## Stack

Python 3.12, fully typed (mypy strict), pytest, ruff (lint + format), `uv`, CI via GitHub Actions (ruff + mypy + pytest). OpenAI Python SDK against Nebius Token Factory (`https://api.tokenfactory.nebius.com/v1/`, verified live). Tavily REST API. `gh` for PRRs. `kind` + Docker for the demo cluster; Docker for the sandbox.

## Model routing (configurable, every call accounted)

| Tier | Model (live IDs) | Job |
|---|---|---|
| nano | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | log/event triage, high volume |
| ultra | `nvidia/Nemotron-3-Ultra-550b-a55b` | root-cause reasoning |
| super | `nvidia/nemotron-3-super-120b-a12b` | patch writing |

`mender.yaml` defines tier → model, price per 1M tokens with a source note (honesty: prices Nebius does not publish are marked as such, never invented), temperature, and max tokens. Env vars override. Each call appends to a usage ledger: tier, model, tokens (prompt/completion/reasoning), latency, cost, and Tavily calls (count, latency) alongside. API failure → one retry with backoff, then a typed error (no silent cross-tier fallback).

## Phases (commit after each)

1. **Skeleton** — pyproject (ruff + mypy-strict + pytest configured), `src/mender/` layout, LICENSE (Apache-2.0), `.gitignore` (excludes `.env`, `project_story.md`, `feedback_answers.md`), `.env.example` (names only), `assets/mender-logo.png`, README stub, `.github/workflows/ci.yml`.
2. **Model router + Tavily** — Nebius client with per-tier usage ledger; Tavily client returning typed citations with backoff on 429/error and a degraded-mode flag (diagnosis proceeds, report marks sources unavailable). Unit tests use recorded fixtures under `tests/fixtures/` (no live calls, no key material in fixtures).
3. **Pipeline** — `triage (nano) → evidence gathering → root-cause report with Tavily citations (ultra) → patch (super) → sandbox verify → PR via gh`. Modules: `router/`, `triage/`, `diagnosis/`, `patching/`, `sandbox/`, `pr/`.
   - **Sandbox:** failure signal = test process exit code; feedback = stdout/stderr tail; `max_retries` configurable (default 3), each retry feeds the previous failure output to the patch model. Tests run in a lightweight Docker container (app unit/integration tests with the patched manifests) — not against the demo cluster, so sandbox and demo cluster never contend.
   - **PRs:** branch `mender/<service>-<short-id>`; body = root cause, evidence, diff, test results, Tavily sources; never draft-auto-merge, never merges — merge permissions are untouched.
4. **Demo environment** — kind cluster + small sample app + fault-injection script. ≥20 distinct faults, each a directory with `fault.yaml` (id, description, apply/cleanup commands, expected root-cause labels, category) so scoring is programmatic.
5. **Eval harness** — runs every fault end-to-end. Definitions: *root-cause accuracy* = predicted labels (normalized) ∩ expected labels / cases; *fix-pass rate* = sandbox tests green on first-or-retry-bounded attempt / cases; *median time-to-PR* over successful cases; *cost per tier* from the ledger. Versioned raw schema `results/<date>/eval-v1.json` committed with per-fault breakdown incl. failures. Nothing invented or rounded up.
6. **Packaging** — Dockerfile, `mender serve`, complete README (architecture diagram with a dedicated Tavily box, quickstart, configuration, model usage, Tavily usage, eval results, limitations). Deployment: Nebius dedicated endpoints documented (Serverless Jobs/Endpoints are not on Token Factory — the local `DockerRunner` implements the `SandboxRunner` interface so a remote runner drops in unchanged).
7. **Release** — reviews by codex, opencode, atomic-agent at phase boundaries and before release, recorded in `REVIEWS.md` (applied vs rejected + why); gitleaks/grep secret scan of tree and history; `gh repo create` with the specified description and topics; license visible on the repo page.
8. **Story, feedback, video** — `project_story.md` and `feedback_answers.md` filled only with measured results, kept out of the public repo; ≤3 min demo video via videowright from real runs, saved under `demo/`, not uploaded.

## Interfaces

- `mender diagnose --service <name>` → root-cause report (JSON + Markdown, Tavily sources cited)
- `mender fix` → patch + sandbox test results
- `mender pr` → opens the PR (root cause, evidence, diff, tests, Tavily sources); never merges
- `mender eval --all` → harness over the fault catalogue
- `SandboxRunner` protocol: `DockerRunner` default; remote Nebius runner later behind the same interface

## Working rules

Recall from Hindsight bank `mender` at session start; retain decisions and lessons. No secret is ever printed or committed; `.env` is gitignored. External reviewer output is advisory — sound suggestions applied, rejections explained in `REVIEWS.md`.
