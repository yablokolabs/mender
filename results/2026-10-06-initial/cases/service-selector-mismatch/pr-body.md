## Root cause
Service selector specifies app=checkout-v2 but pod template labels have app=checkout, so the Service matches zero pods and creates no endpoints [3][5][12]

## Mechanism
1. Deployment creates pods with label app=checkout (from deploy.yaml template metadata.labels) [deploy.yaml]. 2. Service spec.selector requires app=checkout-v2 (from service.yaml) [service.yaml]. 3. Service controller evaluates selector against pod labels; no pod carries app=checkout-v2. 4. Endpoints controller finds no matching pods, so the checkout Service gets zero endpoints. 5. Clients cannot reach the checkout pods even though pods are Running and health checks pass [LOGS]. 6. The terminating pod (checkout-77f44f76d9-jwbj8) is unrelated — it is the old ReplicaSet scaling down during a normal rolling update [EVENTS].

Confidence: 0.95 · Labels: service_selector_mismatch, label_mismatch, service_endpoints_empty, rolling_update

## Evidence relied on
- service.yaml: selector.app=checkout-v2
- deploy.yaml: template.metadata.labels.app=checkout
- check_service_selector_and_ports() assertion: 'service selector app=checkout-v2 matches no pod label {'app': 'checkout', 'version': 'v1'}'
- LOGS: all pods return HTTP 200 on /healthz
- EVENTS: new ReplicaSet 74cdd5f78f creating pods, old 77f44f76d9 terminating pods normally

## Change
Files: demo/manifests/service.yaml
Rationale: The service selector was set to app=checkout-v2, but the pods have label app=checkout. Changing the selector to app=checkout ensures the service selects the correct pods and creates endpoints.

## Sandbox test results
Command: `python3 demo/app/check.py` — **PASSED** in 1 attempt(s)
- attempt 1: exit 0 in 0.7s — ok

## Tavily sources used
Queries: Kubernetes service selector mismatch pod labels rolling update deployment; pod stuck Terminating state deployment rollout service endpoint mismatch; Kubernetes deployment rolling update service selector label mismatch known issue
- GitHub - khaledeltaweel1/Kubernetes-Rolling-Update-Deployment-Strategy: Rolling Update Deployment In Kubernetes: https://github.com/khaledeltaweel1/Kubernetes-Rolling-Update-Deployment-Strategy
- Deployment fails to perform rolling update · Issue #29760 · kubernetes/kubernetes · GitHub: https://github.com/kubernetes/kubernetes/issues/29760
- How to Fix a Kubernetes Selector Label Mismatch - HeyDevJob: https://heydevjob.com/projects/kubernetes-selector-label-mismatch
- After rolling update, old pod still lying around · Issue #27721 · kubernetes/kubernetes · GitHub: https://github.com/kubernetes/kubernetes/issues/27721
- kubernetes - service selector vs deployment selector matchlabels - Stack Overflow: https://stackoverflow.com/questions/63875585/service-selector-vs-deployment-selector-matchlabels
- Kubernetes Pods Stuck in Terminating: A Resolution Guide: https://kodekloud.com/blog/kubernetes-pods-stuck-in-terminating-a-resolution-guide
- Explore Termination Behavior for Pods And Their Endpoints | Kubernetes: https://kubernetes.io/docs/tutorials/services/pods-and-endpoint-termination-flow
- Pods stuck in Terminating status. When Kubernetes pods get stuck in the… | by Harold Finch | Medium: https://medium.com/@haroldfinch01/pods-stuck-in-terminating-status-083168c6b7e8
- Kubernetes Pods Are Stuck in the Terminating Status: https://techdocs.broadcom.com/us/en/vmware-cis/nsx/nsxt-dc/3-2/deployment-guide/troubleshooting-errors/kubernetes-pods-are-stuck-in-the-terminating-status.html
- Pod is Stuck in the Terminating State | Managed Kubernetes: https://platform9.com/kb/pmk/frequently-asked-questions/pod-is-stuck-in-the-terminating-state
- Rolling Updates with Kubernetes Deployments | Kubernetes: https://tachingchen.com/blog/kubernetes-rolling-update-with-deployment
- Updating "-selector-labels" breaks existing deployments · Issue #809 · fluxcd/flagger · GitHub: https://github.com/fluxcd/flagger/issues/809
- Deployment Fail: Fixing the "Label Selector" Mismatch! (CKA/CKAD Lab 12): https://www.youtube.com/watch?v=9CFH9tcX2J8
- Service: label mapping does not work - General Discussions - Discuss Kubernetes: https://discuss.kubernetes.io/t/service-label-mapping-does-not-work/23939
- Fixing the "Label Selector" Mismatch! (CKA/CKAD Lab 12): https://www.youtube.com/watch?v=9CFH9tcX2J8&xstg=CAMSBhUDze3xHw%3D%3D

## How this was verified
Tests ran in an isolated container (`docker run --rm --network none`), replaying the sandbox command above. Evidence captured at 2026-10-06T17:36:44+00:00.

---
Opened by Mender for human review. Do not auto-merge; a person must review and merge this PR.