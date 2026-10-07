## Root cause
The deployment references a non-existent key 'token' in secret 'checkout-secrets' for the SECRET_KEY environment variable, but the secret only contains key 'secret_key'.

## Mechanism
1. Deployment manifest (deploy.yaml) defines env SECRET_KEY with secretKeyRef.name=checkout-secrets and key=token. 2. The actual secret (secret.yaml) only has stringData.secret_key, no 'token' key. 3. When kubelet tries to create the container config for new pods, it cannot resolve the secret key reference, resulting in CreateContainerConfigError with message 'couldn't find key token in Secret shop/checkout-secrets' [1][3]. 4. The running pod (checkout-74995d8c5b-kl29b) uses key 'secret_key' and succeeds, confirming the mismatch.

Confidence: 0.99 · Labels: missing_secret_key, secret_key_mismatch, createcontainerconfigerror, deployment_config_error

## Evidence relied on
- Error: couldn't find key token in Secret shop/checkout-secrets
- SECRET_KEY: <set to the key 'token' in secret 'checkout-secrets'>
- string_data["secret_key"] = "demo-only-not-a-real-key-0123456789abcdef0123456789abcdef"
- key: token

## Change
Files: demo/manifests/deploy.yaml
Rationale: The deployment incorrectly referenced key 'token' in secret 'checkout-secrets', but the secret only contains key 'secret_key'. Changing the key to 'secret_key' aligns the env var with the actual secret data, resolving the CreateContainerConfigError.

## Sandbox test results
Command: `python3 demo/app/check.py` — **PASSED** in 1 attempt(s)
- attempt 1: exit 0 in 0.6s — ok

## Tavily sources used
Queries: Kubernetes CreateContainerConfigError "couldn't find key" secretKeyRef; Kubernetes secretKeyRef key mismatch deployment secret missing key; Kubernetes pod CreateContainerConfigError secret reference failure
- Fix Kubernetes CreateContainerConfigError: Causes and Fixes | Coding Protocols: https://codingprotocols.com/blog/fix-kubernetes-createcontainerconfigerror
- [CreateContainerConfigError secret not found] sync secrets option · Issue #236 · kubernetes-sigs/secrets-store-csi-driver · GitHub: https://github.com/kubernetes-sigs/secrets-store-csi-driver/issues/236
- How to fix Kubernetes CreateContainerConfigError?: https://www.sherlocks.ai/guides/kubernetes/createcontainerconfigerror
- Fixing CreateContainerConfigError & CreateContainerError: https://spacelift.io/blog/createcontainerconfigerror
- Understanding Kubernetes `CreateContainerConfigError`: Causes and Solutions | by Michael Arauza | Medium: https://medium.com/@michaelarauza/understanding-kubernetes-createcontainerconfigerror-causes-and-solutions-e5d8f834970d
- Allow Retrieval of PlainText ExternalSecret (no key value) In Container Spec · external-secrets/kubernetes-external-secrets · Discussion #573 · GitHub: https://github.com/external-secrets/kubernetes-external-secrets/discussions/573
- How to Fix 'Secret Management' Issues: https://oneuptime.com/blog/post/2026-01-24-secret-management-issues/view
- Resolve Common Kubernetes Deployment Errors | SFEIR Institute: https://institute.sfeir.com/en/kubernetes-training/resolve-errors-deployment-kubernetes
- CreateContainerConfigError — Resolve Missing Secrets, ConfigMaps and Keys | Gronex: https://gronex.org/errors/kubernetes-createcontainerconfigerror-secret-configmap
- How to Fix CreateContainerConfigError from Misconfigured Secrets: https://oneuptime.com/blog/post/2026-02-09-createcontainerconfigerror-secrets/view
- Fix CreateContainerConfigError & CreateContainerError: https://www.groundcover.com/kubernetes-troubleshooting/createcontainerconfigerror-createcontainererror
- How to Fix CreateContainerConfigError from Misconfigured Secrets: https://oneuptime.com/blog/post/2026-02-09-createcontainerconfigerror-secrets/view
- Fix Kubernetes CreateContainerConfigError: Causes and Fixes | Coding Protocols: https://codingprotocols.com/blog/fix-kubernetes-createcontainerconfigerror
- CreateContainerConfigError vs CreateContainerError in K8s: https://www.perfectscale.io/blog/createcontainerconfigerror
- Resolve Common Kubernetes Deployment Errors | SFEIR Institute: https://institute.sfeir.com/en/kubernetes-training/resolve-errors-deployment-kubernetes

## How this was verified
Tests ran in an isolated container (`docker run --rm --network none`), replaying the sandbox command above. Evidence captured at 2026-10-06T19:54:55+00:00.

---
Opened by Mender for human review. Do not auto-merge; a person must review and merge this PR.