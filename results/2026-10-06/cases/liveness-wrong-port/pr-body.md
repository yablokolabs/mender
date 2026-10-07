## Root cause
Liveness probe configured with port 9090 but container only exposes port 8080

## Mechanism
1. Deployment spec defines livenessProbe.httpGet.port=9090 [deploy.yaml]. 2. Container spec declares only one port: containerPort=8080 named 'http' [deploy.yaml]. 3. Application serves /healthz on port 8080 (logs show 200 responses on :8080/healthz). 4. Kubelet starts liveness probe after initialDelaySeconds=5s targeting podIP:9090/healthz. 5. Connection refused because no process listens on 9090 [events: 'dial tcp 10.244.0.119:9090: connect: connection refused']. 6. After failureThreshold=3 failures, kubelet kills container and restarts it [events: 'Container checkout failed liveness probe, will be restarted']. 7. Cycle repeats causing crash loop. Readiness probe works because it uses named port 'http' which resolves to 8080 [pod describe: readiness=http://:http/healthz].

Confidence: 0.95 · Labels: probe_config, port_mismatch, liveness_probe, crash_loop

## Evidence relied on
- Liveness probe failed: Get "http://10.244.0.119:9090/healthz": dial tcp 10.244.0.119:9090: connect: connection refused
- Liveness: http-get http://:9090/healthz delay=5s timeout=1s period=10s
- Port: 8080/TCP (http)
- livenessProbe: httpGet: path: /healthz port: 9090
- 06/Oct/2026 19:37:36 - "GET /healthz HTTP/1.1" 200 -

## Change
Files: demo/manifests/deploy.yaml
Rationale: The liveness probe was configured to target port 9090, but the container only exposes port 8080 (named 'http'). Changing the livenessProbe port to the named port 'http' ensures it probes the correct port where the application serves /healthz, aligning with the readiness probe and preventing connection refused errors.

## Sandbox test results
Command: `python3 demo/app/check.py` — **PASSED** in 1 attempt(s)
- attempt 1: exit 0 in 0.7s — ok

## Tavily sources used
Queries: Kubernetes liveness probe connection refused port mismatch container port; Kubernetes probe httpGet port configuration named port vs numeric port; Kubernetes pod restart loop liveness probe failure connection refused
- Troubleshooting Kubernetes Liveness and Readiness Probe Failures: https://resolve.ai/glossary/how-to-debug-kubernetes-probe-issues
- Liveness probe failed connection refused - SUSE Rancher Prime - SUSE: https://forums.suse.com/t/liveness-probe-failed-connection-refused/20837
- How do I resolve Readiness probe connection refused error · Issue #10694 · helm/helm · GitHub: https://github.com/helm/helm/issues/10694
- Kubernetes liveness probe fails with "connection refused ...: https://www.reddit.com/r/kubernetes/comments/e94rae/kubernetes_liveness_probe_fails_with_connection
- Kubernetes Liveness Probes: Configuration & Best Practices: https://www.groundcover.com/blog/kubernetes-liveness-probe
- Guide to Understanding Your Kubernetes Liveness Probes Best Practices: https://www.fairwinds.com/blog/a-guide-to-understanding-kubernetes-liveness-probes-best-practices
- Kubernetes Liveness Probes: Configuration & Best Practices: https://www.groundcover.com/blog/kubernetes-liveness-probe
- How to Configure HTTP GET Probes with Custom Headers and Paths: https://oneuptime.com/blog/post/2026-02-09-http-get-probes-custom-headers/view
- Configure Liveness, Readiness and Startup Probes | Kubernetes: https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes
- Kubernetes probes: startupProbe, livenssProbe, and readinessProbe - DEV Community: https://dev.to/jacktt/kubernetes-probes-livenssprobe-readinessprobe-and-startupprobe-3j37
- Troubleshooting Kubernetes Liveness and Readiness Probe Failures: https://resolve.ai/glossary/how-to-debug-kubernetes-probe-issues
- Pod in 'CrashLoopBackOff' State - 'Readiness\Liveness probe failed: Get http://{POD_IP}:8082/actuator/health: dial tcp {POD_IP}:8082: connect: connection refused | Troubleshooting | Sisense Community: https://community.sisense.com/forum/troubleshooting-39/topic/pod-in-crashloopbackoff-state-readinessliveness-probe-failed-get-httppod_ip8082actuatorhealth-dial-tcp-pod_ip8082-connect-connection-refused-4766
- Kubernetes readiness and liveness probe failures | NOFire AI: https://www.nofire.ai/glossary/kubernetes-probe-failures
- Debug a Pod in CrashLoopBackOff on Kubernetes: Causes and Solutions | SFEIR Institute: https://institute.sfeir.com/en/kubernetes-training/debug-pod-crashloopbackoff-kubernetes-causes-solutions
- Kubernetes Pod Restart Reasons: How to Troubleshoot: https://edgedelta.com/company/knowledge-center/kubernetes-pod-restart-reasons-explained

## How this was verified
Tests ran in an isolated container (`docker run --rm --network none`), replaying the sandbox command above. Evidence captured at 2026-10-06T19:38:01+00:00.

---
Opened by Mender for human review. Do not auto-merge; a person must review and merge this PR.