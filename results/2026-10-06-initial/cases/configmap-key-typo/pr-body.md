## Root cause
Deployment manifest references non-existent ConfigMap key 'config.yamll' (typo) instead of actual key 'config.yaml'

## Mechanism
The deployment manifest (deploy.yaml) defines a ConfigMap volume 'app-config' with items referencing key 'config.yamll' [1]. However, the ConfigMap 'checkout-config' only contains key 'config.yaml' (single 'l') [2]. When kubelet attempts to mount the volume for new pods (ReplicaSets 6c8f468b85 and bd4cd55c6), it fails with 'configmap references non-existent config key: config.yamll' [3], preventing container creation. Existing pods from ReplicaSet cbcbb946 run successfully because they were created before the faulty manifest was applied.

Confidence: 0.95 · Labels: configmap_key_typo, mount_failure, container_creating, deployment_manifest_error

## Evidence relied on
- MountVolume.SetUp failed for volume "app-config" : configmap references non-existent config key: config.yamll
- items:
              - key: config.yamll
                path: config.yaml
- data:
  config.yaml: |
    log_level: info

## Change
Files: demo/manifests/deploy.yaml
Rationale: Fix typo in ConfigMap items key: change 'config.yamll' to 'config.yaml' to match the actual key present in the ConfigMap, allowing the volume to mount correctly.

## Sandbox test results
Command: `python3 demo/app/check.py` — **PASSED** in 1 attempt(s)
- attempt 1: exit 0 in 0.6s — ok

## Tavily sources used
Queries: "configmap references non-existent config key" Kubernetes FailedMount; Kubernetes ConfigMap volume items key typo validation error; FailedMount SetUp failed volume configmap non-existent key
- Core DNS missing NodeHosts key in Configmap · Issue #9274 · k3s-io/k3s · GitHub: https://github.com/k3s-io/k3s/issues/9274
- Kubernetes ConfigMap and Secret Not Mounting in Pod — Every Fix (2026) | DevOpsBoys: https://devopsboys.com/blog/kubernetes-configmap-secret-not-mounting-fix-2026
- Configure a Pod to Use a ConfigMap | Kubernetes: https://kubernetes.io/docs/tasks/configure-pod-container/configure-pod-configmap
- "configmap references non-existent config key"?: https://stackoverflow.com/questions/62312144/why-does-kubernetes-report-configmap-references-non-existent-config-key
- Conftest: configmap references non-existent config key: *** ...: https://github.com/aquasecurity/starboard/issues/509
- kubernetes/pkg/volume/configmap/configmap.go at cfd69463deeebfc5ae8a0813d7d2b125033c4aca · kubernetes/kubernetes · GitHub: https://github.com/kubernetes/kubernetes/blob/cfd69463deeebfc5ae8a0813d7d2b125033c4aca/pkg/volume/configmap/configmap.go
- kubernetes/pkg/volume/configmap/configmap.go at master · kubernetes/kubernetes · GitHub: https://github.com/kubernetes/kubernetes/blob/master/pkg/volume/configmap/configmap.go
- kubernetes/pkg/volume/configmap/configmap.go at master · kubernetes/kubernetes · GitHub: https://github.com/kubernetes/kubernetes/blob/master/pkg/volume/configmap/configmap.go#L334
- Kubernetes ConfigMap and Secret Not Mounting in Pod — Every Fix (2026) | DevOpsBoys: https://devopsboys.com/blog/kubernetes-configmap-secret-not-mounting-fix-2026
- ConfigMap error handling in deployments : r/kubernetes: https://www.reddit.com/r/kubernetes/comments/j0zjcd/configmap_error_handling_in_deployments
- Unable to intercept deployement · Issue #3768: https://github.com/telepresenceio/telepresence/issues/3768
- Kubernetes "MountVolume.SetUp failed" / FailedMount - Fix in ...: https://latchkey.dev/learn/kubernetes/k8s-failedmount-setup-failed
- Kubernetes Error Guide: 'MountVolume.SetUp failed for: https://devopsaitoolkit.com/blog/kubernetes-error-mountvolume-setup-failed
- Kubernetes Error Guide: 'Warning FailedMount': https://devopsaitoolkit.com/blog/kubernetes-error-failedmount
- KUBERNETES CHALLENGE 4 problem with configmap: https://kodekloud.com/community/t/kubernetes-challenge-4-problem-with-configmap/121354

## How this was verified
Tests ran in an isolated container (`docker run --rm --network none`), replaying the sandbox command above. Evidence captured at 2026-10-06T16:57:22+00:00.

---
Opened by Mender for human review. Do not auto-merge; a person must review and merge this PR.