## Root cause
The ConfigMap 'checkout-config' contains malformed config.yaml with log_level: [unclosed (an unclosed bracket), which parses as the string "[unclosed" but fails the service's validation against ALLOWED_LOG_LEVELS = {"debug", "info", "warn", "error"}, causing immediate startup crash.

## Mechanism
1. The checkout-config ConfigMap's config.yaml key has invalid content: 'log_level: [unclosed' (unclosed bracket). 2. New pod checkout-74b79fc65b-tkc49 mounts this ConfigMap at /etc/app/config.yaml. 3. On startup, the service loads and parses the YAML (yaml.safe_load succeeds, yielding log_level = "[unclosed"). 4. Service validates log_level against ALLOWED_LOG_LEVELS; validation fails and raises ConfigError. 5. Service logs 'FATAL: invalid log_level: [unclosed' and exits with code 1 (observed in pod describe: Exit Code 1, container lasted ~1s). 6. Kubernetes restarts the container (restartPolicy=Always), but the same config causes repeated crashes. 7. After 3 restarts, pod enters CrashLoopBackOff. 8. Readiness/liveness probes hit /healthz which returns 500 for invalid log_level (per check_service_healthcheck_logic), so probes never succeed. The two healthy pods (599ffd5c77-*) run an older ReplicaSet with a valid config.

Confidence: 0.95 · Labels: config_map_content, probe_config, crashloopbackoff, validation_failure

## Evidence relied on
- configmap.yaml: log_level: [unclosed
- LOGS: FATAL: invalid log_level: [unclosed
- DESCRIBE checkout-74b79fc65b-tkc49: Exit Code: 1, Reason: CrashLoopBackOff, Restart Count: 3
- service.py: ALLOWED_LOG_LEVELS = {"debug", "info", "warn", "error"}, raises ConfigError on invalid
- check_service_healthcheck_logic: healthcheck returns 500 for invalid log_level

## Change
Files: demo/manifests/configmap.yaml
Rationale: The ConfigMap's config.yaml contained an invalid log_level value '[unclosed' due to an unclosed bracket, causing the service to fail validation and crash. Changing it to a valid log level (e.g., 'info') allows the service to start successfully.

## Sandbox test results
Command: `python3 demo/app/check.py` — **PASSED** in 1 attempt(s)
- attempt 1: exit 0 in 0.7s — ok

## Tavily sources used
Queries: Kubernetes ConfigMap malformed YAML parsing error CrashLoopBackOff; invalid log_level ConfigError yaml.safe_load unclosed bracket; checkout service config.yaml validation ALLOWED_LOG_LEVELS known issues
- Pods are CrashLoopBackOff due to ConfigMap Change - Microsoft Q&A: https://learn.microsoft.com/en-us/answers/questions/5631075/pods-are-crashloopbackoff-due-to-configmap-change
- Kubernetes CrashLoopBackOff – Causes and Fixes (2026) · DevOps With Ramya: https://devopswithramya.com/posts/kubernetes-crashloopbackoff-fix
- CrashLoopBackOff in Kubernetes? Try These Fixes Now!: https://cicdtrail.com/fix-kubernetes-crashloopbackoff
- Pods are CrashLoopBackOff due to ConfigMap Change - Microsoft Q&A: https://learn.microsoft.com/en-nz/answers/questions/5631075/pods-are-crashloopbackoff-due-to-configmap-change
- What is Kubernetes CrashLoopBackOff? And how to fix it | Sysdig: https://www.sysdig.com/blog/debug-kubernetes-crashloopbackoff
- [YAML] 'log_level' is deprecated parameter name. use ...: https://github.com/fluent/fluentd/issues/4463
- Invalid Config with log_level on server config · Issue #14031: https://github.com/grafana/loki/issues/14031
- yml formatting error cause invalid yml file · Issue #449: https://github.com/redhat-developer/vscode-yaml/issues/449
- What's wrong with this log level config? - Configuration: https://community.home-assistant.io/t/whats-wrong-with-this-log-level-config/132282
- [#LOG4J2-2663] Can't configure a logger off in yaml: https://issues.apache.org/jira/browse/LOG4J2-2663
- performance of the checkout step in an Azure DevOps ...: https://stackoverflow.com/questions/79493337/performance-of-the-checkout-step-in-an-azure-devops-yaml-pipeline
- WooCommerce Checkout Validation Issues Explained with Easy Fixes - WSP WP: https://www.wpsupportwebdevelopment.com/blog/woocommerce-checkout-validation-issues-explained-with-easy-fixes
- hermes-config-validation: Validate Hermes Agent configuration, credentials, and auxiliary service issues | skills.rest: https://skills.rest/skill/hermes-config-validation
- Validation schema of config.yaml - RAPIDS: https://www.rapids.science/developers/validation-schema-config
- Validation schema of config.yaml - RAPIDS: https://www.rapids.science/1.6/developers/validation-schema-config

## How this was verified
Tests ran in an isolated container (`docker run --rm --network none`), replaying the sandbox command above. Evidence captured at 2026-10-06T17:11:29+00:00.

---
Opened by Mender for human review. Do not auto-merge; a person must review and merge this PR.