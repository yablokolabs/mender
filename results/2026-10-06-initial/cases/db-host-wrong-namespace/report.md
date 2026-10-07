# Root cause: Checkout pod crashloop due to ConfigMap db_host mismatch causing healthcheck 500

Service `checkout` in namespace `shop`.

## Root cause
The ConfigMap 'checkout-config' contains an incorrect db_host value 'orders-db.default.svc.cluster.local' instead of the required 'orders-db.shop.svc.cluster.local', causing the /healthz endpoint to return HTTP 500, which fails both liveness and readiness probes and triggers repeated container restarts (exit code 137 = SIGKILL from kubelet after liveness probe failure threshold).

## Mechanism
1. The deployment's checkout container reads DB_HOST from checkout-config via configMapKeyRef at pod creation. 2. The new ReplicaSet checkout-687c777bc5 (pod checkout-687c777bc5-h5ccr) receives the wrong value 'orders-db.default.svc.cluster.local' [from ConfigMap manifest]. 3. The service's healthcheck() validates that db_host ends with '.shop.svc.cluster.local' [service.py healthcheck logic]; the mismatch makes it return (500, 'db host outside cluster domain'). 4. Both livenessProbe and readinessProbe are HTTP GET /healthz on port 8080 [describe probe config]. 5. Probes receive 500, exceeding failureThreshold (3) [events: 'Liveness probe failed: HTTP probe failed with statuscode: 500']. 6. Kubelet kills the container (SIGKILL, exit code 137) and restarts it [event: 'Container checkout failed liveness probe, will be restarted'; container Last State Reason: Error, Exit Code: 137]. 7. Restart repeats the same failure because the env var is unchanged.

Confidence: 0.95 · Labels: configmap_error, probe_failure, healthcheck_failure, wrong_db_host, liveness_probe_failure

## Evidence relied on
- ConfigMap manifest: db_host: orders-db.default.svc.cluster.local
- service.py EXPECTED_DB_SUFFIX = '.shop.svc.cluster.local' and healthcheck returns 500 on suffix mismatch
- Failing pod log: 'starting checkout service (log_level=info, db=orders-db.default.svc.cluster.local, cache=96Mi)' followed by 500 responses
- Working pod logs show db=orders-db.shop.svc.cluster.local and 200 responses
- Events: 'Liveness probe failed: HTTP probe failed with statuscode: 500' and 'Container checkout failed liveness probe, will be restarted'
- Container Last State: Reason: Error, Exit Code: 137

## Tavily sources
Queries: Kubernetes exit code 137 OOMKilled container memory limit 512Mi startup cache 96Mi; healthcheck returns 500 when DB_HOST suffix mismatch expected cluster domain .shop.svc.cluster.local; liveness probe readiness probe /healthz HTTP 500 failure threshold restart loop Kubernetes
- [Fix OOMKilled Containers in Kubernetes | K8s Recipes](https://kubernetes.recipes/recipes/troubleshooting/oom-killed-troubleshooting) — Title: Fix OOMKilled Containers in Kubernetes | K8s Recipes
Understand memory limits, kernel OOM killer behavior, and right-sizing strategies for Kubernetes pods. > 💡 **Quick Answer:** OOMKilled (exit code 137) means your container exceeded its memory limit and the kernel killed it. Fix: increase `resources.limits.memory`, fix memory leaks, or use VPA to auto-right-size. > **Gotcha:** JVM `-Xmx` must be LESS than the container memory limit. If `-Xmx=512m` and limit is `512Mi`, the JVM will be OOMKilled because the JVM uses additional memory beyond heap (metaspace, threads, native). # Real-time memory usage (requires metrics-server)# Real-time memory usage (requires metrics-server)kubectl top pod myapp-abc123 kubectl  top  pod myapp-abc123# NAME CPU(cores) MEMORY(bytes)# NAME CPU(cores) MEMORY(bytes)# myapp-abc123 50m 480Mi# myapp-abc123 50m 480Mi # Check the memory limit # Check the memory limitkubectl get pod myapp-abc123 -o jsonpath='{.spec.containers[0].resources.limits.memory}' kubectl  get  pod myapp-abc123 -o jsonpath='{.spec.containers[0].resources.limits.memory}' # 512Mi # 512Mi. If usage is close to the limit, the container will eventually be OOMKilled. graph TD graph TD A[Container Memory Grows] --> B{Exceeds limit?} A[Container Memory Grows] --> B{Exceeds limit?} B -->|Yes| C[cgroup OOM killer] B -->|Yes| C[cgroup OOM killer] C --> D[Container killed, exit 137] C --> D[Container killed, exit 137] D --> E[Pod restarts] D --> E[Pod restarts] B -->|No but node under pressure| F{Node memory pressure?} B -->|No but node under pressure| F{Node memory pressure?} F -->|Yes| G[Kernel OOM killer] F -->|Yes| G[Kernel OOM killer] G --> H[Lowest priority pod killed] G --> H[Lowest priority pod killed] F -->|No| I[Container runs normally] F -->|No| I[Container runs normally]. resources: resources: requests:  requests: memory: "256Mi" # Scheduler uses this for placement  memory: "256Mi"  # Scheduler uses this for placement limits:  limits: memory: "1Gi" # Hard ceiling — OOMKilled if exceeded  memory: "1Gi"  # Hard ceiling — OOMKilled if exceeded. * **Always set memory limits** — without limits, one container can consume all node memory. * **JVM heap = 75% of container limit** — leave room for non-heap memory. * **Monitor with Prometheus** — `container_memory_working_set_bytes` is what the OOM killer uses. * OOMKilled = container exceeded its cgroup memory limit → exit code 137. * VPA can auto-adjust memory limits — use with HPA by splitting resource control. #oomkilled #memory #resources #troubleshooting #kubernetes.
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
- [OOMKilled (Exit Code 137): Causes and Fix | Kubernetes | DevOpsLesson](https://devopslesson.com/troubleshooting/oomkilled) — Modern JVMs are container-aware and respect cgroup limits, but `MaxRAMPercentage` makes the headroom explicit. Use the percentage rather than a fixed `-Xmx` so the setting survives a limit change.

Crucially, heap is not the whole footprint. Metaspace, thread stacks, direct byte buffers and the JIT code cache all live outside it, which is why a container with `-Xmx512m` and a 512Mi limit is OOMKilled reliably. Leave 25 to 30% for non-heap.

Node.js:

```
env: - name: NODE_OPTIONS value: "--max-old-space-size=384" # for a 512Mi limit 
```

.NET: respects limits when `DOTNET_GCHeapHardLimit` or the container limit is detected, but verify rather than assume on older versions.

## Sizing it properly [...] Because heap is not the whole memory footprint. Metaspace, thread stacks, direct byte buffers, the JIT code cache and the JVM's own overhead all live outside the heap, so a container with `-Xmx512m` and a 512Mi limit will be killed. Use `-XX:MaxRAMPercentage=75` rather than a fixed `-Xmx`, which reserves roughly a quarter of the limit for non-heap usage and automatically adapts if you change the limit later.

What is the difference between OOMKilled and an evicted pod?
- [OOMKilled (Exit Code 137): Causes and How to Fix It](https://cast.ai/blog/oomkilled-exit-code-137) — Quick Answer: OOMKilled / Exit Code 137

 Exit code 137 = 128 + SIGKILL (signal 9). The Linux kernel OOM killer fired against your container.
 Root cause: the container crossed its cgroup memory limit — or the node ran out of physical memory.
 Kubernetes surfaces it as `reason: OOMKilled` in `kubectl describe pod`.
 No graceful shutdown: SIGKILL cannot be caught or ignored.
 The fix is correct per-container memory sizing — not globally raising limits or adding nodes.
 QoS class determines kill priority: `BestEffort` pods die first, `Guaranteed` pods last.
 Three distinct scenarios produce OOMKilled. Each has a different fix.

## Why Kubernetes kills a pod with exit code 137

Three distinct scenarios produce OOMKilled. Conflating them leads to the wrong fix. [...] Skip to content

Cut your cloud bill

Cast AI

Book a demo

Sign in

Start free trial

Cloud cost optimization, Engineering

# OOMKilled and Exit Code 137: Why Kubernetes Kills Your Pods and How to Stop It

Exit code 137 means your container was killed by SIGKILL (signal 9) — 128 + 9. The Linux kernel OOM killer fires SIGKILL when a container exceeds its cgroup memory limit. Kubernetes surfaces this as OOMKilled in pod status. There is no grace period: the process is terminated immediately, mid-execution.

Roberto Pesce

Table of contents

 Will display ToC list here.

## What does OOMKilled (exit code 137) mean? [...] ## Frequently Asked Questions

What does exit code 137 mean in Kubernetes?

Exit code 137 means the container was killed by SIGKILL (signal 9): 128 + 9 = 137. In Kubernetes, this almost always means the Linux kernel OOM killer fired because the container exceeded its cgroup memory limit. Kubernetes reports this as `reason: OOMKilled` in pod status.

How do I find which container was OOMKilled?

Run `kubectl describe pod  -n`  and look for `Reason: OOMKilled, Exit Code: 137` in the Last State section. For cluster-wide visibility: `kube_pod_container_status_last_terminated_reason{reason="OOMKilled"}` in Prometheus.

What is the difference between OOMKilled and Evicted in Kubernetes?
- [Kubernetes OOMKilled: How to Diagnose and Fix It](https://www.plural.sh/blog/kubernetes-oomkilled-how-to-diagnose-and-fix-it) — `kubectl describe pod POD_NAME -n NAMESPACE`

   In the `Containers` section, inspect `State`, `Last State`, `Reason`, `Exit Code`, and restart counts. A previous container state with `Reason: OOMKilled` confirms that the container was terminated for exceeding its available memory. Exit code `137` is consistent with an external termination caused by memory pressure, although the reason field is the more direct Kubernetes signal. This is the first check for confirming an OOMKilled container and for correlating the reason with the exit code.
2. ### Check namespace events

   Events provide timing and context around the failure:

   `kubectl get events -n NAMESPACE --sort-by=.lastTimestamp` [...] Exit code 137 is the numeric result of a process receiving signal 9, or `SIGKILL`. In container environments, it is a standard indicator that the process was killed externally, typically because the system was under memory pressure. That makes 137 useful evidence, but not a complete diagnosis. The code tells you how the process ended. It does not, by itself, tell you whether the container hit its own cgroup limit or whether the node was already out of memory. [...] `OOMKilled` is Kubernetes reporting that a container was terminated after running out of memory. More precisely, the Linux kernel's Out-Of-Memory (OOM) killer stopped the container process because it exceeded the memory available to its control group, commonly the container's configured memory limit. Kubernetes then records the termination reason as `OOMKilled` and exposes exit code `137` for the terminated process. The underlying distinction matters: Kubernetes surfaces the event, but the Linux kernel performs the kill.
- [Health_check/migrations failing in 18.7.1 - Upgrade](https://forum.gitlab.com/t/health-check-migrations-failing-in-18-7-1/132265) — This now returns 500 Internal Server Error. I think this may be related to. Health Check Failing After Upgrade: Database Version Mismatch Due
- [TLS name mismatch error](https://community.cloudflare.com/t/tls-name-mismatch-error/137544) — What's the question here? There is a name mismatch in the TLS certificate, fix that and the health check will go up.
- [HealthCheck returns 500 on unhealthy result · Issue #766](https://github.com/dropwizard/metrics/issues/766) — If there is an unhealthy result then the servlet returns with a 500. The problem is that a 500 indicates an "Internal Server Error" whereas
- [How to Troubleshoot DNS Resolution in Kubernetes Pods](https://oneuptime.com/blog/post/2026-03-20-troubleshoot-dns-kubernetes/view) — ## Verify DNS is Working in a Pod

`# Run a temporary debugging pod with DNS tools:
kubectl run dns-debug --image=infoblox/dnstools:latest --rm -it --restart=Never -- bash
# Inside the pod:
# Test service resolution:
nslookup kubernetes.default.svc.cluster.local
dig kubernetes.default.svc.cluster.local
# Test external resolution:
nslookup google.com
dig google.com
# Check pod's DNS configuration:
cat /etc/resolv.conf
# Should contain:
# nameserver <kube-dns service ClusterIP> (for example, 10.96.0.10)
# search <namespace>.svc.cluster.local svc.cluster.local cluster.local
# options ndots:5`

## CoreDNS Health Check [...] ## CoreDNS Health Check

`# Check CoreDNS pod status:
kubectl -n kube-system get pods -l k8s-app=kube-dns
# All pods should be Running
# Check CoreDNS logs:
kubectl -n kube-system logs -l k8s-app=kube-dns --tail=50
# Check CoreDNS service:
kubectl -n kube-system get svc kube-dns
# CLUSTER-IP usually matches what's in /etc/resolv.conf of pods
# unless NodeLocal DNSCache or custom cluster DNS is configured
# Test CoreDNS directly:
COREDNS_IP=$(kubectl -n kube-system get svc kube-dns -o jsonpath='{.spec.clusterIP}')
kubectl run test-dns --image=busybox --rm -it --restart=Never -- \
nslookup kubernetes.default $COREDNS_IP`

## Common DNS Failures [...] `# Failure 1: NXDOMAIN for service names
# Cause: wrong namespace/service name, missing search domain, or custom resolver settings
# Debug:
kubectl run debug --image=busybox --rm -it --restart=Never -- sh
# Inside:
nslookup my-service.my-namespace # Short form
nslookup my-service.my-namespace.svc.cluster.local. # FQDN with trailing dot
# Failure 2: DNS timeout (CoreDNS unreachable)
# Check: can the pod reach CoreDNS?
kubectl run debug --image=busybox --rm -it --restart=Never -- sh
# nslookup kubernetes.default 10.96.0.10 # Test a DNS query
# nc -zv 10.96.0.10 53 # Test TCP connect
# dig +tcp @10.96.0.10 kubernetes.default # Test TCP DNS if dig is available
# Failure 3: Slow DNS causing 5-second delays
# This can be caused by glibc A/AAAA lookups or dropped UDP DNS packets
- [Kubernetes http health check not working as expected](https://stackoverflow.com/questions/66064514/kubernetes-http-health-check-not-working-as-expected-500-response-is-ignored) — To investigate this problem, I have added test endpoints to my pod so that I can change the behaviour at runtime: pass (200), fail (500), delay
- [Kubernetes Liveness and Readiness Probes Guide | K8s Recipes](https://kubernetes.recipes/recipes/deployments/kubernetes-probes-liveness-readiness) — to start  failureThreshold: 30 # 30 × 10s = 5 min to start periodSeconds: 10  periodSeconds: 10    # Liveness probe — restart container if this fails  # Liveness probe — restart container if this fails livenessProbe:  livenessProbe: httpGet:  httpGet: path: /healthz  path: /healthz port: 8080  port: 8080 initialDelaySeconds: 0 # Startup probe handles delay  initialDelaySeconds: 0  # Startup probe handles delay periodSeconds: 15  periodSeconds: 15 timeoutSeconds: 3  timeoutSeconds: 3 failureThreshold: 3 # 3 failures → restart  failureThreshold: 3  # 3 failures → restart    # Readiness probe — remove from Service if this fails  # Readiness probe — remove from Service if this fails readinessProbe:  readinessProbe: httpGet:  httpGet: path: /ready  path: /ready port: 8080  port: 8080 [...] livenessProbe: livenessProbe: httpGet:  httpGet: path: /healthz  path: /healthz port: 8080  port: 8080 initialDelaySeconds: 15 # Wait before first probe (default: 0)  initialDelaySeconds: 15 # Wait before first probe (default: 0) periodSeconds: 10 # How often to probe (default: 10)  periodSeconds: 10 # How often to probe (default: 10) timeoutSeconds: 3 # Timeout per probe (default: 1)  timeoutSeconds: 3 # Timeout per probe (default: 1) failureThreshold: 3 # Failures before action (default: 3)  failureThreshold: 3 # Failures before action (default: 3) successThreshold: 1 # Successes to be considered healthy (default: 1)  successThreshold: 1 # Successes to be considered healthy (default: 1) # For readiness: successThreshold can be >1 # For readiness: successThreshold can be >1 # Total time [...] KubernetesRecipes

Buy Now

Deployments beginner ⏱ 10 minutes K8s 1.28+

# Kubernetes Liveness and Readiness Probes Guide

Configure Kubernetes liveness, readiness, and startup probes for health checks. HTTP, TCP, exec probes, timing parameters, and failure threshold tuning.

By Luca Berton • • 📖 5 min read

> 💡 Quick Answer: Three probe types: Liveness (is the container alive? restart if not), Readiness (can it serve traffic? remove from Service if not), Startup (has it started? disable other probes until it passes). Use `httpGet` for web apps, `tcpSocket` for databases, `exec` for custom checks. Always set `initialDelaySeconds` to avoid premature restarts.

## The Problem

Without health probes:
- [Liveness, Readiness, and Startup Probes | Kubernetes](https://kubernetes.io/docs/concepts/workloads/pods/probes) — failureThreshold:  30   periodSeconds: 10  periodSeconds: 10  periodSeconds:  10   livenessProbe:  livenessProbe:  livenessProbe:   httpGet:  httpGet:  httpGet:   path: /healthz  path: /healthz  path:  /healthz   port: 8080  port: 8080  port:  8080   initialDelaySeconds: 10  initialDelaySeconds: 10  initialDelaySeconds:  10   periodSeconds: 5  periodSeconds: 5  periodSeconds:  5   timeoutSeconds: 3  timeoutSeconds: 3  timeoutSeconds:  3   failureThreshold: 3  failureThreshold: 3  failureThreshold:  3   readinessProbe:  readinessProbe:  readinessProbe:   httpGet:  httpGet:  httpGet:   path: /ready  path: /ready  path:  /ready   port: 8080  port: 8080  port:  8080   periodSeconds: 5  periodSeconds: 5  periodSeconds:  5 [...] `failureThreshold`
:   After a probe fails `failureThreshold` times in a row, Kubernetes considers that the overall check has failed: the container is not ready/healthy/live. Defaults to 3. Minimum value is 1. For the case of a startup or liveness probe, if at least `failureThreshold` probes have failed, Kubernetes treats the container as unhealthy and triggers a restart for that specific container. The kubelet honors the setting of `terminationGracePeriodSeconds` for that container. For a failed readiness probe, the kubelet continues running the container that failed checks, and also continues to run more probes; because the check failed, the kubelet sets the `Ready` condition on the Pod to `false`. [...] If you'd like your container to be killed and restarted if a probe fails, then specify a liveness probe, and specify a `restartPolicy` of `Always` or `OnFailure`.

A common pattern for liveness probes is to use the same low-cost HTTP endpoint as for readiness probes, but with a higher `failureThreshold`. This ensures that the pod is observed as not-ready for some period of time before it is hard killed.

### When should you use a readiness probe?

To start sending traffic to a Pod only when a probe succeeds, specify a readiness probe. The readiness probe might be the same as the liveness probe, but the existence of the readiness probe in the spec means that the Pod will start without receiving any traffic and only start receiving traffic after the probe starts succeeding.
- [Troubleshooting Kubernetes Liveness and Readiness Probe Failures](https://resolve.ai/glossary/how-to-debug-kubernetes-probe-issues) — Think about what the probe protects against. Liveness exists for conditions that don't self-resolve, like deadlocks. A container that's slow for 5 seconds and then recovers doesn't need killing. `failureThreshold: 5` with `periodSeconds: 10` requires roughly 50 seconds of continuous failure before a restart, which catches real deadlocks while tolerating transient slowness.

Wrong port, path, or scheme. A probe aimed at port 8080 while the app listens on 8081 fails instantly with "connection refused". A probe pointing at `/healthz` when the app serves `/health` gets a 404. Two subtler versions of the same problem: [...] `successThreshold` is the one people forget. It defaults to 1 and has to stay 1 for liveness and startup probes. On readiness probes, raising it to 2 or 3 requires that many consecutive passes before the pod re-enters the ready state, which stops a marginal pod from flapping in and out of load balancing.

For slow starters, a startup probe buys time without loosening liveness:

```
startupProbe: httpGet: path: /healthz port: web failureThreshold: 30 periodSeconds: 10 
```

Here's a full manifest that puts the rest together: [...] Liveness probes ask "is this container stuck?" On failure, after `failureThreshold` consecutive misses (default: 3), the kubelet kills the container and the pod's `restartPolicy` decides whether it comes back. Repeated kills climb the restart count into `CrashLoopBackOff`. Typical causes are a genuine deadlock or hang, or a probe aggressive enough to kill a busy-but-healthy container.
- [Configure Liveness, Readiness and Startup Probes | Kubernetes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes) — In the configuration file, you can see that the Pod has a single container. The `periodSeconds` field specifies that the kubelet should perform a liveness probe every 3 seconds. The `initialDelaySeconds` field tells the kubelet that it should wait 3 seconds before performing the first probe. To perform a probe, the kubelet sends an HTTP GET request to the server that is running in the container and listening on port 8080. If the handler for the server's `/healthz` path returns a success code, the kubelet considers the container to be alive and healthy. If the handler returns a failure code, the kubelet kills the container and restarts it.

Any code greater than or equal to 200 and less than 400 indicates success. Any other code indicates failure. [...] ```
ports: ports: ports:  - name: liveness-port - name: liveness-port  name:  liveness-port   containerPort: 8080  containerPort: 8080  containerPort:  8080     livenessProbe: livenessProbe:  livenessProbe:   httpGet:  httpGet:  httpGet:   path: /healthz  path: /healthz  path:  /healthz   port: liveness-port  port: liveness-port  port:  liveness-port   failureThreshold: 1  failureThreshold: 1  failureThreshold:  1   periodSeconds: 10  periodSeconds: 10  periodSeconds:  10     startupProbe: startupProbe:  startupProbe:   httpGet:  httpGet:  httpGet:   path: /healthz  path: /healthz  path:  /healthz   port: liveness-port  port: liveness-port  port:  liveness-port   failureThreshold: 30  failureThreshold: 30  failureThreshold:  30   periodSeconds: 10  periodSeconds: 10  periodSeconds:  10
- [GitHub - iam-rayees/Kubernetes-Health-Probes: Practical Kubernetes guide demonstrating Readiness, Liveness, and Startup probes to build resilient, self-healing, production-ready containerized applications. · GitHub](https://github.com/iam-rayees/Kubernetes-Health-Probes) — ## 💓 Phase 2 — Adding Liveness Probe

### What it does

A liveness probe answers a different question: is this container still doing useful work, or has it entered a broken state it can't recover from on its own?

When a liveness probe fails consecutively beyond `failureThreshold`, `kubelet` restarts the container. This is the automatic recovery mechanism — deadlocks, OOM states, infinite loops, corrupted internal state. The liveness probe catches them and gives the container a clean slate.

Do not conflate liveness with readiness. A pod can be alive (liveness passes) but not ready (readiness fails) — this is normal and expected during startup or when waiting on a dependency. They serve different purposes and are evaluated independently. [...] Without startup probe: You're deploying a heavier variant of the app that takes 45 seconds to start. Your liveness probe has `initialDelaySeconds: 30`. At `t=30s` the liveness probe fires, gets a 503 (still starting), and kills the container. It starts again. Gets killed again. CrashLoopBackOff. Infinite loop that could have been avoided.

With all three probes:

 Startup probe gives the container a 300s window — more than enough
 Readiness probe holds the pod out of the Service until `/index.html` returns 200
 Liveness probe detects the nginx failure and restarts the container within ~60 seconds
 The bad pod is replaced cleanly; zero manual intervention, zero pager alerts

## ⌨️ Complete Command Reference

### Generate a base manifest without applying it