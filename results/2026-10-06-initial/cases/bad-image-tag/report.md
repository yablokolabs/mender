# Root cause: checkout pod ImagePullBackOff due to unpublished image tag 1.9.9

Service `checkout` in namespace `shop`.

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

## Tavily sources
Queries: "insufficient_scope: authorization failed" docker pull; mender-demo-app:1.9.9 image not found repository does not exist; Kubernetes ImagePullBackOff insufficient_scope private registry
- [Runner docker pull fails with insufficient_scope - GitLab CI/CD - GitLab Forum](https://forum.gitlab.com/t/runner-docker-pull-fails-with-insufficient-scope/106063) — # Runner docker pull fails with insufficient\_scope

### Problem to solve

We started seeing this intermittent failure with deploy jobs on our self-hosted Gitlab when the runner tries to pull the image that the job is configured to use:

pull access denied, repository does not exist or may require authorization: server message: insufficient\_scope: authorization failed.

The job is configured to pull an image from a different project, and that project has the “Limit access to this project” setting disabled, as most of our deploy jobs across our projects need to access this image. This has been working fine.

It’s odd that this just started happening and that it happens intermittently. Seems like failures due to tokens with invalid scope should happen all the time or never. [...] ### Related topics

| Topic |  | Replies | Views | Activity |
 ---  --- 
| Cluster Management Project: Failing to pull CI image  GitLab CI/CD | 2 | 864 | July 21, 2021 |
| Gitlab CE Registry "500" & "Insufficient Scope"  How to Use GitLab docker ,  registry | 1 | 1087 | February 14, 2019 |
| Pulling Docker image from GitLab Container Registry stopped working, only for one project  GitLab CI/CD ci ,  docker ,  pipelines | 16 | 99159 | June 13, 2025 |
| Facing error "server message: insufficient\_scope: authorization failed" when running simple docker command from gitlab  How to Use GitLab docker | 0 | 822 | August 5, 2025 |
| Pull access denied for kubernetes runner custom image  Infrastructure as Code & Cloud Native runner ,  kubernetes | 0 | 874 | July 13, 2021 | [...] Powered by Discourse, best viewed with JavaScript enabled
- [Docker hub autobuilds started to fail a few hours ago (copy from private repos within the same organization) - Docker Hub - Docker Community Forums](https://forums.docker.com/t/docker-hub-autobuilds-started-to-fail-a-few-hours-ago-copy-from-private-repos-within-the-same-organization/129402) — `2022-09-26T16:41:41Z #6 FROM docker.io/private/app-common:latest
2022-09-26T16:41:41Z #6 resolve docker.io/private/app-common:latest 0.0s done
2022-09-26T16:41:41Z #6 ERROR: pull access denied, repository does not exist or may require authorization: server message: insufficient_scope: authorization failed
2022-09-26T16:41:41Z
2022-09-26T16:41:41Z #7 [internal] load build context
2022-09-26T16:41:41Z #7 transferring context: 482.35kB 0.0s done
2022-09-26T16:41:41Z #7 CANCELED
2022-09-26T16:41:41Z ------
2022-09-26T16:41:41Z > FROM docker.io/private/app-common:latest:
2022-09-26T16:41:41Z ------ [...] 2022-09-26T16:41:41Z ------
2022-09-26T16:41:41Z ERROR: failed to solve: failed to load cache key: pull access denied, repository does not exist or may require authorization: server message: insufficient_scope: authorization failed
2022-09-26T16:41:41Z Build failed using Buildkit (1)` [...] `docker.io/private/app-common:latest` is a private repo within the same organization. I wonder why authorization fails all of a sudden considering that it worked for quite some time until now (as you can see in the screenshot).

`docker.io/private/app-common:latest`

image

image1283×582 48.9 KB

image

Do I need to do any extra settings to be able to copy from private repos within the same organization?

Here are logs from when authentication worked:
- [insufficient_scope: authorization failed · Issue #160 · docker/build-push-action · GitHub](https://github.com/docker/build-push-action/issues/160) — ## Navigation Menu

# insufficient\_scope: authorization failed #160

## Description

@AntonioFalcaoJr

### Behaviour

#### Steps to reproduce this issue

#### Expected behaviour

Publish image to docker hub

#### Actual behaviour

`ERROR: server message: insufficient_scope: authorization failed`

`ERROR: server message: insufficient_scope: authorization failed`

### Configuration

  

### Command produced

### Logs [...] ### Configuration

  

### Command produced

### Logs

`#33 exporting to image
#33 exporting layers
#33 exporting layers 2.4s done
#33 exporting manifest sha256:3c6a2a955932783e726461031bee8657c2ec7f2b2f239c110ba44ae58effef69 done
#33 exporting config sha256:6d39eefff02cee7c50511f16bd824957f3ef082ed60324850954a5aa3b13a5ee done
#33 pushing layers
#33 pushing layers 0.2s done
#33 ERROR: server message: insufficient_scope: authorization failed

> exporting to image:

failed to solve: rpc error: code = Unknown desc = server message: insufficient_scope: authorization failed
Error: The process '/usr/bin/docker' failed with exit code 1`

## Activity

## Metadata

## Metadata

### Assignees

### Labels

### Type

### Projects

### Milestone

### Relationships

### Development

## Issue actions [...] ### Relationships

### Development

## Issue actions

## Footer

### Footer navigation
- [server message: insufficient_scope: authorization failed](https://github.com/microsoft/vscode-docker/issues/4379) — I assume you are using a PAT (personal access token) for authentication to Docker Hub? Does your PAT have read and write scopes?
- [Docker image can be pushed to one repo, but not another - How to Use GitLab - GitLab Forum](https://forum.gitlab.com/t/docker-image-can-be-pushed-to-one-repo-but-not-another/76199) — `docker buildx`
`customer/foo/foo:latest`
 `=> => pushing layers
=> [auth] customer/foo/foo:pull,push token for registry.example.com
=> [auth] customer/foo/foo:pull,push token for registry.example.com
=> [auth] customer/foo/foo:pull,push token for registry.example.com
=> [auth] main/foo/foo:pull customer/foo/foo:pull,push token for registry.example.com
=> [auth] customer/foo/foo:pull,push token for registry.example.com
=> [auth] customer/foo/foo:pull,push token for registry.example.com
=> [auth] main/foo/foo:pull customer/foo/foo:pull,push token for registry.example.com

> exporting to image:

ERROR: failed to solve: server message: insufficient_scope: authorization failed` [...] To push, I am using a private token with read/write registry scope that is not tied to any particular project (I created it in my user account).

Why can’t I push the image with another tag? Curiously, I see the `main/foo/foo:pull` reference in the second build step despite me not ever specifying the `main` part during this build. I am essentially doing:

`main/foo/foo:pull`
`main`
`docker buildx create --name mybuilder --driver docker-container --bootstrap --use
docker buildx build \
--platform linux/amd64,linux/arm64 \
--push \
-t "${REGISTRY}/${REGISTRY_IMAGE_PREFIX}/${imageNameLatest}" \
.`

Where `REGISTRY_IMAGE_PREFIX` is either `main/foo` or `customer/foo`.

`REGISTRY_IMAGE_PREFIX`
`main/foo`
`customer/foo`

Any ideas?

I can boil down the problem to: [...] `$ docker pull hello-world:latest
latest: Pulling from library/hello-world
7050e35b49f5: Pull complete
Digest: sha256:18a657d0cc1c7d0678a3fbea8b7eb4918bba25968d3e1b0adebfa71caddbc346
Status: Downloaded newer image for hello-world:latest
docker.io/library/hello-world:latest
$ docker tag hello-world:latest registry.example.com/main/foo/foo:latest
$ docker push registry.example.com/main/foo/foo:latest
The push refers to repository [registry.example.com/main/foo/foo]
efb53921da33: Layer already exists
foo: digest: sha256:432f982638b3aefab73cc58ab28f5c16e96fdb504e8c134fc58dff4bae8bf338 size: 525
$ docker tag hello-world:latest registry.example.com/customer/foo/foo:latest
$ docker push registry.example.com/customer/foo/foo:latest
- [Mender](https://www.zoominfo.com/c/mender/459811321) — # Mender. Mender specializes in providing secure, reliable, and scalable over-the-air software updates for IoT devices. Their solutions target a wide range of industries including automotive, medical, and smart energy, aiming to serve both startups and large enterprises. Mender's platform allows developers to seamlessly integrate updates into their existing... ## Company Details. - **Industries:** Software; Storage & System Management Software. ## Social Media. ## Tech Stack. ## News & Media. - The 2026 State of Industrial IoT Device Lifecycle Management reveals that almost 3 in 5 OEMs expect existing infrastructure to fall short within three years — for more than 1 in 10, that point is less than a year away. PALO ALTO, Calif., May 18, 2026 /PRNewswire/ -- Northern.tech, the... - Mender.io has released a new integration with Microsoft Azure IoT Hub for more secure and robust IoT device management at scale. - SAN FRANCISCO, March 19, 2019 /PRNewswire/ -- The team behind Mender.io, the leading open source project for over-the-air (OTA) software update management for IoT devices, unveils Mender Enterprise: the supported version of Mender that extends software updates to all software and devices... - SAN FRANCISCO, Dec. 4, 2018 /PRNewswire/ -- Northern.tech, Inc, the company behind the Mender.io open source project to manage over-the-air (OTA) software updates for IoT devices, announces Mender Hub: a community repository to enable OTA updates for any connected device and OS.
- [mender-dist-packages/scripts/install-mender.sh at master](https://github.com/mendersoftware/mender-dist-packages/blob/master/scripts/install-mender.sh) — A repository containing the packaging scripts for Mender binary packages. Setting up mender-gateway with demo configuration, certificates and key" Set the LSB_
- [Homebrew Formulae: homebrew-core](https://formulae.brew.sh/formula) — # [Homebrew Formulae](https://formulae.brew.sh/). [a2ps](https://formulae.brew.sh/formula/a2ps)4.15.8 Any-to-PostScript filter. [abseil](https://formulae.brew.sh/formula/abseil)20260817.0 C++ Common Libraries. [actions-up](https://formulae.brew.sh/formula/actions-up)1.18.0 Tool to update GitHub Actions to latest versions with SHA pinning. [aescrypt](https://formulae.brew.sh/formula/aescrypt)0.7 Program for encryption/decryption. [akku](https://formulae.brew.sh/formula/akku)1.1.0 Package manager for Scheme. [alejandra](https://formulae.brew.sh/formula/alejandra)4.0.0 Command-line tool for formatting Nix Code. [ykman](https://formulae.brew.sh/formula/ykman)5.9.2 Tool for managing your YubiKey configuration. [yo](https://formulae.brew.sh/formula/yo)7.0.1 CLI tool for running Yeoman generators. [you-get](https://formulae.brew.sh/formula/you-get)0.4.1743 Dumb downloader that scrapes the web. [youplot](https://formulae.brew.sh/formula/youplot)0.5.0 Command-line tool that draw plots on the terminal. [yuicompressor](https://formulae.brew.sh/formula/yuicompressor)2.4.8 Yahoo! [yyjson](https://formulae.brew.sh/formula/yyjson)0.12.0 High performance JSON library written in ANSI C. [z3](https://formulae.brew.sh/formula/z3)5.1.0 High-performance theorem prover. [zbar](https://formulae.brew.sh/formula/zbar)0.23.93 Suite of barcodes-reading tools. [zbctl](https://formulae.brew.sh/formula/zbctl)8.6.0 Zeebe CLI client. [zboy](https://formulae.brew.sh/formula/zboy)0.71 GameBoy emulator. [zebra](https://formulae.brew.sh/formula/zebra)2.2.11 Information management system. [zero](https://formulae.brew.sh/formula/zero)0.8.0 Terminal coding agent you own. [zeromq](https://formulae.brew.sh/formula/zeromq)4.3.5 High-performance, asynchronous messaging library. [zimfw](https://formulae.brew.sh/formula/zimfw)1.20.1 Zsh plugin manager. [zlog](https://formulae.brew.sh/formula/zlog)1.2.18 High-performance C logging library. [zls](https://formulae.brew.sh/formula/zls)0.16.0 Language Server for Zig. [zplug](https://formulae.brew.sh/formula/zplug)2.4.2 Next-generation plugin manager for zsh. [zsh](https://formulae.brew.sh/formula/zsh)5.9.2 UNIX shell (command interpreter). [zshdb](https://formulae.brew.sh/formula/zshdb)1.1.4 Debugger for zsh. [zsync](https://formulae.brew.sh/formula/zsync)0.8.0 File transfer program. [zug](https://formulae.brew.sh/formula/zug)0.1.2 C++ library providing transducers. [zx](https://formulae.brew.sh/formula/zx)8.8.5 Tool for writing better scripts. [zzz](https://formulae.brew.sh/formula/zzz)1 Command-line tool to put Macs to sleep.
- [Building for demo | Mender documentation](https://docs.mender.io/operating-system-updates-yocto-project/build-for-demo) — This document outlines the steps needed to build a Yocto Project image for a device. The build output will most notably include: a disk image for flashing
- [The Circuit Mender](https://www.mapquest.com/us/south-carolina/the-circuit-mender-655120829) — *   Image 5: Download on the App Store. # The Circuit Mender. The Circuit Mender, located in Columbia, SC, specializes in comprehensive IT support and consulting services, addressing a wide range of technology-related issues for both businesses and individuals. Image 19: Best Restaurants in Columbia Best Restaurants in Columbia 3 places. Image 20: Top Things to Do in Columbia Top Things to Do in Columbia 3 places. Image 21: Best Day Trips from Columbia Best Family-Friendly Activities in Columbia 3 places. Image 22: Best Day Trips from Columbia Best Parks in Columbia 4 places. Image 23: Best Neighborhoods in Columbia Best Neighborhoods in Columbia 3 places. Image 24: Best Day Trips from Columbia Best Day Trips from Columbia 5 places. Image 25: Top Things to Do in Florence Sc Top Things to Do in Florence Sc 9 places. Image 26: Best Family-Friendly Activities in Florence Sc Best Family-Friendly Activities in Florence Sc 7 places.
- [Kubernetes ImagePullBackOff: What It Is and How to Fix It](https://www.groundcover.com/kubernetes-troubleshooting/imagepullbackoff) — ## What is ImagePullBackOff Error and Why Does it Occur?

Kubernetes ImagePullBackOff is a status that means Kubernetes could not pull a specified container image and is retrying with increasing delays, leaving the container stuck in the Waiting state. For Kubernetes users, developers, and DevOps teams, this is a practical troubleshooting problem: if the image never pulls, the container never starts, which can disrupt application availability and point to broader issues with registry access, authentication, or networking. [...] ProblemDescriptionHow to resolve Incorrect image   
configurationImage name, tag and/or  
digest value is not properly set.Make sure image configuration matches the  
configuration of the container registry.Inaccessible  
container registryKubernetes can't access  
the container registry.Ensure that Kubernetes and the registry can  
connect over the network. Also make sure the  
registry server is up and running properly.Authentication and  
Authorization IssuesKubernetes can't authenticate  
with a private registry.Make sure the secret for registry access  
is properly configured.Resource Constraints and  
Kubernetes Cluster LoadKubernetes lacks enough  
resources to perform the image pull.Allocate more resources, or wait until cluster [...] The image doesn't exist in the image registry.
 The image name or image tag that you've defined in the configuration for a container or Pod contains a typo.
 Networking issues prevent Kubernetes from connecting to the container image registry.
 The image is stored in a private registry and the secrets that Kubernetes needs to access it are not properly configured.

When you see an ImagePullBackOff error, your job is to identify the specific cause of the pull failure and correct it so the Pod can start normally.

## What is ErrImagePull Error?
- [What Is Kubernetes ImagePullBackOff Error and How to Fix It · Dash0](https://www.dash0.com/guides/kubernetes-imagepullbackoff) — Dash0 acquires Polar Signals

Dash0 Logo

Sign inBook a demo

Start Free Trial

Last updated:February 24, 2026

# What Is Kubernetes ImagePullBackOff Error and How to Fix It

## What Is Kubernetes ImagePullBackOff?

The ImagePullBackOff error is a common error message in Kubernetes that occurs when a container running in a pod fails to pull the required image from a container registry. This error can occur for a variety of reasons, including network connectivity issues, incorrect image name or tag, missing credentials, or insufficient permissions. [...] ### Step 3: Troubleshoot and fix the error

Once you have collected information and reviewed the events section, you can begin to troubleshoot the issue. For example, if the error message is `Repository does not exist`, it indicates that the container registry does not exist or is not accessible. Kubernetes pulls images from Docker Hub by default, so this error could occur if the cluster is using a private registry. To resolve this issue, ensure that the container registry is available and that the pod definition specifies the correct registry URL. [...] Network connectivity issues: The ImagePullBackOff error can also occur when there are issues in the connectivity between the container registry and the Kubernetes cluster. If there is a firewall blocking the connection or a slow network connection, Kubernetes may not be able to download the image from the container registry. It is important to ensure that there are no network connectivity issues and that the Kubernetes cluster can access the container registry.
- [ImagePullBackOff: Causes and How to Fix It](https://cast.ai/blog/imagepullbackoff) — ### Missing imagePullSecret

Private registries require authentication. Kubernetes stores registry credentials in a `Secret` of type `kubernetes.io/dockerconfigjson` and references it via `spec.imagePullSecrets` in the pod spec.

Create the secret manually:

```
kubectl create secret docker-registry regcred \ --docker-server= \ --docker-username= \ --docker-password= \ --docker-email= \ -n 
```

The raw YAML form of the same secret looks like this:

```
apiVersion: v1 kind: Secret metadata: name: regcred namespace: default type: kubernetes.io/dockerconfigjson data: .dockerconfigjson: 
```

Reference the secret in your pod spec:

```
spec: imagePullSecrets: - name: regcred containers: - name: myapp image: myrepo/myapp:1.0.0
``` [...] Once your pods are pulling successfully, connect your cluster to Cast AI. Kvisor scans container images for vulnerabilities using registry credentials configured in the Cast AI console. Add your registry once, and both your pods and Kvisor can access the same private images.

Check Kubernetes exit codes to understand what killed the container

## Frequently Asked Questions

What is ImagePullBackOff in Kubernetes?

ImagePullBackOff is a pod status in Kubernetes indicating the kubelet failed to pull the container image and is waiting before retrying. It follows ErrImagePull, which is the initial failure state. Retries follow exponential backoff, starting at a few seconds and capping at 5 minutes. The pod stays in this loop until the underlying problem is resolved or the pod is deleted. [...] ```
kubectl get pod  -n  -o jsonpath='{.spec.imagePullSecrets[].name}'
```

If this returns empty and the image lives in a private registry, that is your problem.

### kubectl describe pod

The Events section at the bottom of `kubectl describe pod  -n`  tells you the exact error message from the container runtime. This is where the error patterns live: `manifest not found`, `unauthorized`, `toomanyrequests`, `i/o timeout`.
- [Fix Kubernetes ImagePullBackOff: Registry Issues & Authentication Guide](https://www.youtube.com/watch?v=4TLDyyde-XY) — [5:22] First, authenticate with DockerHub using your credentials, which increases your rate limit from 100 polls to 200 polls
[5:30] per 6 hours for free accounts. Second, set up a private registry mirror or pull through cache within your infrastructure, which caches images
[5:38] locally and dramatically reduces external pulls. Third, configure the image pull policy to if not present in
[5:45] your pod specifications, which tells Kubernetes to use locally cached images whenever possible instead of always pulling from the remote registry.
[5:57] Let's review the complete workflow for resolving registry issues. Step one, verify that the image path and registry URL in your pod specification are [...] ### Transcript
[0:00] Welcome to this tutorial on troubleshooting image pullback errors caused by registry issues. In this video, we'll focus specifically on
[0:08] problems related to container registries that prevent Kubernetes from pulling images successfully. Registry issues are
[0:16] one of the most common causes of image pull failures and understanding how to diagnose and fix them is essential for
[0:23] any Kubernetes administrator or developer.
[0:28] Registry issues occur when Kubernetes cannot reach or authenticate with container registries where your images are stored. These problems fall into
[0:37] three main categories. First, registry access problems happen when Kubernetes cannot connect to the registry endpoint [...] [2:10] This verifies that the registry URL and image path are spelled correctly.
[2:15] Finally, check if authentication secrets exist by running cubectal get secrets.
[2:20] These three commands give you a complete picture of what might be preventing the image pull.
[2:28] To authenticate with private registries, you need to create a Kubernetes secret that stores your Docker credentials. Use
[2:35] the cubectal create secret docker registry command followed by a name for your secret such as regard. Then specify
[2:43] the dockery server parameter with your registry URL, docker hyphen username with your username, dockery password
[2:50] with your password and docker hyphen email with your email address. Remember this secret must be created in the same
- [Pull an Image from a Private Registry fails - ImagePullBackOff](https://stackoverflow.com/questions/63168804/pull-an-image-from-a-private-registry-fails-imagepullbackoff) — Problem pulling images when running private docker registry inside of Kubernetes 4 ImagePullBackOff error in Kubernetes while pulling