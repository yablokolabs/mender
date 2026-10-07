## Root cause
The ConfigMap 'checkout-config' contains an incorrect db_host value 'orders-db.default.svc.cluster.local' instead of the required 'orders-db.shop.svc.cluster.local', causing the application's /healthz endpoint to return HTTP 500, which fails both liveness and readiness probes and triggers a continuous restart loop.

## Mechanism
1. The checkout-config ConfigMap defines db_host=orders-db.default.svc.cluster.local [from manifests/configmap.yaml]. 2. The application's healthcheck() function validates that db_host ends with '.shop.svc.cluster.local' and returns HTTP 500 with error 'db host outside cluster domain' when it does not [from demo/app/service.py]. 3. The failing pod's logs show it starts with 'db=orders-db.default.svc.cluster.local' and all /healthz requests return 500, while healthy pods use 'db=orders-db.shop.svc.cluster.local' and return 200 [from LOGS]. 4. Both livenessProbe and readinessProbe are configured to HTTP GET /healthz on port 8080 [from DESCRIBE probes]. 5. Probe failures (statuscode 500) are recorded in events at 5s and 4s ago [from EVENTS]. 6. Kubernetes kills the container due to liveness probe failure (exit code 137 = SIGKILL from probe termination, not OOM) and restarts it, but the new container inherits the same wrong ConfigMap value, repeating the failure [from EVENTS and container Last State].

Confidence: 0.95 · Labels: configmap_error, wrong_db_host, probe_failure, restart_loop, healthcheck_validation

## Evidence relied on
- db_host: orders-db.default.svc.cluster.local (configmap.yaml)
- EXPECTED_DB_HOST = "orders-db.shop.svc.cluster.local" (check.py)
- healthcheck returns 500 when db_host suffix mismatches (service.py)
- failing pod log: db=orders-db.default.svc.cluster.local -> 500 (LOGS)
- healthy pod log: db=orders-db.shop.svc.cluster.local -> 200 (LOGS)
- Liveness probe failed: HTTP probe failed with statuscode: 500 (EVENTS)
- Readiness probe failed: HTTP probe failed with statuscode: 500 (EVENTS)
- Container killed due to liveness probe failure, exit code 137 (EVENTS, DESCRIBE)

## Change
Files: demo/manifests/configmap.yaml
Rationale: The ConfigMap 'checkout-config' contains an incorrect db_host value 'orders-db.default.svc.cluster.local' instead of the required 'orders-db.shop.svc.cluster.local'. This causes the application's healthcheck to fail because it validates that db_host ends with '.shop.svc.cluster.local'. Changing the db_host value to the correct one will allow the healthcheck to pass, resolving the liveness and readiness probe failures and the restart loop.

## Sandbox test results
Command: `python3 demo/app/check.py` — **PASSED** in 1 attempt(s)
- attempt 1: exit 0 in 0.7s — ok

## Tavily sources used
Queries: Kubernetes OOM kill exit code 137 memory limit 512Mi startup cache 96Mi checkout service; Kubernetes liveness probe readiness probe HTTP 500 /healthz configmap DB_HOST misconfiguration orders-db.default.svc.cluster.local; Kubernetes pod OOM killed after single restart memory limit insufficient probe failure 500
- Kubernetes Optimization: Tutorial and Best Practices: https://www.cloudbolt.io/kubernetes-cost-optimization/kubernetes-optimization
- How to Optimize Kubernetes Pod Startup Time: https://oneuptime.com/blog/post/2026-01-19-kubernetes-optimize-pod-startup-time/view
- OOm Pte Ltd Technology Stack | OOm Pte Ltd Technology Profile: https://rocketreach.co/oom-pte-ltd-technology-stack_b5cc9ea4f42e0a88
- Kubernetes Resource Optimization: 5 Proven Strategies for 2025: https://scaleops.com/blog/5-kubernetes-resource-optimization-strategies-that-work-in-production
- Introducing containers  |  Google Kubernetes Engine (GKE)  |  Google Cloud Documentation: https://docs.cloud.google.com/kubernetes-engine/docs/learn/containers
- Liveness, Readiness, and Startup Probes | Kubernetes: https://kubernetes.io/docs/concepts/workloads/pods/probes
- Kubernetes Probes — Health Checks | by Duy Hưng | Medium: https://medium.com/@tdhtp2016/kubernetes-probes-health-checks-0c9a769724c0
- Kubernetes Liveness and Readiness Probes Guide | K8s Recipes: https://kubernetes.recipes/recipes/deployments/kubernetes-probes-liveness-readiness
- Troubleshooting Kubernetes Liveness and Readiness Probe Failures: https://resolve.ai/glossary/how-to-debug-kubernetes-probe-issues
- Configure Liveness, Readiness and Startup Probes | Kubernetes: https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes
- Why Pods Get OOMKilled in Kubernetes (And Why Memory Limits Won’t Save You): https://medium.com/@pillarslive/why-pods-get-oomkilled-in-kubernetes-and-why-memory-limits-wont-save-you-5891b8f338ea
- Kubernetes scheduler liveness probe fails during OOM conditions preventing automatic restart · apache/airflow · Discussion #53662 · GitHub: https://github.com/apache/airflow/discussions/53662
- CrashLoopBackOff in Kubernetes: Causes and Fixes: https://cast.ai/blog/crashloopbackoff
- Kube-probe Liveness probe failed: HTTP 500: https://drdroid.io/stack-diagnosis/kube-probe-liveness-probe-failed--http-500
- 5 Ways You Can Diagnose & Prevent OOMKilled Errors in Kubernetes: https://www.fairwinds.com/blog/5-ways-you-can-diagnose-and-prevent-oomkilled-errors-in-kubernetes

## How this was verified
Tests ran in an isolated container (`docker run --rm --network none`), replaying the sandbox command above. Evidence captured at 2026-10-06T19:29:05+00:00.

---
Opened by Mender for human review. Do not auto-merge; a person must review and merge this PR.