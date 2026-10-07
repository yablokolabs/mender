## Root cause
Deployment spec mounts the checkout-config ConfigMap at /etc/config but the application expects config.yaml at /etc/app/config.yaml (CONFIG_PATH constant in service.py). The new ReplicaSet (hash 6cd8d47d9) introduced this incorrect mountPath while older pods (hash 64fb479466) still mount correctly at /etc/app.

## Mechanism
1. Deployment rollout created new ReplicaSet checkout-6cd8d47d9 with volumeMounts.mountPath=/etc/config [deploy.yaml]. 2. New pod checkout-6cd8d47d9-g7zsk starts and mounts ConfigMap at /etc/config, so config.yaml appears at /etc/config/config.yaml. 3. Application startup reads CONFIG_PATH=/etc/app/config.yaml (hardcoded in service.py) and fails with 'FATAL: config file not found: /etc/app/config.yaml' [logs]. 4. Container exits with code 1, kubelet restarts with back-off (CrashLoopBackOff) [events, describe]. 5. Older pods on previous ReplicaSet (64fb479466) still mount at /etc/app and run healthy [pods, describe].

Confidence: 0.98 · Labels: volume_mount_mismatch, configmap_path, deployment_rollback, crashloopbackoff, config_file_missing

## Evidence relied on
- FATAL: config file not found: /etc/app/config.yaml
- Mounts: /etc/config from app-config (ro) on failing pod
- Mounts: /etc/app from app-config (ro) on healthy pods
- volumeMounts.mountPath: /etc/config in deploy.yaml
- CONFIG_PATH = "/etc/app/config.yaml" in service.py
- pod-template-hash differs: 6cd8d47d9 (failing) vs 64fb479466 (healthy)

## Change
Files: demo/manifests/deploy.yaml
Rationale: The application expects config.yaml at /etc/app/config.yaml (CONFIG_PATH in service.py). The deployment was mounting the checkout-config ConfigMap at /etc/config, causing the file to be unavailable at the expected path. Changing the volumeMounts.mountPath from /etc/config to /etc/app ensures config.yaml is accessible at /etc/app/config.yaml, allowing the pods to start successfully.

## Sandbox test results
Command: `python3 demo/app/check.py` — **PASSED** in 1 attempt(s)
- attempt 1: exit 0 in 0.7s — ok

## Tavily sources used
Queries: Kubernetes ConfigMap volume mount path mismatch container expects config at different path; Kubernetes pod crash config file not found ConfigMap volume mount path; Kubernetes deployment volumeMount mountPath ConfigMap items key path mismatch
- Kubernetes ConfigMaps Volume Mount issue | Codemia: https://codemia.io/knowledge-hub/path/kubernetes_configmaps_volume_mount_issue
- Working with kubernetes configmaps, part 1: volume mounts: https://itnext.io/working-with-kubernetes-configmaps-part-1-volume-mounts-f0ace283f5aa
- Kubernetes - Using ConfigMap SubPaths to Mount Files - DEV Community: https://dev.to/joshduffney/kubernetes-using-configmap-subpaths-to-mount-files-3a1i
- How to Fix 'Configuration Management' Issues: https://oneuptime.com/blog/post/2026-01-24-configuration-management-issues/view
- Kubernetes Volume Mount ConfigMap to File within the ...: https://stackoverflow.com/questions/67532600/kubernetes-volume-mount-configmap-to-file-within-the-pod-without-overwriting-all
- Diagnose and Fix CrashLoopBackOff Caused by Missing Configuration Dependencies: https://oneuptime.com/blog/post/2026-02-09-crashloopbackoff-missing-config/view
- ConfigMap Not Mounting as Volume in Kubernetes | Buglyst: https://buglyst.com/learn/guides/kubernetes-configmap-not-mounting-debug
- Pod with configmap CrashLoopBackOff : r/kubernetes: https://www.reddit.com/r/kubernetes/comments/zvz0mi/pod_with_configmap_crashloopbackoff
- Troubleshooting Kubernetes ConfigMap and Secret Issues: https://www.managekubernetes.com/blog/troubleshooting-kubernetes-configmap-and-secret-issues
- Kubernetes ConfigMap and Secret Not Mounting in Pod — Every Fix (2026) | DevOpsBoys: https://devopsboys.com/blog/kubernetes-configmap-secret-not-mounting-fix-2026
- Discussion of Kubernetes - Using ConfigMap SubPaths to Mount Files - DEV Community: https://dev.to/joshduffney/kubernetes-using-configmap-subpaths-to-mount-files-3a1i/comments
- Kubernetes ConfigMaps Volume Mount issue | Codemia: https://codemia.io/knowledge-hub/path/kubernetes_configmaps_volume_mount_issue
- Kubernetes - Using ConfigMap SubPaths to Mount Files - DEV Community: https://dev.to/joshduffney/kubernetes-using-configmap-subpaths-to-mount-files-3a1i
- subPath is the most confusing thing in Kubernetes - HackMD: https://hackmd.io/@maelvls/kubernetes-subpath
- 14. Resolve VolumeMounts Issue in Kubernetes: https://medium.com/@ayeshalakshan00/14-resolve-volumemounts-issue-in-kubernetes-6251266465c8

## How this was verified
Tests ran in an isolated container (`docker run --rm --network none`), replaying the sandbox command above. Evidence captured at 2026-10-06T19:20:52+00:00.

---
Opened by Mender for human review. Do not auto-merge; a person must review and merge this PR.