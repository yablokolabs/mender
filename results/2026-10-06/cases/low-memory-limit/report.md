# Root cause: checkout pod OOMKilled due to 64Mi memory limit below 96Mi startup cache requirement

Service `checkout` in namespace `shop`.

## Root cause
Deployment checkout-65bcc89cbf sets container memory limit to 64Mi, which is below the application's 96Mi startup cache allocation and the required 512Mi minimum [1][6][11].

## Mechanism
1. Pod checkout-65bcc89cbf-lg87r starts with memory limit 64Mi (request 32Mi). 2. Application initializes and allocates 96Mi cache as shown in logs: 'starting checkout service (log_level=info, db=orders-db.shop.svc.cluster.local, cache=96Mi)'. 3. This allocation exceeds the 64Mi cgroup limit. 4. Linux kernel OOM killer terminates the process with SIGKILL (exit code 137 = 128 + 9). 5. Kubernetes surfaces this as 'Reason: OOMKilled' and restarts the container. 6. Cycle repeats causing CrashLoopBackOff. Meanwhile, pods from ReplicaSet checkout-67bcb9c7f7 run with 512Mi limit and succeed.

Confidence: 0.98 · Labels: oomkilled, memory_limit, deployment_mismatch, cache_sizing, exit_code_137

## Evidence relied on
- Reason: OOMKilled, Exit Code: 137
- Limits: memory: 64Mi (failing pod) vs 512Mi (healthy pods)
- starting checkout service (log_level=info, db=orders-db.shop.svc.cluster.local, cache=96Mi)
- MIN_MEMORY_LIMIT_MIB = 512 (startup cache alone is 96Mi)
- Exit code 137 = 128 + SIGKILL (signal 9) [11]

## Tavily sources
Queries: Kubernetes OOMKilled CrashLoopBackOff memory limit 64Mi insufficient startup cache 96Mi; Kubernetes deployment memory limit misconfiguration OOMKilled pod restart loop known issues; container memory limit below application startup requirements OOMKilled exit code 137 documented causes
- [Kubernetes CrashLoopBackOff After Changing Resource Limits — Fix | DevOpsBoys](https://devopsboys.com/blog/kubernetes-crashloopbackoff-after-resource-limits-fix-2026) — ## Case 1: OOMKilled (Most Common)

bash

```
kubectl describe pod my-app-xxx -n production kubectl  describe  pod my-app-xxx -n  production# ...# ...# Last State: Terminated# Last State: Terminated# Reason: OOMKilled# Reason: OOMKilled# Exit Code: 137# Exit Code: 137
```

Fix: Increase memory limit. Rule of thumb — set limit at 2x your observed peak usage.

yaml

```
resources: resources: requests:  requests: memory: "256Mi"  memory: "256Mi" cpu: "100m"  cpu: "100m" limits:  limits: memory: "512Mi" # was 256Mi — doubled it  memory: "512Mi"  # was 256Mi — doubled it cpu: "500m"  cpu: "500m"
```

For Java apps, memory usage at startup can be 3–4x steady state. Always check startup memory separately:

bash [...] # Check why pod is crashing # Check why pod is crashingkubectl describe pod <pod-name> -n <namespace> kubectl  describe  pod <pod-name> -n < namespace>  # Look for these in the output:# Look for these in the output:# State: Terminated# State: Terminated# Reason: OOMKilled ← memory too low# Reason: OOMKilled ← memory too low# Exit Code: 137 ← OOMKilled# Exit Code: 137 ← OOMKilled# Exit Code: 1 ← app crashed (check logs)# Exit Code: 1 ← app crashed (check logs)  # Check actual resource usage before crash # Check actual resource usage before crashkubectl top pod <pod-name> -n <namespace> kubectl  top  pod <pod-name> -n < namespace>  # Check logs from the PREVIOUS container run # Check logs from the PREVIOUS container runkubectl logs <pod-name> -n <namespace> --previous kubectl  logs [...] ## Why Resource Limit Changes Cause CrashLoopBackOff

When you change resource limits, Kubernetes kills and restarts affected pods with the new constraints. If the new limits are too low, the container crashes immediately — triggering the backoff loop.

Three things kill your container after a limit change:

1. OOMKilled — Memory limit is too low, kernel kills the process  
 2. CPU throttling so severe the app times out — Liveness probe fails, container restarts  
 3. JVM / runtime startup fails — Java apps need memory headroom at startup, not just steady state

## Diagnose First

bash
- [How to Debug CrashLoopBackOff and OOMKilled Pods in Kubernetes](https://oneuptime.com/blog/post/2026-01-06-kubernetes-debug-crashloopbackoff-oomkilled/view) — ### Step 2: Check Memory Usage

`# Current usage
kubectl top pod <pod-name> -n <namespace>
# Check limits
kubectl get pod <pod-name> -o jsonpath='{.spec.containers[].resources}'`

### Step 3: Common Causes and Fixes

#### Cause 1: Memory Limit Too Low

Fix: Increase memory limit based on actual usage

`# Check what the pod actually needs
kubectl top pods -n <namespace> --containers`
`resources:
requests:
memory: 256Mi
limits:
memory: 512Mi # Increase this`

#### Cause 2: Memory Leak in Application

Symptoms: Memory usage grows over time until OOM

Fix: Profile the application, fix the leak

`# Watch memory over time
watch kubectl top pod <pod-name>`

#### Cause 3: JVM Heap Configuration

Symptoms: Java apps ignoring container limits

Fix: Set JVM heap explicitly [...] ### Step 4: Calculate Right Memory Limit

`# Collect metrics over time
kubectl top pods -n <namespace> --containers | tee -a memory-metrics.txt
# After collecting enough data, find P99
# With --containers the columns are: POD NAME CPU(cores) MEMORY(bytes)
cat memory-metrics.txt | awk '{print $4}' | sort -n | tail -1`

Set limit to P99 + 20% buffer:

`resources:
requests:
memory: 256Mi # P50 usage
limits:
memory: 384Mi # P99 + buffer`

## Prevention Strategies

### Set Resource Requests and Limits

`resources:
requests:
cpu: 100m
memory: 256Mi
limits:
cpu: 500m
memory: 512Mi`

### Use Quality of Service Classes

Guaranteed (requests = limits): Highest priority, last to be killed

`resources:
requests:
cpu: 500m
memory: 512Mi
limits:
cpu: 500m
memory: 512Mi` [...] Fix: Set JVM heap explicitly

`env:
- name: JAVA_OPTS
value: "-Xmx384m -Xms256m"
# Or use container-aware options (Java 10+)
- name: JAVA_OPTS
value: "-XX:+UseContainerSupport -XX:MaxRAMPercentage=75.0"`

#### Cause 4: Node Memory Pressure

Symptoms: Multiple pods OOMKilled across the node

`# Check node conditions
kubectl describe node <node-name> | grep -A 5 "Conditions"
# Check memory pressure
kubectl get nodes -o custom-columns=NAME:.metadata.name,MEM:.status.conditions[?(@.type==\"MemoryPressure\")].status`

Fix: Add more nodes, reduce workload, or evict low-priority pods

### Step 4: Calculate Right Memory Limit
- [How to Fix CrashLoopBackOff in Kubernetes? - Komodor](https://komodor.com/learn/how-to-fix-crashloopbackoff-kubernetes-error) — OOMKilled (often exit code 137) indicates the container was killed due to memory limits or node memory pressure. Look for “OOMKilled” in the container status and Events, then adjust memory requests/limits and investigate memory spikes or leaks.

```
kubectl describe pod  # look for Reason: OOMKilled / Exit Code: 137 kubectl logs  -c  --previous 
```

This usually means the Pod references a ConfigMap or Secret that doesn’t exist (wrong name, wrong namespace, or missing key). The exact missing object is typically listed in Events.

```
kubectl describe pod  kubectl get configmap,secret -n  
```
- [CrashLoopBackOff in Kubernetes: Causes and Fixes](https://cast.ai/blog/crashloopbackoff) — Can OOM kills cause CrashLoopBackOff?

Yes – OOM kills are one of the most common causes. The kernel terminates the container when it exceeds its memory limit (exit code 137). Kubernetes registers the crash and restarts the container. If the limit is still too low, the container hits it again, crashes again, and the loop continues. Cast AI Workload Autoscaler detects the OOMKill event and immediately applies a corrected memory limit, breaking the cycle without manual intervention.

What kubectl command shows CrashLoopBackOff? [...] Automate memory rightsizing. Manual limits drift. Cast AI Workload Autoscaler tracks actual memory usage continuously and keeps limits calibrated. Its OOM event handler closes the feedback loop between a kill event and a corrected limit without requiring an engineer to notice, diagnose, and redeploy. At 240 changes per hour across a fleet, it handles scale that VPA alone cannot.

Use OpsPilot for real-time diagnosis. When a CrashLoopBackOff alert fires at 2am, OpsPilot gives you root cause in seconds: “payments-api has restarted 14 times in 2 hours. Root cause: OOMKilled — memory limit 256Mi, peak RSS 312Mi at v2.3.9 rollout.” That’s the full diagnostic loop compressed into one response, with the specific version and memory figures you need to act. [...] LimitRange objects can silently impose memory limits on pods that don’t set them explicitly. If an operator deploys a pod without a `resources.limits.memory` field, a LimitRange default (say, 128Mi) applies automatically — the pod appears to be running without limits but gets OOM-killed at 128Mi. Check before you assume the pod has no limit:

```
# Check for LimitRange objects in the namespace kubectl get limitrange -n  # See the default limits applied kubectl describe limitrange -n 
```

### Liveness and readiness probe failures
- [Kubernetes CrashLoopBackOff: Causes, Diagnosis, and Fixes](https://middleware.io/blog/kubernetes-crashloopbackoff-causes-diagnosis-and-fixes) — Use `kubectl top pod` over several hours under normal load to find actual peak usage, then set the limit to 1.5 to 2x that value as headroom. See our OOMKilled guide and exit code 137 guide for the full approach to right-sizing memory.

### Fix 4: Fix a misconfigured liveness probe

```
livenessProbe: httpGet: path: /health port: 8080 initialDelaySeconds: 30 # increase: give the app time to start periodSeconds: 10 timeoutSeconds: 5 # increase if your health check is slow failureThreshold: 3 # increase: don't kill on first slow response
```

Use a startup probe instead of relying on `initialDelaySeconds` for slow-starting applications:

```
startupProbe: httpGet: path: /health port: 8080 failureThreshold: 30 # 30 x 10s = 5 minutes max startup time periodSeconds: 10
``` [...] Fix the code bug or configuration file the application is failing to read
 Ensure the container image contains all files the application expects at startup
 Add proper startup error handling so the application logs a clear error before exiting

### Fix 2: Missing or misconfigured Secrets/ConfigMaps

```
# Check Secret exists kubectl get secret  -n  # Check ConfigMap exists kubectl get configmap  -n  # Check what keys the Secret actually contains kubectl get secret  -o jsonpath='{.data}' | base64 -d
```

To create a missing Secret:

```
kubectl create secret generic  --from-literal=DATABASE_URL=postgres://user:pass@host:5432/db -n 
```

### Fix 3: OOMKilled: increase memory limit

```
kubectl set resources deployment/ --limits=memory=512Mi --requests=memory=256Mi
``` [...] CrashLoopBackOff means a container in your pod is starting, crashing, and being restarted in a loop. It is a pod state, not a single error.
 Kubernetes applies exponential backoff between each restart attempt: 10s, 20s, 40s, 80s, 160s, capped at 300s (5 minutes), to prevent resource exhaustion.
 The real error is always in the container logs or Events. CrashLoopBackOff itself is only the symptom.
 The six most common causes: application error on startup, misconfigured or missing environment variables/secrets, OOMKilled (memory limit too low), failing liveness probe, missing or unavailable dependency, and incorrect container command or entrypoint.
 Fastest diagnosis path: kubectl describe pod  to read Events, then kubectl logs  –previous to read the last crash output.
- [Why Pods Get OOMKilled in Kubernetes (And Why Memory Limits Won’t Save You)](https://medium.com/@pillarslive/why-pods-get-oomkilled-in-kubernetes-and-why-memory-limits-wont-save-you-5891b8f338ea) — The sequence looks like this:

1.   The application allocates memory normally;
2.   The Linux kernel tracks memory usage via cgroups;
3.   Memory usage approaches the limit (1.9GB, 1.95GB, 1.99GB…);
4.   One more allocation is attempted;
5.   The kernel determines the limit would be exceeded;
6.   The OOM Killer terminates the process;
7.   Kubernetes restarts the container;
8.   The cycle begins again.

## Java and Node.js Memory Behavior in Containers

Node.js made the issue harder to diagnose. The V8 engine manages its own heap and garbage collection. By default, it tries to use as much memory as the system appears to have available. [...] ## The Incident

The incident started like most do: at 3 a.m., a PagerDuty alert — the order processing service was down again. The on-call engineer opened a laptop and checked the Kubernetes dashboard. The pattern was familiar: pods were restarting every few minutes, and the logs showed the same message the team had already seen several times before:

`OOMKilled: Container was killed due to memory pressure`

Memory limits were set. They had always been set. But that, it turned out, was not enough.

A memory limit does not prevent a container from running out of memory. It defines the point at which the container can be killed. In some cases, setting limits too close to real usage can make OOMKills more frequent, not less. [...] When Node.js runs inside a container with a `2Gi` memory limit, the V8 runtime may not size its heap conservatively enough for that limit unless explicitly configured, depending on the Node.js and V8 version. It sees the host’s total memory and assumes it has far more room to grow. The heap can expand to `1.8GB` while total container memory usage (heap, buffers, caches, everything else) crosses the `2Gi` threshold — triggering an OOMKill.

Java has the same problem, with an additional layer of complexity. The JVM heap is only part of total memory usage:
- [Kubernetes OOMKilled out of memory diagnosis](https://www.dynatrace.com/news/blog/kubernetes-oomkilled-out-of-memory-troubleshooting) — Looking at the resource analyses confirmed the suspicion. The following chart shows how memory usage rises to almost the defined limit of 400MB before the pod is killed off and restarted. Historical data shows this didn’t happen with the old version.

Screenshot that shows pod memory metrics indicating how k8s kills the pod when it reaches out of memory limit

Analyzing the pod memory metrics shows how Kubnernetes kills the pod when it reaches the memory limit.

## The fix: Adjust the memory settings to avoid OOMKilled errors

Armed with that knowledge, the solution was simple: Robert increased the pod’s memory limit from 400MB to 600MB so that reports didn’t run into the out-of-memory shortage.

Screenshot that shows proper sizing of k8s resources to avoid out of memory error [...] Header background

# Kubernetes OOMKilled troubleshooting: Diagnosing out-of-memory issues automatically

Published  Updated  7 min read

Andreas Grabner

  Andreas Grabner

DevOps Cloud native Engineering Infrastructure

Anyone who has struggled with Kubernetes OOMKilled (out of memory) issues knows how frustrating they can be to debug.

Kubernetes has a lot of built-in capabilities to ensure your workloads get enough CPU and memory to stay healthy. However, misconfiguration is a common reason why Kubernetes might kill pods despite the workload just doing fine and all your Kubernetes nodes still having enough free resources.
- [Debugging Kubernetes OOMKilled (Exit Code 137): A Root Cause Guide](https://resolve.ai/glossary/how-to-debug-kubernetes-OOMKilled-errors) — For critical workloads, requests equal to limits removes the ambiguity. The pod either schedules with its memory reserved, or it doesn't schedule at all.

## Why are memory issues hard to debug?

The restart is the trap. Auto-recovery means the service is back before anyone investigates, the root cause survives, and the kill returns at the next traffic peak, usually off-hours.

The signal is also split across systems. Usage history lives in Prometheus, the kill itself in kernel logs on the node, and the trigger in a deployment or traffic change somewhere upstream. `kubectl` shows you that it happened, rarely why. [...] ## What are the three types of OOM in Kubernetes?

Memory failures come in three shapes. Two normally produce the OOMKilled status; the third looks related and shows up somewhere else entirely.

### 1. Container OOM

The container exceeded its own `resources.limits.memory`, and the kernel killed a process inside that container's cgroup. It's isolated: one container, one limit, one kill, repeating on the same workload.

The signature: `Reason: OOMKilled`, exit code 137, a climbing restart count, and `CrashLoopBackOff` when it recurs quickly. Common causes: a limit set too low, a genuine leak, a load or batch spike, or a workload whose steady-state footprint was never measured.

### 2. Node OOM [...] Guaranteed helps most under node pressure, but it doesn't stop a container exceeding its own limit, and the CPU half of the deal trades burst headroom for throttling. That's why some teams skip full Guaranteed and instead set memory requests equal to memory limits inside a Burstable pod, which captures most of the memory-side protection. Either way, the requests need to reflect measured usage rather than guesses.

## How do you diagnose OOMKilled errors?

Start with `kubectl get pods`. A workload that keeps getting OOMKilled shows a climbing restart count, and once restarts stack up, a `CrashLoopBackOff` status while the kubelet backs off between attempts.

Then `kubectl describe pod` for the confirmation:

```
kubectl describe pod my-app-xyz123 
```
- [5 Ways You Can Diagnose & Prevent OOMKilled Errors in Kubernetes](https://www.fairwinds.com/blog/5-ways-you-can-diagnose-and-prevent-oomkilled-errors-in-kubernetes) — 1. Properly configure memory limits and memory requests for containers and pods to ensure that they have enough resources to run without running out of available memory.
2. Monitor memory usage and performance metrics to identify potential issues before they lead to OOMKilled errors.
3. Ensure that Kubernetes clusters are properly provisioned with sufficient resources to support the applications running on them.
4. Implement tools to detect and respond to OOMKilled errors in real-time.
5. Analyze OOMKilled errors to identify root causes and develop preventative measures. [...] Restarting the container or pod can provide a temporary solution to the problem by freeing up memory and CPU resources. However, if you do not address the root cause of the OOMKilled error, the container or pod may continue to experience the same error and be restarted repeatedly.

If you see repeated restarts, it may indicate a persistent issue with the container or pod, such as a memory leak or inadequate resource allocation. In these cases, you need to diagnose the root cause of the error and address it to prevent further OOMKilled errors and keep your Kubernetes cluster running smoothly.

## Diagnose & troubleshoot OOMKilled errors in Kubernetes logs [...] ## Optimize the container to reduce memory usage

Memory limits play a crucial role in preventing OOMKilled errors in Kubernetes. When a container or pod requests memory resources, Kubernetes sets a limit on the amount of memory that can be used by that container or pod.

If a container or pod exceeds its memory limit, Kubernetes may terminate the container or pod and generate an OOMKilled error because the system is unable to allocate more memory to the container or pod.

Setting appropriate memory limits can prevent OOMKilled errors by ensuring that containers or pods do not consume more memory than they require. If you find that a container or pod needs more memory than its current limit, you can increase the limit to accommodate the additional memory requirements.
- [Kubernetes OOMKilled Error: How to Fix & Tips for Preventing It · Dash0](https://www.dash0.com/guides/kubernetes-oomkilled-error-how-to-fix-and-tips-for-preventing-it) — It’s important to note that the OOM Killer is a necessary component of the Linux kernel that helps ensure the stability of the system when faced with memory pressure. By understanding how the OOM Killer mechanism functions, we can better design and configure our Kubernetes applications to avoid OOMKilled events.

## Common causes of OOMKilled

OOMKilled events can be triggered by a variety of factors. Here are some of the most common causes:

### Misconfigured memory limits

One of the most common causes of OOMKilled events is misconfigured memory limits. When deploying a container in Kubernetes, it’s essential to set appropriate memory limits. If a pod is allocated less memory than it needs to function correctly, it will attempt to consume more memory, leading to an OOMKilled event. [...] To avoid this, it’s important to understand the memory requirements of your application. Monitor the memory usage of your application under different load scenarios to get a clear picture of its memory needs. Then, set the memory limits accordingly in your Kubernetes deployment configuration.

### Memory leaks in applications

Another common cause of OOMKilled events is memory leaks in applications. A memory leak occurs when a program consumes memory but does not release it back to the system after it’s done using it. Over time, this can lead to an increase in the memory usage of the application, eventually triggering an OOMKilled event. [...] ## Best practices to prevent OOMKilled status

### Properly setting memory requests and limits

The first step to prevent Kubernetes OOMKilled (Exit Code 137) is to properly set memory requests and limits. Memory requests tell the Kubernetes scheduler how much memory to reserve for a pod, while memory limits define the maximum amount of memory a pod can use.

Setting these values appropriately is a balancing act. If requests are too low, your pods might not have enough memory to function correctly, leading to OOMKilled status. Set them too high, and you risk wasting resources and reducing the overall efficiency of your cluster. As a best practice, monitor your application’s memory usage over time and adjust the requests and limits accordingly.

### Monitoring and alerting
- [OOMKilled (Exit Code 137): Causes and How to Fix It](https://cast.ai/blog/oomkilled-exit-code-137) — Quick Answer: OOMKilled / Exit Code 137

 Exit code 137 = 128 + SIGKILL (signal 9). The Linux kernel OOM killer fired against your container.
 Root cause: the container crossed its cgroup memory limit — or the node ran out of physical memory.
 Kubernetes surfaces it as `reason: OOMKilled` in `kubectl describe pod`.
 No graceful shutdown: SIGKILL cannot be caught or ignored.
 The fix is correct per-container memory sizing — not globally raising limits or adding nodes.
 QoS class determines kill priority: `BestEffort` pods die first, `Guaranteed` pods last.
 Three distinct scenarios produce OOMKilled. Each has a different fix.

## Why Kubernetes kills a pod with exit code 137

Three distinct scenarios produce OOMKilled. Conflating them leads to the wrong fix. [...] OOMKilled means the Linux kernel OOM killer terminated a container for crossing its cgroup memory limit – exit code 137, container is restarted per restartPolicy, who kills is the Linux kernel. Evicted means kubelet proactively removed a pod because node-level `memory.available` dropped below the eviction threshold – no exit code (pod phase: Failed), pod stays Failed until deleted, who kills is kubelet. Eviction is preventive; OOMKilled is the kernel acting after limits are breached.

Does OOMKilled always mean exit code 137? [...] Init container OOMKills: If an init container gets OOMKilled, the pod never transitions to `Running` – it stays in `Init` or `Init:OOMKilled` state and restarts. This is distinct from a running container OOMKill, where the pod is already running and the container restarts within it. Check `kubectl describe pod` for init container terminated state.

Sidecars as hidden culprits: Istio proxies, Datadog agents, and other sidecars run in the same pod and draw from the same node memory. An app container correctly sized at 256Mi can still push the pod toward OOM if an Istio sidecar is consuming another 100–150Mi that was never accounted for in the limit. Always inspect every container in the pod, not just the application container.
- [Kubernetes Exit Codes: 137, 139, 143, 127 and Fixes](https://cast.ai/blog/kubernetes-exit-codes) — For a complete walkthrough of diagnosis and remediation, see the OOMKilled deep-dive.

A few patterns that reliably cause exit code 137: ML inference containers that load a model into RAM on startup (the model grows with new versions); Java applications where the JVM heap isn’t bounded by `-XX:MaxRAMPercentage` and grows into the container limit; data processing jobs that read a full dataset into memory and fail when the dataset grows beyond what was tested.

### Exit code 139 (SIGSEGV) [...] See how Cast AI’s Workload Autoscaler eliminates OOMKills at scale without requiring manual limit tuning.

## Frequently Asked Questions

What does exit code 137 mean in Kubernetes?

Exit code 137 means the container was killed by SIGKILL (signal 9). The most common cause is Reason: OOMKilled – the kernel’s OOM killer fired because the container exceeded its configured memory limit. It can also appear with Reason: Error when `terminationGracePeriodSeconds` expired and Kubernetes sent SIGKILL. Check the Reason field in `kubectl describe pod` under Last State to tell them apart. SIGKILL cannot be caught or handled; there is no graceful shutdown regardless of cause.

What is exit code 139 in a container? [...] ## How resource configuration drives the most common exit codes

Exit code 137 is the only one in this list that’s structural rather than accidental. OOMKilled doesn’t happen because of a bug in your application; it happens because the memory limit you set – at deployment time, based on a load test or a rough estimate – no longer matches the memory the workload actually uses. The gap between those two numbers grows over time: the model gets larger, the dataset grows, the traffic pattern changes, and the static limit stays the same.
- [Kubernetes OOMKilled: Fix Memory Limit Issues & Exit Code 137 | K8s Troubleshooting Tutorial](https://www.youtube.com/watch?v=JLw_pHLCN4Y&xstg=CAMSBhUDze3xHw%3D%3D) — [0:42] by its distinctive exit code 137. This exit code is a combination of 128, which
[0:49] is the base code for fatal signals, plus 9, which represents the SI GKILL signal.
[0:56] So whenever you see exit code 137, you know a container was killed due to memory issues.
[1:04] There are four main reasons why OOM killed errors occur. First, the memory limit might simply be set too low for
[1:11] your application's actual needs. Second, your application could have a memory leak, meaning it's not releasing memory
[1:18] properly after use. Third, a sudden traffic spike can cause memory consumption to jump unexpectedly. And
[1:25] fourth, there might be a bug in your application code that's causing excessive memory usage. Identifying which of these is affecting your
- [Debugging Kubernetes OOMKilled (Exit Code 137): A Root Cause Guide](https://resolve.ai/glossary/how-to-debug-kubernetes-OOMKilled-errors) — The signature is evicted pods citing memory pressure, a `MemoryPressure` condition on the node, and a mix of pods dying around the same time, including containers sitting comfortably under their own limits. Common causes: summed limits well above node capacity, a noisy-neighbor pod, or missing requests letting the scheduler overpack the node.

### 3. Runtime OOM, the look-alike

The runtime hits its own memory ceiling before the cgroup does. The JVM throws `OutOfMemoryError`, Node.js aborts with "JavaScript heap out of memory", and the container exits with `Reason: Error` or keeps limping along degraded. OOMKilled never appears, which is exactly why this case gets misdiagnosed: the evidence lives in the application logs rather than the pod status. [...] ## What are the three types of OOM in Kubernetes?

Memory failures come in three shapes. Two normally produce the OOMKilled status; the third looks related and shows up somewhere else entirely.

### 1. Container OOM

The container exceeded its own `resources.limits.memory`, and the kernel killed a process inside that container's cgroup. It's isolated: one container, one limit, one kill, repeating on the same workload.

The signature: `Reason: OOMKilled`, exit code 137, a climbing restart count, and `CrashLoopBackOff` when it recurs quickly. Common causes: a limit set too low, a genuine leak, a load or batch spike, or a workload whose steady-state footprint was never measured.

### 2. Node OOM [...] ## What causes unexpected memory consumption?

Memory leaks. Usage climbs steadily from startup until it hits the limit, the container restarts, and the cycle repeats. The restart resets the clock, which is how leaky services hide behind "it recovered on its own" for months.

Unbounded caches and queues. In-memory caches without eviction, or queues that buffer while a downstream consumer runs slow. These resemble leaks on a graph but plateau when input pressure drops.

Load-proportional spikes. Large request payloads, file processing, fan-out queries. The baseline fits the limit and the p99 doesn't, so kills correlate with traffic rather than uptime.
- [Kubernetes Exit Code 137: Root Causes and How to Fix It](https://www.plural.sh/blog/kubernetes-exit-code-137) — A container that exits with status 137 has not returned a normal application error. It was terminated by signal 9, SIGKILL, which stops the process immediately and cannot be caught or handled. The number follows the Unix convention of 128 plus the fatal signal number, so 128 + 9 produces 137. In Kubernetes, the most common explanation is that the container exceeded its memory limit and was marked OOMKilled, but the status alone is not a complete diagnosis. [...] That distinction matters when an application is restarting in production. Treating every 137 as a container memory-limit violation can lead you to increase limits while the real issue is an operational action. Node instability, or a different layer of resource pressure.

### When OOMKilled is the likely cause

If the container exceeded its cgroup memory limit, the Linux kernel can terminate it with SIGKILL. Kubernetes normally exposes that cause in the terminated container state as `reason: OOMKilled`. A matching event, rising memory metric, or repeatable failure near the configured limit strengthens the diagnosis. In this case, inspect the workload's memory request and limit, then compare them with the process's working set and peak usage before changing the limit. [...] This evidence-based sequence turns `kubernetes exit code 137` from a restart symptom into a specific diagnosis: an application limit breach, node memory pressure, or another SIGKILL source.

## Is Exit Code 137 Always Caused by OOMKilled?

No. OOMKilled is the most common explanation for `kubernetes exit code 137`, but the status alone only tells you that the container's main process ended with signal 9, SIGKILL. The conventional exit-status calculation is 128 plus the signal number, so 128 + 9 produces 137. It does not identify which actor sent the signal.