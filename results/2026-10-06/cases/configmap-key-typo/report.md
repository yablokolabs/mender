# Root cause: Checkout pod stuck in ContainerCreating due to ConfigMap key typo

Service `checkout` in namespace `shop`.

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

## Tavily sources
Queries: Kubernetes ConfigMap volume mount failed non-existent config key error; configmap references non-existent config key MountVolume.SetUp failed; Kubernetes deployment ConfigMap items key typo config.yaml vs config.yamll
- [ConfigMap Not Mounting as Volume in Kubernetes | Buglyst](https://buglyst.com/learn/guides/kubernetes-configmap-not-mounting-debug) — A ConfigMap volume that fails to mount typically points to one of several root causes: the ConfigMap doesn't exist in the same namespace, the volume definition in the pod spec references a key that doesn't exist in the ConfigMap, the mount path is a subdirectory of an existing mount (overlap), or there's a silent failure in the kubelet (e.g., network issue reaching the API server, or the ConfigMap is too large). Because Kubernetes doesn't always surface a clear error for a missing key — it just skips it — you can end up with a pod that looks healthy but is missing critical configuration. Another common cause is a mismatch between the ConfigMap's data keys and the items field in the volume definition; if you specify items but misspell a key, the entire mount may silently drop to an empty [...] The 500s started after a routine Helm upgrade that added a new feature flag to the nginx configuration. The deployment rolled out without errors—no crash loops, no obvious failures. But when I exec'd into a pod, the /etc/nginx/conf.d directory was completely empty. The pod was running, but nginx couldn't find any server blocks.

I immediately checked the ConfigMap: it existed, had the right key 'default.conf'. Then I looked at the pod spec. The volumeMounts section referenced a volume named 'nginx-config' which pointed to the ConfigMap, but the 'items' field listed a key 'nginx-default.conf'—a typo from a developer's copy-paste. Kubernetes didn't throw an error; it just mounted an empty directory because none of the specified items matched actual keys. [...] Things that make this bug worse or harder to find.

 warningAssuming the mount path is created automatically – it must exist in the container image or the mount will fail.
 warningOverwriting critical system directories like /etc or /bin – always mount to a dedicated path.
 warningForgetting that subPath mounts do not get updated when the ConfigMap changes; they are updated only on pod restart.
 warningUsing items with a non-existent key – Kubernetes will not error but the file won't be created, leading to silent failures.
 warningMixing volumeMounts that target overlapping paths – only one mount wins, causing confusion.
 warningIgnoring pod events: always check `kubectl describe pod` for FailedMount events before deep diving.

( 07 )War story
- [Kubernetes JSON configMap not mounted - Stack Overflow](https://stackoverflow.com/questions/71805789/kubernetes-json-configmap-not-mounted) — Title: Kubernetes JSON configMap not mounted - Stack Overflow
Bring the best of human thought and AI automation together at your work. # Kubernetes JSON configMap not mounted. I am trying to map a configMap in JSON format to my docker image in Kubernetes I am using config npm package to fetch the configurations. The idea is that I will have a file development.json in /config directory from there the config package will pick it up. I am running ls is the config directory to see if the development.json file has been mounted but it is not. I want the /config to be replaced and only contain the development.json file. apiVersion: v1 kind: ConfigMap metadata: name: config-development namespace: default data: development.json: | { "production": false,. volumes: - name: config-volume configMap: name: config-development containers: - name: salesforce-compare-api image: XXXX command: ["ls"] args: ["config", "-la"] imagePullPolicy: Always env: - name: NODE_ENV value: "development" volumeMounts: - name: config-volume mountPath: /config/development.json. Usually, when the configmap cannot be mounted, the pod will not even start. volumeMounts: - name: config-volume mountPath: /config/development.json. This lead to the full configmap being mounted into a folder named development.json, while you actually only want to mount the one file. That said, if you config folder inside the container is otherwise empty, you can also drop the subpath and mount the configmap to the /config dir, since it will not override anything important. volumeMounts: - name: config-volume mountPath: /config. The development.json file is not listed in the /config directory. The /config directory is not empty but I read that if you do it without the subPath the whole /config directory in the docker container will be replaced with the mounted data. Find the answer to your question by asking. Kubernetes ConfigMap volume doesn't create file in container. 1") Mounted ConfigMap volume is not served entirely. 0") Why does Kubernetes report: "configmap references non-existent config key"? 0") ConfigMap volume is not mounting as volume along with secret. 0") Script mounted from ConfigMap not found inside Kubernetes container. Kubernetes ConfigMap mount single file instead of directory. 5") ConfigMap being mounted as a folder instead of file. 1") Kubernetes Java client: cannot mount an existing configMap to a Pod.
- [Kubernetes Error Guide: 'Warning FailedMount'](https://devopsaitoolkit.com/blog/kubernetes-error-failedmount) — ## Frequently Asked Questions

How is FailedMount different from “Unable to attach or mount volumes … timed out”? `FailedMount` with `MountVolume.SetUp failed` is the specific per-volume event that names the exact cause and fires immediately on each retry. The “timed out waiting for the condition” message is the kubelet’s aggregate summary after ~2 minutes and only lists volume names. Read the `FailedMount` event for the real reason.

My configMap exists but the mount still fails. Why? It is almost certainly in a different namespace than the pod, or a referenced `items` key does not exist within it. Volumes resolve config objects only within the pod’s own namespace. Verify with `kubectl get configmap  -n` . [...] ## How to Reproduce the Error

Mount a configMap that does not exist:

```
apiVersion: v1 apiVersion: v1kind: Pod kind: Podmetadata: metadata: name: failedmount-demo  name: failedmount-demospec: spec: containers:  containers: - name: app - name: app image: registry.k8s.io/pause:3.9  image: registry.k8s.io/pause:3.9 volumeMounts:  volumeMounts: - name: cfg - name: cfg mountPath: /etc/app  mountPath: /etc/app volumes:  volumes: - name: cfg - name: cfg configMap:  configMap: name: does-not-exist # never created  name: does-not-exist  # never created
```

```
kubectl apply -f failedmount-demo.yaml kubectl  apply -f failedmount-demo.yamlkubectl describe pod failedmount-demo | grep -A4 Events kubectl  describe  pod failedmount-demo  |  grep -A4  Events
``` [...] ```
Warning FailedMount 9s (x4 over 22s) kubelet MountVolume.SetUp failed for volume "cfg" : configmap "does-not-exist" not foundWarning FailedMount 9s (x4 over 22s) kubelet MountVolume.SetUp failed for volume "cfg" : configmap "does-not-exist" not found
```

The pod stays `ContainerCreating` and the event repeats until the configMap is created.

## Diagnostic Commands
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

bash [...] For volume-mounted ConfigMaps: Kubernetes syncs volume-mounted files automatically within 1–2 minutes (controlled by `kubelet` sync period). You don't need to restart for volume mounts — but in-process cache in your app may still hold stale values.

## Error 4: Volume-Mounted ConfigMap Shows Wrong Files

Symptom: You mount a ConfigMap as a volume but only some files appear, or the wrong content is there.

yaml

```
volumes: volumes: - name: config-volume - name: config-volume configMap:  configMap: name: app-config  name: app-config items: # ← Only specified items are mounted  items: # ← Only specified items are mounted - key: nginx.conf - key: nginx.conf path: nginx.conf  path: nginx.conf
```
- [Kubernetes Error Guide: 'MountVolume.SetUp failed for](https://devopsaitoolkit.com/blog/kubernetes-error-mountvolume-setup-failed) — ## How to Reproduce the Error

Create a pod that mounts a ConfigMap that does not exist:

```
apiVersion: v1 apiVersion: v1kind: Pod kind: Podmetadata: metadata: name: config-demo  name: config-demo namespace: prod  namespace: prodspec: spec: containers:  containers: - name: app - name: app image: busybox:1.36  image: busybox:1.36 command: ["sleep", "3600"]  command: ["sleep", "3600"] volumeMounts:  volumeMounts: - name: app-config - name: app-config mountPath: /etc/app  mountPath: /etc/app volumes:  volumes: - name: app-config - name: app-config configMap:  configMap: name: app-config # never created  name: app-config  # never created
``` [...] subPath / readOnly issues. A `subPath` referencing a non-existent path, or a read-only mount where the app expects to write.
 Projected ServiceAccount token problems. Audience/expiry misconfiguration on a projected token source.
 Cache sync timeout. The kubelet cannot populate its Secret/ConfigMap informer cache, often because the node’s credentials lack `get`/`watch` or the API server is slow. [...] Go to the kubelet itself for low-level mount errors:

```
ssh <NODE> 'sudo journalctl -u kubelet --since "5 min ago" | grep -i mount' ssh < NOD E> 'sudo journalctl -u kubelet --since "5 min ago" | grep -i mount'
```

```
kubelet: E0625 mount_linux.go: mount failed: exit status 32kubelet: E0625 mount_linux.go: mount failed: exit status 32kubelet: Output: mount.nfs: Connection timed outkubelet: Output: mount.nfs: Connection timed out
```

## Step-by-Step Resolution

### Missing Secret / ConfigMap

Create the object in the pod’s namespace, then recreate the pod (the kubelet retries automatically once it appears):
- [Conftest: configmap references non-existent config key: *****.rego · Issue #509 · aquasecurity/starboard · GitHub](https://github.com/aquasecurity/starboard/issues/509) — 🐛 bugSomething isn't workingSomething isn't working

Milestone

Release v0.10.1

## Description

@danielpacak

danielpacak

opened on Apr 19, 2021

Issue body actions

What steps did you take and what happened:

Modify `starboard-conftest-config` ConfigMap by deleting the `runs_as_root_user.rego` policy after a scan Job was created but before it was actually run. This ends up with with the following error and Pod stuck in the Pending status:

```
MountVolume.SetUp failed for volume "policies" : configmap references non-existent config key: conftest.policy.runs_as_root_user.rego 
```

What did you expect to happen:

The scan Job has completed even though the ConfigMap was updated.

Anything else you would like to add:

N/A

Environment: [...] Skip to content   
 
 

## Navigation Menu

Sign in

Appearance settings

Sign in

Sign up

Appearance settings

You signed in with another tab or window. Reload to refresh your session. You signed out in another tab or window. Reload to refresh your session. You switched accounts on another tab or window. Reload to refresh your session. Dismiss alert

{{ message }}

aquasecurity   /  starboard  Public

 Notifications  You must be signed in to change notification settings
 Fork 200
 Star  1.4k

# Conftest: configmap references non-existent config key: \\\\\.rego #509

Copy link

Copy link

Closed

#511

Closed

Conftest: configmap references non-existent config key: \\\\\.rego#509

#511

Copy link

Assignees

danielpacak

Labels

🐛 bugSomething isn't workingSomething isn't working [...] Anything else you would like to add:

N/A

Environment:

 Starboard version (use `starboard version`): v0.10.0
 Kubernetes version (use `kubectl version`): any
 OS (macOS 10.15, Windows 10, Ubuntu 19.10 etc): any

Reactions are currently unavailable

## Activity

Sign up for free to join this conversation on GitHub. Already have an account? Sign in to comment

## Metadata

## Metadata

### Assignees

 @danielpacak

  danielpacak

### Labels

🐛 bugSomething isn't workingSomething isn't working

No type

No projects

### Milestone

 Release v0.10.1

None yet

No branches or pull requests

## Issue actions

You can’t perform that action at this time.
- [Unable to intercept deployement · Issue #3768 · telepresenceio/telepresence · GitHub](https://github.com/telepresenceio/telepresence/issues/3768) — pitming

opened on Jan 15, 2025

Issue body actions

Describe the bug  
 error: connector.CreateIntercept: Back-off restarting failed container

In K8S messages from the cluster I see: MountVolume.SetUp failed for volume "traffic-config" : configmap references non-existent config key: {MyService}

Logs from tel-agent-init: error failed to insert --uid-owner rule in OUTPUT: running [/usr/sbin/iptables -t nat -I OUTPUT 3 -m owner --uid-owner 0 -j RETURN --wait]: exit status 4: iptables v1.8.10 (nf\_tables): RULE\_INSERT failed (No such file or directory): rule in chain OUTPUT

I suspect a configuration/conflict problem but don't have any clue on where to start investigating

logs are attached. Tell me if you need anything more
- [Configure a Pod to Use a ConfigMap | Kubernetes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-pod-configmap) — ### Optional references

A ConfigMap reference may be marked optional. If the ConfigMap is non-existent, the mounted volume will be empty. If the ConfigMap exists, but the referenced key is non-existent, the path will be absent beneath the mount point. See Optional ConfigMaps for more details.

### Mounted ConfigMaps are updated automatically

When a mounted ConfigMap is updated, the projected content is eventually updated too. This applies in the case where an optionally referenced ConfigMap comes into existence after a pod has started. [...] When `kubectl` creates a ConfigMap from inputs that are not ASCII or UTF-8, the tool puts these into the `binaryData` field of the ConfigMap, and not in `data`. Both text and binary data sources can be combined in one ConfigMap.

If you want to view the `binaryData` keys (and their values) in a ConfigMap, you can run `kubectl get configmap -o jsonpath='{.binaryData}'` .

Pods can load data from a ConfigMap that uses either `data` or `binaryData`.

## Optional ConfigMaps

You can mark a reference to a ConfigMap as optional in a Pod specification. If the ConfigMap doesn't exist, the configuration for which it provides data in the Pod (for example: environment variable, mounted volume) will be empty. If the ConfigMap exists, but the referenced key is non-existent the data is also empty. [...] If you run this pod, and there is no ConfigMap named `a-config`, the output is empty. If you run this pod, and there is a ConfigMap named `a-config` but that ConfigMap doesn't have a key named `akey`, the output is also empty. If you do set a value for `akey` in the `a-config` ConfigMap, this pod prints that value and then terminates.

You can also mark the volumes and files provided by a ConfigMap as optional. Kubernetes always creates the mount paths for the volume, even if the referenced ConfigMap or key doesn't exist. For example, the following Pod specification marks a volume that references a ConfigMap as optional:
- [ConfigMap Not Found: Fix Kubernetes Errors | AnyGen](https://www.anygen.io/showcase/configmap-not-found/index.html) — A minimal environment-variable reference is: env: - name: LOG\_LEVEL; valueFrom: configMapKeyRef: name: app-settings; key: LOG\_LEVEL. Keep app-settings and LOG\_LEVEL exact: Kubernetes object names and ConfigMap keys are not aliases, and a one-character rename is a different reference.

If you use Helm, inspect the rendered manifest before applying it: helm template RELEASE CHART -n production. The rendered metadata.namespace and ConfigMap reference must both resolve to production.

## Why does the ConfigMap exist but the Pod still not start?

The object can exist while the Pod still fails because the requested key is missing, a volume item maps a nonexistent key, or a ConfigMap reference is mandatory when the application can safely tolerate it being absent. [...] Can a Pod use a ConfigMap from another namespace?

No. Kubernetes requires the Pod and ConfigMap to be in the same namespace for Pod references. Put the ConfigMap in the Pod namespace or deploy the workload into the namespace holding the ConfigMap.

What happens if a ConfigMap key is missing?

A required configMapKeyRef or required volume item prevents the Pod from starting. Check keys with kubectl get configmap CONFIGMAP\_NAME -n NAMESPACE -o jsonpath='{.data}', then correct the key name or add the required key.

Should I set optional true to fix configmap not found? [...] Kubernetes documents optional references for both environment variables and volumes. Use optional: true only when the container has a deliberate fallback, such as LOG\_LEVEL defaulting to info. Do not use it to hide a required production configuration error; an empty mount or undefined variable can move failure from scheduling time to application startup.

For a mandatory application.yaml volume, do not set optional: true. Create the ConfigMap and key first, then start the workload.

## Can apply order or Kustomize cause ConfigMap not found?

Yes. A Pod can be created before its required ConfigMap exists, and generated ConfigMap names can change between builds. Kubernetes requires a non-optional ConfigMap to exist before a Pod references it.
- [SetUp failed for volume : r/kubernetes](https://www.reddit.com/r/kubernetes/comments/17njx4c/setup_failed_for_volume) — Is the configmap available in the same namespace? Yeah that's a pretty simple error. No configmap. I am new in Kubernetes. Can you help my how
- [Helm Values.yaml vs Kubernetes ConfigMaps](https://www.reddit.com/r/kubernetes/comments/jlovje/helm_valuesyaml_vs_kubernetes_configmaps) — Configmaps are for separating configuration from deployment. Without configmaps you'd have to download and redeploy your containers every time
- [ConfigMaps | Kubernetes](https://kubernetes.io/docs/concepts/configuration/configmap) — the case is different here   # from the key name in the ConfigMap.  # from the key name in the ConfigMap.  # from the key name in the ConfigMap.   valueFrom:  valueFrom:  valueFrom:   configMapKeyRef:  configMapKeyRef:  configMapKeyRef:   name: game-demo  # The ConfigMap this value comes from.  name: game-demo  # The ConfigMap this value comes from.  name:  game-demo  # The ConfigMap this value comes from.   key: player_initial_lives # The key to fetch.  key: player_initial_lives # The key to fetch.  key:  player_initial_lives  # The key to fetch.   - name: UI_PROPERTIES_FILE_NAME  - name: UI_PROPERTIES_FILE_NAME  name:  UI_PROPERTIES_FILE_NAME   valueFrom:  valueFrom:  valueFrom:   configMapKeyRef:  configMapKeyRef:  configMapKeyRef:   name: game-demo  name: game-demo  name:  game-demo [...] the name of the ConfigMap you want to mount.  # Provide the name of the ConfigMap you want to mount.  # Provide the name of the ConfigMap you want to mount.   name: game-demo  name: game-demo  name:  game-demo   # An array of keys from the ConfigMap to create as files  # An array of keys from the ConfigMap to create as files  # An array of keys from the ConfigMap to create as files   items:  items:  items:   - key: "game.properties"  - key: "game.properties"  key:  "game.properties"   path: "game.properties"  path: "game.properties"  path:  "game.properties"   - key: "user-interface.properties"  - key: "user-interface.properties"  key:  "user-interface.properties"   path: "user-interface.properties"  path: "user-interface.properties"  path:  "user-interface.properties" [...] ## ConfigMap object

A ConfigMap is an API object that lets you store configuration for other objects to use. Unlike most Kubernetes objects that have a `spec`, a ConfigMap has `data` and `binaryData` fields. These fields accept key-value pairs as their values. Both the `data` field and the `binaryData` are optional. The `data` field is designed to contain UTF-8 strings while the `binaryData` field is designed to contain binary data as base64-encoded strings.

The name of a ConfigMap must be a valid DNS subdomain name.

Each key under the `data` or the `binaryData` field must consist of alphanumeric characters, `-`, `_` or `.`. The keys stored in `data` must not overlap with the keys in the `binaryData` field.
- [Kubernetes ConfigMaps: Examples, Benefits & How to Use Them](https://www.groundcover.com/blog/kubernetes-configmap) — ## Kubernetes ConfigMap best practices

Consider the following best practices to get the most value from ConfigMaps.

### Test ConfigMaps before deployment

Errors in a ConfigMap, such as typos or broken indentation, could cause Kubernetes to fail to read the ConfigMap data properly. To mitigate this risk, consider testing ConfigMaps prior to deployment.

Kubernetes doesn’t offer a native way of testing ConfigMaps (other than applying them and checking whether they cause problems), but you can use external YAML linters, such as YAML Lint, to validate syntax.

### Version-control ConfigMaps [...] ## What is a Kubernetes ConfigMap?

In Kubernetes, a ConfigMap is an API object that can store data using a key-value pairs approach. Each key is a string with a corresponding value.

The primary purpose of ConfigMaps is to store configuration data that applications need to access at runtime. As we mentioned, this is useful because ConfigMaps are a handy way of separating configuration settings from containers themselves. This eliminates the need to hard-code configurations into containers and update the containers whenever configuration values change. It also reduces the risk that a container won’t run properly in one environment and experience an issue such as exit code 127 due to broken configuration settings.

### ConfigMap vs. environment variables
- [Kubernetes ConfigMap: What It Is & How to Use It · Dash0](https://www.dash0.com/knowledge/kubernetes-configmap-what-it-is-and-how-to-use-it) — A few things that aren't obvious until they've bitten you.

The 1 MiB limit is a hard ceiling, not a soft guideline. ConfigMaps are stored in etcd, and etcd caps request sizes at 1 MiB with no override flag. If you're pushing large files through a ConfigMap, use a volume or a dedicated config store instead. Even well below the limit, large ConfigMaps slow pod startup and add etcd load.

Everything is a string. ConfigMaps have no type system, so a value like `true` or `3` is text, and your application has to parse it. YAML's implicit typing makes this easy to miss: write `enabled: true` without quotes and the API server coerces it, but the container still receives the string `"true"`. Quote your values. [...] envFrom:

- configMapRef:

name: app-config

```

Every key becomes an environment variable of the same name. The catch: keys with dots in them, like `feature_flags.yaml`, aren't valid environment variable names, so they get silently skipped. The kubelet logs an event rather than failing the pod. If a value seems to be missing from the environment, this is the first thing to check.

### As files in a mounted volume

Mounting the ConfigMap as a volume projects each key as a file, with the key as the filename and the value as the file contents:

yaml

```

1234567891011

spec:

containers:

- name: app

image: my-app:latest

volumeMounts:

- name: config-volume

mountPath: /etc/app/config

volumes:

- name: config-volume

configMap:

name: app-config

``` [...] ## Creating a ConfigMap

A ConfigMap manifest needs almost nothing: a name and a `data` field with your key-value pairs. Keys may contain only alphanumeric characters plus `.`, `-`, and `_`. Here's one storing three application settings:

yaml

```

12345678910

apiVersion: v1

kind: ConfigMap

metadata:

name: app-config

data:

database_host: "db.production.svc.cluster.local"

log_level: "info"

feature_flags.yaml: |

new_checkout: true

dark_mode: false

```

Notice the two styles. `database_host` and `log_level` are simple property-style values. `feature_flags.yaml` uses the `|` block scalar to store an entire file's contents under one key, useful when your app expects a config file rather than individual variables.

Apply it like any other object:

bash

```

1
- [Kubernetes - ConfigMaps - GeeksforGeeks](https://www.geeksforgeeks.org/devops/kubernetes-configmap) — > Note: ConfigMaps are not secure (use Secrets for sensitive data) and have a 1 MB size limit. For larger files, use Kubernetes Volumes.

## Creating a ConfigMap

In Kubernetes, you can create a ConfigMap either using kubectl commands or a YAML manifest.

1. Using kubectl (imperative commands):

 From literal values:

```
kubectl create configmap demo-config --from-literal=database_host=172.138.0.1 --from-literal=debug_mode=1 --from-literal=log_level=verbose 
```

Screenshot-from-2025-09-14-23-04-32

 From a file:

```
kubectl create configmap demo-config --from-file=config.properties
```

2. Using a YAML manifest (declarative approach):  
 Create a file config.yaml with the following content: [...] geeksforgeeks

search icon

 Interview Prep

 DevOps
 Cloud Computing
 Git
 AWS
 Docker
 Kubernetes
 Microsoft Azure
 Google Cloud Platform
 Python
 Golang
 Operating System
 Computer Network

# Kubernetes - ConfigMaps

Last Updated : 21 Jan, 2026

A ConfigMap stores non-sensitive configuration data (like URLs, hostnames, or settings) in key-value pairs, separate from application code. It helps make applications portable and easy to manage across different environments. ConfigMaps can be used as:

 Environment variables
 Command-line arguments
 Mounted configuration files inside containers

Example: DATABASE\_HOST=localhost locally, and DATABASE\_HOST=my-service in the cloud. [...] ```
apiVersion: v1kind: ConfigMapmetadata: name: demo-configdata: database_host: "172.138.0.1" debug_mode: "1" log_level: "verbose"
```

Screenshot-from-2025-09-14-23-19-15

Then apply it to your cluster:

```
kubectl apply -f config.yaml
```

Screenshot-from-2025-09-14-23-21-30

This creates a ConfigMap named demo-config that stores your configuration data as key-value pairs, ready to be used by Pods in your cluster.

## Best Practices for ConfigMaps