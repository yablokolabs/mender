# Root cause: Checkout pod stuck in Terminating state during rollout due to missing SIGTERM handling

Service `checkout` in namespace `shop`.

## Root cause
The checkout application does not handle SIGTERM signals for graceful shutdown, causing pods to remain in Terminating state for the full 30s termination grace period during rollouts [1][9][10].

## Mechanism
1. A rollout restart (kubectl rollout restart) triggered a new ReplicaSet (58bbc9b99d) and began terminating the old ReplicaSet (58b467895b) [EVENTS]. 2. The kubelet sent SIGTERM to the old pod (checkout-58b467895b-pmjtm) to initiate graceful shutdown [EVENTS: Killing at 25s]. 3. The application (Python ThreadingHTTPServer in service.py) lacks a SIGTERM handler, so the process does not exit promptly and continues serving health checks [LOGS: 200 responses until 17:34:58]. 4. The pod stays in Terminating state with container still Running, consuming the 30s terminationGracePeriodSeconds [DESCRIBE: Termination Grace Period: 30s, Status: Terminating (lasts <invalid>)]. 5. Only after the grace period expires will the kubelet send SIGKILL to force termination [1][4].

Confidence: 0.80 · Labels: sigterm_unhandled, termination_delay, graceful_shutdown_missing, rollout_stuck

## Evidence relied on
- Status: Terminating (lasts <invalid>)
- Termination Grace Period: 30s
- Killing pod/checkout-58b467895b-pmjtm Stopping container checkout
- GET /healthz HTTP/1.1 200 - (continuing during termination)
- [1] If a PreStop hook hangs... Pod's phase will be Terminating... until terminationGracePeriodSeconds expires
- [9] PID 1 ... both SIGTERM and SIGKILL will be ignored by it
- [10] Server in the container does not respond to SIGINT/SIGTERM — signal handler needed

## Tavily sources
Queries: Kubernetes pod stuck in Terminating state beyond terminationGracePeriodSeconds during rolling deployment replica set scale down; containerd container not responding to SIGTERM pod stuck terminating Kubernetes 1.28; ReplicaSet scaling down old pods stuck in Terminating state SuccessfulDelete Killing events
- [Kubernetes Pods Stuck in Terminating: A Resolution Guide - DEV Community](https://dev.to/imjoseangel/kubernetes-pods-stuck-in-terminating-a-resolution-guide-2jh3) — From the Kubernetes Documentation:

> If a `PreStop` hook hangs during execution, the Pod's phase will be `Terminating` and remain there until the Pod is killed after its `terminationGracePeriodSeconds` expires.

For instance. This configuration:

```
spec: terminationGracePeriodSeconds: 3600 containers: - lifecycle: preStop: exec: command: -/bin/sh - -c - sleep 3600
```

Will keep the Pod in the `Terminating` state for 1 hour.

It is essential to handle the `SIGTERM` correctly and ensure that the application terminates gracefully when the kubelet sends the `SIGTERM` to the container.

## Remove Finalizers

Determine if the cause of the `Terminating` state for a Pod, Namespace, or PVC is a finalizer. A Finalizer example to protect PVCs from deletion is the `kubernetes.io/pvc-protection`. [...] When Kubelet knows that a Pod should evict, it marks the Pod state as `Terminating` and stops sending traffic to it. Then, it executes the `preStop` lifecycle hook (when available). It sends the `SIGTERM` to the Main process (pid 1) within each container and waits for their termination. If the applications inside the containers are properly prepared, they will start a graceful shutdown. The duration should not be more than the specified in the spec.terminationGracePeriodSeconds which is 30 seconds by default.

If the application has not completed the shutdown properly, the Kubelet gives a grace period until removing the Pod IP and killing the container by sending a `SIGKILL`. At this point, Kubernetes removes the Pod from the API server.

## Why a Pod can hang on `Terminating` state [...] ```
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

From the Kubernetes Documentation:
- [Gracefully Terminating Pods in Kubernetes: Handling SIGTERM](https://jaadds.medium.com/gracefully-terminating-pods-in-kubernetes-handling-sigterm-fb0d60c7e983) — Pods linger in the Terminating state: If pods take about 30 seconds (which is the default terminationGracePeriodSeconds ) to delete upon issuing
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
- [Hi,

When Kubernetes scale down or if we stopped/ terminated a POD, how can we g . . . - Kubernetes-Slack Discussions - KodeKloud - DevOps Learning Community](https://kodekloud.com/community/t/hi-when-kubernetes-scale-down-or-if-we-stopped-terminated-a-pod-how-can-we-g/68088) — • kubernetes waits graceperiod (30s by default) and if the processes in the pod don’t finish, to the end of this period it kills them. You can manage this time using `terminationGracePeriodSeconds` option.  
And of course if the pod was down suddenly (because power failure of the node for example), no of the above cannot be applied. [...] `terminationGracePeriodSeconds`

Powered by Discourse, best viewed with JavaScript enabled
- [Deployments | Kubernetes](https://kubernetes.io/docs/concepts/workloads/controllers/deployment) — #### Note:

Kubernetes doesn't count terminating Pods when calculating the number of `availableReplicas`, which must be between `replicas - maxUnavailable` and `replicas + maxSurge`. As a result, you might notice that there are more Pods than expected during a rollout, and that the total resources consumed by the Deployment is more than `replicas + maxSurge` until the `terminationGracePeriodSeconds` of the terminating Pods expires.

### Rollover (aka multiple updates in-flight) [...] Pods that become terminating due to deletion or scale down may take a long time to terminate, and may consume additional resources during that period. As a result, the total number of all pods can temporarily exceed `.spec.replicas`. Terminating pods can be tracked using the `.status.terminatingReplicas` field of the Deployment.

### Revision History Limit

A Deployment's revision history is stored in the ReplicaSets it controls. [...] The output is similar to this:

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
- [Pod stuck terminating due to zombie container lingering](https://github.com/containerd/containerd/issues/11133) — containerd should not let this dead container linger as there is no process for it anymore, so that kubelet can reap the pod and let it
- [Container Runtimes | Kubernetes](https://kubernetes.io/docs/setup/production-environment/container-runtimes) — If you experience container crash loops after the initial cluster installation or after installing a CNI, the containerd configuration provided with the package might contain incompatible configuration parameters. Consider resetting the containerd configuration with `containerd config default > /etc/containerd/config.toml` as specified in getting-started.md and then set the configuration parameters specified above accordingly.

If you apply this change, make sure to restart containerd:

```
sudo systemctl restart containerd sudo systemctl restart containerd 
```

In Kubernetes v1.28, you can enable automatic detection of the cgroup driver as an alpha feature. See systemd cgroup driver for more details.

#### Overriding the sandbox (pause) image
- [SIGTERM is not passed through lnd when using Docker ...](https://github.com/lightningnetwork/lnd/issues/4994) — Run lnd in a dockerized environment in kubernetes. run kubectl delete pod lnd. see the container as 'terminating' yet lnd continue as normal
- [Kubernetes: containers, and the “lost” SIGTERM signals](https://itnext.io/kubernetes-containers-and-the-lost-sigterm-signals-40007f35759a) — So here’s what do we have:

   a process `/bin/sh` with PID 1
   the PID 1 is a special process
   checking PID 1 shows us that it “recognizes” the only `SIGHUP` and `SIGCHLD` signals
   and both `SIGTERM` and `SIGKILL` will be ignored by it

But then how does the container stop?

## Docker stop and Linux signals

The process of stopping a container in Docker (or Containerd) is no different than in Kubernetes, because in fact `kubelet` just passes commands to the container runtime. In AWS Kubernetes, this is now `containerd`.

But for the sake of simplicity, let’s do it locally with Docker.

So, we start the container from the same Docker image that we tested in Kubernetes:

$ docker run --name test-app 492148.dkr.ecr.us-east-1.amazonaws.com/fastapi-app-test:entry-2 [...] strace: Process 1 attached

wait4(-1,
Run `kubect delete pod` - but add `time` to measure the time it takes to execute the command:

$ time kk delete pod fastapi-app-6cb6b46c4b-9pd7r

pod "fastapi-app-6cb6b46c4b-9pd7r" deleted

real 0m32.222s
32 seconds…

What’s in the `strace`?

root@fastapi-app-6cb6b46c4b-9pd7r:/app# strace -p 1

strace: Process 1 attached

wait4(-1, 0x7ffe7a390a3c, 0, NULL) = ? ERESTARTSYS (To be restarted if SA_RESTART is set)

--- SIGTERM {si_signo=SIGTERM, si_code=SI_USER, si_pid=0, si_uid=0} ---

wait4(-1, <unfinished ...>) = ?

command terminated with exit code 137
So, what was going on here? [...] 1.   The `kubelet` sent a `SIGTERM` signal to the process with PID 1 - _SIGTERM {si\_signo=SIGTERM}_ - and the PID 1 would have to pass this signal to its children, stop them, and then terminate itself
2.   but the process did not stopped — and `kubelet` waited the default 30 seconds to complete the process' work correctly - see Pod phase
3.   then `kubelet` killed the container, and the process ended with "terminated with exit code 137"

Usually, the 137 exit code is about OutOfMemory Killer, when a process is killed with `SIGKILL`, but in our case there was no OOMKill - just a `SIGKILL` sent because the processes in the Pod did not terminated on time.

Well, where did our `SIGTERM` go then?
- [Server in the container does not respond to SIGINT/SIGTERM](https://github.com/rustdesk/rustdesk-server/issues/36) — The solution I would like to see is a signal handler to be added for those signals, which would cause the process to cleanly exit. I'm concerned
- [Pods getting stuck into "Terminating" state on deletion after ...](https://github.com/rancher/rancher/issues/38270) — From the nginx Deployment delete the older pods, NOT the one's created after scaling it up. Pods will get stuck into Terminating state. pods-
- [ReplicaSet | Kubernetes](https://kubernetes.io/docs/concepts/workloads/controllers/replicaset) — Pods that become terminating due to deletion or scale down may take a long time to terminate, and may consume additional resources during that period. As a result, the total number of all pods can temporarily exceed `.spec.replicas`. Terminating pods can be tracked using the `.status.terminatingReplicas` field of the ReplicaSet.

### Isolating Pods from a ReplicaSet

You can remove Pods from a ReplicaSet by changing their labels. This technique may be used to remove Pods from service for debugging, data recovery, etc. Pods that are removed in this way will be replaced automatically ( assuming that the number of replicas is not also changed).

### Scaling a ReplicaSet [...] Once the original is deleted, you can create a new ReplicaSet to replace it. As long as the old and new `.spec.selector` are the same, then the new one will adopt the old Pods. However, it will not make any effort to make existing Pods match a new, different pod template. To update Pods to a new spec in a controlled way, use a Deployment, as ReplicaSets do not support a rolling update directly.

### Terminating Pods

Feature state: Beta since Kubernetes v1.35; enabled by default

You can enable this feature by setting the `DeploymentReplicaSetTerminatingReplicas` feature gate on the API server and on the kube-controller-manager [...] ### Scaling a ReplicaSet

A ReplicaSet can be easily scaled up or down by simply updating the `.spec.replicas` field. The ReplicaSet controller ensures that a desired number of Pods with a matching label selector are available and operational.

When scaling down, the ReplicaSet controller chooses which pods to delete by sorting the available pods to prioritize scaling down pods based on the following general algorithm:
- [Pods getting stuck in error state after scale down to 0](https://www.reddit.com/r/kubernetes/comments/1nk8nga/pods_getting_stuck_in_error_state_after_scale) — You either need to manually delete them or wait for the garbage collector to delete them. By default terminated-pod-gc-threshold is set to 1250
- [Unable to delete pod in terminating state. : r/kubernetes](https://www.reddit.com/r/kubernetes/comments/1eb4lhc/unable_to_delete_pod_in_terminating_state) — I have deployed a deployment with replicaset of 1 using helm. There is a controller already listening on pod events and it added some
- [How to Debug Pods Stuck in Terminating State and Force Delete Them](https://oneuptime.com/blog/post/2026-02-09-debug-pods-terminating-force-delete/view) — `kubectl scale statefulset my-statefulset --replicas=0
# Or:
kubectl delete statefulset my-statefulset --cascade=orphan
kubectl delete pod stuck-pod --grace-period=0 --force`

## Namespace Stuck in Terminating

Sometimes entire namespaces get stuck terminating, blocking all pod deletions.

Check namespace status:

`kubectl get namespace stuck-namespace`

Output:

`NAME STATUS AGE
stuck-namespace Terminating 30m`

Check namespace finalizers:

`kubectl get namespace stuck-namespace -o jsonpath='{.spec.finalizers}'`

Remove finalizers:

`kubectl get namespace stuck-namespace -o json | \
jq '.spec.finalizers = []' | \
kubectl replace --raw "/api/v1/namespaces/stuck-namespace/finalize" -f -`

Or edit directly:

`kubectl edit namespace stuck-namespace
# Remove finalizers from spec.finalizers` [...] Script to find old terminating pods:

`#!/bin/bash
# find-stuck-terminating.sh
THRESHOLD=300 # 5 minutes in seconds
CURRENT_TIME=$(date +%s)
kubectl get pods -A -o json | jq -r '
.items[] |
select(.metadata.deletionTimestamp != null) |
{
namespace: .metadata.namespace,
name: .metadata.name,
deletionTimestamp: .metadata.deletionTimestamp,
nodeName: .spec.nodeName
} | @json
' | while read -r pod_json; do
DELETION_TIME=$(echo "$pod_json" | jq -r '.deletionTimestamp' | date -f - +%s)
AGE=$((CURRENT_TIME - DELETION_TIME))
if [ $AGE -gt $THRESHOLD ]; then
echo "Stuck pod found:"
echo "$pod_json" | jq .
fi
done`

## Recovering from Force Deletions

After force deleting pods, verify the cleanup:

Check if pod is gone:

`kubectl get pod stuck-pod -n my-namespace` [...] ## Force Deleting Pods

When all else fails, force delete the pod. This bypasses normal termination.

Standard force delete:

`kubectl delete pod stuck-pod --grace-period=0 --force`

This removes the pod object from the API server without waiting for confirmation that the pod's processes have stopped. The processes may continue running on the node until the kubelet or container runtime finishes cleanup.

If the pod still does not delete, remove it from API server:

`kubectl patch pod stuck-pod -p '{"metadata":{"finalizers":null}}' && \
kubectl delete pod stuck-pod --grace-period=0 --force`

For StatefulSet pods, deletion might recreate the pod. If you do not want the controller to recreate it, scale down or delete the StatefulSet first: