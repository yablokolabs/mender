# Root cause: checkout pod CrashLoopBackOff due to ConfigMap mount path mismatch

Service `checkout` in namespace `shop`.

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

## Tavily sources
Queries: Kubernetes ConfigMap volume mount path mismatch CrashLoopBackOff config file not found; Kubernetes deployment volumeMount mountPath ConfigMap items key path config.yaml; CrashLoopBackOff FATAL config file not found /etc/app/config.yaml Kubernetes
- [How to Fix CrashLoopBackOff in Kubernetes? - Komodor](https://komodor.com/learn/how-to-fix-crashloopbackoff-kubernetes-error) — Most CrashLoopBackOff “missing file” problems come from volume mounts (ConfigMaps, Secrets, PVCs) or an incorrect mountPath. First, confirm what Kubernetes intended to mount:

```
kubectl describe pod | sed -n '/Mounts:/,/Conditions:/p'
```

Then verify the file exists inside the container at the mount path:

```
kubectl exec -it -c -- ls -la  
kubectl exec -it -c -- cat /
```

### 2. Be Vigilant With Third-Party Services

If an application uses a third-party service and calls made to a service fail, then the service itself is the problem. Most errors are usually due to an error with the SSL certificate or network issues, so make sure those are functioning correctly. You can log into the container and manually reach the endpoints using `curl` to check. [...] | ConfigMap/Secret missing (often CreateContainerConfigError) Examples: configmap “” not found secret “” not found CreateContainerConfigError | Referenced ConfigMap/Secret does not exist in the namespace, name typo, wrong key, or wrong mount/envFrom reference. | – Create the missing ConfigMap/Secret in the same namespace.  – Fix the reference name/key in YAML (envFrom, valueFrom, or volumes).  – Redeploy rollout: kubectl rollout restart deploy/ -n . | [...] | Permission denied Examples: permission denied mkdir: can’t create directory open /path/file: permission denied | Running as non-root without correct permissions, volume mount ownership mismatch, read-only filesystem, or restrictive security context/policies. | – Set securityContext.runAsUser, runAsGroup, and fsGroup to match volume needs.  – Add an init container to chown/chmod the mounted path.  – Write to a writable path (e.g., /tmp) or mount an emptyDir for writable storage.  – Fix file ownership in the image (Dockerfile) if needed. |
- [Diagnose and Fix CrashLoopBackOff Caused by Missing Configuration Dependencies](https://oneuptime.com/blog/post/2026-02-09-crashloopbackoff-missing-config/view) — `# View current logs
kubectl logs myapp-6d5c4d8f9-x7k2p
# View logs from previous crash
kubectl logs myapp-6d5c4d8f9-x7k2p --previous
# Common error messages:
# Error: Environment variable DATABASE_URL not set
# Fatal: Cannot read configuration file /etc/app/config.yaml
# Error: Secret key 'api-token' not found`

## Diagnosing Missing ConfigMap Volumes

Required ConfigMaps mounted as volumes won't cause immediate container failure if missing. Instead, the pod stays in ContainerCreating status because Kubernetes cannot set up the volume. However, if the ConfigMap reference is optional, or if the ConfigMap exists but lacks a file the application expects, the container can start and then crash during application startup. [...] `# Check if ConfigMap exists
kubectl get configmap app-config
# View ConfigMap contents
kubectl describe configmap app-config
# Check pod volume mounts
kubectl get pod myapp-6d5c4d8f9-x7k2p -o json | jq '.spec.volumes'`

If the ConfigMap doesn't exist, create it before the pod can start successfully.

`apiVersion: v1
kind: ConfigMap
metadata:
name: app-config
data:
config.yaml: |
database:
host: postgres.default.svc.cluster.local
port: 5432
name: appdb
logging:
level: info
features:
new_ui: true`

Apply the ConfigMap and delete the failing pod to trigger a new deployment.

`kubectl apply -f configmap.yaml
kubectl delete pod myapp-6d5c4d8f9-x7k2p`

## Fixing Missing Secret References [...] env:
- name: DATABASE_URL
valueFrom:
secretKeyRef:
name: app-secrets
key: database-url
optional: true
- name: API_TOKEN
valueFrom:
secretKeyRef:
name: app-secrets
key: api-token
optional: true
volumeMounts:
- name: config
mountPath: /etc/config
containers:
- name: app
image: myapp:v1.0
# Main container configuration
volumes:
- name: config
configMap:
name: app-config`
- [Pod with configmap CrashLoopBackOff : r/kubernetes](https://www.reddit.com/r/kubernetes/comments/zvz0mi/pod_with_configmap_crashloopbackoff) — Make sure you only mount the single named.conf.options file with volumeMounts: I think the ConfigMap was mounted wrong, make sure you didn't
- [Kubernetes CrashLoopBackOff: Finding Missing ConfigMaps](https://www.youtube.com/watch?v=Hlk6mUiURxo) — `kubectl get events` to correlate scheduling, volume mounting, and node allocation issues across timestamps.
Exit Code Decoded (Container Fingerprints):
Exit Code 0: Successful execution.
Exit Code 1: Application error, missing configuration, or unhandled exception.
Exit Code 137: OOMKilled (Out Of Memory).
Exit Code 139: SIGSEGV (Segmentation Fault).
Volume Mounts vs. Environment Variables: Learn why updating a ConfigMap mounted via environment variables requires a manual pod restart, whereas volume mounts dynamically update files (with the exception of `subPath`, which breaks automatic updates).
Proactive Fallback Strategies: Implement `optional: true` in pod specifications to gracefully handle missing configuration values without triggering total deployment crashes. [...] [5:28] Subpath is this brilliant feature that lets you mount a single file from a config map into a directory without overwriting everything else in that folder. It's great. However, as our
[5:37] sources highlight, and this is a big one, when you use subpath, the file is not automatically updated when the config map changes. Even for volumes,
[5:45] you must restart the pod. It completely breaks the automatic update feature. If you change that config map, you still have to manually bounce the pod. You
[5:53] definitely want to keep that in mind when you're designing your configuration strategy. You know, sometimes the absolute best fix is just preventing the crash from happening in the first place. [...] [4:54] It's kind of a tale of two methods. On one hand, if you inject a config map as environment variables, those values are completely baked in at pod startup. If
[5:02] you update the config map later, well, the running pods are not going to see those changes until they are manually restarted. But on the other hand, if you consume the config map as a volume
[5:10] mount, Kubernetes updates the files automatically inside the running container. It's a huge difference. So, if your pod is crash looping because of
[5:17] bad environment variables, simply fixing the config map isn't going to cut it.
[5:21] You actually have to go in and restart the pod for it to pick up the fix. But beware, there is a massive gotcha here.
- [Kubernetes CrashLoopBackOff: Finding Missing ConfigMaps](https://www.youtube.com/watch?v=Hlk6mUiURxo&xstg=CAMSBhUDze3xHw%3D%3D) — dreaded CrashLoopBackOff error caused by missing configuration dependencies. We explore how missing ConfigMaps, Secrets, and malformed volume
- [Configmap and Kubernetes : Overriding Configuration Files](https://medium.com/@dheeraj007tripathi/configmap-and-kubernetes-overriding-configuration-files-5db9e6da08c9) — Title: Configmap and Kubernetes : Overriding Configuration Files
## dheeraj tripathi. # Configmap and Kubernetes : Overriding Configuration Files. You might be familiar with the concept of docker volumes wherein you can share the host directory with the container and any change in the shared directory on the host would reflect on the container. It is an easier way of managing and overriding application configurations. In Kubernetes configmap provides you a way to handle or decouple the application configurations of the containers running in the pod. You can override application configuration files at the runtime, and we will see how! Let’s say we need to run tomcat inside a pod, but want to override the default server.xml and context.xml files using helm chart. Using the configmap above we are creating 2 keys namely context.xml and server.xml which will have content as defined here. Next, we define the deployment as below. Notice the “annotation” section above which allows the deployment to read the configmap. Now, to override the configuration files we will create volume Mounts with mountPath =<full path of the file>, and subPath=<file name>. Specifying subPath ensures that only the specified file is overidden, and any other existing content in the mount directory are retained. Also, under the volumes section specify the configmap details with the key and path to be overriden. Define service.yml as below to expose the tomcat service over a NodePort. To run the code above, clone the repo , browse to helm-configmap directory, and run. ## Get dheeraj tripathi’s stories in your inbox. Join Medium for free to get updates from this writer. Remember me for faster sign in. Press enter or click to view image in full size. tomcat NodePort 10.103.159.164 <none> 8080:31290/TCP 1h. Now exec into any of the pods and you can see that the default config file has been overridden. Also, the service can be acccessed on 192.168.99.100:31290. **Note :** The above configuration runs tomcat as root inside the container, it is a good practice to run processes as non-root. ## Written by dheeraj tripathi.
- [Kubernetes ConfigMap Guide: How k8s Handles Pod Configuration - Tecktol](https://tecktol.com/kubernetes-configmap) — Kubernetes ConfigMaps provide a flexible way to decouple configuration data from container images, allowing you to **manage app settings without rebuilding or redeploying workloads**. This guide walks through every practical way to create, manage, and mount ConfigMaps in Kubernetes — from simple literals and YAML files to more advanced techniques involving external sources, namespaces, and volume mounts. Kubernetes offers multiple ways to create a ConfigMap depending on your configuration source — such as literal values, files, directories, environment variables, or even external sources like JSON, databases, or URLs. Below is a quick list of common methods, each linked to its detailed explanation section for easy navigation. Use a `.env` file containing key-value pairs to populate a ConfigMap. This approach simplifies environment variable management across pods. Mount a ConfigMap into a Pod as a volume to make configuration files directly accessible to your application. When you have multiple related configuration files, combine them into a single ConfigMap. Kubernetes will map each filename as a key in the ConfigMap. kubectl create configmap multi-config \ --from-file=db.conf \ --from-file=app.conf \ --from-file=cache.conf. Mounting ConfigMaps in Kubernetes allows you to **inject configuration data directly into Pods** as files or directories. Depending on your use case, you can mount ConfigMaps as **single files, directories, or subPaths**, customize **permissions**, and even **control ownership** or **read/write behavior**. * Mount ConfigMap as File or Directory. ### Mount ConfigMap as File or Directory. When you mount a ConfigMap, each **key becomes a file**. Instead of rebuilding the image, Kubernetes lets you mount this custom file from a ConfigMap using `subPath`, replacing the default config at runtime seamlessly. Use `subPath` to mount a ConfigMap file into a **specific path** inside a container rather than an entire directory. Instead of manually copying these files into every container image, Kubernetes lets you mount a single ConfigMap into all pods within a Deployment or Job. This ensures every instance runs with identical configuration while allowing DevOps teams to update settings centrally without rebuilding or redeploying images. By combining declarative YAML definitions with flexible mounting options, ConfigMaps give you full control over runtime configurations — helping you maintain consistency, reduce image rebuilds, and streamline multi-environment deployments in Kubernetes.
- [Kubernetes ConfigMaps Volume Mount issue | Codemia](https://codemia.io/knowledge-hub/path/kubernetes_configmaps_volume_mount_issue) — ## Basic ConfigMap Volume Mount

yaml

```
1 apiVersion:  v1 2 kind:  ConfigMap 3 metadata:  4  name:  app - config 5 data:  6  app.properties:  |  7 database.host=db.example.com 7 8 database.port=5432  9  logging.conf:  |  10 level=INFO 10 11 format=json  12 ---  13 apiVersion:  v1 14 kind:  Pod 15 metadata:  16  name:  myapp 17 spec:  18  containers:  19  -  name:  app 20  image:  myapp: latest 21  volumeMounts:  22  -  name:  config - volume 23  mountPath: /etc/config 24  volumes:  25  -  name:  config - volume 26  configMap:  27  name:  app - config
```

This creates files `/etc/config/app.properties` and `/etc/config/logging.conf` inside the container. Each key in the ConfigMap becomes a file name, and the value becomes the file content. [...] By default, ConfigMap files are mounted with mode `0644`. Use `defaultMode` to set permissions for all files or `mode` on individual items. The mode must be specified as an octal integer.

## Issue 4: Mounting Specific Keys Only

yaml

```
1 volumes:  2  -  name:  config - volume 3  configMap:  4  name:  app - config 5  items:  6  -  key: app.properties 7  path: application.properties # Rename the file
```

The `items` field selects specific keys from the ConfigMap and optionally renames them. Keys not listed are not mounted. This is useful when a ConfigMap contains multiple files but you only need one.

## Issue 5: ConfigMap Not Found

yaml [...] ## Issue 1: Volume Mount Overwrites Existing Directory

yaml

```
1# PROBLEM: mounting to /etc/config replaces everything in that directory  2 volumeMounts:  3  -  name:  config - volume 4  mountPath: /etc/config # All existing files in /etc/config are hidden  5 6 # FIX: Use subPath to mount individual files without overwriting  7 volumeMounts:  8  -  name:  config - volume 9  mountPath: /etc/config/app.properties 10  subPath: app.properties 11  -  name:  config - volume 12  mountPath: /etc/config/logging.conf 13  subPath: logging.conf
```
- [ConfigMaps | Kubernetes](https://kubernetes.io/docs/concepts/configuration/configmap) — name: game-demo  name: game-demo  name:  game-demo   key: ui_properties_file_name  key: ui_properties_file_name  key:  ui_properties_file_name   volumeMounts:  volumeMounts:  volumeMounts:   - name: config  - name: config  name:  config   mountPath: "/config"  mountPath: "/config"  mountPath:  "/config"   readOnly: true  readOnly: true  readOnly:  true   volumes:  volumes:  volumes:   # You set volumes at the Pod level, then mount them into containers inside that Pod  # You set volumes at the Pod level, then mount them into containers inside that Pod  # You set volumes at the Pod level, then mount them into containers inside that Pod   - name: config  - name: config  name:  config   configMap:  configMap:  configMap:   # Provide the name of the ConfigMap you want to mount.  # Provide [...] To consume a ConfigMap in a volume in a Pod:

1. Create a ConfigMap or use an existing one. Multiple Pods can reference the same ConfigMap.
2. Modify your Pod definition to add a volume under `.spec.volumes[]`. Name the volume anything, and have a `.spec.volumes[].configMap.name` field set to reference your ConfigMap object.
3. Add a `.spec.containers[].volumeMounts[]` to each container that needs the ConfigMap. Specify `.spec.containers[].volumeMounts[].readOnly = true` and `.spec.containers[].volumeMounts[].mountPath` to an unused directory name where you would like the ConfigMap to appear.
4. Modify your image or command line so that the program looks for files in that directory. Each key in the ConfigMap `data` map becomes the filename under `mountPath`. [...] This is an example of a Pod that mounts a ConfigMap in a volume:

```
apiVersion: v1 apiVersion: v1 apiVersion:  v1  kind: Pod kind: Pod  kind:  Pod  metadata: metadata:  metadata:   name: mypod  name: mypod  name:  mypod  spec: spec:  spec:   containers:  containers:  containers:   - name: mypod  - name: mypod  name:  mypod   image: redis  image: redis  image:  redis   volumeMounts:  volumeMounts:  volumeMounts:   - name: foo  - name: foo  name:  foo   mountPath: "/etc/foo"  mountPath: "/etc/foo"  mountPath:  "/etc/foo"   readOnly: true  readOnly: true  readOnly:  true   volumes:  volumes:  volumes:   - name: foo  - name: foo  name:  foo   configMap:  configMap:  configMap:   name: myconfigmap  name: myconfigmap  name:  myconfigmap  
```
- [Kubernetes - Using ConfigMap SubPaths to Mount Files - DEV Community](https://dev.to/joshduffney/kubernetes-using-configmap-subpaths-to-mount-files-3a1i) — `name: volume-rs  
 configMap:  
 name: rs-config  
 items:  
 key: ss.yml  
 path: remote/AppData/  
 containers:  
 name: remote  
 image: registry_name  
 volumeMounts:  
 name: volume-rs  
 mountPath: C:................\App_Data\ss.yml  
 subPath: remote/AppData/`

Can anyone suggest a workaround for this? Any help would be grateful. Thanks in advance.

     

nicksc423 profile image 

nicksc423 

   nicksc423

 Joined

• 

 Copy link

I think there's a typo, you config map is named: mysql-config but you always seem to reference: mysql-configmap in the deployment

    

joshduffney profile image 

Josh Duffney 

   Josh Duffney

advocate @microsoft #cloudnative

 Location

  Central US
 Work

  Microsoft
 Joined

• 

 Copy link [...] I have a kind: Deployment as below where I am mounting rs-config.yaml ConfigMap(which contains a ss.yml file) as volume. With the below configuration I am able to get the ss.yml file in the specified mountPath: C:................\App\_Data  
 Apart from ss.yml I need another directory named DATA in the same path(C:................\App\_Data) for which I used the subPath. With the below code I am able to get DATA directory but the contents in the DATA directory are not getting completely copied(subdirectories and some files are missing which are required for our application to be up). [...] and in the deployment config:

```
[...]  spec:  volumes:  -  name:  logback-configmap-volume  configMap:  name:  logback-configmap  items:  -  key:  logback  path:  logback.xml  defaultMode:  420  [..]  volumeMounts:  -  name:  logback-configmap-volume  mountPath:  /deployments/zfaRouter/WEB-INF/classes/logback.xml  subPath:  logback.xml  [..]  
```

```
$ ls -la. -rw-r--r--.
```

Do you have any idea why this is not working?

     

reshma profile image 

reshmagcp 

   reshmagcp

 Joined

•  • Edited on  • Edited 

 Copy link

I have followed the method mentioned in the blog and it is working. Thanks for this really useful content. But I am facing one issue now which is mentioned below.
- [CrashLoopBackOff on new deployment — ConfigMap created in wrong namespace | Today I Fixed | DevOpsBoys](https://devopsboys.com/today-i-fixed/kubernetes-crashloopbackoff-missing-configmap-fix) — 🎉 DevOps Interview Prep Bundle is live — 1000+ Q&A across 20 topicsGet it →

DevOpsBoys

Mock InterviewInterview

All Fixes

Today I Fixed

# CrashLoopBackOff on new deployment — ConfigMap created in wrong namespace

kubernetesJun 29, 202610 minutes to fixkubernetestroubleshooting

A new deployment went into `CrashLoopBackOff` immediately after `kubectl apply`. Running `kubectl logs` showed the app dying on startup with: `Error: config file not found at /etc/app/config.yaml`.

Root cause: The ConfigMap (`app-config`) had been created in the `default` namespace, but the deployment was running in the `production` namespace. Kubernetes ConfigMaps are namespace-scoped — the pod couldn't find the ConfigMap, so the mounted file simply didn't exist at startup.

Fix: [...] Fix:

First, find where the ConfigMap actually lives:

bash

```
kubectl get configmap -A | grep app-config kubectl  get  configmap -A  | grep app-config# Output: default app-config 1 5m# Output: default app-config 1 5m
```

Recreate it in the correct namespace:

bash

```
# Export from default namespace # Export from default namespacekubectl get configmap app-config -n default -o yaml \ kubectl  get  configmap app-config -n  default -o  yaml  \ | sed 's/namespace: default/namespace: production/' \  | sed 's/namespace: default/namespace: production/'  \ | kubectl apply -f -  | kubectl  apply -f -  # Verify it's in the right place # Verify it's in the right placekubectl get configmap app-config -n production kubectl  get  configmap app-config -n  production
``` [...] Then restart the deployment:

bash

```
kubectl rollout restart deployment my-app -n production kubectl  rollout  restart  deployment my-app -n  productionkubectl rollout status deployment my-app -n production kubectl  rollout  status  deployment my-app -n  production
```

Check that the pod starts cleanly:

bash

```
kubectl logs -n production -l app=my-app --tail=20 kubectl  logs -n  production -l app=my-app --tail=20
```

Lesson: When a pod can't find a mounted ConfigMap or Secret, always run `kubectl get configmap -A | grep`  first — it's almost always a namespace mismatch, not a missing resource.

## Did this fix work?

Tell us what needs improving. No account required.
- [Diagnose and Fix CrashLoopBackOff Caused by Missing Configuration Dependencies](https://oneuptime.com/blog/post/2026-02-09-crashloopbackoff-missing-config/view) — `# View current logs
kubectl logs myapp-6d5c4d8f9-x7k2p
# View logs from previous crash
kubectl logs myapp-6d5c4d8f9-x7k2p --previous
# Common error messages:
# Error: Environment variable DATABASE_URL not set
# Fatal: Cannot read configuration file /etc/app/config.yaml
# Error: Secret key 'api-token' not found`

## Diagnosing Missing ConfigMap Volumes

Required ConfigMaps mounted as volumes won't cause immediate container failure if missing. Instead, the pod stays in ContainerCreating status because Kubernetes cannot set up the volume. However, if the ConfigMap reference is optional, or if the ConfigMap exists but lacks a file the application expects, the container can start and then crash during application startup. [...] `apiVersion: apps/v1
kind: Deployment
metadata:
name: myapp
spec:
selector:
matchLabels:
app: myapp
template:
metadata:
labels:
app: myapp
spec:
initContainers:
- name: config-validator
image: busybox:latest
command:
- sh
- -c
- |
echo "Validating configuration..."
# Check required files exist
if [ ! -f /etc/config/config.yaml ]; then
echo "Error: config.yaml not found"
exit 1
fi
# Check required environment variables
if [ -z "$DATABASE_URL" ]; then
echo "Error: DATABASE_URL not set"
exit 1
fi
if [ -z "$API_TOKEN" ]; then
echo "Error: API_TOKEN not set"
exit 1
fi
# Validate file contents
if ! grep -q "database:" /etc/config/config.yaml; then
echo "Error: config.yaml missing database section"
exit 1
fi
echo "Configuration validation passed"
env:
- name: DATABASE_URL
valueFrom: [...] env:
- name: DATABASE_URL
valueFrom:
secretKeyRef:
name: app-secrets
key: database-url
optional: true
- name: API_TOKEN
valueFrom:
secretKeyRef:
name: app-secrets
key: api-token
optional: true
volumeMounts:
- name: config
mountPath: /etc/config
containers:
- name: app
image: myapp:v1.0
# Main container configuration
volumes:
- name: config
configMap:
name: app-config`
- [Kubernetes ConfigMap Not Found Error: Troubleshooting and Best Practices | Mustafa Shaik posted on the topic | LinkedIn](https://www.linkedin.com/posts/musta-shaik_kubernetes-devops-cloudnative-activity-7419296342113636352-3BaH) — No alternative text description for this image

To view or add a comment, sign in

View profile for Ravi Sharma

Kubernetes CrashLoopBackOff: Panic in Production 🔥🐳
Problem: A critical service kept entering CrashLoopBackOff, bringing down essential parts of the application. The clock was ticking as we faced downtime in production! 😱
Solution:
Logged into the cluster, checked the pod logs, and discovered a misconfigured environment variable. Fixed the config map, redeployed, and stability returned. 🛠️✨
Takeaway: Always double-check environment variables and configuration files before deploying. One small error can cause big issues! 🔍
hashtag
#Kubernetes hashtag
#CrashLoopBackOff hashtag
#ConfigManagement hashtag
#DevOps hashtag
#RealTimeFix

No alternative text description for this image
- [How Do I Fix CrashLoopBackOff in Kubernetes (Step‑by‑Step)?](https://www.fairwinds.com/blog/how-do-i-fix-crashloopbackoff-in-kubernetes-step-by-step) — ```
 kubectl logs -n fairwinds-demo demo-app-786d4c4f86-pwpk6 -c app ERROR: missing /app/config/app.yaml ERROR: missing /app/config/app.yaml ERROR: missing /app/config/app.yaml ERROR: missing /app/config/app.yaml ERROR: missing /app/config/app.yaml 
```

If the container restarts quickly, you often need the logs from the previous attempt:

```
 kubectl logs -n fairwinds-demo demo-app-654f54c559-czsdg -c app   
--previous 
```

You can filter logs by only showing error messages.

```
 kubectl logs -n fairwinds-demo demo-app-786d4c4f86-pwpk6 -c app |   
grep ERROR ERROR: missing /app/config/app.yaml ERROR: missing /app/config/app.yaml ERROR: missing /app/config/app.yaml ERROR: missing /app/config/app.yaml 
```

Look for:
- [Pod with configmap CrashLoopBackOff : r/kubernetes](https://www.reddit.com/r/kubernetes/comments/zvz0mi/pod_with_configmap_crashloopbackoff) — Check the logs with kubectl. It will most likely complain that it cannot find any other config like /etc/bind/named.conf. Make sure you only