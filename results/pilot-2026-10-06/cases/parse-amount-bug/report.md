# Root cause: checkout pods CrashLoopBackOff due to OOM kills from insufficient memory limit for JVM-like workload

Service `checkout` in namespace `shop`.

## Root cause
Memory limit (512Mi) too low for JVM-like workload (96Mi startup cache + unconstrained heap + native memory), causing repeated OOM kills and CrashLoopBackOff [1][2][3]

## Mechanism
1. Pod starts, container initializes with 96Mi startup cache simulating JVM heap [manifests: STARTUP_CACHE_BYTES=96Mi]. 2. Application allocates additional heap memory without -Xmx constraint (search result [2]: 'JVM workloads: Set -Xmx to ~75% of container memory limit... Skipping this is one of the most common causes of Java OOM kills'). 3. Total memory exceeds 512Mi limit. 4. Kernel OOM kills container (exit code 137, search result [3]). 5. Kubelet restarts with exponential back-off (events: 'Back-off restarting failed container'). 6. Repeated OOM kills → CrashLoopBackOff (search result [7]: 'caused entirely by the health check and resource limit interplay')

Confidence: 0.85 · Labels: oomkilled, memory_limit, probe_config

## Evidence relied on
- Back-off restarting failed container checkout in pod checkout-6cfdc85fb9-t4qbf
- STARTUP_CACHE_BYTES = 96 * 1024 * 1024  # the 'JVM heap' that OOMs a 64Mi limit
- MIN_MEMORY_LIMIT_MIB = 512
- JVM workloads: Set -Xmx to ~75% of the container memory limit... Skipping this is one of the most common causes of Java OOM kills in Kubernetes [2]
- OOMKilled (Memory Exceeded) - The container exceeds its memory limit and is killed by the kernel. Exit Code: 137 [3]
- Cause 1: Memory Limit Too Low [1]
- CrashLoopBackOff caused entirely by the health check and resource limit interplay [7]

## Tavily sources
Queries: Kubernetes CrashLoopBackOff OOM kill memory limit 512Mi startup cache 96Mi; Kubernetes readiness liveness probe http healthz delay timeout period CrashLoopBackOff; containerd BackOff restarting failed container memory limit exceeded 512Mi
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
- [CrashLoopBackOff in Kubernetes: Causes and Fixes](https://cast.ai/blog/crashloopbackoff) — VPA helps automate this. Valid `updateMode` values: `Off` (recommendations only), `Initial` (set on pod creation), `Recreate` (apply via pod eviction), `Auto` (in-place on K8s 1.33+, beta with the `InPlacePodVerticalScaling` feature gate; clusters running 1.27–1.32 still use pod eviction).

JVM workloads: Set `-Xmx` to ~75% of the container memory limit. A 512Mi limit should have `-Xmx384m`. This leaves headroom for non-heap memory — metaspace, thread stacks, native libraries. Skipping this is one of the most common causes of Java OOM kills in Kubernetes. [...] Can OOM kills cause CrashLoopBackOff?

Yes – OOM kills are one of the most common causes. The kernel terminates the container when it exceeds its memory limit (exit code 137). Kubernetes registers the crash and restarts the container. If the limit is still too low, the container hits it again, crashes again, and the loop continues. Cast AI Workload Autoscaler detects the OOMKill event and immediately applies a corrected memory limit, breaking the cycle without manual intervention.

What kubectl command shows CrashLoopBackOff? [...] LimitRange objects can silently impose memory limits on pods that don’t set them explicitly. If an operator deploys a pod without a `resources.limits.memory` field, a LimitRange default (say, 128Mi) applies automatically — the pod appears to be running without limits but gets OOM-killed at 128Mi. Check before you assume the pod has no limit:

```
# Check for LimitRange objects in the namespace kubectl get limitrange -n  # See the default limits applied kubectl describe limitrange -n 
```

### Liveness and readiness probe failures
- [Debug a Pod in CrashLoopBackOff on Kubernetes: Causes and Solutions | SFEIR Institute](https://institute.sfeir.com/en/kubernetes-training/debug-pod-crashloopbackoff-kubernetes-causes-solutions) — ### Cause 3: OOMKilled (Memory Exceeded)

The container exceeds its memory limit and is killed by the kernel.

Symptoms:

```
Exit Code: 137 Reason: OOMKilled Last State: Terminated 
```

Diagnosis:

```
# Check memory consumption before crash kubectl top pod checkout-7d4b5c6f9-x2k4n --containers # Compare with limits kubectl get pod checkout-7d4b5c6f9-x2k4n -o jsonpath='{.spec.containers.resources}' 
```

Solutions:

```
resources: requests: memory: "512Mi" limits: memory: "1Gi" # Increase if necessary 
```

For a detailed guide, see Resolve OOMKilled errors.

### Cause 4: Container Image Problem

The image cannot be pulled or the entrypoint is incorrect.

Symptoms:

```
State: Waiting Reason: ImagePullBackOff # or Reason: CrashLoopBackOff with Exit Code: 127 (command not found) 
``` [...] ### Cause 2: Missing Configuration (ConfigMap/Secret)

The container tries to read an environment variable or configuration file that doesn't exist.

Symptoms:

```
State: Waiting Reason: CreateContainerConfigError 
```

Diagnosis:

```
# Check referenced ConfigMaps kubectl describe pod checkout-7d4b5c6f9-x2k4n | grep -A5 "Environment" # Verify ConfigMap exists kubectl get configmap checkout-config -n production 
```

Solutions:

```
# Make variable optional env: - name: DATABASE_URL valueFrom: configMapKeyRef: name: checkout-config key: database-url optional: true # Pod starts even if absent 
```

> Key takeaway: Use `optional: true` for non-critical configurations. Validate required configurations in an init container.

### Cause 3: OOMKilled (Memory Exceeded)
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

bash [...] ## Why Resource Limit Changes Cause CrashLoopBackOff

When you change resource limits, Kubernetes kills and restarts affected pods with the new constraints. If the new limits are too low, the container crashes immediately — triggering the backoff loop.

Three things kill your container after a limit change:

1. OOMKilled — Memory limit is too low, kernel kills the process  
 2. CPU throttling so severe the app times out — Liveness probe fails, container restarts  
 3. JVM / runtime startup fails — Java apps need memory headroom at startup, not just steady state

## Diagnose First

bash [...] # Check why pod is crashing # Check why pod is crashingkubectl describe pod <pod-name> -n <namespace> kubectl  describe  pod <pod-name> -n < namespace>  # Look for these in the output:# Look for these in the output:# State: Terminated# State: Terminated# Reason: OOMKilled ← memory too low# Reason: OOMKilled ← memory too low# Exit Code: 137 ← OOMKilled# Exit Code: 137 ← OOMKilled# Exit Code: 1 ← app crashed (check logs)# Exit Code: 1 ← app crashed (check logs)  # Check actual resource usage before crash # Check actual resource usage before crashkubectl top pod <pod-name> -n <namespace> kubectl  top  pod <pod-name> -n < namespace>  # Check logs from the PREVIOUS container run # Check logs from the PREVIOUS container runkubectl logs <pod-name> -n <namespace> --previous kubectl  logs
- [How to Fix CrashLoopBackOff in Kubernetes? - Komodor](https://komodor.com/learn/how-to-fix-crashloopbackoff-kubernetes-error) — OOMKilled (often exit code 137) indicates the container was killed due to memory limits or node memory pressure. Look for “OOMKilled” in the container status and Events, then adjust memory requests/limits and investigate memory spikes or leaks.

```
kubectl describe pod  # look for Reason: OOMKilled / Exit Code: 137 kubectl logs  -c  --previous 
```

This usually means the Pod references a ConfigMap or Secret that doesn’t exist (wrong name, wrong namespace, or missing key). The exact missing object is typically listed in Events.

```
kubectl describe pod  kubectl get configmap,secret -n  
``` [...] | OOMKilled / Exit code 137 Examples: Reason: OOMKilled Exit Code: 137 Container killed by OOM | Container exceeded memory limit, node memory pressure, memory leak, or bursts during startup causing a spike. | – Raise memory resources.limits and set realistic requests.  – Reduce concurrency / batch size / cache size.  – Investigate leaks and tune JVM/Node/Python memory settings.  – If node pressure: spread replicas, scale nodes, or reduce other workloads. |
- [Kubernetes readiness and liveness probe failures | NOFire AI](https://www.nofire.ai/glossary/kubernetes-probe-failures) — ### 3. initialDelaySeconds too short

The container is probed before it finishes initializing. The liveness probe fails, Kubernetes kills the container, and the cycle repeats. This is one of the primary causes of CrashLoopBackOff on first deploy or after a pod reschedule.

This is especially common with:

 Java/JVM applications (30-90 second startup times are normal)
 Applications that run database migrations on startup
 Services that wait for a sidecar to be ready before accepting connections

### 4. CPU throttling causing probe timeouts

If a container is at or near its CPU limit, the health endpoint may not respond within `timeoutSeconds`. The probe fails even though the application is functioning. The failure appears intermittent and correlates with high-traffic periods. [...] ```
docker run --rm <your-image> & docker  run --rm <your-imag e>  &curl -s -o /dev/null -w "%{http_code}" localhost:8080/health curl -s -o /dev/null -w "%{http_code}" localhost:8080/health
```

If it does not return 200, the probe will fail in the cluster.

Alert on restart count, not just CrashLoopBackOff. CrashLoopBackOff means Kubernetes has already backed off after repeated failures. A restart count above 3 in a rolling window is an early signal worth alerting on:

```
- alert: PodRestartingFrequently - alert:  PodRestartingFrequently expr: |  expr:  | increase(kube_pod_container_status_restarts_total[1h]) > 3 increase(kube_pod_container_status_restarts_total[1h]) > 3 for: 5m  for:  5m labels:  labels: severity: warning  severity:  warning
```
- [Kubernetes Liveness, Readiness, and Startup Probes](https://hackernoon.com/kubernetes-liveness-readiness-and-startup-probes-keys-to-container-health-and-resilience) — in a permanent CrashLoopBackOffwhere the service was effectively down, caused entirely by the health check and resource limit interplay. The resolution was to relax the liveness probe settings (5s timeout and require 10 failures) and remove the CPU limit, which broke the feedback loop. The moral here is that liveness probes should be tuned to truly indicate a stuck application, not just momentary slowness. During overload, failing a probe might worsen the situation by killing containers that were actually working (just slow). It’s often better to let a slow pod continue serving what it can (perhaps marked not ready) rather than restart it and add more strain on the system. [...] Resisting Overload Failures: Even with the best tuning, an overly aggressive liveness probe can amplify problems under heavy load. A real-world incident in 2023 described how a combination of a tight liveness probe and a CPU limit caused an unstable feedback loop. The application would get a burst of traffic and slow down under CPU throttling; the liveness probe (set with a 1 second timeout) would occasionally time out and force a restart of the pod. But restarting cleared in-memory state and also removed the pod from service briefly, pushing more load onto fewer pods. When the pod came back, it was hit with an even larger backlog of requests, causing the liveness probe to fail again, leading to another restart. This cycle resulted in a permanent CrashLoopBackOffwhere the service was [...] CrashLoopBackOff status is another red flag often tied to failing liveness probes. If you see pods in CrashLoopBackOff, describe them to find if liveness probe failures are the cause. An alert on pods stuck in CrashLoopBackOff for X minutes might be useful.
 Some teams also set up synthetic external checks or dashboards to monitor service availability which indirectly catches if pods are being taken out by probes.
- [Liveness, Readiness, and Startup Probes | Kubernetes](https://kubernetes.io/docs/concepts/workloads/pods/probes) — failureThreshold:  30   periodSeconds: 10  periodSeconds: 10  periodSeconds:  10   livenessProbe:  livenessProbe:  livenessProbe:   httpGet:  httpGet:  httpGet:   path: /healthz  path: /healthz  path:  /healthz   port: 8080  port: 8080  port:  8080   initialDelaySeconds: 10  initialDelaySeconds: 10  initialDelaySeconds:  10   periodSeconds: 5  periodSeconds: 5  periodSeconds:  5   timeoutSeconds: 3  timeoutSeconds: 3  timeoutSeconds:  3   failureThreshold: 3  failureThreshold: 3  failureThreshold:  3   readinessProbe:  readinessProbe:  readinessProbe:   httpGet:  httpGet:  httpGet:   path: /ready  path: /ready  path:  /ready   port: 8080  port: 8080  port:  8080   periodSeconds: 5  periodSeconds: 5  periodSeconds:  5 [...] apiVersion: v1 apiVersion: v1 apiVersion:  v1  kind: Pod kind: Pod  kind:  Pod  metadata: metadata:  metadata:   name: probe-example  name: probe-example  name:  probe-example  spec: spec:  spec:   containers:  containers:  containers:   - name: app  - name: app  name:  app   image: registry.k8s.io/e2e-test-images/agnhost:2.40  image: registry.k8s.io/e2e-test-images/agnhost:2.40  image:  registry.k8s.io/e2e-test-images/agnhost:2.40   ports:  ports:  ports:   - containerPort: 8080  - containerPort: 8080  containerPort:  8080   startupProbe:  startupProbe:  startupProbe:   httpGet:  httpGet:  httpGet:   path: /healthz  path: /healthz  path:  /healthz   port: 8080  port: 8080  port:  8080   failureThreshold: 30  failureThreshold: 30  failureThreshold:  30   periodSeconds: 10  periodSeconds: [...] spec: spec: spec:   terminationGracePeriodSeconds: 3600 # pod-level  terminationGracePeriodSeconds: 3600 # pod-level  terminationGracePeriodSeconds:  3600  # pod-level   containers:  containers:  containers:   - name: test  - name: test  name:  test   image: ...  image: ...  image:  ...      ports:  ports:  ports:   - name: liveness-port  - name: liveness-port  name:  liveness-port   containerPort: 8080  containerPort: 8080  containerPort:  8080      livenessProbe:  livenessProbe:  livenessProbe:   httpGet:  httpGet:  httpGet:   path: /healthz  path: /healthz  path:  /healthz   port: liveness-port  port: liveness-port  port:  liveness-port   failureThreshold: 1  failureThreshold: 1  failureThreshold:  1   periodSeconds: 60  periodSeconds: 60  periodSeconds:  60   # Override pod-level
- [Kubernetes Health Probes: A Deep Dive into Liveness and Readiness | by Ibrahim Cisse | Medium](https://medium.com/@Ibraheemcisse/kubernetes-health-probes-a-deep-dive-into-liveness-and-readiness-475ba0f7cc65) — ```
Events:Normal  Scheduled  88s   default-scheduler  Successfully assigned default/hello to node01Normal  Pulled     82s   kubelet  Successfully pulled imageWarning Unhealthy  11s   kubelet  Liveness probe failed: HTTP probe failed with statuscode: 500Normal  Killing    11s   kubelet  Container liveness failed liveness probe, will be restartedWarning Unhealthy  11s   kubelet  Readiness probe failed: HTTP probe failed with statuscode: 500Warning BackOff    10s   kubelet  Back-off restarting failed containerEvents: 88s default default to 82s 11s with 500 11s 11s with 500 10s off
```

The pod eventually entered a `CrashLoopBackOff` state with 6 restarts, demonstrating how persistent probe failures can lead to application instability.

## Solving the CrashLoopBackOff Problem [...] apiVersion: v1kind: Podmetadata:  name: hello-fixedspec:  containers:  - name: liveness    image: registry.k8s.io/e2e-test-images/agnhost:2.40    args:    - liveness    livenessProbe:      httpGet:        path: /healthz        port: 8080      initialDelaySeconds: 10  # Increased from 3 to 10      periodSeconds: 10        # Increased from 3 to 10      timeoutSeconds: 5        # Added explicit timeout      failureThreshold: 3      # Made explicit (default is 3)    readinessProbe:      httpGet:        path: /healthz        port: 8080      initialDelaySeconds: 5   # Reduced from 15 to 5      periodSeconds: 5         # Reduced from 10 to 5      timeoutSeconds: 3        # Added explicit timeout      failureThreshold: 1      # Made explicit (default is 3)apiVersion: v1kind: [...] This approach simply attempts to establish a TCP connection to the specified port. If the connection succeeds, the container is considered healthy; if it fails, it’s marked as unhealthy.

## Key Insights from My Testing Experience

Through these experiments on my killerkoda cluster, I gained several crucial insights:

## 1. Timing is Everything

The `initialDelaySeconds` and `periodSeconds` parameters are critical. Set them too aggressively, and you'll get false positives during application startup. Set them too conservatively, and you'll miss actual failures. My CrashLoopBackOff experience taught me that finding the right balance is essential.

## 2. Different Probes Serve Different Purposes
- [Debug a Pod in CrashLoopBackOff on Kubernetes: Causes and Solutions | SFEIR Institute](https://institute.sfeir.com/en/kubernetes-training/debug-pod-crashloopbackoff-kubernetes-causes-solutions) — ```
# Check probe timing kubectl get pod checkout-7d4b5c6f9-x2k4n -o yaml | grep -A10 livenessProbe 
```

Solutions:

```
livenessProbe: httpGet: path: /health port: 8080 initialDelaySeconds: 60 # Wait for startup periodSeconds: 10 failureThreshold: 3 # 3 failures before restart readinessProbe: httpGet: path: /ready port: 8080 initialDelaySeconds: 5 # Faster than liveness periodSeconds: 5 
```

> Key takeaway: readinessProbe should be faster than livenessProbe. Start with conservative values then optimize.

## Advanced Kubernetes Debugging Techniques

### Using kubectl debug (Kubernetes 1.25+)

Ephemeral containers allow attaching a debug container to a running or crashed pod. [...] ### Cause 1: Application Error at Startup

The container starts but the application crashes immediately. This is the most common cause (45% of cases according to Komodor).

Symptoms:

```
Exit Code: 1 Reason: Error 
```

Diagnosis:

```
# Application logs kubectl logs checkout-7d4b5c6f9-x2k4n --previous # Example output Error: Cannot connect to database at postgres:5432 
```

Solutions:

```
# 1. Add init containers for dependencies initContainers: - name: wait-for-db image: busybox:1.36 command: ['sh', '-c', 'until nc -z postgres 5432; do sleep 2; done'] # 2. Configure readiness/liveness probes correctly readinessProbe: httpGet: path: /health port: 8080 initialDelaySeconds: 10 periodSeconds: 5 
```

### Cause 2: Missing Configuration (ConfigMap/Secret)
- [Kubernetes CrashLoopBackOff: Diagnosing and Resolving Container Startup Crashes | ButItWorkedLocal.com](https://butitworkedlocal.com/posts/kubernetes-crashloopbackoff-container-crashing-during-startup-pod) — Title: Kubernetes CrashLoopBackOff: Diagnosing and Resolving Container Startup Crashes | ButItWorkedLocal.com
The `CrashLoopBackOff` status in Kubernetes is a common and often frustrating error indicating that a container within a pod is repeatedly starting, crashing, and then restarting after a delay. Name: my-app-deployment-78f9xxxx-abcdeName: my-app-deployment-78f9xxxx-abcdeNamespace: my-namespaceNamespace: my-namespacePriority: 0Priority: 0Node: worker-node-01/192.168.1.10Node: worker-node-01/192.168.1.10Start Time: Tue, 25 Jun 2024 10:00:00 -0400Start Time: Tue, 25 Jun 2024 10:00:00 -0400Labels: app=my-appLabels: app=my-app pod-template-hash=78f9xxxx pod-template-hash=78f9xxxxAnnotations: Annotations: Status: CrashLoopBackOffStatus: CrashLoopBackOffIP: 10.42.0.15IP: 10.42.0.15IPs:IPs: IP: 10.42.0.15 IP: 10.42.0.15Containers:Containers: my-app-container: my-app-container: Container ID: containerd://xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx Container ID: containerd://xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx Image: my-registry/my-app:1.0.0 Image: my-registry/my-app:1.0.0 Image ID: my-registry/my-app@sha256:yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy Image ID: my-registry/my-app@sha256:yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy Port: 80/TCP Port: 80/TCP Host Port: 0/TCP Host Port: 0/TCP State: Waiting State: Waiting Reason: CrashLoopBackOff Reason: CrashLoopBackOff Last State: Terminated Last State: Terminated Reason: Error Reason: Error Exit Code: 1 Exit Code: 1 Started At: Tue, 25 Jun 2024 10:02:00 -0400 Started At: Tue, 25 Jun 2024 10:02:00 -0400 Finished At: Tue, 25 Jun 2024 10:02:01 -0400 Finished At: Tue, 25 Jun 2024 10:02:01 -0400 Ready: False Ready: False Restart Count: 5 Restart Count: 5 Limits: Limits: cpu: 500m cpu: 500m memory: 512Mi memory: 512Mi Requests: Requests: cpu: 200m cpu: 200m memory: 256Mi memory: 256Mi Liveness: http-get http://:80/health delay=30s timeout=1s period=10s #success=1 #failure=3 Liveness: http-get http://:80/health delay=30s timeout=1s period=10s #success=1 #failure=3 Readiness: http-get http://:80/ready delay=5s timeout=1s period=10s #success=1 #failure=3 Readiness: http-get http://:80/ready delay=5s timeout=1s period=10s #success=1 #failure=3 Environment: Environment: DB_HOST: db-service DB_HOST: db-service DB_PORT: 5432 DB_PORT: 5432 Mounts: Mounts: /var/run/secrets/kubernetes.io/serviceaccount from kube-api-access-zzzzz (ro) /var/run/secrets/kubernetes.io/serviceaccount from kube-api-access-zzzzz (ro)Conditions:Conditions:  Type Status  Type Status  Initialized True  Initialized True  Ready False  Ready False  ContainersReady False  ContainersReady False  PodScheduled True  PodScheduled TrueEvents:Events:  Type Reason Age From Message  Type Reason Age From Message ---- ------ ---- ---- ------- ---- ------ ---- ---- ------- Normal Pulled 2m40s (x6 over 3m) kubelet Container image "my-registry/my-app:1.0.0" already present on machine Normal Pulled 2m40s (x6 over 3m) kubelet Container image "my-registry/my-app:1.0.0" already present on machine Normal Created 2m40s (x6 over 3m) kubelet Created container my-app-container Normal Created 2m40s (x6 over 3m) kubelet Created container my-app-container Normal Started 2m40s (x6 over 3m) kubelet Started container my-app-container Normal Started 2m40s (x6 over 3m) kubelet Started container my-app-container Warning BackOff 15s (x8 over 2m40s) kubelet Back-off restarting failed container my-app-container in pod my-app-deployment-78f9xxxx-abcde Warning BackOff 15s (x8 over 2m40s) kubelet Back-off restarting failed container my-app-container in pod my-app-deployment-78f9xxxx-abcde.
- [[Question] Pod can't run when memory resource limit set using kata. · Issue #2588 · kata-containers/runtime · GitHub](https://github.com/kata-containers/runtime/issues/2588) — Title: [Question] Pod can't run when memory resource limit set using kata. · Issue #2588 · kata-containers/runtime · GitHub
## Navigation Menu. # Search code, repositories, users, issues, pull requests... You signed in with another tab or window. Reload to refresh your session. You signed out in another tab or window. Reload to refresh your session. You switched accounts on another tab or window. Reload to refresh your session. This repository was archived by the owner on May 12, 2021. It is now read-only. kata-containers   /  **runtime**  Public archive. * Notifications  You must be signed in to change notification settings. This repository was archived by the owner on May 12, 2021. It is now read-only. # [Question] Pod can't run when memory resource limit set using kata. [[Question] Pod can't run when memory resource limit set using kata.](#top)#2588. bugIncorrect behaviourIncorrect behaviourneeds-reviewNeeds to be assessed by the team.Needs to be assessed by the team. ## Description. opened on Apr 6, 2020. # Description of problem. I am a new bee to kata container. I have just get my kata enviroment setup by refering the document, I created a pod with memory resouce limit and it failed.When I remove the resouce limit , the pod can run normally. Here is my pod yaml. apiVersion: v1 kind: Pod metadata: name: nginx-untrusted annotations: io.kubernetes.cri.untrusted-workload: "true" spec: containers: - name: nginx image: nginx:alpine resources: requests: memory: "512Mi" limits: memory: "1024Mi". Events: Type Reason Age From Message ---- ------ ---- ---- ------- Normal Scheduled 33s default-scheduler Successfully assigned default/nginx-untrusted to debian0 Normal Pulled 16s (x3 over 31s) kubelet, debian0 Container image "nginx:alpine" already present on machine Normal Created 16s (x3 over 31s) kubelet, debian0 Created container nginx Warning Failed 15s (x3 over 31s) kubelet, debian0 Error: failed to create containerd task: Unable to hotplug 1024 MiB memory, the SB has 2048 MiB and the maximum amount is 1971 MiB: unknown Warning BackOff 2s (x4 over 29s) kubelet, debian0 Back-off restarting failed container. # Expected result. # Actual result. ## Metadata. ## Metadata. ### Labels. bugIncorrect behaviourIncorrect behaviourneeds-reviewNeeds to be assessed by the team.Needs to be assessed by the team. No branches or pull requests. ## Issue actions. You can’t perform that action at this time.
- [What is Kubernetes 'back-off restarting failed container' error?](https://kodekloud.com/blog/what-is-kubernetes-back-off-restarting-failed-container-error) — ```
# This is the original pod spec that causes the 'back-off restarting failed container' error due to insufficient memory apiVersion: v1 kind: Pod metadata:   name: my-app spec:   containers:   - name: my-app     image: my-app:latest     command: ["python", "app.py"] # This is the modified pod spec that fixes the error by specifying the resource requests and limits for the pod apiVersion: v1 kind: Pod metadata:   name: my-app spec:   containers:   - name: my-app     image: my-app:latest     command: ["python", "app.py"]     resources:       requests:         cpu: "100m"         memory: "256Mi"       limits:         cpu: "500m"         memory: "512Mi"
``` [...] What is Kubernetes 'back-off restarting failed container' error? Here are the fixes

 Kubernetes
 back-off restarting failed container
 error

#### Highlights

 The “Back-Off Restarting Failed Container” error means your container keeps crashing and Kubernetes is delaying restarts.
 Most cases appear as CrashLoopBackOff in Kubernetes.
 Common causes include misconfigurations, missing dependencies, resource limits, and probe issues.
 Key diagnostic tools: `kubectl logs`, `kubectl describe`, and checking Pod YAML.
 Fixes often involve adjusting resource limits, correcting commands/env vars, or fixing liveness/readiness probes.
 Prevent issues with proper health probes, startup delays, and continuous monitoring of restart loops. [...] Once you have identified the root cause, you can apply the appropriate fix for it. Depending on the cause, the fix might involve:

 Adjusting the resource requests and limits: Specify the minimum and maximum amount of CPU and memory that your pod needs using the `resources` field in the pod spec. This will help Kubernetes schedule your pod on a suitable node and prevent it from being evicted or killed due to resource starvation. For example:
- [kube-scheduler: failed to create containerd container: failed to create prepare snapshot dir : stat /data/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots: no such file or directory Warning BackOff kubelet Back-off restarting failed container · Issue #7834 · containerd/containerd · GitHub](https://github.com/containerd/containerd/issues/7834) — version = 2 root = "/data/containerd" state = "/run/containerd" oom_score = 0 [grpc] max_recv_message_size = 16777216 max_send_message_size = 16777216 [debug] level = "info" [metrics] address = "" grpc_histogram = false [plugins] [plugins."io.containerd.grpc.v1.cri"] sandbox_image = "registry.k8s.io/pause:3.7" max_container_log_line_size = -1 [plugins."io.containerd.grpc.v1.cri".containerd] default_runtime_name = "runc" snapshotter = "overlayfs" [plugins."io.containerd.grpc.v1.cri".containerd.runtimes] [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc] runtime_type = "io.containerd.runc.v2" runtime_engine = "" runtime_root = "" [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc.options] systemdCgroup = true [plugins."io.containerd.grpc.v1.cri".registry] [...] Skip to content   
 

## Navigation Menu

Sign in

Appearance settings

Sign in

Sign up

Appearance settings

You signed in with another tab or window. Reload to refresh your session. You signed out in another tab or window. Reload to refresh your session. You switched accounts on another tab or window. Reload to refresh your session. Dismiss alert

{{ message }}

### Uh oh!

There was an error while loading. Please reload this page.

containerd   /  containerd  Public

 Notifications  You must be signed in to change notification settings
 Fork 4.1k
 Star  21.2k [...] Reactions are currently unavailable

## Activity

Sign up for free to join this conversation on GitHub. Already have an account? Sign in to comment

## Metadata

## Metadata

No one assigned

### Labels

kind/bug

No type

No projects

No milestone

None yet

No branches or pull requests

## Issue actions

You can’t perform that action at this time.
- [containerd: failed to stop container · Issue #9240 · containerd/containerd · GitHub](https://github.com/containerd/containerd/issues/9240) — Title: containerd: failed to stop container · Issue #9240 · containerd/containerd · GitHub
"failed to stop container: context deadline exceeded: unknown". Oct 13 16:12:08 ed-c16-208-221-76 containerd[1548]: time="2023-10-13T16:12:08.020634516Z" level=error msg="Failed to handle backOff event &TaskExit{ContainerID:680d7356661f9f87a602b589bd5cec535bf3a674a65bd38966072b75a779a8fd,ID:680d7356661f9f87a602b589bd5cec535bf3a674a65bd38966072b75a779a8fd,Pid:12412,ExitStatus:0,ExitedAt:2023-10-13 01:10:17.977124706 +0000 UTC,XXX_unrecognized:[],} for 680d7356661f9f87a602b589bd5cec535bf3a674a65bd38966072b75a779a8fd" error="failed to handle container TaskExit event: failed to cleanup container 680d7356661f9f87a602b589bd5cec535bf3a674a65bd38966072b75a779a8fd in task-service: container must be created: failed precondition". version = 2 root = "/var/lib/containerd" state = "/run/containerd" plugin_dir = "" disabled_plugins = [] required_plugins = [] oom_score = 0 [grpc] address = "/run/containerd/containerd.sock" tcp_address = "" tcp_tls_cert = "" tcp_tls_key = "" uid = 0 gid = 0 max_recv_message_size = 16777216 max_send_message_size = 16777216 [ttrpc] address = "" uid = 0 gid = 0 [debug] address = "" uid = 0 gid = 0 level = "" [metrics] address = "" grpc_histogram = false [cgroup] path = "" [timeouts] "io.containerd.timeout.shim.cleanup" = "5s" "io.containerd.timeout.shim.load" = "5s" "io.containerd.timeout.shim.shutdown" = "3s" "io.containerd.timeout.task.state" = "2s" [plugins] [plugins."io.containerd.gc.v1.scheduler"] pause_threshold = 0.02 deletion_threshold = 0 mutation_threshold = 100 schedule_delay = "0s" startup_delay = "100ms" [plugins."io.containerd.grpc.v1.cri"] disable_tcp_service = true stream_server_address = "127.0.0.1" stream_server_port = "0" stream_idle_timeout = "4h0m0s" enable_selinux = true selinux_category_range = 1024 sandbox_image = "k8s.gcr.io/pause:3.1" stats_collect_period = 10 systemd_cgroup = true enable_tls_streaming = false tolerate_missing_hugetlb_controller = true ignore_image_defined_volumes = false netns_mounts_under_state_dir = false max_container_log_line_size = 16384 disable_cgroup = false disable_apparmor = true restrict_oom_score_adj = false max_concurrent_downloads = 3 disable_proc_mount = false unset_seccomp_profile = "" disable_hugetlb_controller = true enable_unprivileged_ports = false enable_unprivileged_icmp = false [plugins."io.containerd.grpc.v1.cri".containerd] snapshotter = "overlayfs" default_runtime_name = "runc" no_pivot = false disable_snapshot_annotations = true discard_unpacked_layers = false [plugins."io.containerd.grpc.v1.cri".containerd.default_runtime] runtime_type = "" runtime_engine = "" runtime_root = "" privileged_without_host_devices = false base_runtime_spec = "" [plugins."io.containerd.grpc.v1.cri".containerd.untrusted_workload_runtime] runtime_type = "" runtime_engine = "" runtime_root = "" privileged_without_host_devices = false base_runtime_spec = "" [plugins."io.containerd.grpc.v1.cri".containerd.runtimes] [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc] runtime_type = "io.containerd.runtime.v1.linux" runtime_engine = "" runtime_root = "" pod_annotations = [] container_annotations = [] privileged_without_host_devices = false base_runtime_spec = "" cni_conf_dir = "/etc/cni/net.d" cni_max_conf_num = 1 [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc.options] NoPivotRoot = false NoNewKeyring = false ShimCgroup = "" IoUid = 0 IoGid = 0 BinaryName = "" Root = "" CriuPath = "" SystemdCgroup = true CriuImagePath = "" CriuWorkPath = "" [plugins."io.containerd.grpc.v1.cri".cni] bin_dir = "/opt/cni/bin" conf_dir = "/etc/cni/net.d" max_conf_num = 1 conf_template = "" ip_pref = "ipv4" [plugins."io.containerd.grpc.v1.cri".registry] [plugins."io.containerd.grpc.v1.cri".registry.mirrors] [plugins."io.containerd.grpc.v1.cri".registry.mirrors."docker.io"] endpoint = ["http...