## Root cause
The failing pod (checkout-67bc9dbdf8-cvzgt) mounts the checkout-config ConfigMap at /etc/config instead of /etc/app, so the application cannot find its required config.yaml at /etc/app/config.yaml.

## Mechanism
1. The pod starts with the ConfigMap volume mounted at /etc/config (evident in its Mounts section) [1]. 2. The application's CONFIG_PATH defaults to /etc/app/config.yaml (see service.py). 3. On startup, the app attempts to load the config file from /etc/app/config.yaml but finds nothing because the volume is mounted at /etc/config. 4. The app logs 'FATAL: config file not found: /etc/app/config.yaml' and exits with code 1. 5. Kubernetes restarts the container, which repeats the failure, leading to CrashLoopBackOff. The two healthy pods (pod-template-hash 9f49f8b65) correctly mount at /etc/app per the deployment manifest.

Confidence: 0.95 · Labels: crashloopbackoff, configmap_mount, mount_path, probe_config

## Evidence relied on
- FATAL: config file not found: /etc/app/config.yaml
- Mounts: /etc/config from app-config (ro) on failing pod vs /etc/app from app-config (ro) on healthy pods
- deployment manifest shows mountPath: /etc/app
- service.py CONFIG_PATH defaults to /etc/app/config.yaml

## Change
Files: demo/manifests/deploy.yaml
Rationale: Change the ConfigMap volume mount path from /etc/config to /etc/app so the application can find config.yaml at /etc/app/config.yaml as expected, fixing the CrashLoopBackOff caused by missing configuration.

## Sandbox test results
Command: `python3 demo/app/check.py` — **PASSED** in 1 attempt(s)
- attempt 1: exit 0 in 0.7s — ok

## Tavily sources used
Queries: Kubernetes ConfigMap volume mount path mismatch CrashLoopBackOff config file not found; Kubernetes deployment volumeMount mountPath ConfigMap items key path config.yaml; CrashLoopBackOff FATAL config file not found /etc/app/config.yaml Kubernetes
- How to Fix CrashLoopBackOff in Kubernetes? - Komodor: https://komodor.com/learn/how-to-fix-crashloopbackoff-kubernetes-error
- Diagnose and Fix CrashLoopBackOff Caused by Missing Configuration Dependencies: https://oneuptime.com/blog/post/2026-02-09-crashloopbackoff-missing-config/view
- Pod with configmap CrashLoopBackOff : r/kubernetes: https://www.reddit.com/r/kubernetes/comments/zvz0mi/pod_with_configmap_crashloopbackoff
- Kubernetes CrashLoopBackOff: Finding Missing ConfigMaps: https://www.youtube.com/watch?v=Hlk6mUiURxo
- Kubernetes CrashLoopBackOff: Finding Missing ConfigMaps: https://www.youtube.com/watch?v=Hlk6mUiURxo&xstg=CAMSBhUDze3xHw%3D%3D
- Configmap and Kubernetes : Overriding Configuration Files: https://medium.com/@dheeraj007tripathi/configmap-and-kubernetes-overriding-configuration-files-5db9e6da08c9
- Kubernetes ConfigMap Guide: How k8s Handles Pod Configuration - Tecktol: https://tecktol.com/kubernetes-configmap
- Kubernetes ConfigMaps Volume Mount issue | Codemia: https://codemia.io/knowledge-hub/path/kubernetes_configmaps_volume_mount_issue
- ConfigMaps | Kubernetes: https://kubernetes.io/docs/concepts/configuration/configmap
- Kubernetes - Using ConfigMap SubPaths to Mount Files - DEV Community: https://dev.to/joshduffney/kubernetes-using-configmap-subpaths-to-mount-files-3a1i
- CrashLoopBackOff on new deployment — ConfigMap created in wrong namespace | Today I Fixed | DevOpsBoys: https://devopsboys.com/today-i-fixed/kubernetes-crashloopbackoff-missing-configmap-fix
- Diagnose and Fix CrashLoopBackOff Caused by Missing Configuration Dependencies: https://oneuptime.com/blog/post/2026-02-09-crashloopbackoff-missing-config/view
- Kubernetes ConfigMap Not Found Error: Troubleshooting and Best Practices | Mustafa Shaik posted on the topic | LinkedIn: https://www.linkedin.com/posts/musta-shaik_kubernetes-devops-cloudnative-activity-7419296342113636352-3BaH
- How Do I Fix CrashLoopBackOff in Kubernetes (Step‑by‑Step)?: https://www.fairwinds.com/blog/how-do-i-fix-crashloopbackoff-in-kubernetes-step-by-step
- Pod with configmap CrashLoopBackOff : r/kubernetes: https://www.reddit.com/r/kubernetes/comments/zvz0mi/pod_with_configmap_crashloopbackoff

## How this was verified
Tests ran in an isolated container (`docker run --rm --network none`), replaying the sandbox command above. Evidence captured at 2026-10-06T16:59:31+00:00.

---
Opened by Mender for human review. Do not auto-merge; a person must review and merge this PR.