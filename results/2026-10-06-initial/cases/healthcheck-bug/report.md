# Root cause: Checkout pod failing probes due to healthcheck logic bug in new deployment

Service `checkout` in namespace `shop`.

## Root cause
The healthcheck endpoint (/healthz) returns HTTP 500 because the application's healthcheck logic incorrectly rejects the valid DB_HOST value (orders-db.shop.svc.cluster.local) as 'outside cluster domain' when it actually ends with the expected suffix (.shop.svc.cluster.local). This bug exists in the new ReplicaSet (pod-template-hash=76bd4cbff7) but not in the old one (9bd4d689f), as evidenced by different image SHAs.

## Mechanism
1. New ReplicaSet 76bd4cbff7 rolls out with a buggy healthcheck: the condition `if db_host.endswith(EXPECTED_DB_SUFFIX):` should be negated, so a correct DB_HOST triggers a 500 response. 2. Liveness probe (delay=5s, period=10s, failureThreshold=3) and readiness probe (delay=2s, period=5s, failureThreshold=3) both hit /healthz and receive 500. 3. After three consecutive liveness failures (~30s), kubelet kills the container (SIGKILL, exit code 137, Reason: Error) and restarts it — the 'OOMKilled' label in triage is a mischaracterization; exit 137 here is from probe-driven kill, not memory pressure. 4. The replacement container runs the same buggy image, so probes continue to fail, leaving the pod stuck at 0/1 Ready while the two healthy pods on the old ReplicaSet serve 200.

Confidence: 0.95 · Labels: probe_config, image_tag, healthcheck_bug, rolling_deployment

## Evidence relied on
- healthcheck code: `if db_host.endswith(EXPECTED_DB_SUFFIX): problems.append(...)` — inverted logic
- logs: failing pod shows repeated 'GET /healthz HTTP/1.1" 500 -' while healthy pods show 200
- events: 'Container checkout failed liveness probe, will be restarted' at 55s ago
- describe: failing pod Last State Reason=Error Exit Code=137; healthy pods Ready=True
- image IDs differ: failing pod sha256:2a5097d2... vs healthy pods sha256:4c1ea449...
- probe config: liveness/readiness both HTTP GET /healthz with low thresholds

## Tavily sources
Queries: Kubernetes OOM kill exit code 137 memory limit 512Mi startup cache 96Mi pod restart; Kubernetes liveness probe readiness probe HTTP 500 /healthz checkout service memory pressure; Kubernetes pod continuous 500 healthz probe failures after OOM kill memory limit insufficient
- [Exit Code 137 in Kubernetes: Causes, Diagnosis, and Fixes](https://middleware.io/blog/exit-code-137-in-kubernetes-causes-diagnosis-fixes) — Exit code 137 means Kubernetes killed a container with SIGKILL (128 + 9), almost always because the Linux OOM killer stepped in to free memory.
 Common causes are OOM conditions, memory limits set too low, memory leaks or spikes, and containers failing repeated health checks.
 Forced kills can corrupt in-flight writes, drop active sessions, and hide real memory needs, leading teams to under-provision resources afterward.
 Diagnosing it means checking pod logs with kubectl logs, node metrics with kubectl describe node, and a monitoring tool to spot the pattern.
 Fixes include raising memory requests and limits, fixing memory leaks in the app itself, and tuning liveness/readiness probe timing so healthy pods aren’t killed prematurely.
- [What Exit Code 137 means for Kubernetes | Refine](https://refine.dev/blog/kubernetes-exit-code-137) — ### How Kubernetes pods display this exit code​

Kubernetes can kill any container in the cluster when it reaches its memory limit and mark it with the 'OOMKilled' status, which means that the process was killed due to an 'out-of-memory' condition. The exit code for this error is 137. Your pods may experience this issue with their status labeled as 'OOMKilled' that can be viewed using the command `kubectl get pods`.

### Importance of the OOMKilled status in Kubernetes​
- [Exit Code 137 in Kubernetes: Causes & Fixes (2026)](https://www.nudgebee.com/resources/blog/fixing-exit-code-137-pod-termination-kubernetes) — ## How to Fix OOMKilled and Exit Code 137 (Step-by-Step)

### Increase Pod Memory Limits

Update your deployment:

Adjust your deployment YAML to allocate more memory.

code

```
resources: requests: memory: "512Mi" limits: memory: "1Gi"
```

Best for:

 stable apps needing more memory

Be careful:

 don’t over-allocate → node crash risk

### 2. Fix Memory Leaks (Important)

If memory keeps increasing:

👉 You need to fix code, not infra

Use tools:

 pprof
 heap dumps
 Prometheus metrics

Check:

 large objects
 open connections
 unnecessary caching

### 3. Use Vertical Pod Autoscaler (VPA)

Automatically adjusts memory

Best for:

 unpredictable workloads

### 4. Monitor Memory Usage

Don’t wait for crash.

Use:

kubectl top pods

Or:

 Prometheus
 Grafana

Set alerts when usage > 80% [...] In short: OOMKilled is one specific cause of exit code 137, and eviction is Kubernetes acting a layer higher, at the node, before any single container's OOM killer gets involved.

Fix OOM at the Source

Limits, leaks, or node pressure.

Book a demo  Free on GitHub

## Why does Exit Code 137 happen in Kubernetes?

Here are the most common reasons:

### 1. Memory limit is too low

Your pod has a limit like:

code

```
resources: limits: memory: "512Mi"
```

👉 If your app needs more → it crashes

### 2. Memory leak in application

Your app keeps consuming memory:

 unclosed connections
 large caches
 inefficient loops

👉 Eventually → exceeds limit → killed

### 3. Node memory pressure

Even if your pod is fine:

👉 Node doesn’t have enough memory

👉 Kubernetes kills pods to survive [...] OOMKilled: the container itself exceeded its own memory limit. The kernel's OOM killer inside that container's cgroup kills the process, and Kubernetes reports Reason: OOMKilled with exit code 137.
 Exit code 137: the exit code itself, not a cause. It means SIGKILL. OOMKilled is the most common reason a container exits with 137, but a container can also be force-killed by a manual kubectl delete --force, or by exceeding its termination grace period during a rolling update, so 137 alone doesn't prove memory was the problem.
- [Kubernetes OOMKilled and Exit Code 137: Fix Guide | Webalert](https://web-alert.io/blog/kubernetes-oomkilled-exit-code-137-memory-limits-guide) — Skip to content

kubernetes oomkilled containers debugging memory troubleshooting

# Kubernetes OOMKilled (Exit Code 137): Causes and Fixes

Why Kubernetes kills pods with OOMKilled and exit code 137, how memory requests and limits cause it, and how to diagnose and fix out-of-memory restarts.

Webalert Team

Published

Updated 

6 min read

A container that was running fine suddenly restarts, and `kubectl describe pod` shows `Last State: Terminated`, `Reason: OOMKilled`, `Exit Code: 137`. No stack trace, no application error—the process was killed from underneath the app. This usually means Linux cgroup OOM handling killed a process after the container exceeded its memory limit. Exit code 137 alone is not proof of OOM, but `Reason: OOMKilled` is the decisive signal. [...] `OOMKilled` is one of the most common reasons pods restart, and unlike a code crash it leaves almost no trace in your application logs. This guide explains what's happening, why exit code 137 appears, and how to diagnose and fix out-of-memory kills for good.

## What OOMKilled and Exit Code 137 Mean

OOM stands for Out Of Memory. When a container exceeds its memory limit, the Linux kernel's OOM killer steps in and sends the process a `SIGKILL` — an immediate, unblockable termination. Kubernetes reports this as `OOMKilled`. [...] Two distinct OOM scenarios follow from this:

1. Container exceeds its own limit. The most common case: your container's `limit` is 512Mi, it tries to use 600Mi, and it's killed. This is a per-container limit kill.
2. Node runs out of memory. Under node memory pressure, kubelet may evict pods according to eviction signals and QoS/priority, or the kernel may invoke its system OOM killer before kubelet can react. This is distinct from a container exceeding its own cgroup limit, and the pod status and events can differ.
- [Exit Code 137 - Fixing OOMKilled Kubernetes Error](https://spacelift.io/blog/oomkilled-exit-code-137) — ```
kubectl describe pod < podname>
```

```
State: Running  Started: Fri, 12  May 2023  11:14:13 +0200  Exit Code: 137   ...
```

Use `kubectl logs`  to get logs, or inspect logs using container runtime tools (like `crictl logs`) if you have direct node access.

Check out also how to view Kubernetes pod logs files with kubectl.

### Step 2: Analyze resource limits

Inspect the pod definition and compare the memory limit to actual usage from monitoring tools:

```
resources:  memory: "512Mi"
```

### Step 3: Check usage over time

Use Kubernetes monitoring tools such as Prometheus and Grafana, or `kubectl top pod` to see memory usage patterns. This can help you identify which containers are consuming too much memory and triggering the OOMKilled error. [...] ## What is the OOMKilled Kubernetes error (exit code 137)?

In Kubernetes, when a container uses more memory than its assigned `memory limit`, the Linux Out-Of-Memory (OOM) killer forcibly stops the process. This results in the container exiting with code 137, which corresponds to `SIGKILL (signal 9) + 128`. The container is then marked as `OOMKilled` in the Pod’s status.

This often happens when:

 The container exceeds its memory limit (as set in resources.limits.memory), triggering an OOMKill.
 The node runs critically low on memory, and the kernel OOMKiller terminates one or more containers.

To resolve it, either optimize memory usage or increase the container’s memory limit. Monitoring with tools like Prometheus or using `kubectl describe pod` can help identify patterns. [...] If you want to learn more about Spacelift, create a free account today or book a demo with one of our engineers.

## Key points

OOM Killed in Kubernetes with Exit Code 137 means a container was terminated because it exceeded its memory limit.

To avoid the OOMKilled error, it is recommended to monitor memory usage in Kubernetes pods and containers, set resource limits to prevent containers from consuming too much memory, and optimize application code to reduce memory consumption.

Additionally, consider increasing the memory resources allocated to the pod or using horizontal pod autoscaling to scale up the number of pods in response to increased workload demands.

### The most flexible CI/CD automation tool
- [Creating Kubernetes liveness and readiness probes | Opensource.com](https://opensource.com/article/18/3/kubernetes-liveness-readiness-probes) — Title: Creating Kubernetes liveness and readiness probes | Opensource.com
# Creating Kubernetes liveness and readiness probes. Keep your Kubernetes containers running smoothly with these self-healing probes. The kubelet uses liveness probes to know when to restart a container. The kubelet uses readiness probes to know when a container is ready to start accepting traffic. ## Kubernetes liveness probes. Kubernetes can probe the container in three ways:. The following YAML listing creates a pod that includes an HTTP GET liveness probe:. apiVersion: v1 kind: Pod metadata: labels: test: liveness name: liveness-http spec: containers: - name: liveness image: k8s.gcr.io/liveness args: - /server livenessProbe: httpGet: path: /healthz port: 8080 httpHeaders: - name: X-Custom-Header value: Awesome initialDelaySeconds: 3 periodSeconds: 3. The pod descriptor defines an `httpGet` liveness probe, which tells Kubernetes to periodically perform HTTP Get requests on path `/healthz`  on Port `8080` to determine if the container is still healthy. The following YAML listing creates a pod that includes a TCP socket liveness probe:. The following YAML listing creates a pod that includes an Exec liveness probe:. apiVersion: v1 kind: Pod metadata: labels: test: liveness name: liveness-exec spec: containers: - name: liveness image: k8s.gcr.io/busybox args: - /bin/sh - -c - touch /tmp/healthy; sleep 30; rm -rf /tmp/healthy; sleep 600 livenessProbe: exec: command: - cat - /tmp/healthy initialDelaySeconds: 5 periodSeconds: 5. ## Kubernetes readiness probes. The following YAML listing creates a pod that includes an HTTP Get readiness probe:. apiVersion: v1 kind: Pod metadata: labels: test: readiness name: readiness-http spec: containers: - name: readiness image: k8s.gcr.io/liveness args: - /server readinessProbe: httpGet: path: /healthz port: 8080 httpHeaders: - name: X-Custom-Header value: Awesome initialDelaySeconds: 3 periodSeconds: 3. The following YAML listing creates a pod that includes a TCP socket readiness probe:. The following YAML listing creates a pod that includes an Exec readiness probe:. apiVersion: v1 kind: Pod metadata: labels: test: readiness name: readiness-exec spec: containers: - name: readiness image: k8s.gcr.io/busybox args: - /bin/sh - -c - touch /tmp/healthy; sleep 30; rm -rf /tmp/healthy; sleep 600 readinessProbe: exec: command: - cat - /tmp/healthy initialDelaySeconds: 5 periodSeconds: 5. Kubernetes keeps your containers running by restarting them if they crash or if their liveness probes fail.
- [Kubernetes Probes Liveness Readiness | K8s Recipes](https://kubernetes.recipes/recipes/deployments/kubernetes-liveness-readiness-startup-probes) — Title: Kubernetes Probes Liveness Readiness | K8s Recipes
# Kubernetes Probes Liveness Readiness. Configure liveness, readiness, and startup probes in Kubernetes. HTTP, TCP, exec, and gRPC probe types with real-world tuning for production workloads. > 💡 **Quick Answer:** Three probe types: **Liveness** (restart if dead), **Readiness** (remove from Service if not ready), **Startup** (protect slow-starting containers). Use HTTP GET for web apps, TCP for databases, exec for custom checks. ### Liveness Probe (Is it alive?). containers: containers: - name: web - name: web livenessProbe:  livenessProbe: httpGet:  httpGet: path: /healthz  path: /healthz port: 8080  port: 8080 initialDelaySeconds: 15  initialDelaySeconds: 15 periodSeconds: 10  periodSeconds: 10 timeoutSeconds: 3  timeoutSeconds: 3 failureThreshold: 3 # 3 failures = restart  failureThreshold: 3 # 3 failures = restart successThreshold: 1  successThreshold: 1. ### Readiness Probe (Can it serve traffic?). containers: containers: - name: web - name: web readinessProbe:  readinessProbe: httpGet:  httpGet: path: /ready  path: /ready port: 8080  port: 8080 initialDelaySeconds: 5  initialDelaySeconds: 5 periodSeconds: 5  periodSeconds: 5 timeoutSeconds: 3  timeoutSeconds: 3 failureThreshold: 3 # 3 failures = remove from Service  failureThreshold: 3 # 3 failures = remove from Service successThreshold: 1  successThreshold: 1. ### Startup Probe (Is it still starting?). containers: containers: - name: legacy-app - name: legacy-app startupProbe:  startupProbe: httpGet:  httpGet: path: /healthz  path: /healthz port: 8080  port: 8080 initialDelaySeconds: 0  initialDelaySeconds: 0 periodSeconds: 10  periodSeconds: 10 failureThreshold: 30 # 30 × 10s = 300s max startup time  failureThreshold: 30 # 30 × 10s = 300s max startup time livenessProbe:  livenessProbe: httpGet:  httpGet: path: /healthz  path: /healthz port: 8080  port: 8080 periodSeconds: 10 # Only starts after startup probe succeeds  periodSeconds: 10  # Only starts after startup probe succeeds. (lightweight, no deps) livenessProbe:  livenessProbe: httpGet:  httpGet: path: /healthz  path: /healthz port: 8080  port: 8080 periodSeconds: 10  periodSeconds: 10 timeoutSeconds: 3  timeoutSeconds: 3 failureThreshold: 3  failureThreshold: 3    # Can it serve requests? (check deps here) readinessProbe:  readinessProbe: httpGet:  httpGet: path: /ready  path: /ready port: 8080  port: 8080 periodSeconds: 5  periodSeconds: 5 timeoutSeconds: 3  timeoutSeconds: 3 failureThreshold: 3  failureThreshold: 3. **No startup probe on slow apps**. #probes #health-checks #liveness #readiness #startup.
- [Kubernetes Probes: Readiness, Liveness, and Startup Checks | by E Behrangi | Medium](https://medium.com/@elahe.behrangi/beginners-guide-to-kubernetes-probes-readiness-liveness-and-startup-checks-10731bac57d6) — Title: Kubernetes Probes: Readiness, Liveness, and Startup Checks | by E Behrangi | Medium
# Kubernetes Probes: Readiness, Liveness, and Startup Checks. In Kubernetes, probes are how the system checks the health of your containers, making decisions like:bShould this pod receive traffic? Should Kubernetes restart this pod? In this article, we’ll break down **liveness**, **readiness**, and **startup** probes, and show how to configure them properly for real-world apps. What Are Probes in Kubernetes? A probe is an action Kubernetes performs periodically against a container to check its health or readiness. Join Medium for free to get updates from this writer. There are three types of probes:. **Readiness Probe:** Checks if the container is ready to serve traffic. **Liveness Probe:** Checks if the container is still alive (otherwise restart it). **Startup Probe:**Special probe for slow-starting applications; delays liveness/readiness checks. ### Readiness Probe. * Kubernetes uses the **readiness probe** to decide whether to send requests to a pod. * If the readiness probe fails, Kubernetes removes the pod from the Service endpoints temporarily. readinessProbe:  httpGet:    path: /healthz/ready    port: 8080  initialDelaySeconds: 5  periodSeconds: 10  timeoutSeconds: 2  failureThreshold: 3readinessProbe:httpGet:path:/healthz/readyport: 8080initialDelaySeconds: 5periodSeconds: 10timeoutSeconds: 2failureThreshold: 3. Kubernetes will check `/healthz/ready` on port 8080 every 10 seconds, starting 5 seconds after the container launches. ### Liveness Probe. * Kubernetes uses the **liveness probe** to detect when a container has entered a broken state. * If the liveness probe fails, Kubernetes restarts the container automatically. livenessProbe:  httpGet:    path: /healthz/live    port: 8080  initialDelaySeconds: 15  periodSeconds: 20  timeoutSeconds: 3  failureThreshold: 5livenessProbe:httpGet:path:/healthz/liveport: 8080initialDelaySeconds: 15periodSeconds: 20timeoutSeconds: 3failureThreshold: 5. Kubernetes will restart the pod if `/healthz/live` fails 5 times in a row. ### Startup Probe. * **Startup probes** are used instead of liveness during container startup. * Kubernetes disables liveness and readiness probes until the startup probe succeeds. Kubernetes will allow up to 5 minutes (30 x 10 seconds) for your app to start before considering it failed. ### Probe Types (HTTP, TCP, Command). Kubernetes supports three kinds of probes:. ### Key Probe Settings. **initialDelaySeconds:** How long to wait after container starts before probing begins. **periodSeconds:** How often to perform the probe. **timeoutSeconds:** How long to wait for a probe to succeed before considering it failed. Probes are crucial to running resilient applications in Kubernetes. ## Recommended from Medium.
- [Kubernetes — Liveness and Readiness Probes — Difference](https://medium.com/@AADota/kubernetes-liveness-and-readiness-probes-difference-1b659c369e17) — # Kubernetes — Liveness and Readiness Probes — Difference 3 min readJun 20, 2019 Liveness and Readiness probes are used to control the health of an application running inside a Pod’s container. ## Liveness Probe Suppose that a Pod is running our application inside a container, but due to some reason let’s say memory leak, cpu usage, application deadlock etc the application is not responding to our requests, and stuck in error state. We can define liveness probe in 3 ways: ### Liveness command apiVersion: v1kind: Podmetadata: labels: test: liveness name: liveness-execspec: containers: - name: liveness image: /busybox args: - /bin/sh - -c - touch /tmp/healthy; sleep 30; rm -rf /tmp/healthy; sleep 600 livenessProbe: exec: command: - cat - /tmp/healthy initialDelaySeconds: 3 periodSeconds: 5 We are creating a container with name **liveness**, and as the container initialise we use the following command: - touch /tmp/healthy; sleep 30; rm -rf /tmp/healthy; sleep 600 to create a file **healthy** at path **/tmp/healthy**, and delete it after 30 seconds. exec: command: - cat - /tmp/healthy This commands tell the liveness probe to open file at path **/tmp/healthy**, and if it can’t the liveness probe will fail and container will restart. ### Liveness HTTP request livenessProbe: httpGet: path: /healthz port: 8080 initialDelaySeconds: 3 periodSeconds: 3 In this case the kubelet will send **HTTP GET** request to **/healthz** endpoint at port **8080** of the application running inside the container. ### TCP Liveness probe livenessProbe: tcpSocket: port: 8080 initialDelaySeconds: 15 periodSeconds: 20 In this case the kubelet will try to open a tcp socket at port 8080 in container running the application. If it succeeds the application will be considered healthy, otherwise the probe will fail, and the container will restart. ## Readiness Probe In some cases we would like our application to be alive, but not serve traffic unless some conditions are met e.g, populating a dataset, waiting for some other service to be alive etc. We just need to replace **livenessProbe** with **readinessProbe** like this: readinessProbe: exec: command: - cat - /tmp/healthy initialDelaySeconds: 5 periodSeconds: 5 ## Summary Both liveness & readiness probes are used to control the health of an application. Failing liveness probe will restart the container, whereas failing readiness probe will stop our application from serving traffic.
- [Kubernetes Readiness, Liveness and Startup Probes | Cloudiaries](https://cloudiaries.com/posts/kubernetes-readiness-liveness-startup-probes) — Title: Kubernetes Readiness, Liveness and Startup Probes | Cloudiaries
# Kubernetes Readiness, Liveness and Startup Probes. * And if we have an application that has a long-running initialization process, we want the `kubelet` to be patient and give it enough time to perform its initialization, before checking if it is live and ready ⇒ Startup probes. These probes are defined for each container of the pod. Liveness probes are used to perform checks on the container, to make sure it is running. if the probe fails, the container is killed by the `kubelet` and will get restarted following the defined restartPolicy in the pod `spec`. The pod will start and will show as running (Readiness Probes are successful). kubectl describe po podinfo-777f58f87f-l5rdp kubectl describe po podinfo-777f58f87f-l5rdp #[...] #[...] #[...]Events: Events:  Type Reason Age From Message  Type Reason Age From Message  ---- ------ ---- ---- -------  ---- ------ ---- ---- ------- #[...] #[...] #[...] Warning Unhealthy 42s kubelet Liveness probe failed: 2023-04-15T09:59:48.039Z INFO podcli/check.go:137 check failed {"address": "http://localhost:9898/healthz", "status code": 503}  Warning Unhealthy 42s kubelet Liveness probe failed: 2023-04-15T09:59:48.039Z INFO podcli/check.go:137 check failed {"address": "http://localhost:9898/healthz", "status code": 503} {"address""http://localhost:9898/healthz" "status code"} Warning Unhealthy 30s kubelet Liveness probe failed: 2023-04-15T10:00:00.042Z INFO podcli/check.go:137 check failed {"address": "http://localhost:9898/healthz", "status code": 503}  Warning Unhealthy 30s kubelet Liveness probe failed: 2023-04-15T10:00:00.042Z INFO podcli/check.go:137 check failed {"address": "http://localhost:9898/healthz", "status code": 503} {"address""http://localhost:9898/healthz" "status code"} Warning Unhealthy 22s kubelet Liveness probe failed: 2023-04-15T10:00:08.029Z INFO podcli/check.go:137 check failed {"address": "http://localhost:9898/healthz", "status code": 503}  Warning Unhealthy 22s kubelet Liveness probe failed: 2023-04-15T10:00:08.029Z INFO podcli/check.go:137 check failed {"address": "http://localhost:9898/healthz", "status code": 503} {"address""http://localhost:9898/healthz" "status code"} Normal Killing 22s kubelet Container podinfo failed liveness probe, will be restarted  Normal Killing 22s kubelet Container podinfo failed liveness probe, will be restarted. Readiness probe checks if the container is ready to receive requests. A pod is ready when all of its containers are ready (successful readiness probes for all containers). The default chart performs readiness probes using a command:. When the startup probe succeeds, the liveness and readiness probes are enabled and traffic is served to the pod upon Readiness probe success. Readiness probes and Liveness probes plays different roles in the lifecycle of a pod.
- [Kubernetes scheduler liveness probe fails during OOM conditions preventing automatic restart · apache/airflow · Discussion #53662 · GitHub](https://github.com/apache/airflow/discussions/53662) — reliability and requires manual intervention, violating Kubernetes self-healing principles. The solution addresses a fundamental operational gap in the current architecture. Alternative Workarounds Current mitigation strategies:   1. Resource Limits: Set memory limits to trigger OOMKilled (bypasses probe issue) 2. External Monitoring: Deploy sidecar pods to monitor scheduler health 3. Conservative Probe Settings: Increase timeouts (doesn't solve root cause) 4. Manual Monitoring: Platform team monitoring and manual restarts   However, these workarounds don't address the fundamental design issue and require additional operational overhead.  Would the maintainers be open to a PR implementing the HTTP health endpoint approach? This seems like the most robust solution that follows Kubernetes [...] ### Monitoring Data Patterns

Memory usage: 85-95% of container limits  
Process count: Normal (scheduler process still running)  
CPU usage: Normal or slightly elevated  
Liveness probe success rate: Drops to 0% while scheduler process remains active

### Current Behavior

### Expected Behavior

Kubernetes should automatically detect unhealthy scheduler pods experiencing OOM conditions and restart them without manual intervention, ensuring high availability and operational reliability.

### Impact

### Proposed Solutions

#### 1. HTTP Health Endpoint for Liveness Probes

Add an optional lightweight HTTP health endpoint to the scheduler: [...] of memory / stuck #11365, Scheduler Memory Leak in Airflow 2.0.1 #14924, airflow workers and scheduler memory leak #28740) 2. Memory pressure threshold: Pod reaches high memory usage from processing large DAGs, task queuing, or prolonged operation 3. Below-limit memory exhaustion: Memory usage stays below Kubernetes limits (e.g., using 3.5GB of 4GB limit) but approaches system allocation limits 4. Container process continues running but system cannot spawn new processes due to memory fragmentation/pressure 5. Liveness probe exec command fails: OCI runtime exec failed: cannot allocate memory 6. Kubernetes logs probe failures but doesn't restart pod (process still running) 7. Scheduler becomes unresponsive to new DAG runs but appears "healthy" to Kubernetes 8. Manual pod deletion required
- [CrashLoopBackOff in Kubernetes: Causes and Fixes](https://cast.ai/blog/crashloopbackoff) — LimitRange objects can silently impose memory limits on pods that don’t set them explicitly. If an operator deploys a pod without a `resources.limits.memory` field, a LimitRange default (say, 128Mi) applies automatically — the pod appears to be running without limits but gets OOM-killed at 128Mi. Check before you assume the pod has no limit:

```
# Check for LimitRange objects in the namespace kubectl get limitrange -n  # See the default limits applied kubectl describe limitrange -n 
```

### Liveness and readiness probe failures [...] Step 4: Check cluster events

```
# Events sorted by time — look for OOMKill, probe failures, scheduling issues kubectl get events -n  --sort-by='.lastTimestamp'
```

Step 5: Check live resource usage

```
# Requires metrics-server kubectl top pod  -n  --containers
```

Step 6: Extract the exit code programmatically

```
# Read exit code from lastState — 137=OOMKilled, 1/2=app error, 127=command not found kubectl get pod  -n  \ -o jsonpath='{.status.containerStatuses.lastState.terminated.exitCode}'
```

Prometheus alert for proactive OOM detection: Track `container_memory_working_set_bytes` against memory limits. Alert at 80% — that’s your warning window before the kernel OOM killer fires. [...] Can OOM kills cause CrashLoopBackOff?

Yes – OOM kills are one of the most common causes. The kernel terminates the container when it exceeds its memory limit (exit code 137). Kubernetes registers the crash and restarts the container. If the limit is still too low, the container hits it again, crashes again, and the loop continues. Cast AI Workload Autoscaler detects the OOMKill event and immediately applies a corrected memory limit, breaking the cycle without manual intervention.

What kubectl command shows CrashLoopBackOff?
- [Kubernetes OOMKilled out of memory diagnosis](https://www.dynatrace.com/news/blog/kubernetes-oomkilled-out-of-memory-troubleshooting) — Looking at the resource analyses confirmed the suspicion. The following chart shows how memory usage rises to almost the defined limit of 400MB before the pod is killed off and restarted. Historical data shows this didn’t happen with the old version.

Screenshot that shows pod memory metrics indicating how k8s kills the pod when it reaches out of memory limit

Analyzing the pod memory metrics shows how Kubnernetes kills the pod when it reaches the memory limit.

## The fix: Adjust the memory settings to avoid OOMKilled errors

Armed with that knowledge, the solution was simple: Robert increased the pod’s memory limit from 400MB to 600MB so that reports didn’t run into the out-of-memory shortage.

Screenshot that shows proper sizing of k8s resources to avoid out of memory error
- [Troubleshooting Kubernetes Liveness and Readiness Probe Failures](https://resolve.ai/glossary/how-to-debug-kubernetes-probe-issues) — Get a usage snapshot from `kubectl top pod` and compare it against the limits in `kubectl describe pod`. Averaged usage near the CPU limit is a hint; the confirmation is the CFS throttling metrics (`container_cpu_cfs_throttled_periods_total`) climbing. Then raise `timeoutSeconds` to something the app can meet under load, or raise the limit.

One distinction worth keeping straight is that CPU limits throttle while memory limits kill. A container that dies with exit code 137 took a SIGKILL from somewhere, and `Reason: OOMKilled` in its last state is what confirms the memory limit rather than a probe kill.

### Dependency problems behind the health endpoint
- [Troubleshoot OOMKilled errors in AKS clusters - Azure | Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/azure/azure-kubernetes/availability-performance/troubleshoot-oomkilled-aks-clusters) — ## Handle OOMKilled for user pods

User pods might be OOMKilled due to insufficient memory limits or excessive memory consumption. Solutions include setting appropriate resource requests and limits, and engaging application vendors to investigate memory usage.

### Cause 1: User workloads may be running in a system node pool

It's recommended to create user node pools for user workloads. For more information, see: Manage system node pools in Azure Kubernetes Service (AKS).

### Cause 2: Application pod keeps restarting due to OOMkilled

This behavior might be due to the pod not having enough memory assigned
to it and it requires more, which causes the pod to constantly
restart. [...] `kubectl logs <pod-name> -n <namespace>`

If the pod restarts, check the previous logs:

`kubectl logs <pod-name> -n <namespace> --previous`

### Node logs

Review the kubelet logs on the node to see if any messages indicate that the OOM killer was triggered at the time of the issue and that the pod's memory usage reached its limit.

Alternatively, SSH into the node where the pod was running and check the kernel logs for any OOM messages. This command displays which processes the OOM killer terminated:

`chroot /host # access the node session`

`chroot /host # access the node session`

`grep -i "Memory cgroup out of memory" /var/log/syslog`

`grep -i "Memory cgroup out of memory" /var/log/syslog`

### Events [...] To solve, review request and limits documentation to understand how to modify
your deployment accordingly. For more information, see Resource Management for Pods and Containers.

`kubectl set resources deployment <deployment-name> --limits=memory=<LIMITS>Mi ---requests=memory=<MEMORY>Mi`

`kubectl set resources deployment <deployment-name> --limits=memory=<LIMITS>Mi ---requests=memory=<MEMORY>Mi`

Setting resource requests and limits to the recommended amount for the
application pod.

To diagnose, see Azure Kubernetes Service (AKS) Diagnose and Solve Problems
overview.

### Cause 3: Application running in pod is consuming excessive memory

Confirm the Memory Pressure at the pod level:

Use kubectl top to check memory usage:

`kubectl top pod <pod-name> -n <namespace>`