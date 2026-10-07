<p align="center">
  <img src="assets/mender-logo.png" width="120" alt="Mender logo">
</p>

# Mender: Kubernetes Incident-to-Fix Agent

Mender takes a broken Kubernetes service and returns a verified fix: it finds the root
cause, writes a patch, tests the patch in an isolated sandbox, and opens a pull request
with the evidence attached. A human reviews and merges — **Mender never merges anything
itself.**

## Architecture

<details>
<summary>Architecture diagram (inline SVG)</summary>

<svg viewBox="0 0 900 520" xmlns="http://www.w3.org/2000/svg" font-family="system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif" style="max-width:100%; height:auto; border:1px solid #bfc0c0; border-radius:8px;">
  <rect width="900" height="520" fill="#f5f5f5"/>
  <text x="32" y="34" font-size="14" font-weight="600" fill="#2d3142">Mender architecture</text>
  <text x="32" y="48" font-size="10" fill="#7a8399">Incident → triage → root cause → patch → sandbox → PR. A human reviews; Mender never merges.</text>

  <!-- Kubernetes cluster column -->
  <text x="32" y="86" font-size="8" fill="#7a8399" letter-spacing="0.18em" font-weight="500">Kubernetes cluster</text>
  <rect x="32" y="96" width="240" height="300" fill="#ececec" stroke="#bfc0c0" stroke-width="1" rx="8" ry="8"/>
  <text x="44" y="116" font-size="9" fill="#7a8399" font-family="ui-monospace, 'JetBrains Mono', Menlo, monospace">kind · namespace shop</text>
  <rect x="48" y="128" width="208" height="64" fill="#ffffff" stroke="#2d3142" stroke-width="1" rx="8" ry="8"/>
  <text x="60" y="148" font-size="12" font-weight="600" fill="#2d3142">checkout service</text>
  <text x="60" y="164" font-size="9" fill="#7a8399" font-family="ui-monospace, 'JetBrains Mono', Menlo, monospace">Deployment + Service + 21 invariant checks</text>
  <rect x="48" y="204" width="208" height="52" fill="#ffffff" stroke="#2d3142" stroke-width="1" rx="8" ry="8"/>
  <text x="60" y="222" font-size="12" font-weight="600" fill="#2d3142">fault injection</text>
  <text x="60" y="238" font-size="9" fill="#7a8399" font-family="ui-monospace, 'JetBrains Mono', Menlo, monospace">demo/inject.py · apply/cleanup per fault.yaml</text>
  <rect x="48" y="268" width="208" height="56" fill="#ffffff" stroke="#2d3142" stroke-width="1" rx="8" ry="8"/>
  <text x="60" y="286" font-size="12" font-weight="600" fill="#2d3142">evidence: events, logs, manifests</text>
  <text x="60" y="302" font-size="9" fill="#7a8399" font-family="ui-monospace, 'JetBrains Mono', Menlo, monospace">kubectl get/describe · pod status · container logs</text>

  <!-- Mender agent column (focal, accent border) -->
  <text x="332" y="86" font-size="8" fill="#7a8399" letter-spacing="0.18em" font-weight="500">Mender agent</text>
  <rect x="332" y="96" width="236" height="300" fill="#ffffff" stroke="#eb6c36" stroke-width="1.5" rx="8" ry="8"/>
  <text x="344" y="116" font-size="9" fill="#7a8399" font-family="ui-monospace, 'JetBrains Mono', Menlo, monospace">src/mender · Python 3.12 · mypy strict</text>
  <rect x="348" y="128" width="204" height="44" fill="#ffffff" stroke="#2d3142" stroke-width="1" rx="8" ry="8"/>
  <text x="360" y="144" font-size="12" font-weight="600" fill="#2d3142">triage  (nano)</text>
  <text x="360" y="160" font-size="9" fill="#7a8399" font-family="ui-monospace, 'JetBrains Mono', Menlo, monospace">evidence → signals + suspects</text>
  <rect x="348" y="184" width="204" height="52" fill="#ffffff" stroke="#2d3142" stroke-width="1" rx="8" ry="8"/>
  <text x="360" y="200" font-size="12" font-weight="600" fill="#2d3142">Tavily search</text>
  <text x="360" y="216" font-size="9" fill="#7a8399" font-family="ui-monospace, 'JetBrains Mono', Menlo, monospace">advanced depth · ranked sources · cited</text>
  <rect x="348" y="248" width="204" height="44" fill="#ffffff" stroke="#2d3142" stroke-width="1" rx="8" ry="8"/>
  <text x="360" y="264" font-size="12" font-weight="600" fill="#2d3142">root cause  (ultra)</text>
  <text x="360" y="280" font-size="9" fill="#7a8399" font-family="ui-monospace, 'JetBrains Mono', Menlo, monospace">evidence + web sources → report</text>
  <rect x="348" y="304" width="204" height="44" fill="#ffffff" stroke="#2d3142" stroke-width="1" rx="8" ry="8"/>
  <text x="360" y="320" font-size="12" font-weight="600" fill="#2d3142">patch  (super)</text>
  <text x="360" y="336" font-size="9" fill="#7a8399" font-family="ui-monospace, 'JetBrains Mono', Menlo, monospace">allowed files only · path escapes rejected</text>

  <!-- Nebius Token Factory column -->
  <text x="632" y="86" font-size="8" fill="#7a8399" letter-spacing="0.18em" font-weight="500">Nebius Token Factory</text>
  <rect x="632" y="96" width="236" height="80" fill="#ececec" stroke="#bfc0c0" stroke-width="1" rx="8" ry="8"/>
  <text x="644" y="116" font-size="9" fill="#7a8399" font-family="ui-monospace, 'JetBrains Mono', Menlo, monospace">OpenAI-compatible API</text>
  <text x="644" y="132" font-size="9" fill="#7a8399" font-family="ui-monospace, 'JetBrains Mono', Menlo, monospace">https://api.tokenfactory.nebius.com/v1/</text>
  <rect x="648" y="140" width="204" height="36" fill="#ffffff" stroke="#2d3142" stroke-width="1" rx="8" ry="8"/>
  <text x="660" y="155" font-size="11" font-weight="600" fill="#2d3142">nano · triage · $0.06/$0.24</text>
  <rect x="648" y="184" width="204" height="36" fill="#ffffff" stroke="#2d3142" stroke-width="1" rx="8" ry="8"/>
  <text x="660" y="199" font-size="11" font-weight="600" fill="#2d3142">ultra · root cause · $1.00/$3.00</text>
  <rect x="648" y="228" width="204" height="36" fill="#ffffff" stroke="#2d3142" stroke-width="1" rx="8" ry="8"/>
  <text x="660" y="243" font-size="11" font-weight="600" fill="#2d3142">super · patch + repair · $0.30/$0.90</text>

  <!-- Sandbox column -->
  <text x="632" y="290" font-size="8" fill="#7a8399" letter-spacing="0.18em" font-weight="500">Sandbox</text>
  <rect x="632" y="300" width="236" height="72" fill="#ececec" stroke="#bfc0c0" stroke-width="1" rx="8" ry="8"/>
  <text x="644" y="318" font-size="9" fill="#7a8399" font-family="ui-monospace, 'JetBrains Mono', Menlo, monospace">Docker · --network none</text>
  <rect x="648" y="330" width="204" height="34" fill="#ffffff" stroke="#2d3142" stroke-width="1" rx="8" ry="8"/>
  <text x="660" y="348" font-size="11" font-weight="600" fill="#2d3142">runs test command · max_retries 3</text>

  <!-- Pull request column -->
  <text x="632" y="386" font-size="8" fill="#7a8399" letter-spacing="0.18em" font-weight="500">Pull request</text>
  <rect x="632" y="396" width="236" height="92" fill="#ffffff" stroke="#2d3142" stroke-width="1" rx="8" ry="8"/>
  <text x="644" y="414" font-size="12" font-weight="600" fill="#2d3142">gh pr: root cause · evidence · diff</text>
  <text x="644" y="430" font-size="9" fill="#7a8399" font-family="ui-monospace, 'JetBrains Mono', Menlo, monospace">test results · Tavily sources</text>
  <text x="644" y="446" font-size="10" fill="#7a8399">Never merges — human reviews.</text>

  <!-- Arrows -->
  <path d="M 272 180 C 300 180, 320 180, 328 180" fill="none" stroke="#2e5aa8" stroke-width="1"/>
  <text x="296" y="174" font-size="8" fill="#7a8399" font-family="ui-monospace, 'JetBrains Mono', Menlo, monospace">evidence</text>
  <path d="M 456 210 C 490 210, 520 210, 560 210" fill="none" stroke="#2e5aa8" stroke-width="1"/>
  <path d="M 560 210 L 632 132" fill="none" stroke="#2e5aa8" stroke-width="1"/>
  <text x="500" y="204" font-size="8" fill="#7a8399" font-family="ui-monospace, 'JetBrains Mono', Menlo, monospace">queries</text>
  <path d="M 632 150 C 560 150, 520 150, 456 210" fill="none" stroke="#2e5aa8" stroke-width="1"/>
  <text x="540" y="144" font-size="8" fill="#7a8399" font-family="ui-monospace, 'JetBrains Mono', Menlo, monospace">sources</text>
  <path d="M 452 172 L 452 184" fill="none" stroke="#4f5d75" stroke-width="1"/>
  <path d="M 452 232 L 452 248" fill="none" stroke="#4f5d75" stroke-width="1"/>
  <path d="M 452 292 L 452 304" fill="none" stroke="#4f5d75" stroke-width="1"/>
  <path d="M 456 264 C 490 264, 520 264, 560 264" fill="none" stroke="#2e5aa8" stroke-width="1"/>
  <path d="M 560 264 L 632 150" fill="none" stroke="#2e5aa8" stroke-width="1"/>
  <text x="500" y="258" font-size="8" fill="#7a8399" font-family="ui-monospace, 'JetBrains Mono', Menlo, monospace">queries</text>
  <path d="M 556 326 L 632 320" fill="none" stroke="#2e5aa8" stroke-width="1"/>
  <text x="590" y="316" font-size="8" fill="#7a8399" font-family="ui-monospace, 'JetBrains Mono', Menlo, monospace">patch</text>
  <path d="M 750 368 L 750 396" fill="none" stroke="#2e5aa8" stroke-width="1"/>
  <text x="756" y="384" font-size="8" fill="#7a8399" font-family="ui-monospace, 'JetBrains Mono', Menlo, monospace">verified</text>

  <!-- Usage ledger footer -->
  <rect x="32" y="420" width="836" height="72" fill="#ececec" stroke="#bfc0c0" stroke-width="1" rx="8" ry="8"/>
  <text x="44" y="440" font-size="8" fill="#7a8399" letter-spacing="0.18em" font-weight="500">Usage ledger (append-only)</text>
  <text x="44" y="458" font-size="9" fill="#7a8399" font-family="ui-monospace, 'JetBrains Mono', Menlo, monospace">Every model call + Tavily call recorded: tokens, reasoning tokens, latency, cost per tier, failures.</text>
  <text x="44" y="474" font-size="9" fill="#7a8399" font-family="ui-monospace, 'JetBrains Mono', Menlo, monospace">Reports and eval rows trace back to what they actually cost — no invented numbers.</text>
</svg>


</details>

Every stage appends to a usage ledger (tokens, latency, cost per tier, Tavily call
counts), so every report and every eval row can be traced back to what it actually
cost.

## Quickstart

```bash
git clone <repo> && cd mender
uv sync                                   # Python 3.12, all deps

cp .env.example .env                      # then fill in:
#   NEBIUS_API_KEY=...   (Nebius Token Factory)
#   TAVILY_API_KEY=...   (Tavily)

make test                                 # ruff + mypy strict + pytest
make demo                                 # kind cluster + 1-command incident demo

uv run mender diagnose --service checkout --namespace shop
uv run mender run      --service checkout --namespace shop \
    --workdir . --test-files demo/manifests/deploy.yaml \
    --test-command "python3 demo/app/check.py"
uv run mender eval --settle 25 --out results/$(date +%F)
```

`mender pr` then opens the PR from a finished run (mode `gh`), or `--pr-mode prepare`
writes the branch and PR body without touching GitHub.

### Demo in one command

```bash
make demo        # = demo/demo.sh
```

sets up the `kind` cluster, deploys the sample checkout service (21 invariant checks
pass), injects a chosen fault, and runs the full pipeline to a prepared PR.

### Fault catalogue

`demo/faults/<id>/fault.yaml` — 23 faults across seven categories (app bugs, probes,
configuration, secrets, resources, scheduling, services/migrations). Each declares its
apply/cleanup snippet, which files it touches, and the `expected_labels` used for
scoring, so every eval row is programmatic rather than a hand-judged pass.

## Configuration

`mender.yaml` is the single source of configuration; `.env` carries secrets (gitignored,
names only in `.env.example`).

```yaml
router:
  base_url: https://api.tokenfactory.nebius.com/v1/
  max_retries: 1            # then a typed error — no silent cross-tier fallback
  tiers:
    nano:  { model: ..., max_tokens: 8192, price: { input_per_m: ..., output_per_m: ... } }
    ultra: { ... }
    super: { ... }
tavily:
  search_depth: advanced    # max_results, timeout, retries with backoff
sandbox:
  image: python:3.12-slim   # max_retries: 3, timeout_s: 900
```

Price entries carry a `source` note. Where Nebius publishes no official table (the nano
tier), the config says so and names the third-party aggregators the figure came from —
prices are never invented.

## Model tiers

| Tier | Model | Used for | Input / Output (USD per 1M tok) |
|---|---|---|---|
| nano | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | triage: reduce raw evidence to signals and suspects | $0.06 / $0.24 — third-party aggregators, Nebius publishes no table |
| ultra | `nvidia/Nemotron-3-Ultra-550b-a55b` | root-cause report, search-query planning | $1.00 / $3.00 — models.dev |
| super | `nvidia/nemotron-3-super-120b-a12b` | patch writing and test-driven repair | $0.30 / $0.90 — models.dev |

Design points, each verified against the live API:

- **Tiering by job, not by hope** — cheap triage at high volume, expensive reasoning
  once per incident, mid-tier patch writing with a bounded repair loop.
- **No cross-tier fallback.** A failed call retries once with backoff, then raises a
  typed error. Falling back to a different tier would silently change cost and quality.
- **Nemotron models are reasoning models.** Small `max_tokens` starves the `content`
  field (reasoning eats the whole budget and the reply comes back empty), so tiers are
  configured with 8k–16k output budgets and the JSON-repair path folds an explicit
  no-reasoning nudge into the system message — the failure mode was reproduced on the
  live API and the fix verified against the exact starving prompt.
- **Every call is accounted**: tier, model, prompt/completion/reasoning tokens, latency,
  computed cost — appended to `usage.jsonl` per run.

## Tavily

Tavily is a first-class component of diagnosis, not a bolt-on search box:

1. The ultra tier proposes 1–3 queries from the triage summary and evidence.
2. All queries run in parallel-ish sequence against Tavily (`advanced` depth, bounded
   retries with backoff on 429/error).
3. Ranked results become **numbered citations** in the root-cause report
   (`[1] [2] ...` with title + URL + snippet), and the report's markdown lists every
   source.
4. The PR body repeats the sources, so a reviewer can check the web evidence without
   leaving GitHub.
5. **Degraded mode never blocks**: if Tavily fails after retries, diagnosis proceeds on
   cluster evidence alone and the report is explicitly marked
   *"Tavily search was degraded for some queries — sources may be incomplete."*
   Tavily calls are recorded in the same usage ledger (count + latency; Tavily is billed
   per search credit, plan-dependent, so no USD figure is invented for it).

## Eval harness

```bash
uv run mender eval --settle 25 --out results/2026-10-06 --work-dir runs/eval
```

runs every fault in the catalogue end-to-end: clone the repo, inject, wait for symptoms,
collect evidence, run the pipeline, verify in the sandbox, clean up — one case per fault,
with evidence isolated between cases.

Metric definitions (fixed before the first run):

- **root-cause accuracy** = cases where normalized predicted labels ∩ expected labels
  is non-empty, over cases run;
- **fix-pass rate** = cases whose sandbox tests went green within the bounded retry
  count;
- **median time-to-PR** over cases that reached a prepared PR;
- **cost per tier** summed from the ledger — `null` when any call in that tier had no
  published price (never estimated).

Raw results are committed under `results/<date>/eval-v1.json` (`schema_version:
mender-eval-v1`) with a per-fault breakdown including failures.

### Results (2026-10-06, 23-fault demo cluster, `--settle 25`, `pr_mode=prepare`)

Committed raw output: `results/2026-10-06/eval-v1.json` (`schema_version: mender-eval-v1`).

| Metric | Value |
|---|---|
| Cases run | 23 |
| Root-cause accuracy | 9/23 (0.391) |
| Fix-pass rate | 20/23 (0.870) |
| Median time-to-PR-ready | 33.8 s (n=20) |
| Nano cost USD | $0.023 (25 calls, 307,405 tok) |
| Super cost USD | $0.190 (30 calls, 456,320 tok) |
| Ultra cost USD | $0.824 (46 calls, 663,539 tok) |
| Tavily cost USD | not reported (per-credit, plan-dependent; 69 calls logged with count + latency) |

Failures (3):

- `cpu-limit-missing` — `verify-failed` (sandbox did not go green within the retry bound).
- `migration-missing-column` — `error`: `PatchError: patch path outside allowed set: demo/manifests/deploy.yaml`.
- `parse-amount-bug` — `error`: `PatchError: patch path outside allowed set: demo/manifests/deploy.yaml`.

The two `patch path outside allowed set` failures share a single cause: the model's repair patch wrote to `demo/manifests/deploy.yaml`, which is not in the fault's allowed `files` set (the fault touches migration/sql + app code). The patch was rejected by `validate_patch` before it reached the sandbox, so the case never reached verification. This is the allow-set doing its job (it stopped an out-of-scope write) but it also means the model did not propose a fix restricted to the allowed files for those two cases.

For comparison, the first full eval (same cluster, before the failure-mode fixes in commit `de04a02`) scored root-cause 7/23 (0.304) and fix-pass 18/23 (0.783), with 5 failures (4× JSONError from the runaway-reasoning loop and 1× cpu-request-too-high inject-failed). The current run's 3 failures are a different, narrower set: 1× verify-failed + 2× allow-set rejection.

## Limitations

- **Sandbox is local Docker, not Nebius.** Nebius Token Factory has no Serverless
  Jobs/Endpoints (verified: only dedicated endpoints exist), so the sandbox runs local
  Docker behind the `SandboxRunner` interface — a remote runner can drop in unchanged,
  but it is not built.
- **Root-cause scoring is label intersection**, which is deliberately strict: a report
  that names the right mechanism with unexpected label vocabulary scores as a miss.
  Expect this metric to understate semantic correctness.
- **Nemotron pricing for the nano tier is third-party sourced** — Nebius publishes no
  per-model price table. The provenance is recorded in `mender.yaml`.
- **Tavily cost is not reported in USD** because it is billed per search credit on a
  plan-dependent basis; call counts and latency are reported instead.
- **The demo cluster is a single-node kind cluster** running one sample service; the
  fault catalogue covers common failure classes but not multi-node networking,
  autoscaling, or RBAC failures.
- **Mender prepares PRs, it never merges.** Merge policy, CODEOWNERS, and required
  reviews remain entirely human.
- **Reasoning-model nondeterminism is real**: at temperature 0 the same prompt can
  still diverge into a runaway-reasoning loop occasionally; the repair path catches it,
  but a case can fail if both attempts starve.

## Development

```bash
make test        # uv run ruff check + ruff format --check + mypy + pytest
make serve       # mender serve on :8080 (GET /healthz, POST /diagnose, POST /run)
docker build -t mender .   # python:3.12-slim + kubectl
```

- `src/mender/` — package (mypy strict, fully typed)
- `demo/` — kind cluster setup, sample app, 23-fault catalogue, injection tooling
- `results/` — committed eval outputs
- `PLAN.md` — phase plan; `REVIEWS.md` — external review audit trail

## License

Apache-2.0 — see [LICENSE](LICENSE).
