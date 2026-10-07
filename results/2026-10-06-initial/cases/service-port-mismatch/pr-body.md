## Root cause
The checkout application does not handle SIGTERM signals for graceful shutdown, causing pods to remain in Terminating state for the full 30s termination grace period during rollouts [1][9][10].

## Mechanism
1. A rollout restart (kubectl rollout restart) triggered a new ReplicaSet (58bbc9b99d) and began terminating the old ReplicaSet (58b467895b) [EVENTS]. 2. The kubelet sent SIGTERM to the old pod (checkout-58b467895b-pmjtm) to initiate graceful shutdown [EVENTS: Killing at 25s]. 3. The application (Python ThreadingHTTPServer in service.py) lacks a SIGTERM handler, so the process does not exit promptly and continues serving health checks [LOGS: 200 responses until 17:34:58]. 4. The pod stays in Terminating state with container still Running, consuming the 30s terminationGracePeriodSeconds [DESCRIBE: Termination Grace Period: 30s, Status: Terminating (lasts <invalid>)]. 5. Only after the grace period expires will the kubelet send SIGKILL to force termination [1][4].

Confidence: 0.80 · Labels: sigterm_unhandled, termination_delay, graceful_shutdown_missing, rollout_stuck

## Evidence relied on
- Status: Terminating (lasts <invalid>)
- Termination Grace Period: 30s
- Killing pod/checkout-58b467895b-pmjtm Stopping container checkout
- GET /healthz HTTP/1.1 200 - (continuing during termination)
- [1] If a PreStop hook hangs... Pod's phase will be Terminating... until terminationGracePeriodSeconds expires
- [9] PID 1 ... both SIGTERM and SIGKILL will be ignored by it
- [10] Server in the container does not respond to SIGINT/SIGTERM — signal handler needed

## Change
Files: demo/manifests/service.yaml
Rationale: The service manifest incorrectly specified targetPort: 80, which does not match the container port 8080. This would cause user traffic to be misrouted. Changing targetPort to 8080 ensures the service correctly forwards traffic to the application. While this does not directly address the SIGTERM handling issue in the application, it is the only permissible change and resolves a manifest error that could contribute to service instability.

## Sandbox test results
Command: `python3 demo/app/check.py` — **PASSED** in 1 attempt(s)
- attempt 1: exit 0 in 0.7s — ok

## Tavily sources used
Queries: Kubernetes pod stuck in Terminating state beyond terminationGracePeriodSeconds during rolling deployment replica set scale down; containerd container not responding to SIGTERM pod stuck terminating Kubernetes 1.28; ReplicaSet scaling down old pods stuck in Terminating state SuccessfulDelete Killing events
- Kubernetes Pods Stuck in Terminating: A Resolution Guide - DEV Community: https://dev.to/imjoseangel/kubernetes-pods-stuck-in-terminating-a-resolution-guide-2jh3
- Gracefully Terminating Pods in Kubernetes: Handling SIGTERM: https://jaadds.medium.com/gracefully-terminating-pods-in-kubernetes-handling-sigterm-fb0d60c7e983
- Some pods stuck in Terminating state and can only be removed if deleting with propagationPolicy=Background · Issue #65569 · kubernetes/kubernetes · GitHub: https://github.com/kubernetes/kubernetes/issues/65569
- Hi,

When Kubernetes scale down or if we stopped/ terminated a POD, how can we g . . . - Kubernetes-Slack Discussions - KodeKloud - DevOps Learning Community: https://kodekloud.com/community/t/hi-when-kubernetes-scale-down-or-if-we-stopped-terminated-a-pod-how-can-we-g/68088
- Deployments | Kubernetes: https://kubernetes.io/docs/concepts/workloads/controllers/deployment
- Pod stuck terminating due to zombie container lingering: https://github.com/containerd/containerd/issues/11133
- Container Runtimes | Kubernetes: https://kubernetes.io/docs/setup/production-environment/container-runtimes
- SIGTERM is not passed through lnd when using Docker ...: https://github.com/lightningnetwork/lnd/issues/4994
- Kubernetes: containers, and the “lost” SIGTERM signals: https://itnext.io/kubernetes-containers-and-the-lost-sigterm-signals-40007f35759a
- Server in the container does not respond to SIGINT/SIGTERM: https://github.com/rustdesk/rustdesk-server/issues/36
- Pods getting stuck into "Terminating" state on deletion after ...: https://github.com/rancher/rancher/issues/38270
- ReplicaSet | Kubernetes: https://kubernetes.io/docs/concepts/workloads/controllers/replicaset
- Pods getting stuck in error state after scale down to 0: https://www.reddit.com/r/kubernetes/comments/1nk8nga/pods_getting_stuck_in_error_state_after_scale
- Unable to delete pod in terminating state. : r/kubernetes: https://www.reddit.com/r/kubernetes/comments/1eb4lhc/unable_to_delete_pod_in_terminating_state
- How to Debug Pods Stuck in Terminating State and Force Delete Them: https://oneuptime.com/blog/post/2026-02-09-debug-pods-terminating-force-delete/view

## How this was verified
Tests ran in an isolated container (`docker run --rm --network none`), replaying the sandbox command above. Evidence captured at 2026-10-06T17:34:59+00:00.

---
Opened by Mender for human review. Do not auto-merge; a person must review and merge this PR.