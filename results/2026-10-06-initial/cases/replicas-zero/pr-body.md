## Root cause
Deployment 'checkout' in namespace 'shop' has spec.replicas set to 0, causing the ReplicaSet to scale down to zero and terminate all pods.

## Mechanism
The Deployment controller observes spec.replicas=0 and instructs the ReplicaSet to reduce pod count to zero. The ReplicaSet deletes pods (sending SIGTERM, then SIGKILL after terminationGracePeriodSeconds) to match the desired replica count. This results in pods entering Terminating state and being deleted, as seen in events.

Confidence: 0.95 · Labels: deployment_scale_zero, replicaset_scale_down, pod_termination, config_error

## Evidence relied on
- replicas: 0 (from deploy.yaml)
- Killing pod/checkout-7b597c5cf4-lzjww Stopping container checkout (from EVENTS)
- SuccessfulDelete replicaset/checkout-7b597c5cf4 Deleted pod: checkout-7b597c5cf4-tds99 (from EVENTS)
- Deployment's spec.replicas is set to 0, causing a scale‑down that triggers pod deletion (from TRIAGE)
- Scaling a deployment to zero replicas terminates all pods managed by that deployment [2][3]

## Change
Files: demo/manifests/deploy.yaml
Rationale: The Deployment's spec.replicas was set to 0, causing the ReplicaSet to scale down to zero and terminate all pods. Increasing replicas to 1 ensures at least one pod runs, satisfying the invariant that replicas must be >= 1.

## Sandbox test results
Command: `python3 demo/app/check.py` — **PASSED** in 1 attempt(s)
- attempt 1: exit 0 in 0.7s — ok

## Tavily sources used
Queries: Kubernetes Deployment spec.replicas=0 pod termination scale-down behavior; ReplicaSet deletes pods when Deployment replicas set to zero; Kubernetes Deployment scale down to zero replicas pod termination grace period
- Deployments | Kubernetes: https://kubernetes.io/docs/concepts/workloads/controllers/deployment
- The Ultimate Guide to `kubectl scale deployment`: https://www.plural.sh/blog/kubectl-scale-deployment-guide
- Kubectl Scale Deployment to 0 | CloudBolt: https://www.cloudbolt.io/kubernetes-autoscaling/kubectl-scale-deployment-to-0
- When scale replicas==0, do K8s send SIGTERM?: https://discuss.kubernetes.io/t/when-scale-replicas-0-do-k8s-send-sigterm/11838
- Removing spec.replicas of the Deployment resets ...: https://github.com/kubernetes/kubernetes/issues/67135
- When kubernetes deployment is deleted, ReplicaSets are not being deleted - General Discussions - Discuss Kubernetes: https://discuss.kubernetes.io/t/when-kubernetes-deployment-is-deleted-replicasets-are-not-being-deleted/24625
- Your first Kubernetes Pod and ReplicaSet (LABS) | Learn Cloud Native: https://learncloudnative.com/blog/2021-07-10-pods-replicasets
- Deployments | Kubernetes: https://kubernetes.io/docs/concepts/workloads/controllers/deployment
- ReplicaSet vs Deployment: Kubernetes Differences Explained: https://www.groundcover.com/learn/kubernetes/replicaset-vs-deployment
- Troubleshoot Kubernetes Deployment ReplicaSet Stuck at Zero Available Replicas: https://oneuptime.com/blog/post/2026-02-09-replicaset-stuck-zero-replicas/view
- Horizontal Manual Scaling for a Deployment | Kubernetes: https://kubernetes.io/docs/tasks/run-application/scale-deployment
- Scaling to Zero in Kubernetes with Elasti and KEDA: https://www.truefoundry.com/blog/scaling-to-zero-in-kubernetes-a-deep-dive-into-elasti
- Kubectl Scale Deployment to 0 | CloudBolt: https://www.cloudbolt.io/kubernetes-autoscaling/kubectl-scale-deployment-to-0
- Understanding Kubernetes Pod Termination Grace Periods: https://ftp.sleeklens.com/master-series/understanding-kubernetes-pod-termination-grace-periods-1767648289
- Understanding Kubernetes Pod Termination Grace Periods: https://experience.rockfeller.com.br/key-speak/understanding-kubernetes-pod-termination-grace-periods-1767648289

## How this was verified
Tests ran in an isolated container (`docker run --rm --network none`), replaying the sandbox command above. Evidence captured at 2026-10-06T17:29:38+00:00.

---
Opened by Mender for human review. Do not auto-merge; a person must review and merge this PR.