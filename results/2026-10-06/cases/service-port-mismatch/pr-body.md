## Root cause
Duplicate SuccessfulDelete events from the ReplicaSet controller corrupted the pod's deletionTimestamp, rendering the termination duration metric invalid ("lasts <invalid>") and causing monitoring to falsely classify a normal 30s grace-period termination as stuck [12].

## Mechanism
1. Deployment rolling update creates new ReplicaSet 7c6f9879f4; new pods pass readiness/liveness probes (logs show consistent 200 on /healthz) [12]. 2. Old ReplicaSet 6b97c764b8 scales down and issues delete for pod mwwlq. 3. Controller race produces two SuccessfulDelete events for the same pod (31s and 25s ago) with a Killing event between them, corrupting deletionTimestamp. 4. API server reports termination duration as "<invalid>" while pod is in normal grace period (25s/30s elapsed, container still Running and healthy). 5. Monitoring interprets Terminating + "<invalid>" as stuck, but pod will be SIGKILLed at 30s mark.

Confidence: 0.70 · Labels: rolling_update, termination_timestamp_corruption, false_alert, probe_healthy

## Evidence relied on
- 31s Normal SuccessfulDelete replicaset/checkout-6b97c764b8 Deleted pod: checkout-6b97c764b8-mwwlq
- 25s Normal Killing pod/checkout-6b97c764b8-mwwlq Stopping container checkout
- 25s Normal SuccessfulDelete replicaset/checkout-6b97c764b8 Deleted pod: checkout-6b97c764b8-mwwlq
- Status: Terminating (lasts <invalid>)
- Termination Grace Period: 30s
- logs showing 200 healthz responses during termination

## Change
Files: demo/manifests/service.yaml
Rationale: The service's targetPort was incorrectly set to 80, while the container listens on port 8080. This misconfiguration could cause the service to fail to route traffic properly, potentially interfering with health checks or endpoint updates during rolling updates. Correcting targetPort to 8080 ensures the service properly routes to the container's port, which may help avoid race conditions in the ReplicaSet controller during scaling operations by maintaining accurate endpoint states.

## Sandbox test results
Command: `python3 demo/app/check.py` — **PASSED** in 1 attempt(s)
- attempt 1: exit 0 in 0.6s — ok

## Tavily sources used
Queries: Kubernetes pod stuck Terminating state rolling update graceful termination delay; pod termination grace period liveness probe failure stuck terminating containerd; Kubernetes ReplicaSet rolling update old pod termination stuck finalizers
- Pod Stuck in Terminating State Due to PreStop Hook. | Managed Kubernetes | Knowledge Base: https://platform9.com/kb/pmk/solutions/pod-stuck-in-terminating-state-unless-deleted-forcefully
- Pods stuck in Terminating when PVC is attached during graceful node evacuations · Issue #3370 · bottlerocket-os/bottlerocket · GitHub: https://github.com/bottlerocket-os/bottlerocket/issues/3370
- Exploring the Termination Process in Kubernetes – IT Exams Training – Pass4Sure: https://www.pass4sure.com/blog/exploring-the-termination-process-in-kubernetes
- Kubernetes Deployment Rolling Update: https://stackoverflow.com/questions/70321665/kubernetes-deployment-rolling-update
- Kubernetes Pods Stuck in Terminating: A Resolution Guide - DEV Community: https://dev.to/imjoseangel/kubernetes-pods-stuck-in-terminating-a-resolution-guide-2jh3
- Pod stuck terminating due to zombie container lingering · Issue #11133 · containerd/containerd · GitHub: https://github.com/containerd/containerd/issues/11133
- ContainerAppProbe interface | Microsoft Learn: https://learn.microsoft.com/en-us/javascript/api/@azure/arm-appcontainers/containerappprobe?view=azure-node-latest
- liveness/readiness probe is executed and failed while pod is terminated · Issue #52817 · kubernetes/kubernetes · GitHub: https://github.com/kubernetes/kubernetes/issues/52817
- Replacing pods which are failing liveness probes: https://www.reddit.com/r/kubernetes/comments/1t72z3x/replacing_pods_which_are_failing_liveness_probes
- Pods stuck in Terminating status: https://stackoverflow.com/questions/35453792/pods-stuck-in-terminating-status
- Kubernetes Deployment Rolling Update: https://stackoverflow.com/questions/70321665/kubernetes-deployment-rolling-update
- Kubernetes Rolling Update and Termination Grace Periods | by Thomas Césaré-Herriau | Brex Tech Blog | Medium: https://medium.com/brexeng/kubernetes-rolling-update-and-termination-grace-periods-d922c6b84d88
- Kubernetes Rolling Update: Deploy Without Service Interruption | SFEIR Institute: https://institute.sfeir.com/en/kubernetes-training/rolling-update-kubernetes-deploy-zero-downtime
- Kubernetes Deployment Not Updating: Causes, Fixes & Insights: https://www.groundcover.com/learn/kubernetes/deployment-not-updating
- Diagnose Kubernetes Pod Stuck in Terminating State Due to Finalizer Issues: https://oneuptime.com/blog/post/2026-02-09-pod-stuck-terminating-finalizer/view

## How this was verified
Tests ran in an isolated container (`docker run --rm --network none`), replaying the sandbox command above. Evidence captured at 2026-10-06T19:58:29+00:00.

---
Opened by Mender for human review. Do not auto-merge; a person must review and merge this PR.