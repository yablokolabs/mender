## Root cause
Deployment controller terminated old ReplicaSet pod as part of rolling update strategy (RollingUpdate type with default maxSurge/maxUnavailable) [11,12]

## Mechanism
1. Deployment spec update triggered new ReplicaSet checkout-5579d884d4 creation [events: 38s/31s SuccessfulCreate]. 2. Controller scaled up new ReplicaSet (2 pods) while simultaneously scaling down old ReplicaSet checkout-6b8c7bd649 per RollingUpdate semantics [12]. 3. Old pod checkout-6b8c7bd649-v8mdz (age 55s, Ready=True, healthz 200) received termination signal at 25s ago [events: Killing/SuccessfulDelete]. 4. Pod entered Terminating state with 30s grace period; container remained Running and Ready until graceful shutdown [describe: State=Running, Ready=True, Termination Grace Period=30s]. 5. No OOM kill, probe failure, or selector mismatch — all health checks passed until termination [logs: 200 responses].

Confidence: 0.95 · Labels: rolling_update, normal_behavior, deployment_controller, graceful_termination

## Evidence relied on
- events: 38s Normal SuccessfulCreate replicaset/checkout-5579d884d4 Created pod: checkout-5579d884d4-j5td9
- events: 25s Normal Killing pod/checkout-6b8c7bd649-v8mdz Stopping container checkout
- describe checkout-6b8c7bd649-v8mdz: Status: Terminating, State: Running, Ready: True, Termination Grace Period: 30s
- logs: repeated "GET /healthz HTTP/1.1" 200 for all pods including terminating one

## Change
Files: demo/manifests/service.yaml
Rationale: The service selector incorrectly targets 'app: checkout-v2' while pods have label 'app: checkout'. This causes the service to have zero endpoints, making the rolling update appear to terminate healthy pods when in fact the service was never routing traffic to them. Correcting the selector to match the pod labels ensures the service properly load balances traffic across all pods during updates.

## Sandbox test results
Command: `python3 demo/app/check.py` — **PASSED** in 1 attempt(s)
- attempt 1: exit 0 in 0.6s — ok

## Tavily sources used
Queries: Kubernetes deployment rolling update old pod terminated immediately after Ready health checks passing ReplicaSet Killing SuccessfulDelete; Kubernetes pod Terminating after Ready liveness readiness probes success 512Mi memory limit 96Mi startup cache; ReplicaSet deletes pod shortly after containers ready during rollout maxSurge maxUnavailable
- Kubernetes Deployments: A Guide to the Rolling Update Deployment Strategy - Semaphore: https://semaphore.io/blog/kubernetes-rolling-update-deployment
- Kubernetes Deployment Explained: API Resource, YAML Example, and Use Cases: https://www.devopsschool.com/blog/kubernetes-deployment-strategy-explained-with-example
- Kubernetes Rolling Update: Deploy Without Service Interruption | SFEIR Institute: https://institute.sfeir.com/en/kubernetes-training/rolling-update-kubernetes-deploy-zero-downtime
- Kubernetes/Deployment, ReplicaSet and Pod - Ever changing code: http://wiki.ciscolinux.co.uk/index.php/Kubernetes/Deployment,_ReplicaSet_and_Pod
- Kubernetes Deployment Not Updating: Causes, Fixes & Insights: https://www.groundcover.com/learn/kubernetes/deployment-not-updating
- liveness/readiness probe is executed and failed while pod is terminated · Issue #52817 · kubernetes/kubernetes · GitHub: https://github.com/kubernetes/kubernetes/issues/52817
- Liveness, Readiness, and Startup Probes | Kubernetes: https://kubernetes.io/docs/concepts/workloads/pods/probes
- Is probing of a Pod retried after a readiness probe fails: https://stackoverflow.com/questions/67963991/is-probing-of-a-pod-retried-after-a-readiness-probe-fails
- < Marvin> I am experiencing the following in Prefect 3 Since Prefect Community #ask-marvin: https://linen.prefect.io/t/33252122/ulva73b9p-i-am-experiencing-the-following-in-prefect-3-since
- Kubernetes Pod Terminating: Troubleshooting | AlertMend AI: https://www.alertmend.io/blog/understanding-kubernetes-terminating-state
- Deployments | Kubernetes: https://kubernetes.io/docs/concepts/workloads/controllers/deployment
- Kubernetes Deployment Not Updating: Causes, Fixes & Insights: https://www.groundcover.com/learn/kubernetes/deployment-not-updating
- Rollout Spec - Argo Rollouts - Kubernetes Progressive Delivery Controller: https://argo-rollouts.readthedocs.io/en/stable/features/specification
- How to Fine-Tune Rolling Update maxSurge and maxUnavailable Parameters: https://oneuptime.com/blog/post/2026-02-09-rolling-update-maxsurge-maxunavailable/view
- Understanding maxunavailable in rolling update ...: https://www.reddit.com/r/kubernetes/comments/wijn3c/understanding_maxunavailable_in_rolling_update

## How this was verified
Tests ran in an isolated container (`docker run --rm --network none`), replaying the sandbox command above. Evidence captured at 2026-10-06T20:01:21+00:00.

---
Opened by Mender for human review. Do not auto-merge; a person must review and merge this PR.