# Root cause: Checkout pod OOM kill risk due to memory request undersized vs startup cache

Service `checkout` in namespace `shop`.

## Root cause
Container memory request (32Mi) is less than the mandatory startup cache allocation (96Mi), causing Kubernetes to schedule pods on nodes with insufficient memory headroom and risking OOM kills under memory pressure.

## Mechanism
1. The checkout container declares a memory request of 32Mi but a limit of 512Mi. 2. At startup, the service allocates a fixed 96Mi cache (STARTUP_CACHE_BYTES), exceeding the request by 3x. 3. Kubernetes uses the request (32Mi) for scheduling decisions, potentially placing the pod on a node with only ~32Mi allocatable memory. 4. When the 96Mi cache is allocated, actual usage exceeds the node's reserved capacity, triggering memory pressure. 5. The node-level OOM killer may terminate the pod to reclaim memory, even though the pod is under its 512Mi limit, because the node is overcommitted. 6. This manifests as sudden pod termination with OOMKilled status and restart loops [11].

Confidence: 0.75 · Labels: oomkilled, memory_limit, memory_request, startup_cache, scheduling

## Evidence relied on
- Requests: memory: 32Mi / Limits: memory: 512Mi (pod describe)
- STARTUP_CACHE_BYTES = 96 * 1024 * 1024  # simulated startup cache; the limit must fit it (service.py)
- memory limit {limit} below required {MIN_MEMORY_LIMIT_MIB}Mi (startup cache alone is 96Mi) (check.py)
- memory limit sizing relative to the startup cache (triage)
- If the application grows beyond that limit, the kernel can terminate it [11]

## Tavily sources
Queries: Kubernetes secret key length validation ConfigError 32 characters minimum startup; DB_HOST domain validation cluster.local suffix healthcheck 500 error; memory limit 512Mi startup cache 96Mi OOM kill Kubernetes deployment
- [Secrets | Kubernetes](https://kubernetes.io/docs/concepts/configuration/secret) — For instructions, refer to Define container environment variables using Secret data.

It's important to note that the range of characters allowed for environment variable names in pods is restricted. If any keys do not meet the rules, those keys are not made available to your container, though the Pod is allowed to start.

### Container image pull Secrets

If you want to fetch container images from a private repository, you need a way for the kubelet on each node to authenticate to that repository. You can configure image pull Secrets to make this possible. These Secrets are configured at the Pod level.

#### Using imagePullSecrets [...] # Secrets

A Secret is an object that contains a small amount of sensitive data such as a password, a token, or a key. Such information might otherwise be put in a Pod specification or in a container image. Using a Secret means that you don't need to include confidential data in your application code.

Because Secrets can be created independently of the Pods that use them, there is less risk of the Secret (and its data) being exposed during the workflow of creating, viewing, and editing Pods. Kubernetes, and applications that run in your cluster, can also take additional precautions with Secrets, such as avoiding writing sensitive data to nonvolatile storage.

Secrets are similar to ConfigMaps but are specifically intended to hold confidential data.

#### Caution: [...] ### TLS Secrets

The `kubernetes.io/tls` Secret type is for storing a certificate and its associated key that are typically used for TLS.

One common use for TLS Secrets is to configure encryption in transit for an Ingress, but you can also use it with other resources or directly in your workload. When using this type of Secret, the `tls.key` and the `tls.crt` key must be provided in the `data` (or `stringData`) field of the Secret configuration, although the API server doesn't actually validate the values for each key.

As an alternative to using `stringData`, you can use the `data` field to provide the base64 encoded certificate and private key. For details, see Constraints on Secret names and data.

The following YAML contains an example config for a TLS Secret:
- [Secret and ConfigMap should limit # of keys · Issue #19969 · kubernetes/kubernetes · GitHub](https://github.com/kubernetes/kubernetes/issues/19969) — Skip to content   
 
 

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

# Secret and ConfigMap should limit # of keys #19969

Copy link

Copy link

Closed

Closed

Secret and ConfigMap should limit # of keys#19969

Copy link

Labels [...] Copy link

Labels

lifecycle/frozenIndicates that an issue or PR should not be auto-closed due to staleness.Indicates that an issue or PR should not be auto-closed due to staleness.priority/backlogHigher priority than priority/awaiting-more-evidence.Higher priority than priority/awaiting-more-evidence.sig/api-machineryCategorizes an issue or PR as relevant to SIG API Machinery.Categorizes an issue or PR as relevant to SIG API Machinery.

## Description

@thockin

thockin

opened on Jan 22, 2016

Issue body actions

I think it's best to say "max 1000 keys, max key size is 256 characters. max total size of keys + data is 1 MB" or similar.

@pmorie promises to do this unless someone gets there first.

Reactions are currently unavailable

## Activity [...] Reactions are currently unavailable

## Activity

Sign up for free to join this conversation on GitHub. Already have an account? Sign in to comment

## Metadata

## Metadata

### Assignees

No one assigned

### Labels

lifecycle/frozenIndicates that an issue or PR should not be auto-closed due to staleness.Indicates that an issue or PR should not be auto-closed due to staleness.priority/backlogHigher priority than priority/awaiting-more-evidence.Higher priority than priority/awaiting-more-evidence.sig/api-machineryCategorizes an issue or PR as relevant to SIG API Machinery.Categorizes an issue or PR as relevant to SIG API Machinery.

No type

No projects

No milestone

None yet

No branches or pull requests

## Issue actions

You can’t perform that action at this time.
- [LiveKit Server Startup Error: Secret Key Length and Redis Connection Issues · Issue #2582 · livekit/livekit · GitHub](https://github.com/livekit/livekit/issues/2582) — Title: LiveKit Server Startup Error: Secret Key Length and Redis Connection Issues · Issue #2582 · livekit/livekit · GitHub
## Navigation Menu. # Search code, repositories, users, issues, pull requests... You signed in with another tab or window. Reload to refresh your session. You signed out in another tab or window. Reload to refresh your session. You switched accounts on another tab or window. Reload to refresh your session. * Notifications  You must be signed in to change notification settings. # LiveKit Server Startup Error: Secret Key Length and Redis Connection Issues #2582. LiveKit Server Startup Error: Secret Key Length and Redis Connection Issues#2582. ## Description. opened on Mar 17, 2024. I'm encountering a couple of issues when trying to start the LiveKit server on my environment. Below are the error logs and details regarding the issues:. 1. **Secret Key Length Error**. * During the startup, the LiveKit server logs an error related to the secret key length being too short. The exact log message is as follows:. 2024-03-17T04:59:09.818Z ERROR livekit config/config.go:668 secret is too short, should be at least 32 characters for security {"apiKey": "apioenimkey"}. * It seems that the validation step for the secret/API key requires it to be at least 32 characters long. However, I'm unsure if this requirement has changed recently or if there's a specific format the key needs to follow. * Following the secret key length error, there's also an issue with connecting to Redis. The log indicates that the connection is refused:. 2024-03-17T04:59:09.820Z INFO livekit redis/redis.go:133 connecting to redis {"simple": true, "addr": "172.20.189.167:6379"} unable to connect to redis: dial tcp 172.20.189.167:6379: connect: connection refused. * This issue occurs despite the Redis server being up and running, and accessible from other services within the same network. I would appreciate any guidance or recommendations on resolving these issues. Specifically, I'm looking for:. * Confirmation on the secret/API key length requirement and any format it needs to comply with. * Suggestions on troubleshooting the Redis connection issue, considering the server is operational and there haven't been recent changes to its configuration or network access rules. ## Metadata. ## Metadata. No branches or pull requests. ## Issue actions. You can’t perform that action at this time.
- [Kubernetes secret for encryption key](https://github.com/glassflow/clickhouse-etl/raw/refs/heads/main/docs/app/release-notes/v2.7.0/page.mdx) — description: Release notes for the GlassFlow ClickHouse ETL v2.7.0 - Enterprise-grade encryption, improved security, and enhanced schema validation. Version 2.7.0 introduces \*\*enterprise-grade encryption\*\* for sensitive pipeline data, improved security architecture with Kubernetes secrets integration, and enhanced schema validation capabilities. This release focuses on making GlassFlow more secure and compliant for enterprise environments while improving data integrity and validation. GlassFlow now provides \*\*AES-256-GCM encryption\*\* for sensitive pipeline data stored in PostgreSQL:. - \*\*Encryption key management\*\* - Encryption keys can be provided via Kubernetes secrets or environment variables. Pipeline configurations have been moved from Kubernetes CRDs to \*\*Kubernetes Secrets\*\* for better security:. - \*\*Pipeline config as secrets\*\* - Pipeline JSON configurations are now stored as Kubernetes secrets instead of in CRDs, and the Kubernetes operator reads pipeline configurations from these secrets. - \*\*Improved RBAC\*\* - Better access control through Kubernetes RBAC policies for secret access. This change provides better security isolation and allows organizations to enforce stricter access controls on pipeline configurations. Schema validation has been significantly improved for better data integrity:. - \*\*Comprehensive validation\*\* - Enhanced validation of pipeline schemas and field mappings. - \*\*Improved error handling\*\* - Better error handling and default value handling for transformations. - \*\*Better developer experience\*\* - Improved developer experience for API integration. ### Encryption Configuration. Encryption can be configured via Kubernetes secrets or environment variables:. # Kubernetes secret for encryption key. ### Pipeline Configuration Storage. Pipeline configurations are now stored as Kubernetes secrets:. The API automatically manages these secrets when pipelines are created or updated. - \*\*Secret migration\*\* - Pipeline configurations will be automatically migrated to secrets format. - \*\*Encryption key\*\* - New optional encryption key configuration via secrets or environment variables. - \*\*Secret management\*\* - Pipeline configurations are now managed as Kubernetes secrets. - \*\*Better deduplication\*\* - Fixed async publish limits improve deduplication throughput. - \*\*Improved validation\*\* - Enhanced schema validation with better error handling. 2. \*\*Configure encryption\*\* - Set up encryption keys via Kubernetes secrets or environment variables. 5. \*\*Review security\*\* - Verify that pipeline configurations are stored as secrets. For a complete list of all changes, improvements, and bug fixes in v2.7.0, see our GitHub release v2.7.0.
- [Understanding Kubernetes Secrets: A Comprehensive Guide](https://www.perfectscale.io/blog/kubernetes-secrets) — --cert=path/to/cert/file \

--key=path/to/key/file

```

7. Bootstrap Token Secrets

This type is used for tokens that sign well-known ConfigMaps during the bootstrap process. It is used to store tokens used during the node bootstrap process.

```

apiVersion: v1

kind: Secret

metadata:

name: bootstrap-token-6emitej

namespace: kube-system

type: bootstrap.kubernetes.io/token

data:

auth-extra-groups: c3lzdGVtOmJvb3RzdHJhcHBlcnM6a3ViZWFkbTpkZWZhdWx0LW5vZGUtdG9rZW4=

expiration: MjAyMC0wOS0xM1QwNDozOToxMFo=

token-id: NWVtaXRq

token-secret: a3E0Z2lodnN6emduMXAwcg==

usage-bootstrap-authentication: dHJ1ZQ==

usage-bootstrap-signing: dHJ1ZQ==

```

Create using kubectl:

Terminal window

```

kubectl create secret generic bootstrap-token-6emitej \

--type=bootstrap.kubernetes.io/token \ [...] ```

apiVersion: v1

kind: Secret

metadata:

name: tls-secret

type: kubernetes.io/tls

data:

tls.crt: LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUNVakNDQWJzQ0FnMytNQTBHQ1NxR1NJYjNEUUVCQlFVQU1JR2JNUXN3Q1FZRFZRUUdFd0pLVURFT01Bd0cKQTFVRUNCTUZWRzlyZVc4eEVEQU9CZ05WQkFjVEIwTm9kVzh0YTNVeEVUQVBCZ05WQkFvVENFWnlZVzVyTkVSRQpNUmd3RmdZRFZRUUxFdzlYWldKRFpYSjBJRk4xY0hCdmNuUXhHREFXQmdOVkJBTVREMFp5WVc1ck5FUkVJRmRsCllpQkRRVEVqTUNFR0NTcUdTSWIzRFFFSkFSWVVjM1Z3Y0c5eWRFQm1jbUZ1YXpSa1pDNWpiMjB3SGhjTk1UTXcKTVRFeE1EUTFNVE01V2hjTk1UZ3dNVEV3TURRMU1UTTVXakJMTVFzd0NRWURWUVFHREFKS1VERVB...

tls.key: RXhhbXBsZSBkYXRhIGZvciB0aGUgVExTIGNydCBmaWVsZA== # base64 encoded private key

```

Create using kubectl:

Terminal window

```

kubectl create secret tls tls-secret \

--cert=path/to/cert/file \

--key=path/to/key/file [...] Secrets are namespaced resources that can be managed with the Kubernetes API, kubectl, or declarative manifests. They integrate with Kubernetes features such as RBAC, ServiceAccounts, and volume mounts, making it easier to control which workloads can access specific credentials. Although Secrets provide a standardized way to manage confidential data, they are not a complete security solution. By default, Secret values are only Base64-encoded and stored unencrypted in etcd unless encryption at rest is enabled, so additional security controls are required for production environments.

Main takeaways from this article:
- [Kubernetes Application Discovery fails when the cluster ...](https://github.com/gravitational/teleport/issues/39007) — I have located what I believe is the cause - the cluster.local suffix is hardcoded in the getServiceFQDN() function, which the autodiscovery
- [validation for azure local cluster failed in step 150 like stuck.](https://learn.microsoft.com/en-us/answers/questions/5722330/validation-for-azure-local-cluster-failed-in-step) — The cluster validation failures were caused by a local WinRM configuration on each node that restricted remote management access. Although WinRM
- [Resolving Custom Domain Name Resolution Issues for Pods in Kubernetes](https://medium.com/@kaliarch/resolving-custom-domain-name-resolution-issues-for-pods-in-kubernetes-756f58534f4a) — Updated Corefile with`hosts`Directive:

.:53 {  
 errors  
 health  
 ready  
 hosts { # Add custom host entries here  
 192.168.1.100 api.k8s-cluster.example.com  
 fallthrough # Forward other requests to the next directive  
 }  
 kubernetes cluster.local in-addr.arpa ip6.arpa {  
 pods insecure  
 fallthrough in-addr.arpa ip6.arpa  
 }  
 prometheus :9153  
 forward . 8.8.8.8  
 cache 30  
 loop  
 reload  
 loadbalance  
}
### Method 3: Use the Cluster’s Internal API Server Domain

As an alternative, use Kubernetes’ built-in internal domain for the API server: `kubernetes.default.svc.cluster.local` (maps to the API server’s ClusterIP). This avoids custom domain resolution entirely for API server communication.

## 3.3 Verify and Restart Services [...] Example Corefile Configuration:

.:53 {  
 errors # Log DNS resolution errors  
 health # Expose health check endpoint at :8080  
 ready # Expose readiness probe endpoint at :8181  
 kubernetes cluster.local in-addr.arpa ip6.arpa {  
 pods insecure # Allow pods to resolve other pods by IP  
 fallthrough in-addr.arpa ip6.arpa # Forward unresolved requests  
 }  
 prometheus :9153 # Expose metrics for Prometheus  
 forward . 8.8.8.8 # Forward all unresolvable domains to Google DNS  
 cache 30 # Cache DNS responses for 30 seconds  
 loop # Detect DNS loops  
 reload # Auto-reload configuration on changes  
 loadbalance # Distribute requests across DNS servers  
}
### Step 3: Restart CoreDNS to Apply Changes
- [Troubleshoot DNS resolution errors - Container Service for Kubernetes - Alibaba Cloud Documentation Center](https://www.alibabacloud.com/help/en/ack/ack-managed-and-ack-dedicated/user-guide/dns-troubleshooting-1) — This Product

Container Service for Kubernetes:Troubleshoot DNS resolution errors

# Container Service for Kubernetes:Troubleshoot DNS resolution errors

Diagnose and fix DNS failures in ACK clusters caused by CoreDNS, network, policy, or kernel issues.

## How DNS resolution works

When an application pod sends a DNS query, it follows this path:

The pod sends a DNS query to the address in `/etc/resolv.conf`, which is typically the kube-dns Service IP.

`/etc/resolv.conf`

kube-dns forwards the query to a CoreDNS pod in the `kube-system` namespace.

`kube-system`

For internal domain names ending with `.cluster.local`, CoreDNS resolves from its cache without contacting upstream servers.

`.cluster.local` [...] `.cluster.local`

For external domain names, CoreDNS forwards the query to the upstream DNS servers specified in its configuration. The default upstream servers are `100.100.2.136` and `100.100.2.138`, both deployed in the virtual private cloud (VPC).

`100.100.2.136`
`100.100.2.138`

With NodeLocal DNSCache, queries go to the local cache (`169.254.20.10`) first and fall back to kube-dns only if unresolved.

`169.254.20.10`

## Key concepts [...] ### Domain names of headless Services cannot be resolved

In CoreDNS before 1.7.0, API server network jitter can cause CoreDNS to exit, stopping headless Service record updates. Update to 1.7.0 or later. See [\[Component Updates\] Update CoreDNS](/help/en/ack/product-overview/update-coredns#task-1964489).

### Domain names of StatefulSet pods cannot be resolved

The StatefulSet pod template must set `serviceName` to the headless Service name. Without this, per-pod DNS names (for example, `pod.headless-svc.ns.svc.cluster.local`) cannot be resolved, even though the Service-level name (for example, `headless-svc.ns.svc.cluster.local`) works. Set `serviceName` in the StatefulSet spec.

`serviceName`
`pod.headless-svc.ns.svc.cluster.local`
`headless-svc.ns.svc.cluster.local`
`serviceName`
- [Healthcheck and liveness probe 500 error - Installation Issues - Passbolt community forum](https://community.passbolt.com/t/healthcheck-and-liveness-probe-500-error/9949) — extraEnvFrom:
- secretRef:
name: passbolt-secrets-env # <- This provides the DATASOURCES_DEFAULT_PASSWORD
## Passbolt deployment parameters
service:
# -- Configure passbolt service type
type: ClusterIP
# -- Annotations to add to the service
annotations: {}
# -- Configure the service ports
ports:
http:
# -- Configure passbolt HTTP service port
port: 80
# -- Configure passbolt HTTP service targetPort
targetPort: 80
# -- Configure passbolt HTTP service port name
name: http
# -- Configure passbolt container livenessProbe
livenessProbe:
# @ignore
httpGet:
port: https
scheme: HTTPS
path: /healthcheck/status.json
httpHeaders:
- name: Host
value: passbolt.local
initialDelaySeconds: 20
periodSeconds: 10
# -- Configure passbolt container RadinessProbe
readinessProbe:
# @ignore
httpGet:
port: https [...] # Healthcheck and liveness probe 500 error

Checklist  
 I have read intro post: About the Installation Issues category  
 I have read the tutorials, help and searched for similar issues  
 I provide relevant information about my server (component names and versions, etc.)  
 I provide a copy of my logs and healthcheck  
 I describe the steps I have taken to trouble shoot the problem  
 I describe the steps on how to reproduce the issue

I’m trying to set up Passbolt for my kubernetes cluster using the Helm chart. I keep getting a 500 error on my healthcheck and liveness probes, which causes the pods to restart infinitely. [...] readinessProbe:
# @ignore
httpGet:
port: https
scheme: HTTPS
httpHeaders:
- name: Host
value: passbolt.local
path: /healthcheck/status.json
initialDelaySeconds: 5
periodSeconds: 10`
- [Kubernetes OOMKilled: How to Diagnose and Fix It](https://www.plural.sh/blog/kubernetes-oomkilled-how-to-diagnose-and-fix-it) — For the first case, imagine a container with a memory limit of 512Mi. If the application grows beyond that limit, the kernel can terminate it even when the Kubernetes node still has unused memory. The container then restarts according to its pod policy, and a deployment may appear healthy at a glance while one or more replicas repeatedly cycle. Transient allocation spikes, unbounded caches, and memory leaks can all produce this pattern. A limit that is too close to normal peak usage leaves little room for legitimate variation. [...] Start by reviewing the workload's recent memory profile and its resource configuration. A useful baseline is the amount of memory the container needs during ordinary operation, including expected concurrency and routine background work. Set the memory request close to that baseline so Kubernetes can schedule the workload on a node with appropriate capacity. Then set a limit that leaves room for legitimate variation. Requests provide a guaranteed allocation, while limits cap maximum consumption. Both values need to reflect how the application actually behaves, not an arbitrary default.

For example, a deployment might begin with a deliberately conservative configuration:

```
resources: requests: memory: "512Mi" limits: memory: "1Gi"
``` [...] Requests and limits serve different purposes. A memory request is the amount Kubernetes uses when scheduling the pod and the amount of memory the container is guaranteed to receive under normal resource accounting. A memory limit is the maximum memory the container may consume. For example:

```
resources: requests: memory: "512Mi" limits: memory: "1Gi" 
```

With this configuration, the scheduler evaluates the pod against a 512 MiB request, while the container is capped at 1 GiB. A request is not a reservation of unlimited burst capacity. And a limit does not guarantee that the node has that amount of physical memory available at every moment. Treating the two fields as interchangeable often produces either poor bin-packing or unexpected OOMKilled restarts.
- [How to Fix OOMKilled in Kubernetes: We Resolved 500+ Cases (2026 Guide) | Tasrie IT Services](https://tasrieit.com/blog/how-to-fix-oomkilled-kubernetes-2026) — Fix: Increase the memory limit:

```
resources: resources: requests:  requests: memory: "512Mi" # Used for scheduling  memory: "512Mi"  # Used for scheduling limits:  limits: memory: "1Gi" # Hard cap — OOMKilled if exceeded  memory: "1Gi"  # Hard cap — OOMKilled if exceeded
```

How to choose the right limit:

 Set the limit to 1.5-2x the typical memory usage
 Monitor actual usage with `kubectl top pod` or Prometheus over several days
 Use Vertical Pod Autoscaler (VPA) to get data-driven recommendations

## Fix for JVM Applications (Java, Kotlin, Scala)

JVM applications are the most common source of OOMKilled we see. The problem is usually that the JVM uses more memory than just the heap, and teams set `-Xmx` equal to the container limit.

### Understanding JVM Memory [...] ### The Fix: Set Heap to 75% of Container Limit

```
env: env: - name: JAVA_OPTS - name: JAVA_OPTS value: "-Xmx768m -Xms256m -XX:MaxMetaspaceSize=128m"  value: "-Xmx768m -Xms256m -XX:MaxMetaspaceSize=128m"resources: resources: requests:  requests: memory: "512Mi"  memory: "512Mi" limits:  limits: memory: "1Gi"  memory: "1Gi"
```

Modern JVM (Java 17+) alternative — use container-aware flags:

```
env: env: - name: JAVA_OPTS - name: JAVA_OPTS value: "-XX:MaxRAMPercentage=75.0 -XX:InitialRAMPercentage=25.0"  value: "-XX:MaxRAMPercentage=75.0 -XX:InitialRAMPercentage=25.0"
```

`-XX:MaxRAMPercentage=75.0` automatically sets the heap to 75% of the detected container memory limit. This is the recommended approach for containerised JVM applications.

### Verify JVM Memory Usage [...] ```
# Check the memory limit # Check the memory limitkubectl get pod <pod-name> -n <namespace> -o jsonpath='{.spec.containers[].resources}' kubectl  get  pod <pod-name> -n < namespace> -o jsonpath='{.spec.containers[].resources}' # Check peak memory usage (if the pod is currently running)# Check peak memory usage (if the pod is currently running)kubectl top pod <pod-name> -n <namespace> --containers kubectl  top  pod <pod-name> -n < namespace> --containers
```

If the memory usage consistently approaches the limit before getting killed, the limit is probably too low.

Fix: Increase the memory limit:
- [Kubernetes OOMKilled: Root Causes and Remediation | CloudBolt](https://www.cloudbolt.io/kubernetes-resource-optimization-platforms/kubernetes-oomkilled) — ```
kubectl describe pod api-server-7d9f4b-xk2np -n production Containers: api-server: State: Running Started: Thu, 14 May 2026 14:22:51 +0000 Last State: Terminated Reason: OOMKilled Exit Code: 137 Started: Thu, 14 May 2026 13:41:07 +0000 Finished: Thu, 14 May 2026 14:22:43 +0000 Restart Count: 4 Limits: memory: 512Mi Requests: memory: 256Mi QoS Class: Burstable Events: Type Reason Age Message Warning BackOff 42m (x3 over 81m) Back-off restarting failed container api-server
```

Key insight: The `Finished` timestamp and the Prometheus memory timeline are the two data points that separate a bad limit from a leak and should be considered together to determine the root cause..

Stop Setting Kubernetes Requests and Limits

LEARN MORE

## Distinguishing OOMKilled from other crash causes [...] ## How the Linux OOM killer terminates containers

Kubernetes memory limits are not enforced by the control plane. The Linux kernel enforces them through cgroups. When you set `resources.limits.memory` on a container, Kubernetes writes that value to memory.max in the container’s cgroup (memory.limit\_in\_bytes on older cgroup v1 systems). From there, the kernel tracks allocation against that boundary, and once the process crosses it, the kernel’s cgroup OOM killer fires. The kill occurs regardless of the node’s free memory, unlike the system-wide OOM killer, which responds to memory exhaustion across the entire node. [...] ### VPA

The Kubernetes Vertical Pod Autoscaler reviews historical usage and generates updated recommendations for requests and limits. With `updateMode: Auto`, it applies them directly:

```
kubectl get vpa api-server -n production NAME MODE CPU MEM PROVIDED AGE api-server Auto 250m 512Mi True 14d
```

For workloads with stable usage, VPA’s default 8-day lookback provides accurate results and eliminates the manual step. However, it is less useful for irregular or periodic workloads. A recommendation built from 8 days of low traffic is too low for the next monthly reporting run.

### ML-based rightsizing
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

The request helps Kubernetes choose a node. The limit defines the approximate maximum memory usage before the container may be killed. [...] Example:

resources:  
 limits:  
 memory: "1Gi"
Kubernetes documents that memory limits are enforced reactively: a container can be killed when it uses more than its memory limit and the kernel detects memory pressure.

### The Important Relationship

Memory request → affects SCHEDULING  
Memory limit → affects RUNTIME KILL boundary
Example:

resources:  
 requests:  
 memory: "512Mi"  
 limits:  
 memory: "1Gi"
This means:

   Kubernetes schedules based on `512Mi`
   The container may use more than `512Mi` if available
   If memory usage grows beyond `1Gi`, the container may be OOMKilled

### Practical Memory Sizing Example

Suppose your API memory usage looks like this:
- [Tackling Kubernetes Out-of-Memory (OOM) Kills Without Blindly Increasing Resource Limits | CloudAtler Blog](https://cloudatler.com/blog/tackling-kubernetes-out-of-memory-oom-kills-without-blindly-increasing-resource-limits) — ```
apiVersion: v1 kind: LimitRange metadata: name: core-limits namespace: payment-processing spec: limits: - default: memory: "1Gi" cpu: "500m" defaultRequest: memory: "512Mi" cpu: "200m" max: memory: "4Gi" cpu: "2" min: memory: "128Mi" cpu: "100m" type: Container
```

By enforcing a maximum memory limit of 4 GiB at the namespace level, the platform team prevents any individual deployment from requesting excessive node memory, containing potential memory leaks or misconfigurations within safe boundaries.

## How CloudAtler Unifies Performance, FinOps, and Security [...] It is a scenario familiar to every site reliability engineer (SRE) and cloud architect: a critical production microservice suddenly drops, throwing an `OOMKilled` status with `Exit Code 137`. The immediate pressure to restore service availability often leads to a quick, brute-force mitigation—doubling the memory limit in the deployment's Helm chart or Kubernetes manifest. While this temporary fix may quiet the alerting system, it introduces a insidious architectural anti-pattern that directly undermines both enterprise financial operations (FinOps) and cluster scheduling efficiency.