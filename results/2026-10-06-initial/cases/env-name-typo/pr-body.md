## Root cause
Deployment manifest defines environment variable DB_HOSTS (with trailing 'S') referencing ConfigMap key db_host, but application code requires DB_HOST (without 'S'), causing startup failure with 'FATAL: missing required env var DB_HOST' [1].

## Mechanism
1. Deployment spec sets env var name=DB_HOSTS from configmap checkout-config key db_host. 2. New ReplicaSet checkout-8f99c6776 rolls out pods with DB_HOSTS=orders-db.shop.svc.cluster.local. 3. Application entrypoint calls require_environment() which reads os.environ.get('DB_HOST') — finds nothing. 4. Raises ConfigError('missing required env var DB_HOST') and exits with code 1. 5. Container restarts repeatedly; kubelet backs off into CrashLoopBackOff. 6. Older ReplicaSet checkout-7fff58d6ff still runs correct DB_HOST (no 'S') so those pods stay healthy.

Confidence: 0.95 · Labels: probe_config, missing_secret, configmap_change

## Evidence relied on
- DB_HOSTS: <set to the key 'db_host' of config map 'checkout-config'> (crashing pod)
- DB_HOST: <set to the key 'db_host' of config map 'checkout-config'> (healthy pods)
- FATAL: missing required env var DB_HOST (logs)
- - name: DB_HOSTS (deploy.yaml)
- raise ConfigError("missing required env var DB_HOST") (service.py)
- Search [1]: "Error: Missing environment variable DB_HOST"

## Change
Files: demo/manifests/deploy.yaml
Rationale: The application code expects the environment variable DB_HOST (without trailing 'S'), but the deployment was incorrectly setting DB_HOSTS. Changing the env var name to DB_HOST aligns the deployment with the application's requirement, preventing the missing env var error and crash loop.

## Sandbox test results
Command: `python3 demo/app/check.py` — **PASSED** in 1 attempt(s)
- attempt 1: exit 0 in 0.6s — ok

## Tavily sources used
Queries: Kubernetes CrashLoopBackOff missing required environment variable DB_HOST ConfigMap key mismatch; Kubernetes deployment env var name mismatch ConfigMap key db_host application expects DB_HOST; Kubernetes pod CrashLoopBackOff FATAL missing required env var environment variable naming
- Fix Kubernetes Pods Stuck in CrashLoopBackOff Errors: https://www.supportpro.com/blog/how-to-fix-kubernetes-pods-that-are-stuck-in-crashloopbackoff
- Diagnose and Fix CrashLoopBackOff Caused by Missing Configuration Dependencies: https://oneuptime.com/blog/post/2026-02-09-crashloopbackoff-missing-config/view
- Kubernetes CrashLoopBackOff: Finding Missing ConfigMaps: https://www.youtube.com/watch?v=Hlk6mUiURxo
- Kubernetes Most Occurred Issue | CrashLoopBackOff: https://aws.plainenglish.io/kubernetes-most-occurred-issue-crashloopbackoff-cc107a48d0c0
- Kubernetes CrashLoopBackOff: Fixing Missing ConfigMap ...: https://www.linkedin.com/posts/kumar-ujjwal-682713186_kubernetes-devops-cloud-activity-7441455599013490688-lsU5
- Kubernetes ConfigMaps for Decoupling Configuration: https://devsecopsguru.in/kb/kubernetes-configmaps-for-decoupling-configuration
- Kubernetes ConfigMap and Secret Not Mounting in Pod — Every Fix (2026) | DevOpsBoys: https://devopsboys.com/blog/kubernetes-configmap-secret-not-mounting-fix-2026
- Kubernetes ConfigMap: Create, Mount, Update | K8s Recipes: https://kubernetes.recipes/recipes/configuration/kubernetes-configmap-guide
- Kustomize 3.8.5 orders overlayed environment variable differently than 3.7.0 · Issue #3157 · kubernetes-sigs/kustomize · GitHub: https://github.com/kubernetes-sigs/kustomize/issues/3157
- KA-B012: Duplicate environment variable keys | Kubernetes Manifest Analyzer: https://patrykgolabek.dev/tools/k8s-analyzer/rules/ka-b012
- Fix Kubernetes Pods Stuck in CrashLoopBackOff Errors: https://www.supportpro.com/blog/how-to-fix-kubernetes-pods-that-are-stuck-in-crashloopbackoff
- Pod Stuck in CrashLoopBackOff. CrashLoopBackOff is a type of error… | by Shashwat Tripathi | Medium: https://medium.com/@shashwattripathi11/pod-stuck-in-crashloopbackoff-b1549a174952
- Pods are CrashLoopBackOff due to ConfigMap Change - Microsoft Q&A: https://learn.microsoft.com/en-nz/answers/questions/5631075/pods-are-crashloopbackoff-due-to-configmap-change
- Diagnose and Fix CrashLoopBackOff Caused by Missing Configuration Dependencies: https://oneuptime.com/blog/post/2026-02-09-crashloopbackoff-missing-config/view
- Kubernetes CrashLoopBackOff: A Systematic Debug Guide ...: https://blog.stackademic.com/kubernetes-crashloopbackoff-a-systematic-debug-guide-for-production-engineers-03a61f44122c

## How this was verified
Tests ran in an isolated container (`docker run --rm --network none`), replaying the sandbox command above. Evidence captured at 2026-10-06T17:06:35+00:00.

---
Opened by Mender for human review. Do not auto-merge; a person must review and merge this PR.