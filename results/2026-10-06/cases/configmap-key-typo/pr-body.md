## Root cause
Deployment manifest references non-existent ConfigMap key 'config.yamll' (double 'l') instead of actual key 'config.yaml'

## Mechanism
1. Deployment manifest specifies ConfigMap volume 'app-config' with items.key=config.yamll [deploy.yaml]. 2. ConfigMap 'checkout-config' only contains key 'config.yaml' (single 'l') [configmap.yaml]. 3. Kubelet attempts to mount volume for new ReplicaSet pods (hash d69997d588) and fails with 'configmap references non-existent config key: config.yamll' [events]. 4. Pod remains in ContainerCreating because volume mount is required (optional: false) and cannot be satisfied [describe: PodReadyToStartContainers=False]. 5. Old ReplicaSet pods (hash 7694f54754) continue running because they were created before the faulty manifest was applied.

Confidence: 0.99 · Labels: configmap_key_typo, volume_mount_failure, container_creating, rolling_update

## Evidence relied on
- MountVolume.SetUp failed for volume "app-config" : configmap references non-existent config key: config.yamll
- items:
        - key: config.yamll
          path: config.yaml
- data:
  config.yaml: |
- PodReadyToStartContainers   False

## Change
Files: demo/manifests/deploy.yaml
Rationale: The Deployment manifest incorrectly referenced a ConfigMap key 'config.yamll' (double 'l') while the ConfigMap only contains 'config.yaml'. Changing the key to match the existing ConfigMap entry allows the volume to mount correctly, resolving the ContainerCreating state.

## Sandbox test results
Command: `python3 demo/app/check.py` — **PASSED** in 1 attempt(s)
- attempt 1: exit 0 in 0.7s — ok

## Tavily sources used
Queries: Kubernetes ConfigMap volume mount failed non-existent config key error; configmap references non-existent config key MountVolume.SetUp failed; Kubernetes deployment ConfigMap items key typo config.yaml vs config.yamll
- ConfigMap Not Mounting as Volume in Kubernetes | Buglyst: https://buglyst.com/learn/guides/kubernetes-configmap-not-mounting-debug
- Kubernetes JSON configMap not mounted - Stack Overflow: https://stackoverflow.com/questions/71805789/kubernetes-json-configmap-not-mounted
- Kubernetes Error Guide: 'Warning FailedMount': https://devopsaitoolkit.com/blog/kubernetes-error-failedmount
- Kubernetes ConfigMap and Secret Not Mounting in Pod — Every Fix (2026) | DevOpsBoys: https://devopsboys.com/blog/kubernetes-configmap-secret-not-mounting-fix-2026
- Kubernetes Error Guide: 'MountVolume.SetUp failed for: https://devopsaitoolkit.com/blog/kubernetes-error-mountvolume-setup-failed
- Conftest: configmap references non-existent config key: *****.rego · Issue #509 · aquasecurity/starboard · GitHub: https://github.com/aquasecurity/starboard/issues/509
- Unable to intercept deployement · Issue #3768 · telepresenceio/telepresence · GitHub: https://github.com/telepresenceio/telepresence/issues/3768
- Configure a Pod to Use a ConfigMap | Kubernetes: https://kubernetes.io/docs/tasks/configure-pod-container/configure-pod-configmap
- ConfigMap Not Found: Fix Kubernetes Errors | AnyGen: https://www.anygen.io/showcase/configmap-not-found/index.html
- SetUp failed for volume : r/kubernetes: https://www.reddit.com/r/kubernetes/comments/17njx4c/setup_failed_for_volume
- Helm Values.yaml vs Kubernetes ConfigMaps: https://www.reddit.com/r/kubernetes/comments/jlovje/helm_valuesyaml_vs_kubernetes_configmaps
- ConfigMaps | Kubernetes: https://kubernetes.io/docs/concepts/configuration/configmap
- Kubernetes ConfigMaps: Examples, Benefits & How to Use Them: https://www.groundcover.com/blog/kubernetes-configmap
- Kubernetes ConfigMap: What It Is & How to Use It · Dash0: https://www.dash0.com/knowledge/kubernetes-configmap-what-it-is-and-how-to-use-it
- Kubernetes - ConfigMaps - GeeksforGeeks: https://www.geeksforgeeks.org/devops/kubernetes-configmap

## How this was verified
Tests ran in an isolated container (`docker run --rm --network none`), replaying the sandbox command above. Evidence captured at 2026-10-06T19:18:41+00:00.

---
Opened by Mender for human review. Do not auto-merge; a person must review and merge this PR.