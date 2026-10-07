## Root cause
Deployment spec references image tag '1.9.9' which does not exist in the container registry; only tag '1.0.0' is published and allowlisted [4].

## Mechanism
1. Deployment manifest specifies image: mender-demo-app:1.9.9 with comment noting 'release tag: 1.0.0 (the only published tag)' [4]. 2. New ReplicaSet checkout-64b956cff4 rolls out with this tag. 3. Kubelet attempts to pull docker.io/library/mender-demo-app:1.9.9. 4. Registry responds 'pull access denied, repository does not exist or may require authorization: server message: insufficient_scope: authorization failed' [1]. 5. Pod enters ImagePullBackOff and never becomes Ready. 6. Older ReplicaSet checkout-f584c55cc continues running on valid tag 1.0.0 [2,3].

Confidence: 0.95 · Labels: image_tag, image_pull_failure, deployment_config

## Evidence relied on
- Pulling image "mender-demo-app:1.9.9"
- Failed to pull image "mender-demo-app:1.9.9": failed to pull and unpack image "docker.io/library/mender-demo-app:1.9.9": failed to resolve reference "docker.io/library/mender-demo-app:1.9.9": pull access denied, repository does not exist or may require authorization: server message: insufficient_scope: authorization failed
- image: mender-demo-app:1.9.9  # release tag: 1.0.0 (the only published tag)
- IMAGE_TAG_ALLOWLIST = {"1.0.0"}
- Image: mender-demo-app:1.0.0 (on running pods)

## Change
Files: demo/manifests/deploy.yaml
Rationale: The deployment incorrectly references image tag '1.9.9' which does not exist in the registry. The only published and allowlisted tag is '1.0.0'. Changing the image tag to '1.0.0' resolves the ImagePullBackOff and allows the pod to start.

## Sandbox test results
Command: `python3 demo/app/check.py` — **PASSED** in 1 attempt(s)
- attempt 1: exit 0 in 0.7s — ok

## Tavily sources used
Queries: "insufficient_scope: authorization failed" mender-demo-app; Kubernetes ImagePullBackOff "insufficient_scope" container registry; mender-demo-app:1.9.9 tag not found registry pull access denied
- Insufficient Scope Error - Questions - Square Developer Forums: https://developer.squareup.com/forums/t/insufficient-scope-error/1374
- server message: insufficient_scope: authorization failed ...: https://github.com/docker/buildx/issues/2364
- #40 - error when uploading insufficient_scope: authorization failed - woodpecker-plugins/docker-buildx - Codeberg.org: https://codeberg.org/woodpecker-plugins/docker-buildx/issues/40
- ERROR: failed to solve: resources: pull access denied, repository does not exist or may require…: https://medium.com/bugs-that-bite/error-failed-to-solve-resources-pull-access-denied-repository-does-not-exist-or-may-require-ab23b9781a07
- insufficient_scope: authorization failed · Issue #160 · docker/build-push-action · GitHub: https://github.com/docker/build-push-action/issues/160
- gcloud - ImagePullBackOff Kubernetes from Google Cloud Container Registry - Server Fault: https://serverfault.com/questions/963638/imagepullbackoff-kubernetes-from-google-cloud-container-registry
- Kubernetes ImagePullBackOff Explained: https://fshaikh2.wordpress.com/2025/01/05/kubernetes-imagepullbackoff-explained
- Kubernetes ImagePullBackOff: What It Is and How to Fix It: https://www.groundcover.com/kubernetes-troubleshooting/imagepullbackoff
- What Is Kubernetes ImagePullBackOff Error and How to Fix It · Dash0: https://www.dash0.com/guides/kubernetes-imagepullbackoff
- What Is Kubernetes ImagePullBackOff Error and How to Fix It · Dash0: https://lumigo.io/kubernetes-troubleshooting/kubernetes-imagepullbackoff
- Mender Client | Mender documentation: https://docs.mender.io/troubleshoot/mender-client
- Homebrew Formulae: homebrew-core: https://formulae.brew.sh/formula
- The Frame Mender, Washington, DC 20006, US - MapQuest: https://www.mapquest.com/us/district-of-columbia/the-frame-mender-713454192
- Vulnerability Summary for the Week of November 4, 2024 | CISA: https://www.cisa.gov/news-events/bulletins/sb24-317
- Demonstrating the Mender Troubleshoot Add-on: https://mender.io/resources/videos/mender-troubleshoot-add-on-use-case

## How this was verified
Tests ran in an isolated container (`docker run --rm --network none`), replaying the sandbox command above. Evidence captured at 2026-10-06T19:16:33+00:00.

---
Opened by Mender for human review. Do not auto-merge; a person must review and merge this PR.