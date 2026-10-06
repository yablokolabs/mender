# Root cause: checkout pod OOMKilled due to 64Mi memory limit below 96Mi startup cache requirement

Service `checkout` in namespace `shop`.

## Root cause
The checkout-76b4dd4bd ReplicaSet specifies a container memory limit of 64Mi, but the application allocates a 96MiB startup cache (STARTUP_CACHE_BYTES = 96 * 1024 * 1024) at launch, causing immediate OOMKill.

## Mechanism
1. Pod checkout-76b4dd4bd-bdl7d starts with memory limit 64Mi [pod describe]. 2. Application main() creates bytearray(96*1024*1024) simulating a JVM heap [service.py: STARTUP_CACHE_BYTES]. 3. Allocation exceeds 64Mi cgroup limit, kernel OOM-kills container (exit code 137 = SIGKILL) [pod describe: Reason: OOMKilled, Exit Code: 137]. 4. Kubernetes restarts container; same allocation repeats -> CrashLoopBackOff [pod status + events: BackOff warnings]. 5. Other ReplicaSets (e.g., 69c74c5b74) run with 512Mi limit and stay healthy [pod describe: Limits.memory=512Mi].

Confidence: 0.95 · Labels: oomkilled, memory_limit, config_error, resource_quota

## Evidence relied on
- STARTUP_CACHE_BYTES = 96 * 1024 * 1024  # the 'JVM heap' that OOMs a 64Mi limit
- cache = bytearray(STARTUP_CACHE_BYTES)
- Reason: OOMKilled, Exit Code: 137
- Limits: memory: 64Mi
- memory limit {limit} below required {MIN_MEMORY_LIMIT_MIB}Mi (startup cache alone is 96Mi)

## Tavily sources
Queries: Kubernetes OOMKilled exit code 137 memory limit 64Mi startup cache 96Mi; container CrashLoopBackOff OOMKilled insufficient memory limit for application startup cache; Kubernetes pod OOMKilled memory limit below application startup heap requirement
- [Exit Code 137 - Fixing OOMKilled Kubernetes Error](https://spacelift.io/blog/oomkilled-exit-code-137) — ## What is the OOMKilled Kubernetes error (exit code 137)?

In Kubernetes, when a container uses more memory than its assigned `memory limit`, the Linux Out-Of-Memory (OOM) killer forcibly stops the process. This results in the container exiting with code 137, which corresponds to `SIGKILL (signal 9) + 128`. The container is then marked as `OOMKilled` in the Pod’s status.

This often happens when:

 The container exceeds its memory limit (as set in resources.limits.memory), triggering an OOMKill.
 The node runs critically low on memory, and the kernel OOMKiller terminates one or more containers.

To resolve it, either optimize memory usage or increase the container’s memory limit. Monitoring with tools like Prometheus or using `kubectl describe pod` can help identify patterns. [...] If you want to learn more about Spacelift, create a free account today or book a demo with one of our engineers.

## Key points

OOM Killed in Kubernetes with Exit Code 137 means a container was terminated because it exceeded its memory limit.

To avoid the OOMKilled error, it is recommended to monitor memory usage in Kubernetes pods and containers, set resource limits to prevent containers from consuming too much memory, and optimize application code to reduce memory consumption.

Additionally, consider increasing the memory resources allocated to the pod or using horizontal pod autoscaling to scale up the number of pods in response to increased workload demands.

### The most flexible CI/CD automation tool [...] Look for spikes approaching or exceeding the limit.

### Step 4: Tune memory management

If justified, increase memory limits, optimize code for lower usage, or implement retries if the operation can be broken into smaller chunks.

## How to troubleshoot and fix Exit Code 137

Below are the common causes of the OOMKilled Kubernetes error and their resolutions.

### 1. Increase memory limits in resource configuration

When containers exceed their memory limits, Kubernetes kills them with `SIGKILL`, resulting in Exit Code 137. If your pod is running close to or beyond its assigned memory (`limits.memory`), increasing this limit ensures the container has enough room to operate without being terminated. Update your pod’s or deployment’s resource specification:
- [Kubernetes OOMKilled: Fix Memory Limit Issues & Exit Code 137 | K8s Troubleshooting Tutorial](https://www.youtube.com/watch?v=JLw_pHLCN4Y) — [0:42] by its distinctive exit code 137. This exit code is a combination of 128, which
[0:49] is the base code for fatal signals, plus 9, which represents the SI GKILL signal.
[0:56] So whenever you see exit code 137, you know a container was killed due to memory issues.
[1:04] There are four main reasons why OOM killed errors occur. First, the memory limit might simply be set too low for
[1:11] your application's actual needs. Second, your application could have a memory leak, meaning it's not releasing memory
[1:18] properly after use. Third, a sudden traffic spike can cause memory consumption to jump unexpectedly. And
[1:25] fourth, there might be a bug in your application code that's causing excessive memory usage. Identifying which of these is affecting your [...] [1:33] application is the first step toward fixing the problem.
[1:39] To detect if your pod was killed due to out of memory, you can use the cubectal describe pod command followed by your pod name. This will show you detailed
[1:47] information about the pod status. Look specifically for the last state section in the output. If you see the reason
[1:54] listed as OOM killed and exit code 137, you've confirmed that your container was terminated due to exceeding its memory
[2:02] limit. This information is essential for troubleshooting and determining your next steps.
[2:09] Kubernetes uses two different settings to manage container memory requests and limits. Memory requests specify the
[2:16] minimum amount of memory guaranteed to your container for scheduling purposes. [...] [3:09] prevents the container from using more than 512 megabytes, protecting the node from memory exhaustion.
[3:15] These values should be based on your application's actual memory usage patterns.
[3:22] When facing an OOM killed error, follow these four troubleshooting steps. First, check your current memory usage using
[3:30] the cubectal top command to see how much memory your containers are actually consuming. Second, review your application logs to identify memory usage patterns and potential spikes.
[3:41] Third, analyze whether your memory limits align with your actual usage or if they're too restrictive. Finally,
[3:48] based on your findings, either adjust the memory limits to accommodate your workload or investigate your application code for memory leaks or inefficiencies.
- [Debugging Kubernetes OOMKilled (Exit Code 137): A Root Cause Guide](https://resolve.ai/glossary/how-to-debug-kubernetes-OOMKilled-errors) — ## What is an OOMKilled error in Kubernetes?

OOMKilled is the status Kubernetes reports when the Linux kernel's out-of-memory (OOM) killer terminates a process inside your container. The kernel sends SIGKILL, the process dies immediately, and the container's last state records `Reason: OOMKilled` with exit code 137. That exit code turns up in other situations too, which the next section covers.

Since Kubernetes 1.28 on cgroups v2, the kubelet normally sets `memory.oom.group`, so an OOM event kills every process in the container together. On older versions, the OOM killer could pick a single child process and leave the container running degraded; 1.32 added a kubelet setting, `singleProcessOOMKill`, for clusters that want the single-process behaviour back. [...] ## What are the three types of OOM in Kubernetes?

Memory failures come in three shapes. Two normally produce the OOMKilled status; the third looks related and shows up somewhere else entirely.

### 1. Container OOM

The container exceeded its own `resources.limits.memory`, and the kernel killed a process inside that container's cgroup. It's isolated: one container, one limit, one kill, repeating on the same workload.

The signature: `Reason: OOMKilled`, exit code 137, a climbing restart count, and `CrashLoopBackOff` when it recurs quickly. Common causes: a limit set too low, a genuine leak, a load or batch spike, or a workload whose steady-state footprint was never measured.

### 2. Node OOM [...] ## Does exit code 137 always mean OOMKilled?

No. Exit code 137 means the process died from SIGKILL (128 plus signal 9), and the OOM killer is only one sender. The same code shows up when:

 A liveness probe fails, the kubelet sends SIGTERM, and the container ignores it until `terminationGracePeriodSeconds` expires
 A pod is deleted or a node is drained, and the process sits through its grace period the same way
 Something kills the process manually, or a controller does it during a rollout or scale-down

The `Reason` field is what disambiguates. `OOMKilled` means the kernel's OOM killer. `Error` with exit code 137 means a SIGKILL from somewhere else, and the events often say where. Checking the reason first saves you from tuning memory limits to fix a probe problem.
- [Kubernetes OOMKilled Error: How to Fix & Tips for Preventing It · Dash0](https://www.dash0.com/guides/kubernetes-oomkilled-error-how-to-fix-and-tips-for-preventing-it) — Dash0 acquires Polar Signals

Dash0 Logo

Sign inBook a demo

Start Free Trial

Last updated:February 24, 2026

# Kubernetes OOMKilled Error: How to Fix & Tips for Preventing It

## What is Kubernetes OOMKilled (Exit Code 137)?

The Kubernetes OOMKilled (Exit Code 137) is a signal sent by the Linux Kernel to terminate a process due to an Out Of Memory (OOM) condition. This event is usually an indication that a container in a pod has exceeded its memory limit and the system cannot allocate additional memory. When a container is terminated due to an OOM condition, Kubernetes marks it as OOMKilled, and the exit code 137 is logged for troubleshooting. [...] ## Best practices to prevent OOMKilled status

### Properly setting memory requests and limits

The first step to prevent Kubernetes OOMKilled (Exit Code 137) is to properly set memory requests and limits. Memory requests tell the Kubernetes scheduler how much memory to reserve for a pod, while memory limits define the maximum amount of memory a pod can use.

Setting these values appropriately is a balancing act. If requests are too low, your pods might not have enough memory to function correctly, leading to OOMKilled status. Set them too high, and you risk wasting resources and reducing the overall efficiency of your cluster. As a best practice, monitor your application’s memory usage over time and adjust the requests and limits accordingly.

### Monitoring and alerting [...] ### Examining resource quotas and limits

The next step in diagnosing Kubernetes OOMKilled (Exit Code 137) is examining resource quotas and limits. Kubernetes allows us to set resource quotas at the namespace level and resource limits at the container level. These settings help to ensure fair allocation of resources among pods and prevent any single pod from hogging resources.

When a container exceeds its resource limit, the Kubernetes system kills it, leading to the OOMKilled status. You can inspect the resource usage of your pods using kubectl describe pod, which will provide information on both the requested and the actual usage. If you find that your pods are consistently reaching or exceeding their resource limits, it might be time to reassess your resource allocation.
- [Subprocess Killed with a 137 error - General Discussions - Discuss Kubernetes](https://discuss.kubernetes.io/t/subprocess-killed-with-a-137-error/22058) — Many thanks!

exit code 137 is signal 9 (128 + 9 = 137). Signal 9 is SIGKILL. It’s not just OOM that could cause this - anything which can signal your process could cause it.

If ti was OOM, you would see something in `dmesg` usually, which might give you a clue.

`dmesg`

Thanks for the info :slight_smile:

:slight_smile:

dmesg yielded:

`[ +0.000002] oom-kill:constraint=CONSTRAINT_MEMCG,nodemask=(null),cpuset=...,mems_allowed=0,oom_memcg=/kubepods/burstable/...,task_memcg=/kubepods/burstable/pod...
[ +0.000022] Memory cgroup out of memory: Killed process 1463994 ...`

That is defo the issue! Now I have somewhere to dig!

I will report back.

Thanks again! [...] I will report back.

Thanks again!

Yeah so this was an OOM because the firing up of the bash (as a sub-process) tipped the pod over its total allocation and the node terminated the sub-process. I watched dmesg with

`sudo dmesg -wH`

and then varied the resource limits on our dev cluster and observed that

Thanks again :slight_smile:

:slight_smile:

The exit code of the process was 137 because that is how cgroup memory violations are handled in the cluster. Doing a describe on the pod, or checking its status after it crashed should have shown that it was evicted due to oom. (You may see 137 for failed health checks too). [...] So exit code 137 can be deceptive because they can be OOM or it could be some foreign process sending a kill signal. You can enable audit logs to see if its a foreign process .

But in my experience if the process is being killed in an expected way by kubernetes (OOM violation, failed heath check, etc) when describing the pod there should be a corresponding event.

### Related topics
- [Kubernetes CrashLoopBackOff: Causes, Diagnosis, and Fixes](https://middleware.io/blog/kubernetes-crashloopbackoff-causes-diagnosis-and-fixes) — CrashLoopBackOff means a container in your pod is starting, crashing, and being restarted in a loop. It is a pod state, not a single error.
 Kubernetes applies exponential backoff between each restart attempt: 10s, 20s, 40s, 80s, 160s, capped at 300s (5 minutes), to prevent resource exhaustion.
 The real error is always in the container logs or Events. CrashLoopBackOff itself is only the symptom.
 The six most common causes: application error on startup, misconfigured or missing environment variables/secrets, OOMKilled (memory limit too low), failing liveness probe, missing or unavailable dependency, and incorrect container command or entrypoint.
 Fastest diagnosis path: kubectl describe pod  to read Events, then kubectl logs  –previous to read the last crash output. [...] Fix the code bug or configuration file the application is failing to read
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
``` [...] ### What causes CrashLoopBackOff?

The most common causes are: application code crashing on startup, missing or misconfigured environment variables or Secrets, memory limits that are too low (causing OOMKilled), a misconfigured liveness probe that kills a healthy container, a required dependency being unavailable at startup, and an incorrect container entrypoint command.

### Does CrashLoopBackOff fix itself?

It can, if the underlying cause is transient. For example, a dependency that was temporarily unavailable may recover before the next restart attempt. If the cause is permanent (code bug, wrong configuration, memory limit too low), the pod stays in CrashLoopBackOff indefinitely until you make a change.

### How is CrashLoopBackOff different from OOMKilled?
- [Diagnosing and Fixing CrashLoopBackOff in Kubernetes](https://danielcosenza.com/posts/devops-fix-crashloopbackoff) — Last State: Terminated, Reason: OOMKilled means the container exceeded its memory limit and the kernel’s OOM killer terminated it — a resource-configuration problem, not an application bug per se. The fix is either raising the pod’s memory limits, or (if the application is genuinely leaking memory) fixing the leak itself:
- [Kubernetes Troubleshooting: Errors, Causes & Fixes](https://cast.ai/blog/kubernetes-troubleshooting) — Start with the right signal. Pod status, exit codes, and `kubectl events` together tell a complete story. Each error type has a specific first command – jumping to fixes without reading the signal wastes time.
 OOMKilled (exit 137) means the container exceeded its memory limit. The fix starts with memory requests and limits, not the application.
 CrashLoopBackOff is a restart loop, not a single error. Use `kubectl logs --previous` to read the log from the most recent crashed container before Kubernetes replaces it.
 ImagePullBackOff means the kubelet cannot pull the container image. Check the image name and tag first, then registry authentication, then network – in that order. [...] What causes OOMKilled in Kubernetes?

OOMKilled (exit code 137) occurs when a container uses more memory than its configured limit and the Linux kernel sends SIGKILL. Common causes include a memory limit set too low for the application’s peak working set, a memory leak in the application, and node-level MemoryPressure caused by other pods with no limits set. BestEffort pods (no requests or limits configured) are the first to be killed when a node faces memory pressure, because they sit at the lowest QoS class. Note that exit code 137 covers all SIGKILL events; confirm OOM specifically by checking `Reason: OOMKilled` in the pod’s Last State.

What is CrashLoopBackOff in Kubernetes? [...] ## Pod Lifecycle Errors

### CrashLoopBackOff

CrashLoopBackOff means a container crashes repeatedly and kubelet restarts it with exponential backoff: 10 seconds initially, doubling up to a 300-second cap. The RESTARTS counter in `kubectl get pods` climbs with each cycle. However, the status string itself does not explain why the container crashes. The logs do.

Causes: Application error (exit code 1 or 2). OOMKilled (exit code 137) triggering the loop. Failing liveness probe causing kubelet to restart a healthy container. Wrong image or entrypoint. Missing ConfigMap or Secret the application requires. Init container failure blocking the main container from starting.

First command:

```
kubectl logs  -n  --previous
```
- [CrashLoopBackOff in Kubernetes: Causes and Fixes](https://cast.ai/blog/crashloopbackoff) — Can OOM kills cause CrashLoopBackOff?

Yes – OOM kills are one of the most common causes. The kernel terminates the container when it exceeds its memory limit (exit code 137). Kubernetes registers the crash and restarts the container. If the limit is still too low, the container hits it again, crashes again, and the loop continues. Cast AI Workload Autoscaler detects the OOMKill event and immediately applies a corrected memory limit, breaking the cycle without manual intervention.

What kubectl command shows CrashLoopBackOff? [...] Automate memory rightsizing. Manual limits drift. Cast AI Workload Autoscaler tracks actual memory usage continuously and keeps limits calibrated. Its OOM event handler closes the feedback loop between a kill event and a corrected limit without requiring an engineer to notice, diagnose, and redeploy. At 240 changes per hour across a fleet, it handles scale that VPA alone cannot.

Use OpsPilot for real-time diagnosis. When a CrashLoopBackOff alert fires at 2am, OpsPilot gives you root cause in seconds: “payments-api has restarted 14 times in 2 hours. Root cause: OOMKilled — memory limit 256Mi, peak RSS 312Mi at v2.3.9 rollout.” That’s the full diagnostic loop compressed into one response, with the specific version and memory figures you need to act. [...] ## How to prevent crash loops

Set accurate resource requests and limits. Requests drive scheduling; limits cap consumption. Profile under realistic load — don’t guess. An undersized memory limit produces OOM kills; no limit lets a leaking container consume the entire node.

Use startup probes for init-heavy workloads. For Java applications on Kubernetes, implementing a `startupProbe` with `failureThreshold=30` and removing CPU limits allows the JVM class-loading phase to complete without being throttled or killed — this is the combination that eliminates init-phase CrashLoopBackOff for JVM workloads. CPU limits cause throttling that dramatically slows JVM class loading; rely on CPU requests for scheduling and monitor actual utilization instead of capping it hard.
- [How to Fix CrashLoopBackOff in Kubernetes? - Komodor](https://komodor.com/learn/how-to-fix-crashloopbackoff-kubernetes-error) — | OOMKilled / Exit code 137 Examples: Reason: OOMKilled Exit Code: 137 Container killed by OOM | Container exceeded memory limit, node memory pressure, memory leak, or bursts during startup causing a spike. | – Raise memory resources.limits and set realistic requests.  – Reduce concurrency / batch size / cache size.  – Investigate leaks and tune JVM/Node/Python memory settings.  – If node pressure: spread replicas, scale nodes, or reduce other workloads. | [...] OOMKilled (often exit code 137) indicates the container was killed due to memory limits or node memory pressure. Look for “OOMKilled” in the container status and Events, then adjust memory requests/limits and investigate memory spikes or leaks.

```
kubectl describe pod  # look for Reason: OOMKilled / Exit Code: 137 kubectl logs  -c  --previous 
```

This usually means the Pod references a ConfigMap or Secret that doesn’t exist (wrong name, wrong namespace, or missing key). The exact missing object is typically listed in Events.

```
kubectl describe pod  kubectl get configmap,secret -n  
```
- [Memory settings for Java process running in Kubernetes pod](https://medium.com/@sharprazor.app/memory-settings-for-java-process-running-in-kubernetes-pod-1e608a5d2a64) — Image 11

After reducing the heap percentage

➊❷ _WSS/RSS stabilized at 3.6GB and had a safe margin to the pod memory limit (4.29GB)_

## Conclusion

The following approach can be used to tackle the uncertainty of Java process memory usage and eliminate the pod _OOMKilled_ issue:

1.   Begin with a reasonable `MaxRAMPercentage` value, and`75%` is normally a good starting point.
2.   Monitor the `heap` usage and the system memory `WSS/RSS` over time. [...] Sitemap

Open in app

Sign up

Sign in



### Initial Attempt to Address the Issue

To mitigate the _OOMKilled_ issue, we increased the pod’s memory limit from `2Gi` to `4Gi`, which did help reduce the problem. However, certain questions remained:

1.   Why was the `container_memory_working_set` and `container_memory_rss` close to 100%, while the JVM heap and non-heap usage were significantly lower?

Press enter or click to view image in full size

Image 4

2. Why was the Working Set Size (WSS)/Resident Set Size (RSS) memory usage more than the JVM’s total memory given the Java process was the only process running in the pod?

Press enter or click to view image in full size

Image 5

3. Why was the process memory usage still close to 100%, almost reaching the pod memory limit? [...] if your maximum `heap` usage is high(i.e. Stays in the _>90% range_), that’s a signal to increase your pod’s memory limit(`resources.limits.memory`). Your `heap` needs more space.
   if the maximum `heap` usage is OK (i.e. Keeps well below _<90%_), but the `WSS/RSS` is high and close to the process limit, consider decreasing the `MaxRAMPercentage`to allocate more memory to the `non/off-heap` space.
   monitor the maximum `WSS/RSS` to make sure there is always a 5% to 10% safety margin from the pod memory limit. Don’t fly too close to the sun!

_Thanks__Paul Smith__for reviewing the post and all the great feedback._

## References

   
   
   
   
   
   
   

Kubernetes

Oomkilled

Jvm Memory

[](

--

[](

--

6

[](

--

[](

Image 12: Fan Liu

Image 13: Fan Liu
- [Why Pods Get OOMKilled in Kubernetes (And Why Memory Limits Won’t Save You)](https://medium.com/@pillarslive/why-pods-get-oomkilled-in-kubernetes-and-why-memory-limits-wont-save-you-5891b8f338ea) — When Node.js runs inside a container with a `2Gi` memory limit, the V8 runtime may not size its heap conservatively enough for that limit unless explicitly configured, depending on the Node.js and V8 version. It sees the host’s total memory and assumes it has far more room to grow. The heap can expand to `1.8GB` while total container memory usage (heap, buffers, caches, everything else) crosses the `2Gi` threshold — triggering an OOMKill.

Java has the same problem, with an additional layer of complexity. The JVM heap is only part of total memory usage: [...] volumeMounts:  
- name: dshm  
 mountPath: /dev/shm  
volumes:  
- name: dshm  
 emptyDir:  
 medium: Memory  
 sizeLimit: "1Gi"
That `1Gi` shared memory volume counted against the container’s total memory limit. When the application wrote large files to `/dev/shm`, it triggered OOMKills even though the application’s heap usage was normal.

### File System Cache

Linux aggressively caches file I/O in memory. Under memory pressure, a portion of this cache can count toward the container’s memory usage and contribute to OOMKills: [...] # Container limit: 2048MB (2Gi)  
# Allocate 80% to V8 heap: 2048  0.8 = 1638MB  
# Reserve 20% for native modules, buffers, and overhead  
node --max-old-space-size=1638 server.js
This ensures V8 triggers garbage collection before approaching the container limit, reducing the risk of OOMKills caused by heap growth.

The memory leak was fixed by implementing proper cache eviction:

const LRU = require('lru-cache');  
  
const customerCache = new LRU({  
 max: 10000, // Maximum number of items  
 ttl: 1000  60  60, // 1 hour TTL  
 updateAgeOnGet: true // Reset TTL on access  
});
### 3. Monitoring and Alerting

Alerts were added at 85% of the memory limit using `container_memory_working_set_bytes` — as described in the monitoring section above.

### 4. Vertical Pod Autoscaler (VPA)
- [Kubernetes OOMKilled out of memory diagnosis](https://www.dynatrace.com/news/blog/kubernetes-oomkilled-out-of-memory-troubleshooting) — Looking at the resource analyses confirmed the suspicion. The following chart shows how memory usage rises to almost the defined limit of 400MB before the pod is killed off and restarted. Historical data shows this didn’t happen with the old version.

Screenshot that shows pod memory metrics indicating how k8s kills the pod when it reaches out of memory limit

Analyzing the pod memory metrics shows how Kubnernetes kills the pod when it reaches the memory limit.

## The fix: Adjust the memory settings to avoid OOMKilled errors

Armed with that knowledge, the solution was simple: Robert increased the pod’s memory limit from 400MB to 600MB so that reports didn’t run into the out-of-memory shortage.

Screenshot that shows proper sizing of k8s resources to avoid out of memory error
- [Direct Memory and Container OOMKilled Errors | Proofpoint US](https://www.proofpoint.com/us/blog/engineering-insights/direct-memory-and-container-oomkilled-errors) — Then, in this developer blog, I came across the following detail: “Netty uses ByteBuffers and direct memory to allocate and deallocate memory.” This made me realize that an unexpected increase in off-heap memory usage might be the cause of the OOMKilled errors.

### The problem: an increase in off-heap memory usage

Let's look at an abstract example of how this could happen. In this example, we examine the Java memory usage of our application before and after the gRPC calls.

Java heap size

  -Xms128m (initial heap size)

  -Xmx256m (max heap size)

Kubernetes pod resource requests and limits

  resources:

    requests:

      memory: 200M

    limits:

      memory: 360M

Figure 1: Java memory allocation before the gRPC calls - total 200M. [...] Dockerfile

FROM openjdk... 

...

ENTRYPOINT ["java", "-Xms512m", "-Xmx2g", "-XX:MaxDirectMemorySize=700m", "-jar", "/app/my-grpc-app.jar"]

Kubernetes pod resource requests and limits

```
resources: requests: memory: "2Gi" # minimum memory request limits: memory: "3Gi" # maximum memory limit 
```

### Join the team

At Proofpoint, our people—and the diversity of their lived experiences and backgrounds—are the driving force behind our success. We have a passion for protecting people, data, and brands from today’s advanced threats and compliance risks.

We hire the best people in the business to: [...] Recently, we encountered continuous integration (CI) build failures in two of our microservices, caused by Java unit tests.

Even though the Java heap size limit was appropriate relative to the resources of the Docker pod, each test generated a Kubernetes OOMKilled error. There were no errors in the logs and no core or heap dump file was generated.
- [How can we tell if the OOMKilled in k8s is because the node is running out of memory and thus killing the pod, or if the pod itself is being killed because the memory it has requested exceeds the limt declaration limit? - General Discussions - Discuss Kubernetes](https://discuss.kubernetes.io/t/how-can-we-tell-if-the-oomkilled-in-k8s-is-because-the-node-is-running-out-of-memory-and-thus-killing-the-pod-or-if-the-pod-itself-is-being-killed-because-the-memory-it-has-requested-exceeds-the-limt-declaration-limit/26303) — Image ID: docker-pullable://nononoxx.nononox.com/nonono-cn/image-vector@sha256:058c43265845a975d7cc537911ddcc203fa26f608714fe8b388d5dfd1eb02d92
Port: 9205/TCP
Host Port: 0/TCP
Command:
python
api.py
State: Running
Started: Wed, 01 Nov 2023 18:35:49 +0800
Last State: Terminated
Reason: OOMKilled
Exit Code: 137
Started: Wed, 01 Nov 2023 18:25:34 +0800
Finished: Wed, 01 Nov 2023 18:35:47 +0800
Ready: True
Restart Count: 8
Limits:
cpu: 2
memory: 2000Mi
Requests:
cpu: 10m
memory: 1000Mi
Liveness: http-get  delay=60s timeout=1s period=30s #success=1 #failure=3
Readiness: http-get  delay=60s timeout=1s period=30s #success=1 #failure=3
Environment: <none>
Mounts:
/var/run/secrets/kubernetes.io/serviceaccount from kube-api-access-2kwj9 (ro)
Conditions:
Type Status
Initialized True
Ready True [...] Want to analyse this kind of problem without introducing external tools (like prometheus)

@ponponon  
In Pods are running container(s) - usualy one.

Limits are settled at the level of container, if container exceeded MEM limits then it will be killed by OOMKille Linux Kernel GCroup sub-sytem with signal SIGKILL (9), BUT pod WILL NOT BE KILLED - container will be restarted (if restartPolicy allow) within the same Pod - so here is in your case is not becuase of Node, but because of containewr within a pod exceeded limit. Exit code is 128 + Killed Signal = 128 + 9 = 137 in your case, and “OOMKilled” refferes to container.