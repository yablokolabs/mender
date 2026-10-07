## Root cause
Deployment specifies image tag 1.9.9 which does not exist in the container registry; only tag 1.0.0 is published.

## Mechanism
A deployment update changed the container image from mender-demo-app:1.0.0 to mender-demo-app:1.9.9. The new ReplicaSet checkout-77bcd9dcbd attempts to start pods that pull this tag. The registry returns 'pull access denied, repository does not exist or may require authorization: server message: insufficient_scope: authorization failed' because tag 1.9.9 was never published [1]. The pod enters ImagePullBackOff while the older ReplicaSet checkout-fbf548748 continues running pods on the valid 1.0.0 tag.

Confidence: 0.95 · Labels: image_tag, image_pull_failure, deployment_config

## Evidence relied on
- Pulling image "mender-demo-app:1.9.9"
- Failed to pull image "mender-demo-app:1.9.9": failed to pull and unpack image "docker.io/library/mender-demo-app:1.9.9": failed to resolve reference "docker.io/library/mender-demo-app:1.9.9": pull access denied, repository does not exist or may require authorization: server message: insufficient_scope: authorization failed
- Image: mender-demo-app:1.0.0 (running pods)
- image: mender-demo-app:1.9.9  # release tag: 1.0.0 (the only published tag)
- IMAGE_TAG_ALLOWLIST = {"1.0.0"}

## Change
Files: demo/manifests/deploy.yaml
Rationale: The deployment incorrectly references image tag 1.9.9 which does not exist in the registry. Changing the image tag to 1.0.0 aligns with the only published tag and resolves the ImagePullBackOff error.

## Sandbox test results
Command: `python3 demo/app/check.py` — **PASSED** in 1 attempt(s)
- attempt 1: exit 0 in 0.7s — ok

## Tavily sources used
Queries: "insufficient_scope: authorization failed" docker pull; mender-demo-app:1.9.9 image not found repository does not exist; Kubernetes ImagePullBackOff insufficient_scope private registry
- Runner docker pull fails with insufficient_scope - GitLab CI/CD - GitLab Forum: https://forum.gitlab.com/t/runner-docker-pull-fails-with-insufficient-scope/106063
- Docker hub autobuilds started to fail a few hours ago (copy from private repos within the same organization) - Docker Hub - Docker Community Forums: https://forums.docker.com/t/docker-hub-autobuilds-started-to-fail-a-few-hours-ago-copy-from-private-repos-within-the-same-organization/129402
- insufficient_scope: authorization failed · Issue #160 · docker/build-push-action · GitHub: https://github.com/docker/build-push-action/issues/160
- server message: insufficient_scope: authorization failed: https://github.com/microsoft/vscode-docker/issues/4379
- Docker image can be pushed to one repo, but not another - How to Use GitLab - GitLab Forum: https://forum.gitlab.com/t/docker-image-can-be-pushed-to-one-repo-but-not-another/76199
- Mender: https://www.zoominfo.com/c/mender/459811321
- mender-dist-packages/scripts/install-mender.sh at master: https://github.com/mendersoftware/mender-dist-packages/blob/master/scripts/install-mender.sh
- Homebrew Formulae: homebrew-core: https://formulae.brew.sh/formula
- Building for demo | Mender documentation: https://docs.mender.io/operating-system-updates-yocto-project/build-for-demo
- The Circuit Mender: https://www.mapquest.com/us/south-carolina/the-circuit-mender-655120829
- Kubernetes ImagePullBackOff: What It Is and How to Fix It: https://www.groundcover.com/kubernetes-troubleshooting/imagepullbackoff
- What Is Kubernetes ImagePullBackOff Error and How to Fix It · Dash0: https://www.dash0.com/guides/kubernetes-imagepullbackoff
- ImagePullBackOff: Causes and How to Fix It: https://cast.ai/blog/imagepullbackoff
- Fix Kubernetes ImagePullBackOff: Registry Issues & Authentication Guide: https://www.youtube.com/watch?v=4TLDyyde-XY
- Pull an Image from a Private Registry fails - ImagePullBackOff: https://stackoverflow.com/questions/63168804/pull-an-image-from-a-private-registry-fails-imagepullbackoff

## How this was verified
Tests ran in an isolated container (`docker run --rm --network none`), replaying the sandbox command above. Evidence captured at 2026-10-06T16:55:13+00:00.

---
Opened by Mender for human review. Do not auto-merge; a person must review and merge this PR.