## Root cause
The secret 'checkout-secrets' contains a secret_key value of only 5 characters ('short'), but the application enforces a minimum length of 32 characters in its startup validation [6].

## Mechanism
1. A new ReplicaSet (checkout-95b59cfdb) was created, likely from a deployment update. 2. The new pod (checkout-95b59cfdb-2ztgw) starts and reads SECRET_KEY from the secret 'checkout-secrets' (value 'short', 5 chars). 3. Application startup calls require_environment() which validates len(SECRET_KEY) >= 32 [6]. 4. Validation fails with 'FATAL: SECRET_KEY too short (5 < 32 chars)' (see logs). 5. Container exits with code 1, kubelet restarts with exponential backoff → CrashLoopBackOff. 6. The two older pods (hash 6ddf79b575) continue running because they started before the secret was changed or they use a cached value.

Confidence: 0.98 · Labels: secret_validation, secret_too_short, crashloopbackoff, deployment_rollback_needed, config_error

## Evidence relied on
- FATAL: SECRET_KEY too short (5 < 32 chars)
- secret_key: "short" in secret.yaml
- assert len(value) >= 32, f"secret_key too short ({len(value)} < 32 chars)" in check.py
- require_environment() raises ConfigError if len(secret) < MIN_SECRET_LENGTH (32) in service.py
- Pod checkout-95b59cfdb-2ztgw has pod-template-hash=95b59cfdb while running pods have 6ddf79b575

## Change
Files: demo/manifests/secret.yaml
Rationale: The secret_key value was only 5 characters, causing the application's startup validation (requiring >=32 characters) to fail. Updating the secret to a 56-character demo-only value satisfies the length requirement while preserving the comment and structure.

## Sandbox test results
Command: `python3 demo/app/check.py` — **PASSED** in 1 attempt(s)
- attempt 1: exit 0 in 0.9s — ok

## Tavily sources used
Queries: "SECRET_KEY too short" Kubernetes config validation; mender-demo-app SECRET_KEY 32 character minimum requirement; Kubernetes secret key length validation CrashLoopBackOff
- Secrets | Kubernetes: https://kubernetes.io/docs/concepts/configuration/secret
- Kubernetes CreateContainerConfigError: 7 Common ...: https://cubeapm.com/blog/kubernetes-createcontainerconfigerror
- Deployment configuration options | Solution Guide—AI ...: https://infohub.delltechnologies.com/en-us/l/solution-guide-ai-agents-for-business-users-with-aible/deployment-configuration-options-9
- Kubernetes-101: ConfigMaps and Secrets · mattias.engineer: https://mattias.engineer/courses/kubernetes/configmaps-and-secrets
- Secret and ConfigMap should limit # of keys · Issue #19969: https://github.com/kubernetes/kubernetes/issues/19969
- rehmatworks/secret-key-generator: https://github.com/rehmatworks/secret-key-generator
- Security | Mender documentation: https://docs.mender.io/overview/security
- Building for demo | Mender documentation: https://docs.mender.io/operating-system-updates-yocto-project/build-for-demo
- Configuration | Mender documentation: https://docs.mender.io/operating-system-updates-zephyr/configuration
- Django `SECRET_KEY` settings: https://stackoverflow.com/questions/40856593/django-secret-key-settings
- Diagnose and Fix CrashLoopBackOff Caused by Missing Configuration Dependencies: https://oneuptime.com/blog/post/2026-02-09-crashloopbackoff-missing-config/view
- How to Debug CrashLoopBackOff in Kubernetes: https://www.youtube.com/watch?v=U8Fu2kgSdyo
- "CrashLoopBackOff in Kubernetes: Common Causes and Fixes" | Isreal Urephu posted on the topic | LinkedIn: https://www.linkedin.com/posts/isrealurephu_understanding-and-fixing-crashloopbackoff-activity-7385999020810354689-X--y
- What is Kubernetes CrashLoopBackOff? And how to fix it | Sysdig: https://www.sysdig.com/blog/debug-kubernetes-crashloopbackoff
- Understanding Kubernetes CrashLoopBackOff & How to Fix It: https://www.groundcover.com/kubernetes-troubleshooting/crashloopbackoff

## How this was verified
Tests ran in an isolated container (`docker run --rm --network none`), replaying the sandbox command above. Evidence captured at 2026-10-06T17:33:44+00:00.

---
Opened by Mender for human review. Do not auto-merge; a person must review and merge this PR.