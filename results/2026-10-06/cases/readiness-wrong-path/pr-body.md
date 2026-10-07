## Root cause
The deployment manifest was updated to configure the readiness probe with path `/ready`, but the application code only implements `/healthz` and `/amount` endpoints — no `/ready` handler exists.

## Mechanism
1. A deployment rollout created new ReplicaSet checkout-6558b8b689 with updated readinessProbe.path=/ready (while livenessProbe remains /healthz). 2. New pod checkout-6558b8b689-98gf6 started and kubelet began probing HTTP GET /ready every 5s. 3. The application's HTTP handler (service.py) only routes /healthz and /amount; all other paths return 404. 4. Each probe receives 404, so the pod never becomes Ready (events show "Readiness probe failed: HTTP probe failed with statuscode: 404"). 5. Older pods on ReplicaSet checkout-7b4fcf8959 still use /healthz for both probes and remain Ready.

Confidence: 0.95 · Labels: probe_config, manifest_drift, missing_endpoint

## Evidence relied on
- Events: "Readiness probe failed: HTTP probe failed with statuscode: 404"
- Describe failing pod: "Readiness: http-get http://:http/ready delay=2s timeout=1s period=5s"
- Describe working pods: "Readiness: http-get http://:http/healthz delay=2s timeout=1s period=5s"
- Logs failing pod: "GET /ready HTTP/1.1" 404 (repeated) vs "GET /healthz HTTP/1.1" 200
- Service code (service.py): Handler only implements /healthz and /amount; no /ready route
- Deployment manifest (deploy.yaml): readinessProbe.httpGet.path: /ready

## Change
Files: demo/manifests/deploy.yaml
Rationale: The readiness probe was incorrectly configured to probe /ready, but the application only exposes /healthz and /amount. Changing the readinessProbe path back to /healthz aligns the probe with an existing endpoint, allowing pods to become Ready.

## Sandbox test results
Command: `python3 demo/app/check.py` — **PASSED** in 1 attempt(s)
- attempt 1: exit 0 in 0.6s — ok

## Tavily sources used
Queries: Kubernetes readiness probe 404 endpoint mismatch deployment configuration; Kubernetes probe path configuration application endpoint mismatch troubleshooting; readiness probe HTTP 404 not found endpoint missing application
- Spring Boot Actuator 404 Liveness/Readiness Fix for Kubernetes Deployments | CodeArchPedia.com: https://openillumi.com/en/en-spring-boot-actuator-liveness-readiness-404-fix
- Spring Boot custom Kubernetes readiness probe | Codemia: https://codemia.io/knowledge-hub/path/spring_boot_custom_kubernetes_readiness_probe
- Troubleshooting Kubernetes Liveness and Readiness Probe Failures: https://resolve.ai/glossary/how-to-debug-kubernetes-probe-issues
- Liveness and Readiness Probe Configuration - Wiki - wiki.jmehan.com: https://wiki.jmehan.com/display/KNOW/Liveness+and+Readiness+Probe+Configuration
- Availability | Ensure Container readiness probe is configured: https://www.stream.security/rules/ensure-container-readiness-probe-is-configured
- Troubleshooting Kubernetes Liveness and Readiness Probe Failures: https://resolve.ai/glossary/how-to-debug-kubernetes-probe-issues
- Kubernetes Probes- livenessProbe, readinessProbe, startupProbe |How to use kubernetes probes-part 14: https://www.youtube.com/watch?v=aTlQBofihJQ
- How to Configure Kubernetes Liveness Probes Without Causing Restart Loops · MeteorOps: https://meteorops.com/blog/how-to-configure-kubernetes-liveness-probes-without-causing-restart-loops
- Readiness Probe Failed in Kubernetes: How to Fix It: https://nudgebee.com/resources/blog/readiness-probe-failed-in-kubernetes
- Kubernetes Readiness Probes - Examples & Common Pitfalls: https://www.vcluster.com/blog/kubernetes-readiness-probes-examples-and-common-pitfalls
- Kubernetes readiness and liveness probe failures | NOFire AI: https://www.nofire.ai/glossary/kubernetes-probe-failures
- Kubernetes Readiness Probe Failed: HTTP Probe Failed with ...: https://hatchjs.com/readiness-probe-failed-http-probe-failed-with-statuscode-404
- 503 - readiness probe failed - Microsoft Q&A: https://learn.microsoft.com/en-us/answers/questions/2280612/503-readiness-probe-failed
- Kubernetes Readiness Probes - Examples & Common Pitfalls: https://www.vcluster.com/blog/kubernetes-readiness-probes-examples-and-common-pitfalls
- is there any way to resolve liveness probe failure issue in ...: https://stackoverflow.com/questions/74960530/is-there-any-way-to-resolve-liveness-probe-failure-issue-in-kubernetes-environme

## How this was verified
Tests ran in an isolated container (`docker run --rm --network none`), replaying the sandbox command above. Evidence captured at 2026-10-06T19:51:11+00:00.

---
Opened by Mender for human review. Do not auto-merge; a person must review and merge this PR.