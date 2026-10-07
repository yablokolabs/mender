# Root cause: Checkout pod stuck in ContainerCreating due to ConfigMap key typo in deployment manifest

Service `checkout` in namespace `shop`.

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

## Tavily sources
Queries: "configmap references non-existent config key" Kubernetes FailedMount; Kubernetes ConfigMap volume items key typo validation error; FailedMount SetUp failed volume configmap non-existent key
- [Core DNS missing NodeHosts key in Configmap · Issue #9274 · k3s-io/k3s · GitHub](https://github.com/k3s-io/k3s/issues/9274) — safderali5

opened on Jan 19, 2024

Issue body actions

When deploying latest k3s version v1.29.0+k3s1 the coredns pod is stuck in ContainerCreating stage as it cannot find the key NodeHosts in configmap coredns. When looking at the manifests definitions, it looks the problem is real.

Upon searching k3s documentation there is no mention of how to specify those NodeHosts without manually editing configmap after deployment.

Error:  
 Warning FailedMount 85s (x19 over 23m) kubelet MountVolume.SetUp failed for volume "config-volume" : configmap references non-existent config key: NodeHosts

Manifests Link:  
 

Reactions are currently unavailable

## Activity

Sign up for free to join this conversation on GitHub. Already have an account? Sign in to comment

## Metadata

## Metadata [...] Skip to content   
 
 

## Navigation Menu

Sign in

Appearance settings

Sign in

Sign up

Appearance settings

You signed in with another tab or window. Reload to refresh your session. You signed out in another tab or window. Reload to refresh your session. You switched accounts on another tab or window. Reload to refresh your session. Dismiss alert

{{ message }}

k3s-io   /  k3s  Public

 Notifications  You must be signed in to change notification settings
 Fork 2.7k
 Star  34.1k

# Core DNS missing NodeHosts key in Configmap #9274

Copy link

Copy link

Closed

Closed

Core DNS missing NodeHosts key in Configmap#9274

Copy link

Assignees

brandondfmoral2

Milestone

v1.29.2+k3s1

## Description

@safderali5

safderali5

opened on Jan 19, 2024

Issue body actions [...] ## Metadata

## Metadata

### Assignees

 @brandond

  brandond
 @fmoral2

  fmoral2

### Labels

No labels

No labels

No type

 K3s Development

  Status

  Done Issue

  Show more project fields

### Milestone

 v1.29.2+k3s1

None yet

No branches or pull requests

## Issue actions

You can’t perform that action at this time.
- [Kubernetes ConfigMap and Secret Not Mounting in Pod — Every Fix (2026) | DevOpsBoys](https://devopsboys.com/blog/kubernetes-configmap-secret-not-mounting-fix-2026) — ## How ConfigMap/Secret Mounting Works

Kubernetes mounts ConfigMaps and Secrets in two ways:

1. Environment variables — values injected into the container's environment
2. Volume mounts — files written to a directory inside the container

Both have different failure modes.

## Error 1: Pod Stuck in `CreateContainerConfigError`

```
kubectl get pods kubectl  get  pods # NAME READY STATUS RESTARTS # NAME READY STATUS RESTARTS# myapp 0/1 CreateContainerConfigError 0# myapp 0/1 CreateContainerConfigError 0  kubectl describe pod myapp kubectl  describe  pod  myapp# Events:# Events:# Error: couldn't find key DB_HOST in ConfigMap default/app-config# Error: couldn't find key DB_HOST in ConfigMap default/app-config
```

Cause: You referenced a key in the ConfigMap that doesn't exist.

yaml [...] yaml

```
# BAD — key name mismatch # BAD — key name mismatchenvFrom: envFrom: - configMapRef: - configMapRef: name: app-config  name: app-config  env: env: - name: DB_HOST - name: DB_HOST valueFrom:  valueFrom: configMapKeyRef:  configMapKeyRef: name: app-config  name: app-config key: DB_HOST # ← This key must exist in the ConfigMap  key: DB_HOST  # ← This key must exist in the ConfigMap
```

Check what keys actually exist:

bash

```
kubectl get configmap app-config -o jsonpath='{.data}' | jq keys kubectl  get  configmap app-config -o jsonpath='{.data}'  | jq  keys
```

Fix: Either add the missing key to the ConfigMap or correct the key name in the pod spec.

bash [...] yaml

```
env: env: - name: FEATURE_FLAG - name: FEATURE_FLAG valueFrom:  valueFrom: configMapKeyRef:  configMapKeyRef: name: feature-flags  name: feature-flags key: ENABLE_DARK_MODE  key: ENABLE_DARK_MODE optional: true # ← Pod starts even if ConfigMap/key doesn't exist  optional: true # ← Pod starts even if ConfigMap/key doesn't exist
```

`optional: true` means if the ConfigMap or key doesn't exist, the env var is just empty instead of crashing the pod. Check if the ConfigMap actually has the key:

bash

```
kubectl get configmap feature-flags -o yaml kubectl  get  configmap feature-flags -o  yaml
```

## Debugging Checklist

bash
- [Configure a Pod to Use a ConfigMap | Kubernetes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-pod-configmap) — ### Optional references

A ConfigMap reference may be marked optional. If the ConfigMap is non-existent, the mounted volume will be empty. If the ConfigMap exists, but the referenced key is non-existent, the path will be absent beneath the mount point. See Optional ConfigMaps for more details.

### Mounted ConfigMaps are updated automatically

When a mounted ConfigMap is updated, the projected content is eventually updated too. This applies in the case where an optionally referenced ConfigMap comes into existence after a pod has started. [...] If you run this pod, and there is no ConfigMap named `a-config`, the output is empty. If you run this pod, and there is a ConfigMap named `a-config` but that ConfigMap doesn't have a key named `akey`, the output is also empty. If you do set a value for `akey` in the `a-config` ConfigMap, this pod prints that value and then terminates.

You can also mark the volumes and files provided by a ConfigMap as optional. Kubernetes always creates the mount paths for the volume, even if the referenced ConfigMap or key doesn't exist. For example, the following Pod specification marks a volume that references a ConfigMap as optional: [...] ## Restrictions

 You must create the `ConfigMap` object before you reference it in a Pod specification. Alternatively, mark the ConfigMap reference as `optional` in the Pod spec (see Optional ConfigMaps). If you reference a ConfigMap that doesn't exist and you don't mark the reference as `optional`, the Pod won't start. Similarly, references to keys that don't exist in the ConfigMap will also prevent the Pod from starting, unless you mark the key references as `optional`.
 If you use `envFrom` to define environment variables from ConfigMaps, keys that are considered invalid will be skipped. The pod will be allowed to start, but the invalid names will be recorded in the event log (`InvalidVariableNames`). The log message lists each skipped key. For example:
- ["configmap references non-existent config key"?](https://stackoverflow.com/questions/62312144/why-does-kubernetes-report-configmap-references-non-existent-config-key) — Why does Kubernetes report: "configmap references non-existent config key"? ... I tried to delete the configmap and the pod and then recreate them
- [Conftest: configmap references non-existent config key: *** ...](https://github.com/aquasecurity/starboard/issues/509) — failed for volume "policies" : configmap references non-existent config key: The scan Job has completed even though the ConfigMap was updated.
- [kubernetes/pkg/volume/configmap/configmap.go at cfd69463deeebfc5ae8a0813d7d2b125033c4aca · kubernetes/kubernetes · GitHub](https://github.com/kubernetes/kubernetes/blob/cfd69463deeebfc5ae8a0813d7d2b125033c4aca/pkg/volume/configmap/configmap.go) — Title: kubernetes/pkg/volume/configmap/configmap.go at cfd69463deeebfc5ae8a0813d7d2b125033c4aca · kubernetes/kubernetes · GitHub
You signed in with another tab or window. You switched accounts on another tab or window. Licensed under the Apache License, Version 2.0 (the "License");. you may not use this file except in compliance with the License. You may obtain a copy of the License at. See the License for the specific language governing permissions and. v1 "k8s.io/api/core/v1". "k8s.io/apimachinery/pkg/api/errors". metav1 "k8s.io/apimachinery/pkg/apis/meta/v1". "k8s.io/apimachinery/pkg/types". "k8s.io/kubernetes/pkg/volume". volumeutil "k8s.io/kubernetes/pkg/volume/util". // ProbeVolumePlugins is the entry point for plugin detection in a package. getConfigMap func(namespace, name string) (\*v1.ConfigMap, error). var \_ volume.VolumePlugin = &configMapPlugin{}. func getPath(uid types.UID, volName string, host volume.VolumeHost) string {. func (plugin \*configMapPlugin) Init(host volume.VolumeHost) error {. func (plugin \*configMapPlugin) GetPluginName() string {. func (plugin \*configMapPlugin) GetVolumeName(spec \*volume.Spec) (string, error) {. return "", fmt.Errorf("Spec does not reference a ConfigMap volume type"). func (plugin \*configMapPlugin) CanSupport(spec \*volume.Spec) bool {. return spec.Volume != nil && spec.Volume.ConfigMap != nil. func (plugin \*configMapPlugin) RequiresRemount(spec \*volume.Spec) bool {. func (plugin \*configMapPlugin) SupportsMountOption() bool {. func (plugin \*configMapPlugin) SupportsBulkVolumeVerification() bool {. func (plugin \*configMapPlugin) NewMounter(spec \*volume.Spec, pod \*v1.Pod, opts volume.VolumeOptions) (volume.Mounter, error) {. volume.NewCachedMetrics(volume.NewMetricsDu(getPath(pod.UID, spec.Name(), plugin.host))),. func (plugin \*configMapPlugin) NewUnmounter(volName string, podUID types.UID) (volume.Unmounter, error) {. volume.NewCachedMetrics(volume.NewMetricsDu(getPath(podUID, volName, plugin.host))),. func (plugin \*configMapPlugin) ConstructVolumeSpec(volumeName, mountPath string) (\*volume.Spec, error) {. var \_ volume.Volume = &configMapVolume{}. func (sv \*configMapVolume) GetPath() string {. // and placing them into the volume on the host. // This is the spec for the volume that this plugin wraps. func (b \*configMapVolumeMounter) SetUp(mounterArgs volume.MounterArgs) error {. return b.SetUpAt(b.GetPath(), mounterArgs). func (b \*configMapVolumeMounter) SetUpAt(dir string, mounterArgs volume.MounterArgs) error {. klog.V(3).Infof("Setting up volume %v for pod %v at %v", b.volName, b.pod.UID, dir). wrapped, err := b.plugin.host.NewWrapperMounter(b.volName, wrappedVolumeSpec(), &b.pod, \*b.opts). configMap, err := b.getConfigMap(b.pod.Namespace, b.source.Name). klog.Errorf("Couldn't get configMap %v/%v: %v", b.pod.Namespace, b.source.Name, err). if err := volumeutil.MakeNestedMountpoints(b.volName, dir, b.pod); err != nil {. unmounter, unmountCreateErr := b.plugin.NewUnmounter(b.volName, b.podUID). writerContext := fmt.Sprintf("pod %v/%v volume %v", b.pod.Namespace, b.pod.Name, b.volName). klog.Errorf("Error writing payload to dir: %v", err). err = volume.SetVolumeOwnership(b, mounterArgs.FsGroup, nil /\*fsGroupChangePolicy\*/, volumeutil.FSGroupCompleteHook(b.plugin, nil)). func MakePayload(mappings []v1.KeyToPath, configMap \*v1.ConfigMap, defaultMode \*int32, optional bool) (map[string]volumeutil.FileProjection, error) {. for name, data := range configMap.BinaryData {. func getVolumeSource(spec \*volume.Spec) (\*v1.ConfigMapVolumeSource, bool) {. if spec.Volume != nil && spec.Volume.ConfigMap != nil {.
- [kubernetes/pkg/volume/configmap/configmap.go at master · kubernetes/kubernetes · GitHub](https://github.com/kubernetes/kubernetes/blob/master/pkg/volume/configmap/configmap.go) — Title: kubernetes/pkg/volume/configmap/configmap.go at master · kubernetes/kubernetes · GitHub
You signed in with another tab or window. You switched accounts on another tab or window. Licensed under the Apache License, Version 2.0 (the "License");. you may not use this file except in compliance with the License. You may obtain a copy of the License at. See the License for the specific language governing permissions and. v1 "k8s.io/api/core/v1". "k8s.io/apimachinery/pkg/api/errors". metav1 "k8s.io/apimachinery/pkg/apis/meta/v1". "k8s.io/apimachinery/pkg/types". "k8s.io/kubernetes/pkg/features". "k8s.io/kubernetes/pkg/volume". volumeutil "k8s.io/kubernetes/pkg/volume/util". // ProbeVolumePlugins is the entry point for plugin detection in a package. getConfigMap func(namespace, name string) (\*v1.ConfigMap, error). var \_ volume.VolumePlugin = &configMapPlugin{}. func getPath(uid types.UID, volName string, host volume.VolumeHost) string {. func (plugin \*configMapPlugin) Init(host volume.VolumeHost) error {. func (plugin \*configMapPlugin) GetPluginName() string {. func (plugin \*configMapPlugin) GetVolumeName(spec \*volume.Spec) (string, error) {. return "", fmt.Errorf("Spec does not reference a ConfigMap volume type"). func (plugin \*configMapPlugin) CanSupport(spec \*volume.Spec) bool {. return spec.Volume != nil && spec.Volume.ConfigMap != nil. func (plugin \*configMapPlugin) RequiresRemount(spec \*volume.Spec) bool {. func (plugin \*configMapPlugin) SupportsMountOption() bool {. func (plugin \*configMapPlugin) SupportsSELinuxContextMount(spec \*volume.Spec) (bool, error) {. func (plugin \*configMapPlugin) NewMounter(spec \*volume.Spec, pod \*v1.Pod) (volume.Mounter, error) {. volume.NewCachedMetrics(volume.NewMetricsDu(getPath(pod.UID, spec.Name(), plugin.host))),. func (plugin \*configMapPlugin) NewUnmounter(volName string, podUID types.UID) (volume.Unmounter, error) {. volume.NewCachedMetrics(volume.NewMetricsDu(getPath(podUID, volName, plugin.host))),. func (plugin \*configMapPlugin) ConstructVolumeSpec(volumeName, mountPath string) (volume.ReconstructedVolume, error) {. var \_ volume.Volume = &configMapVolume{}. // and placing them into the volume on the host. // This is the spec for the volume that this plugin wraps. func (b \*configMapVolumeMounter) SetUp(mounterArgs volume.MounterArgs) error {. return b.SetUpAt(b.GetPath(), mounterArgs). func (b \*configMapVolumeMounter) SetUpAt(dir string, mounterArgs volume.MounterArgs) error {. klog.V(3).Infof("Setting up volume %v for pod %v at %v", b.volName, b.pod.UID, dir). wrapped, err := b.plugin.host.NewWrapperMounter(b.volName, wrappedVolumeSpec(), &b.pod). configMap, err := b.getConfigMap(b.pod.Namespace, b.source.Name). klog.Errorf("Couldn't get configMap %v/%v: %v", b.pod.Namespace, b.source.Name, err). if err := volumeutil.MakeNestedMountpoints(b.volName, dir, b.pod); err != nil {. unmounter, unmountCreateErr := b.plugin.NewUnmounter(b.volName, b.podUID). writerContext := fmt.Sprintf("pod %v/%v volume %v", b.pod.Namespace, b.pod.Name, b.volName). setPerms := func(\_ string) error {. // change the permissions on the whole volume and not only in the timestamp directory. klog.Errorf("Error writing payload to dir: %v", err). func MakePayload(mappings []v1.KeyToPath, configMap \*v1.ConfigMap, defaultMode \*int32, defaultUser \*int64, optional bool) (map[string]volumeutil.FileProjection, error) {. func getVolumeSource(spec \*volume.Spec) (\*v1.ConfigMapVolumeSource, bool) {. if spec.Volume != nil && spec.Volume.ConfigMap != nil {.
- [kubernetes/pkg/volume/configmap/configmap.go at master · kubernetes/kubernetes · GitHub](https://github.com/kubernetes/kubernetes/blob/master/pkg/volume/configmap/configmap.go#L334) — Title: kubernetes/pkg/volume/configmap/configmap.go at master · kubernetes/kubernetes · GitHub
You signed in with another tab or window. You switched accounts on another tab or window. Licensed under the Apache License, Version 2.0 (the "License");. you may not use this file except in compliance with the License. You may obtain a copy of the License at. See the License for the specific language governing permissions and. v1 "k8s.io/api/core/v1". "k8s.io/apimachinery/pkg/api/errors". metav1 "k8s.io/apimachinery/pkg/apis/meta/v1". "k8s.io/apimachinery/pkg/types". "k8s.io/kubernetes/pkg/features". "k8s.io/kubernetes/pkg/volume". volumeutil "k8s.io/kubernetes/pkg/volume/util". // ProbeVolumePlugins is the entry point for plugin detection in a package. getConfigMap func(namespace, name string) (\*v1.ConfigMap, error). var \_ volume.VolumePlugin = &configMapPlugin{}. func getPath(uid types.UID, volName string, host volume.VolumeHost) string {. func (plugin \*configMapPlugin) Init(host volume.VolumeHost) error {. func (plugin \*configMapPlugin) GetPluginName() string {. func (plugin \*configMapPlugin) GetVolumeName(spec \*volume.Spec) (string, error) {. return "", fmt.Errorf("Spec does not reference a ConfigMap volume type"). func (plugin \*configMapPlugin) CanSupport(spec \*volume.Spec) bool {. return spec.Volume != nil && spec.Volume.ConfigMap != nil. func (plugin \*configMapPlugin) RequiresRemount(spec \*volume.Spec) bool {. func (plugin \*configMapPlugin) SupportsMountOption() bool {. func (plugin \*configMapPlugin) SupportsSELinuxContextMount(spec \*volume.Spec) (bool, error) {. func (plugin \*configMapPlugin) NewMounter(spec \*volume.Spec, pod \*v1.Pod) (volume.Mounter, error) {. volume.NewCachedMetrics(volume.NewMetricsDu(getPath(pod.UID, spec.Name(), plugin.host))),. func (plugin \*configMapPlugin) NewUnmounter(volName string, podUID types.UID) (volume.Unmounter, error) {. volume.NewCachedMetrics(volume.NewMetricsDu(getPath(podUID, volName, plugin.host))),. func (plugin \*configMapPlugin) ConstructVolumeSpec(volumeName, mountPath string) (volume.ReconstructedVolume, error) {. var \_ volume.Volume = &configMapVolume{}. // and placing them into the volume on the host. // This is the spec for the volume that this plugin wraps. func (b \*configMapVolumeMounter) SetUp(mounterArgs volume.MounterArgs) error {. return b.SetUpAt(b.GetPath(), mounterArgs). func (b \*configMapVolumeMounter) SetUpAt(dir string, mounterArgs volume.MounterArgs) error {. klog.V(3).Infof("Setting up volume %v for pod %v at %v", b.volName, b.pod.UID, dir). wrapped, err := b.plugin.host.NewWrapperMounter(b.volName, wrappedVolumeSpec(), &b.pod). configMap, err := b.getConfigMap(b.pod.Namespace, b.source.Name). klog.Errorf("Couldn't get configMap %v/%v: %v", b.pod.Namespace, b.source.Name, err). if err := volumeutil.MakeNestedMountpoints(b.volName, dir, b.pod); err != nil {. unmounter, unmountCreateErr := b.plugin.NewUnmounter(b.volName, b.podUID). writerContext := fmt.Sprintf("pod %v/%v volume %v", b.pod.Namespace, b.pod.Name, b.volName). setPerms := func(\_ string) error {. // change the permissions on the whole volume and not only in the timestamp directory. klog.Errorf("Error writing payload to dir: %v", err). func MakePayload(mappings []v1.KeyToPath, configMap \*v1.ConfigMap, defaultMode \*int32, defaultUser \*int64, optional bool) (map[string]volumeutil.FileProjection, error) {. func getVolumeSource(spec \*volume.Spec) (\*v1.ConfigMapVolumeSource, bool) {. if spec.Volume != nil && spec.Volume.ConfigMap != nil {.
- [Kubernetes ConfigMap and Secret Not Mounting in Pod — Every Fix (2026) | DevOpsBoys](https://devopsboys.com/blog/kubernetes-configmap-secret-not-mounting-fix-2026) — | Error | Cause | Fix |
 --- 
| `CreateContainerConfigError` | Missing key in ConfigMap/Secret | Add key or fix name |
| Secret not found | Wrong namespace | Create in correct namespace |
| Stale env vars | Env vars baked at pod start | `kubectl rollout restart` |
| Missing files in volume | `items` filtering | Remove `items` or add missing key |
| Permission denied | Wrong file mode | Set `defaultMode: 0400` |
| Files missing after `subPath` | Volume replaced directory | Use `subPath` correctly |
| Empty optional env var | ConfigMap/key doesn't exist | Check ConfigMap exists |

ConfigMap and Secret issues are almost always a namespace mismatch, a key name typo, or forgetting to restart the pod after an update.

## Did this fix work?

Tell us what needs improving. No account required. [...] exec <pod-name> -- env | grep -i <your-var> kubectl  exec <pod-name> --  env  | grep -i <your-var>kubectl exec <pod-name> -- ls /path/to/mount/ kubectl  exec <pod-name> --  ls /path/to/mount/kubectl exec <pod-name> -- cat /path/to/mount/<file> kubectl  exec <pod-name> --  cat /path/to/mount/< file>  # 5. Check pod spec for typos# 5. Check pod spec for typoskubectl get pod <pod-name> -o yaml | grep -A 10 configMapKeyRef kubectl  get  pod <pod-name> -o  yaml  | grep -A  10  configMapKeyRefkubectl get pod <pod-name> -o yaml | grep -A 10 secretKeyRef kubectl  get  pod <pod-name> -o  yaml  | grep -A  10  secretKeyRef [...] yaml

```
# BAD — key name mismatch # BAD — key name mismatchenvFrom: envFrom: - configMapRef: - configMapRef: name: app-config  name: app-config  env: env: - name: DB_HOST - name: DB_HOST valueFrom:  valueFrom: configMapKeyRef:  configMapKeyRef: name: app-config  name: app-config key: DB_HOST # ← This key must exist in the ConfigMap  key: DB_HOST  # ← This key must exist in the ConfigMap
```

Check what keys actually exist:

bash

```
kubectl get configmap app-config -o jsonpath='{.data}' | jq keys kubectl  get  configmap app-config -o jsonpath='{.data}'  | jq  keys
```

Fix: Either add the missing key to the ConfigMap or correct the key name in the pod spec.

bash
- [ConfigMap error handling in deployments : r/kubernetes](https://www.reddit.com/r/kubernetes/comments/j0zjcd/configmap_error_handling_in_deployments) — If either the name (of the ConfigMap) or the key we want to reference is wrong, the entire container won't come up. This makes it extremely
- [Unable to intercept deployement · Issue #3768](https://github.com/telepresenceio/telepresence/issues/3768) — ... messages from the cluster I see: MountVolume.SetUp failed for volume "traffic-config" : configmap references non-existent config key: {MyServi..
- [Kubernetes "MountVolume.SetUp failed" / FailedMount - Fix in ...](https://latchkey.dev/learn/kubernetes/k8s-failedmount-setup-failed) — The kubelet tried to set up a volume for the pod and failed. For Secret/ConfigMap volumes this almost always means the source object (or a referenced key) does not exist; for CSI volumes the driver could not provision or attach it.
- [Kubernetes Error Guide: 'MountVolume.SetUp failed for](https://devopsaitoolkit.com/blog/kubernetes-error-mountvolume-setup-failed) — ## Exact Error Message

`MountVolume.SetUp failed` is a kubelet event raised when it cannot make a volume available inside a pod’s filesystem. It appears in `kubectl describe pod` events, in several variants depending on the underlying cause:

```
Warning FailedMount 18s (x7 over 2m13s) kubelet MountVolume.SetUp failed for volume "app-config" : configmap "app-config" not foundWarning FailedMount 18s (x7 over 2m13s) kubelet MountVolume.SetUp failed for volume "app-config" : configmap "app-config" not found
```

```
Warning FailedMount 31s kubelet MountVolume.SetUp failed for volume "tls-secret" : secret "tls-secret" not foundWarning FailedMount 31s kubelet MountVolume.SetUp failed for volume "tls-secret" : secret "tls-secret" not found
``` [...] ```
kubectl apply -f config-demo.yaml kubectl  apply -f config-demo.yamlkubectl describe pod config-demo -n prod | grep -A4 Events kubectl  describe  pod config-demo -n  prod  |  grep -A4  Events
```

```
Warning FailedMount 10s kubelet MountVolume.SetUp failed for volume "app-config" : configmap "app-config" not foundWarning FailedMount 10s kubelet MountVolume.SetUp failed for volume "app-config" : configmap "app-config" not found
```

The pod is stuck in `ContainerCreating` until the ConfigMap is created in the `prod` namespace.

## Diagnostic Commands

Start with the pod events — they name the volume and the reason: [...] ## How to Reproduce the Error

Create a pod that mounts a ConfigMap that does not exist:

```
apiVersion: v1 apiVersion: v1kind: Pod kind: Podmetadata: metadata: name: config-demo  name: config-demo namespace: prod  namespace: prodspec: spec: containers:  containers: - name: app - name: app image: busybox:1.36  image: busybox:1.36 command: ["sleep", "3600"]  command: ["sleep", "3600"] volumeMounts:  volumeMounts: - name: app-config - name: app-config mountPath: /etc/app  mountPath: /etc/app volumes:  volumes: - name: app-config - name: app-config configMap:  configMap: name: app-config # never created  name: app-config  # never created
```
- [Kubernetes Error Guide: 'Warning FailedMount'](https://devopsaitoolkit.com/blog/kubernetes-error-failedmount) — Fix the 'Warning FailedMount ... MountVolume.SetUp failed for volume' event in Kubernetes by finding the missing secret, configmap, subPath, or permission behind it. Run these first before going deeper. Need a triage plan for this exact error? Paste your exact error and get a triage plan.
- [KUBERNETES CHALLENGE 4 problem with configmap](https://kodekloud.com/community/t/kubernetes-challenge-4-problem-with-configmap/121354) — Warning FailedMount 106s (x13 over 12m) kubelet MountVolume.SetUp failed for volume “conf” : configmap “redis-cluster-configmap” not found