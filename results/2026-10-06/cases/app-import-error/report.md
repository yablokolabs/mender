# Root cause: checkout pod CrashLoopBackOff due to misplaced __future__ import in service.py

Service `checkout` in namespace `shop`.

## Root cause
Python SyntaxError: 'from __future__ import annotations' appears after a docstring and an import statement in service.py, violating the rule that __future__ imports must be at the very beginning of the file [1].

## Mechanism
1. The failing pod (checkout-86d87b9fd5-7bgxc) pulls image digest 4132451ca440... which contains the broken service.py. 2. On container start, Python parses service.py and immediately raises 'SyntaxError: from __future__ imports must occur at the beginning of the file' (see logs). 3. The container exits with code 1. 4. Kubernetes' default restartPolicy (Always) triggers a restart with exponential backoff, producing the CrashLoopBackOff status [7]. 5. The two healthy pods run a newer image digest (4c1ea44931b8...) where the import has been fixed, so they stay Running.

Confidence: 0.95 · Labels: syntax_error, late_future_import, crashloopbackoff, image_version_mismatch

## Evidence relied on
- File "/app/service.py", line 10\n    from __future__ import annotations\n    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nSyntaxError: from __future__ imports must occur at the beginning of the file
- service.py shows: 'import kubernetes_asyncio\n"""Checkout demo service...\n"""\nfrom __future__ import annotations' — import precedes the __future__ statement
- [1] Ruff rule late-future-import (F404): '__future__ imports must be placed the beginning of the file, before any other statements (apart from docstrings)'

## Tavily sources
Queries: Python SyntaxError "from __future__ imports must occur at the beginning of the file" Kubernetes container crash loop; Kubernetes CrashLoopBackOff Python syntax error container startup failure; containerd Kubernetes pod restart loop exit code 1 Python import error
- [late-future-import (F404) | Ruff](https://docs.astral.sh/ruff/rules/late-future-import) — Skip to content

# late-future-import (F404)

Added in v0.0.34 · Related issues) · View source

Derived from the Pyflakes linter.

## What it does

Checks for `__future__` imports that are not located at the beginning of a file.

## Why is this bad?

Imports from `__future__` must be placed the beginning of the file, before any other statements (apart from docstrings). The use of `__future__` imports elsewhere is invalid and will result in a `SyntaxError`.

## Example

```
 from  pathlib  import Path from  __future__  import annotations
```

Use instead:

```
 from  __future__  import annotations from  pathlib  import Path
```

## References

 Python documentation: Future statements
- [[Python] SyntaxError: from __future__ imports must occur at the beginning of the file · Issue #4600 · microsoft/kiota · GitHub](https://github.com/microsoft/kiota/issues/4600) — ``` [...] ``` [...] ```
- [`SyntaxError: from __future__ imports must occur ...](https://github.com/koxudaxi/datamodel-code-generator/issues/2079) — SyntaxError: from __future__ imports must occur at the beginning of the file when custom header is used #2079. New issue.
- ["SyntaxError: from __future__ imports must occur at the beginning of the file" after comments · Issue #385 · agronholm/typeguard · GitHub](https://github.com/agronholm/typeguard/issues/385) — _call_with_frames_removed( ^^^^^^^^^^^^^^^^^^^^^^^^^^ File "C:\Python311\Lib\site-packages\typeguard\_importhook.py", line 47, in _call_with_frames_removed return f(args, kwargs) ^^^^^^^^^^^^^^^^^^ File "C:\Temp\A.py", line 4 from __future__ import annotations ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ SyntaxError: from __future__ imports must occur at the beginning of the file [...] Traceback (most recent call last): File "C:\Temp\test.py", line 4, in  import_module('A') File "C:\Python311\Lib\importlib\__init__.py", line 126, in import_module return _bootstrap._gcd_import(name[level:], package, level) ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ File "", line 1206, in _gcd_import File "", line 1178, in _find_and_load File "", line 1149, in _find_and_load_unlocked File "", line 690, in _load_unlocked File "C:\Python311\Lib\site-packages\typeguard\_importhook.py", line 98, in exec_module super().exec_module(module) File "", line 936, in exec_module File "", line 1074, in get_code File "C:\Python311\Lib\site-packages\typeguard\_importhook.py", line 87, in source_to_code return _call_with_frames_removed( ^^^^^^^^^^^^^^^^^^^^^^^^^^ File [...] #273lovasoa/marshmallow\_dataclass#273

Closed

"SyntaxError: from \_\_future\_\_ imports must occur at the beginning of the file" after comments#385

lovasoa/marshmallow\_dataclass

#273

Copy link

Labels

bug

## Description

@jolaf

jolaf

opened on Aug 25, 2023

Issue body actions

### Things to check first

 I have searched the existing issues and didn't find my bug already reported there
 I have checked that my bug is still present in the latest release

### Typeguard version

4.1.2

### Python version

3.11.2

### What happened?
- [from __future__ imports must occur at the beginning of the file](https://github.com/maxpumperla/hyperas/issues/157) — The problem arose when I imported future packages to the same file as where the Hyperas package is imported. I solved it by moving all functions that were dependent on the future packages to a different file and imported them. Did you have any future packages in your code when using Python 3.6?
- [What is Kubernetes CrashLoopBackOff? And how to fix it | Sysdig](https://www.sysdig.com/blog/debug-kubernetes-crashloopbackoff) — Kubernetes will wait an increasing back-off time between restarts to give you a chance to fix the error. As such, CrashLoopBackOff is not an error on itself, but indicates that there’s an error happening that prevents a Pod from starting properly.

Note that the reason why it’s restarting is because its `restartPolicy` is set to `Always`(by default) or `OnFailure`. The kubelet is then reading this configuration and restarting the containers in the Pod and causing the loop. This behavior is actually useful, since this provides some time for missing resources to finish loading, as well as for us to detect the problem and debug it – more on that later. [...] ```
- alert: RestartsAlert - alert: RestartsAlert  expr: rate(kube_pod_container_status_restarts_total[5m]) > 0  expr: rate(kube_pod_container_status_restarts_total[5m]) > 0   for: 10m  for: 10m  labels:  labels:  severity: warning  annotations:  annotations:  summary: Pod is being restarted  description: Pod {{ $labels.pod }} in {{ $labels.namespace }} has a container {{ $labels.container }} which is being restarted  description: Pod {{ $labels.pod }} in {{ $labels.namespace }} has a container {{ $labels.container }} which is being restarted
```

## Conclusion

In this article, we have seen how CrashLoopBackOff isn’t an error by itself, but just a notification of the retrial loop that is happening in the pod.
- [Kubernetes CrashLoopBackOff Error: Common Causes & Solutions · Dash0](https://www.dash0.com/guides/kubernetes-crashloopbackoff) — Dash0 acquires Polar Signals

Dash0 Logo

Sign inBook a demo

Start Free Trial

Last updated:March 23, 2026

# Kubernetes CrashLoopBackOff Error: Common Causes & Solutions

## What Is Kubernetes CrashLoopBackOff?

The CrashLoopBackOff error in Kubernetes is a common issue that occurs when a container in a pod repeatedly crashes and fails to start up again. When a container fails, Kubernetes automatically restarts it, but if it continues to fail, Kubernetes will attempt to restart it again with an exponential backoff delay. The backoff delay starts at a small value and increases exponentially with each successive failure. Kubernetes eventually gives up and enters the CrashLoopBackOff state. [...] Lack of resources: If a pod doesn't have enough resources like memory or CPU, it may cause the containers to crash repeatedly. This can happen when the application is resource-intensive or when the resource requests and limits are not configured correctly.
 Terminating a pod immediately upon startup: If a pod is terminated immediately upon startup, it can cause a CrashLoopBackOff error. This can happen if the container fails to start correctly or if there is a misconfiguration in the application or Kubernetes configuration.
 Missing dependencies: If an application requires specific dependencies that are not present in the container image or are not installed correctly, the application may repeatedly fail to start up, resulting in a CrashLoopBackOff error. [...] Misconfigured liveness probes: Liveness probes are used to determine if a container is still running correctly. If a liveness probe is misconfigured or fails, Kubernetes may repeatedly restart the container, resulting in a CrashLoopBackOff error.
- [Kubernetes CrashLoopBackOff Errors: 6 Causes and Fixes | OpManager Nexus](https://www.manageengine.com/it-operations-management/tech-topics/kubernetes-crashloopbackoff-errors.html) — ## What is Kubernetes CrashLoopBackOff?

CrashLoopBackOff is a Kubernetes state that indicates a container is repeatedly failing to start, and Kubernetes is delaying its restart attempts.

When a container exits with an error, the kubelet restarts it. If the failure continues, Kubernetes applies an exponential backoff between restarts, starting at 10 seconds and doubling with each failure, up to a maximum of five minutes. This is the "backoff" reflected in the pod status.

The important distinction is that CrashLoopBackOff is not the root cause of the issue. It's a signal. Something in your application, configuration, or runtime environment is consistently failing, and Kubernetes is preventing an aggressive restart loop.

## How to diagnose CrashLoopBackOff quickly [...] ImagePullBackOff means Kubernetes cannot pull the container image — either the image name or tag is wrong, the registry is unreachable, or credentials are missing. The container never starts. CrashLoopBackOff means the image pulled successfully but the container fails after starting. If you see `ErrImagePull` or `ImagePullBackOff` in pod events, the issue is upstream of the application entirely and requires fixing the image reference or registry access, not the application configuration.

## Six common CrashLoopBackOff causes and how to fix them

### 1. Resource limits set too low (OOMKilled)

Memory exhaustion is one of the most frequent causes of CrashLoopBackOff in production clusters. [...] Exit codes 0 and 143 are the most commonly misread. A clean exit (0) in a CrashLoopBackOff loop almost always means the container ran, completed, and exited — pointing to a wrong entry point or a short-lived job being run as a long-running service. Exit code 143 means Kubernetes sent SIGTERM but the container didn't respond within the termination grace period.

## Why CrashLoopBackOff happens

Kubernetes is designed to maintain the desired state of your workloads. When a container fails, it assumes the failure is temporary and attempts to recover by restarting it.
- [Understanding Kubernetes CrashLoopBackOff & How to Fix It](https://www.groundcover.com/kubernetes-troubleshooting/crashloopbackoff) — ## What is Kubernetes CrashLoopBackOff?

A CrashLoopBackOff error is a condition where containers inside a Kubernetes Pod restart and subsequently crash in a never-ending loop. When this happens, Kubernetes will begin introducing a delay – known as a backoff period – between restarts, in an effort to give admins time to correct whichever issue is triggering the recurring crashes. It also typically generates an error message that mentions "back off restarting failed container."

So, although CrashLoopBackOff may sound like a nonsensical term, it actually makes sense when you think about it: It refers to a state where your containers are in a loop of repeated crashes, with backoff periods introduced between the crashes.

## Causes of CrashLoopBackOff/kubernetes-troubleshooting/dns-issues [...] In short, basically any condition that could cause containers to crash right after they start has the potential to create a CrashLoopBackOff. If the containers repeatedly try to restart and repeatedly fail, you get this error.

## What does a CrashLoopBackOff error look like in Kubernetes?

No red light starts flashing on your Kubernetes console when a CrashLoopBackOff event occurs. Kubernetes doesn't explicitly warn you about the issue.

But you can figure out that it's happening by checking on the state of your Pods with a command like:

```
kubectl get pods -n demo-ng
```

(demo-ng is the namespace we’ll be targeting in this guide. As the name suggests, it’s a demo setup).

If you see results like the following, you'll know you have a CrashLoopBackOff issue: [...] ### 9. Implement robust error handling

Robust error handling provides clear feedback when a bug prevents an application from starting properly. Implementing robust error handling requires writing application logic that generates exceptions when the normal flow of the application is disrupted.

Implementing error handling can be a lot of work, since it involves updating application code. But if you've done everything else to prevent CrashLoopBackOffs and are still running into issues, changing the code is a good final step to try.

## Back off, CrashLoopBackOffs

In a perfect world, your containers and Pods would start perfectly every time.
- [Kubernetes Most Occurred Issue | CrashLoopBackOff](https://aws.plainenglish.io/kubernetes-most-occurred-issue-crashloopbackoff-cc107a48d0c0) — Containers may fail to start if invalid command-line arguments are passed at runtime. Example: Providing a path to a non-existent config file
- [⎈ A Hands-On Guide to Kubernetes Exit Codes: Simulate and Fix ⚙️ | by Anvesh Muppeda | Medium](https://medium.com/@muppedaanvesh/a-hands-on-guide-to-kubernetes-exit-codes-simulate-and-fix-%EF%B8%8F-f2ad57d3cdca) — 3. Expected Outcome: When you apply this configuration, the Pod will terminate with Exit Code 1 due to the division by zero error in the Python code. You can check the logs with:

```
kubectl logs exit-code-1-simulation code 1
```

The output will indicate the error:

```
Starting application...Traceback (most recent call last):  File "<string>", line 1, in <module>ZeroDivisionError: division by zero call"<string>" 1 in moduleZeroDivisionError: by
```

### Fixing Exit Code 1

To resolve the Exit Code 1 error, you should ensure the application logic is correct and does not attempt to divide by zero.

1. Updated Pod Configuration: Here’s an updated configuration that ensures the command will execute successfully without causing an error.

File Name: `exit-code-1-fix.yaml` Configuration: [...] Common causes for Exit Code 1 include:

 Application Errors: Errors in the application logic, such as unhandled exceptions or logical errors (e.g., division by zero).
 Invalid Command: If the command specified in the Pod configuration fails or points to a non-existent file or directory.
 Misconfigured Environment: Missing or incorrectly set environment variables that the application requires.

### Simulation of Exit Code 1

1. Pod Configuration: We will create a Kubernetes Pod that runs a Python command that will intentionally fail due to a division by zero.
2. File Name: `exit-code-1-simulation.yaml` Configuration: [...] File Name: `exit-code-1-fix.yaml` Configuration:

```
apiVersion: v1kind: Podmetadata:  name: exit-code-1-fixspec:  containers:  - name: exit-code-1-app    image: python:alpine3.20  # Use a lightweight Python image    command: ["python", "-c", "print('Starting application...'); result = 1"]  # Fixed command with no error  restartPolicy: OnFailureapiVersion: v1kind: Podmetadata:name:exit-code-1-fixspec:containers: -name:exit-code-1-appimage:python:alpine3.20
# Use a lightweight Python imagecommand: "python""-c""print('Starting application...'); result = 1"
# Fixed command with no errorrestartPolicy: OnFailure
```

2. Deploy the Fix: To deploy the fixed configuration, run the following command:

```
kubectl apply -f exit-code-1-fix.yaml code 1.yaml
```
- [Kubernetes Exit Code 1 (SIGTERM): Causes and Troubleshooting · Dash0](https://www.dash0.com/guides/kubernetes-exit-code-1-sigterm-causes-and-troubleshooting) — Diagnosing and resolving Exit Code 1 errors requires a thorough check of the container’s environment, application logs, and Kubernetes pod states. To identify the root cause and resolve the issue, it is essential to explore various potential issues, such as configuration errors and resource constraints, as the cause cannot be pinpointed.

## Common Scenarios Leading to Exit Code 1 in Kubernetes

An Exit Code 1 error may occur in the following situations.

### Container Configuration Issues

Mistakes like wrong image names, incorrect or missing environment variables, or improperly configured volumes can prevent a container from starting, leading to this error. [...] Dash0 acquires Polar Signals

Dash0 Logo

Sign inBook a demo

Start Free Trial

Last updated:February 24, 2026

# Kubernetes Exit Code 1 (SIGTERM): Causes and Troubleshooting

## What Is the Exit Code 1 Error?

Exit Code 1 is an operating system signal that indicates an application terminated with an error. In Kubernetes, it typically indicates that a container in a pod failed to run correctly, terminating with an error. This generic exit code signifies an unspecified error within the application or the container’s environment. It doesn’t point to a specific issue, making it a common but challenging problem to diagnose in Kubernetes environments. [...] #### Troubleshooting example

Suppose you run `kubectl describe pod` and receive an output that includes the following:

yaml

```

12345678910111213

Containers:

my-container:

...

Limits:

cpu: 500m

memory: 256Mi

Requests:

cpu: 250m

memory: 128Mi

...

Last State: Terminated

Reason: OOMKilled

Exit Code: 1

```

This output indicates that the container my-container was killed because it exceeded its memory limit (OOMKilled stands for Out-Of-Memory Killed).

In this case, the root cause of the Exit Code 1 error is insufficient memory allocation. To resolve this issue, you would need to adjust the memory limits upwards, based on the application’s needs and previous usage patterns observed through monitoring tools.

## Best Practices to Deal with Exit Code 1 Error
- [Kubernetes Terminated with exit code 1 error | Refine](https://refine.dev/blog/kubernetes-terminated-with-exit-code-1) — Failed Health Checks: Kubernetes can terminate a container that fails its liveness or readiness checks repeatedly. While this often leads to restarts rather than a direct exit code 1, it can contribute to a situation where the container is unable to stay running.

Dependency Issues Inside Containers: If your containerized application has dependencies that are not met (e.g., missing libraries, inaccessible external services), this can cause the application to exit with code

Resource Limit Constraints: Containers in Kubernetes have resource limits, and exceeding these can lead to termination. However, this usually results in an `OOMKilled` error rather than an exit code 1, unless your application is explicitly designed to handle such scenarios with a custom exit code. [...] Expert tip: A container exiting multiple times with a non-zero exit code, such as `exit code 1`, can lead to a `CrashLoopBackOff` state in Kubernetes. If you look at the below error logs, you can see `CrashLoopBackOff` which was caused because the container exited many times with exit code 1.

kubectl describe pod output showing CrashLoopBackOff eventskubectl describe pod output showing CrashLoopBackOff events

### Verifying Container and Application Configurations​

Sometimes incorrect container or application configuration causes the error. Check your Kubernetes manifests and application configuration files. You can use the below command to see the details of your Kubernetes deployment: [...] Refine/Blog

All posts

10 min read

# Kubernetes Terminated with exit code 1 error

EngineeringMuhammad Khabbab

Share on:

Kubernetes Terminated with exit code 1 error

RefineRefine

## Introduction​

Getting an "Exit Code 1" error in Kubernetes is common and can be frustrating for developers. If you see this error, it means that something is wrong with your containerized application. In this article, we will get into the details of this error, look at some of the most common scenarios that cause it, and then give you a step-by-step plan for fixing it.

Also, we will share with you some of the best practices to ensure that you identify and resolve this error swiftly. But first, let's start with understanding what exactly is an exit code and what is the significance of exit code 1.
- [Pod In CrashLoopBackOff State – Runbooks](https://containersolutions.github.io/runbooks/posts/kubernetes/crashloopbackoff) — 3.1) Exit Code 1. The container failed to run its command successfully, and returned an exit code of 1. This is an application failure within the process that
- [Kubernetes CrashLoopBackOff: Causes & Quick Fixes | Netdata](https://www.netdata.cloud/academy/kubernetes-crash-loop-backoff) — Exit Code 0: The container exited successfully. If it keeps restarting, it might be a short-lived job that isn’t configured correctly for a deployment that expects a long-running process.
 Exit Code 1: General application error. This is a catch-all for unhandled exceptions or generic failures within your application. This is your cue to check the application logs.
 Exit Code 137 (128 + 9): The container was terminated by a `SIGKILL` signal. In Kubernetes, this almost always means the container exceeded its memory limit, triggering the OOM (Out-of-Memory) Killer. The `describe` output might explicitly state the reason as `OOMKilled`.