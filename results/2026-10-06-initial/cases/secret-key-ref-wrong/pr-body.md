## Root cause
The deployment manifest references secret key 'token' in secret 'checkout-secrets', but the secret only contains key 'secret_key'.

## Mechanism
The deployment spec (deploy.yaml) defines env var SECRET_KEY with secretKeyRef pointing to key 'token' in secret 'checkout-secrets' [1]. The secret manifest (secret.yaml) only defines stringData.secret_key [2]. When kubelet attempts to create container config for new pods, it cannot find key 'token' in the secret, emitting 'couldn't find key token in Secret shop/checkout-secrets' [3] and leaving pods in CreateContainerConfigError. The running pod (hash 5c85758c96) uses key 'secret_key' and succeeds, while newer ReplicaSets (hashes 5b569c99d4, 6f4d5845b5) use the faulty 'token' reference.

Confidence: 0.95 · Labels: secret_key_mismatch, createcontainerconfigerror, missing_secret_key, deployment_config_error

## Evidence relied on
- Error: couldn't find key token in Secret shop/checkout-secrets
- SECRET_KEY:  <set to the key 'token' in secret 'checkout-secrets'>
- stringData:
  secret_key: "demo-only-not-a-real-key-0123456789abcdef0123456789abcdef"
- key: token

## Change
Files: demo/manifests/deploy.yaml
Rationale: The deployment manifest incorrectly referenced secret key 'token' in secret 'checkout-secrets', but the secret only contains key 'secret_key'. Changing the key to 'secret_key' aligns the env var SECRET_KEY with the actual secret data, resolving the CreateContainerConfigError.

## Sandbox test results
Command: `python3 demo/app/check.py` — **PASSED** in 1 attempt(s)
- attempt 1: exit 0 in 0.6s — ok

## Tavily sources used
Queries: Kubernetes CreateContainerConfigError couldn't find key in Secret secretKeyRef mismatch; Kubernetes deployment secret key reference error missing key token secretKeyRef; Kubernetes pod pending CreateContainerConfigError secret key not found
- Kubernetes Error Guide: 'CreateContainerConfigError' Missing: https://devopsaitoolkit.com/blog/kubernetes-error-createcontainerconfigerror
- Fix Kubernetes CreateContainerConfigError: Causes and Fixes | Coding Protocols: https://codingprotocols.com/blog/fix-kubernetes-createcontainerconfigerror
- CreateContainerConfigError: Causes and Fix | Kubernetes: https://devopslesson.com/troubleshooting/createcontainerconfigerror
- Fix Kubernetes CreateContainerConfigError (2026): https://lucaberton.com/blog/fix-kubernetes-createcontainerconfigerror
- How to Fix CreateContainerConfigError from Misconfigured Secrets: https://oneuptime.com/blog/post/2026-02-09-createcontainerconfigerror-secrets/view
- Resolve Common Kubernetes Deployment Errors | SFEIR Institute: https://institute.sfeir.com/en/kubernetes-training/resolve-errors-deployment-kubernetes
- CreateContainerConfigError — Resolve Missing Secrets, ConfigMaps and Keys | Gronex: https://gronex.org/errors/kubernetes-createcontainerconfigerror-secret-configmap
- Unable to use secretKeyRef when key is not value #2329: https://github.com/kubernetes-sigs/kustomize/issues/2329
- How to Fix 'Secret Management' Issues: https://oneuptime.com/blog/post/2026-01-24-secret-management-issues/view
- Resolve the 10 Most Common Kubernetes Deployment Errors | SFEIR Institute: https://institute.sfeir.com/en/kubernetes-training/resolve-errors-deployment-kubernetes-common
- [CreateContainerConfigError secret not found] sync secrets option · Issue #236 · kubernetes-sigs/secrets-store-csi-driver · GitHub: https://github.com/kubernetes-sigs/secrets-store-csi-driver/issues/236
- How to Fix CreateContainerConfigError from Misconfigured Secrets: https://oneuptime.com/blog/post/2026-02-09-createcontainerconfigerror-secrets/view
- 🚨 Day 16/100 : Secret not found: https://medium.com/@shaikmustafa8991/day-16-100-secret-not-found-ab6cdab8ecd4
- Fix the "CreateContainerConfigError" (CKA/CKAD Lab 10): https://www.youtube.com/watch?v=1V8egFEmqdk
- Kubernetes CreateContainerConfigError and CreateContainerError | Sysdig: https://www.sysdig.com/blog/kubernetes-createcontainerconfigerror-createcontainererror

## How this was verified
Tests ran in an isolated container (`docker run --rm --network none`), replaying the sandbox command above. Evidence captured at 2026-10-06T17:31:40+00:00.

---
Opened by Mender for human review. Do not auto-merge; a person must review and merge this PR.