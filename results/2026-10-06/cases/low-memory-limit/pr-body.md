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

## Change
Files: demo/manifests/deploy.yaml
Rationale: The deployment's memory limit was set to 64Mi, which is below the application's 96Mi startup cache and the required 512Mi minimum, causing OOMKilled crashes. Increasing the limit to 512Mi ensures the container has enough memory to start and run without hitting the cgroup limit.

## Sandbox test results
Command: `python3 demo/app/check.py` — **PASSED** in 1 attempt(s)
- attempt 1: exit 0 in 0.6s — ok

## Tavily sources used
Queries: Kubernetes OOMKilled CrashLoopBackOff memory limit 64Mi insufficient startup cache 96Mi; Kubernetes deployment memory limit misconfiguration OOMKilled pod restart loop known issues; container memory limit below application startup requirements OOMKilled exit code 137 documented causes
- Kubernetes CrashLoopBackOff After Changing Resource Limits — Fix | DevOpsBoys: https://devopsboys.com/blog/kubernetes-crashloopbackoff-after-resource-limits-fix-2026
- How to Debug CrashLoopBackOff and OOMKilled Pods in Kubernetes: https://oneuptime.com/blog/post/2026-01-06-kubernetes-debug-crashloopbackoff-oomkilled/view
- How to Fix CrashLoopBackOff in Kubernetes? - Komodor: https://komodor.com/learn/how-to-fix-crashloopbackoff-kubernetes-error
- CrashLoopBackOff in Kubernetes: Causes and Fixes: https://cast.ai/blog/crashloopbackoff
- Kubernetes CrashLoopBackOff: Causes, Diagnosis, and Fixes: https://middleware.io/blog/kubernetes-crashloopbackoff-causes-diagnosis-and-fixes
- Why Pods Get OOMKilled in Kubernetes (And Why Memory Limits Won’t Save You): https://medium.com/@pillarslive/why-pods-get-oomkilled-in-kubernetes-and-why-memory-limits-wont-save-you-5891b8f338ea
- Kubernetes OOMKilled out of memory diagnosis: https://www.dynatrace.com/news/blog/kubernetes-oomkilled-out-of-memory-troubleshooting
- Debugging Kubernetes OOMKilled (Exit Code 137): A Root Cause Guide: https://resolve.ai/glossary/how-to-debug-kubernetes-OOMKilled-errors
- 5 Ways You Can Diagnose & Prevent OOMKilled Errors in Kubernetes: https://www.fairwinds.com/blog/5-ways-you-can-diagnose-and-prevent-oomkilled-errors-in-kubernetes
- Kubernetes OOMKilled Error: How to Fix & Tips for Preventing It · Dash0: https://www.dash0.com/guides/kubernetes-oomkilled-error-how-to-fix-and-tips-for-preventing-it
- OOMKilled (Exit Code 137): Causes and How to Fix It: https://cast.ai/blog/oomkilled-exit-code-137
- Kubernetes Exit Codes: 137, 139, 143, 127 and Fixes: https://cast.ai/blog/kubernetes-exit-codes
- Kubernetes OOMKilled: Fix Memory Limit Issues & Exit Code 137 | K8s Troubleshooting Tutorial: https://www.youtube.com/watch?v=JLw_pHLCN4Y&xstg=CAMSBhUDze3xHw%3D%3D
- Debugging Kubernetes OOMKilled (Exit Code 137): A Root Cause Guide: https://resolve.ai/glossary/how-to-debug-kubernetes-OOMKilled-errors
- Kubernetes Exit Code 137: Root Causes and How to Fix It: https://www.plural.sh/blog/kubernetes-exit-code-137

## How this was verified
Tests ran in an isolated container (`docker run --rm --network none`), replaying the sandbox command above. Evidence captured at 2026-10-06T19:40:13+00:00.

---
Opened by Mender for human review. Do not auto-merge; a person must review and merge this PR.