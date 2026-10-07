# Root cause: checkout deployment uses non-existent image tag 1.9.9 causing ImagePullBackOff

Service `checkout` in namespace `shop`.

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

## Tavily sources
Queries: "insufficient_scope: authorization failed" mender-demo-app; Kubernetes ImagePullBackOff "insufficient_scope" container registry; mender-demo-app:1.9.9 tag not found registry pull access denied
- [Insufficient Scope Error - Questions - Square Developer Forums](https://developer.squareup.com/forums/t/insufficient-scope-error/1374) — # Insufficient Scope Error

I started seeing this today, while everything was working fine about 2 weeks back.

I’m receiving the below error when trying to run a query using API Explorer.

`{
"errors": [
{
"code": "INSUFFICIENT_SCOPES",
"detail": "The merchant has not given your application sufficient permissions to do that. The merchant must authorize your application for the following scopes: [ORDERS_READ]",
"category": "AUTHENTICATION_ERROR"
}
]
}`

Can you share your application id? What endpoint are you hitting when you receive this error?

App Id: sq0idp-LXyFOXjv\_dK-4GfvXPdVQQ

Orders - Batch Retrieve [...] That will not work, you cannot add scopes via the API. You must go through the OAuth authorization url again. Refreshing the token will generate a new token with the same permissions. If you passed the `scopes` parameter, that’s only for reducing the scopes, not adding new scopes.

`scopes`

That was it! Thank you so much Stephen! I really appreciate your help.

### Related topics [...] Apologies for the confusion here, I didn’t realize these errors do not log the application id. I was able to find it using your location id tied to your application. So, looking your access tokens up, I see you’ve created several, I’m guessing through OAuth. Several of them only have `PAYMENTS_READ` permission, so this error is accurate: you need `ORDERS_READ` permission. If you are using OAuth, you need to be sure to include all of the scopes in the OAuth authorization URL.

`PAYMENTS_READ`
`ORDERS_READ`

No problem. I apologize for getting a little impatient as well.

I just refreshed a token using API Explorer adding Payments\_read and Orders\_Read scopes. But Im still getting the same error.
- [server message: insufficient_scope: authorization failed ...](https://github.com/docker/buildx/issues/2364) — The problem is that the auth token … fails with the authorization scope error because it is using the first auth token, instead of the second
- [#40 - error when uploading insufficient_scope: authorization failed - woodpecker-plugins/docker-buildx - Codeberg.org](https://codeberg.org/woodpecker-plugins/docker-buildx/issues/40) — See the attached file for the complete log.

```
#6 exporting to image #6 exporting layers done #6 exporting manifest sha256:d70f21776e6f47f590703c0fa97e5a6ecde1b559eb8132c59c75238cd45ccbba 0.0s done #6 exporting config sha256:49f2cd73abba5e27a691fcc994a161055f565296bfe76575d08f27e61a8216fc 0.0s done #6 pushing layers #6 pushing layers 0.7s done #6 ERROR: server message: insufficient_scope: authorization failed 
```

Uploading an image works using the docker CLI. [...] 0a884882e8e9: Pushed 994393dc58e7: Pushed latest: digest: sha256:4e2a54594cfe7002a98c483c28f6f3a78e5c7f4010c355a8cf960292a3fdecfe size: 1365 [...] Codeberg has changed its Terms of Use. View complete changes.

1. LLM-generated content is being restricted. View change or read the blog post
2. Cryptocurrency projects are no longer allowed. View change

woodpecker-plugins/docker-buildx

woodpecker-plugins/docker-buildx

9

Fork  33

Code   Issues 35   Pull requests 4   Releases 29   Packages 1   Activity

# error when uploading insufficient\_scope: authorization failed #40

New issue

opened 2022-11-10 14:31:55 +01:00 by Ghost · 5 comments

  Ghost commented 2022-11-10 14:31:55 +01:00

Copy link

### Steps to reproduce
- [ERROR: failed to solve: resources: pull access denied, repository does not exist or may require…](https://medium.com/bugs-that-bite/error-failed-to-solve-resources-pull-access-denied-repository-does-not-exist-or-may-require-ab23b9781a07) — Sitemap

Open in app

Sign up

Sign in

[](

Get app

Write

Search

Sign up

Sign in

Image 1: Unknown user

## Bugs That Bite

·
Follow publication

Image 2: Bugs That Bite
Helping make the world a better place, one error message at a time.

Follow publication

Member-only story

Error Message

Docker

Buildx

Build Context

Authorization

# ERROR: failed to solve: resources: pull access denied, repository does not exist or may require authorization: server message: insufficient_scope: authorization failed

## Misleading error message when using buildx with docker

Image 3: Teri Radichel

Teri Radichel

Follow

2 min read

·

Feb 20, 2024

[](

35

[](

[](

Listen

Share

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- [insufficient_scope: authorization failed · Issue #160 · docker/build-push-action · GitHub](https://github.com/docker/build-push-action/issues/160) — Skip to content   
 
 

## Navigation Menu

Sign in

Appearance settings

Sign in

Sign up

Appearance settings

You signed in with another tab or window. Reload to refresh your session. You signed out in another tab or window. Reload to refresh your session. You switched accounts on another tab or window. Reload to refresh your session. Dismiss alert

{{ message }}

docker   /  build-push-action  Public

 Notifications  You must be signed in to change notification settings
 Fork 737
 Star  5.4k

# insufficient\_scope: authorization failed #160

Copy link

Copy link

Closed

Closed

insufficient\_scope: authorization failed#160

Copy link

## Description

@AntonioFalcaoJr

AntonioFalcaoJr

opened on Oct 5, 2020

Issue body actions

### Behaviour

#### Steps to reproduce this issue [...] ### Logs

```
#33 exporting to image #33 exporting layers #33 exporting layers 2.4s done #33 exporting manifest sha256:3c6a2a955932783e726461031bee8657c2ec7f2b2f239c110ba44ae58effef69 done #33 exporting config sha256:6d39eefff02cee7c50511f16bd824957f3ef082ed60324850954a5aa3b13a5ee done #33 pushing layers #33 pushing layers 0.2s done #33 ERROR: server message: insufficient_scope: authorization failed ------ > exporting to image: ------ failed to solve: rpc error: code = Unknown desc = server message: insufficient_scope: authorization failed Error: The process '/usr/bin/docker' failed with exit code 1 
```

Reactions are currently unavailable

## Activity

Sign up for free to join this conversation on GitHub. Already have an account? Sign in to comment

## Metadata

## Metadata [...] ### Behaviour

#### Steps to reproduce this issue

1. Set up QEMU
2. Set up Docker Buildx
3. Login to DockerHub
4. Build and push

#### Expected behaviour

Publish image to docker hub

#### Actual behaviour

`ERROR: server message: insufficient_scope: authorization failed`

### Configuration
- [gcloud - ImagePullBackOff Kubernetes from Google Cloud Container Registry - Server Fault](https://serverfault.com/questions/963638/imagepullbackoff-kubernetes-from-google-cloud-container-registry) — Title: gcloud - ImagePullBackOff Kubernetes from Google Cloud Container Registry - Server Fault
#### Stack Exchange Network. Stack Exchange network consists of 183 Q&A communities including Stack Overflow, the largest, most trusted online community for developers to learn, share their knowledge, and build their careers. ### your communities. ### more stack exchange communities. # ImagePullBackOff Kubernetes from Google Cloud Container Registry. There appears to be some pull access issue, despite the fact that things should work right off the box when working with Kubernetes on GCP in combination with the Google Cloud. "Using Google Container Registry Kubernetes has native support for the Google Container Registry (GCR), when running on Google Compute Engine (GCE). If you are running your cluster on GCE or Google Kubernetes Engine, simply use the full image name (e.g. gcr.io/my\_project/image:tag). All pods in a cluster will have read access to images in this registry. I double checked that I used the right image name (copy pasted it from container registry). Normal Scheduled 7m default-scheduler Successfully assigned default/hello-web-694bc87958-rcdvg to gke-hello-cluster-default-pool-9cbfb505-588j. Normal SandboxChanged 7m (x3 over 7m) kubelet, gke-hello-cluster-default-pool-9cbfb505-588j Pod sandbox changed, it will be killed and re-created. Normal BackOff 7m (x6 over 7m) kubelet, gke-hello-cluster-default-pool-9cbfb505-588j Back-off pulling image "gcr.io/data-platform-tst/hello-app:v1". Normal Pulling 6m (x3 over 7m) kubelet, gke-hello-cluster-default-pool-9cbfb505-588j pulling image "gcr.io/data-platform-tst/hello-app:v1". Warning Failed 6m (x3 over 7m) kubelet, gke-hello-cluster-default-pool-9cbfb505-588j Failed to pull image "gcr.io/data-platform-tst/hello-app:v1": rpc error: code = Unknown desc = Error response from daemon: repository gcr.io/data-platform-tst/hello-app not found: does not exist or no pull access. Warning Failed 6m (x3 over 7m) kubelet, gke-hello-cluster-default-pool-9cbfb505-588j Error: ErrImagePull. Warning Failed 2m (x24 over 7m) kubelet, gke-hello-cluster-default-pool-9cbfb505-588j Error: ImagePullBackOff`. Robert van Overbeek's user avatar. Please make sure that you have the proper scopes set up within your cluster for the service account to pull the image. Please follow the Official Documentation that provides step-by-step instructions on how to grant users permission to pull an image from a **Container Registry.**. I understand that you are using Google Container Registry so in this case, GKE nodes already have access to the **Google Container Registry images** in the same **Google Cloud Platform** project as the cluster. So please check the scope you have given to your cluster. Nibrass H's user avatar. Find the answer to your question by asking.
- [Kubernetes ImagePullBackOff Explained](https://fshaikh2.wordpress.com/2025/01/05/kubernetes-imagepullbackoff-explained) — # Kubernetes ImagePullBackOff Explained The `ImagePullBackOff` error in Kubernetes indicates that a Pod is unable to start because it cannot pull the specified container image from the container registry. Below is a detailed explanation of the `ImagePullBackOff` error, its causes, and how to troubleshoot it. ### **What is ImagePullBackOff?** When Kubernetes attempts to create a container for a Pod, it first needs to pull the specified container image from a container registry (e.g., Docker Hub, Google Container Registry, etc.). If the image cannot be pulled, Kubernetes will retry pulling the image with an exponential backoff delay. ### **Common Causes of ImagePullBackOff** **Incorrect Image Name or Tag**: ### **How to Troubleshoot ImagePullBackOff** #### 1. Use `kubectl describe pod <pod-name>` to view detailed information about the Pod, including events that led to the `ImagePullBackOff` error. `kubectl describe pod <pod-name>` `kubectl describe pod <pod-name>` `Failed to pull image "<image-name>:<tag>": rpc error: code = Unknown desc = Error response from daemon: pull access denied for <image-name>, repository does not exist or may require 'docker login'` `Failed to pull image "<image-name>:<tag>": rpc error: code = Unknown desc = Error response from daemon: manifest for <image-name>:<tag> not found` These messages provide clues about the root cause. **Verify Image Name and Tag** Double-check the image name and tag in the Pod’s YAML file. Ensure that the image exists in the registry and the tag is correct. If the image is hosted in a private registry, ensure that: To create a secret for a private registry: `kubectl create secret docker-registry regcred \ #### 4. Ensure that the Kubernetes node can access the container registry: #### 5. If you’re using a public registry like Docker Hub, ensure that you haven’t exceeded the rate limits. Ensure that the node has sufficient disk space to pull and store the image. If the issue persists, check the logs of the container runtime (e.g., Docker, containerd) on the node for more details. `sudo journalctl -u docker.service` ### **Example of Fixing ImagePullBackOff** Suppose you have a Pod with the following YAML: `kubectl apply -f pod.yaml` ### **Summary** By following these steps, you can resolve the `ImagePullBackOff` error and get your Pod running successfully.
- [Kubernetes ImagePullBackOff: What It Is and How to Fix It](https://www.groundcover.com/kubernetes-troubleshooting/imagepullbackoff) — ## What is ImagePullBackOff Error and Why Does it Occur?

Kubernetes ImagePullBackOff is a status that means Kubernetes could not pull a specified container image and is retrying with increasing delays, leaving the container stuck in the Waiting state. For Kubernetes users, developers, and DevOps teams, this is a practical troubleshooting problem: if the image never pulls, the container never starts, which can disrupt application availability and point to broader issues with registry access, authentication, or networking. [...] ### Inaccessible Container Registry

If your Kubernetes cluster can't connect to your container registry, you'll get an ImagePullBackOff event.

Failure to connect is most often the result of a networking configuration problem; for example, your registry might be located on a private network that kubelet can't access. But container registry access issues could also result from problems like a server that hosts the registry temporarily crashing. These registry issues can also include registry rate limits on public services such as Docker Hub, and rate-limited pulls are more likely when many Kubernetes deployments or Pods are repeatedly requesting images. In addition, network issues or network connectivity issues on the Kubernetes node can stop it from reaching the registry. [...] ProblemDescriptionHow to resolve Incorrect image   
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
resources to perform the image pull.Allocate more resources, or wait until cluster
- [What Is Kubernetes ImagePullBackOff Error and How to Fix It · Dash0](https://www.dash0.com/guides/kubernetes-imagepullbackoff) — Dash0 acquires Polar Signals

Dash0 Logo

Sign inBook a demo

Start Free Trial

Last updated:February 24, 2026

# What Is Kubernetes ImagePullBackOff Error and How to Fix It

## What Is Kubernetes ImagePullBackOff?

The ImagePullBackOff error is a common error message in Kubernetes that occurs when a container running in a pod fails to pull the required image from a container registry. This error can occur for a variety of reasons, including network connectivity issues, incorrect image name or tag, missing credentials, or insufficient permissions. [...] Reaching the container registry rate limit: Some container registries limit the number of requests that can be made to their API in a given period of time. If the Kubernetes cluster exceeds this rate limit, the ImagePullBackOff error may occur. In this case, it is important to ensure that the Kubernetes cluster is not exceeding the rate limit and to contact the container registry to request a higher rate limit if needed. [...] Network connectivity issues: The ImagePullBackOff error can also occur when there are issues in the connectivity between the container registry and the Kubernetes cluster. If there is a firewall blocking the connection or a slow network connection, Kubernetes may not be able to download the image from the container registry. It is important to ensure that there are no network connectivity issues and that the Kubernetes cluster can access the container registry.
- [What Is Kubernetes ImagePullBackOff Error and How to Fix It · Dash0](https://lumigo.io/kubernetes-troubleshooting/kubernetes-imagepullbackoff) — Dash0 acquires Polar Signals

Dash0 Logo

Sign inBook a demo

Start Free Trial

Last updated:February 24, 2026

# What Is Kubernetes ImagePullBackOff Error and How to Fix It

## What Is Kubernetes ImagePullBackOff?

The ImagePullBackOff error is a common error message in Kubernetes that occurs when a container running in a pod fails to pull the required image from a container registry. This error can occur for a variety of reasons, including network connectivity issues, incorrect image name or tag, missing credentials, or insufficient permissions. [...] Reaching the container registry rate limit: Some container registries limit the number of requests that can be made to their API in a given period of time. If the Kubernetes cluster exceeds this rate limit, the ImagePullBackOff error may occur. In this case, it is important to ensure that the Kubernetes cluster is not exceeding the rate limit and to contact the container registry to request a higher rate limit if needed. [...] Network connectivity issues: The ImagePullBackOff error can also occur when there are issues in the connectivity between the container registry and the Kubernetes cluster. If there is a firewall blocking the connection or a slow network connection, Kubernetes may not be able to download the image from the container registry. It is important to ensure that there are no network connectivity issues and that the Kubernetes cluster can access the container registry.
- [Mender Client | Mender documentation](https://docs.mender.io/troubleshoot/mender-client) — This is caused by using an outdated version of the mender-artifact tool. To solve this issue, install mender-artifact from the Mender APT repository following
- [Homebrew Formulae: homebrew-core](https://formulae.brew.sh/formula) — # [Homebrew Formulae](https://formulae.brew.sh/). [a2ps](https://formulae.brew.sh/formula/a2ps)4.15.8 Any-to-PostScript filter. [abseil](https://formulae.brew.sh/formula/abseil)20260817.0 C++ Common Libraries. [actions-up](https://formulae.brew.sh/formula/actions-up)1.18.0 Tool to update GitHub Actions to latest versions with SHA pinning. [aescrypt](https://formulae.brew.sh/formula/aescrypt)0.7 Program for encryption/decryption. [akku](https://formulae.brew.sh/formula/akku)1.1.0 Package manager for Scheme. [alejandra](https://formulae.brew.sh/formula/alejandra)4.0.0 Command-line tool for formatting Nix Code. [ykman](https://formulae.brew.sh/formula/ykman)5.9.2 Tool for managing your YubiKey configuration. [yo](https://formulae.brew.sh/formula/yo)7.0.1 CLI tool for running Yeoman generators. [you-get](https://formulae.brew.sh/formula/you-get)0.4.1743 Dumb downloader that scrapes the web. [youplot](https://formulae.brew.sh/formula/youplot)0.5.0 Command-line tool that draw plots on the terminal. [yuicompressor](https://formulae.brew.sh/formula/yuicompressor)2.4.8 Yahoo! [yyjson](https://formulae.brew.sh/formula/yyjson)0.12.0 High performance JSON library written in ANSI C. [z3](https://formulae.brew.sh/formula/z3)5.1.0 High-performance theorem prover. [zbar](https://formulae.brew.sh/formula/zbar)0.23.93 Suite of barcodes-reading tools. [zbctl](https://formulae.brew.sh/formula/zbctl)8.6.0 Zeebe CLI client. [zboy](https://formulae.brew.sh/formula/zboy)0.71 GameBoy emulator. [zebra](https://formulae.brew.sh/formula/zebra)2.2.11 Information management system. [zero](https://formulae.brew.sh/formula/zero)0.8.0 Terminal coding agent you own. [zeromq](https://formulae.brew.sh/formula/zeromq)4.3.5 High-performance, asynchronous messaging library. [zimfw](https://formulae.brew.sh/formula/zimfw)1.20.1 Zsh plugin manager. [zlog](https://formulae.brew.sh/formula/zlog)1.2.18 High-performance C logging library. [zls](https://formulae.brew.sh/formula/zls)0.16.0 Language Server for Zig. [zplug](https://formulae.brew.sh/formula/zplug)2.4.2 Next-generation plugin manager for zsh. [zsh](https://formulae.brew.sh/formula/zsh)5.9.2 UNIX shell (command interpreter). [zshdb](https://formulae.brew.sh/formula/zshdb)1.1.4 Debugger for zsh. [zsync](https://formulae.brew.sh/formula/zsync)0.8.0 File transfer program. [zug](https://formulae.brew.sh/formula/zug)0.1.2 C++ library providing transducers. [zx](https://formulae.brew.sh/formula/zx)8.8.5 Tool for writing better scripts. [zzz](https://formulae.brew.sh/formula/zzz)1 Command-line tool to put Macs to sleep.
- [The Frame Mender, Washington, DC 20006, US - MapQuest](https://www.mapquest.com/us/district-of-columbia/the-frame-mender-713454192) — # The Frame Mender. The Frame Mender Eyeglass Frame Repair Centers. "It was surprisingly hard to find a place that repairs glasses at a reasonable price, and I'm so glad I found this one. "I had another great experience with Moniqua. She went above and beyond to help me and understand my requirement. "I had a great experience with Dr. Miller and the team at MyEyeDr, L Street. I have been seeing him for 17 years, and I continue to come to DC...". Some background: I actually stopped by at APEX by chance, to see if they could fix my eye glass frames (the screw had broken on...". Free Things to Do in Washington, DC. Best Restaurants in Clinton Ia. Best Restaurants in Clinton Ia. Top Things to Do in Clinton Ia. Top Things to Do in Clinton Ia. Best Family-Friendly Activities in Clinton Ia. Best Family-Friendly Activities in Clinton Ia. Best Day Trips from Clinton. Top Things to Do in Reston. Best Family-Friendly Activities in Reston.
- [Vulnerability Summary for the Week of November 4, 2024 | CISA](https://www.cisa.gov/news-events/bulletins/sb24-317) — The CISA Vulnerability Bulletin provides a summary of new vulnerabilities that have been recorded in the past week. In some cases, the vulnerabilities in the bulletin may not yet have assigned CVSS scores. Vulnerabilities are based on the Common Vulnerabilities and Exposures (CVE) vulnerability naming standard and are organized according to severity, determined by the Common Vulnerability Scoring System (CVSS) standard. * **High**: vulnerabilities with a CVSS base score of 7.0–10.0. * **Medium**: vulnerabilities with a CVSS base score of 4.0–6.9. * **Low**: vulnerabilities with a CVSS base score of 0.0–3.9. This issue affects some unknown processing of the file /admin/admin-profile.php. The manipulation of the argument adminname leads to sql injection. Affected by this vulnerability is an unknown functionality of the file /contact\_process.php. The manipulation of the argument fnm leads to sql injection. Affected by this issue is some unknown functionality of the file /admin/login\_process.php of the component Login.
- [Demonstrating the Mender Troubleshoot Add-on](https://mender.io/resources/videos/mender-troubleshoot-add-on-use-case) — # Demonstrating the Mender Troubleshoot Add-on. Mender 2.7 sees the release of the Troubleshoot Add-on. We demonstrate it using an example use case. With the Troubleshoot Add-on, you can resolve issues with your devices in real-time, all securely and efficiently. Read about the Add-on package which you can add to your Mender plan here, and see it in action in the video below:. ### Related resources. Some similar resources you may also be interested in. ## Mender: General Solution Overview. Mender offers robust, secure, and customizable OTA updates for field devices with its open-source client and server solution. How to get started with Mender Gateway. Learn how to use Mender Gateway to connect devices running in a segregated or isolated network to a Mender Server. Connected medical and diagnostics devices, OTA software updates & device management. For medical IoT devices, manufacturers can use OTA updates and remote access for feature enhancements, remote support, and security.