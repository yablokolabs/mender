# Root cause: Checkout pods stuck in Terminating state during rolling update

Service `checkout` in namespace `shop`.

## Root cause
The checkout application does not handle SIGTERM signals, causing containers to not exit during pod termination, which leaves pods stuck in Terminating state beyond the grace period and blocks the rolling update.

## Mechanism
1. A rolling update triggers creation of a new ReplicaSet and termination of old pods. 2. The kubelet sends SIGTERM to the checkout container (PID 1) and waits for terminationGracePeriodSeconds (30s). 3. The Python HTTP server (ThreadingHTTPServer.serve_forever) does not install a signal handler for SIGTERM, so the process does not exit gracefully. 4. After 30s, the kubelet should send SIGKILL, but the container runtime (containerd) fails to stop the container, leaving it in Running state. 5. The pod remains in Terminating state indefinitely, preventing the old ReplicaSet from scaling down. 6. The deployment controller creates additional ReplicaSets, but the old ones never fully terminate, resulting in multiple ReplicaSets with pods stuck in Terminating.

Confidence: 0.70 · Labels: probe_config

## Evidence relied on
- Status: Terminating (lasts <invalid>) ... State: Running
- terminationGracePeriod: 30s
- server.serve_forever()
- Created pod: checkout-7cd7468b7c-t8r9b ... Killing pod/checkout-7dd9ffb99d-cpprv

## Tavily sources
Queries: Kubernetes pods stuck Terminating state Ready true rolling update ReplicaSet; liveness probe termination grace period pod stuck terminating Kubernetes; ReplicaSet rolling update pod cleanup stuck terminating finalizers
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
 The issue / bug is, that there is no way to delete those pods via kubectl. I was able to remove the deployment and replica-set, but the pods still waited there "Terminating". [...] Skip to content   
 
 

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

Labels [...] Reactions are currently unavailable

## Activity

Sign up for free to join this conversation on GitHub. Already have an account? Sign in to comment

## Metadata

## Metadata

No one assigned

### Labels

kind/bugCategorizes issue or PR as related to a bug.Categorizes issue or PR as related to a bug.sig/api-machineryCategorizes an issue or PR as relevant to SIG API Machinery.Categorizes an issue or PR as relevant to SIG API Machinery.

No type

No projects

No milestone

None yet

No branches or pull requests

## Issue actions

You can’t perform that action at this time.
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

However, for the Event Consumer, it appeared that the old Replica Set had been terminated even though the new one was in CrashLoopBackOff! [...] ### Configuration

After some investigation, we discovered that it wasn’t a faulty readiness check that led to the bad behavior of our deployment. The Readiness Probe actually had worked as expected, and never returned true. From Kubernetes perspective, the new Replica Set had never become ready.

What had happened was a bit more subtle. Let’s look at part of our Events Consumer Deployment configuration. We use Helm charts and templates, and some configuration values were shared between our RPC Server and Events Consumer deployments. It would resolve to the following:

```
spec:  revisionHistoryLimit: 1  replicas: 1  strategy:  type: RollingUpdate  rollingUpdate:  maxUnavailable: 1  maxSurge: 100%template:  spec:  terminationGracePeriodSeconds: 400
```
- [How to Debug a Stuck Kubernetes Rollout with a Hands-On Lab](https://www.freecodecamp.org/news/how-to-debug-a-stuck-kubernetes-rollout-with-a-hands-on-lab) — Exactly two application Pods should remain, both owned by the current ReplicaSet, Ready, and not terminating. Their UIDs should be the ready Service endpoints, and the HTTP samples should return v2 from those Pod names.

In the original experiment, recovery reused the existing healthy ReplicaSet and the same two Pods. Their template already matched the restored configuration. The failed ReplicaSet scaled to zero.

Revision annotations changed even though those healthy Pods remained. These values are from the recorded run:

| Case | Before failure | Failed revision | After recovery |
 ---  --- |
| Image | 2 | 3 | 4 |
| Readiness | 4 | 5 | 6 |
| Scheduling | 6 | 7 | 8 |

Your numbers can differ. Restore the known healthy specification rather than relying on these example revision numbers. [...] | Control | Revision | Updated | Ready | Available | Correct HTTP responses |
 ---  ---  --- |
| v1 | 1 | 2 | 2 | 2 | 10/10 |
| v2 | 2 | 2 | 2 | 2 | 10/10 |

For example, the decoded response body of one recorded v2 request was:

```
{"version": "v2", "pod": "rollout-demo-5b4b45f68f-qrntz"} 
```

Your Pod names will differ. Check your current state:

```
k get deployment rollout-demo -o json k get pods -l app=rollout-demo -o wide 
```

Before continuing, wait until exactly two application Pods remain, both Ready and neither terminating. The Deployment should have two updated, ready, and available replicas, with `status.observedGeneration` matching `metadata.generation`. [...] With these rollout settings, the controller can add one replacement Pod. It waits for replacement availability before reducing the two healthy old replicas. A new Pod must remain Ready for five seconds to count as available. The progress deadline is 180 seconds.

`maxUnavailable: 0` constrains this rollout. It doesn't protect the old Pods from unrelated failures. Terminating Pods can also remain visible beyond the active replica counts. These settings are teaching choices, not a production availability guarantee.

The recorded controls each completed successfully and returned ten correct Service responses. This table is derived from the two Deployment snapshots:
- [Pods stuck in Terminating when PVC is attached during graceful node evacuations · Issue #3370 · bottlerocket-os/bottlerocket · GitHub](https://github.com/bottlerocket-os/bottlerocket/issues/3370) — The Fix: Rolling back to 1.14.1..

At this point, I had a suspicion that there was something wrong with the AMI update so we rolled that back. Since rolling the update back, we have not seen a single failure. We noted that the pods stuck in `Terminating` state were on nodes that were actively being drained for replacement.

Our suspicion was that #3230 was somehow biting us ... but after reading through this, it seems that `1.14.2+` is supposed to contain the fix for a problem (that we weren't seeing on 1.14.1). So we are unclear at this point what the root cause is or why we're seeing this problem.

How to reproduce the problem:

I haven't fully tested the instructions - but this is roughly how to replicate the environment we saw the issues in. [...] Failure 1: EFS Backed PVC

In one of our development workloads, an engineer reached out to me for help because all of his pods were stuck in the `Terminating` state, but they were not being terminated. After troubleshooting a bit, we manually deleted the pods with `kubectl delete pod --force`, which caused new pods to come up. We let this problem go initially as a strange one-off situation.

Failure 2: EBS backed PVC

A day after the first problem above, we had two failures on the same service across different clusters. We were alerted to pods using EBS-backed PVCS that were stuck in the `Terminating` state again. Again, after much troubleshooting, we solved the problem by forcefully deleting the pods with `kubectl delete --force`.

The Fix: Rolling back to 1.14.1..
- [Kubernetes Pods Stuck in Terminating: A Resolution Guide](https://kodekloud.com/blog/kubernetes-pods-stuck-in-terminating-a-resolution-guide) — ## Prevent Future Occurrences

Below are some preventative measures you can take to avoid having kubernetes pods stuck in terminating states:

 Implement Pod hooks and preStop for graceful shutdown. You can use these hooks to perform some cleanup or finalization tasks, such as closing connections, flushing buffers, or sending notifications. This will help the Pod to shut down gracefully and avoid errors or data loss.
 Add liveness/readiness probes to prevent recreating loops. Use these probes to detect and recover from failures, such as deadlocks, crashes, or network issues. This will prevent the Pod from getting stuck in a loop of recreating and terminating.

Learn more about readiness probe in this article:

Kubernetes Readiness Probe: A Simple Guide with Examples [...] ```
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
``` [...] ```
apiVersion: v1 kind: Pod metadata: name: prestop-demo spec: terminationGracePeriodSeconds: 3600 containers: - name: prestop-demo image: nginx:latest ports: - containerPort: 80 lifecycle: preStop: exec: command: - /bin/sh - -c - sleep 3600 
```

Create a Pod by running the following command:

```
kubectl create -f deployment.yaml
```

Verify the Pod has been created using the following command:

```
kubectl get pods
```

After the Pod creation process is complete, delete it by running the following command:

```
kubectl delete pod prestop-demo
```
- [liveness/readiness probe is executed and failed while pod is terminated · Issue #52817 · kubernetes/kubernetes · GitHub](https://github.com/kubernetes/kubernetes/issues/52817) — How to reproduce it (as minimally and precisely as possible):  
 execute `kubectl delete pod nginx-A1` to delete pod, so status of the nginx-podA1 is changed to `Terminating`, right after that it seems Liveness and Readiness Probe is executed and failed, but only once.  
 Nginx reverse proxy is running in the pod. so I just use `httpGet`method for liveness and readiness

Here is my Deployment config.

```
... spec terminationGracePeriodSeconds 60... livenessProbe httpGet path/healthz port 8080 initialDelaySeconds 15 timeoutSeconds 3 readinessProbe httpGet path/healthz port 8080 initialDelaySeconds 15 timeoutSeconds 3
```

Here is Events log by `kubectl describe pod nginx-A1` [...] #98571

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
 liveness/readiness probe fails while pod is terminated. Also it happened only once during the pod termination. The issue started happening after upgrading version to v1.7 from v1.6.X [...] ## Metadata

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
- [Kubernetes Pods Stuck in Terminating: A Resolution Guide - DEV Community](https://dev.to/imjoseangel/kubernetes-pods-stuck-in-terminating-a-resolution-guide-2jh3) — When Kubelet knows that a Pod should evict, it marks the Pod state as `Terminating` and stops sending traffic to it. Then, it executes the `preStop` lifecycle hook (when available). It sends the `SIGTERM` to the Main process (pid 1) within each container and waits for their termination. If the applications inside the containers are properly prepared, they will start a graceful shutdown. The duration should not be more than the specified in the spec.terminationGracePeriodSeconds which is 30 seconds by default.

If the application has not completed the shutdown properly, the Kubelet gives a grace period until removing the Pod IP and killing the container by sending a `SIGKILL`. At this point, Kubernetes removes the Pod from the API server.

## Why a Pod can hang on `Terminating` state [...] From the Kubernetes Documentation:

> If a `PreStop` hook hangs during execution, the Pod's phase will be `Terminating` and remain there until the Pod is killed after its `terminationGracePeriodSeconds` expires.

For instance. This configuration:

```
spec: terminationGracePeriodSeconds: 3600 containers: - lifecycle: preStop: exec: command: -/bin/sh - -c - sleep 3600
```

Will keep the Pod in the `Terminating` state for 1 hour.

It is essential to handle the `SIGTERM` correctly and ensure that the application terminates gracefully when the kubelet sends the `SIGTERM` to the container.

## Remove Finalizers

Determine if the cause of the `Terminating` state for a Pod, Namespace, or PVC is a finalizer. A Finalizer example to protect PVCs from deletion is the `kubernetes.io/pvc-protection`. [...] Review the status of your Pods with:

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
- [Pods stuck in Terminating status. When Kubernetes pods get stuck in the… | by Harold Finch | Medium](https://medium.com/@haroldfinch01/pods-stuck-in-terminating-status-083168c6b7e8) — > Common Causes

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

Join Medium for free to get updates from this writer. [...] 2. Force Delete the Pod

 If the pod cannot be deleted gracefully, you can force delete it.

```
kubectl delete pod <pod-name> --grace-period=0 --force delete< ->
--grace-period=0 --force
```

3. Remove Finalizers

 If finalizers are preventing deletion, remove them manually.

```
kubectl patch pod <pod-name> -p '{"metadata":{"finalizers":null}}' "metadata" "finalizers"
```

4. Check for Stuck Volumes

 Ensure that volumes are properly detached.

```
kubectl get pv,pvc | grep <pod-name> get
```

5. Node Issues

 If the node itself has issues, you may need to restart the kubelet on that node or drain and cordon the node.
- [Decoding the pod termination lifecycle in Kubernetes: a comprehensive guide | CNCF](https://www.cncf.io/blog/2024/12/19/decoding-the-pod-termination-lifecycle-in-kubernetes-a-comprehensive-guide) — Practical troubleshooting tips and solutions:

 Pods stuck in Terminating state: For pods stuck in the Terminating state, you can force delete the pod with kubectl delete pod  –grace-period=0 –force. However, this should be a last resort as it can cause data loss. It’s better to identify the root cause by checking the pod description (kubectl describe pod ) and looking for any errors.
 Pod Disruption Budgets: If you have a PDB that’s preventing pod termination, you may need to reconsider your PDB settings. If necessary, you can delete the PDB, but be aware that this may impact the availability of your application. Always consider the implications and plan downtime accordingly.

## Conclusion [...] When a pod is asked to terminate, Kubernetes updates the object state and marks it as “Terminating”.

Kubernetes also sends a SIGTERM signal to the main process in each container of the pod.

The SIGTERM signal is an indication that the processes in the containers should stop. The processes have a grace period (default is 30 seconds) to shut down properly.

If a process is still running after the grace period, Kubernetes sends a SIGKILL signal to force the process to terminate.

To gracefully terminate the pod you can either add terminationGracePeriodSeconds to your spec or add  kubectl delete pods  –grace-period=

The below contains a time series graph for graceful termination:

The “preStop” hook is executed just before a container is terminated. [...] NOTE: Remember that Kubernetes will run the preStop hook, then wait for the grace period (default 30 seconds) before forcibly terminating the container. If your preStop hook takes longer than the grace period, Kubernetes will interrupt it.

The above image explains it.

## Factors Influencing Pod Termination

1. How resource constraints impact pod termination decisions.
- [rollingUpdate strategy instantly killed all PODs in replicaSet](https://github.com/kubernetes/kubernetes/issues/70570) — Right now I was able to reproduce this only with replicaSets of 2 replicas. So, both PODs in replicaset is being terminated resulting in application downtime. What you expected to happen: Kubernetes should have terminate one POD, launch new replicaSet, wait at least one POD of new replicaSet is ready and then terminate another POD. How to reproduce it (as minimally and precisely as possible
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
- [Diagnose Kubernetes Pod Stuck in Terminating State Due to Finalizer Issues](https://oneuptime.com/blog/post/2026-02-09-pod-stuck-terminating-finalizer/view) — `// Example operator code with proper finalizer handling
func (r MyReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
instance := &myv1.MyResource{}
err := r.Get(ctx, req.NamespacedName, instance)
if err != nil {
return ctrl.Result{}, client.IgnoreNotFound(err)
}
finalizerName := "myoperator.example.com/cleanup"
// Handle deletion
if !instance.ObjectMeta.DeletionTimestamp.IsZero() {
if containsString(instance.ObjectMeta.Finalizers, finalizerName) {
// Perform cleanup with timeout
ctx, cancel := context.WithTimeout(ctx, 30time.Second)
defer cancel()
if err := r.cleanupExternalResources(ctx, instance); err != nil {
// Leave the finalizer in place and retry cleanup later
return ctrl.Result{RequeueAfter: 5  time.Second}, err
}
// Remove finalizer [...] }
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
}` [...] ## Implementing Finalizer Timeouts

Add timeouts to finalizer cleanup to prevent indefinite blocking.

`apiVersion: v1
kind: ConfigMap
metadata:
name: operator-config
namespace: operators
data:
finalizer-timeout: "60s"
max-cleanup-retries: "3"`

The operator should respect these timeouts and remove finalizers even if cleanup fails after max retries, logging errors for manual investigation.

## Monitoring Stuck Finalizers

Create alerts for resources stuck with finalizers to catch issues quickly.
- [Kubernetes Deployment Rolling Update](https://stackoverflow.com/questions/70321665/kubernetes-deployment-rolling-update) — My problem is that during updates,all the older version pods are stuck at "Terminating" status while all the new pods are created. During
- [Kubernetes pod stuck Terminating: finalizers, grace periods, and force delete](https://www.netdata.cloud/guides/kubernetes/kubernetes-pod-stuck-terminating) — 1. Confirm the delete reached the API server. Verify `deletionTimestamp` is set. If it is missing, the delete request may not have reached the API server.
2. Inspect finalizers. If `metadata.finalizers` is not empty, identify which controller owns the finalizer. A missing or crashed controller never removes the finalizer. Patching it manually allows the API server to complete deletion, but you must accept that whatever cleanup the finalizer was protecting is skipped. [...] # Check deletion timestamp and configured grace period # Check deletion timestamp and configured grace period # Check deletion timestamp and configured grace periodkubectl get pod  -o jsonpath='deletionTimestamp={.metadata.deletionTimestamp}{"\n"}gracePeriod={.spec.terminationGracePeriodSeconds}{"\n"}' kubectl get pod  -o jsonpath='deletionTimestamp={.metadata.deletionTimestamp}{"\n"}gracePeriod={.spec.terminationGracePeriodSeconds}{"\n"}' ='deletionTimestamp={.metadata.deletionTimestamp}{"\n"}gracePeriod={.spec.terminationGracePeriodSeconds}{"\n"}'   # Inspect finalizers blocking deletion # Inspect finalizers blocking deletion # Inspect finalizers blocking deletionkubectl get pod  -o jsonpath='{.metadata.finalizers}' kubectl get pod  -o jsonpath='{.metadata.finalizers}' [...] kubectl get pod  -o jsonpath='{.metadata.finalizers}' ='{.metadata.finalizers}'   # Check if containers are still running on the node # Check if containers are still running on the node # Check if containers are still running on the nodecrictl ps -a | grep  crictl ps -a | grep    # List volume attachments for the node # List volume attachments for the node # List volume attachments for the nodekubectl get volumeattachment -o json | jq '.items[] | select(.spec.nodeName=="") | {name: .metadata.name, attached: .status.attached}' kubectl get volumeattachment -o json | jq '.items[] | select(.spec.nodeName=="") | {name: .metadata.name, attached: .status.attached}' '.items[] | select(.spec.nodeName=="") | {name: .metadata.name, attached: .status.attached}'   # Check kubelet logs for unmount or