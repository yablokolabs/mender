# Root cause: Checkout pod stuck Pending due to excessive CPU request (32 cores) exceeding single-node capacity

Service `checkout` in namespace `shop`.

## Root cause
Deployment manifest specifies container resources.requests.cpu=32 and resources.limits.cpu=32, which exceeds the cluster's single-node CPU capacity, causing the scheduler to reject the new ReplicaSet's pod with 'Insufficient cpu'.

## Mechanism
1. A new Deployment rollout created ReplicaSet checkout-854c6bdd48 with container CPU request=32 and limit=32 (from deploy.yaml). 2. The cluster has only one node (mender-control-plane) which cannot satisfy a 32-core request. 3. The scheduler evaluates the pod and emits FailedScheduling events: '0/1 nodes are available: 1 Insufficient cpu' [1][2]. 4. The pod checkout-854c6bdd48-6fpv9 remains Pending with PodScheduled=False. 5. The older ReplicaSet checkout-776f46c77 (cpu request=100m, limit=1) continues running two healthy pods.

Confidence: 0.95 · Labels: cpu_request_excessive, scheduling_failure, manifest_misconfig, insufficient_cpu

## Evidence relied on
- Events: FailedScheduling pod/checkout-854c6bdd48-6fpv9 0/1 nodes are available: 1 Insufficient cpu
- DESCRIBE checkout-854c6bdd48-6fpv9: Limits.cpu=32, Requests.cpu=32
- DESCRIBE checkout-776f46c77-kqc8b: Limits.cpu=1, Requests.cpu=100m
- MANIFESTS deploy.yaml: resources.requests.cpu=32, resources.limits.cpu=32
- Search [1]: Pending phase, scheduler rejects with Insufficient cpu
- Search [2]: Pod with cpu 1.1 fails on node capacity 1

## Tavily sources
Queries: Kubernetes pod Pending Insufficient cpu request 32 cores node capacity scheduling failure; Kubernetes resource requests cpu limit exceeds node capacity known issue troubleshooting; checkout service cpu request 32 cores deployment manifest misconfiguration
- [Kubernetes pod stuck Pending: scheduling failures explained](https://www.netdata.cloud/guides/kubernetes/kubernetes-pod-pending) — ## What this means

In Kubernetes, Pending is the phase before a pod is bound to a node. The scheduler watches for pods with an empty `spec.nodeName` and evaluates them against nodes through the Filter phase (hard constraints) and Score phase (soft preferences). If every node fails filtering, the pod moves to the unschedulable queue and retries with exponential backoff.

A pod stuck Pending from scheduling failure has `PodScheduled` condition `False` with reason `Unschedulable`. The Events section of `kubectl describe pod` contains the rejection reason, such as `Insufficient cpu` or `node(s) had untolerated taint`. If there is no FailedScheduling event, the scheduler may not be running, or the pod may target a custom scheduler that does not exist. [...] 3. Determine if the rejection is global or selective. `Insufficient cpu` on all nodes means the cluster is capacity-constrained. A taint or node affinity error affects only a subset of nodes. Scale the cluster for global rejections; change constraints for selective rejections.
4. Compare pod requests to node allocatable. The scheduler subtracts existing pod requests from `status.allocatable` to compute headroom. Run `kubectl describe node` and check the `Allocated resources` section. If CPU or memory requests are at or near allocatable, no new pods requesting those resources can land. `kubectl top nodes` shows usage, which can be much lower than requests. [...] flowchart TD A[Pod stuck Pending] --> B{kubectl describe pod Events} B -->|FailedScheduling: Insufficient cpu/memory| C[Check node allocatable vs requests] B -->|FailedScheduling: untolerated taint| D[Check node taints and pod tolerations] B -->|FailedScheduling: node affinity mismatch| E[Check node labels and pod affinity] B -->|FailedScheduling: unbound PVC| F[Check PVC phase and StorageClass] B -->|FailedScheduling: anti-affinity| G[Check topology and replica count] B -->|No FailedScheduling event| H[Check scheduler health and spec.schedulerName] C --> I[Scale cluster or right-size requests] D --> J[Add toleration or remove taint] E --> K[Align labels or relax rule] F --> L[Fix provisioner or use WaitForFirstConsumer] G --> M[Relax rule or add topology] H --> N[Restore scheduler or
- [Resource Management for Pods and Containers | Kubernetes](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers) — In the preceding example, the Pod named "frontend" fails to be scheduled due to insufficient CPU resource on any node. Similar error messages can also suggest failure due to insufficient memory (PodExceedsFreeMemory). In general, if a Pod is pending with a message of this type, there are several things to try:

 Add more nodes to the cluster.
 Terminate unneeded Pods to make room for pending Pods.
 Check that the Pod is not larger than all the nodes. For example, if all the nodes have a capacity of `cpu: 1`, then a Pod with a request of `cpu: 1.1` will never be scheduled.
 Check for node taints. If most of your nodes are tainted, and the new Pod does not tolerate that taint, the scheduler only considers placements onto the remaining nodes that don't have that taint. [...] ## Troubleshooting

### My Pods are pending with event message `FailedScheduling`

If the scheduler cannot find any node where a Pod can fit, the Pod remains unscheduled until a place can be found. An Event is produced each time the scheduler fails to find a place for the Pod. You can use `kubectl` to view the events for a Pod; for example:

```
kubectl describe pod frontend | grep -A 9999999999 Events kubectl describe pod frontend | grep -A 9999999999 Events | 9999999999
```

```
Events: Type Reason Age From Message ---- ------ ---- ---- ------- Warning FailedScheduling 23s default-scheduler 0/42 nodes available: insufficient cpu 
```
- [Kubernetes Pods not scheduled due to "Insufficient CPU" when CPU resources are available · Issue #33777 · kubernetes/kubernetes · GitHub](https://github.com/kubernetes/kubernetes/issues/33777) — Environment:

 Cloud provider or hardware configuration: AWS, masters (Count: 3, Size: m3.medium), minions (Count 5, Size m4.xlarge)
 OS (e.g. from /etc/os-release): 14.04.5 LTS, Trusty Tahr
 Kernel (e.g. `uname -a`): Master: 3.13.0-95-generic Minion: 4.4.0-38-generic
 Install tools: Ansible using modified contrib playbooks: 
 Others:

What happened: When scheduling pods with a low resource request for CPU (15m) We recieve the message "Insufficient CPU" across all nodes attempting to schedule the pod. We are using multi container pods and running a describe pods shows nodes with available resources to schedule the pods. However k8s refuses to schedule across all nodes.  
 kubectl\_output.txt

What you expected to happen: [...] Copy link

Labels

area/nodecontrollerlifecycle/rottenDenotes an issue or PR that has aged beyond stale and will be auto-closed.Denotes an issue or PR that has aged beyond stale and will be auto-closed.sig/schedulingCategorizes an issue or PR as relevant to SIG Scheduling.Categorizes an issue or PR as relevant to SIG Scheduling.

## Description

@armandocerna

armandocerna

opened on Sep 29, 2016

Issue body actions

Kubernetes version (use `kubectl version`): [...] Skip to content   
 
 

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
 Fork 46k
 Star  128k

# Kubernetes Pods not scheduled due to "Insufficient CPU" when CPU resources are available #33777

Copy link

Copy link

Closed

Closed

Kubernetes Pods not scheduled due to "Insufficient CPU" when CPU resources are available#33777

Copy link

Labels
- [Fix GKE Pod Stuck in Pending State Due to Insufficient CPU or Memory Resources](https://oneuptime.com/blog/post/2026-02-17-how-to-fix-gke-pod-stuck-in-pending-state-due-to-insufficient-cpu-or-memory-resources/view) — ```
# Show allocatable resources and current allocation for all nodes kubectl describe nodes | grep -A 5 "Allocated resources"
```

For a more structured view, use kubectl top:

```
# Show actual CPU and memory usage across nodes kubectl top nodes
```

You might see something like this:

```
NAME CPU(cores) CPU% MEMORY(bytes) MEMORY% gke-cluster-pool-abc 1850m 92% 5800Mi 90% gke-cluster-pool-def 1920m 96% 6100Mi 95% gke-cluster-pool-ghi 1780m 89% 5500Mi 85%
```

If all your nodes are above 85-90% actual usage, the cluster is under heavy pressure. For scheduling decisions, still compare your pod's requests against the requested resources already allocated on each node.

## Step 2 - Right-Size Your Resource Requests [...] When a pod is stuck in Pending, run through this list:

1. `kubectl describe pod` - read the scheduling failure message
2. `kubectl top nodes` - check actual node utilization
3. `kubectl top pods` - compare actual usage with configured requests
4. Check if cluster autoscaler is enabled and working
5. Verify your machine type is large enough for the pod's requests
6. Look for resource fragmentation across nodes
7. Review DaemonSet and system pod overhead

Most of the time, it comes down to either over-requesting resources or not having enough nodes. Start with right-sizing your requests, and use the cluster autoscaler as your safety net.

Share this article

Nawaz Dhandala

### Nawaz Dhandala

Author

@nawazdhandala • Feb 17, 2026 • [...] ## On this page

You deploy your workload and it just sits there. The pod status says Pending, and nothing happens. No crash loops, no errors in the container logs - just silence. This is one of the most common issues in GKE, and it almost always comes down to the scheduler not being able to find a node with enough CPU or memory to place your pod.

Let's walk through how to diagnose this, fix it, and prevent it from happening again.

## Confirming the Problem

The first thing to do is check what the scheduler is actually telling you. Run kubectl describe on the stuck pod:

```
# Check the events section for scheduling failures kubectl describe pod your-pod-name -n your-namespace
```

Look at the Events section at the bottom. If you see a message like this, you have a resource shortage:
- [Solving Kubernetes Scheduling Failures: Requests, Taints, and Affinity](https://resolve.ai/glossary/how-to-debug-kubernetes-pod-pending-state) — Check allocatable versus requested resources:

```
kubectl describe nodes | grep -A 5 "Allocated resources" 
```

The gap between "Allocated resources" and "Allocatable" determines what's available for new pods. If your pod's requests exceed this gap on every node, it stays Pending.

Namespaces with ResourceQuotas add another constraint layer. A namespace might have 32Gi memory quota with 30Gi already allocated across existing pods. A new pod requesting 4Gi fails quota admission before the scheduler even evaluates node capacity

```
kubectl describe resourcequota -n  
``` [...] `0/3 nodes are available: insufficient cpu` or `insufficient memory`
 `0/3 nodes are available: 1 node(s) had taint {key: value}, that the pod didn't tolerate`
 `pod has unbound immediate PersistentVolumeClaims`
 `0/3 nodes are available: 1 node(s) didn't match Pod's node affinity/selector`
 `0/3 nodes are available: 3 Insufficient cpu. preemption: 0/3 nodes are available: 3 No preemption victims found for incoming pod`

Each message points to a different constraint failure category.

Resource constraints

Kubernetes schedules based on requests, not actual usage. A pod requesting 4Gi of memory won't schedule if every node has less than 4Gi allocatable or already committed, regardless of actual memory consumption on those nodes.

Check allocatable versus requested resources: [...] ```
kubectl describe resourcequota -n  
```

LimitRanges enforce per-pod or per-container constraints. A pod without explicit requests inherits default values from the LimitRange. These defaults might exceed available node capacity even if the workload's actual needs are minimal.

Pod priority and preemption

When cluster capacity is exhausted, scheduling outcome depends on PriorityClasses. Higher-priority pods can preempt (evict) lower-priority pods to free resources.

A pod stays Pending when:

1. No node has sufficient resources, AND
2. The pod's priority isn't high enough to preempt existing workloads, OR
3. Preemption is disabled for the pod (`preemptionPolicy: Never`), OR
4. No combination of evictions would free sufficient resources without violating PodDisruptionBudgets
- [Kubernetes Resource Requests and Limits — Full Guide](https://devtoolhub.com/kubernetes-resource-requests-and-limits-full-guide) — Background Worker / Batch Job:

```
resources: requests: cpu: "50m" memory: "64Mi" limits: memory: "256Mi" # No CPU limit — let it burst freely 
```

Batch jobs do not have latency requirements. Skip the CPU limit so they finish faster when CPU is available.

## Troubleshooting Resource Issues

Pod stuck in Pending:

```
kubectl describe pod <pod-name> | grep -A 10 "Events:" 
```

If you see `Insufficient cpu` or `Insufficient memory`, the request is too high for any available node. Either lower the request or add more nodes.

OOMKilled pods:

```
kubectl describe pod <pod-name> | grep -A 5 "Last State" # Look for Reason: OOMKilled 
```

Increase memory limit. Check for memory leaks if it keeps growing.

Slow application performance — check CPU throttling: [...] Symptom: Check CPU throttling on your containers:

```
# Install metrics-server first, then kubectl top pods -n production 
```

Or check with cAdvisor metrics in Prometheus:

```
container_cpu_cfs_throttled_seconds_total 
```

If this number is climbing, your CPU limit is too low.

Mistake 3 — Setting memory requests too low

If your memory request is lower than actual usage, the scheduler puts more pods on a node than it can handle. When memory runs out, pods start getting evicted.

Mistake 4 — Setting limits without requests [...] CPU is compressible.

If a container hits its CPU limit, the kernel throttles it. The container slows down. It does not crash. It does not restart. It just runs slower until CPU is available.

This can silently destroy your application’s performance. A latency-sensitive API hitting its CPU limit will have slower response times without any obvious error in your logs.

Memory is not compressible.

If a container exceeds its memory limit, the kernel kills it immediately with an OOM (Out of Memory) kill. The pod restarts. You see `OOMKilled` in the pod status.

```
# Check if a pod was OOMKilled kubectl describe pod <pod-name> | grep -A 5 "Last State" 
```

Output:

```
Last State: Terminated Reason: OOMKilled Exit Code: 137 
```
- [Why Your Kubernetes Pods Keep Getting Rejected: The Resource Management Guide You Actually Need](https://medium.com/@christian.dussol/why-your-kubernetes-pods-keep-getting-rejected-the-resource-management-guide-you-actually-need-48ea965eb038) — # Monitor quota usage  
kubectl describe resourcequota -n your-namespace  
  
# Check for limit violations  
kubectl get events --field-selector reason=FailedScheduling  
  
# Monitor actual vs requested resources  
kubectl top pods -n your-namespace  
  
# Check Kyverno policy reports  
kubectl get policyreport -A
## Troubleshooting

## Common Error Messages and Solutions

### 1. “exceeded quota: requests.cpu”

# Problem: ResourceQuota limit reached  
# Solution: Check current usage  
kubectl describe resourcequota -n your-namespace  
  
# Find resource-heavy pods  
kubectl top pods -n your-namespace --sort-by=cpu  
# Options:  
# - Delete unused pods  
# - Reduce resource requests  
# - Increase quota (if justified)
### 2. “maximum cpu usage per Container is 4, but limit is 6” [...] 37.   2. LimitRange Best Practices
38.   3. ResourceQuota Strategy
39.   4. Kyverno Policy Best Practices
40.   5. Monitoring and Alerting
41.   Troubleshooting
42.   Common Error Messages and Solutions
    1.   1. “exceeded quota: requests.cpu”
    2.   2. “maximum cpu usage per Container is 4, but limit is 6”
    3.   3. Pod stuck in “Pending” state
    4.   4. “admission webhook ‘validate.kyverno.svc’ denied the request”
    5.   5. “pod didn’t trigger scale-up (it wouldn’t fit if a new node is added)””")

43.   Debug Commands
44.   Summary
45.   Key Takeaways
46.   When to Use What
47.   In the Context of Pod Resize (Kubernetes 1.33)")
48.   Connect

Image 2: Christian Dussol
## Christian Dussol

Director of Engineering at teciem | Cloud Native × AI Native × Financial Services
- [DevOps Glossary | Kubernetes Resource Requests and Limits · MeteorOps](https://www.meteorops.com/glossary/kubernetes-resource-requests-and-limits) — Kubernetes Resource Requests and Limits are per-container settings that tell Kubernetes how much CPU and memory a workload needs and the maximum it can use. A request is the amount Kubernetes uses when scheduling a Pod onto a node, such as `cpu: 500m` or `memory: 256Mi`. A limit is the runtime cap, such as `cpu: 1` or `memory: 512Mi`. If a container exceeds its memory limit, Kubernetes can terminate it with an out-of-memory error; if it exceeds its CPU limit, it is throttled. Teams use requests and limits to improve bin packing, reduce noisy-neighbor problems, control cost, and make Kubernetes infrastructure management more predictable, but values set too low can cause throttling or crashes, while values set too high can waste cluster capacity.
- [Top Resource Management Issues in Kubernetes](https://scaleops.com/blog/top-resource-management-issues-in-kubernetes) — ```
apiVersion: v1 kind: Pod metadata: name: high-resource-pod spec: affinity: nodeAffinity: requiredDuringSchedulingIgnoredDuringExecution: nodeSelectorTerms: - matchExpressions: - key: high-resource operator: In values: - "true" containers: - name: example-container image: example-image resources: requests: memory: "512Mi" cpu: "1000m" limits: memory: "1024Mi" cpu: "2000m" --- apiVersion: v1 kind: Node metadata: name: example-node labels: high-resource: "true"
```

## 2. CPU Throttling and Limits: Striking the Right Balance

What Is CPU Throttling?

CPU throttling occurs when a pod exceeds its allocated CPU limit, causing Kubernetes to restrict its CPU usage. This can lead to performance degradation and latency issues.

Example [...] What Happens on Loaded Nodes?

When a node is heavily loaded, even pods with adequate memory limits might face OOM issues if the total memory usage exceeds the node’s capacity. This is particularly problematic in environments with dynamic workloads.

Example

Consider a cluster running multiple applications with varying memory usage patterns. If several applications peak in memory usage simultaneously, the node might run out of memory, causing OOM errors across multiple pods.

How to Manage Loaded Nodes

 Rightsize Resource Requests: Ensure that resource requests accurately reflect the memory needs of your pods, helping to prevent nodes from being overloaded.
 Constantly Monitor Node Capacity and Utilization

## Conclusion
- [Kubernetes Pod Resource Quota Exceeded Error: Namespace Limits, CPU Throttling & Workload Blocking - CubeAPM](https://cubeapm.com/blog/kubernetes-pod-resource-quota-exceeded-error) — Pods remain in a FailedCreate or Forbidden state.
 Namespace usage exceeds the defined CPU, memory, or storage quotas.
 CI/CD rollouts may stop midway due to blocked Pod creation.
 Resource utilization dashboards show saturation at the namespace level.
 Cluster administrators notice pending Pods even with available node capacity.

## Why Kubernetes Pod Resource Quota Exceeded Error Happens

### 1. Namespace Resource Limits Reached

When a namespace reaches its defined CPU, memory, or storage limits, new Pods that request additional resources cannot be created. This is the most common trigger for the Kubernetes Pod Resource Quota Exceeded error, especially in tightly controlled production environments.

### 2. Excessive Resource Requests in Pod Specs [...] Quick check:

Bash

```
 kubectl describe resourcequota -n <namespace> kubectl describe resourcequota -n< namespac e>
```

Fix: Review the “Used” vs “Hard” limits in the output and plan a quota adjustment accordingly.

Bash

```
kubectl get resourcequota <quota-name> -n <namespace> -o yaml kubectl get resourcequota<quota-nam e> -n< namespac e> -o yaml
```

### 2. Reduce Pod Resource Requests

Pods may request excessive CPU or memory resources, exhausting the namespace quota. Lowering requests and limits for non-critical Pods helps release quota capacity.

Quick check:

Bash [...] Example snippet inside updated-resourcequota.yaml:

YAML

```
apiVersion: v1 apiVersion: v1kind: ResourceQuota kind: ResourceQuotametadata: metadata:  name: team-quota    name:team-quota  namespace: dev    namespace: devspec: spec:  hard:    hard:    requests.cpu: "10"     requests.cpu: " 10 "    requests.memory: 20Gi     requests.memory: 20Gi    limits.cpu: "15"     limits.cpu: " 15 "    limits.memory: 30Gi     limits.memory: 30Gi
```

### 5. Clean Up Unused Persistent Volumes

Old or unreferenced PersistentVolumeClaims (PVCs) can quickly consume storage quotas. Removing them frees up space for new workloads.

Quick check:

Bash

```
kubectl get pvc -n <namespace> kubectl get pvc -n< namespac e>
```

Fix: Delete unused PVCs after verifying they’re not linked to running Pods.

Bash
- [Configure CPU topology aware scheduling for CPU pinning](https://www.alibabacloud.com/help/en/ack/ack-managed-and-ack-dedicated/user-guide/topology-aware-cpu-scheduling) — Use this policy for large-scale AMD machine types with 32 or more cores. Configuration: For a workload such as a Deployment: add them to spec.
- [How to Deploy a Headless Commerce Backend on Azure ...](https://oneuptime.com/blog/post/2026-02-16-how-to-deploy-a-headless-commerce-backend-on-azure-kubernetes-service/view) — Deploy the Checkout Service with Event-Driven Processing Checkout is the most critical path. It needs to validate inventory, process payment,
- [Mastering Kubernetes Manifests: A Full Guide](https://www.plural.sh/blog/kubernetes-manifests-guide) — I'm worried about making a mistake in my manifest that could break something. How can I check my work before applying it? That's a valid concern; thankfully, there are ways to catch issues early. Before you ever send a manifest to your cluster, you can use tools called linters to check for syntax errors or common misconfigurations. Kubernetes itself also offers a "dry run" option with `kubectl apply`. This lets you see what changes would be made without actually applying them. Within a platform like Plural, this kind of pre-flight check is often built into the deployment process, for example, by automatically running plans for infrastructure changes before they are applied, giving you a chance to review. [...] If my deployment fails and I suspect it's a manifest issue, how can Plural help me figure out what went wrong? Chasing down issues in manifest files can definitely be time-consuming. If you're using Plural, our AI Insight Engine is designed to help with exactly this. It can automatically analyze logs, Kubernetes events, and your manifest configurations to help pinpoint the root cause of a problem. Instead of manually digging through files, the AI can offer suggestions for fixes or explain complex configurations, which can significantly speed up your troubleshooting process. [...] Even meticulously crafted manifests can present challenges. Pinpointing the root cause of a deployment hiccup or application glitch within extensive YAML files often consumes valuable engineering time, a known drag on developer productivity. Plural’s AI capabilities are designed to mitigate this. Our AI Insight Engine automates root cause analysis by examining logs, events, and manifest configurations to quickly identify issues. Beyond detection, the AI Fix Engine can propose precise code modifications to resolve manifest-related problems. For particularly complex manifests, the "Explain With AI" feature offers clear, understandable explanations, making intricate configurations accessible to your entire team and reducing the manual effort in debugging.
- [Assign CPU Resources to Containers and Pods | Kubernetes](https://kubernetes.io/docs/tasks/configure-pod-container/assign-cpu-resource) — ```
kubectl get apiservices kubectl get apiservices 
```

If the resource metrics API is available, the output will include a reference to `metrics.k8s.io`.

```
NAME v1beta1.metrics.k8s.io 
```

## Create a namespace

Create a Namespace so that the resources you create in this exercise are isolated from the rest of your cluster.

```
kubectl create namespace cpu-example kubectl create namespace cpu-example 
```

## Specify a CPU request and a CPU limit

To specify a CPU request for a container, include the `resources.requests.cpu` field in the container’s resource manifest. To specify a CPU limit, include `resources.limits.cpu`. [...] In this exercise, you create a Pod that has a CPU request so big that it exceeds the capacity of any Node in your cluster. Here is the configuration file for a Pod that has one Container. The Container requests 100 CPU, which is likely to exceed the capacity of any Node in your cluster.

`pods/resource/cpu-request-limit-2.yaml` [...] ## Motivation for CPU requests and limits

By configuring the CPU requests and limits of the Containers that run in your cluster, you can make efficient use of the CPU resources available on your cluster Nodes. By keeping a Pod CPU request low, you give the Pod a good chance of being scheduled. By having a CPU limit that is greater than the CPU request, you accomplish two things:

 The Pod can have bursts of activity where it makes use of CPU resources that happen to be available.
 The amount of CPU resources a Pod can use during a burst is limited to some reasonable amount.

## Clean up

Delete your namespace:

```
kubectl delete namespace cpu-example kubectl delete namespace cpu-example 
```

## What's next

### For app developers
- [Kubernetes CPU Throttling: What it is, and Best Practices](https://www.groundcover.com/blog/kubernetes-cpu-throttling) — ## Faqs

CPU is a compressible resource in Linux, so Kubernetes slows workloads through throttling instead of terminating them when limits are exceeded.

 CPU limits are enforced through the Linux CFS (Completely Fair Scheduler), which pauses container execution when it exceeds its quota.
 Memory is not compressible, so exceeding limits leads to OOMKilled events.
 Throttling allows containers to continue running, but latency and request times increase significantly.
 This is why CPU misconfiguration often appears as performance degradation rather than an obvious failure.

Explore Kubernetes performance concepts.

CPU throttling usually appears as unexplained latency spikes even when overall CPU utilization appears moderate. [...] Using a request (which, again, we'll discuss in more detail in a bit), you've configured a container or Pod to receive more CPU units than are available. This causes what's known as CPU overcommitment because you've committed your workloads to using more CPUs than actually exist. Even if the workloads don't actually require all of the CPU capacity you've assigned to them, overcommitment can cause issues because it reduces the CPUs available to other workloads. [...] CPU requests are so high that they tie up CPU that other workloads need. For example, if you assign 8 CPUs to one container while only having 16 CPUs available in total, and you’re running a dozen containers, the one container with the 8 requests might end up hogging CPU, with the result that the other containers will experience throttling.
 CPU requests that are higher than the actual CPU available. For instance, you don't want to assign 4 CPU units to a container if its host node only has 2 CPU cores. This leads to CPU overcommitment.
 CPU limits that are too low to meet the requirements of a workload. An excessively low CPU limit won't result in throttling, but it may cause performance issues because your workload won't have enough CPU.