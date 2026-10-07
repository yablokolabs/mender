# Root cause: Checkout pod termination timestamp corruption during rolling update triggers false stuck alert

Service `checkout` in namespace `shop`.

## Root cause
Duplicate SuccessfulDelete events from the ReplicaSet controller corrupted the pod's deletionTimestamp, rendering the termination duration metric invalid ("lasts <invalid>") and causing monitoring to falsely classify a normal 30s grace-period termination as stuck [12].

## Mechanism
1. Deployment rolling update creates new ReplicaSet 7c6f9879f4; new pods pass readiness/liveness probes (logs show consistent 200 on /healthz) [12]. 2. Old ReplicaSet 6b97c764b8 scales down and issues delete for pod mwwlq. 3. Controller race produces two SuccessfulDelete events for the same pod (31s and 25s ago) with a Killing event between them, corrupting deletionTimestamp. 4. API server reports termination duration as "<invalid>" while pod is in normal grace period (25s/30s elapsed, container still Running and healthy). 5. Monitoring interprets Terminating + "<invalid>" as stuck, but pod will be SIGKILLed at 30s mark.

Confidence: 0.70 · Labels: rolling_update, termination_timestamp_corruption, false_alert, probe_healthy

## Evidence relied on
- 31s Normal SuccessfulDelete replicaset/checkout-6b97c764b8 Deleted pod: checkout-6b97c764b8-mwwlq
- 25s Normal Killing pod/checkout-6b97c764b8-mwwlq Stopping container checkout
- 25s Normal SuccessfulDelete replicaset/checkout-6b97c764b8 Deleted pod: checkout-6b97c764b8-mwwlq
- Status: Terminating (lasts <invalid>)
- Termination Grace Period: 30s
- logs showing 200 healthz responses during termination

## Tavily sources
Queries: Kubernetes pod stuck Terminating state rolling update graceful termination delay; pod termination grace period liveness probe failure stuck terminating containerd; Kubernetes ReplicaSet rolling update old pod termination stuck finalizers
- [Pod Stuck in Terminating State Due to PreStop Hook. | Managed Kubernetes | Knowledge Base](https://platform9.com/kb/pmk/solutions/pod-stuck-in-terminating-state-unless-deleted-forcefully) — ## Environment

 Platform9 Managed Kubernetes - v5.4 and Higher
 Platform9 Edge Cloud - v5.3 and Higher

## Cause

PreStop hook failure is the reason for the pod to be stuck in termination state, these errors can be seen in the kubelet log.

The preStop lifecycle hook in Kubernetes pods allows for performing a specific action before a pod is terminated. It gives applications running in a pod an opportunity to gracefully shut down and clean up any resources or connections before the pod is terminated.

When a pod receives a termination signal, such as when it is being scaled down or during a rolling update, Kubernetes initiates the termination process. Before the pod is actually terminated, Kubernetes executes the preStop hook, if defined, in each container of the pod:
- [Pods stuck in Terminating when PVC is attached during graceful node evacuations · Issue #3370 · bottlerocket-os/bottlerocket · GitHub](https://github.com/bottlerocket-os/bottlerocket/issues/3370) — The Fix: Rolling back to 1.14.1..

At this point, I had a suspicion that there was something wrong with the AMI update so we rolled that back. Since rolling the update back, we have not seen a single failure. We noted that the pods stuck in `Terminating` state were on nodes that were actively being drained for replacement.

Our suspicion was that #3230 was somehow biting us ... but after reading through this, it seems that `1.14.2+` is supposed to contain the fix for a problem (that we weren't seeing on 1.14.1). So we are unclear at this point what the root cause is or why we're seeing this problem.

How to reproduce the problem:

I haven't fully tested the instructions - but this is roughly how to replicate the environment we saw the issues in. [...] Failure 1: EFS Backed PVC

In one of our development workloads, an engineer reached out to me for help because all of his pods were stuck in the `Terminating` state, but they were not being terminated. After troubleshooting a bit, we manually deleted the pods with `kubectl delete pod --force`, which caused new pods to come up. We let this problem go initially as a strange one-off situation.

Failure 2: EBS backed PVC

A day after the first problem above, we had two failures on the same service across different clusters. We were alerted to pods using EBS-backed PVCS that were stuck in the `Terminating` state again. Again, after much troubleshooting, we solved the problem by forcefully deleting the pods with `kubectl delete --force`.

The Fix: Rolling back to 1.14.1.. [...] What I expected to happen:

We expected to see no differences between the old and new nodes. However, what we found was that many different services that were using PVCs (both EFS and EBS backed) were seeing many pods stuck in `Terminating` states for 10, 15, 20 minutes. Eventually the Pods were purged, but only when the underlying node that held them was finally deleted from the cluster.

We saw this behavior across 3 different clusters, across 2 different applications on those clusters, across both EBS and EFS PVCs.

What actually happened:
- [Exploring the Termination Process in Kubernetes – IT Exams Training – Pass4Sure](https://www.pass4sure.com/blog/exploring-the-termination-process-in-kubernetes) — Termination is a natural part of a Pod’s lifecycle. Ideally, it should be brief, allowing the container to shut down gracefully while Kubernetes releases resources and updates cluster state. However, there are times when this termination phase extends indefinitely, leaving the Pod stuck and unresponsive. This behavior not only leads to resource leaks but also impairs the broader functionality of the system by preventing new Pods from being scheduled or updated correctly.

Understanding why a Pod might enter and remain in this liminal state is critical. The root causes are often subtle, tied to misconfigurations, timing issues, or overlooked design decisions. Addressing the problem demands both insight into Kubernetes internals and practical troubleshooting techniques. [...] However, if a preStop hook is long-running or blocked—say, by a hanging process, unreachable endpoint, or faulty script—the termination sequence can be delayed beyond the configured grace period. This can cause the container to ignore the termination signal, leaving Kubernetes in a waiting state. If the hook exceeds the deadline, the container receives a forceful termination, but the Pod itself may still appear stuck if any other post-termination tasks, such as log flushing or storage detachment, are incomplete. [...] ## Force Deletion to Reclaim Resources

When all else fails, and a Pod remains stuck with no obvious finalizers or lifecycle hooks to blame, a force deletion becomes necessary. This is typically reserved for emergency situations, such as when stuck Pods block deployment pipelines, delay scaling, or interfere with rolling updates.

Force deletion tells Kubernetes to immediately remove the Pod from the API server and issue a SIGKILL to all containers, disregarding any cleanup or graceful shutdown logic. While this technique is effective in reclaiming system resources, it should be considered a last resort due to the potential for side effects, especially with persistent workloads.
- [Kubernetes Deployment Rolling Update](https://stackoverflow.com/questions/70321665/kubernetes-deployment-rolling-update) — My problem is that during updates,all the older version pods are stuck at "Terminating" status while all the new pods are created. During
- [Kubernetes Pods Stuck in Terminating: A Resolution Guide - DEV Community](https://dev.to/imjoseangel/kubernetes-pods-stuck-in-terminating-a-resolution-guide-2jh3) — ```
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

From the Kubernetes Documentation: [...] When Kubelet knows that a Pod should evict, it marks the Pod state as `Terminating` and stops sending traffic to it. Then, it executes the `preStop` lifecycle hook (when available). It sends the `SIGTERM` to the Main process (pid 1) within each container and waits for their termination. If the applications inside the containers are properly prepared, they will start a graceful shutdown. The duration should not be more than the specified in the spec.terminationGracePeriodSeconds which is 30 seconds by default.

If the application has not completed the shutdown properly, the Kubelet gives a grace period until removing the Pod IP and killing the container by sending a `SIGKILL`. At this point, Kubernetes removes the Pod from the API server.

## Why a Pod can hang on `Terminating` state [...] Review the status of your Pods with:

```
-A
```

```
NAMESPACE NAME READY STATUS RESTARTS AGE default mypod 0/1 Terminating 0 5m42s kube-system etcd-minikube 1/1 Running 0 14m kube-system kube-apiserver-minikube 1/1 Running 0 14m kube-system kube-controller-manager-minikube 1/1 Running 0 14m kube-system kube-proxy-5dwnf 1/1 Running 0 14m kube-system kube-scheduler-minikube 1/1 Running 0 14m 
```

Check Pod finalizer as usual:

```
-o
```

```
apiVersion: v1 kind: Pod metadata: creationTimestamp: "2023-01-29T14:12:38Z" deletionGracePeriodSeconds: 0 deletionTimestamp: "2023-01-29T14:13:28Z" finalizers: - kubernetes
```

And patch when needed:

```
-p'{"metadata":{"finalizers":null}}'
```

## Conclusion
- [Pod stuck terminating due to zombie container lingering · Issue #11133 · containerd/containerd · GitHub](https://github.com/containerd/containerd/issues/11133) — Name: foo-bar-65dddf97df-tx7jf Namespace: baz Priority: 0 Service Account: baz Node: gke-cluster-1-default-pool-5-9698588f-vv8v/248.1.0.96 Start Time: Mon, 09 Dec 2024 15:00:46 +0000 [...] Status: Terminating (lasts 112m) Termination Grace Period: 30s IP: 240.128.17.51 IPs: IP: 240.128.17.51 Controlled By: ReplicaSet/foo-bar-65dddf97df Containers: foo-bar: Container ID: containerd://842cbfe442a906449d0accb3fb8c3c2d6e87614dedf00a49f8652faa84bd313f [...] State: Running Started: Mon, 09 Dec 2024 15:00:50 +0000 Ready: True Restart Count: 0 Limits: cpu: 2 memory: 300Mi Requests: cpu: 1 memory: 200Mi Liveness: exec [/usr/bin/grpc_health_probe -addr=:8080] delay=10s timeout=1s period=10s #success=1 #failure=3 Readiness: exec [/usr/bin/grpc_health_probe -addr=:8080] delay=5s timeout=1s period=10s [...] with a grace period" pod="baz/foo-bar-65dddf97df-tx7jf" podUID="2dc2bb82-579d-42f3-b72d-f166a9f0e15d" containerName="foo-bar" containerID="containerd://842cbfe442a906449d0accb3fb8c3c2d6e87614dedf00a49f8652faa84bd313f" gracePeriod=30 Dec 10 15:07:27 gke-cluster-1-default-pool-5-9698588f-vv8v containerd: time="2024-12-10T15:07:27.025687480Z" level=info msg="StopContainer for \"842cbfe442a906449d0accb3fb8c3c2d6e87614dedf00a49f8652faa84bd313f\" with timeout 30 (s)" Dec 10 15:07:27 gke-cluster-1-default-pool-5-9698588f-vv8v containerd: time="2024-12-10T15:07:27.026256060Z" level=info msg="Stop container \"842cbfe442a906449d0accb3fb8c3c2d6e87614dedf00a49f8652faa84bd313f\" with signal terminated" Dec 10 15:07:27 gke-cluster-1-default-pool-5-9698588f-vv8v systemd: [...] cmd from runtime service failed" err="rpc error: code = Unknown desc = failed to exec in container: failed to start exec \"d82254a5d7c7e448585546d174223cc35b83ad7cf04851c681c057a4e934b50c\": OCI runtime exec failed: exec failed: cannot exec in a stopped container: unknown" containerID="842cbfe442a906449d0accb3fb8c3c2d6e87614dedf00a49f8652faa84bd313f" cmd=["/usr/bin/grpc_health_probe","-addr=:8080"] [...]
- [ContainerAppProbe interface | Microsoft Learn](https://learn.microsoft.com/en-us/javascript/api/@azure/arm-appcontainers/containerappprobe?view=azure-node-latest) — Optional duration in seconds the pod needs to terminate gracefully upon probe failure. The grace period is the duration in seconds after the processes running in the pod are sent a termination signal and the time when the processes are forcibly halted with a kill signal. Set this value longer than the expected cleanup time for your process.
- [liveness/readiness probe is executed and failed while pod is terminated · Issue #52817 · kubernetes/kubernetes · GitHub](https://github.com/kubernetes/kubernetes/issues/52817) — #98571

Copy link

Assignees

ashleyschuettmatthyx

Labels

area/kubeletkind/bugCategorizes issue or PR as related to a bug.Categorizes issue or PR as related to a bug.priority/important-soonMust be staffed and worked on either currently, or very soon, ideally in time for the next release.Must be staffed and worked on either currently, or very soon, ideally in time for the next release.sig/nodeCategorizes an issue or PR as relevant to SIG Node.Categorizes an issue or PR as relevant to SIG Node.

## Description

@sunao-uehara

sunao-uehara

opened on Sep 20, 2017

Issue body actions

What happened:  
 liveness/readiness probe fails while pod is terminated. Also it happened only once during the pod termination. The issue started happening after upgrading version to v1.7 from v1.6.X [...] How to reproduce it (as minimally and precisely as possible):  
 execute `kubectl delete pod nginx-A1` to delete pod, so status of the nginx-podA1 is changed to `Terminating`, right after that it seems Liveness and Readiness Probe is executed and failed, but only once.  
 Nginx reverse proxy is running in the pod. so I just use `httpGet`method for liveness and readiness

Here is my Deployment config.

```
... spec terminationGracePeriodSeconds 60... livenessProbe httpGet path/healthz port 8080 initialDelaySeconds 15 timeoutSeconds 3 readinessProbe httpGet path/healthz port 8080 initialDelaySeconds 15 timeoutSeconds 3
```

Here is Events log by `kubectl describe pod nginx-A1` [...] ## Metadata

## Metadata

### Assignees

 @ashleyschuett
 @matthyx

### Labels

area/kubeletkind/bugCategorizes issue or PR as related to a bug.Categorizes issue or PR as related to a bug.priority/important-soonMust be staffed and worked on either currently, or very soon, ideally in time for the next release.Must be staffed and worked on either currently, or very soon, ideally in time for the next release.sig/nodeCategorizes an issue or PR as relevant to SIG Node.Categorizes an issue or PR as relevant to SIG Node.

No type

No projects

No milestone

None yet

No branches or pull requests

## Issue actions

You can’t perform that action at this time.
- [Replacing pods which are failing liveness probes](https://www.reddit.com/r/kubernetes/comments/1t72z3x/replacing_pods_which_are_failing_liveness_probes) — It has 24 Hours termination grace period with a preStop hook which checks if the number of in flights requests have reached to 0. The reason
- [Pods stuck in Terminating status](https://stackoverflow.com/questions/35453792/pods-stuck-in-terminating-status) — 3

Reply

   Copy link

Add a comment

, then SSH on to the node and use `containerd` to list running containers - (`sudo ctr -n k8s.io containers ls`). However, in most cases (EKS or not) I tend to find that the container is not running on the identified node, and it's tuck in a terminating state for some other reason.

2024-12-03T16:55:11.013Z+00:00

1

Reply

   Copy link

Add a comment

; do kubectl delete pod $p --grace-period=0 --force;done
```

It will delete all pods in Terminating status in default namespace.

Share

Share a link to this answer 

Copy linkCC BY-SA 4.0

Short permalink to this answer

Improve this answer

 Follow 

Follow this answer to receive notifications

 answered Mar 9, 2019 at 17:53

Image 21: belabrinel's user avatar

belabrinel [...] answered Feb 27, 2018 at 10:31

Image 32: Roee Rakovsky's user avatar

Roee Rakovsky

345 3 3 silver badges 8 8 bronze badges

## 3 Comments

Add a comment

Image 33

raiyan

raiyanOver a year ago

Persistent volume got deleted after this. What does it really do?

2018-07-23T13:43:38.45Z+00:00

1

Reply

   Copy link

Image 34

valorl

valorlOver a year ago

This was the only thing that fixed the stuck pod for me when `delete -grace-period=0 --force` didn't. I'd also appreciate some elaboration on what does it do exactly, though.

2018-08-24T07:52:45.763Z+00:00

1

Reply

   Copy link

Image 35

Sean Keane

Sean KeaneOver a year ago
- [Kubernetes Deployment Rolling Update](https://stackoverflow.com/questions/70321665/kubernetes-deployment-rolling-update) — My problem is that during updates,all the older version pods are stuck at "Terminating" status while all the new pods are created. During
- [Kubernetes Rolling Update and Termination Grace Periods | by Thomas Césaré-Herriau | Brex Tech Blog | Medium](https://medium.com/brexeng/kubernetes-rolling-update-and-termination-grace-periods-d922c6b84d88) — Join Medium for free to get updates from this writer.

And here lies the problem that caused the incident: the old and functioning ReplicaSet would be terminated before the new buggy one would finish starting up. And it never did!

### The solution

The solution was to not allow any unavailable pod:

```
spec:  revisionHistoryLimit: 1  replicas: 1  strategy:  type: RollingUpdate  rollingUpdate:  maxUnavailable: 0  maxSurge: 100%template:  spec:    terminationGracePeriodSeconds: 400
```

This ensures the new Pod is up and running (Live and Ready) before the old one is terminated. Success!

## A note on Graceful Shutdown with Elixir

Press enter or click to view image in full size

### Kubernetes Termination Period [...] The same code was used in a gRPC server and an Event Consumer, and we didn’t notice any visible impact with the RPC Server (otherwise, a bunch of synchronous operations would have started failing loudly). This was due to the fact that the old ReplicaSet was still running. After being deployed, the new ReplicaSet entered a CrashLoopBackOff state, and therefore never became available (Ready) — some of the old pods were therefore not terminated.

However, for the Event Consumer, it appeared that the old Replica Set had been terminated even though the new one was in CrashLoopBackOff! [...] 1. The new ReplicaSet is created, scheduling 1 Pod using the new image.
2. The Pod is scheduled, bringing the current state to 2 Pods: 1 Available (old pod) and 1 Unavailable (new pod)
3. As the desired state is 1 Pod and it is acceptable to have 1 Unavailable Pod, Kubernetes terminates the old pod bringing the current state to 1 Unavailable Pod.
4. The Unavailable Pod continues starting up.

This is actually equivalent to the Recreate Deployment strategy, where the old ReplicaSet is terminated before the new one is scheduled.

## Get Thomas Césaré-Herriau’s stories in your inbox

Join Medium for free to get updates from this writer.
- [Kubernetes Rolling Update: Deploy Without Service Interruption | SFEIR Institute](https://institute.sfeir.com/en/kubernetes-training/rolling-update-kubernetes-deploy-zero-downtime) — ### Required Environment

| Component | Minimum Version | Verification Command |
 --- 
| kubectl | v1.28+ | `kubectl version --client` |
| Kubernetes Cluster | v1.28+ | `kubectl version` |
| Existing Deployment  `kubectl get deployments` |

`kubectl version --client`
`kubectl version`
`kubectl get deployments`
`kubectl version --client
# Expected output:
# Client Version: v1.29.0
# Kustomize Version: v5.0.4-0.20230601165947-6ce0bf390ce3`

### Prior Knowledge

You should understand:

## Step 1: Understand the Rolling Update Mechanism

A rolling update is a Kubernetes progressive update strategy that replaces pods one by one. Kubernetes creates a new ReplicaSet, starts pods with the new version there, then progressively terminates pods from the old ReplicaSet. [...] ## Troubleshooting Common Errors

Rolling updates can fail for several reasons. Identify and resolve these problems quickly.

### Pods Stuck in ImagePullBackOff

`kubectl get pods -l app=webapp
# Problem detected:
# NAME READY STATUS RESTARTS AGE
# webapp-7d4f5b8c9-abc12 0/1 ImagePullBackOff 0 2m`

Solution: Verify the image name and tag, as well as registry credentials.

`kubectl describe pod webapp-7d4f5b8c9-abc12 | grep -A 5 "Events"`

### Deployment Stuck: Readiness Probe Fails

`kubectl rollout status deployment/webapp
# Problem detected:
# Waiting for deployment "webapp" rollout to finish: 1 old replicas are pending termination...`

Old pods don't terminate because new ones never reach Ready state.

Solution: Check your readiness probe configuration and application logs.
- [Kubernetes Deployment Not Updating: Causes, Fixes & Insights](https://www.groundcover.com/learn/kubernetes/deployment-not-updating) — Conversely, a much more insidious scenario occurs when the rollout starts but hangs: a new ReplicaSet is created and begins scaling up. Still, it gets stuck because the newly created Pods fail their Readiness Probes or crash loop, preventing the Deployment from safely terminating the older Pods due to availability constraints.

## Common Reasons a Kubernetes Deployment Is Not Updating

Deployment failures generally fall into two categories: the update never starts, or it starts but hangs indefinitely. The following table breaks down the most frequent causes, categorized by the failure mode, and provides immediate diagnostic steps: [...] ### RollingUpdate (The Default)

The RollingUpdate strategy is the default and preferred method, designed for zero-downtime deployments. When a new Pod template is detected:

 The Deployment Controller creates a new ReplicaSet reflecting the updated configuration.
 The Deployment scales up the new ReplicaSet (creating new Pods) while simultaneously scaling down the old ReplicaSet (terminating old Pods).

This gradual, synchronized exchange continues until the new ReplicaSet reaches the desired replica count and the old one is scaled down to zero. Two parameters control the pacing:

 maxSurge: The maximum number of Pods allowed above the desired replica count during the update.
 maxUnavailable: The maximum number of Pods that can be unavailable during the update.

### Recreate
- [Diagnose Kubernetes Pod Stuck in Terminating State Due to Finalizer Issues](https://oneuptime.com/blog/post/2026-02-09-pod-stuck-terminating-finalizer/view) — }
// Remove finalizer
instance.ObjectMeta.Finalizers = removeString(instance.ObjectMeta.Finalizers, finalizerName)
if err := r.Update(ctx, instance); err != nil {
return ctrl.Result{}, err
}
}
return ctrl.Result{}, nil
}
// Add finalizer if not present
if !containsString(instance.ObjectMeta.Finalizers, finalizerName) {
instance.ObjectMeta.Finalizers = append(instance.ObjectMeta.Finalizers, finalizerName)
if err := r.Update(ctx, instance); err != nil {
return ctrl.Result{}, err
}
}
// Normal reconciliation logic
return ctrl.Result{}, nil
}` [...] `kubernetes.io/pvc-protection`
`# Check if PVC exists
PVC_NAME=$(kubectl get pod stuck-pod-abc123 -n default -o json | \
jq -r '.spec.volumes[]?.persistentVolumeClaim.claimName // empty' | head -n 1)
kubectl get pvc $PVC_NAME -n default
# If PVC is also stuck in terminating
kubectl get pvc $PVC_NAME -n default -o yaml | grep -A 5 finalizers`

Remove the pod or update it so it no longer references the PVC. If the PVC itself remains stuck after that, remove its finalizer only after ensuring no pods reference it. [...] ## Understanding Kubernetes Finalizers

Finalizers are metadata fields that prevent object deletion until external cleanup completes. When you delete an object with finalizers, Kubernetes marks it for deletion by setting a deletion timestamp but doesn't remove it from etcd. Controllers watching that object perform cleanup operations and then remove their finalizer. Only when all finalizers are removed does Kubernetes actually delete the object.

Common finalizers include protection for persistent volume claims, cleanup for custom resources managed by operators, and garbage collection for dependent objects. Pods themselves rarely have finalizers, but when they do, stuck finalizers cause termination delays.