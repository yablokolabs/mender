# Root cause: Checkout pod crashloop due to ConfigMap volume mount path mismatch (/etc/config vs /etc/app)

Service `checkout` in namespace `shop`.

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

## Tavily sources
Queries: Kubernetes ConfigMap volume mount path mismatch container expects config at different path; Kubernetes pod crash config file not found ConfigMap volume mount path; Kubernetes deployment volumeMount mountPath ConfigMap items key path mismatch
- [Kubernetes ConfigMaps Volume Mount issue | Codemia](https://codemia.io/knowledge-hub/path/kubernetes_configmaps_volume_mount_issue) — Practice Now

Volume Mount

### Kubernetes ConfigMaps Volume Mount issue

###### System Designpractice on Codemia

Work through 120+ system design problems with detailed solutions, from rate limiters to multi-region storage.

Practice system design

KubernetesDevOps & DeploymentDebugging & Errors

## Introduction

Mounting a ConfigMap as a volume in Kubernetes injects configuration data as files inside a container. Common issues include the ConfigMap overwriting the entire target directory, file permissions being incorrect, changes not propagating to running pods, and path mismatches. Understanding how Kubernetes mounts ConfigMap volumes — specifically that it replaces the mount directory contents — is key to avoiding most of these problems.

## Basic ConfigMap Volume Mount

yaml [...] Mounting overwrites the entire directory: A ConfigMap volume mount replaces all files at the mount path. If your container image has files at `/etc/config`, they become invisible. Use `subPath` to mount individual files without overwriting.
 subPath prevents automatic updates: Files mounted with `subPath` are static bind mounts. ConfigMap changes are not reflected until the pod is restarted. Use directory mounts (without `subPath`) if you need live updates.
 Binary data corruption: ConfigMap values are UTF-8 strings. Binary files (images, certificates) should use the `binaryData` field with base64 encoding, or use a Secret instead. Regular `data` fields may corrupt binary content. [...] ## Basic ConfigMap Volume Mount

yaml

```
1 apiVersion:  v1 2 kind:  ConfigMap 3 metadata:  4  name:  app - config 5 data:  6  app.properties:  |  7 database.host=db.example.com 7 8 database.port=5432  9  logging.conf:  |  10 level=INFO 10 11 format=json  12 ---  13 apiVersion:  v1 14 kind:  Pod 15 metadata:  16  name:  myapp 17 spec:  18  containers:  19  -  name:  app 20  image:  myapp: latest 21  volumeMounts:  22  -  name:  config - volume 23  mountPath: /etc/config 24  volumes:  25  -  name:  config - volume 26  configMap:  27  name:  app - config
```

This creates files `/etc/config/app.properties` and `/etc/config/logging.conf` inside the container. Each key in the ConfigMap becomes a file name, and the value becomes the file content.
- [Working with kubernetes configmaps, part 1: volume mounts](https://itnext.io/working-with-kubernetes-configmaps-part-1-volume-mounts-f0ace283f5aa) — spec:  
 [snip]  
 volumes:  
 - configMap:  
 name: clusters-config-env  
 name: clusters-config-volume
We do not need to change the `volumeMounts` section, because we are mounting a different map, but _at the same mount point_. When we issue a GET call to the `/config` endpoint now, we get:

{  
 "cluster1.endpoint": "  
 "cluster1.name": "mycluster",  
 "cluster2.endpoint": "  
 "cluster3.endpoint": "  
 "cluster4.endpoint": "  
 "cluster5.endpoint": "  
 "current.target": "cluster1.endpoint"  
}
Just like in the original `clusters-config-env` configmap’s `data` section, we have one key/value pair for each of the pairs in the original file.

_Okay, I get that, but why do I need to care?_ [...] spec:  
 containers:  
 image: index.docker.io/sandycash/cm-loader  
 volumeMounts:  
 - mountPath: /clusters-config  
 name: clusters-config-volume  
 volumes:  
 - configMap:  
 name: clusters-config-file  
 name: clusters-config-volume
This snippet specifies doing the following things:

1.   Create a container using the specified image from DockerHub;
2.   Make the configmap `clusters-config-file` available as a mountable volume called `clusters-config-volume`; and
3.   Mount that volume into the container at the path `/clusters-config`

The application we will use for this first example is built from the `load/load.go` source file in my repository — here’s the source: [...] ## How configmap volume mounts work

To answer the previous question, we need to consider what it means to “mount a configmap as a volume.” If you recall, we specified our mount point as `/clusters-config` — this is the name by which your application will refer to this configmap when accessing it via the filesystem. One critical aspect is that _mount points are always directories_. So the application will actually see the configmap as a directory containing one or more files (assuming your configmap’s `data` section is not empty). Where do these files come from? We never created any “files,” did we?
- [Kubernetes - Using ConfigMap SubPaths to Mount Files - DEV Community](https://dev.to/joshduffney/kubernetes-using-configmap-subpaths-to-mount-files-3a1i) — ### Apply the Manifests

```
 #save the above manifests (mysql-configmap.yaml & mysql-deployment.yaml) kubectl apply -f . # Use kubctl exec to list /etc/mysql/conf.d contents kubectl exec -it mysql-59fcc88776-g768b ls /etc/mysql/conf.d 
```

### The problem

The screen shot above tells us the volume mount worked. Kubernetes took the map name of `mysql_binlog_format.cnf` present it as a file with the contents that were stored in the data source of the configMap. The problem however is it laid that volume on top of the existing directory. The default configuration files for mysql are no longer present. I'd have to create all the mysql configuration files and store them into the configMap. Or, I can use a subPath.

## Using a configMap subPath [...] `name: volume-rs  
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

 Copy link [...] ### Deployment Using a configMap Volume

As I mentioned configMaps can be used as volumes. The volumeMounts inside the template.spec are the same as any other volume. However, the volumes section is different. Instead of specifying a persistentVolumeClaim or other volume type you reference the configMap by name. This takes all the map names and data sources of the configMap named mysql-configmap and mounts it as a volume at `/etc/mysql/conf.d`
- [How to Fix 'Configuration Management' Issues](https://oneuptime.com/blog/post/2026-01-24-configuration-management-issues/view) — ```
# Problem: Config file not found at expected path apiVersion: apps/v1 kind: Deployment spec: template: spec: containers: - name: myapp volumeMounts: - name: config mountPath: /etc/myapp/config.yaml # Mounts directory, not file volumes: - name: config configMap: name: myapp-config # Fix: Mount as subPath for single file apiVersion: apps/v1 kind: Deployment spec: template: spec: containers: - name: myapp volumeMounts: - name: config mountPath: /etc/myapp/config.yaml subPath: config.yaml # Now mounts just the file volumes: - name: config configMap: name: myapp-config items: - key: config.yaml path: config.yaml
```

### Debugging File Mount Issues
- [Kubernetes Volume Mount ConfigMap to File within the ...](https://stackoverflow.com/questions/67532600/kubernetes-volume-mount-configmap-to-file-within-the-pod-without-overwriting-all) — When configMap is mounted as volume then it will delete all the files which were previously present in the mount path, this is expected
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

## Fixing Missing Secret References
- [ConfigMap Not Mounting as Volume in Kubernetes | Buglyst](https://buglyst.com/learn/guides/kubernetes-configmap-not-mounting-debug) — A ConfigMap volume that fails to mount typically points to one of several root causes: the ConfigMap doesn't exist in the same namespace, the volume definition in the pod spec references a key that doesn't exist in the ConfigMap, the mount path is a subdirectory of an existing mount (overlap), or there's a silent failure in the kubelet (e.g., network issue reaching the API server, or the ConfigMap is too large). Because Kubernetes doesn't always surface a clear error for a missing key — it just skips it — you can end up with a pod that looks healthy but is missing critical configuration. Another common cause is a mismatch between the ConfigMap's data keys and the items field in the volume definition; if you specify items but misspell a key, the entire mount may silently drop to an empty [...] ( 01 )Fast diagnosis

The first ten minutes — establish facts before touching code.

 1Run `kubectl get configmap  -n  -o yaml` to verify the ConfigMap exists and contains the expected keys and data.
 2Run `kubectl describe pod  -n ` and check the 'Volumes' section for the ConfigMap volume status. Look for 'Mountable' or error messages.
 3Exec into the container: `kubectl exec -it  -n  -- ls -la ` to see what's actually there.
 4Check kubelet logs on the node: `journalctl -u kubelet -n 100 | grep -i configmap` or look at /var/log/pods// for volume plugin logs.
 5Use `kubectl logs  -c  --previous` if the pod restarted to catch mount errors from the kubelet.

( 02 )Where to look

The specific files, logs, configs, and dashboards that usually own this bug. [...] The 500s started after a routine Helm upgrade that added a new feature flag to the nginx configuration. The deployment rolled out without errors—no crash loops, no obvious failures. But when I exec'd into a pod, the /etc/nginx/conf.d directory was completely empty. The pod was running, but nginx couldn't find any server blocks.

I immediately checked the ConfigMap: it existed, had the right key 'default.conf'. Then I looked at the pod spec. The volumeMounts section referenced a volume named 'nginx-config' which pointed to the ConfigMap, but the 'items' field listed a key 'nginx-default.conf'—a typo from a developer's copy-paste. Kubernetes didn't throw an error; it just mounted an empty directory because none of the specified items matched actual keys.
- [Pod with configmap CrashLoopBackOff : r/kubernetes](https://www.reddit.com/r/kubernetes/comments/zvz0mi/pod_with_configmap_crashloopbackoff) — Make sure you only mount the single named.conf.options file with volumeMounts: your configmap is mounted on /etc/bind, effectively replacing
- [Troubleshooting Kubernetes ConfigMap and Secret Issues](https://www.managekubernetes.com/blog/troubleshooting-kubernetes-configmap-and-secret-issues) — Troubleshooting Common Issues Issue 1: ConfigMap Not Found Symptoms: Pod fails to start; logs show "ConfigMap not found". Cause: ConfigMap not created or misnamed. Solution: Verify ConfigMap existence and name. ... Issue 2: Secret Volume Mount Fails Symptoms: Pod unable to mount Secret as volume. Cause: Incorrect Secret name or access permissions.
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
# WITHOUT subPath — replaces /etc/nginx/ entirely# WITHOUT subPath — replaces /etc/nginx/ entirelyvolumeMounts: volumeMounts: - name: nginx-config - name: nginx-config mountPath: /etc/nginx/  mountPath: /etc/nginx/  # WITH subPath — only mounts nginx.conf, leaves rest of /etc/nginx/ intact# WITH subPath — only mounts nginx.conf, leaves rest of /etc/nginx/ intactvolumeMounts: volumeMounts: - name: nginx-config - name: nginx-config mountPath: /etc/nginx/nginx.conf  mountPath: /etc/nginx/nginx.conf subPath: nginx.conf  subPath: nginx.conf
```

Important `subPath` limitation: When using `subPath`, the file is not automatically updated when the ConfigMap changes, even for volume mounts. You must restart the pod.

## Error 7: ConfigMap Too Large (1MB Limit)

Symptom: [...] For volume-mounted ConfigMaps: Kubernetes syncs volume-mounted files automatically within 1–2 minutes (controlled by `kubelet` sync period). You don't need to restart for volume mounts — but in-process cache in your app may still hold stale values.

## Error 4: Volume-Mounted ConfigMap Shows Wrong Files

Symptom: You mount a ConfigMap as a volume but only some files appear, or the wrong content is there.

yaml

```
volumes: volumes: - name: config-volume - name: config-volume configMap:  configMap: name: app-config  name: app-config items: # ← Only specified items are mounted  items: # ← Only specified items are mounted - key: nginx.conf - key: nginx.conf path: nginx.conf  path: nginx.conf
```
- [Discussion of Kubernetes - Using ConfigMap SubPaths to Mount Files - DEV Community](https://dev.to/joshduffney/kubernetes-using-configmap-subpaths-to-mount-files-3a1i/comments) — `name: volume-rs  
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

 Copy link [...] ```
kind:  ConfigMap  apiVersion:  v 1  metadata:  name:  logback-configmap  data:  logback:  |   version="1.0" encoding="UTF-8"?>  scan="true" scanPeriod="60 seconds"> [...]  version="1.0"  encoding="UTF-8"?>   scan="true" scanPeriod="60 seconds"> [...]  scan= "true"  scanPeriod= "60 seconds">  [...]  
```

and in the deployment config:

```
[...]  spec:  volumes:  -  name:  logback-configmap-volume  configMap:  name:  logback-configmap  items:  -  key:  logback  path:  logback.xml  defaultMode:  420  [..]  volumeMounts:  -  name:  logback-configmap-volume  mountPath:  /deployments/zfaRouter/WEB-INF/classes/logback.xml  subPath:  logback.xml  [..]  
```

```
$ ls -la. -rw-r--r--.
```

Do you have any idea why this is not working?

     

reshma profile image 

reshmagcp 

   reshmagcp [...] I have a kind: Deployment as below where I am mounting rs-config.yaml ConfigMap(which contains a ss.yml file) as volume. With the below configuration I am able to get the ss.yml file in the specified mountPath: C:................\App\_Data  
 Apart from ss.yml I need another directory named DATA in the same path(C:................\App\_Data) for which I used the subPath. With the below code I am able to get DATA directory but the contents in the DATA directory are not getting completely copied(subdirectories and some files are missing which are required for our application to be up).
- [Kubernetes ConfigMaps Volume Mount issue | Codemia](https://codemia.io/knowledge-hub/path/kubernetes_configmaps_volume_mount_issue) — Practice Now

Volume Mount

### Kubernetes ConfigMaps Volume Mount issue

###### System Designpractice on Codemia

Work through 120+ system design problems with detailed solutions, from rate limiters to multi-region storage.

Practice system design

KubernetesDevOps & DeploymentDebugging & Errors

## Introduction

Mounting a ConfigMap as a volume in Kubernetes injects configuration data as files inside a container. Common issues include the ConfigMap overwriting the entire target directory, file permissions being incorrect, changes not propagating to running pods, and path mismatches. Understanding how Kubernetes mounts ConfigMap volumes — specifically that it replaces the mount directory contents — is key to avoiding most of these problems.

## Basic ConfigMap Volume Mount

yaml [...] ## Basic ConfigMap Volume Mount

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

yaml
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

 Copy link [...] and in the deployment config:

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

I have followed the method mentioned in the blog and it is working. Thanks for this really useful content. But I am facing one issue now which is mentioned below. [...] I also need to update the templates.volumes section. Instead of simply providing the configMap name I now also need to provide and items list of the entries I want to include from the configMap. Under items I've specified the key, which is the map name and the path. The path value must match the subPath value define din template.spec.volumeMounts.
- [subPath is the most confusing thing in Kubernetes - HackMD](https://hackmd.io/@maelvls/kubernetes-subpath) — I've turned this into a table: | Host volume | Pod mount point |  -------- | | /lib/kubelet/pods/bc2bf/volumes/kubernetes.io~configmap/conf/..2024\_07\_01\_14\_15\_02.3624755718/conf.yaml | /etc/conf.yaml | Now, let's make the distinction between `mountPath` and `subPath`: - `mountPath` is about the pod mount point. - `subPath` is about the host volume path. Without `subPath`, the outcome would have been very different. Let's remove the `subPath` from the manifest: ```yaml apiVersion: v1 kind: Pod metadata: name: example spec: containers: - name: example image: busybox:1.28 command: ['sh', '-c', 'echo "Running!" && tail -f /dev/null'] volumeMounts: - name: conf mountPath: /etc/conf.yaml volumes: - name: conf configMap: name: conf ``` The host "volume" (a directory, really) looks like [...] needs to be mounted. \\Important learnings:\\ - If the path given in `subPath` isn't found, what's mounted at `mountPath` is a host-mounted volume that is made of an empty directory. The `subPath` name doesn't matter in this case. - If the path given in `subPath` corresponds to a file in the host volume (e.g., it matches a configmap key), that file alone is mounted to `mountPath`. - If the path given in `subPath` corresponds to a directory in the host-mounted volume (only happens when mounting a PV volume), then `mountPath` is a directory that corresponds to the sub- directory `subPath` in the host-mounted volume. If your concern is that you want to mount multiple configmap keys to a directory with existing files (such as `/etc`), the following will cause `/etc` to be replaced by the [...] the following will cause `/etc` to be replaced by the host-mounted volume: ```yaml volumeMounts: - name: conf mountPath: /etc ``` The `subPath` is exactly what you want in this case. You will have to have one volume mount per file, though: ```yaml volumeMounts: - name: conf mountPath: /etc/conf.yaml subPath: conf.yaml - name: conf mountPath: /etc/other.yaml subPath: other.yaml ``` ## What about mistakenly using a `subPath` that doesn't exist in the host's volume? On the host, since `baz` doesn't exist in the configmap `myconf`, the host volume is an empty directory: ```console $ sudo ls -al /lib/kubelet/pods/bc2bf/volumes/kubernetes.io~configmap/myconf/foo drwxrwxrwx 2 root root 4096 Jul 1 15:56 . ``` On the host, when `foo` exists in the configmap `myconf`, it appears as a file in the
- [14. Resolve VolumeMounts Issue in Kubernetes](https://medium.com/@ayeshalakshan00/14-resolve-volumemounts-issue-in-kubernetes-6251266465c8) — 🔹 4. emptyDir is Temporary

   Data is lost when the pod restarts
   Files must be copied again

> 🎯 Conclusion

This task demonstrates a real-world DevOps scenario where:

A simple path mismatch between containers and configuration caused the application to fail.

By systematically:

   Inspecting the pod
   Verifying volume mounts
   Fixing ConfigMap configuration

the issue was successfully resolved.

Kubernetes

DevOps

Kodekloud

Cloud Computing

Cloud

[](

--

[](

--

1

[](

--

[](

Image 7: Ayeshalakshan

Image 8: Ayeshalakshan

## Written by Ayeshalakshan

8 followers

·46 following

Help

Status

About

Careers

Press

Blog

Store

Privacy

Rules

Terms

Text to speech [...] Sitemap

Open in app

Sign up

Sign in



root /var/www/html; ❌

👉 This path did not match the actual shared volume location.

💥 Root Cause

The failure happened because:

Nginx, PHP-FPM, and the ConfigMap were not aligned on the same directory path.

In Kubernetes:

   emptyDir provides shared storage
   But each container defines its own mount path

If these paths differ → the application breaks.

> 🛠️ Step-by-Step Solution

1️⃣ Inspect the Pod

kubectl describe pod nginx-phpfpm
Key findings:

   Two containers in one pod
   Shared emptyDir volume
   ConfigMap mounted into Nginx

2️⃣ Identify the Correct Path

👉 Default Nginx web root:

/usr/share/nginx/html
3️⃣ Fix the ConfigMap

kubectl edit configmap nginx-config
Update:

## Get Ayeshalakshan’s stories in your inbox