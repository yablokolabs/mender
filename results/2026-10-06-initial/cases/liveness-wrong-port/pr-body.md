## Root cause
The liveness probe is configured to check port 9090, but the container only exposes port 8080 and the application only listens on port 8080.

## Mechanism
1. Deployment manifest specifies livenessProbe.httpGet.port=9090 [deploy.yaml]. 2. Container spec declares only containerPort 8080 (named 'http') [describe pods]. 3. Application code binds HTTP server to 0.0.0.0:8080 only [service.py]. 4. Kubelet executes liveness probe against podIP:9090/healthz. 5. TCP connection refused because no process listens on 9090 [events: 'dial tcp 10.244.0.51:9090: connect: connection refused']. 6. After failureThreshold=3 failures, kubelet kills and restarts the container [events: 'Container checkout failed liveness probe, will be restarted']. 7. New pod starts with same misconfiguration → infinite restart loop [11].

Confidence: 0.95 · Labels: probe_config, port_mismatch, liveness_probe, restart_loop, connection_refused

## Evidence relied on
- Liveness probe failed: Get "http://10.244.0.51:9090/healthz": dial tcp 10.244.0.51:9090: connect: connection refused
- Liveness: http-get http://:9090/healthz delay=5s timeout=1s period=10s
- Port: 8080/TCP (http)
- livenessProbe: httpGet: path: /healthz port: 9090
- ThreadingHTTPServer(("0.0.0.0", 8080), Handler)
- The liveness probe references a port that is not declared in the container ports array [11]

## Change
Files: demo/manifests/deploy.yaml
Rationale: The liveness probe was incorrectly targeting port 9090 while the container only exposes port 8080 (named 'http'). Changing the livenessProbe port to 'http' aligns it with the container's actual listening port, preventing connection refused errors and the resulting restart loop.

## Sandbox test results
Command: `python3 demo/app/check.py` — **PASSED** in 1 attempt(s)
- attempt 1: exit 0 in 0.7s — ok

## Tavily sources used
Queries: Kubernetes liveness probe port mismatch container port 8080 connection refused; Kubernetes probe configuration error wrong port number liveness readiness; containerPort 8080 livenessProbe port 9090 misconfiguration documented issues
- Troubleshooting Kubernetes Liveness and Readiness Probe Failures: https://resolve.ai/glossary/how-to-debug-kubernetes-probe-issues
- Kubernetes liveness probe fails with "connection refused ...: https://www.reddit.com/r/kubernetes/comments/e94rae/kubernetes_liveness_probe_fails_with_connection
- Liveness probe failed connection refused - SUSE Rancher Prime - SUSE: https://forums.suse.com/t/liveness-probe-failed-connection-refused/20837
- Elastic pod is not Ready: Readiness probe failed: nc: connect to 127.0.0.1 port 8080 (tcp) failed: Connection refused - Elasticsearch - Discuss the Elastic Stack: https://discuss.elastic.co/t/elastic-pod-is-not-ready-readiness-probe-failed-nc-connect-to-127-0-0-1-port-8080-tcp-failed-connection-refused/368853
- Kubernetes Liveness Probes: Configuration & Best Practices: https://www.groundcover.com/blog/kubernetes-liveness-probe
- Troubleshooting Kubernetes Liveness and Readiness Probe Failures: https://resolve.ai/glossary/how-to-debug-kubernetes-probe-issues
- aks kube-system readiness liveness probe keep failing - Microsoft Q&A: https://learn.microsoft.com/en-us/answers/questions/2279482/aks-kube-system-readiness-liveness-probe-keep-fail
- Configure Liveness, Readiness and Startup Probes | Kubernetes: https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes
- Kubernetes liveness probe fails with "connection refused ...: https://www.reddit.com/r/kubernetes/comments/e94rae/kubernetes_liveness_probe_fails_with_connection
- Liveness, Readiness, and Startup Probes | Kubernetes: https://kubernetes.io/docs/concepts/workloads/pods/probes
- KA-B009: Liveness probe port not in container ports: https://patrykgolabek.dev/tools/k8s-analyzer/rules/ka-b009
- How to Configure Liveness and Readiness Probes Properly: https://oneuptime.com/blog/post/2026-01-24-kubernetes-liveness-readiness-probes/view
- Troubleshooting Kubernetes Liveness and Readiness Probe Failures: https://resolve.ai/glossary/how-to-debug-kubernetes-probe-issues
- Configure Liveness, Readiness and Startup Probes | Kubernetes: https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes
- How to Configure Kubernetes Liveness Probes Without Causing Restart Loops · MeteorOps: https://meteorops.com/blog/how-to-configure-kubernetes-liveness-probes-without-causing-restart-loops

## How this was verified
Tests ran in an isolated container (`docker run --rm --network none`), replaying the sandbox command above. Evidence captured at 2026-10-06T17:12:56+00:00.

---
Opened by Mender for human review. Do not auto-merge; a person must review and merge this PR.