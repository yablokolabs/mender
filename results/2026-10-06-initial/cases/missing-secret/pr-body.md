## Root cause
The deployment manifest references a secret named 'checkout-secrets-x' for the SECRET_KEY environment variable, but the actual secret in the cluster is named 'checkout-secrets' (without the '-x' suffix).

## Mechanism
1. The deployment manifest (deploy.yaml) specifies env SECRET_KEY with valueFrom.secretKeyRef.name=checkout-secrets-x [from deploy.yaml]. 2. The cluster only has a secret named 'checkout-secrets' (as shown in secret.yaml and confirmed by the running pods checkout-7cf7bd8689-* which reference 'checkout-secrets'). 3. When the new ReplicaSet (checkout-77b57fd854) creates pod checkout-77b57fd854-t5v95, the kubelet attempts to resolve the secret reference and fails with 'secret "checkout-secrets-x" not found' (Events). 4. This causes the pod to enter CreateContainerConfigError state, preventing container startup. 5. The running pods use the correct secret name 'checkout-secrets' and are healthy.

Confidence: 0.98 · Labels: missing_secret, secret_name_mismatch, deployment_config_error, createcontainerconfigerror

## Evidence relied on
- deploy.yaml: valueFrom.secretKeyRef.name=checkout-secrets-x
- Events: Warning Failed pod/checkout-77b57fd854-t5v95 Error: secret "checkout-secrets-x" not found
- describe checkout-7cf7bd8689-5p4sx: SECRET_KEY from secret 'checkout-secrets'
- secret.yaml: metadata.name=checkout-secrets

## Change
Files: demo/manifests/deploy.yaml
Rationale: The deployment manifest incorrectly referenced a secret named 'checkout-secrets-x' while the actual secret in the cluster is named 'checkout-secrets'. Changing the secret name in the SECRET_KEY environment variable's secretKeyRef to match the existing secret resolves the CreateContainerConfigError and allows the pod to start.

## Sandbox test results
Command: `python3 demo/app/check.py` — **PASSED** in 1 attempt(s)
- attempt 1: exit 0 in 0.8s — ok

## Tavily sources used
Queries: Kubernetes CreateContainerConfigError secret not found secretKeyRef name mismatch; Pod Pending CreateContainerConfigError referenced secret does not exist troubleshooting; Kubernetes deployment secretKeyRef wrong secret name container startup failure
- How to Fix CreateContainerConfigError from Misconfigured Secrets: https://oneuptime.com/blog/post/2026-02-09-createcontainerconfigerror-secrets/view
- Fixing CreateContainerConfigError & CreateContainerError: https://spacelift.io/blog/createcontainerconfigerror
- Kubernetes CreateContainerConfigError and CreateContainerError | Sysdig: https://www.sysdig.com/blog/kubernetes-createcontainerconfigerror-createcontainererror
- CreateContainerConfigError vs CreateContainerError in K8s: https://www.perfectscale.io/blog/createcontainerconfigerror
- Fix CreateContainerConfigError & CreateContainerError: https://www.groundcover.com/kubernetes-troubleshooting/createcontainerconfigerror-createcontainererror
- Fix CreateContainerConfigError & CreateContainerError: https://www.groundcover.com/kubernetes-troubleshooting/createcontainerconfigerror-createcontainererror
- CreateContainerConfigError vs CreateContainerError in K8s: https://www.perfectscale.io/blog/createcontainerconfigerror
- Fixing CreateContainerConfigError & CreateContainerError: https://spacelift.io/blog/createcontainerconfigerror
- Kubernetes CreateContainerConfigError and CreateContainerError | Sysdig: https://www.sysdig.com/blog/kubernetes-createcontainerconfigerror-createcontainererror
- How to Fix CreateContainerConfigError from Misconfigured Secrets: https://oneuptime.com/blog/post/2026-02-09-createcontainerconfigerror-secrets/view
- Resolve Common Kubernetes Deployment Errors | SFEIR Institute: https://institute.sfeir.com/en/kubernetes-training/resolve-errors-deployment-kubernetes
- Secrets | Kubernetes: https://kubernetes.io/docs/concepts/configuration/secret
- 10 Most Common Reasons Kubernetes Deployments Fail (Part 1): https://kukulinski.com/10-most-common-reasons-kubernetes-deployments-fail-part-1
- How to Fix CreateContainerConfigError from Misconfigured Secrets: https://oneuptime.com/blog/post/2026-02-09-createcontainerconfigerror-secrets/view
- Day 16/100 : Secret not found: https://medium.com/@shaikmustafa8991/day-16-100-secret-not-found-ab6cdab8ecd4

## How this was verified
Tests ran in an isolated container (`docker run --rm --network none`), replaying the sandbox command above. Evidence captured at 2026-10-06T17:20:58+00:00.

---
Opened by Mender for human review. Do not auto-merge; a person must review and merge this PR.