## Root cause
The healthcheck endpoint (/healthz) returns HTTP 500 because the application's healthcheck logic incorrectly rejects the valid DB_HOST value (orders-db.shop.svc.cluster.local) as 'outside cluster domain' when it actually ends with the expected suffix (.shop.svc.cluster.local). This bug exists in the new ReplicaSet (pod-template-hash=76bd4cbff7) but not in the old one (9bd4d689f), as evidenced by different image SHAs.

## Mechanism
1. New ReplicaSet 76bd4cbff7 rolls out with a buggy healthcheck: the condition `if db_host.endswith(EXPECTED_DB_SUFFIX):` should be negated, so a correct DB_HOST triggers a 500 response. 2. Liveness probe (delay=5s, period=10s, failureThreshold=3) and readiness probe (delay=2s, period=5s, failureThreshold=3) both hit /healthz and receive 500. 3. After three consecutive liveness failures (~30s), kubelet kills the container (SIGKILL, exit code 137, Reason: Error) and restarts it — the 'OOMKilled' label in triage is a mischaracterization; exit 137 here is from probe-driven kill, not memory pressure. 4. The replacement container runs the same buggy image, so probes continue to fail, leaving the pod stuck at 0/1 Ready while the two healthy pods on the old ReplicaSet serve 200.

Confidence: 0.95 · Labels: probe_config, image_tag, healthcheck_bug, rolling_deployment

## Evidence relied on
- healthcheck code: `if db_host.endswith(EXPECTED_DB_SUFFIX): problems.append(...)` — inverted logic
- logs: failing pod shows repeated 'GET /healthz HTTP/1.1" 500 -' while healthy pods show 200
- events: 'Container checkout failed liveness probe, will be restarted' at 55s ago
- describe: failing pod Last State Reason=Error Exit Code=137; healthy pods Ready=True
- image IDs differ: failing pod sha256:2a5097d2... vs healthy pods sha256:4c1ea449...
- probe config: liveness/readiness both HTTP GET /healthz with low thresholds

## Change
Files: demo/app/service.py
Rationale: The healthcheck function incorrectly treats a DB_HOST ending with the expected suffix as invalid. The condition should be negated so that a DB_HOST not ending with the suffix is considered invalid. This change ensures the valid DB_HOST (orders-db.shop.svc.cluster.local) passes the healthcheck, returning 200 instead of 500.

## Sandbox test results
Command: `python3 demo/app/check.py` — **PASSED** in 1 attempt(s)
- attempt 1: exit 0 in 0.8s — ok

## Tavily sources used
Queries: Kubernetes OOM kill exit code 137 memory limit 512Mi startup cache 96Mi pod restart; Kubernetes liveness probe readiness probe HTTP 500 /healthz checkout service memory pressure; Kubernetes pod continuous 500 healthz probe failures after OOM kill memory limit insufficient
- Exit Code 137 in Kubernetes: Causes, Diagnosis, and Fixes: https://middleware.io/blog/exit-code-137-in-kubernetes-causes-diagnosis-fixes
- What Exit Code 137 means for Kubernetes | Refine: https://refine.dev/blog/kubernetes-exit-code-137
- Exit Code 137 in Kubernetes: Causes & Fixes (2026): https://www.nudgebee.com/resources/blog/fixing-exit-code-137-pod-termination-kubernetes
- Kubernetes OOMKilled and Exit Code 137: Fix Guide | Webalert: https://web-alert.io/blog/kubernetes-oomkilled-exit-code-137-memory-limits-guide
- Exit Code 137 - Fixing OOMKilled Kubernetes Error: https://spacelift.io/blog/oomkilled-exit-code-137
- Creating Kubernetes liveness and readiness probes | Opensource.com: https://opensource.com/article/18/3/kubernetes-liveness-readiness-probes
- Kubernetes Probes Liveness Readiness | K8s Recipes: https://kubernetes.recipes/recipes/deployments/kubernetes-liveness-readiness-startup-probes
- Kubernetes Probes: Readiness, Liveness, and Startup Checks | by E Behrangi | Medium: https://medium.com/@elahe.behrangi/beginners-guide-to-kubernetes-probes-readiness-liveness-and-startup-checks-10731bac57d6
- Kubernetes — Liveness and Readiness Probes — Difference: https://medium.com/@AADota/kubernetes-liveness-and-readiness-probes-difference-1b659c369e17
- Kubernetes Readiness, Liveness and Startup Probes | Cloudiaries: https://cloudiaries.com/posts/kubernetes-readiness-liveness-startup-probes
- Kubernetes scheduler liveness probe fails during OOM conditions preventing automatic restart · apache/airflow · Discussion #53662 · GitHub: https://github.com/apache/airflow/discussions/53662
- CrashLoopBackOff in Kubernetes: Causes and Fixes: https://cast.ai/blog/crashloopbackoff
- Kubernetes OOMKilled out of memory diagnosis: https://www.dynatrace.com/news/blog/kubernetes-oomkilled-out-of-memory-troubleshooting
- Troubleshooting Kubernetes Liveness and Readiness Probe Failures: https://resolve.ai/glossary/how-to-debug-kubernetes-probe-issues
- Troubleshoot OOMKilled errors in AKS clusters - Azure | Microsoft Learn: https://learn.microsoft.com/en-us/troubleshoot/azure/azure-kubernetes/availability-performance/troubleshoot-oomkilled-aks-clusters

## How this was verified
Tests ran in an isolated container (`docker run --rm --network none`), replaying the sandbox command above. Evidence captured at 2026-10-06T17:08:50+00:00.

---
Opened by Mender for human review. Do not auto-merge; a person must review and merge this PR.