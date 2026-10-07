## Root cause
Deployment.spec.replicas is set to 0 in the manifest, which instructs Kubernetes to terminate all managed pods.

## Mechanism
The Deployment manifest (deploy.yaml) explicitly sets spec.replicas: 0. The ReplicaSet controller continuously reconciles actual pod count with desired replicas. Seeing 0 desired replicas, it selects all running pods for deletion, issuing SIGTERM (Killing events) and then removing them (SuccessfulDelete events). Pods were healthy — passing readiness/liveness probes and serving traffic — but are terminated because the control loop's target state is zero. This is expected Kubernetes behavior when scaling a Deployment to zero [1][3][5].

Confidence: 0.95 · Labels: replica_count_zero, deployment_scale_down, intentional_termination, manifest_misconfig

## Evidence relied on
- deploy.yaml: spec.replicas: 0
- EVENTS: Killing pod/checkout-d6f4887c4-m6f2g Stopping container checkout
- EVENTS: SuccessfulDelete Deleted pod: checkout-d6f4887c4-wmb7w
- PODS: Status: Terminating
- LOGS: continuous 200 healthz responses showing pods were healthy before termination

## Change
Files: demo/manifests/deploy.yaml
Rationale: The root cause is that spec.replicas is set to 0, causing the ReplicaSet to terminate all pods. Increasing replicas to 1 ensures the Deployment maintains at least one pod, satisfying the check_replicas invariant and preventing unwanted terminations.

## Sandbox test results
Command: `python3 demo/app/check.py` — **PASSED** in 1 attempt(s)
- attempt 1: exit 0 in 0.7s — ok

## Tavily sources used
Queries: Kubernetes deployment replicas=0 pods immediately terminating after creation; Kubernetes replica set scales down to zero pods deleted SuccessfulDelete event; Kubernetes deployment zero replicas pod lifecycle termination behavior
- Deployments | Kubernetes: https://kubernetes.io/docs/concepts/workloads/controllers/deployment
- Troubleshoot Kubernetes Deployment ReplicaSet Stuck at Zero Available Replicas: https://oneuptime.com/blog/post/2026-02-09-replicaset-stuck-zero-replicas/view
- Kubectl Scale Deployment to 0 | CloudBolt: https://www.cloudbolt.io/kubernetes-autoscaling/kubectl-scale-deployment-to-0
- Kubernetes pod gets recreated when deleted: https://stackoverflow.com/questions/40686151/kubernetes-pod-gets-recreated-when-deleted
- When scale replicas==0, do K8s send SIGTERM? - General Discussions - Discuss Kubernetes: https://discuss.kubernetes.io/t/when-scale-replicas-0-do-k8s-send-sigterm/11838
- Scale Kubernetes Pods to Zero, Without Cold Starts: https://loopholelabs.io/blog/scale-to-zero
- When scale replicas==0, do K8s send SIGTERM? - General Discussions - Discuss Kubernetes: https://discuss.kubernetes.io/t/when-scale-replicas-0-do-k8s-send-sigterm/11838
- ReplicaSet | Kubernetes: https://kubernetes.io/docs/concepts/workloads/controllers/replicaset
- The Ultimate Guide to `kubectl scale deployment`: https://www.plural.sh/blog/kubectl-scale-deployment-guide
- Kubernetes: how to scale my pods: https://stackoverflow.com/questions/38344896/kubernetes-how-to-scale-my-pods
- Understanding the Kubernetes Pod Lifecycle and Graceful Shutdown: https://medium.com/@sharathkumarlokesh/understanding-the-kubernetes-pod-lifecycle-and-graceful-shutdown-acd5a56fce06
- Best Practices for Scaling Kubernetes Pods to Zero with ...: https://devgex.com/en/article/00021246
- Exploring the Termination Process in Kubernetes – IT Exams Training – Pass4Sure: https://www.pass4sure.com/blog/exploring-the-termination-process-in-kubernetes
- Kubectl Scale Deployment to 0 | CloudBolt: https://www.cloudbolt.io/kubernetes-autoscaling/kubectl-scale-deployment-to-0
- When scale replicas==0, do K8s send SIGTERM? - General Discussions - Discuss Kubernetes: https://discuss.kubernetes.io/t/when-scale-replicas-0-do-k8s-send-sigterm/11838

## How this was verified
Tests ran in an isolated container (`docker run --rm --network none`), replaying the sandbox command above. Evidence captured at 2026-10-06T19:52:53+00:00.

---
Opened by Mender for human review. Do not auto-merge; a person must review and merge this PR.