## Root cause
The ConfigMap 'checkout-config' contains a malformed log_level value '[unclosed' in its config.yaml key, which is not in the application's allowed log levels (debug, info, warn, error).

## Mechanism
1. The ConfigMap 'checkout-config' stores config.yaml with content 'log_level: [unclosed' [1]. 2. Pods mount this as /etc/app/config.yaml. 3. On startup, the application loads and parses this config via parse_config(), which validates log_level against ALLOWED_LOG_LEVELS [2]. 4. Validation fails because '[unclosed' is not allowed, raising ConfigError. 5. main() catches ConfigError, logs 'FATAL: invalid log_level: [unclosed' and exits with code 1 [3]. 6. Container terminates with Reason: Error, Exit Code: 1 [4]. 7. Kubernetes restarts the container with exponential backoff (BackOff event) [5], creating a crash loop. 8. Readiness/liveness probes never succeed because the container never stays running [6].

Confidence: 0.95 · Labels: configmap_error, invalid_yaml, probe_config, crash_loop, exit_code_1

## Evidence relied on
- FATAL: invalid log_level: [unclosed
- Last State: Terminated Reason: Error Exit Code: 1
- config.yaml: | log_level: [unclosed
- ALLOWED_LOG_LEVELS = {"debug", "info", "warn", "error"}
- raise ConfigError(f"invalid log_level: {config['log_level']}")
- Back-off restarting failed container

## Change
Files: demo/manifests/configmap.yaml
Rationale: The ConfigMap 'checkout-config' contains an invalid log_level value '[unclosed' which is not in the allowed set {debug, info, warn, error}. Changing it to 'info' (a valid level) will allow the application to start correctly, breaking the crash loop caused by ConfigError on startup.

## Sandbox test results
Command: `python3 demo/app/check.py` — **PASSED** in 1 attempt(s)
- attempt 1: exit 0 in 0.6s — ok

## Tavily sources used
Queries: Kubernetes ConfigMap malformed YAML config.yaml log_level unclosed bracket causes pod crash exit code 1; mender-demo-app config validation ConfigError invalid log_level parsing failure documented issues; Kubernetes deployment ConfigMap mount application startup failure due to invalid YAML syntax
- ⎈ A Hands-On Guide to Kubernetes Exit Codes: Simulate and Fix ⚙️ | by Anvesh Muppeda | Medium: https://medium.com/@muppedaanvesh/a-hands-on-guide-to-kubernetes-exit-codes-simulate-and-fix-%EF%B8%8F-f2ad57d3cdca
- Kubernetes Exit Code 1 (SIGTERM): Causes and Troubleshooting · Dash0: https://www.dash0.com/guides/kubernetes-exit-code-1-sigterm-causes-and-troubleshooting
- Debug a Pod in CrashLoopBackOff: Causes, Diagnosis and Solutions | SFEIR Institute: https://institute.sfeir.com/en/kubernetes-training/debug-pod-crashloopbackoff-causes-solutions-kubernetes
- Kubernetes CrashLoopBackOff: Finding Missing ConfigMaps: https://www.youtube.com/watch?v=Hlk6mUiURxo&xstg=CAMSBhUD_LL2Hw%3D%3D
- Kubernetes ConfigMap配置导致Pod崩溃问题咨询: https://www.volcengine.com/article/799748
- Mender client testing on solidrun with Mender demo server - General Discussions - Mender Hub: https://hub.mender.io/t/mender-client-testing-on-solidrun-with-mender-demo-server/505
- Mender Client | Mender documentation: https://docs.mender.io/troubleshoot/mender-client
- Mender | Embedded Artists Developer Site: https://developer.embeddedartists.com/docs-app/ota/ota-mender
- Mender MCU | Mender documentation: https://docs.mender.io/troubleshoot/mender-mcu
- GitHub - mendersoftware/mender-demo-artifact · GitHub: https://github.com/mendersoftware/mender-demo-artifact
- Error when adding ConfigMap data into deployment yaml - Regional Discussions - Discuss Kubernetes: https://discuss.kubernetes.io/t/error-when-adding-configmap-data-into-deployment-yaml/30885
- Kubernetes Errors With Solution - Always learning - Medium: https://ibrahims.medium.com/kubernetes-errors-with-solution-ab3f5643c2dd
- Kubernetes ConfigMap: What It Is & How to Use It · Dash0: https://www.dash0.com/knowledge/kubernetes-configmap-what-it-is-and-how-to-use-it
- Kubernetes ConfigMaps: Examples, Benefits & How to Use Them: https://www.groundcover.com/blog/kubernetes-configmap
- 10 Kubernetes Errors you must know(and How to Fix Them): https://www.perfectscale.io/blog/kubernetes-errors

## How this was verified
Tests ran in an isolated container (`docker run --rm --network none`), replaying the sandbox command above. Evidence captured at 2026-10-06T19:36:34+00:00.

---
Opened by Mender for human review. Do not auto-merge; a person must review and merge this PR.