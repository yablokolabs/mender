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

## Change
Files: demo/manifests/deploy.yaml
Rationale: The application allocates a 96MiB startup cache, which exceeds the current memory limit of 64Mi, causing OOMKill. Increasing the memory limit to 512Mi matches the healthy ReplicaSets and satisfies the invariant check requiring at least 512Mi.

## Sandbox test results
Command: `python3 demo/app/check.py` — **PASSED** in 1 attempt(s)
- attempt 1: exit 0 in 0.8s — ok

## Tavily sources used
Queries: Kubernetes OOMKilled exit code 137 memory limit 64Mi startup cache 96Mi; container CrashLoopBackOff OOMKilled insufficient memory limit for application startup cache; Kubernetes pod OOMKilled memory limit below application startup heap requirement
- Exit Code 137 - Fixing OOMKilled Kubernetes Error: https://spacelift.io/blog/oomkilled-exit-code-137
- Kubernetes OOMKilled: Fix Memory Limit Issues & Exit Code 137 | K8s Troubleshooting Tutorial: https://www.youtube.com/watch?v=JLw_pHLCN4Y
- Debugging Kubernetes OOMKilled (Exit Code 137): A Root Cause Guide: https://resolve.ai/glossary/how-to-debug-kubernetes-OOMKilled-errors
- Kubernetes OOMKilled Error: How to Fix & Tips for Preventing It · Dash0: https://www.dash0.com/guides/kubernetes-oomkilled-error-how-to-fix-and-tips-for-preventing-it
- Subprocess Killed with a 137 error - General Discussions - Discuss Kubernetes: https://discuss.kubernetes.io/t/subprocess-killed-with-a-137-error/22058
- Kubernetes CrashLoopBackOff: Causes, Diagnosis, and Fixes: https://middleware.io/blog/kubernetes-crashloopbackoff-causes-diagnosis-and-fixes
- Diagnosing and Fixing CrashLoopBackOff in Kubernetes: https://danielcosenza.com/posts/devops-fix-crashloopbackoff
- Kubernetes Troubleshooting: Errors, Causes & Fixes: https://cast.ai/blog/kubernetes-troubleshooting
- CrashLoopBackOff in Kubernetes: Causes and Fixes: https://cast.ai/blog/crashloopbackoff
- How to Fix CrashLoopBackOff in Kubernetes? - Komodor: https://komodor.com/learn/how-to-fix-crashloopbackoff-kubernetes-error
- Memory settings for Java process running in Kubernetes pod: https://medium.com/@sharprazor.app/memory-settings-for-java-process-running-in-kubernetes-pod-1e608a5d2a64
- Why Pods Get OOMKilled in Kubernetes (And Why Memory Limits Won’t Save You): https://medium.com/@pillarslive/why-pods-get-oomkilled-in-kubernetes-and-why-memory-limits-wont-save-you-5891b8f338ea
- Kubernetes OOMKilled out of memory diagnosis: https://www.dynatrace.com/news/blog/kubernetes-oomkilled-out-of-memory-troubleshooting
- Direct Memory and Container OOMKilled Errors | Proofpoint US: https://www.proofpoint.com/us/blog/engineering-insights/direct-memory-and-container-oomkilled-errors
- How can we tell if the OOMKilled in k8s is because the node is running out of memory and thus killing the pod, or if the pod itself is being killed because the memory it has requested exceeds the limt declaration limit? - General Discussions - Discuss Kubernetes: https://discuss.kubernetes.io/t/how-can-we-tell-if-the-oomkilled-in-k8s-is-because-the-node-is-running-out-of-memory-and-thus-killing-the-pod-or-if-the-pod-itself-is-being-killed-because-the-memory-it-has-requested-exceeds-the-limt-declaration-limit/26303

## How this was verified
Tests ran in an isolated container (`docker run --rm --network none`), replaying the sandbox command above. Evidence captured at 2026-10-06T16:40:23+00:00.

---
Opened by Mender for human review. Do not auto-merge; a person must review and merge this PR.