# Root cause: Checkout pods stuck in Terminating state during rolling deployment due to probe misconfiguration and old Kubernetes version

Service `checkout` in namespace `shop`.

## Root cause
Liveness and readiness probes both target the same /healthz endpoint without differentiation, and on Kubernetes v1.15.10 this causes the kubelet to mishandle probe failures during pod termination, preventing SIGKILL after the grace period expires.

## Mechanism
1. Rolling deployment creates new ReplicaSet (7b4fcf8959) and terminates old pods (774b5f56b6). 2. Kubelet marks old pods Terminating, sends SIGTERM, and starts 60s grace period. 3. Both probes continue hitting /healthz every 5-10s while application shuts down. 4. Probes fail as /healthz becomes unavailable, but due to a known bug in v1.15 [1] the kubelet does not advance to SIGKILL after grace period — it may reset the termination timer or wait for probe success. 5. Pods remain in Terminating with containers still Running for >2 minutes (observed 2m57s, 2m51s) despite 60s grace period. 6. New pods start serving traffic while old pods linger, causing no events and ungraceful termination.

Confidence: 0.80 · Labels: probe_config, termination_stuck, old_kubernetes_version, rolling_deployment, graceful_shutdown

## Evidence relied on
- Status: Terminating (lasts <invalid>)
- Termination Grace Period: 60s
- livenessProbe: httpGet path: /healthz port: http
- readinessProbe: httpGet path: /healthz port: http
- Kubernetes version: v1.15.10
- liveness/readiness probe is executed and failed while pod is terminating [1]
- No differentiation between liveness and readiness [2]

## Tavily sources
Queries: Kubernetes pod stuck terminating grace period invalid no events liveness readiness probe same endpoint; containerd pod terminating stuck graceful shutdown SIGTERM handling kubernetes deployment rollout old replicaset; kubernetes termination grace period 60s invalid duration pod finalizer admission webhook blocking deletion
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
 liveness/readiness probe fails while pod is terminated. Also it happened only once during the pod termination. The issue started happening after upgrading version to v1.7 from v1.6.X
- [Kubernetes Pod Kept Restarting. The Problem Was the Liveness Probe.](https://medium.com/lets-code-future/kubernetes-pod-kept-restarting-the-problem-was-the-liveness-probe-dedbdf607e04) — No differentiation between liveness and readiness

   Same endpoint for both probes
   Should have `/live` and `/ready` endpoints
   Different checks for different purposes

No metrics on probe failures

   Can’t see how often probes fail but recover
   Can’t track probe response times
   No alerting on degraded health

We’re fixing these next month. After we recover from this incident.

## Resources That Actually Helped

If you’re dealing with Kubernetes in production, these resources helped me avoid the next 847 restarts:

📚 Free Resources (Learn the Basics):

Kubernetes in Production Pack — Deployment, scaling, and troubleshooting. Has a section on probe configuration I wish I’d read before this incident. [...] startupProbe:  
 httpGet:  
 path: /health  
 port: 8080  
 initialDelaySeconds: 0  
 periodSeconds: 5  
 failureThreshold: 30  
 timeoutSeconds: 3  
  
livenessProbe:  
 httpGet:  
 path: /health  
 port: 8080  
 initialDelaySeconds: 0  
 periodSeconds: 10  
 failureThreshold: 3  
 timeoutSeconds: 5  
readinessProbe:  
 httpGet:  
 path: /health  
 port: 8080  
 initialDelaySeconds: 0  
 periodSeconds: 5  
 failureThreshold: 2  
 timeoutSeconds: 3
## What’s Still Broken

Even with the fix, we have problems:

Health endpoint is too simple

   Returns 200 if server is up
   Doesn’t check database connection
   Doesn’t check Redis connection
   Doesn’t check downstream services

No differentiation between liveness and readiness [...] Comment 4: “This is why we don’t use Kubernetes for small apps.”

We have 12 services. 40 pods. Kubernetes makes sense for us.

The problem wasn’t Kubernetes. The problem was copying config without understanding it.

## What I Learned About Kubernetes Health Checks

Liveness probe ≠ readiness probe

Liveness: “Is the app alive?” (If no → restart) Readiness: “Can the app serve traffic?” (If no → remove from load balancer)

I was using liveness for both. Wrong.

startupProbe is not optional for slow apps

If your app takes >30 seconds to start, you NEED startupProbe.

Without it, liveness probe will kill your pod during startup.

failureThreshold × periodSeconds = grace period

periodSeconds: 10  
failureThreshold: 3
= 30 seconds to recover before restart.
- [Client is disconnected when the pod is terminating or fails the readiness probe - General Discussions - Discuss Kubernetes](https://discuss.kubernetes.io/t/client-is-disconnected-when-the-pod-is-terminating-or-fails-the-readiness-probe/19408) — `Terminating`
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
- [Liveness, Readiness, and Startup Probes | Kubernetes](https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes) — Feature state: Stable since Kubernetes v1.28

In 1.25 and above, users can specify a probe-level `terminationGracePeriodSeconds` as part of the probe specification. When both a pod- and probe-level `terminationGracePeriodSeconds` are set, the kubelet will use the probe-level value.

When setting the `terminationGracePeriodSeconds`, note the following:

 The kubelet always honors the probe-level `terminationGracePeriodSeconds` field if it is present on a Pod.
 If you have existing Pods where the `terminationGracePeriodSeconds` field is set and you no longer wish to use per-probe termination grace periods, you must delete those existing Pods.

For example: [...] If you'd like your container to be killed and restarted if a probe fails, then specify a liveness probe, and specify a `restartPolicy` of `Always` or `OnFailure`.

A common pattern for liveness probes is to use the same low-cost HTTP endpoint as for readiness probes, but with a higher `failureThreshold`. This ensures that the pod is observed as not-ready for some period of time before it is hard killed.

### When should you use a readiness probe?

To start sending traffic to a Pod only when a probe succeeds, specify a readiness probe. The readiness probe might be the same as the liveness probe, but the existence of the readiness probe in the spec means that the Pod will start without receiving any traffic and only start receiving traffic after the probe starts succeeding. [...] `terminationGracePeriodSeconds`
:   configure a grace period for the kubelet to wait between triggering a shut down of the failed container, and then forcing the container runtime to stop that container. The default is to inherit the Pod-level value for `terminationGracePeriodSeconds` (30 seconds if not specified), and the minimum value is 1. See probe-level `terminationGracePeriodSeconds` for more detail.

#### Caution:

Incorrect implementation of readiness probes may result in an ever growing number of processes in the container, and resource starvation if this is left unchecked.

### Probe-level `terminationGracePeriodSeconds`

Feature state: Stable since Kubernetes v1.28
- [Liveness, Readiness, and Startup Probes | Kubernetes](https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes#readiness-probe) — Feature state: Stable since Kubernetes v1.28

In 1.25 and above, users can specify a probe-level `terminationGracePeriodSeconds` as part of the probe specification. When both a pod- and probe-level `terminationGracePeriodSeconds` are set, the kubelet will use the probe-level value.

When setting the `terminationGracePeriodSeconds`, note the following:

 The kubelet always honors the probe-level `terminationGracePeriodSeconds` field if it is present on a Pod.
 If you have existing Pods where the `terminationGracePeriodSeconds` field is set and you no longer wish to use per-probe termination grace periods, you must delete those existing Pods.

For example: [...] If you'd like your container to be killed and restarted if a probe fails, then specify a liveness probe, and specify a `restartPolicy` of `Always` or `OnFailure`.

A common pattern for liveness probes is to use the same low-cost HTTP endpoint as for readiness probes, but with a higher `failureThreshold`. This ensures that the pod is observed as not-ready for some period of time before it is hard killed.

### When should you use a readiness probe?

To start sending traffic to a Pod only when a probe succeeds, specify a readiness probe. The readiness probe might be the same as the liveness probe, but the existence of the readiness probe in the spec means that the Pod will start without receiving any traffic and only start receiving traffic after the probe starts succeeding. [...] `terminationGracePeriodSeconds`
:   configure a grace period for the kubelet to wait between triggering a shut down of the failed container, and then forcing the container runtime to stop that container. The default is to inherit the Pod-level value for `terminationGracePeriodSeconds` (30 seconds if not specified), and the minimum value is 1. See probe-level `terminationGracePeriodSeconds` for more detail.

#### Caution:

Incorrect implementation of readiness probes may result in an ever growing number of processes in the container, and resource starvation if this is left unchecked.

### Probe-level `terminationGracePeriodSeconds`

Feature state: Stable since Kubernetes v1.28
- [Gracefully Terminating Pods in Kubernetes: Handling SIGTERM](https://jaadds.medium.com/gracefully-terminating-pods-in-kubernetes-handling-sigterm-fb0d60c7e983) — Handling SIGTERM. Kubernetes sends SIGTERM to the main process inside a container, giving the application a chance to shut down gracefully.
- [Avoiding downtime in rolling deployments by blocking SIGTERM](https://andrewlock.net/deploying-asp-net-core-applications-to-kubernetes-part-11-avoiding-downtime-in-rolling-deployments-by-blocking-sigterm) — Option 1 was very heavy-handed, had other implications, and wasn't an option on the table, so we can scratch that! Option 2 again, has broader (performance) implications, and wouldn't actually fix the problem, it would only mitigate it. That left option 3 as the easiest way to work around the issue.

The idea is that when Kubernetes asks for a pod to terminate, we ignore the signal for a while. We note that termination was requested, but we don't actually shut down the application for 30s, so we can continue to handle requests. After 30s, we gracefully shut down.

 Instead of terminating immediately, the old pods remain until the NGINX config updates 

Instead of terminating immediately, the old pods remain until the NGINX config updates [...] That's all we need in our applications, but if you try deploying this to Kubernetes as-is you might be disappointed. It almost works, but Kubernetes will start hard `SIGKILL`ing your pods!

## Preventing Kubernetes from killing your pods

When Kubernetes sends the `SIGTERM` signal to terminate a pod, it expects the pod to shutdown in a graceful manner. If the pod doesn't, then Kubernetes gets bored and `SIGKILL`s it instead. The time between `SIGTERM` and `SIGKILL` is called the `terminationGracePeriodSeconds`.

By default, that's 30 seconds. Given that we've just added a 30s delay after `SIGTERM` before our app starts shutting down, it's now pretty much guaranteed that our app is going to be hard killed. To avoid that, we need to extend the `terminationGracePeriodSeconds`. [...] ## So what went wrong?

Unfortunately, rebuilding all that configuration is an expensive operation. For that reason, the ingress controller only applies updates to the NGINX configuration every 30s by default. That was causing the following sequence of events during a deployment upgrade:

1. New pods are deployed, old pods continue running.
2. When the new pods are ready, the old pods are marked for termination.
3. Pods marked for termination receive a SIGTERM notification. This causes the pods to start shutting down.
4. The Kubernetes service observes the pod change, and removes them from the list of available endpoints.
5. The ingress controller observes the change to the service and endpoints.
6. After 30s, the ingress controller updates the NGINX pods' config with the new endpoints.
- [Kubernetes Pods Stuck in Terminating: A Resolution Guide - DEV Community](https://dev.to/imjoseangel/kubernetes-pods-stuck-in-terminating-a-resolution-guide-2jh3) — When Kubelet knows that a Pod should evict, it marks the Pod state as `Terminating` and stops sending traffic to it. Then, it executes the `preStop` lifecycle hook (when available). It sends the `SIGTERM` to the Main process (pid 1) within each container and waits for their termination. If the applications inside the containers are properly prepared, they will start a graceful shutdown. The duration should not be more than the specified in the spec.terminationGracePeriodSeconds which is 30 seconds by default.

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

From the Kubernetes Documentation: [...] From the Kubernetes Documentation:

> If a `PreStop` hook hangs during execution, the Pod's phase will be `Terminating` and remain there until the Pod is killed after its `terminationGracePeriodSeconds` expires.

For instance. This configuration:

```
spec: terminationGracePeriodSeconds: 3600 containers: - lifecycle: preStop: exec: command: -/bin/sh - -c - sleep 3600
```

Will keep the Pod in the `Terminating` state for 1 hour.

It is essential to handle the `SIGTERM` correctly and ensure that the application terminates gracefully when the kubelet sends the `SIGTERM` to the container.

## Remove Finalizers

Determine if the cause of the `Terminating` state for a Pod, Namespace, or PVC is a finalizer. A Finalizer example to protect PVCs from deletion is the `kubernetes.io/pvc-protection`.
- [Importance of Graceful Shutdown in Kubernetes](https://medium.com/criteo-engineering/importance-of-graceful-shutdown-in-kubernetes-605f0669d6ae) — Sitemap

Open in app

Sign up

Sign in

, you might still see errors during deployment. This is especially annoying when you are trying to maintain “zero-downtime” systems.

When Kubernetes needs to terminate a pod (for any reason), it follows this sequence:

1.   Sends a SIGTERM signal to your container
2.   Waits for a grace period (30 seconds by default)
3.   If the container does not exit after the grace period, it gets brutal and sends a SIGKILL signal [...] The problem? Most applications do not properly handle that SIGTERM signal. They just die immediately, dropping any in-flight requests. In the real world, while most API requests complete in 100–300ms, there are often those long-running operations that take 5–15 seconds or more. Think about processing uploads, generating reports, or running complex database queries. When these longer operations get cut off, that’s when users really feel the pain.

### When Does Kubernetes Terminate Pods?

Rolling updates are just one scenario where your pods might be terminated. Here are other common situations that can lead to pod terminations:
- [Kubernetes Pod Graceful Shutdown Explained](https://www.linkedin.com/posts/bibinwilson_devops-kubernetes-activity-7481203168912240640-7K24) — When a pod shuts down in Kubernetes, It sends a SIGTERM signal to the container. If your app does not handle SIGTERM properly, it might stop in
- [Kubernetes pod stuck Terminating: finalizers, grace periods, and force delete](https://www.netdata.cloud/guides/kubernetes/kubernetes-pod-stuck-terminating) — # Check deletion timestamp and configured grace period # Check deletion timestamp and configured grace period # Check deletion timestamp and configured grace periodkubectl get pod  -o jsonpath='deletionTimestamp={.metadata.deletionTimestamp}{"\n"}gracePeriod={.spec.terminationGracePeriodSeconds}{"\n"}' kubectl get pod  -o jsonpath='deletionTimestamp={.metadata.deletionTimestamp}{"\n"}gracePeriod={.spec.terminationGracePeriodSeconds}{"\n"}' ='deletionTimestamp={.metadata.deletionTimestamp}{"\n"}gracePeriod={.spec.terminationGracePeriodSeconds}{"\n"}'   # Inspect finalizers blocking deletion # Inspect finalizers blocking deletion # Inspect finalizers blocking deletionkubectl get pod  -o jsonpath='{.metadata.finalizers}' kubectl get pod  -o jsonpath='{.metadata.finalizers}' [...] # Review recent pod events for lifecycle hook failures # Review recent pod events for lifecycle hook failures # Review recent pod events for lifecycle hook failureskubectl get events --field-selector involvedObject.name= --sort-by='.lastTimestamp' kubectl get events --field-selector involvedObject.name= --sort-by='.lastTimestamp' = ='.lastTimestamp'   # Check API server DELETE latency during mass termination events # Check API server DELETE latency during mass termination events # Check API server DELETE latency during mass termination eventskubectl get --raw /metrics | grep 'apiserver_request_duration_seconds_bucket{.verb="DELETE".resource="pods"' kubectl get --raw /metrics | grep 'apiserver_request_duration_seconds_bucket{.verb="DELETE".resource="pods"' [...] | Signal | Why it matters | Warning sign |
 --- 
| `kubelet_pleg_relist_duration_seconds` p99 | Slow PLEG means the kubelet cannot detect container exits, delaying Terminating state resolution | > 10 seconds sustained |
| `kubelet_runtime_operations_errors_total` | Failed CRI operations prevent container stop and volume unmount | Any sustained increase |
| VolumeAttachment count per node | Stuck attachments block pod deletion and rescheduling | Attachments persist longer than 6 minutes for terminated pods |
| Node Ready condition | NotReady nodes cannot complete graceful termination | Ready=False or Unknown for longer than 1 minute |
| `apiserver_request_duration_seconds` for DELETE on pods | Control plane saturation slows deletion processing | p99 > 1 second sustained |
- [Pod stuck in Terminating: what is actually blocking the delete | KubeGlance Blog](https://kubeglance.com/blog/pod-stuck-terminating) — Zoom

The API server never deletes the record itself until the grace period has elapsed and the finalizer list is empty.

The important property is that the API server is a bookkeeper here, not an executor. It marks the object and waits. Nothing in that sequence has a timeout that eventually gives up — a finalizer whose controller is gone will hold the object indefinitely, and that is by design.

## 1. The grace period has not elapsed

The default is 30 seconds, and it starts when the deletion is accepted, not when the process exits. The kubelet sends `SIGTERM`, waits, then sends `SIGKILL`. [...] ## Preventing it

 Handle `SIGTERM`. A process that exits on the signal terminates in milliseconds. One that ignores it costs you the full grace period every time, on every deploy.
 Set `terminationGracePeriodSeconds` deliberately. The default 30 is fine for a web service and far too short for something draining a queue. Make it a decision rather than an inherited number.
 Audit finalizers you did not add. `kubectl get pods -o json | jq '.items[] | select(.metadata.finalizers) | .metadata.name'` after uninstalling an operator is a cheap check, and uninstalled operators are where orphan finalizers come from.
 Never force-delete a StatefulSet pod as a habit. If it is routine, the real problem is the shutdown path, and you are papering over it. [...] ## The fastest check

```
kubectl get pod  -o jsonpath='{.metadata.deletionTimestamp}{"\t"}{.metadata.deletionGracePeriodSeconds}{"\t"}{.metadata.finalizers}{"\n"}' kubectl get pod  -o jsonpath='{.metadata.deletionTimestamp}{"\t"}{.metadata.deletionGracePeriodSeconds}{"\t"}{.metadata.finalizers}{"\n"}' jsonpath ='{.metadata.deletionTimestamp}{"\t"}{.metadata.deletionGracePeriodSeconds}{"\t"}{.metadata.finalizers}{"\n"}'
```

On a pod held by a finalizer, that prints something like:

```
2026-08-25T11:06:20Z 30 ["example.com/blocks-deletion"] 
```

Three fields, and they eliminate three of the four causes between them:
- [Kubernetes best practices: terminating with grace | Google Cloud Blog](https://cloud.google.com/blog/products/containers-kubernetes/kubernetes-best-practices-terminating-with-grace) — If your app finishes shutting down and exits before the terminationGracePeriod is done, Kubernetes moves to the next step immediately.

If your pod usually takes longer than 30 seconds to shut down, make sure you increase the grace period. You can do that by setting the terminationGracePeriodSeconds option in the Pod YAML. For example, to change it to 60 seconds:

### 5 - SIGKILL signal is sent to pod, and the pod is removed

If the containers are still running after the grace period, they are sent the SIGKILL signal and forcibly removed. At this point, all Kubernetes objects are cleaned up as well.

### Conclusion
- [Pods termination grace period seconds are not executed as expected. · Issue #109352 · kubernetes/kubernetes · GitHub](https://github.com/kubernetes/kubernetes/issues/109352) — 1. create the kubenetes cluster  
    `minikube start`
2. deploy the application  
    `kubectl apply -f tornado_8000.yml`
3. expose the service to local machine  
    `kubectl expose deployment tornado_8000 --type=LoadBalancer --name=tornado-service --port 8000`
4. access the service from local machine  
    `curl   
    result is: the hello world str will be printed after 35s.
5. Delete the pod  
    result is: the pod will be restarted after around 40s no matter there are have in-flight requests or not, the grace termination  
    time was expected 30s but I always see the pod was terminated around 40s.  
    request

### Anything else we need to know?

No response

### Kubernetes version

Details [...] No response

### Kubernetes version

Details

```
kubectl version paste output hereClient Version: version.Info{Major:"1", Minor:"22", GitVersion:"v1.22.4", GitCommit:"b695d79d4f967c403a96986f1750a35eb75e75f1", GitTreeState:"clean", BuildDate:"2021-11-17T15:48:33Z", GoVersion:"go1.16.10", Compiler:"gc", Platform:"darwin/amd64"}Server Version: version.Info{Major:"1", Minor:"23", GitVersion:"v1.23.3", GitCommit:"816c97ab8cff8a1c72eccca1026f7820e93e0d25", GitTreeState:"clean", BuildDate:"2022-01-25T21:19:12Z", GoVersion:"go1.17.6", Compiler:"gc", Platform:"linux/amd64"}
```

### Cloud provider

Details no cloud provider 

### OS version

Details [...] ```
- [Achieving Graceful Pod Termination in Production ...](https://www.linkedin.com/pulse/achieving-graceful-pod-termination-production-kubernetes-ajay-pawar-cgzff) — The default Kubernetes termination process can be aggressive. By default, Kubernetes gives Pods only 30 seconds to shut down gracefully. This