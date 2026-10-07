# Root cause: Checkout pods stuck in Terminating state past grace period on control plane node

Service `checkout` in namespace `shop`.

## Root cause
A hanging preStop hook (or equivalent graceful shutdown blocker) prevents pod termination completion, causing pods to remain in Terminating state with containers still Running well beyond the 30s terminationGracePeriodSeconds [15]

## Mechanism
1. Rolling deployment creates new ReplicaSet (f9995f9f) and marks old ReplicaSet (7c5bdcc9d5) pods for deletion
2. Kubelet sends SIGTERM to containers and starts 30s grace period (default terminationGracePeriodSeconds)
3. Application (service.py) lacks SIGTERM handling; any preStop hook (possibly injected by mutating webhook) or graceful shutdown hangs [15]
4. Grace period expires but kubelet fails to send SIGKILL or container runtime doesn't terminate process
5. Pods show 'Terminating (lasts <invalid>)' with container State: Running for 2+ minutes, no termination events recorded

Confidence: 0.65 · Labels: termination_stuck, grace_period_exceeded, sigterm_unhandled, preStop_hook, control_plane_kubelet

## Evidence relied on
- Pod describe: 'Status: Terminating (lasts <invalid>)' and 'State: Running' for containers after 2m+
- Logs: health checks on old pods stop at 17:15:16, new pods start at 17:15:25 indicating rollout
- Search result [15]: 'If a PreStop hook hangs during execution, the Pod's phase will be Terminating and remain there until the Pod is killed after its terminationGracePeriodSeconds expires'
- Search result [15]: 'It is essential to handle the SIGTERM correctly and ensure that the application terminates gracefully'
- Deployment manifest: no preStop hook visible, but behavior matches hanging hook; terminationGracePeriodSeconds=30s default

## Tavily sources
Queries: Kubernetes pod stuck terminating "lasts <invalid>" no events; pod termination stuck finalizer preStop hook kubelet containerd; kubelet pod terminating state containers running no events graceful termination timeout
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

## Conclusion [...] ```
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
- [Kubernetes Pods Stuck in Terminating: A Resolution Guide](https://kodekloud.com/blog/kubernetes-pods-stuck-in-terminating-a-resolution-guide) — #### Highlights

 The Root Cause: Pods usually stick in the "Terminating" state due to unfulfilled Finalizers, failed PreStop hooks, or strict StatefulSet ordering.
 The Fix for Finalizers: Manually edit the Pod metadata to remove the blocking finalizer key.
 The Fix for PreStop Hooks: Use the `--force` and `--grace-period=0` flags to bypass the graceful shutdown timer.
 The Fix for StatefulSets: Change the podManagementPolicy from OrderedReady to Parallel to speed up deletion.

If you are a DevOps engineer who works with Kubernetes, you might have encountered the frustrating issue where kubernetes pods stuck in terminating state refuse to go away. This can be problematic, especially if you need to free up resources or deploy new versions of your applications. [...] ```
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
- [Node down - pods shown still as Running for hours, others stuck in Terminating - General Discussions - Discuss Kubernetes](https://discuss.kubernetes.io/t/node-down-pods-shown-still-as-running-for-hours-others-stuck-in-terminating/20669) — time="2022-07-19T09:26:26+01:00" level=debug msg="DesiredSet - No change(2) apps/v1, Kind=DaemonSet kube-system/svclb-traefik-adf18ba2 for svccontroller kube-system/traefik"
I0719 09:31:31.934393 6745 taint_manager.go:106] "NoExecuteTaintManager is deleting pod" pod="default/ubuntu-pod-with-csi"
I0719 09:31:31.934393 6745 taint_manager.go:106] "NoExecuteTaintManager is deleting pod" pod="dev/plain-alpine-container"
I0719 09:31:31.934407 6745 taint_manager.go:106] "NoExecuteTaintManager is deleting pod" pod="default/ubuntu-pod"
I0719 09:31:31.934859 6745 event.go:294] "Event occurred" object="default/ubuntu-pod-with-csi" kind="Pod" apiVersion="" type="Normal" reason="TaintManagerEviction" message="Marking for deletion Pod default/ubuntu-pod-with-csi" [...] You talk about Kubernetes 1.18 and 1.19.  
We run Kubernetes 1.23.

We have the same/related issue (also k3s v1.21.14) also on-prem.  
Sometimes nodes do fail and then all pods on that node stay in terminating state. While they are replaced on other nodes, it’s still not possible to connect to some services (example: kubeflow) until the terminating pods are deleted completly or the node that went down has recovered (and deletes the old pods by itself)  
It is mind boggling to me why that is, as the sole purpose of kubernetes is to make sure everything always is available.

I believe we actually found the source of our problem, and the right approach. I’ll document it here, before closing the issue, for the benefit of those who would stumble across the same. [...] `$ kubectl get nodes -o wide
NAME STATUS ROLES AGE VERSION INTERNAL-IP EXTERNAL-IP OS-IMAGE KERNEL-VERSION CONTAINER-RUNTIME
e09ctwe080b000102186 Ready <none> 31d v1.23.8+k3s2 10.101.35.11 <none> Alpine Linux v3.9 4.9.291-vsys-1.0 docker://18.9.1
e10ccwe080c000001127 Ready control-plane,master 53d v1.23.8+k3s2 172.31.0.143 <none> Alpine Linux v3.9 4.9.291-vsys-1.0 docker://18.9.1
e10ctwe080c000002458 NotReady <none> 31d v1.23.8+k3s2 10.101.115.39 <none> Alpine Linux v3.9 4.9.291-vsys-1.0 docker://18.9.1`

The log entries also seem to indicate that the Kubernetes has registered the node-down event, and it’s taking the respective actions. (e.g. the initial actions and the ones after the default eviction timeout of 5min)
- [Pods stuck in terminating state : r/kubernetes](https://www.reddit.com/r/kubernetes/comments/1q914gz/pods_stuck_in_terminating_state) — A common fix is to auto-delete pods that stay in Terminating too long, using a small script or controller. Also worth checking finalizers and
- [Troubleshoot pods and namespaces stuck in the Terminating state - Azure | Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/azure/azure-kubernetes/storage/pods-namespaces-terminating-state) — Ensure you have the following prerequisites:

`kubectl`
`namespaces/finalize`
`customresourcedefinitions`
`Windows`
`Standard`
`Legacy`
`<pod-name>`
`<namespace-name>`

## Troubleshoot a pod stuck in the Terminating state

### Step 1: Inspect the pod and its node

A pod shown as `Terminating` already has a deletion request in progress. Investigate what is preventing deletion from completing instead of repeating a normal delete request.

`Terminating`

Run the following command.

`kubectl get pod --all-namespaces --output wide
kubectl describe pod <pod-name> --namespace <namespace-name>
kubectl get pod <pod-name> --namespace <namespace-name> --output yaml --show-managed-fields` [...] Run the following commands.

`namespace="<namespace-name>"
kubectl get namespace "$namespace" --output json > "$namespace.json" &&
kubectl patch --local --filename "$namespace.json" --type=merge --patch '{"spec":{"finalizers":[]}}' --output json > "$namespace-finalize.json" &&
kubectl replace --raw "/api/v1/namespaces/${namespace}/finalize" -f "$namespace-finalize.json"`

Run the following commands. [...] Run the following command.

`kubectl patch <resource-type> <resource-name> --namespace <namespace-name> --type=json --patch='[{"op":"remove","path":"/metadata/finalizers"}]'`

When resource cleanup succeeds, the namespace controller removes its `kubernetes` finalizer. Other finalizers on the namespace can still prevent deletion.

`kubernetes`

### Step 4: Force-finalize the namespace only as a last resort

For a namespace still in `Terminating`, confirm the following before using the `finalize` subresource:

`Terminating`
`finalize`

Warning

Force-finalizing can delete the namespace while leaving resource objects in etcd. Don't use it to bypass discovery or listing errors.
- [Kubernetes Pods Stuck in Terminating: A Resolution Guide](https://kodekloud.com/blog/kubernetes-pods-stuck-in-terminating-a-resolution-guide) — The Pod has a preStop hook that takes too long to execute or fails. A preStop hook is a command or a script that runs inside the container before it is terminated. It is used to perform some graceful shutdown actions, like closing connections, flushing buffers, or sending notifications. However, if the preStop hook takes longer than the terminationGracePeriodSeconds (which defaults to 30 seconds), the kubelet will forcefully kill the container, and the Pod will remain in the terminating state. Similarly, if the preStop hook fails or returns a non-zero exit code, the Pod will not be deleted. [...] #### Highlights

 The Root Cause: Pods usually stick in the "Terminating" state due to unfulfilled Finalizers, failed PreStop hooks, or strict StatefulSet ordering.
 The Fix for Finalizers: Manually edit the Pod metadata to remove the blocking finalizer key.
 The Fix for PreStop Hooks: Use the `--force` and `--grace-period=0` flags to bypass the graceful shutdown timer.
 The Fix for StatefulSets: Change the podManagementPolicy from OrderedReady to Parallel to speed up deletion.

If you are a DevOps engineer who works with Kubernetes, you might have encountered the frustrating issue where kubernetes pods stuck in terminating state refuse to go away. This can be problematic, especially if you need to free up resources or deploy new versions of your applications. [...] ```
kubectl edit pod finalizer-demo -n default
```

This will open the Pod's YAML definition in your default editor. Find the finalizers field in the metadata section and delete the line that contains the finalizer name. Save and exit the editor. This will update the Pod's definition and trigger its deletion.

## Resolving Pod Stuck in Termination Due to PreStop Hook

Just like in the previous section, we shall use a simple example to demonstrate how to resolve the termination issue due to the preStop hook.

Create a YAML file named deployment.yaml with the following specs:
- [Kubernetes Pods Stuck in Terminating: A Resolution Guide - DEV Community](https://dev.to/imjoseangel/kubernetes-pods-stuck-in-terminating-a-resolution-guide-2jh3) — From the Kubernetes Documentation:

> If a `PreStop` hook hangs during execution, the Pod's phase will be `Terminating` and remain there until the Pod is killed after its `terminationGracePeriodSeconds` expires.

For instance. This configuration:

```
spec: terminationGracePeriodSeconds: 3600 containers: - lifecycle: preStop: exec: command: -/bin/sh - -c - sleep 3600
```

Will keep the Pod in the `Terminating` state for 1 hour.

It is essential to handle the `SIGTERM` correctly and ensure that the application terminates gracefully when the kubelet sends the `SIGTERM` to the container.

## Remove Finalizers

Determine if the cause of the `Terminating` state for a Pod, Namespace, or PVC is a finalizer. A Finalizer example to protect PVCs from deletion is the `kubernetes.io/pvc-protection`. [...] ```
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

## Why a Pod can hang on `Terminating` state
- [Kubernetes pod stuck Terminating: finalizers, grace periods, and force delete](https://www.netdata.cloud/guides/kubernetes/kubernetes-pod-stuck-terminating) — A pod stuck in `Terminating` stays visible in the API server after `kubectl delete`, sometimes for minutes or hours. Usually a finalizer blocks removal, a CSI volume is still attached, or the container is ignoring SIGTERM. Force deleting without diagnosis orphans containers and can violate StatefulSet guarantees. Check the signals first, then decide whether to wait, patch a finalizer, or force delete.

## What This Means

When you delete a pod, the API server sets `metadata.deletionTimestamp` and starts a graceful deletion window controlled by `terminationGracePeriodSeconds` (default 30). The kubelet executes any `preStop` hooks, sends SIGTERM to all containers, and waits up to the grace period before sending SIGKILL. [...] 3. Check if containers are still running. If `crictl ps -a` on the node shows the container as Running, the kubelet has not yet sent SIGKILL. The grace period has not expired, or a `preStop` hook is still executing. If the grace period has expired and the container is still running, the application is likely ignoring SIGTERM.
4. Look for volume attachment hangs. If the pod used a CSI PersistentVolume, check `kubectl get volumeattachment`. A stuck VolumeAttachment on a NotReady node often means the CSI driver or attach-detach controller has not completed cleanup. The controller-manager may wait roughly six minutes before force-detaching. If the node is shut down, the CSI driver on the node may have been terminated before unmount completed. [...] | Cause | What it looks like | First thing to check |
 --- 
| Finalizer not removed by controller | `deletionTimestamp` is set, phase is Terminating, `finalizers` is non-empty | `kubectl get pod  -o jsonpath='{.metadata.finalizers}'` |
| CSI volume detach hang | Pod on a NotReady node, VolumeAttachment still present, container stopped | `kubectl get volumeattachment` |
| Application ignores SIGTERM | Container stays Running with `deletionTimestamp` set, no `preStop` hook active | `crictl ps -a` on the node |
| `preStop` hook hang | Events show hook execution, grace period appears to expire twice | `kubectl get event --field-selector involvedObject.name=` |
- [Exploring the Termination Process in Kubernetes – IT Exams Training – Pass4Sure](https://www.pass4sure.com/blog/exploring-the-termination-process-in-kubernetes) — However, if a preStop hook is long-running or blocked—say, by a hanging process, unreachable endpoint, or faulty script—the termination sequence can be delayed beyond the configured grace period. This can cause the container to ignore the termination signal, leaving Kubernetes in a waiting state. If the hook exceeds the deadline, the container receives a forceful termination, but the Pod itself may still appear stuck if any other post-termination tasks, such as log flushing or storage detachment, are incomplete. [...] ## Proactive Strategies for Avoiding Termination Issues

While understanding and reacting to stuck Pods is necessary, the better strategy is to prevent them from occurring in the first place. Several proactive techniques can be implemented:

 Design lifecycle hooks with short, reliable execution times.
 Monitor and log hook behavior to catch errors early.
 Avoid hardcoded delays or blocking scripts in preStop hooks.
 Use finalizers sparingly and ensure external controllers are reliable.
 Adopt PID namespaces and init systems in container images.
 Opt for Parallel PodManagementPolicy in StatefulSets where order is not crucial.
 Establish observability with metrics for termination latency.
 Regularly audit resources for lingering finalizers and unfinished deletions. [...] In practice, when a finalizer is set on a Pod and the associated task doesn’t complete, Kubernetes cannot remove the resource from the API server. The Pod continues to appear as “Terminating,” even though the underlying containers may have already exited. Manual intervention becomes necessary at this point, usually involving editing the Pod definition and removing the finalizer from the metadata manually.

## Challenges Posed by PreStop Hooks
- [Pod Stuck in Terminating State Due to PreStop Hook.](https://platform9.com/kb/pmk/solutions/pod-stuck-in-terminating-state-unless-deleted-forcefully) — PreStop hook failure is the reason for the pod to be stuck in termination state, these errors can be seen in the kubelet log.
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

Determine if the cause of the `Terminating` state for a Pod, Namespace, or PVC is a finalizer. A Finalizer example to protect PVCs from deletion is the `kubernetes.io/pvc-protection`. [...] ## Pod Termination

There are multiple reasons why the Kubernetes Scheduler can evict a healthy container. For example, the execution of Pods with higher priority, the drain of a node during a version update, an auto-scaling process, a resource bin-packing, or a simple `kubectl delete` command.

Kubernetes provides graceful termination for not needed Pods with Container Lifecycle Hooks. They are executed by the kubelet on the specific containers when it receives the event.
- [Pod Lifecycle | Kubernetes](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle) — Typically, with this graceful termination of the pod, kubelet makes requests to the container runtime to attempt to stop the containers in the pod by first sending a TERM (aka. SIGTERM) signal, with a grace period timeout, to the main process in each container. The requests to stop the containers are processed by the container runtime asynchronously. There is no guarantee to the order of processing for these requests. Many container runtimes respect the `STOPSIGNAL` value defined in the container image and, if different, send the container image configured STOPSIGNAL instead of TERM. Once the grace period has expired, the KILL signal is sent to any remaining processes, and the Pod is then deleted from the API Server. If the kubelet or the container runtime's management service is [...] Pod termination flow, illustrated with an example:

1. You use the `kubectl` tool to manually delete a specific Pod, with the default grace period (30 seconds).
2. The Pod in the API server is updated with the time beyond which the Pod is considered "dead" along with the grace period. If you use `kubectl describe` to check the Pod you're deleting, that Pod shows up as "Terminating". On the node where the Pod is running: as soon as the kubelet sees that a Pod has been marked as terminating (a graceful shutdown duration has been set), the kubelet begins the local Pod shutdown process. [...] This "in-place" restart offers a more efficient way to reset a Pod's state compared to full deletion and recreation. This is especially valuable for workloads where rescheduling is costly, such as batch jobs or AI/ML training tasks.

##### How in-place Pod restarts work

When a `RestartAllContainers` action is triggered, the kubelet performs the following steps:

1. Fast Termination: All running containers in the Pod are terminated. The configured `terminationGracePeriodSeconds` is not respected, and any configured `preStop` hooks are not executed. This ensures a swift shutdown.
2. Preservation of Pod Resources: The Pod's essential resources are preserved:
- [Gracefully Terminating Pods in Kubernetes: Handling SIGTERM](https://jaadds.medium.com/gracefully-terminating-pods-in-kubernetes-handling-sigterm-fb0d60c7e983) — If the application doesn't terminate before the grace period ends, the kubelet sends a SIGKILL signal, forcefully stopping the containers and
- [Decoding the pod termination lifecycle in Kubernetes: a comprehensive guide | CNCF](https://www.cncf.io/blog/2024/12/19/decoding-the-pod-termination-lifecycle-in-kubernetes-a-comprehensive-guide) — When a pod is asked to terminate, Kubernetes updates the object state and marks it as “Terminating”.

Kubernetes also sends a SIGTERM signal to the main process in each container of the pod.

The SIGTERM signal is an indication that the processes in the containers should stop. The processes have a grace period (default is 30 seconds) to shut down properly.

If a process is still running after the grace period, Kubernetes sends a SIGKILL signal to force the process to terminate.

To gracefully terminate the pod you can either add terminationGracePeriodSeconds to your spec or add  kubectl delete pods  –grace-period=

The below contains a time series graph for graceful termination:

The “preStop” hook is executed just before a container is terminated. [...] Practical troubleshooting tips and solutions:

 Pods stuck in Terminating state: For pods stuck in the Terminating state, you can force delete the pod with kubectl delete pod  –grace-period=0 –force. However, this should be a last resort as it can cause data loss. It’s better to identify the root cause by checking the pod description (kubectl describe pod ) and looking for any errors.
 Pod Disruption Budgets: If you have a PDB that’s preventing pod termination, you may need to reconsider your PDB settings. If necessary, you can delete the PDB, but be aware that this may impact the availability of your application. Always consider the implications and plan downtime accordingly.

## Conclusion [...] Pod Termination due to Out of Memory / CrashloopBackoff : If a node is severely low on memory, the Linux kernel’s Out of Memory (OOM) Killer process kicks in and starts terminating processes to free up memory. In a Kubernetes context, this could lead to abrupt termination of your pods. This is not a graceful termination, so it’s usually a situation to avoid. You can mitigate such scenarios by setting appropriate resource requests and limits for your pods.
 Pod Termination due to Unschedulable Pods: When you create a pod, if there is not enough resource in any of the nodes to meet the resource request of the pod, the pod remains in a state of Pending. This could lead to pod termination if it remains unscheduled for a long time.
- [Kubernetes Pod Lifecycle Explained: Pending to Running to Termination](https://www.youtube.com/watch?v=Fh99XUsl2BA) — [0:46] running phase means at least one container is actively executing. The succeeded phase indicates all containers have completed successfully. The failed
[0:55] phase means one or more containers terminated with an error. The unknown phase occurs when the pod state cannot
[1:02] be determined. Finally, the terminating phase happens when the pod is being gracefully shut down. Each of these
[1:09] phases plays a critical role in understanding pod behavior.
[1:15] The pending phase is the initial state when a pod is first created. During this phase, the pod has been accepted by Kubernetes, but the containers are not
[1:23] yet running. There are several common reasons why a pod stays in the pending state. First, Kubernetes might be downloading container images from a [...] [3:53] and recreated. These phases are crucial for understanding whether your workloads completed as expected.
[4:02] Pod termination is a graceful shutdown process that occurs when a pod is deleted from the cluster. Understanding this process is essential for ensuring
[4:11] clean application shutdowns. The termination follows a specific sequence.
[4:16] First, any pre-top hooks that are configured are executed, allowing the application to perform cleanup tasks.
[4:23] Second, Kubernetes sends a SIGRM signal to all containers, notifying them to begin shutting down gracefully.
[4:31] Third, a grace period countdown begins with a default duration of 30 seconds, giving containers time to terminate on