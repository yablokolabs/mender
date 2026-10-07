# Root cause: Checkout pods stuck in Terminating during rolling deployment update due to missing SIGTERM handling

Service `checkout` in namespace `shop`.

## Root cause
The checkout application does not handle SIGTERM signals (likely because the container's CMD uses shell form, making the shell PID 1 which does not forward signals to the Python process), preventing graceful shutdown within the 30s terminationGracePeriodSeconds during a rolling deployment update.

## Mechanism
1) A rolling Deployment update creates a new ReplicaSet (5cf6bd4cc7) and immediately terminates the old ReplicaSet (67bcb9c7f7) pods [1][3]. 2) The old pods enter Terminating state; Kubernetes sends SIGTERM to PID 1 [6]. 3) Because the application is launched via shell-form CMD (e.g., `CMD python service.py`), the shell becomes PID 1 and does not forward SIGTERM to the Python HTTP server [8]. 4) The application continues running and serving healthz (logs show 200 responses up to 19:40:56), so the container stays in Running state. 5) The 30s terminationGracePeriodSeconds elapses while the container ignores SIGTERM [6][10]. 6) Kubernetes should then send SIGKILL, but the pods are observed stuck in Terminating with containers still Running, indicating the grace period has just expired or forceful termination is delayed. 7) Meanwhile, new pods start and pass readiness, causing temporary over-capacity (4 pods vs 2 desired) as described in [1][2].

Confidence: 0.80 · Labels: migration_failure, probe_config, image_tag

## Evidence relied on
- State: Running for containers in terminating pods (checkout-67bcb9c7f7-6tg4g, checkout-67bcb9c7f7-m2lc6)
- Termination Grace Period: 30s
- starting checkout service (log_level=info, db=orders-db.shop.svc.cluster.local, cache=96Mi)
- Healthz 200 responses continuing until 06/Oct/2026 19:40:56
- [8] SIGTERM and PID1: shell-form CMD makes shell PID 1, Python becomes child, SIGTERM not forwarded
- [6] Pod termination sequence: SIGTERM sent, wait grace period, then SIGKILL
- [1] Rolling updates cause old pods stuck in Terminating while new pods created
- [3] Deployment rolling update: old pods terminated immediately, new pods created before old fully removed

## Tavily sources
Queries: Kubernetes pods stuck in Terminating state during Deployment rolling update old ReplicaSet; pod termination grace period exceeded container still running no events SIGTERM handling; Kubernetes finalizer blocking pod deletion Terminating state stuck containerd
- [Kubernetes Deployment Rolling Updates - Stack Overflow](https://stackoverflow.com/questions/61737471/kubernetes-deployment-rolling-updates) — Title: Kubernetes Deployment Rolling Updates - Stack Overflow
### your communities. ### more stack exchange communities. ##### Collectives™ on Stack Overflow. # Kubernetes Deployment Rolling Updates. This application has 4 replicas and I'm doing a rolling update on each deployment. My problem is that during updates, I have over-capacity since all the older version pods are stuck at "Terminating" status while all the new pods are created. I tried to set `maxSurge` to 0, but this setting doesn't take into consideration the "Terminating" pods, so the load on my servers during the deployment is too high. The behaviour I'm trying to get is that new pods will only get created after the old version pods finished successfully, so at all times I'm not exceeding the number of replicas I set. ## 2 Answers 2. I also set `terminationGracePeriodSeconds` to the maximum time it takes for a pod to terminate. As a part of my deployment process, I apply the new `StatefulSet` with the new image and then delete all the running pods. This way all the pods are entering `Terminating` state and whenever a pod finished its task and terminated a new pod with the new image will replace it. Deployments implement the concept of ready pods to aide rolling updates. **Readiness probes** allow the deployment to gradually update pods while giving you the control to determine when the rolling update can proceed. A Ready pod is one that is considered successfully updated by the Deployment and will no longer count towards the surge count for deployment. A pod will be considered ready **if its readiness probe is successful and `spec.minReadySeconds` have passed since the pod was created**. So, what you can do, is implement (if you haven't done so yet) a readiness probe for your pods **in addition** to setting the `spec.minReadySeconds` to a value that will make sense (worst case) to the time that it takes for your pods to terminate. ## Your Answer. Thanks for contributing an answer to Stack Overflow! Find the answer to your question by asking. # Subscribe to RSS. To subscribe to this RSS feed, copy and paste this URL into your RSS reader. ##### Stack Overflow. ##### Stack Exchange Network.
- [Kubernetes Deployment Rolling Update - Stack Overflow](https://stackoverflow.com/questions/70321665/kubernetes-deployment-rolling-update) — # Kubernetes Deployment Rolling Update. This question shows research effort; it is useful and clear. I have an application that I deploy on Kubernetes. This application has 5 replicas and I'm doing a rolling update on each deployment. My problem is that during updates,all the older version pods are stuck at "Terminating" status while all the new pods are created. During the updates, I end up running with 8 containers and it is something I'm trying to avoid. The behaviour I'm trying to get is that new pods will only get created after the old version pods terminated successfully, so at all times I'm not exceeding the number of replicas I set. Follow this question to receive notifications. asked Dec 12, 2021 at 7:13. * If the application is going to keep processing for half an hour when Kubernetes requests it to stop, when should it decide the application has just ignored the shutdown signal and forcibly terminate it? Dec 12, 2021 at 12:34. ## 2 Answers 2. set maxSurge to 5, so the number of all pods (both terminating and creating) will not exceed 5. Follow this answer to receive notifications. answered Dec 12, 2021 at 12:55. Nope it's not working.kubernetes rolling update is not waiting for pod's terminating state to complete before launching new pod. I think the best way to achieve this goal is to use Statefulsets, some of the key features of Statefulsets are:. Follow this answer to receive notifications. answered Dec 12, 2021 at 12:13. Start asking to get answers. Find the answer to your question by asking. * How everyone and anyone can use AI for good. * Results of the January 2026 Community Asks Sprint: Community Badges. How to update a set of pods running in kubernetes? Kubernetes deployment not doing rolling update. How to Update Kubernetes Deployments + Services. kubernetes deployment wait between pods on rolling update. Right way to update deployments on Kubernetes. How to rolling update deployment in kubernetes? Kubernetes Rolling Updates: Respect pod readiness before updating. Updating kubernetes deployment will create new pod. * Asking for help regarding how to think when solving this elementary geometry problem (likely spiral similarity/angle chasing).
- [Deployments | Kubernetes](https://kubernetes.io/docs/concepts/workloads/controllers/deployment) — #### Note:

This will only guarantee Pod termination previous to creation for upgrades. If you upgrade a Deployment, all Pods of the old revision will be terminated immediately. Successful removal is awaited before any Pod of the new revision is created. If you manually delete a Pod, the lifecycle is controlled by the ReplicaSet and the replacement will be created immediately (even if the old Pod is still in a Terminating state). If you need an "at most" guarantee for your Pods, you should consider using a StatefulSet.

#### Rolling Update Deployment [...] #### Rolling Update Deployment

The Deployment updates Pods in a rolling update fashion (gradually scale down the old ReplicaSets and scale up the new one) when `.spec.strategy.type==RollingUpdate`. You can specify `maxUnavailable` and `maxSurge` to control the rolling update process.

##### Max Unavailable

`.spec.strategy.rollingUpdate.maxUnavailable` is an optional field that specifies the maximum number of Pods that can be unavailable during the update process. The value can be an absolute number (for example, 5) or a percentage of desired Pods (for example, 10%). The absolute number is calculated from percentage by rounding down. The value cannot be 0 if `.spec.strategy.rollingUpdate.maxSurge` is 0. The default value is 25%. [...] The output is similar to this:

  ```
  Waiting for rollout to finish: 1 out of 3 new replicas have been updated... 
  ```
 Press Ctrl-C to stop the above rollout status watch. For more information on stuck rollouts, read more here.
 You see that the number of old replicas (adding the replica count from `nginx-deployment-1564180365` and `nginx-deployment-2035384211`) is 3, and the number of new replicas (from `nginx-deployment-3066724191`) is 1.

  ```
  kubectl get rs kubectl get rs 
  ```

  The output is similar to this:

  ```
  NAME DESIRED CURRENT READY AGE nginx-deployment-1564180365 3 3 3 25s nginx-deployment-2035384211 0 0 0 36s nginx-deployment-3066724191 1 1 0 6s 
  ```
 Looking at the Pods created, you see that 1 Pod created by new ReplicaSet is stuck in an image pull loop.
- [Kubernetes Deployment Not Updating: Causes, Fixes & Insights](https://www.groundcover.com/learn/kubernetes/deployment-not-updating) — Conversely, a much more insidious scenario occurs when the rollout starts but hangs: a new ReplicaSet is created and begins scaling up. Still, it gets stuck because the newly created Pods fail their Readiness Probes or crash loop, preventing the Deployment from safely terminating the older Pods due to availability constraints.

## Common Reasons a Kubernetes Deployment Is Not Updating

Deployment failures generally fall into two categories: the update never starts, or it starts but hangs indefinitely. The following table breaks down the most frequent causes, categorized by the failure mode, and provides immediate diagnostic steps: [...] ### RollingUpdate (The Default)

The RollingUpdate strategy is the default and preferred method, designed for zero-downtime deployments. When a new Pod template is detected:

 The Deployment Controller creates a new ReplicaSet reflecting the updated configuration.
 The Deployment scales up the new ReplicaSet (creating new Pods) while simultaneously scaling down the old ReplicaSet (terminating old Pods).

This gradual, synchronized exchange continues until the new ReplicaSet reaches the desired replica count and the old one is scaled down to zero. Two parameters control the pacing:

 maxSurge: The maximum number of Pods allowed above the desired replica count during the update.
 maxUnavailable: The maximum number of Pods that can be unavailable during the update.

### Recreate [...] | Rollout Never Starts | Imperative Change Conflict | A previous imperative command (e.g., kubectl edit) might have left a field that is preventing a new kubectl apply from taking effect. | Run kubectl describe deployment  and look for unexpected inline field overrides. |
| Rollout Hangs Mid-Update | Failing Readiness/Liveness Probes | The new Pods are unhealthy, causing them to fail their Readiness Probes. The maxUnavailable setting prevents the Deployment from terminating old, healthy Pods. | Check Pod events: kubectl describe pod . Check container logs: kubectl logs . |
- [ReplicaSet | Kubernetes](https://kubernetes.io/docs/concepts/workloads/controllers/replicaset) — Once the original is deleted, you can create a new ReplicaSet to replace it. As long as the old and new `.spec.selector` are the same, then the new one will adopt the old Pods. However, it will not make any effort to make existing Pods match a new, different pod template. To update Pods to a new spec in a controlled way, use a Deployment, as ReplicaSets do not support a rolling update directly.

### Terminating Pods

Feature state: Beta since Kubernetes v1.35; enabled by default

You can enable this feature by setting the `DeploymentReplicaSetTerminatingReplicas` feature gate on the API server and on the kube-controller-manager [...] ```
NAME READY STATUS RESTARTS AGE frontend-b2zdv 1/1 Running 0 10m frontend-vcmts 1/1 Running 0 10m frontend-wtsmm 1/1 Running 0 10m pod1 0/1 Terminating 0 1s pod2 0/1 Terminating 0 1s 
```

If you create the Pods first:

```
kubectl apply -f  kubectl apply -f  
```

And then create the ReplicaSet however:

```
kubectl apply -f  kubectl apply -f  
```

You shall see that the ReplicaSet has acquired the Pods and has only created new ones according to its spec until the number of its new Pods and the original matches its desired count. As fetching the Pods:

```
kubectl get pods kubectl get pods 
```

Will reveal in its output:

```
NAME READY STATUS RESTARTS AGE frontend-hmmj2 1/1 Running 0 9s pod1 1/1 Running 0 36s pod2 1/1 Running 0 36s 
```
- [K8s Pod Lifecycle and Graceful Shutdown | K8s Recipes](https://kubernetes.recipes/recipes/deployments/kubernetes-pod-lifecycle-termination) — Title: K8s Pod Lifecycle and Graceful Shutdown | K8s Recipes
# K8s Pod Lifecycle and Graceful Shutdown. Understand Kubernetes pod lifecycle phases, termination sequence, preStop hooks, SIGTERM handling, and terminationGracePeriodSeconds for graceful shutdown. > 💡 **Quick Answer:** Pod termination: 1) Pod set to Terminating, 2) preStop hook runs, 3) SIGTERM sent to PID 1, 4) `terminationGracePeriodSeconds` countdown (default 30s), 5) SIGKILL if still running. For graceful shutdown: handle SIGTERM in your app, use preStop hooks for cleanup, set `terminationGracePeriodSeconds` high enough for drain. SIGTERM sent to PID 1 in each container - After preStop completes (or immediately if no preStop) - After preStop completes (or immediately if no preStop) - App should start graceful shutdown - App should start graceful shutdown 4. SIGKILL sent if containers still running after grace period - Forceful kill, no cleanup possible - Forceful kill, no cleanup possible Timeline:Timeline:├─ t=0: Pod marked Terminating, endpoints removal starts├─ t=0: Pod marked Terminating, endpoints removal starts├─ t=0: preStop hook starts├─ t=0: preStop hook starts├─ t=X: preStop completes, SIGTERM sent├─ t=X: preStop completes, SIGTERM sent├─ t=30: Grace period expires → SIGKILL├─ t=30: Grace period expires → SIGKILL └─ Pod removed from API └─ Pod removed from API. Problem:Problem:  DELETE pod → endpoints removal AND SIGTERM happen in PARALLEL  DELETE pod → endpoints removal AND SIGTERM happen in PARALLEL Some kube-proxy/ingress controllers still route to the pod Some kube-proxy/ingress controllers still route to the pod after it starts shutting down → connection errors! Solution: preStop sleepSolution: preStop sleep lifecycle:lifecycle: preStop: preStop: exec: exec: command: ["sleep", "5"] # Wait for endpoints to propagate command: ["sleep", "5"] # Wait for endpoints to propagate # Timeline with fix:# Timeline with fix:# t=0: Pod Terminating, endpoints removal starts# t=0: Pod Terminating, endpoints removal starts# t=0: preStop: sleep 5 (pod still accepting traffic)# t=0: preStop: sleep 5 (pod still accepting traffic)# t=5: Endpoints fully removed from all proxies# t=5: Endpoints fully removed from all proxies# t=5: SIGTERM sent, app starts graceful shutdown# t=5: SIGTERM sent, app starts graceful shutdown# t=5+: No new traffic arrives, existing requests drain# t=5+: No new traffic arrives, existing requests drain.
- [Kubernetes pod stuck Terminating: finalizers, grace periods, and force delete](https://www.netdata.cloud/guides/kubernetes/kubernetes-pod-stuck-terminating) — 3. Check if containers are still running. If `crictl ps -a` on the node shows the container as Running, the kubelet has not yet sent SIGKILL. The grace period has not expired, or a `preStop` hook is still executing. If the grace period has expired and the container is still running, the application is likely ignoring SIGTERM.
4. Look for volume attachment hangs. If the pod used a CSI PersistentVolume, check `kubectl get volumeattachment`. A stuck VolumeAttachment on a NotReady node often means the CSI driver or attach-detach controller has not completed cleanup. The controller-manager may wait roughly six minutes before force-detaching. If the node is shut down, the CSI driver on the node may have been terminated before unmount completed. [...] | Cause | What it looks like | First thing to check |
 --- 
| Finalizer not removed by controller | `deletionTimestamp` is set, phase is Terminating, `finalizers` is non-empty | `kubectl get pod  -o jsonpath='{.metadata.finalizers}'` |
| CSI volume detach hang | Pod on a NotReady node, VolumeAttachment still present, container stopped | `kubectl get volumeattachment` |
| Application ignores SIGTERM | Container stays Running with `deletionTimestamp` set, no `preStop` hook active | `crictl ps -a` on the node |
| `preStop` hook hang | Events show hook execution, grace period appears to expire twice | `kubectl get event --field-selector involvedObject.name=` | [...] ```
flowchart TD A[Pod stuck Terminating] --> B{Finalizers present?} B -->|Yes| C[Check owning controller] B -->|No| D{Containers still running?} C --> E[Patch finalizers null or fix controller] D -->|Yes| F{preStop hook running?} D -->|No| G{VolumeAttachment exists?} F -->|Yes| H[Wait or reduce grace period] F -->|No| I[Check SIGTERM handler in app] G -->|Yes| J[Verify CSI driver and node status] G -->|No| K[Force delete as last resort] J --> L[Detach stuck volume or remove finalizer] I --> M[Fix app signal handling]
```

## Metrics & Signals To Monitor
- [SIGTERM and PID1 | semi/signal](https://semisignal.com/sigterm-and-pid1) — #### Responding to SIGTERM

So, for processes without an explicit signal handler, when Kubernetes issues `SIGTERM`, nothing will happen. The process will simply keep running. Only after the termination grace period, when Kubernetes forcible deletes the container, will the process be killed. In some cases, this is not a problem (the termination grace period is doesn’t matter and graceful termination isn’t a concern) but for programs that handle long-running tasks, it can certainly be an issue.

If the process running is an application or script where the source code is available, the solution is obvious, write a handler for `SIGTERM`. [...] When a pod is set to the `Terminating` state, all containers are sent SIGTERM
 Kubernetes waits a grace period (default is 30s) for containers to handle `SIGTERM`
  + If a container process has no handler for `SIGTERM`, the Linux kernel will kill the process immediately
  + If a container process does have a handler for `SIGTERM`, the handler can do whatever is needed to wrap up, then exit
 At the end of the grace period, any container still alive is sent `SIGKILL` and deleted

This is all very reasonable but it does depends on container processes handling `SIGTERM` or not handling `SIGTERM` and letting the kernel kill the process.

#### Not having a handler for SIGTERM
- [Graceful pod termination by fixing SIGTERM handling and using PreStop hook – Minh’s sharing](https://minhpn.com/graceful-pod-termination-by-fixing-sigterm-handling-and-using-prestop-hook) — The root cause lay in how the application was launched inside the container. Many Dockerfiles, including the client’s original one, use the shell form of the CMD instruction—something like:

```
CMD uvicorn app:app --host 0.0.0.0--port 80 --workers 4 CMD uvicorn app:app --host 0.0.0.0--port 80 --workers 4
```

In this form, the command runs inside a shell, dash in this case, which becomes PID 1—the init process, and the python processes become the child processes.

SigCgt (signals caught) refers to the signals that a process has registered a custom handler for. Here we can translate  
SigCgt: 0000000000010002 to SIGHUP (1) and SIGCHLD (17).There is no SIGTERM (15) here so the shell isn’t catching it. [...] Digging into the logs and metrics, we pinpointed the issue: pods were being terminated abruptly while still processing requests.   
  
In Kubernetes, when a pod is slated for termination:  
– The kubelet sends a SIGTERM signal to the main process (PID 1) inside the container. This signal is designed for the application to shut down gracefully—finish ongoing tasks, close connections, then exit nicely.  
– If the application doesn’t handle SIGTERM properly, Kubernetes waits for a grace period (defaulting to 30 seconds) before sending SIGKILL, which force stops the process. This hard stop could result in the pod’s 502 and 504 errors, as the in-flight requests were cut off during execution.

## Step 1: Fixing Signal Handling by modifying the Dockerfile [...] If a process custom handler doesn’t handling the SIGTERM, the default action by the default handler SIG\_DFL is taken. The default behavior for certain signals like SIGTERM, when applied to PID 1, is to ignore them. This is a safety mechanism and also the critical point here.   
  
To resolve this, we updated the Dockerfile to use the exec form of CMD:

```
FROM python:3.12-slim FROM python:3.12-slim WORKDIR /app WORKDIR /appCOPY . /app COPY . /appCOPY requirements.txt . COPY requirements.txt . RUN pip install -r requirements.txt RUN pip install -r requirements.txt CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80", "--workers", "4"] CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80", "--workers", "4"]
```
- [How to Configure Pod Termination Grace Period](https://oneuptime.com/blog/post/2026-01-25-pod-termination-grace-period/view) — ## Pod Termination Sequence

`sequenceDiagram
participant K as Kubernetes
participant P as Pod
participant C as Container
K->>P: Delete Pod
P->>P: Set to "Terminating"
P->>P: Mark terminating / not ready in EndpointSlices
K->>C: Execute preStop hook
Note over C: preStop runs
K->>C: Send SIGTERM
Note over C: App handles SIGTERM
Note over K,C: Wait terminationGracePeriodSeconds
K->>C: Send SIGKILL (if still running)
K->>P: Delete Pod`

## Default Behavior

The default termination grace period is 30 seconds:

`apiVersion: v1
kind: Pod
metadata:
name: myapp
spec:
terminationGracePeriodSeconds: 30 # Default
containers:
- name: myapp
image: myapp:1.0.0`

## Setting Custom Grace Period

### Increase for Long-Running Tasks

For applications that need more time to shut down gracefully: [...] ### Check Container Exit Code

`kubectl get pod myapp-pod -n production -o jsonpath='{.status.containerStatuses.lastState.terminated}'
# Exit codes:
# 0 - Normal exit (SIGTERM handled)
# 137 - SIGKILL (128 + 9)
# 143 - SIGTERM (128 + 15) - if not caught`

## Testing Graceful Shutdown

### Simulate Termination

`# Send SIGTERM to container process
kubectl exec myapp-pod -n production -- kill -SIGTERM 1
# Watch logs
kubectl logs myapp-pod -n production -f`

### Load Test During Rolling Update

`# Start load test
hey -z 2m -c 50 
# Trigger rolling update in another terminal
kubectl rollout restart deployment/myapp -n production
# Check for errors in load test output` [...] ### The Traffic Problem

`sequenceDiagram
participant LB as Load Balancer
participant EP as K8s Endpoints
participant Pod
Note over Pod: Pod termination starts
Pod->>EP: Mark terminating / not ready
Note over LB: Still routing traffic (stale cache)
LB->>Pod: Request arrives
Note over Pod: Receives SIGTERM
Note over Pod: Drops request!`

### The Solution: Delay + preStop

`spec:
terminationGracePeriodSeconds: 60
containers:
- name: api
lifecycle:
preStop:
exec:
command:
- sh
- -c
- |
# Wait for load balancer to update
sleep 15
# Now safe to start shutdown`

## Best Practices

### Match Grace Period to App Needs
- [Diagnose Kubernetes Pod Stuck in Terminating State Due to Finalizer Issues](https://oneuptime.com/blog/post/2026-02-09-pod-stuck-terminating-finalizer/view) — The problem arises when the controller responsible for a finalizer no longer runs. The finalizer blocks deletion, but nothing removes it. The pod stays in Terminating state forever unless you manually intervene.

## Identifying Pods Stuck in Terminating

Check for pods stuck in Terminating state across your cluster.

`# Find terminating pods
kubectl get pods --all-namespaces | \
grep Terminating
# Get more details with custom columns
kubectl get pods -A -o custom-columns=\
NAMESPACE:.metadata.namespace,\
NAME:.metadata.name,\
STATUS:.status.phase,\
DELETION:.metadata.deletionTimestamp
# Output shows:
# NAMESPACE NAME STATUS DELETION
# default stuck-pod-abc123 Running 2024-02-09T10:00:00Z`

A pod showing a deletion timestamp but still running indicates it's stuck in termination. [...] ## Understanding Kubernetes Finalizers

Finalizers are metadata fields that prevent object deletion until external cleanup completes. When you delete an object with finalizers, Kubernetes marks it for deletion by setting a deletion timestamp but doesn't remove it from etcd. Controllers watching that object perform cleanup operations and then remove their finalizer. Only when all finalizers are removed does Kubernetes actually delete the object.

Common finalizers include protection for persistent volume claims, cleanup for custom resources managed by operators, and garbage collection for dependent objects. Pods themselves rarely have finalizers, but when they do, stuck finalizers cause termination delays. [...] Run this as a CronJob for automated checking.

`apiVersion: batch/v1
kind: CronJob
metadata:
name: check-stuck-finalizers
namespace: kube-system
spec:
schedule: "/15    " # Every 15 minutes
jobTemplate:
spec:
template:
spec:
containers:
- name: checker
image: bitnami/kubectl:latest
command:
- /bin/bash
- /scripts/check-stuck-finalizers.sh
volumeMounts:
- name: scripts
mountPath: /scripts
volumes:
- name: scripts
configMap:
name: finalizer-check-script
defaultMode: 0755
serviceAccountName: finalizer-checker
restartPolicy: OnFailure`

## Force Deleting Pods as Last Resort

When a pod is stuck because the kubelet cannot finish graceful termination, force delete the pod. This bypasses graceful pod termination, but finalizers still need to be removed before Kubernetes can complete deletion.
- [Kubernetes Pods Stuck in Terminating: A Resolution Guide](https://kodekloud.com/blog/kubernetes-pods-stuck-in-terminating-a-resolution-guide) — #### Highlights

 The Root Cause: Pods usually stick in the "Terminating" state due to unfulfilled Finalizers, failed PreStop hooks, or strict StatefulSet ordering.
 The Fix for Finalizers: Manually edit the Pod metadata to remove the blocking finalizer key.
 The Fix for PreStop Hooks: Use the `--force` and `--grace-period=0` flags to bypass the graceful shutdown timer.
 The Fix for StatefulSets: Change the podManagementPolicy from OrderedReady to Parallel to speed up deletion.

If you are a DevOps engineer who works with Kubernetes, you might have encountered the frustrating issue where kubernetes pods stuck in terminating state refuse to go away. This can be problematic, especially if you need to free up resources or deploy new versions of your applications. [...] The Pod has a finalizer that prevents it from being deleted until a certain condition is met. A finalizer is a field in the Pod's metadata that specifies an external controller or resource that needs to perform some cleanup or finalization tasks before the Pod is deleted. For example, a Pod might have a finalizer that waits for a backup to finish or a volume to unmount. [...] ```
kubectl get pods
```

After the Pod creation process is complete, delete it by running the following command:

```
kubectl delete pod finalizer-demo
```

If you run the `kubectl get pods` again, you’ll see the Pod is now stuck in the terminating stage. When you deleted the Pod, it was not deleted. Instead, it was modified to include deletion time. To view this, run the following command and check the `metadata` section:

```
kubectl get pod/finalizer-demo -o yaml
```

You should see this in the metadata section:

To delete this pod, you’ll need to remove the finalizer manually. You do this by running the command:

```
kubectl edit pod finalizer-demo -n default
```
- [Kubernetes pod stuck Terminating: finalizers, grace periods, and force delete](https://www.netdata.cloud/guides/kubernetes/kubernetes-pod-stuck-terminating) — A pod stuck in `Terminating` stays visible in the API server after `kubectl delete`, sometimes for minutes or hours. Usually a finalizer blocks removal, a CSI volume is still attached, or the container is ignoring SIGTERM. Force deleting without diagnosis orphans containers and can violate StatefulSet guarantees. Check the signals first, then decide whether to wait, patch a finalizer, or force delete.

## What This Means

When you delete a pod, the API server sets `metadata.deletionTimestamp` and starts a graceful deletion window controlled by `terminationGracePeriodSeconds` (default 30). The kubelet executes any `preStop` hooks, sends SIGTERM to all containers, and waits up to the grace period before sending SIGKILL. [...] | Signal | Why it matters | Warning sign |
 --- 
| `kubelet_pleg_relist_duration_seconds` p99 | Slow PLEG means the kubelet cannot detect container exits, delaying Terminating state resolution | > 10 seconds sustained |
| `kubelet_runtime_operations_errors_total` | Failed CRI operations prevent container stop and volume unmount | Any sustained increase |
| VolumeAttachment count per node | Stuck attachments block pod deletion and rescheduling | Attachments persist longer than 6 minutes for terminated pods |
| Node Ready condition | NotReady nodes cannot complete graceful termination | Ready=False or Unknown for longer than 1 minute |
| `apiserver_request_duration_seconds` for DELETE on pods | Control plane saturation slows deletion processing | p99 > 1 second sustained | [...] | Cause | What it looks like | First thing to check |
 --- 
| Finalizer not removed by controller | `deletionTimestamp` is set, phase is Terminating, `finalizers` is non-empty | `kubectl get pod  -o jsonpath='{.metadata.finalizers}'` |
| CSI volume detach hang | Pod on a NotReady node, VolumeAttachment still present, container stopped | `kubectl get volumeattachment` |
| Application ignores SIGTERM | Container stays Running with `deletionTimestamp` set, no `preStop` hook active | `crictl ps -a` on the node |
| `preStop` hook hang | Events show hook execution, grace period appears to expire twice | `kubectl get event --field-selector involvedObject.name=` |
- [Kubernetes Pods Stuck in Terminating: A Resolution Guide - DEV Community](https://dev.to/imjoseangel/kubernetes-pods-stuck-in-terminating-a-resolution-guide-2jh3) — To delete the Pod, patch it on the command line to remove the finalizers:

```
--type = -p'[{"op": "remove", "path": "/metadata/finalizers" }]'
```

or

```
-p'{"metadata":{"finalizers":null}}'
```

Once the finalizer list is empty, the object can be reclaimed by Kubernetes and put into a queue to be deleted from the registry.

## Force Delete the POD

The Kubernetes Documentation asserts that force deletions do not wait for confirmation from the kubelet that the Pod has been Terminated. Use it with care and as a workaround solution:

```
--grace-period = --force
```

## Extra: Finalizers blocking Kubernetes upgrade

One or many of your Cluster node resources or availability can cause Pod eviction. [...] ```
kubectl delete pod/mypod & 
```

Kubernetes will report back that its deletion:

```
-o
```

What happened is that the object was updated, not deleted. The Pod gets modified to include the deletion timestamp keeping it in the `Terminating` state.

```
creationTimestamp: "2023-01-28T15:01:32Z" deletionGracePeriodSeconds: 0 deletionTimestamp: "2023-01-28T15:01:44Z" finalizers: - kubernetes status: state: terminated: containerID:containerd://b6298f7ee5613b717000bb5a54cf96e70f7f0cb8dd8e1c3c5f9d115b0fbfc7c9 exitCode: 0 finishedAt: "2023-01-28T15:01:44Z" reason: Completed startedAt: "2023-01-28T15:01:33Z"
```

### The PreStop hook and terminationGracePeriodSeconds

From the Kubernetes Documentation: [...] ## Why a Pod can hang on `Terminating` state

The most common reasons for a Pod hanging during the eviction process are:

 A Finalizer dependency
 An incorrect `terminationGracePeriodSeconds` value

### Finalizers

From Kubernetes documentation:

> Finalizers are namespaced keys that tell Kubernetes to wait until specific conditions are met before it fully deletes resources marked for deletion.

Finalizers are used to prevent the accidental deletion of resources. When a Pod hangs in the Terminating state, check its `metadata/finalizers`.

For instance, this example has a Kubernetes key as a finalizer used for namespaces.

```
kind: Pod metadata: finalizers: - kubernetes spec: containers:
```

Upon attempting to delete the pod:

```
kubectl delete pod/mypod & 
```
- [Stuck Kubernetes Finalizers - DevOps.dev](https://blog.devops.dev/stuck-kubernetes-finalizers-e20c7f0c9fb7) — Kubernetes resources sometimes get stuck in a Terminating state due to lingering finalizers that prevent deletion.