# Reviews

External reviewers: **codex**, **opencode**, **atomic-agent**. Their output is advisory; this file records what was applied and what was rejected (with reasons).

## Round 1 — PLAN.md (pre-build, 2026-10-06)

### opencode (`opencode run`)

| # | Suggestion | Decision |
|---|---|---|
| 1 | Sandbox retry strategy too vague (limit, feedback content, failure signal) | **Applied** — explicit failure signal (non-zero exit + stdout/stderr), default `max_retries=3`, feedback fed back to the patch model, configurable. |
| 2 | Eval metrics need computation definitions, JSON schema, per-fault breakdown | **Applied** — metric definitions and versioned `results/<date>/eval-v1.json` with per-fault rows added to PLAN.md. |
| 3 | Tavily citation protocol undefined (format, filtering, 429 handling) | **Applied** — typed citations (title/url/query), backoff on 429/error, degraded-mode flag in the report. |
| 4 | Routing config schema and API-failure fallback unspecified | **Applied** — `mender.yaml` schema + price-source field; one backoff retry then typed error, no silent cross-tier fallback. |
| 5 | `gh` PR specifics missing (branch naming, auto-merge risk) | **Applied** — `mender/<service>-<short-id>` branches, merge permissions untouched, never enables auto-merge. |
| 6 | Fault catalogue structure undefined | **Applied** — `fault.yaml` schema with expected labels for programmatic scoring. |
| 7 | No CI pipeline | **Applied** — `.github/workflows/ci.yml` (ruff + mypy + pytest) added to Phase 1. |
| 8 | Secret management light | **Partially applied** — gitleaks over tree + history was already in the brief/plan; key rotation is out of scope for an open-source repo with env-only creds. |
| 9 | Type coverage unproven (no mypy config) | **Applied** — mypy strict added to tooling and CI. |
| 10 | Story/feedback/video phases premature | **Rejected** — the project brief mandates updating them continuously from real runs; they trail the build and do not drive it. |
| — | "Three-tier routing over-engineered for Phase 1" | **Rejected as stated** — routing is a hard requirement; it lands in Phase 2 with the first model call, before any pipeline code. |

### atomic-agent (`echo … | atomic-agent run`)

| # | Suggestion | Decision |
|---|---|---|
| 1 | Verify Nebius model IDs are live before committing to them | **Applied early** — all three tiers smoke-tested against the live API on 2026-10-06 before Phase 1. |
| 2 | Tighten sandbox failure signal (exit code vs log grep) | **Applied** — exit code is authoritative; output tail is feedback, not signal. |
| 3 | Test-fixture samples for cluster events/pods, keep secrets out of fixtures | **Applied** — recorded fixtures under `tests/fixtures/`, scrubbed of key material. |
| 4 | Tavily cost/usage as first-class metric | **Applied** — Tavily call count + latency recorded in the same usage ledger. |
| 5 | `gh` token availability inside the sandbox | **Applied as clarification** — `gh` runs only in the `pr` step outside the sandbox; the sandbox container gets no GitHub credentials. |
| 6 | Kind cluster vs sandbox resource contention | **Applied** — sandbox runs lightweight test containers, not the kind cluster; they are separate phases. |
| 7 | Versioned results schema to avoid drift | **Applied** — `eval-v1` schema version field. |
| 8 | Add `docs/api-contract.md` for the Nebius client contract | **Rejected** — the OpenAI SDK is used unmodified; the README "How models are used" section documents base URL, headers, and assumptions instead of a separate file. |
| 9 | Add `.github/workflows/lint.yml` (separate from #7) | **Merged** — one CI workflow runs lint + typecheck + tests. |

### codex (`codex exec`)

Not run: the local Codex install returned a usage-limit error (quota exhausted until 2026-10-09). Will retry before the release review; if still unavailable, it will be recorded as "review not obtained" rather than passed.
