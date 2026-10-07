## Root cause
Deployment manifest defines environment variable as DB_HOSTS (plural) but application code requires DB_HOST (singular), causing immediate startup failure with 'FATAL: missing required env var DB_HOST'

## Mechanism
1. Deployment manifest (deploy.yaml) specifies env var name 'DB_HOSTS' referencing ConfigMap key 'db_host' [1]. 2. Pod checkout-6bf57488d6-kt8ls starts with DB_HOSTS in its environment (visible in DESCRIBE). 3. Application service.py require_environment() checks for 'DB_HOST' (singular) and raises ConfigError when not found [2]. 4. Container exits with code 1, Kubernetes restarts it, entering CrashLoopBackOff with exponential backoff [3]. 5. Two older pods (cdfc46887) run successfully because they were created from a prior ReplicaSet that had the correct env var name 'DB_HOST'.

Confidence: 0.95 · Labels: env_var_typo, config_map_key_ref, crashloopbackoff, missing_env_var, deployment_manifest_bug

## Evidence relied on
- FATAL: missing required env var DB_HOST
- DB_HOSTS: <set to the key 'db_host' of config map 'checkout-config'>
- DB_HOST: <set to the key 'db_host' of config map 'checkout-config'>
- - name: DB_HOSTS
  valueFrom:
    configMapKeyRef:
      name: checkout-config
      key: db_host
- db_host = os.environ.get("DB_HOST", "")
if not db_host:
    raise ConfigError("missing required env var DB_HOST")

## Change
Files: demo/manifests/deploy.yaml
Rationale: The application code expects an environment variable named DB_HOST, but the deployment manifest incorrectly defined it as DB_HOSTS. Changing the env var name to DB_HOST aligns the deployment with the application's requirement, resolving the startup failure.

## Sandbox test results
Command: `python3 demo/app/check.py` — **PASSED** in 1 attempt(s)
- attempt 1: exit 0 in 0.7s — ok

## Tavily sources used
Queries: Kubernetes CrashLoopBackOff missing required environment variable DB_HOST deployment configmap key mismatch; Kubernetes deployment env var name typo DB_HOSTS vs DB_HOST configMapKeyRef application startup validation failure; Kubernetes pod CrashLoopBackOff ConfigError missing env var documented causes known issues
- Fix Kubernetes Pods Stuck in CrashLoopBackOff Errors: https://www.supportpro.com/blog/how-to-fix-kubernetes-pods-that-are-stuck-in-crashloopbackoff
- Kubernetes CrashLoopBackOff: Finding Missing ConfigMaps: https://www.youtube.com/watch?v=Hlk6mUiURxo
- Diagnose and Fix CrashLoopBackOff Caused by Missing Configuration Dependencies: https://oneuptime.com/blog/post/2026-02-09-crashloopbackoff-missing-config/view
- kubernetes - k8s: configMap does not work in deployment - Stack Overflow: https://stackoverflow.com/questions/63079479/k8s-configmap-does-not-work-in-deployment
- Kubernetes Most Occurred Issue | CrashLoopBackOff: https://aws.plainenglish.io/kubernetes-most-occurred-issue-crashloopbackoff-cc107a48d0c0
- How to Fix 'Configuration Management' Issues: https://oneuptime.com/blog/post/2026-01-24-configuration-management-issues/view
- How to Use ConfigMaps with Environment Variables in Kubernetes: https://oneuptime.com/blog/post/2026-01-22-configmaps-environment-variables-kubernetes/view
- Unresolved ConfigMap Key reference in container ...: https://kubevious.io/docs/built-in-validators/container/unresolved-configmap-key-reference-in-container-environment-variables
- Kubernetes ConfigMap Not Found Error: Troubleshooting and Best Practices | Mustafa Shaik posted on the topic | LinkedIn: https://www.linkedin.com/posts/musta-shaik_kubernetes-devops-cloudnative-activity-7419296342113636352-3BaH
- Kubernetes ConfigMap: What It Is & How to Use It · Dash0: https://www.dash0.com/knowledge/kubernetes-configmap-what-it-is-and-how-to-use-it
- Debug a Pod in CrashLoopBackOff on Kubernetes: Causes and Solutions | SFEIR Institute: https://institute.sfeir.com/en/kubernetes-training/debug-pod-crashloopbackoff-kubernetes-causes-solutions
- Fix Kubernetes Pods Stuck in CrashLoopBackOff Errors: https://www.supportpro.com/blog/how-to-fix-kubernetes-pods-that-are-stuck-in-crashloopbackoff
- Kubernetes CrashLoopBackOff: Causes, Diagnosis, and Fixes: https://middleware.io/blog/kubernetes-crashloopbackoff-causes-diagnosis-and-fixes
- Kubernetes CrashLoopBackOff – Causes and Fixes (2026) · DevOps With Ramya: https://devopswithramya.com/posts/kubernetes-crashloopbackoff-fix
- Fix Kubernetes CrashLoopBackOff: Causes and Solutions: https://karandeepsingh.ca/posts/fix-kubernetes-crashloopbackoff

## How this was verified
Tests ran in an isolated container (`docker run --rm --network none`), replaying the sandbox command above. Evidence captured at 2026-10-06T19:31:17+00:00.

---
Opened by Mender for human review. Do not auto-merge; a person must review and merge this PR.