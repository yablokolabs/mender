# Root cause: Checkout pods stuck in Terminating state during rolling deployment update

Service `checkout` in namespace `shop`.

## Root cause
Pod finalizer or PreStop hook failure preventing clean termination during Deployment rolling update

## Mechanism
1. Deployment rolling update creates new ReplicaSet (5dbb69d55d) and scales it up [EVENTS: ScalingReplicaSet, SuccessfulCreate]
2. New pods start successfully and pass readiness/liveness probes [LOGS: healthz 200 responses]
3. Old ReplicaSet (5cf6bd4cc7) pods receive termination signal and enter Terminating state [EVENTS: Killing, SuccessfulDelete]
4. Termination grace period (30s) expires but pods remain stuck with 'Terminating (lasts <invalid>)' [PODS: Status field]
5. A finalizer or PreStop hook fails to complete, blocking API server from removing pod metadata [1][15]
6. Rollout completes with new healthy pods but old pods orphaned in Terminating state

Confidence: 0.85 · Labels: pod_stuck_terminating, finalizer_issue, rolling_update, prestop_hook, deployment

## Evidence relied on
- PODS: Status: Terminating (lasts <invalid>)
- EVENTS: Killing pod/checkout-5cf6bd4cc7-vpsw7 Stopping container checkout
- EVENTS: SuccessfulDelete replicaset/checkout-5cf6bd4cc7 Deleted pod
- LOGS: healthz 200 responses showing old pods healthy before termination
- [1] PreStop hook failure is the reason for the pod to be stuck in termination state
- [15] Pods usually stick in Terminating state due to unfulfilled Finalizers, failed PreStop hooks

## Tavily sources
Queries: Kubernetes pod stuck terminating invalid duration replica set cleanup rolling update; pod termination grace period invalid status stuck terminating finalizer kubernetes; deployment rolling update replica set deletion pods stuck terminating state
- [Pod Stuck in Terminating State Due to PreStop Hook. | Managed Kubernetes | Knowledge Base](https://platform9.com/kb/pmk/solutions/pod-stuck-in-terminating-state-unless-deleted-forcefully) — ## Environment

 Platform9 Managed Kubernetes - v5.4 and Higher
 Platform9 Edge Cloud - v5.3 and Higher

## Cause

PreStop hook failure is the reason for the pod to be stuck in termination state, these errors can be seen in the kubelet log.

The preStop lifecycle hook in Kubernetes pods allows for performing a specific action before a pod is terminated. It gives applications running in a pod an opportunity to gracefully shut down and clean up any resources or connections before the pod is terminated.

When a pod receives a termination signal, such as when it is being scaled down or during a rolling update, Kubernetes initiates the termination process. Before the pod is actually terminated, Kubernetes executes the preStop hook, if defined, in each container of the pod: [...] The preStop hook within the pod:

```
# kubectl get pod pod_name3 -n ns1 -oyaml # kubectl get pod pod_name3 -n ns1 -oyaml # kubectl  get  pod  pod_name3  - n  ns1  - oyamlapiVersion: v1 apiVersion: v1 apiVersion:  v1kind: Pod kind: Pod kind:  Podmetadata: metadata: metadata: name: pod_name3  name: pod_name3  name:  pod_name3 namespace: ns1  namespace: ns1  namespace:  ns1spec: spec: spec: containers:   containers:   containers:   preStop:   preStop:   preStop:   exec:  exec:  exec: command:  command:  command: - /bin/bash  - /bin/bash  -  / bin/ bash - -c  - -c  -  - c - service stop httpd; sleep 20 - service stop httpd; sleep 20  -  service  stop  httpd;  sleep  20
```

## Solution
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

### Kubernetes Termination Period [...] You may have identified the problem — we had kept the default configuration which worked well for our RPC servers. And the Elixir application terminates itself after 20 seconds! Therefore Kubernetes will not wait the whole terminationGracePeriodSeconds period, as the pod’s process will terminate before it expires. You can configure this differently within your application but…

### There is another problem…

There is also another assumption made that defeats the purpose of having such a long termination period. [...] ### Configuration

After some investigation, we discovered that it wasn’t a faulty readiness check that led to the bad behavior of our deployment. The Readiness Probe actually had worked as expected, and never returned true. From Kubernetes perspective, the new Replica Set had never become ready.

What had happened was a bit more subtle. Let’s look at part of our Events Consumer Deployment configuration. We use Helm charts and templates, and some configuration values were shared between our RPC Server and Events Consumer deployments. It would resolve to the following:

```
spec:  revisionHistoryLimit: 1  replicas: 1  strategy:  type: RollingUpdate  rollingUpdate:  maxUnavailable: 1  maxSurge: 100%template:  spec:  terminationGracePeriodSeconds: 400
```
- [Pods stuck in Terminating status. When Kubernetes pods get stuck in the… | by Harold Finch | Medium](https://medium.com/@haroldfinch01/pods-stuck-in-terminating-status-083168c6b7e8) — Sitemap

Open in app

Sign in

Sign in

Harold Finch

## Harold Finch

A DevOps Engineer Looking for new challenges

Kubernetes

DevOps

Linux

Terraform

AWS

# Pods stuck in Terminating status

Harold Finch

Harold Finch

2 min read

·

May 25, 2024

Press enter or click to view image in full size

Pods stuck in Terminating status

When Kubernetes pods get stuck in the “Terminating” status, it can be frustrating and disruptive. This issue often arises when the Kubernetes API server cannot fully complete the termination process for the pods. Here are some common causes and steps to resolve the problem:

> Common Causes

1. Finalizers [...] > Common Causes

1. Finalizers

 Finalizers are functions that Kubernetes must execute before deleting resources. If a pod has a finalizer that cannot complete, it will remain in the “Terminating” state.

2. Stuck Volumes

 Persistent volumes attached to the pod might be stuck in the unmount process.

3. Network Issues

 Network disruptions can prevent the Kubernetes API server from communicating with the node where the pod is running.

4. Graceful Termination Timeout

 The pod might be taking longer to terminate gracefully than the allowed termination grace period.

> Steps to Resolve

1. Check Pod Details

 Inspect the pod details to identify potential issues.

```
kubectl describe pod <pod-name><pod-name>pod-name
```

2. Force Delete the Pod [...] Proper Resource Management
 Ensure resources are appropriately managed and there are sufficient system resources to handle pod operations.
 Graceful Termination Handling
 Implement proper handling in your applications to ensure they terminate gracefully within the allowed time.

Pods getting stuck in the “Terminating” status can often be resolved by forcefully deleting the pods, removing finalizers, or addressing underlying node issues. Regular monitoring and proactive management of resources can help prevent these issues from occurring. By following these steps, you can effectively manage and troubleshoot stuck pods in your Kubernetes environment.

## Get Harold Finch’s stories in your inbox

Join Medium for free to get updates from this writer.
- [Kubernetes Pods Stuck in Terminating: A Resolution Guide - DEV Community](https://dev.to/imjoseangel/kubernetes-pods-stuck-in-terminating-a-resolution-guide-2jh3) — Review the status of your Pods with:

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

## Conclusion [...] When Kubelet knows that a Pod should evict, it marks the Pod state as `Terminating` and stops sending traffic to it. Then, it executes the `preStop` lifecycle hook (when available). It sends the `SIGTERM` to the Main process (pid 1) within each container and waits for their termination. If the applications inside the containers are properly prepared, they will start a graceful shutdown. The duration should not be more than the specified in the spec.terminationGracePeriodSeconds which is 30 seconds by default.

If the application has not completed the shutdown properly, the Kubelet gives a grace period until removing the Pod IP and killing the container by sending a `SIGKILL`. At this point, Kubernetes removes the Pod from the API server.

## Why a Pod can hang on `Terminating` state [...] ## Why a Pod can hang on `Terminating` state

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
- [Kubernetes Pod Stuck in Terminating State | Shivam Rana ...](https://www.linkedin.com/posts/shivam-rana-873a3b99_kubernetes-kubernetesdebugging-devops-activity-7497857792788332545-1rmT) — But if a preStop hook or cleanup process takes too long, the Pod can remain stuck in Terminating — and your rollout can get stuck with it.
- [Diagnose Kubernetes Pod Stuck in Terminating State Due to Finalizer Issues](https://oneuptime.com/blog/post/2026-02-09-pod-stuck-terminating-finalizer/view) — `# Force delete with grace period 0
kubectl delete pod stuck-pod-abc123 -n default --force --grace-period=0
# Warning: This leaves cleanup incomplete
# Only use when absolutely necessary`

Force deletion should be a last resort after attempting proper finalizer removal, as it can leave orphaned resources that require manual cleanup. [...] Run this as a CronJob for automated checking.

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

When a pod is stuck because the kubelet cannot finish graceful termination, force delete the pod. This bypasses graceful pod termination, but finalizers still need to be removed before Kubernetes can complete deletion. [...] `# Get current finalizers
kubectl get pod stuck-pod-abc123 -n default -o jsonpath='{.metadata.finalizers}'
# Remove specific finalizer using JSON patch
kubectl patch pod stuck-pod-abc123 -n default --type json \
-p='[{"op": "remove", "path": "/metadata/finalizers/0"}]'`

After removing finalizers, verify the pod terminates successfully.

`# Watch pod status
kubectl get pod stuck-pod-abc123 -n default -w
# Should show deletion within seconds
# stuck-pod-abc123 Terminating 0/1 0 5m
# stuck-pod-abc123 Terminating 0/1 0 5m1s (deleted)`

## Handling Pods with PVC Protection Finalizer

The `kubernetes.io/pvc-protection` finalizer prevents deletion of PVCs while pods are using them. A deleted PVC stays in Terminating until no pod object references it.
- [How to Fix "Kubernetes Pods stuck in Terminating status" Error?](https://supportfly.io/kubernetes-pods-stuck-in-terminating-status) — ### Step-4: Force Delete the Pod

If the previous step of removal of the finalizer did not work, you need to delete the pod forcefully by running the following command.This command will forcefully delete the pod, ignoring the grace period.

kubectl delete pod  -n  –grace-period=0 –force

### Step-5: Check Node Status

If the pod still stucks in the terminating state after forcefully deletion , you should check the status of the node it was running on. You can do this by running the following command.This command will give you a detailed description of the node, including its status and any events that have occurred.

kubectl describe node

### Step-6: Restart the Kubelet [...] ### Step-2: Checking the Pod Status

After the first process of identifying the pods causing the problem, check this Pod’s status to see why it’s stuck in the terminating state. You can do this by running the following command. This command will give you a description in detail of the pod, including its current status and any events that have occurred.

kubectl describe pod  -n

### Step-3: Remove the Finalizer

If a pod gets stuck in the terminating condition, it may be likely because it has a finalizer that prevents it from being deleted. To remove the finalizer, you need to run the following command.This command will remove all finalizers from the pod, allowing it to be deleted.

kubectl patch pod  -n  -p ‘{“metadata”:{“finalizers”:[]}}’ –type=merge

### Step-4: Force Delete the Pod
- [Kubernetes Pods Stuck in Terminating: A Resolution Guide - DEV Community](https://dev.to/imjoseangel/kubernetes-pods-stuck-in-terminating-a-resolution-guide-2jh3) — Review the status of your Pods with:

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

## Conclusion [...] From the Kubernetes Documentation:

> If a `PreStop` hook hangs during execution, the Pod's phase will be `Terminating` and remain there until the Pod is killed after its `terminationGracePeriodSeconds` expires.

For instance. This configuration:

```
spec: terminationGracePeriodSeconds: 3600 containers: - lifecycle: preStop: exec: command: -/bin/sh - -c - sleep 3600
```

Will keep the Pod in the `Terminating` state for 1 hour.

It is essential to handle the `SIGTERM` correctly and ensure that the application terminates gracefully when the kubelet sends the `SIGTERM` to the container.

## Remove Finalizers

Determine if the cause of the `Terminating` state for a Pod, Namespace, or PVC is a finalizer. A Finalizer example to protect PVCs from deletion is the `kubernetes.io/pvc-protection`. [...] ## Why a Pod can hang on `Terminating` state

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
- [Kubernetes pod stuck Terminating: finalizers, grace periods, and force delete](https://www.netdata.cloud/guides/kubernetes/kubernetes-pod-stuck-terminating) — A pod stuck in `Terminating` stays visible in the API server after `kubectl delete`, sometimes for minutes or hours. Usually a finalizer blocks removal, a CSI volume is still attached, or the container is ignoring SIGTERM. Force deleting without diagnosis orphans containers and can violate StatefulSet guarantees. Check the signals first, then decide whether to wait, patch a finalizer, or force delete.

## What This Means

When you delete a pod, the API server sets `metadata.deletionTimestamp` and starts a graceful deletion window controlled by `terminationGracePeriodSeconds` (default 30). The kubelet executes any `preStop` hooks, sends SIGTERM to all containers, and waits up to the grace period before sending SIGKILL. [...] 5. Evaluate node health. A node with an unhealthy PLEG, runtime disconnection, or kubelet OOM can lose the ability to report container status or complete unmounts. If the node is NotReady, eviction may be initiated but the kubelet cannot complete it.
6. Choose the intervention. If a finalizer is stuck and the owning controller is permanently gone, patch the finalizers. If a volume is stuck and the node is dead, wait for the attach-detach controller timeout or manually detach if the storage backend allows. If the application is ignoring SIGTERM, reduce `terminationGracePeriodSeconds` after fixing the application. Only use force delete when you accept that the container may continue running on the node and that StatefulSet at-most-one semantics may be violated. [...] If the application ignores SIGTERM or a `preStop` hook hangs, the effective termination time can exceed the configured grace period. In Kubernetes 1.26, upstream issue #115817 documents behavior where the kubelet may grant a second full grace period after a hung `preStop` hook times out, doubling the wait. For pods with CSI volumes, the kubelet depends on the volume manager to signal the CSI driver when it is safe to unmount. On node shutdown, the CSI driver may terminate before workload volumes fully unmount, leaving the Attach/Detach controller to wait several minutes before issuing a force detach.

## Common Causes
- [Kubernetes Pods Stuck in Terminating: A Resolution Guide](https://kodekloud.com/blog/kubernetes-pods-stuck-in-terminating-a-resolution-guide) — #### Highlights

 The Root Cause: Pods usually stick in the "Terminating" state due to unfulfilled Finalizers, failed PreStop hooks, or strict StatefulSet ordering.
 The Fix for Finalizers: Manually edit the Pod metadata to remove the blocking finalizer key.
 The Fix for PreStop Hooks: Use the `--force` and `--grace-period=0` flags to bypass the graceful shutdown timer.
 The Fix for StatefulSets: Change the podManagementPolicy from OrderedReady to Parallel to speed up deletion.

If you are a DevOps engineer who works with Kubernetes, you might have encountered the frustrating issue where kubernetes pods stuck in terminating state refuse to go away. This can be problematic, especially if you need to free up resources or deploy new versions of your applications. [...] ```
kubectl delete pod prestop-demo
```

If you run the `kubectl get pods` again, you’ll see the Pod is now stuck in the terminating stage. When you deleted the Pod, it was not deleted. Instead, it was modified to include deletion time. To view this, run the following command and check the `metadata` section:

```
kubectl get pod/prestop-demo -o yaml
```

You should see this in the metadata section:

Note that the deletionGracePeriodSeconds is set at 3600. This means the pod will be terminated one hour after the delete command is executed. However, you can remove it instantly and bypass the grace period. You do that by setting the new grace period to 0 using the following command:

```
kubectl delete Pod prestop-demo -n default --force --grace-period=0
``` [...] If you need a refresher on Pods in Kubernetes, you can read our article on What Are Pods in Kubernetes? A Quick Explanation for a simple overview.

## Resolving Pod Stuck in Termination Due to Finalizer

In this section, we shall use a simple example to demonstrate how to resolve the termination issue due to the finalizer.

Create a YAML file named deployment.yaml with the following specs:

```
apiVersion: v1 kind: Pod metadata: name: finalizer-demo finalizers: - kubernetes spec: containers: - name: finalizer-demo image: nginx:latest ports: - containerPort: 80 
```

Create a Pod by running the following command:

```
kubectl create -f deployment.yaml
```

Verify the Pod has been created using the following command:

```
kubectl get pods
```
- [Some pods stuck in Terminating state and can only be removed if deleting with propagationPolicy=Background · Issue #65569 · kubernetes/kubernetes · GitHub](https://github.com/kubernetes/kubernetes/issues/65569) — Copy link

Labels

kind/bugCategorizes issue or PR as related to a bug.Categorizes issue or PR as related to a bug.sig/api-machineryCategorizes an issue or PR as relevant to SIG API Machinery.Categorizes an issue or PR as relevant to SIG API Machinery.

## Description

@frittentheke

frittentheke

opened on Jun 28, 2018

Issue body actions

/kind bug

What happened:  
 One (worker) node went OOM and pods where evicted. Before the node was "saved" the kernel OOM-killed at least some of the running containers.

The cluster came back to a save state, but a few pods got stuck in the state terminating.  
 The issue / bug is, that there is no way to delete those pods via kubectl. I was able to remove the deployment and replica-set, but the pods still waited there "Terminating". [...] Only after I send a DELETE request via API using  
 `'{"kind":"DeleteOptions","apiVersion":"v1","propagationPolicy":"Background"}`

the Pods where deleted.

Also the kubelet on that node where the Pod / container used to run was actively sending DELETE requests to the API with no luck. There are also

I strongly believe there is some "inconsistency" in the data that

What you expected to happen:

The pods to be deleted.

How to reproduce it (as minimally and precisely as possible):

I shall attach a Pod object which I successfully deleted with propagationPolicy=Background and I do have more Pods in state Terminating that I can get info off if need be.

Anything else we need to know?: [...] Skip to content   
 
 

## Navigation Menu

Sign in

Appearance settings

Sign in

Sign up

Appearance settings

You signed in with another tab or window. Reload to refresh your session. You signed out in another tab or window. Reload to refresh your session. You switched accounts on another tab or window. Reload to refresh your session. Dismiss alert

{{ message }}

kubernetes   /  kubernetes  Public

 Notifications  You must be signed in to change notification settings
 Fork 46.2k
 Star  128k

# Some pods stuck in Terminating state and can only be removed if deleting with propagationPolicy=Background #65569

Copy link

Copy link

Closed

Closed

Some pods stuck in Terminating state and can only be removed if deleting with propagationPolicy=Background#65569

Copy link

Labels
- [Deployments | Kubernetes](https://kubernetes.io/docs/concepts/workloads/controllers/deployment) — #### Note:

This will only guarantee Pod termination previous to creation for upgrades. If you upgrade a Deployment, all Pods of the old revision will be terminated immediately. Successful removal is awaited before any Pod of the new revision is created. If you manually delete a Pod, the lifecycle is controlled by the ReplicaSet and the replacement will be created immediately (even if the old Pod is still in a Terminating state). If you need an "at most" guarantee for your Pods, you should consider using a StatefulSet.

#### Rolling Update Deployment [...] Pods that become terminating due to deletion or scale down may take a long time to terminate, and may consume additional resources during that period. As a result, the total number of all pods can temporarily exceed `.spec.replicas`. Terminating pods can be tracked using the `.status.terminatingReplicas` field of the Deployment.

### Revision History Limit

A Deployment's revision history is stored in the ReplicaSets it controls. [...] #### Rolling Update Deployment

The Deployment updates Pods in a rolling update fashion (gradually scale down the old ReplicaSets and scale up the new one) when `.spec.strategy.type==RollingUpdate`. You can specify `maxUnavailable` and `maxSurge` to control the rolling update process.

##### Max Unavailable

`.spec.strategy.rollingUpdate.maxUnavailable` is an optional field that specifies the maximum number of Pods that can be unavailable during the update process. The value can be an absolute number (for example, 5) or a percentage of desired Pods (for example, 10%). The absolute number is calculated from percentage by rounding down. The value cannot be 0 if `.spec.strategy.rollingUpdate.maxSurge` is 0. The default value is 25%.
- [Kubernetes Deployment Not Updating: Causes, Fixes & Insights](https://www.groundcover.com/learn/kubernetes/deployment-not-updating) — Conversely, a much more insidious scenario occurs when the rollout starts but hangs: a new ReplicaSet is created and begins scaling up. Still, it gets stuck because the newly created Pods fail their Readiness Probes or crash loop, preventing the Deployment from safely terminating the older Pods due to availability constraints.

## Common Reasons a Kubernetes Deployment Is Not Updating

Deployment failures generally fall into two categories: the update never starts, or it starts but hangs indefinitely. The following table breaks down the most frequent causes, categorized by the failure mode, and provides immediate diagnostic steps: [...] ### RollingUpdate (The Default)

The RollingUpdate strategy is the default and preferred method, designed for zero-downtime deployments. When a new Pod template is detected:

 The Deployment Controller creates a new ReplicaSet reflecting the updated configuration.
 The Deployment scales up the new ReplicaSet (creating new Pods) while simultaneously scaling down the old ReplicaSet (terminating old Pods).

This gradual, synchronized exchange continues until the new ReplicaSet reaches the desired replica count and the old one is scaled down to zero. Two parameters control the pacing:

 maxSurge: The maximum number of Pods allowed above the desired replica count during the update.
 maxUnavailable: The maximum number of Pods that can be unavailable during the update.

### Recreate [...] To effectively detect these situations, specialized visibility into the Kubernetes API events and the Deployment's rollout history is necessary.

## Troubleshooting Deployment Update Failures

When a Deployment update fails to complete, a methodical approach is required to isolate the cause, moving from application-specific issues to configuration errors and finally to cluster-wide constraints. The goal is always to identify the specific event or condition that blocks the new ReplicaSet from achieving its desired state.

### 1. Container Image Issues

Problems with the container image are the most common reason a rollout hangs, often resulting in new Pods repeatedly crashing or failing to start.
- [kubernetes - Why does my deployment terminate pods on ...](https://stackoverflow.com/questions/71108394/why-does-my-deployment-terminate-pods-on-deployment) — You can then see the rollout happening as it updates one pod at a time (terminating one pod from the old set, and bringing it up on the new set), since you specified 0 maxUnavailable, it won't terminate more than it's bringing up in the new replica set.
- [Decoding the pod termination lifecycle in Kubernetes: a comprehensive guide | CNCF](https://www.cncf.io/blog/2024/12/19/decoding-the-pod-termination-lifecycle-in-kubernetes-a-comprehensive-guide) — Pods stuck in Terminating state: Sometimes, pods can get stuck in the Terminating state due to various reasons like storage issues, finalizers stuck in deletion, or network issues.
 Pod Disruption Budgets: If you have set a Pod Disruption Budget (PDB) which limits the number of pods of a replicated application that are down simultaneously from voluntary disruptions, it can prevent voluntary termination of pods.

Practical troubleshooting tips and solutions: [...] Practical troubleshooting tips and solutions:

 Pods stuck in Terminating state: For pods stuck in the Terminating state, you can force delete the pod with kubectl delete pod  –grace-period=0 –force. However, this should be a last resort as it can cause data loss. It’s better to identify the root cause by checking the pod description (kubectl describe pod ) and looking for any errors.
 Pod Disruption Budgets: If you have a PDB that’s preventing pod termination, you may need to reconsider your PDB settings. If necessary, you can delete the PDB, but be aware that this may impact the availability of your application. Always consider the implications and plan downtime accordingly.

## Conclusion [...] Scaling Down/ Deleted : When a StatefulSet is scaled down or commissioned to be destroyed, Kubernetes will terminate the Pods in reverse order, starting from the highest to the lowest, ensuring that the state is maintained. For example, if you have pods named web-0, web-1, web-2, and scale down, web-2 would be deleted first, then web-1, and so on.