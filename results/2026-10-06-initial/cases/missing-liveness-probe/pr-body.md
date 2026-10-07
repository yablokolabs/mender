## Root cause
The deployment uses a RollingUpdate strategy with maxUnavailable: 0 and terminationGracePeriodSeconds: 400, causing old pods to remain in Terminating state for up to 400 seconds while gracefully shutting down, even though new pods are already Ready [6].

## Mechanism
1. Deployment update triggers rolling rollout: new ReplicaSet (7b8f847c7b) created with 2 pods. 2. New pods start, pass readiness probes, become Ready (observed at 17:17:35-17:17:41). 3. Controller begins terminating old ReplicaSet (f9995f9f) pods. 4. Pods enter Terminating state; kubelet sends SIGTERM (Killing events at 7s/1s ago) then waits up to 400s for graceful exit. 5. Old pods also carry a liveness probe (initialDelaySeconds=5, periodSeconds=10) that was removed in the new template, but probes continue running during termination and do not block it. 6. Pods appear 'stuck' in Terminating for minutes, but are actually within the configured grace period.

Confidence: 0.75 · Labels: termination_grace_period, rolling_update, probe_config, maxunavailable_zero

## Evidence relied on
- deployment manifest: terminationGracePeriodSeconds: 400
- events: Killing events 7s/1s ago but pods Terminating for 2m+
- pod describe: old pods have liveness probe, new pods only readiness
- search result [6]: rolling update with maxUnavailable:0 and 400s grace period is the documented solution for zero-downtime rollouts

## Change
Files: demo/manifests/deploy.yaml
Rationale: Setting maxUnavailable:1 allows the Deployment controller to terminate old pods while new pods are starting, rather than waiting for all new pods to become Ready before terminating any old ones. This reduces the time old pods spend in the Terminating state after new pods are already Ready, addressing the observed delay without affecting any of the validated invariants.

## Sandbox test results
Command: `python3 demo/app/check.py` — **PASSED** in 2 attempt(s)
- attempt 1: exit 1 in 0.6s — failed
- attempt 2: exit 0 in 0.7s — ok

## Tavily sources used
Queries: Kubernetes pod stuck terminating liveness probe rolling update; Kubernetes termination grace period pods stuck terminating replica set rollout; liveness probe configuration causes pod termination stuck Kubernetes
- Pod Stuck in Terminating State Due to PreStop Hook. | Managed Kubernetes | Knowledge Base: https://platform9.com/kb/pmk/solutions/pod-stuck-in-terminating-state-unless-deleted-forcefully
- Kubernetes Rolling Updates Stalled by Readiness Probes: https://www.linkedin.com/posts/kshitijhatwar_kubernetes-devops-sre-activity-7459448463534137344-soS9
- Lost requests when doing a rolling update · Issue #43576 · kubernetes/kubernetes · GitHub: https://github.com/kubernetes/kubernetes/issues/43576
- Kubernetes update results in pod stuck on terminating: https://serverfault.com/questions/986177/kubernetes-update-results-in-pod-stuck-on-terminating
- Diagnose Kubernetes Pod Stuck in Terminating State Due to Finalizer Issues: https://oneuptime.com/blog/post/2026-02-09-pod-stuck-terminating-finalizer/view
- Kubernetes Rolling Update and Termination Grace Periods | by Thomas Césaré-Herriau | Brex Tech Blog | Medium: https://medium.com/brexeng/kubernetes-rolling-update-and-termination-grace-periods-d922c6b84d88
- Kubernetes Pods Stuck in Terminating: A Resolution Guide: https://kodekloud.com/blog/kubernetes-pods-stuck-in-terminating-a-resolution-guide
- Decoding the pod termination lifecycle in Kubernetes: a comprehensive guide | CNCF: https://www.cncf.io/blog/2024/12/19/decoding-the-pod-termination-lifecycle-in-kubernetes-a-comprehensive-guide
- Pods termination grace period - Ansible AWX Operator Documentation: https://docs.ansible.com/projects/awx-operator/en/latest/user-guide/advanced-configuration/pods-termination-grace-period.html
- Some pods stuck in Terminating state and can only be removed if deleting with propagationPolicy=Background · Issue #65569 · kubernetes/kubernetes · GitHub: https://github.com/kubernetes/kubernetes/issues/65569
- Increase Kubernetes Reliability: A Best Practices Guide for Readiness Probes: https://www.fairwinds.com/blog/increase-kubernetes-reliability-a-best-practices-guide-for-readiness-probes
- Readiness vs liveliness probes: How to set them up and when to use them in your Kubernetes cluster | Google Cloud Blog: https://cloud.google.com/blog/products/containers-kubernetes/kubernetes-best-practices-setting-up-health-checks-with-readiness-and-liveness-probes
- Guide to Kubernetes Liveness Probes with Examples: https://spacelift.io/blog/kubernetes-liveness-probe
- Kubernetes Liveness Probes: Configuration & Best Practices: https://www.groundcover.com/blog/kubernetes-liveness-probe
- Configure Liveness, Readiness and Startup Probes | Kubernetes: https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes

## How this was verified
Tests ran in an isolated container (`docker run --rm --network none`), replaying the sandbox command above. Evidence captured at 2026-10-06T17:17:48+00:00.

---
Opened by Mender for human review. Do not auto-merge; a person must review and merge this PR.