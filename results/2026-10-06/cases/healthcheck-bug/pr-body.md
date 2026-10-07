## Root cause
Mutable image tag 'mender-demo-app:1.0.0' was re-pushed with a defective image (different digest), causing OOM kills and health check failures in new pods.

## Mechanism
1. A new image was pushed to the same tag '1.0.0' (mutable tag) [10]. 2. The deployment controller created a new ReplicaSet (c65dc45c5) for the new pods. 3. The new pod (checkout-c65dc45c5-l6lgj) pulled the new image (digest 2a5097d2...) while healthy pods run the old image (digest ccb3f7a1...). 4. The defective image has a memory leak or higher memory usage, causing the container to exceed its 512Mi limit and be OOM-killed (exit code 137) [1,2,3,4]. 5. After restart, the health check endpoint (/healthz) returns HTTP 500 (seen in logs at 19:33:13 onward), causing liveness/readiness probes to fail and the pod to enter a crash loop.

Confidence: 0.95 · Labels: mutable_image_tag, oomkilled, health_check_failure, bad_build, rollout_issue

## Evidence relied on
- Pods: checkout-c65dc45c5-l6lgj image ID docker.io/library/import-2026-10-06@sha256:2a5097d2a4012dd813ff65e860088a033cfaea88d1e84ca5612f4cfec372b40a vs healthy pods ccb3f7a1370ed210fd016076ff906af182ead91d86a5e0ebf2a14f0ed5538f20
- Events: Container checkout failed liveness probe, will be restarted; Liveness probe failed: HTTP probe failed with statuscode: 500
- Logs: healthz requests return 200 then after restart return 500
- Search result [10]: Two Pods. Same Tag. Different Code. Here's How We Caught It
- Search result [9]: mutable tag problem and rollout undo

## Change
Files: demo/app/service.py
Rationale: The root cause was a defective image that had both a memory leak and an inverted healthcheck logic (returning 500 for healthy db_host). Since only the service.py file can be modified, the fix corrects the healthcheck condition: change `if db_host.endswith(EXPECTED_DB_SUFFIX):` to `if not db_host.endswith(EXPECTED_DB_SUFFIX):`. This ensures healthy pods return 200 on /healthz, preventing unnecessary crash loops due to probe failures. While the memory leak remains, addressing the healthcheck restores correct probe behavior and is the minimal change possible within the allowed files.

## Sandbox test results
Command: `python3 demo/app/check.py` — **PASSED** in 1 attempt(s)
- attempt 1: exit 0 in 0.6s — ok

## Tavily sources used
Queries: Kubernetes pod OOM exit code 137 memory limit request mismatch healthcheck failure; Kubernetes deployment partial rollout same image tag different digest healthcheck 500; Application healthcheck logic inverted condition database hostname endswith suffix returns 500
- Exit Code 137: Causes & Best Practices to Prevent It: https://www.groundcover.com/kubernetes-troubleshooting/exit-code-137
- Kubernetes Exit Code 137: Root Causes and How to Fix It: https://www.plural.sh/blog/kubernetes-exit-code-137
- Kubernetes OOMKilled Error: How to Fix & Tips for Preventing It · Dash0: https://www.dash0.com/guides/kubernetes-oomkilled-error-how-to-fix-and-tips-for-preventing-it
- Exit Code 137 - Fixing OOMKilled Kubernetes Error: https://spacelift.io/blog/oomkilled-exit-code-137
- Kubernetes OOMKilled: Fix Memory Limit Issues & Exit Code 137 | K8s Troubleshooting Tutorial: https://www.youtube.com/watch?v=JLw_pHLCN4Y
- Purpose of image digest injection in pods? : r/kubernetes: https://www.reddit.com/r/kubernetes/comments/1nxqeuu/purpose_of_image_digest_injection_in_pods
- Deployment gets restarted with old image tag · Issue #95703: https://github.com/kubernetes/kubernetes/issues/95703
- How to ensure consistent Kubernetes container versions - Gremlin: https://www.gremlin.com/blog/kubernetes-container-image-version-uniformity
- How to Fix kubectl rollout undo When Mutable Tags Restore the Bad Build: https://oneuptime.com/blog/post/2026-09-26-rollout-undo-mutable-image-tag-bad-build/view
- Two Pods. Same Tag. Different Code. Here's How We ...: https://pub.towardsai.net/two-pods-same-tag-different-code-heres-how-we-caught-it-45ef7338802e
- Why does the Health Check Service returns 500?: https://community.progress.com/s/article/health-check-service-returns-500
- HealthCheck returns 500 on unhealthy result · Issue #766 · dropwizard/metrics · GitHub: https://github.com/dropwizard/metrics/issues/766
- An Internal Error Has Occurred Error 500 - Installation Issues - Passbolt community forum: https://community.passbolt.com/t/an-internal-error-has-occurred-error-500/4949
- Target Group Health Check is Healthy, but has 500 error. | AWS re:Post: https://repost.aws/questions/QUYcChsS9MSkCmPHTZQMnIqg/target-group-health-check-is-healthy-but-has-500-error
- Health Check Endpoint - Customer Support - NetX: https://support.netx.net/hc/en-us/articles/18234645275671-Health-Check-Endpoint

## How this was verified
Tests ran in an isolated container (`docker run --rm --network none`), replaying the sandbox command above. Evidence captured at 2026-10-06T19:33:32+00:00.

---
Opened by Mender for human review. Do not auto-merge; a person must review and merge this PR.