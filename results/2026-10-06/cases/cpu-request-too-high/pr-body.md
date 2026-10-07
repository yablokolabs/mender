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

## Change
Files: demo/manifests/deploy.yaml
Rationale: The Deployment requested 32 CPU cores, exceeding the single-node cluster capacity. Reduced requests.cpu to 100m and limits.cpu to 1, matching the existing stable ReplicaSet and satisfying the cluster's CPU availability while keeping memory unchanged.

## Sandbox test results
Command: `python3 demo/app/check.py` — **PASSED** in 1 attempt(s)
- attempt 1: exit 0 in 0.5s — ok

## Tavily sources used
Queries: Kubernetes pod Pending Insufficient cpu request 32 cores node capacity scheduling failure; Kubernetes resource requests cpu limit exceeds node capacity known issue troubleshooting; checkout service cpu request 32 cores deployment manifest misconfiguration
- Kubernetes pod stuck Pending: scheduling failures explained: https://www.netdata.cloud/guides/kubernetes/kubernetes-pod-pending
- Resource Management for Pods and Containers | Kubernetes: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers
- Kubernetes Pods not scheduled due to "Insufficient CPU" when CPU resources are available · Issue #33777 · kubernetes/kubernetes · GitHub: https://github.com/kubernetes/kubernetes/issues/33777
- Fix GKE Pod Stuck in Pending State Due to Insufficient CPU or Memory Resources: https://oneuptime.com/blog/post/2026-02-17-how-to-fix-gke-pod-stuck-in-pending-state-due-to-insufficient-cpu-or-memory-resources/view
- Solving Kubernetes Scheduling Failures: Requests, Taints, and Affinity: https://resolve.ai/glossary/how-to-debug-kubernetes-pod-pending-state
- Kubernetes Resource Requests and Limits — Full Guide: https://devtoolhub.com/kubernetes-resource-requests-and-limits-full-guide
- Why Your Kubernetes Pods Keep Getting Rejected: The Resource Management Guide You Actually Need: https://medium.com/@christian.dussol/why-your-kubernetes-pods-keep-getting-rejected-the-resource-management-guide-you-actually-need-48ea965eb038
- DevOps Glossary | Kubernetes Resource Requests and Limits · MeteorOps: https://www.meteorops.com/glossary/kubernetes-resource-requests-and-limits
- Top Resource Management Issues in Kubernetes: https://scaleops.com/blog/top-resource-management-issues-in-kubernetes
- Kubernetes Pod Resource Quota Exceeded Error: Namespace Limits, CPU Throttling & Workload Blocking - CubeAPM: https://cubeapm.com/blog/kubernetes-pod-resource-quota-exceeded-error
- Configure CPU topology aware scheduling for CPU pinning: https://www.alibabacloud.com/help/en/ack/ack-managed-and-ack-dedicated/user-guide/topology-aware-cpu-scheduling
- How to Deploy a Headless Commerce Backend on Azure ...: https://oneuptime.com/blog/post/2026-02-16-how-to-deploy-a-headless-commerce-backend-on-azure-kubernetes-service/view
- Mastering Kubernetes Manifests: A Full Guide: https://www.plural.sh/blog/kubernetes-manifests-guide
- Assign CPU Resources to Containers and Pods | Kubernetes: https://kubernetes.io/docs/tasks/configure-pod-container/assign-cpu-resource
- Kubernetes CPU Throttling: What it is, and Best Practices: https://www.groundcover.com/blog/kubernetes-cpu-throttling

## How this was verified
Tests ran in an isolated container (`docker run --rm --network none`), replaying the sandbox command above. Evidence captured at 2026-10-06T19:26:54+00:00.

---
Opened by Mender for human review. Do not auto-merge; a person must review and merge this PR.