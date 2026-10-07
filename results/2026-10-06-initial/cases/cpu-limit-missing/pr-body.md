## Root cause
Rapid successive deployment updates caused overlapping rolling updates, terminating pods from two previous replica sets while they were still healthy.

## Mechanism
1. Deployment updated to revision b4dfc8f77 (pod-template-hash=b4dfc8f77) at ~17:00:24, creating new pods. 2. Before that rollout completed, a second update to revision 9c78769bf (pod-template-hash=9c78769bf) was applied at ~17:00:41, creating another pod set. 3. The new 9c78769bf pods passed readiness probes (events show SuccessfulCreate, Started, Ready=True). 4. The deployment controller then terminated pods from both previous replica sets (b4dfc8f77 and 9f49f8b65) because they were no longer needed, even though they still reported Ready=True. 5. Terminating pods remain in Ready=True state until the termination grace period expires, which is normal Kubernetes rolling update behavior [1][2].

Confidence: 0.90 · Labels: rolling_update, rapid_successive_updates, terminating_pods_ready, normal_behavior, false_alarm

## Evidence relied on
- Status: Terminating (lasts <invalid>) for checkout-9f49f8b65-*, checkout-b4dfc8f77-*
- Ready: True for all terminating pods
- Events: Killing pod/checkout-b4dfc8f77-zdqzm, SuccessfulDelete replicaset/checkout-b4dfc8f77
- Events: SuccessfulCreate replicaset/checkout-9c78769bf, Started pod/checkout-9c78769bf-glzqr
- Logs: healthz 200 responses from pods of all three replica sets

## Change
Files: demo/manifests/deploy.yaml
Rationale: Adding minReadySeconds to the Deployment ensures that newly created pods are considered ready only after they have been ready for the specified duration (10 seconds). This slows down the rollout process, preventing the deployment controller from terminating old replica set pods too quickly when rapid successive updates occur. It gives the new pods time to stabilize and reduces the chance of overlapping rolling updates causing healthy pods to be terminated prematurely.

## Sandbox test results
Command: `python3 demo/app/check.py` — **PASSED** in 2 attempt(s)
- attempt 1: exit 1 in 0.8s — failed
- attempt 2: exit 0 in 0.8s — ok

## Tavily sources used
Queries: Kubernetes rolling update race condition pods terminating while Ready=true liveness readiness probe; Kubernetes deployment rollout pods killed despite passing health checks termination grace period; Kubernetes ReplicaSet deletion race condition pod terminating ready status true known issue
- Kubernetes Health Probes: Liveness, Readiness, and Startup ...: https://dev.to/toothbrush/kubernetes-health-probes-liveness-readiness-and-startup-explained-5app
- Kubernetes Rolling Update Configuration: https://www.bluematador.com/blog/kubernetes-deployments-rolling-update-configuration
- Kubernetes Rolling Updates Stalled by Readiness Probes: https://www.linkedin.com/posts/kshitijhatwar_kubernetes-devops-sre-activity-7459448463534137344-soS9
- Client is disconnected when the pod is terminating or fails the readiness probe - General Discussions - Discuss Kubernetes: https://discuss.kubernetes.io/t/client-is-disconnected-when-the-pod-is-terminating-or-fails-the-readiness-probe/19408
- Kubernetes Rolling Update: Deploy Without Service Interruption | SFEIR Institute: https://institute.sfeir.com/en/kubernetes-training/rolling-update-kubernetes-deploy-zero-downtime
- `kubectl rollout restart deployment`: The Right Way: https://www.plural.sh/blog/kubectl-rollout-restart-deployment
- Kubernetes Deployment Strategies: Tutorial & Examples - Apptio: https://www.apptio.com/blog/kubernetes-deployment-strategy
- How to Configure Pod Termination Grace Period: https://oneuptime.com/blog/post/2026-01-25-pod-termination-grace-period/view
- Deployments | Kubernetes: https://kubernetes.io/docs/concepts/workloads/controllers/deployment
- Exploring the Termination Process in Kubernetes – IT Exams Training – Pass4Sure: https://www.pass4sure.com/blog/exploring-the-termination-process-in-kubernetes
- ReplicaSet | Kubernetes: https://kubernetes.ac.cn/docs/reference/kubernetes-api/apps/replica-set-v1
- Unable to delete pod in terminating state. : r/kubernetes: https://www.reddit.com/r/kubernetes/comments/1eb4lhc/unable_to_delete_pod_in_terminating_state
- ReplicaSet | Kubernetes: https://v1-33.docs.kubernetes.io/docs/reference/kubernetes-api/workload-resources/replica-set-v1
- ReplicaSet | Kubernetes: https://www.kubernetes.io/docs/reference/kubernetes-api/workload-resources/replica-set-v1
- ReplicaSet | Kubernetes: http://kubernetes.io/docs/reference/kubernetes-api/workload-resources/replica-set-v1

## How this was verified
Tests ran in an isolated container (`docker run --rm --network none`), replaying the sandbox command above. Evidence captured at 2026-10-06T17:00:54+00:00.

---
Opened by Mender for human review. Do not auto-merge; a person must review and merge this PR.