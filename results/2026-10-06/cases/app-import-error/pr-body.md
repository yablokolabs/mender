## Root cause
Python SyntaxError: 'from __future__ import annotations' appears after a docstring and an import statement in service.py, violating the rule that __future__ imports must be at the very beginning of the file [1].

## Mechanism
1. The failing pod (checkout-86d87b9fd5-7bgxc) pulls image digest 4132451ca440... which contains the broken service.py. 2. On container start, Python parses service.py and immediately raises 'SyntaxError: from __future__ imports must occur at the beginning of the file' (see logs). 3. The container exits with code 1. 4. Kubernetes' default restartPolicy (Always) triggers a restart with exponential backoff, producing the CrashLoopBackOff status [7]. 5. The two healthy pods run a newer image digest (4c1ea44931b8...) where the import has been fixed, so they stay Running.

Confidence: 0.95 · Labels: syntax_error, late_future_import, crashloopbackoff, image_version_mismatch

## Evidence relied on
- File "/app/service.py", line 10\n    from __future__ import annotations\n    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nSyntaxError: from __future__ imports must occur at the beginning of the file
- service.py shows: 'import kubernetes_asyncio\n"""Checkout demo service...\n"""\nfrom __future__ import annotations' — import precedes the __future__ statement
- [1] Ruff rule late-future-import (F404): '__future__ imports must be placed the beginning of the file, before any other statements (apart from docstrings)'

## Change
Files: demo/app/service.py
Rationale: The __future__ import must be at the very beginning of the file. Moving it to the first line resolves the SyntaxError while preserving all other functionality.

## Sandbox test results
Command: `python3 demo/app/check.py` — **PASSED** in 2 attempt(s)
- attempt 1: exit 1 in 0.7s — failed
- attempt 2: exit 0 in 0.7s — ok

## Tavily sources used
Queries: Python SyntaxError "from __future__ imports must occur at the beginning of the file" Kubernetes container crash loop; Kubernetes CrashLoopBackOff Python syntax error container startup failure; containerd Kubernetes pod restart loop exit code 1 Python import error
- late-future-import (F404) | Ruff: https://docs.astral.sh/ruff/rules/late-future-import
- [Python] SyntaxError: from __future__ imports must occur at the beginning of the file · Issue #4600 · microsoft/kiota · GitHub: https://github.com/microsoft/kiota/issues/4600
- `SyntaxError: from __future__ imports must occur ...: https://github.com/koxudaxi/datamodel-code-generator/issues/2079
- "SyntaxError: from __future__ imports must occur at the beginning of the file" after comments · Issue #385 · agronholm/typeguard · GitHub: https://github.com/agronholm/typeguard/issues/385
- from __future__ imports must occur at the beginning of the file: https://github.com/maxpumperla/hyperas/issues/157
- What is Kubernetes CrashLoopBackOff? And how to fix it | Sysdig: https://www.sysdig.com/blog/debug-kubernetes-crashloopbackoff
- Kubernetes CrashLoopBackOff Error: Common Causes & Solutions · Dash0: https://www.dash0.com/guides/kubernetes-crashloopbackoff
- Kubernetes CrashLoopBackOff Errors: 6 Causes and Fixes | OpManager Nexus: https://www.manageengine.com/it-operations-management/tech-topics/kubernetes-crashloopbackoff-errors.html
- Understanding Kubernetes CrashLoopBackOff & How to Fix It: https://www.groundcover.com/kubernetes-troubleshooting/crashloopbackoff
- Kubernetes Most Occurred Issue | CrashLoopBackOff: https://aws.plainenglish.io/kubernetes-most-occurred-issue-crashloopbackoff-cc107a48d0c0
- ⎈ A Hands-On Guide to Kubernetes Exit Codes: Simulate and Fix ⚙️ | by Anvesh Muppeda | Medium: https://medium.com/@muppedaanvesh/a-hands-on-guide-to-kubernetes-exit-codes-simulate-and-fix-%EF%B8%8F-f2ad57d3cdca
- Kubernetes Exit Code 1 (SIGTERM): Causes and Troubleshooting · Dash0: https://www.dash0.com/guides/kubernetes-exit-code-1-sigterm-causes-and-troubleshooting
- Kubernetes Terminated with exit code 1 error | Refine: https://refine.dev/blog/kubernetes-terminated-with-exit-code-1
- Pod In CrashLoopBackOff State – Runbooks: https://containersolutions.github.io/runbooks/posts/kubernetes/crashloopbackoff
- Kubernetes CrashLoopBackOff: Causes & Quick Fixes | Netdata: https://www.netdata.cloud/academy/kubernetes-crash-loop-backoff

## How this was verified
Tests ran in an isolated container (`docker run --rm --network none`), replaying the sandbox command above. Evidence captured at 2026-10-06T19:11:52+00:00.

---
Opened by Mender for human review. Do not auto-merge; a person must review and merge this PR.