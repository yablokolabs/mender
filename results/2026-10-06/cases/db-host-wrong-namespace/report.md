# Root cause: Checkout pod restart loop due to ConfigMap DB_HOST misconfiguration causing healthcheck failures

Service `checkout` in namespace `shop`.

## Root cause
The ConfigMap 'checkout-config' contains an incorrect db_host value 'orders-db.default.svc.cluster.local' instead of the required 'orders-db.shop.svc.cluster.local', causing the application's /healthz endpoint to return HTTP 500, which fails both liveness and readiness probes and triggers a continuous restart loop.

## Mechanism
1. The checkout-config ConfigMap defines db_host=orders-db.default.svc.cluster.local [from manifests/configmap.yaml]. 2. The application's healthcheck() function validates that db_host ends with '.shop.svc.cluster.local' and returns HTTP 500 with error 'db host outside cluster domain' when it does not [from demo/app/service.py]. 3. The failing pod's logs show it starts with 'db=orders-db.default.svc.cluster.local' and all /healthz requests return 500, while healthy pods use 'db=orders-db.shop.svc.cluster.local' and return 200 [from LOGS]. 4. Both livenessProbe and readinessProbe are configured to HTTP GET /healthz on port 8080 [from DESCRIBE probes]. 5. Probe failures (statuscode 500) are recorded in events at 5s and 4s ago [from EVENTS]. 6. Kubernetes kills the container due to liveness probe failure (exit code 137 = SIGKILL from probe termination, not OOM) and restarts it, but the new container inherits the same wrong ConfigMap value, repeating the failure [from EVENTS and container Last State].

Confidence: 0.95 · Labels: configmap_error, wrong_db_host, probe_failure, restart_loop, healthcheck_validation

## Evidence relied on
- db_host: orders-db.default.svc.cluster.local (configmap.yaml)
- EXPECTED_DB_HOST = "orders-db.shop.svc.cluster.local" (check.py)
- healthcheck returns 500 when db_host suffix mismatches (service.py)
- failing pod log: db=orders-db.default.svc.cluster.local -> 500 (LOGS)
- healthy pod log: db=orders-db.shop.svc.cluster.local -> 200 (LOGS)
- Liveness probe failed: HTTP probe failed with statuscode: 500 (EVENTS)
- Readiness probe failed: HTTP probe failed with statuscode: 500 (EVENTS)
- Container killed due to liveness probe failure, exit code 137 (EVENTS, DESCRIBE)

## Tavily sources
Queries: Kubernetes OOM kill exit code 137 memory limit 512Mi startup cache 96Mi checkout service; Kubernetes liveness probe readiness probe HTTP 500 /healthz configmap DB_HOST misconfiguration orders-db.default.svc.cluster.local; Kubernetes pod OOM killed after single restart memory limit insufficient probe failure 500
- [Kubernetes Optimization: Tutorial and Best Practices](https://www.cloudbolt.io/kubernetes-cost-optimization/kubernetes-optimization) — ### Resource limits

Resource limits establish the maximum amount of resources a container can consume, acting as hard constraints enforced by the kubelet and container runtime.

CPU resources are measured in millicores (m), where 1000m equals one CPU core. Memory resources are specified in bytes, with common units including Mi (mebibytes) and Gi (gibibytes).

### Resource termination

When a container exceeds its memory limit, the kernel OOM killer terminates it with SIGKILL, and Kubernetes reports the container status as OOMKilled (exit code 137). CPU limits work differently. Containers that exceed CPU limits experience throttling, where the kernel restricts CPU time allocation based on the Completely Fair Scheduler (CFS) quotas. [...] For example, the configuration below creates a pod where the container’s resource requests exactly match its limits, ensuring predictable resource allocation and maximum eviction protection.

```
# Guaranteed QoS - requests equal limits for all resources  
apiVersion: v1  
kind: Pod  
metadata:  
 name: guaranteed-pod  
spec:  
 containers:  
 - name: app  
 image: nginx  
 resources:  
 requests:  
 memory: "512Mi"  
 cpu: "250m"  
 limits:  
 memory: "512Mi"  
 cpu: "250m"
```

#### Burstable QoS Class [...] Java applications typically allocate heap memory based on host specifications rather than container limits, which can result in memory pressure and OutOfMemory (OOM) Kill events.

```
# Optimized JVM settings for containerized deployment  
- name: JAVA_OPTS  
 value: "-XX:+UseG1GC -XX:MaxRAMPercentage=75.0 -XX:+UseContainerSupport"
```

Python applications suffer from memory fragmentation issues when default malloc settings create excessive memory arenas.

```
# Optimized python settings for containerized deployment  
- name: MALLOC_ARENA_MAX  
 value: 2  
- name: PYTHONUNBUFFERED  
 value: 1  
- name: PYTHONMALLOC  
 value: malloc
```
- [How to Optimize Kubernetes Pod Startup Time](https://oneuptime.com/blog/post/2026-01-19-kubernetes-optimize-pod-startup-time/view) — ## Resource Optimization

### Burst Resources for Startup

`apiVersion: v1
kind: Pod
metadata:
name: burst-resources
spec:
containers:
- name: app
image: myapp:latest
resources:
requests:
cpu: 100m # Low sustained usage
memory: 256Mi
limits:
cpu: "2" # Allow burst during startup
memory: 1Gi # Allow more memory during startup`

### Guaranteed QoS for Critical Apps

`apiVersion: v1
kind: Pod
metadata:
name: guaranteed-pod
spec:
containers:
- name: app
image: myapp:latest
resources:
requests:
cpu: 500m
memory: 512Mi
limits:
cpu: 500m # Same as request = Guaranteed QoS
memory: 512Mi # Best eviction protection under node pressure`

## Application-Level Optimization

### Lazy Initialization [...] ## Image Optimization

### 1. Use Smaller Base Images

`# Bad: Large base image (~1GB)
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y python3
COPY app.py /app/
CMD ["python3", "/app/app.py"]
# Good: Minimal base image (~50MB)
FROM python:3.11-slim
COPY app.py /app/
CMD ["python3", "/app/app.py"]
# Best: Distroless image (~20MB)
FROM python:3.11-slim AS builder
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
FROM gcr.io/distroless/python3-debian12
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY app.py /app/
CMD ["/app/app.py"]`

### 2. Multi-Stage Builds [...] ### 2. Multi-Stage Builds

`# Build stage
FROM golang:1.26 AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o main .
# Runtime stage - tiny final image
FROM scratch
COPY --from=builder /app/main /main
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
ENTRYPOINT ["/main"]`

### 3. Layer Optimization

`# Bad: Creates many layers, cache invalidation issues
FROM node:24-alpine
COPY . /app
RUN npm install
RUN npm run build
# Good: Optimized layer caching
FROM node:24-alpine
WORKDIR /app
# Copy package files first (cached if unchanged)
COPY package.json ./
RUN npm ci
# Copy source code (changes more frequently)
COPY . .
RUN npm run build`

## Image Pulling Strategies
- [OOm Pte Ltd Technology Stack | OOm Pte Ltd Technology Profile](https://rocketreach.co/oom-pte-ltd-technology-stack_b5cc9ea4f42e0a88) — Image 72: Verz DesignVerz Design

 137 

 $20.7m 

Image 73: M-DAQ GlobalM-DAQ Global

 339 

 $7.4m 

Image 74: Kerry ConsultingKerry Consulting

 99 

 $23.8m 

Image 75: Perx TechnologiesPerx Technologies

 41 

 $23.8m 

Image 76: DocDoc Pte. Ltd.DocDoc Pte. Ltd.

 45 

 $9m 

Image 77: TheSmartLocal.comTheSmartLocal.com

 128 

 $8.5m 

Image 78: Boustead Projects LimitedBoustead Projects Limited

 127 

 $505.7m 

Image 79: Rice Communications Pte LtdRice Communications Pte Ltd

 209 

 $5.8m 

Image 80: ShootstaShootsta

 96 

 $31.7m 

Image 81: amc asia!amc asia!

 127 

 $13m 

Image 82: i-dac Asiai-dac Asia

 177 

 $16.3m
- [Kubernetes Resource Optimization: 5 Proven Strategies for 2025](https://scaleops.com/blog/5-kubernetes-resource-optimization-strategies-that-work-in-production) — ### CPU Throttling and OOMKills

Underprovisioning is just as bad. It guarantees poor performance and service disruptions. Nothing ruins a customer’s day faster than a 503 error during checkout because a pod got OOMKilled. It’s a balancing act: while overprovisioning wastes money, resource constraints, like CPU throttling and OOMKilled errors, remain a primary cause of application instability.

### Noisy Neighbor Problems [...] ScaleOps
ScaleOps

Core Platform

Continuously right-sized CPU, memory, and nodes across VPA, HPA, and Karpenter

GPU Platform

Autonomous GPU and memory optimization across every accelerator

What Are You Running?

ScaleOps AI

AI-native tools connecting ScaleOps to your agentic workflows

Technologies

Self-hosted by design, deployable anywhere you run Kubernetes

# Kubernetes Resource Optimization: 5 Proven Strategies That Work in Production

Nic Vermandé

## Table of contents

### Stop paying for resources you don't use

We’ve all been there. You deploy a new microservice, and you hear that little voice reminding you to set CPU and memory requests and limits. And then the sacred ritual begins: the wild guess. 100m? 500Mi? Who knows? [...] ### Noisy Neighbor Problems

Without proper resource limits, one misbehaving pod can monopolize a node’s resources and crash every other service it hosts. This “noisy neighbor” problem is especially dangerous in Kubernetes. Unlike heavily isolated virtual machines, pods are processes sharing the host’s kernel. A single runaway application, if not properly contained by kernel-level safeguards, can choke an entire node.

## 5 Comprehensive Kubernetes Resource Optimization Strategies

This is where we go deep. For each strategy, we’ll break down:

### 1. The Foundation: Getting Requests and Limits Right (Finally)

The Standard Advice: “Set appropriate CPU and memory requests and limits for every container, and rightsize them based on actual usage.”
- [Introducing containers  |  Google Kubernetes Engine (GKE)  |  Google Cloud Documentation](https://docs.cloud.google.com/kubernetes-engine/docs/learn/containers) — ```
apiVersion:  apps/v1 kind:  Deployment metadata:  name:  loadgenerator spec:  replicas:  1  selector:  matchLabels:  app:  loadgenerator  template:  metadata:  labels:  app:  loadgenerator  spec:  containers:  -  env:  -  name:  SERVER_ADDR  value:    -  name:  REQUESTS_PER_SECOND  value:  '10'  image:  gcr.io/google-samples/istio/loadgen:v0.0.1  imagePullPolicy:  Always  name:  main  resources:  limits:  cpu:  500m  memory:  512Mi  requests:  cpu:  300m  memory:  256Mi  restartPolicy:  Always  terminationGracePeriodSeconds:  5
```

Because the `loadgen` doesn't accept incoming requests, the `type` field is set to `ClusterIP`. This type of Service provides a stable IP address that entities in the cluster can use, but the IP address isn't exposed to external clients.
- [Liveness, Readiness, and Startup Probes | Kubernetes](https://kubernetes.io/docs/concepts/workloads/pods/probes) — failureThreshold:  30   periodSeconds: 10  periodSeconds: 10  periodSeconds:  10   livenessProbe:  livenessProbe:  livenessProbe:   httpGet:  httpGet:  httpGet:   path: /healthz  path: /healthz  path:  /healthz   port: 8080  port: 8080  port:  8080   initialDelaySeconds: 10  initialDelaySeconds: 10  initialDelaySeconds:  10   periodSeconds: 5  periodSeconds: 5  periodSeconds:  5   timeoutSeconds: 3  timeoutSeconds: 3  timeoutSeconds:  3   failureThreshold: 3  failureThreshold: 3  failureThreshold:  3   readinessProbe:  readinessProbe:  readinessProbe:   httpGet:  httpGet:  httpGet:   path: /ready  path: /ready  path:  /ready   port: 8080  port: 8080  port:  8080   periodSeconds: 5  periodSeconds: 5  periodSeconds:  5 [...] apiVersion: v1 apiVersion: v1 apiVersion:  v1  kind: Pod kind: Pod  kind:  Pod  metadata: metadata:  metadata:   name: probe-example  name: probe-example  name:  probe-example  spec: spec:  spec:   containers:  containers:  containers:   - name: app  - name: app  name:  app   image: registry.k8s.io/e2e-test-images/agnhost:2.40  image: registry.k8s.io/e2e-test-images/agnhost:2.40  image:  registry.k8s.io/e2e-test-images/agnhost:2.40   ports:  ports:  ports:   - containerPort: 8080  - containerPort: 8080  containerPort:  8080   startupProbe:  startupProbe:  startupProbe:   httpGet:  httpGet:  httpGet:   path: /healthz  path: /healthz  path:  /healthz   port: 8080  port: 8080  port:  8080   failureThreshold: 30  failureThreshold: 30  failureThreshold:  30   periodSeconds: 10  periodSeconds: [...] spec: spec: spec:   terminationGracePeriodSeconds: 3600 # pod-level  terminationGracePeriodSeconds: 3600 # pod-level  terminationGracePeriodSeconds:  3600  # pod-level   containers:  containers:  containers:   - name: test  - name: test  name:  test   image: ...  image: ...  image:  ...      ports:  ports:  ports:   - name: liveness-port  - name: liveness-port  name:  liveness-port   containerPort: 8080  containerPort: 8080  containerPort:  8080      livenessProbe:  livenessProbe:  livenessProbe:   httpGet:  httpGet:  httpGet:   path: /healthz  path: /healthz  path:  /healthz   port: liveness-port  port: liveness-port  port:  liveness-port   failureThreshold: 1  failureThreshold: 1  failureThreshold:  1   periodSeconds: 60  periodSeconds: 60  periodSeconds:  60   # Override pod-level
- [Kubernetes Probes — Health Checks | by Duy Hưng | Medium](https://medium.com/@tdhtp2016/kubernetes-probes-health-checks-0c9a769724c0) — apiVersion: apps/v1kind: Deploymentmetadata:  name: appspec:  selector:    matchLabels:      app: app  replicas: 1  template:    metadata:      labels:        app: app    spec:      containers:      - name: go-web        image: strongjz/go-web:v0.0.2        ports:          - containerPort: 8080        livenessProbe:          httpGet:            path: /healthz            port: 8080          initialDelaySeconds: 5          periodSeconds: 5        readinessProbe:          httpGet:            path: /            port: 8080          initialDelaySeconds: 5          periodSeconds: 5        env:          - name: DB_HOST            value: "postgres"          - name: DB_USER            value: "postgres"          - name: DB_PASSWORD            value: "mysecretpassword"          - name: DB_PORT
- [Kubernetes Liveness and Readiness Probes Guide | K8s Recipes](https://kubernetes.recipes/recipes/deployments/kubernetes-probes-liveness-readiness) — # HTTP GET — most common for web apps # HTTP GET — most common for web appslivenessProbe: livenessProbe: httpGet:  httpGet: path: /healthz  path: /healthz port: 8080  port: 8080 httpHeaders:  httpHeaders: - name: Accept - name: Accept value: application/json  value: application/json # Success: 200-399 status code # Success: 200-399 status code # TCP Socket — for databases, caches, non-HTTP services# TCP Socket — for databases, caches, non-HTTP serviceslivenessProbe: livenessProbe: tcpSocket:  tcpSocket: port: 5432  port: 5432 # Success: TCP connection established # Success: TCP connection established # Exec — run a command inside the container # Exec — run a command inside the containerlivenessProbe: livenessProbe: exec:  exec: command:  command: - sh - sh - -c - -c - pg_isready -U [...] livenessProbe: livenessProbe: httpGet:  httpGet: path: /healthz  path: /healthz port: 8080  port: 8080 initialDelaySeconds: 15 # Wait before first probe (default: 0)  initialDelaySeconds: 15 # Wait before first probe (default: 0) periodSeconds: 10 # How often to probe (default: 10)  periodSeconds: 10 # How often to probe (default: 10) timeoutSeconds: 3 # Timeout per probe (default: 1)  timeoutSeconds: 3 # Timeout per probe (default: 1) failureThreshold: 3 # Failures before action (default: 3)  failureThreshold: 3 # Failures before action (default: 3) successThreshold: 1 # Successes to be considered healthy (default: 1)  successThreshold: 1 # Successes to be considered healthy (default: 1) # For readiness: successThreshold can be >1 # For readiness: successThreshold can be >1 # Total time [...] to start  failureThreshold: 30 # 30 × 10s = 5 min to start periodSeconds: 10  periodSeconds: 10    # Liveness probe — restart container if this fails  # Liveness probe — restart container if this fails livenessProbe:  livenessProbe: httpGet:  httpGet: path: /healthz  path: /healthz port: 8080  port: 8080 initialDelaySeconds: 0 # Startup probe handles delay  initialDelaySeconds: 0  # Startup probe handles delay periodSeconds: 15  periodSeconds: 15 timeoutSeconds: 3  timeoutSeconds: 3 failureThreshold: 3 # 3 failures → restart  failureThreshold: 3  # 3 failures → restart    # Readiness probe — remove from Service if this fails  # Readiness probe — remove from Service if this fails readinessProbe:  readinessProbe: httpGet:  httpGet: path: /ready  path: /ready port: 8080  port: 8080
- [Troubleshooting Kubernetes Liveness and Readiness Probe Failures](https://resolve.ai/glossary/how-to-debug-kubernetes-probe-issues) — The test is to `kubectl exec` into the pod and curl the health endpoint twice, once on `localhost` and once on the pod IP, because the pod IP is what the kubelet actually probes. Localhost passing while the pod IP fails usually means the app is bound to 127.0.0.1. Both passing while probes still fail points outside the pod. Check the mesh first, then the CNI. And if the image has no curl, `kubectl debug` with an ephemeral container gets you a shell.

### Probe misconfiguration [...] 1. The app serves HTTPS but the probe's scheme is HTTP
2. The health endpoint sits behind auth middleware that returns 401 or 403, both of which land outside the 200 to 399 success range.

These mismatches creep in when application code changes without the manifest, or when manifests get copied between apps. Named ports add a layer of complexity as a probe can reference a `containerPort` by name, so the mismatch hides behind the name.

```
livenessProbe: httpGet: path: /healthz # Does this path exist? port: web # Which containerPort does "web" resolve to? scheme: HTTPS # Only if the app actually serves TLS on this port 
``` [...] ### Probe misconfiguration

Probes start before the application is listening. If a container needs 30 seconds to load configuration, connect to databases, and warm caches, but the liveness probe starts after 5, the probe fails, the kubelet restarts the container, and the whole cycle repeats. Sometimes the process isn't even listening yet, so instead of a timeout you get "connection refused". Either way, the events look like:

```
Warning Unhealthy Liveness probe failed: connection refused Normal Killing Container failed liveness probe, will be restarted 
```
- [Configure Liveness, Readiness and Startup Probes | Kubernetes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes) — apiVersion: v1 apiVersion: v1 apiVersion:  v1  kind: Pod kind: Pod  kind:  Pod  metadata: metadata:  metadata:   name: h2c-app  name: h2c-app  name:  h2c-app  spec: spec:  spec:   containers:  containers:  containers:   - name: app  - name: app  name:  app   image: registry.k8s.io/e2e-test-images/agnhost:2.64.0  image: registry.k8s.io/e2e-test-images/agnhost:2.64.0  image:  registry.k8s.io/e2e-test-images/agnhost:2.64.0   command: ["/agnhost", "h2c-server", "--port=8080"]  command: ["/agnhost", "h2c-server", "--port=8080"]  command:  ["/agnhost",  "h2c-server",  "--port=8080"]   ports:  ports:  ports:   - containerPort: 8080  - containerPort: 8080  containerPort:  8080   livenessProbe:  livenessProbe:  livenessProbe:   httpGet:  httpGet:  httpGet:   path: /healthz  path: /healthz  path: [...] ```
ports: ports: ports:  - name: liveness-port - name: liveness-port  name:  liveness-port   containerPort: 8080  containerPort: 8080  containerPort:  8080     livenessProbe: livenessProbe:  livenessProbe:   httpGet:  httpGet:  httpGet:   path: /healthz  path: /healthz  path:  /healthz   port: liveness-port  port: liveness-port  port:  liveness-port   failureThreshold: 1  failureThreshold: 1  failureThreshold:  1   periodSeconds: 10  periodSeconds: 10  periodSeconds:  10     startupProbe: startupProbe:  startupProbe:   httpGet:  httpGet:  httpGet:   path: /healthz  path: /healthz  path:  /healthz   port: liveness-port  port: liveness-port  port:  liveness-port   failureThreshold: 30  failureThreshold: 30  failureThreshold:  30   periodSeconds: 10  periodSeconds: 10  periodSeconds:  10 [...] You can see the source code for the server in server.go.

For the first 10 seconds that the container is alive, the `/healthz` handler returns a status of 200. After that, the handler returns a status of 500.
- [Why Pods Get OOMKilled in Kubernetes (And Why Memory Limits Won’t Save You)](https://medium.com/@pillarslive/why-pods-get-oomkilled-in-kubernetes-and-why-memory-limits-wont-save-you-5891b8f338ea) — # Inside container  
dd if=/dev/zero of=/tmp/large-file bs=1M count=500  
# This creates a 500MB file, and Linux caches it in memory  
# That cache counts toward your container's memory usage
A batch processing job that read gigabyte-sized CSV files experienced this. The file cache pushed memory usage over the limit, even though the application itself used minimal memory. The solution was either increasing limits to account for cache, or using direct I/O flags to bypass the cache.

## Practical Recommendations

### For Memory Limits [...] ## The Incident

The incident started like most do: at 3 a.m., a PagerDuty alert — the order processing service was down again. The on-call engineer opened a laptop and checked the Kubernetes dashboard. The pattern was familiar: pods were restarting every few minutes, and the logs showed the same message the team had already seen several times before:

`OOMKilled: Container was killed due to memory pressure`

Memory limits were set. They had always been set. But that, it turned out, was not enough.

A memory limit does not prevent a container from running out of memory. It defines the point at which the container can be killed. In some cases, setting limits too close to real usage can make OOMKills more frequent, not less. [...] apiVersion: apps/v1  
kind: Deployment  
metadata:  
 name: order-processor  
spec:  
 template:  
 spec:  
 containers:  
 - name: processor  
 image: order-processor:v2.3  
 resources:  
 requests:  
 memory: "1Gi"  
 cpu: "500m"  
 limits:  
 memory: "2Gi"  
 cpu: "1000m" # requests ≠ limits → Burstable QoS
The application was a Node.js service processing order webhooks. Under normal load, memory usage hovered around `800MB`. A `2Gi` limit felt like plenty of headroom.

## Two Types of Memory Kills

There are two distinct scenarios that can kill your pods:

### 1. Container-Level OOMKill
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

Add an optional lightweight HTTP health endpoint to the scheduler:
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

Prometheus alert for proactive OOM detection: Track `container_memory_working_set_bytes` against memory limits. Alert at 80% — that’s your warning window before the kernel OOM killer fires. [...] ### Out-of-memory restarts

Exit code 137 with `OOMKilled: true` in `lastState` means the Linux kernel terminated the container for exceeding its memory limit. See our deep-dive: OOMKilled in Kubernetes.

Setting limits correctly is harder than it looks. In our 2026 Kubernetes Optimization Report, clusters averaged around 20% memory utilization — heavily overprovisioned overall, yet individual pods were still undersized. In one representative cluster analyzed for our 2026 Kubernetes Optimization Report, we recorded 40–50 OOM kills per hour — spiking above 80 during peak load. After deploying automated rightsizing, the rate dropped to near zero.
- [Kube-probe Liveness probe failed: HTTP 500](https://drdroid.io/stack-diagnosis/kube-probe-liveness-probe-failed--http-500) — When a liveness probe fails consistently, Kubernetes will restart the pod to try and recover from the error. This can lead to application downtime if not
- [5 Ways You Can Diagnose & Prevent OOMKilled Errors in Kubernetes](https://www.fairwinds.com/blog/5-ways-you-can-diagnose-and-prevent-oomkilled-errors-in-kubernetes) — ## Optimize the container to reduce memory usage

Memory limits play a crucial role in preventing OOMKilled errors in Kubernetes. When a container or pod requests memory resources, Kubernetes sets a limit on the amount of memory that can be used by that container or pod.

If a container or pod exceeds its memory limit, Kubernetes may terminate the container or pod and generate an OOMKilled error because the system is unable to allocate more memory to the container or pod.

Setting appropriate memory limits can prevent OOMKilled errors by ensuring that containers or pods do not consume more memory than they require. If you find that a container or pod needs more memory than its current limit, you can increase the limit to accommodate the additional memory requirements. [...] Restarting the container or pod can provide a temporary solution to the problem by freeing up memory and CPU resources. However, if you do not address the root cause of the OOMKilled error, the container or pod may continue to experience the same error and be restarted repeatedly.

If you see repeated restarts, it may indicate a persistent issue with the container or pod, such as a memory leak or inadequate resource allocation. In these cases, you need to diagnose the root cause of the error and address it to prevent further OOMKilled errors and keep your Kubernetes cluster running smoothly.

## Diagnose & troubleshoot OOMKilled errors in Kubernetes logs [...] 1. Properly configure memory limits and memory requests for containers and pods to ensure that they have enough resources to run without running out of available memory.
2. Monitor memory usage and performance metrics to identify potential issues before they lead to OOMKilled errors.
3. Ensure that Kubernetes clusters are properly provisioned with sufficient resources to support the applications running on them.
4. Implement tools to detect and respond to OOMKilled errors in real-time.
5. Analyze OOMKilled errors to identify root causes and develop preventative measures.