## Root cause
The ConfigMap 'checkout-config' contains an incorrect db_host value 'orders-db.default.svc.cluster.local' instead of the required 'orders-db.shop.svc.cluster.local', causing the /healthz endpoint to return HTTP 500, which fails both liveness and readiness probes and triggers repeated container restarts (exit code 137 = SIGKILL from kubelet after liveness probe failure threshold).

## Mechanism
1. The deployment's checkout container reads DB_HOST from checkout-config via configMapKeyRef at pod creation. 2. The new ReplicaSet checkout-687c777bc5 (pod checkout-687c777bc5-h5ccr) receives the wrong value 'orders-db.default.svc.cluster.local' [from ConfigMap manifest]. 3. The service's healthcheck() validates that db_host ends with '.shop.svc.cluster.local' [service.py healthcheck logic]; the mismatch makes it return (500, 'db host outside cluster domain'). 4. Both livenessProbe and readinessProbe are HTTP GET /healthz on port 8080 [describe probe config]. 5. Probes receive 500, exceeding failureThreshold (3) [events: 'Liveness probe failed: HTTP probe failed with statuscode: 500']. 6. Kubelet kills the container (SIGKILL, exit code 137) and restarts it [event: 'Container checkout failed liveness probe, will be restarted'; container Last State Reason: Error, Exit Code: 137]. 7. Restart repeats the same failure because the env var is unchanged.

Confidence: 0.95 · Labels: configmap_error, probe_failure, healthcheck_failure, wrong_db_host, liveness_probe_failure

## Evidence relied on
- ConfigMap manifest: db_host: orders-db.default.svc.cluster.local
- service.py EXPECTED_DB_SUFFIX = '.shop.svc.cluster.local' and healthcheck returns 500 on suffix mismatch
- Failing pod log: 'starting checkout service (log_level=info, db=orders-db.default.svc.cluster.local, cache=96Mi)' followed by 500 responses
- Working pod logs show db=orders-db.shop.svc.cluster.local and 200 responses
- Events: 'Liveness probe failed: HTTP probe failed with statuscode: 500' and 'Container checkout failed liveness probe, will be restarted'
- Container Last State: Reason: Error, Exit Code: 137

## Change
Files: demo/manifests/configmap.yaml
Rationale: The ConfigMap 'checkout-config' contains an incorrect db_host value 'orders-db.default.svc.cluster.local' instead of the required 'orders-db.shop.svc.cluster.local'. This causes the healthcheck to fail with HTTP 500, leading to liveness and readiness probe failures and container restarts. Updating the db_host to the correct value ensures the service can connect to the database and passes healthchecks.

## Sandbox test results
Command: `python3 demo/app/check.py` — **PASSED** in 1 attempt(s)
- attempt 1: exit 0 in 0.7s — ok

## Tavily sources used
Queries: Kubernetes exit code 137 OOMKilled container memory limit 512Mi startup cache 96Mi; healthcheck returns 500 when DB_HOST suffix mismatch expected cluster domain .shop.svc.cluster.local; liveness probe readiness probe /healthz HTTP 500 failure threshold restart loop Kubernetes
- Fix OOMKilled Containers in Kubernetes | K8s Recipes: https://kubernetes.recipes/recipes/troubleshooting/oom-killed-troubleshooting
- Exit Code 137 - Fixing OOMKilled Kubernetes Error: https://spacelift.io/blog/oomkilled-exit-code-137
- OOMKilled (Exit Code 137): Causes and Fix | Kubernetes | DevOpsLesson: https://devopslesson.com/troubleshooting/oomkilled
- OOMKilled (Exit Code 137): Causes and How to Fix It: https://cast.ai/blog/oomkilled-exit-code-137
- Kubernetes OOMKilled: How to Diagnose and Fix It: https://www.plural.sh/blog/kubernetes-oomkilled-how-to-diagnose-and-fix-it
- Health_check/migrations failing in 18.7.1 - Upgrade: https://forum.gitlab.com/t/health-check-migrations-failing-in-18-7-1/132265
- TLS name mismatch error: https://community.cloudflare.com/t/tls-name-mismatch-error/137544
- HealthCheck returns 500 on unhealthy result · Issue #766: https://github.com/dropwizard/metrics/issues/766
- How to Troubleshoot DNS Resolution in Kubernetes Pods: https://oneuptime.com/blog/post/2026-03-20-troubleshoot-dns-kubernetes/view
- Kubernetes http health check not working as expected: https://stackoverflow.com/questions/66064514/kubernetes-http-health-check-not-working-as-expected-500-response-is-ignored
- Kubernetes Liveness and Readiness Probes Guide | K8s Recipes: https://kubernetes.recipes/recipes/deployments/kubernetes-probes-liveness-readiness
- Liveness, Readiness, and Startup Probes | Kubernetes: https://kubernetes.io/docs/concepts/workloads/pods/probes
- Troubleshooting Kubernetes Liveness and Readiness Probe Failures: https://resolve.ai/glossary/how-to-debug-kubernetes-probe-issues
- Configure Liveness, Readiness and Startup Probes | Kubernetes: https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes
- GitHub - iam-rayees/Kubernetes-Health-Probes: Practical Kubernetes guide demonstrating Readiness, Liveness, and Startup probes to build resilient, self-healing, production-ready containerized applications. · GitHub: https://github.com/iam-rayees/Kubernetes-Health-Probes

## How this was verified
Tests ran in an isolated container (`docker run --rm --network none`), replaying the sandbox command above. Evidence captured at 2026-10-06T17:04:12+00:00.

---
Opened by Mender for human review. Do not auto-merge; a person must review and merge this PR.