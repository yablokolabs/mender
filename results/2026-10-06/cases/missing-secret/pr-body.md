## Root cause
Deployment references secret 'checkout-secrets-x' but the actual secret in namespace 'shop' is named 'checkout-secrets' (missing '-x' suffix).

## Mechanism
1. Deployment manifest specifies env SECRET_KEY with secretKeyRef.name=checkout-secrets-x [deploy.yaml]. 2. Kubelet attempts to start pod checkout-94f578998-lvx2w and resolves the secret reference. 3. Secret 'checkout-secrets-x' does not exist in namespace 'shop' (only 'checkout-secrets' exists) [secret.yaml]. 4. Because the secret is non-optional (Optional: false), Kubernetes refuses to start the container and reports CreateContainerConfigError with message 'secret "checkout-secrets-x" not found' [events]. 5. The pod remains in Pending state with container state Waiting:CreateContainerConfigError [describe pod].

Confidence: 0.99 · Labels: missing_secret, secret_name_mismatch, createcontainerconfigerror, deployment_config_error

## Evidence relied on
- Error: secret "checkout-secrets-x" not found
- SECRET_KEY:  <set to the key 'secret_key' in secret 'checkout-secrets-x'>
- name: checkout-secrets
- secretKeyRef:
                  name: checkout-secrets-x

## Change
Files: demo/manifests/deploy.yaml
Rationale: Fix the secret name referenced in the Deployment's SECRET_KEY environment variable from 'checkout-secrets-x' to 'checkout-secrets' to match the existing secret in the shop namespace, resolving the CreateContainerConfigError.

## Sandbox test results
Command: `python3 demo/app/check.py` — **PASSED** in 1 attempt(s)
- attempt 1: exit 0 in 0.8s — ok

## Tavily sources used
Queries: Kubernetes CreateContainerConfigError secret not found deployment env secretKeyRef; pod pending CreateContainerConfigError missing secret reference mismatch manifest; Kubernetes deployment secretKeyRef name mismatch causes pod startup failure
- [CreateContainerConfigError secret not found] sync secrets option · Issue #236 · kubernetes-sigs/secrets-store-csi-driver · GitHub: https://github.com/kubernetes-sigs/secrets-store-csi-driver/issues/236
- How to Fix CreateContainerConfigError from Misconfigured Secrets: https://oneuptime.com/blog/post/2026-02-09-createcontainerconfigerror-secrets/view
- Fixing CreateContainerConfigError & CreateContainerError: https://spacelift.io/blog/createcontainerconfigerror
- 🚨 Day 16/100 : Secret not found: https://medium.com/@shaikmustafa8991/day-16-100-secret-not-found-ab6cdab8ecd4
- Kubernetes CreateContainerConfigError and CreateContainerError | Sysdig: https://www.sysdig.com/blog/kubernetes-createcontainerconfigerror-createcontainererror
- Fix CreateContainerError, CreateContainerConfigError in K8s: https://komodor.com/learn/how-to-fix-createcontainerconfigerror-and-createcontainer-errors
- How to Fix CreateContainerConfigError from Misconfigured Secrets: https://oneuptime.com/blog/post/2026-02-09-createcontainerconfigerror-secrets/view
- Fixing CreateContainerConfigError & CreateContainerError: https://spacelift.io/blog/createcontainerconfigerror
- Fix CreateContainerConfigError & CreateContainerError: https://www.groundcover.com/kubernetes-troubleshooting/createcontainerconfigerror-createcontainererror
- Troubleshooting and Resolving a Pod Stuck in 'CreateContainerConfigError' in Kubernetes · Coffee with Ana in the 🌩️: https://coffeewithana.cloud/posts/k8s-pod-createcontainerconfigerror
- Secrets | Kubernetes: https://kubernetes.io/docs/concepts/configuration/secret
- 🚨 Day 16/100 : Secret not found: https://medium.com/@shaikmustafa8991/day-16-100-secret-not-found-ab6cdab8ecd4
- Instagram: https://www.instagram.com/p/DUGL945mD7O
- 10 Most Common Reasons Kubernetes Deployments Fail (Part 1): https://kukulinski.com/10-most-common-reasons-kubernetes-deployments-fail-part-1
- Kubernetes Error Guide: 'CreateContainerConfigError' Missing: https://devopsaitoolkit.com/blog/kubernetes-error-createcontainerconfigerror

## How this was verified
Tests ran in an isolated container (`docker run --rm --network none`), replaying the sandbox command above. Evidence captured at 2026-10-06T19:46:52+00:00.

---
Opened by Mender for human review. Do not auto-merge; a person must review and merge this PR.