# Root cause: Normal Kubernetes deployment rollout misinterpreted as pod failure

Service `checkout` in namespace `shop`.

## Root cause
Old ReplicaSet pods (7cf7bd8689) are gracefully terminating as part of a standard zero-downtime deployment rollout after new ReplicaSet pods (6b64f4dd94) became ready — this is expected Kubernetes behavior, not a failure.

## Mechanism
1. Deployment controller created new ReplicaSet 6b64f4dd94 (pod-template-hash changed from 7cf7bd8689) [describe shows different hashes]. 2. New pods checkout-6b64f4dd94-2sxqj (16s) and -cmh5j (9s) started and passed readiness probes (healthz returns 200 in logs). 3. EndpointSlice controller shifted traffic to new pods once readiness succeeded [3]. 4. Old ReplicaSet 7cf7bd8689 scaled down, sending SIGTERM to its pods with 30s terminationGracePeriodSeconds. 5. Old pods checkout-7cf7bd8689-5p4sx (2m14s) and -s9f5g (2m22s) entered Terminating state with READY=True (they were ready before termination began) [4]. 6. No events recorded because graceful termination is normal [EVENTS: (none)]. 7. The perceived 'incident' stems from misunderstanding the pod lifecycle choreography during rollouts [4].

Confidence: 0.95 · Labels: deployment_rollout, graceful_termination, zero_downtime, false_alarm, pod_lifecycle

## Evidence relied on
- checkout-7cf7bd8689-5p4sx   1/1     Terminating   0          2m14s
- checkout-6b64f4dd94-2sxqj   1/1     Running       0          16s
- 06/Oct/2026 17:21:26 - "GET /healthz HTTP/1.1" 200
- EVENTS: (none)
- [3] If the readiness probe returns a failed state, the EndpointSlice controller removes the Pod's IP address from the EndpointSlices
- [4] Typical rollout flow: New Pod starts → Readiness succeeds → Traffic shifts → Old Pod begins graceful shutdown → Termination completes

## Tavily sources
Queries: Kubernetes pods terminating gracefully despite passing readiness and liveness probes READY=True no events; Kubernetes deployment rollout old ReplicaSet pods stuck terminating 30s grace period health checks passing; Kubernetes memory limit 512Mi startup cache 96Mi OOM kill probe timeout period configuration
- [Troubleshooting Kubernetes Liveness and Readiness Probe Failures](https://resolve.ai/glossary/how-to-debug-kubernetes-probe-issues) — When liveness failures repeat, `kubectl get pods` shows the pod in `CrashLoopBackOff` with a climbing restart count. CrashLoopBackOff means the kubelet is backing off exponentially between restarts; the `Unhealthy` events above tell you why the restarts keep happening. And if the pod is stuck in Pending, its probes haven't run at all and the problem sits earlier in the lifecycle, in scheduling, image pulls, or volumes, not in the health checks.

If the pod is running but probes fail, test the endpoint by hand:

```
kubectl exec -it my-app-xyz123 -- curl -v  
```

Success here with failing probes points to timing (probes fire before the app is ready), timeout (curl will wait longer than the 1-second default), or interception (the network bucket above). [...] Startup probes ask "has this container finished starting?" While one is configured and hasn't succeeded, liveness and readiness stay disabled. If it never succeeds within `failureThreshold` × `periodSeconds`, the container is killed before the other probes ever run. Typical causesare long initialization (migrations, cache warming, JIT) against thresholds set too low. Slow starters without a startup probe get killed by liveness instead.

Liveness and readiness failures both appear as `Unhealthy` events in `kubectl describe pod`, but they trigger different responses and usually have different root causes:

```
Warning Unhealthy Liveness probe failed: Get " context deadline exceeded Warning Unhealthy Readiness probe failed: HTTP probe failed with statuscode: 503 
``` [...] The test is to `kubectl exec` into the pod and curl the health endpoint twice, once on `localhost` and once on the pod IP, because the pod IP is what the kubelet actually probes. Localhost passing while the pod IP fails usually means the app is bound to 127.0.0.1. Both passing while probes still fail points outside the pod. Check the mesh first, then the CNI. And if the image has no curl, `kubectl debug` with an ephemeral container gets you a shell.

### Probe misconfiguration
- [Client is disconnected when the pod is terminating or fails the readiness probe - General Discussions - Discuss Kubernetes](https://discuss.kubernetes.io/t/client-is-disconnected-when-the-pod-is-terminating-or-fails-the-readiness-probe/19408) — `LoadBalancer`
`connection reset by peer`

I’m using the internal k8s platform in my company and I asked the same issue to its managers.  
They said closing client connections when the pod is removed from service endpoints is the official spec of k8s.  
However, I think keeping connections and letting the pod handle them gracefully are more reasonable.

Could you guys please confirm whether it is truly a spec of k8s or not?  
There are several docs which say pods will not receive new connections in `Terminating` or `Not-Ready` status, but it is hard to find an official doc that says already established connections will be closed or not.  
Also could you guys suggest some points or ways that I or our platform managers can try on settings of k8s to slove this issue? [...] I am no developer, but regarding the 12 factor app

Processes shut down gracefully when they receive a SIGTERM signal from the process manager. For a web process, graceful shutdown is achieved by ceasing to listen on the service port (thereby refusing any new requests), allowing any current requests to finish, and then exiting. Implicit in this model is that HTTP requests are short (no more than a few seconds), or in the case of long polling, the client should seamlessly attempt to reconnect when the connection is lost.

Your description seems to fit in the “long polling” scenario described here, so maybe the application can be updated to retry the un-processed request (on a different pod).

Best regards,

Xavi

The unfortunate answer is that it was under-defined. Both behaviors exist. [...] `Terminating`
`Not-Ready`

Thanks!

### Cluster information:

Kubernetes version: v1.15.10  
I’m sorry but, as I’m using the internal k8s platform in my company as I said above, the detailed cluster information is invisible to me.

Hi Junghoon:

From the Pod Lifecycle you’ve provided:

Pods that shut down slowly cannot continue to serve traffic as load balancers (like the service proxy) remove the Pod from the list of endpoints as soon as the termination grace period begins.

As the pod is removed as a valid endpoint, your client gets a `connection reset by peer`.

`connection reset by peer`

I am no developer, but regarding the 12 factor app
- [Pod Lifecycle | Kubernetes](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle) — If the readiness probe returns a failed state, the EndpointSlice controller removes the Pod's IP address from the EndpointSlices of all Services that match the Pod.

Readiness probes run on the container during its whole lifecycle.

## Termination of Pods

Because Pods represent processes running on nodes in the cluster, it is important to allow those processes to gracefully terminate when they are no longer needed (rather than being abruptly stopped with a `KILL` signal and having no chance to clean up). [...] #### Note:

When a pod is failing to start repeatedly, `CrashLoopBackOff` may appear in the `Status` field of some kubectl commands. Similarly, when a pod is being deleted, `Terminating` may appear in the `Status` field of some kubectl commands.

Make sure not to confuse Status, a kubectl display field for user intuition, with the pod's `phase`. Pod phase is an explicit part of the Kubernetes data model and of the Pod API.

```
 NAMESPACE NAME READY STATUS RESTARTS AGE alessandras-namespace alessandras-pod 0/1 CrashLoopBackOff 200 2d9h 
```

A Pod is granted a term to terminate gracefully, which defaults to 30 seconds. You can use the flag `--force` to terminate a Pod by force. [...] This type of probe is only executed at startup, unlike liveness and readiness probes, which are run periodically.

If the startup probe fails, the kubelet kills the container, and the container is subjected to its restart policy.

### Liveness probe

Liveness probes determine when to restart a container. For example, liveness probes could catch a deadlock, where an application is running, but unable to make progress. Restarting a container in such a state can help to make the application more available despite bugs.
- [Understanding the Kubernetes Pod Lifecycle and Graceful Shutdown](https://medium.com/@sharathkumarlokesh/understanding-the-kubernetes-pod-lifecycle-and-graceful-shutdown-acd5a56fce06) — Typical rollout flow:

New Pod starts  
↓  
Readiness succeeds  
↓  
Traffic shifts  
↓  
Old Pod begins graceful shutdown  
↓  
Termination completes
This choreography enables:

_Zero-downtime deployments._

## CrashLoopBackOff: Lifecycle Gone Wrong

One of the most common Pod lifecycle problems.

Meaning:

   Container repeatedly crashes
   Kubernetes repeatedly restarts it

Typical causes:

   Application errors
   Bad probes
   Missing configs
   Startup failures

## Real Example

Liveness probe too aggressive:

Startup time = 60s  
Probe timeout = 10s
Kubernetes thinks app is dead:

   Restarts continuously

This creates:

CrashLoopBackOff
## Best Practices That Actually Matter

## Handle SIGTERM Properly

Applications should: [...] This is the steady operational state.

Meaning:

   Pod scheduled successfully
   Containers started
   At least one container running

But important detail:

_Running does NOT necessarily mean ready._

That’s where readiness probes matter.

## Running vs Ready

A Pod can be:

Running = Yes  
Ready = No
Example:

   Application process started
   Database connection still initializing

Without readiness checks:

   Traffic may reach incomplete applications

## Readiness Gates Traffic

When readiness succeeds:

   Pod added to Service endpoints
   Traffic begins flowing

This is critical during:

   Rollouts
   Scaling
   Recovery

## Phase 3: Succeeded or Failed

These phases commonly appear with:

   Jobs
   Batch workloads

## Succeeded

All containers exited successfully.

Example: [...] _Pod termination and transition events._

Understanding the Pod lifecycle in Kubernetes is essential if you want reliable applications and zero-downtime deployments.

Let’s break down how Pods actually behave from creation to termination — and why graceful shutdown matters so much.

## First: Pods Are Ephemeral

This is one of the most important Kubernetes concepts.

Pods are not permanent machines.

They are:

_Disposable runtime instances._

Kubernetes may terminate Pods because of:

   Deployments
   Node failures
   Scaling events
   Resource pressure
   Evictions
   Maintenance operations

Applications must be designed with this reality in mind.

## The High-Level Pod Lifecycle

A Pod typically moves through these phases:
- [Liveness, Readiness, and Startup Probes | Kubernetes](https://kubernetes.io/docs/concepts/workloads/pods/probes) — Feature state: Stable since Kubernetes v1.28

In 1.25 and above, users can specify a probe-level `terminationGracePeriodSeconds` as part of the probe specification. When both a pod- and probe-level `terminationGracePeriodSeconds` are set, the kubelet will use the probe-level value.

When setting the `terminationGracePeriodSeconds`, note the following:

 The kubelet always honors the probe-level `terminationGracePeriodSeconds` field if it is present on a Pod.
 If you have existing Pods where the `terminationGracePeriodSeconds` field is set and you no longer wish to use per-probe termination grace periods, you must delete those existing Pods.

For example: [...] `failureThreshold`
:   After a probe fails `failureThreshold` times in a row, Kubernetes considers that the overall check has failed: the container is not ready/healthy/live. Defaults to 3. Minimum value is 1. For the case of a startup or liveness probe, if at least `failureThreshold` probes have failed, Kubernetes treats the container as unhealthy and triggers a restart for that specific container. The kubelet honors the setting of `terminationGracePeriodSeconds` for that container. For a failed readiness probe, the kubelet continues running the container that failed checks, and also continues to run more probes; because the check failed, the kubelet sets the `Ready` condition on the Pod to `false`. [...] Probe-level `terminationGracePeriodSeconds` cannot be set for readiness probes. It will be rejected by the API server.

## Probe mechanism details

### HTTP probes

HTTP probes have additional fields that can be set on `httpGet`:
- [Deployments | Kubernetes](https://kubernetes.io/docs/concepts/workloads/controllers/deployment) — The output is similar to this:

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
 Looking at the Pods created, you see that 1 Pod created by new ReplicaSet is stuck in an image pull loop. [...] Use the status of the Deployment as an indicator that a rollout has stuck.
 Clean up older ReplicaSets that you don't need anymore. [...] Create a Deployment to rollout a ReplicaSet. The ReplicaSet creates Pods in the background. Check the status of the rollout to see if it succeeds or not.
 Declare the new state of the Pods by updating the PodTemplateSpec of the Deployment. A new ReplicaSet is created, and the Deployment gradually scales it up while scaling down the old ReplicaSet, ensuring Pods are replaced at a controlled rate. Each new ReplicaSet updates the revision of the Deployment.
 Rollback to an earlier Deployment revision if the current state of the Deployment is not stable. Each rollback updates the revision of the Deployment.
 Scale up the Deployment to facilitate more load.
 Pause the rollout of a Deployment to apply multiple fixes to its PodTemplateSpec and then resume it to start a new rollout.
- [How to Debug a Stuck Kubernetes Rollout with a Hands-On Lab](https://www.freecodecamp.org/news/how-to-debug-a-stuck-kubernetes-rollout-with-a-hands-on-lab) — ```
k get endpointslices -l kubernetes.io/service-name=rollout-demo -o json k exec --pod-running-timeout=30s --request-timeout=60s http-client -- \ python -u /app/probe.py --url  \ --expected-version v2 --count 10 --interval 0.2 
```

The probe checks the status and version and records the responding Pod's name. Compare those names with the previous healthy ReplicaSet's Pods. Compare the EndpointSlice `targetRef.uid` values with their UIDs too.

In the recorded run, all ten responses came from the two previous-revision Pods. Their EndpointSlice entries were ready. The blocked image Pod was also listed, but its endpoint had `ready: false` and `serving: false`. [...] ```
k apply -f failure-lab/manifests/healthy.json k rollout status deployment/rollout-demo --timeout=300s k wait --for=delete "pod/$BAD_POD" --timeout=120s k get deployment rollout-demo -o json k get replicasets -l app=rollout-demo -o wide k get pods -l app=rollout-demo -o wide k get endpointslices -l kubernetes.io/service-name=rollout-demo -o json k exec --pod-running-timeout=30s --request-timeout=60s http-client -- \ python -u /app/probe.py --url  \ --expected-version v2 --count 10 --interval 0.2 
```

Check the whole recovery, not just the rollout command's success. The desired spec should match `healthy.json`. The controller must have observed it, with replicas, updated replicas, ready replicas, and available replicas all equal to two. [...] `Available=True` remained because the old Pods still supplied the required availability. `Progressing=False` reported the stalled update. Conversely, `Progressing=True` can also remain after a successful rollout, so always read its reason and the replica counts.

The Deployment controller reports the deadline without automatically rolling back. The missing image was still the desired image in the deadline snapshot.

Repeat the Service check now. All ten recorded requests after the deadline also came from the old Pods. Only the image case waits for the controller deadline in this tutorial.

## How to Restore the Healthy Configuration

Recover now, before introducing another failure. Keep `BAD_POD` set to the failed Pod you just inspected:
- [Kubernetes Deployment & ReplicaSet Troubleshooting](https://www.linkedin.com/pulse/kubernetes-deployment-replicaset-troubleshooting-sivaiah-yakkanti-xe8bc) — Old ReplicaSet Not Terminating Symptoms An old ReplicaSet remains even after the rollout completes. Common Causes ReplicaSet still has replicas
- [Replica set sticks around after new deployment : r/kubernetes](https://www.reddit.com/r/kubernetes/comments/lt6ct7/replica_set_sticks_around_after_new_deployment) — I've seen this when the old pod is on a crippled host. Maybe kubelet is down or docker is busted or it's having some other issue. The controller
- [Kubernetes Interview Question 77  Scenario: A Deployment ...](https://www.facebook.com/maliwadevops/videos/-kubernetes-interview-question-77-scenarioa-deployment-rollout-is-stuck-the-new-/1059112163716622) — It outlines a scenario where old ReplicaSet pods do not terminate during a rollout and offers a seven-step resolution process involving
- [CrashLoopBackOff in Kubernetes: Causes and Fixes](https://cast.ai/blog/crashloopbackoff) — VPA helps automate this. Valid `updateMode` values: `Off` (recommendations only), `Initial` (set on pod creation), `Recreate` (apply via pod eviction), `Auto` (in-place on K8s 1.33+, beta with the `InPlacePodVerticalScaling` feature gate; clusters running 1.27–1.32 still use pod eviction).

JVM workloads: Set `-Xmx` to ~75% of the container memory limit. A 512Mi limit should have `-Xmx384m`. This leaves headroom for non-heap memory — metaspace, thread stacks, native libraries. Skipping this is one of the most common causes of Java OOM kills in Kubernetes.
- [What Happens When Kubernetes Pods Run Out of Memory or Shut Down?](https://medium.com/@shubham.patel191295/what-happens-when-kubernetes-pods-run-out-of-memory-or-shut-down-2f801e0e2e8d) — ### What Is an OOM Kill?

OOM means Out Of Memory.

An OOM kill happens when a process uses too much memory and the operating system terminates it to protect the machine.

In Kubernetes, memory limits are enforced by the kubelet, container runtime, and ultimately the Linux kernel using cgroups. If a container uses more memory than its configured limit, the kernel may terminate it. Kubernetes documents that memory limits are enforced reactively through OOM kills rather than smooth throttling.

### Simple Explanation

Imagine your container has this memory limit:

resources:  
 limits:  
 memory: "512Mi"
This means:

> _“This container should not use more than 512 MiB of memory.”_ [...] ## Example: A Pod That Can Be OOMKilled

apiVersion: v1  
kind: Pod  
metadata:  
 name: memory-demo  
spec:  
 containers:  
 - name: app  
 image: example.com/memory-demo:v1  
 resources:  
 requests:  
 # Kubernetes uses this value for SCHEDULING.  
 # It means: "I need at least 256Mi memory."  
 memory: "256Mi"  
 cpu: "250m"  
 limits:  
 # If the container uses more than THIS,  
 # it may be KILLED by the kernel.  
 memory: "512Mi"  
 # If the container uses more than THIS,  
 # it is usually THROTTLED, not killed.  
 cpu: "500m"
In this example:

   `memory request = 256Mi` → Scheduling hint
   `memory limit = 512Mi` → Maximum before OOM kill

The request helps Kubernetes choose a node. The limit defines the approximate maximum memory usage before the container may be killed. [...] ✅ Better:

resources:  
 requests:  
 memory: "512Mi"  
 limits:  
 memory: "1Gi"
### Mistake 3: Ignoring SIGTERM

If your app ignores shutdown signals, Kubernetes may eventually force kill it after the grace period.

✅ Better:

signal.Notify(stop, syscall.SIGTERM, syscall.SIGINT)
### Mistake 4: Grace Period Shorter Than Request Duration

If your API has requests that take up to 60 seconds, this is risky:

❌ Bad:

terminationGracePeriodSeconds: 10
✅ Better:

terminationGracePeriodSeconds: 75
But don’t set it too high without reason, because slow termination can slow rollouts.

### Mistake 5: Using Only Liveness Probes

Liveness probes restart unhealthy containers. Readiness probes decide whether a Pod should receive traffic.

For graceful shutdown, readiness is extremely important.
- [Container Memory Limits and OOMKilled Debugging Guide 2026](https://khimananda.com/blog/container-memory-limits-and-oomkilled-debugging) — 1. Establish a Baseline: Deploy with generous limits in staging and record `container_memory_working_set_bytes` for at least one full business cycle. Exclude cache-only memory using `container_memory_rss` for Java/Go apps where page cache inflates working set.
2. Calculate Percentiles: Set requests to the p80 of working set memory. Set limits to p99 + 15%. This accommodates normal variance while catching true anomalies before they crash the pod.
3. Account for Runtime Overhead: JVM-based applications require additional headroom for metaspace, code cache, and direct buffers beyond `-Xmx`. A safe formula is `limit = Xmx + 512Mi + (Xmx  0.1)`. For Node.js, account for V8 heap plus native addon allocations. [...] Quick answer: Container memory limits and OOMKilled debugging involves checking `kubectl describe pod` for "OOMKilled" exit codes, analyzing kernel logs via `dmesg`, and comparing actual usage against configured limits. Fix issues by right-sizing memory requests/limits based on percentile metrics, tuning runtime garbage collection, or resolving application-level memory leaks.

Figure 1: The kernel enforces container memory limits via cgroups; exceeding them triggers an OOM kill that Kubelet reports as OOMKilled.

## How do you diagnose container memory limits and OOMKilled debugging in Kubernetes? [...] Most Kubernetes distributions disable swap entirely. If enabled, containers may experience severe latency before OOMKilled as the kernel swaps anonymous pages. Disable swap on all nodes using swapoff -a and mask the systemd unit to ensure predictable memory enforcement and performance.

Init containers run sequentially with their own limits but share the pod memory context. If an init container consumes excessive memory, it can trigger node-level pressure affecting subsequent containers. Set explicit limits on init containers and monitor their memory usage separately during startup phases.
- [How to Right-Size Kubernetes Resource Requests and Limits](https://oneuptime.com/blog/post/2026-01-06-kubernetes-right-size-resources/view) — `# Find OOM killed pods from cluster events
kubectl get events -n production --field-selector reason=OOMKilled
# Check container last state for OOM information
kubectl get pod <pod-name> -n production -o jsonpath='{.status.containerStatuses[].lastState}'`

### Fix OOM Kills

When pods are consistently OOM killed, increase both the request and limit. The request ensures the pod gets scheduled on a node with sufficient memory.

`resources:
requests:
memory: 512Mi # Increase if consistently OOMing
limits:
memory: 768Mi # Give buffer for memory spikes`

Also check for memory leaks in your application.

## Step 6: Quality of Service (QoS) Classes

Kubernetes assigns QoS based on resource settings:

### Guaranteed (Highest Priority)
- [Kubernetes OOMKilled Error: How to Fix & Tips for Preventing It · Dash0](https://www.dash0.com/guides/kubernetes-oomkilled-error-how-to-fix-and-tips-for-preventing-it) — To avoid this, it’s important to understand the memory requirements of your application. Monitor the memory usage of your application under different load scenarios to get a clear picture of its memory needs. Then, set the memory limits accordingly in your Kubernetes deployment configuration.

### Memory leaks in applications

Another common cause of OOMKilled events is memory leaks in applications. A memory leak occurs when a program consumes memory but does not release it back to the system after it’s done using it. Over time, this can lead to an increase in the memory usage of the application, eventually triggering an OOMKilled event.