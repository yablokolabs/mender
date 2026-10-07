## Root cause
The Kubernetes secret 'checkout-secrets' key 'secret_key' was set to a 5-character value ('short'), but the application validates that SECRET_KEY must be at least 32 characters (MIN_SECRET_LENGTH=32) on startup.

## Mechanism
1) The secret 'checkout-secrets' was updated with secret_key='short' (5 chars) [secret.yaml]. 2) A new deployment created ReplicaSet checkout-7f7d45d5c8 (different pod-template-hash than the two healthy pods). 3) New pod checkout-7f7d45d5c8-2d9bz starts, reads SECRET_KEY from the secret via env ref. 4) Application's require_environment() validates length >=32, fails, logs 'FATAL: SECRET_KEY too short (5 < 32 chars)' and exits with code 1 [logs, service.py]. 5) Kubernetes restarts container with back-off, but secret unchanged, causing CrashLoopBackOff [events, pod describe]. The two older pods (ReplicaSet 56655c8669) continue running because they started with the previous valid secret value; Kubernetes does not automatically restart pods when secrets change [12,13].

Confidence: 0.95 · Labels: secret_too_short, secret_validation, crashloopbackoff, deployment_rollback_needed, secret_rotation

## Evidence relied on
- FATAL: SECRET_KEY too short (5 < 32 chars)
- secret_key: "short"
- if len(secret) < MIN_SECRET_LENGTH: raise ConfigError(f"SECRET_KEY too short ({len(secret)} < {MIN_SECRET_LENGTH} chars)")
- assert len(value) >= 32, f"secret_key too short ({len(value)} < 32 chars)"
- pod-template-hash=7f7d45d5c8 vs 56655c8669
- Back-off restarting failed container

## Change
Files: demo/manifests/secret.yaml
Rationale: The secret_key value was only 5 characters, violating the application's minimum length requirement of 32 characters. Updated the secret to a 41-character placeholder value to satisfy the validation while keeping the demo nature of the value.

## Sandbox test results
Command: `python3 demo/app/check.py` — **PASSED** in 1 attempt(s)
- attempt 1: exit 0 in 0.6s — ok

## Tavily sources used
Queries: Kubernetes pod CrashLoopBackOff secret validation failure SECRET_KEY too short; application startup fatal error secret length validation 32 characters minimum; Kubernetes secret key value too short causing container restart loop
- How to Fix CrashLoopBackOff in Kubernetes? - Komodor: https://komodor.com/learn/how-to-fix-crashloopbackoff-kubernetes-error
- Why 80% of Kubernetes CrashLoopBackOff Errors Come ...: https://blog.stackademic.com/why-80-of-kubernetes-crashloopbackoff-errors-come-from-the-same-5-mistakes-52cd62040046
- Debug a CrashLoopBackOff in Kubernetes: 2026 Fix Guide: https://khimananda.com/blog/debug-a-crashloopbackoff-in-kubernetes
- How to Debug CrashLoopBackOff in Kubernetes: https://www.youtube.com/watch?v=U8Fu2kgSdyo
- What is Kubernetes CrashLoopBackOff? And how to fix it | Sysdig: https://www.sysdig.com/blog/debug-kubernetes-crashloopbackoff
- Client Secret Minimum Length Enforcement in ... - ServiceNow: https://support.servicenow.com/kb?id=kb_article_view&sysparm_article=KB2630413
- Invalid storage secret key length, must be 32 characters ...: https://userapps.support.sap.com/sap/support/knowledge/en/3799444
- security: JWT SECRET_KEY minimum-length requirement is ...: https://github.com/Chetan0e/Verath/issues/235
- As of 2405: Increasing the Minimum Character Length for ...: https://help.sap.com/docs/SAP_CPQ/abe5bf645c9542a5bd4cbfdcc1a4876c/82bc326be16840218f22c840d8afd905.html
- `Secret key for encrypting tokens should be 32 characters ...: https://github.com/quarkusio/quarkus/issues/33532
- Kubernetes Pod Restart Reasons: How to Troubleshoot: https://edgedelta.com/company/knowledge-center/kubernetes-pod-restart-reasons-explained
- Reload, when secret has changed : r/kubernetes: https://www.reddit.com/r/kubernetes/comments/1hco0ge/reload_when_secret_has_changed
- Restart Pods When Secret Changes in Kubernetes: https://docs.stakater.com/reloader/1.4/how-to-guides/restart-pods-when-secret-changes.html
- Understanding the ‘Back-Off Restarting Failed Container’ Error in Kubernetes – IT Exams Training – Pass4Sure: https://www.pass4sure.com/blog/understanding-the-back-off-restarting-failed-container-error-in-kubernetes
- Kubernetes Secrets and Pod Restarts: How to Reload Secrets Safely: https://blog.ascendingdc.com/blog/kubernetes-secrets-and-pod-restarts

## How this was verified
Tests ran in an isolated container (`docker run --rm --network none`), replaying the sandbox command above. Evidence captured at 2026-10-06T19:57:02+00:00.

---
Opened by Mender for human review. Do not auto-merge; a person must review and merge this PR.