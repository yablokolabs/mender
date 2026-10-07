# Root cause: Checkout pod crash loop due to invalid log_level in ConfigMap

Service `checkout` in namespace `shop`.

## Root cause
The ConfigMap 'checkout-config' contains a malformed log_level value '[unclosed' in its config.yaml key, which is not in the application's allowed log levels (debug, info, warn, error).

## Mechanism
1. The ConfigMap 'checkout-config' stores config.yaml with content 'log_level: [unclosed' [1]. 2. Pods mount this as /etc/app/config.yaml. 3. On startup, the application loads and parses this config via parse_config(), which validates log_level against ALLOWED_LOG_LEVELS [2]. 4. Validation fails because '[unclosed' is not allowed, raising ConfigError. 5. main() catches ConfigError, logs 'FATAL: invalid log_level: [unclosed' and exits with code 1 [3]. 6. Container terminates with Reason: Error, Exit Code: 1 [4]. 7. Kubernetes restarts the container with exponential backoff (BackOff event) [5], creating a crash loop. 8. Readiness/liveness probes never succeed because the container never stays running [6].

Confidence: 0.95 · Labels: configmap_error, invalid_yaml, probe_config, crash_loop, exit_code_1

## Evidence relied on
- FATAL: invalid log_level: [unclosed
- Last State: Terminated Reason: Error Exit Code: 1
- config.yaml: | log_level: [unclosed
- ALLOWED_LOG_LEVELS = {"debug", "info", "warn", "error"}
- raise ConfigError(f"invalid log_level: {config['log_level']}")
- Back-off restarting failed container

## Tavily sources
Queries: Kubernetes ConfigMap malformed YAML config.yaml log_level unclosed bracket causes pod crash exit code 1; mender-demo-app config validation ConfigError invalid log_level parsing failure documented issues; Kubernetes deployment ConfigMap mount application startup failure due to invalid YAML syntax
- [⎈ A Hands-On Guide to Kubernetes Exit Codes: Simulate and Fix ⚙️ | by Anvesh Muppeda | Medium](https://medium.com/@muppedaanvesh/a-hands-on-guide-to-kubernetes-exit-codes-simulate-and-fix-%EF%B8%8F-f2ad57d3cdca) — Common causes for Exit Code 1 include:

 Application Errors: Errors in the application logic, such as unhandled exceptions or logical errors (e.g., division by zero).
 Invalid Command: If the command specified in the Pod configuration fails or points to a non-existent file or directory.
 Misconfigured Environment: Missing or incorrectly set environment variables that the application requires.

### Simulation of Exit Code 1

1. Pod Configuration: We will create a Kubernetes Pod that runs a Python command that will intentionally fail due to a division by zero.
2. File Name: `exit-code-1-simulation.yaml` Configuration: [...] 3. Expected Outcome: When you apply this configuration, the Pod will terminate with Exit Code 1 due to the division by zero error in the Python code. You can check the logs with:

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

File Name: `exit-code-1-fix.yaml` Configuration: [...] ```
kubectl apply -f exit-code-1-fix.yaml code 1.yaml
```

3. Expected Outcome: With this configuration, when you apply it and check the logs, you will see the successful execution of the command:

```
kubectl logs exit-code-1-fix code 1
```

The output will be:

```
Starting application... Starting
```

### How to Prevent Exit Code 1 in the Future

To avoid encountering Exit Code 1 in future deployments, consider the following best practices:
- [Kubernetes Exit Code 1 (SIGTERM): Causes and Troubleshooting · Dash0](https://www.dash0.com/guides/kubernetes-exit-code-1-sigterm-causes-and-troubleshooting) — Diagnosing and resolving Exit Code 1 errors requires a thorough check of the container’s environment, application logs, and Kubernetes pod states. To identify the root cause and resolve the issue, it is essential to explore various potential issues, such as configuration errors and resource constraints, as the cause cannot be pinpointed.

## Common Scenarios Leading to Exit Code 1 in Kubernetes

An Exit Code 1 error may occur in the following situations.

### Container Configuration Issues

Mistakes like wrong image names, incorrect or missing environment variables, or improperly configured volumes can prevent a container from starting, leading to this error. [...] To prevent these issues, it’s essential to verify container configurations before deployment thoroughly. Using tools like Kubernetes linter can automate identifying misconfigurations, ensuring containers are correctly set up to run in the Kubernetes environment.

### Failed Health Checks

Kubernetes uses liveness and readiness probes to check the health of containers. If these checks fail, Kubernetes may restart the container, resulting in Exit Code 1. The failure could stem from application errors or issues like incorrect probe paths or timings.

Ensuring health checks are accurately configured and correspond to the application’s requirements is crucial. Proper configuration helps Kubernetes manage container health effectively, reducing instances of unexpected terminations. [...] yaml

```

123

env:

- name: DATABASE_URL

value: "

```

If the application logs or errors point towards a database connection issue, it is important to verify the environment variable `DATABASE_URL`. If the application can’t find or connect to the required database due to a missing or incorrect environment variable, this will lead to an Exit Code 1 error.

### Check Container Resources

Insufficient or misallocated resources can cause containers to exit unexpectedly. Use `kubectl describe pod`  to review the pod’s resource allocations and utilization.

If resource limits are too low, consider increasing them based on the application’s needs. Monitoring tools can help track resource usage over time, guiding appropriate adjustments to prevent similar issues.
- [Debug a Pod in CrashLoopBackOff: Causes, Diagnosis and Solutions | SFEIR Institute](https://institute.sfeir.com/en/kubernetes-training/debug-pod-crashloopbackoff-causes-solutions-kubernetes) — ### Cause 1: Application error

The application itself crashes at startup. Check the exit code:

```
kubectl describe pod my-app | grep "Exit Code" 
```

| Exit Code | Meaning |
 --- |
| 0 | Success (but if the container should run, problem) |
| 1 | General application error |
| 137 | SIGKILL (likely OOMKilled) |
| 139 | SIGSEGV (segmentation fault) |
| 143 | SIGTERM (requested stop) |

Solution: Fix the application code or startup configuration.

### Cause 2: Missing configuration

ConfigMaps or Secrets not mounted correctly:

```
# Check mounts kubectl describe pod my-app | grep -A 10 "Mounts" # Check ConfigMaps existence kubectl get configmap my-config 
``` [...] ### Method 3: Copy files from container

```
# Copy internal logs kubectl cp my-app:/var/log/app.log ./app.log # Copy configuration kubectl cp my-app:/app/config.yaml ./config.yaml 
```

## CrashLoopBackOff Diagnostic Checklist

| Check | Command | Action if problem |
 --- 
| Container logs | `kubectl logs --previous` | Fix application error |
| Pod events | `kubectl describe pod` | Identify cause |
| Exit code | `grep "Exit Code"` | See code table |
| Memory | `grep "OOMKilled"` | Increase limits.memory |
| ConfigMaps | `kubectl get cm` | Create missing ConfigMaps |
| Secrets | `kubectl get secret` | Create missing Secrets |
| Image | `kubectl get pod -o yaml` | Verify image tag |
| Permissions | `securityContext` | Adjust runAsUser | [...] ```
# ❌ Reference to non-existent ConfigMap envFrom: - configMapRef: name: missing-config # ✅ Verify ConfigMap exists kubectl create configmap my-config --from-literal=KEY=value 
```

### Cause 3: OOMKilled (insufficient memory)

```
# Check the reason for last stop kubectl describe pod my-app | grep -A 5 "Last State" 
```

```
Last State: Terminated Reason: OOMKilled Exit Code: 137 
```

Solution: Increase memory limits or optimize the application.

```
resources: requests: memory: "256Mi" limits: memory: "512Mi" # Increase if necessary 
```

### Cause 4: Incorrect startup command

```
# ❌ Invalid command command: ["./start.sh"] # File not executable or missing # ✅ Verify existence and permissions command: ["/bin/sh", "-c", "chmod +x /app/start.sh && /app/start.sh"] 
```
- [Kubernetes CrashLoopBackOff: Finding Missing ConfigMaps](https://www.youtube.com/watch?v=Hlk6mUiURxo&xstg=CAMSBhUD_LL2Hw%3D%3D) — *Exit Code 0:* Successful execution. *Exit Code 1:* Application error, missing configuration, or unhandled exception. *Exit Code 137
- [Kubernetes ConfigMap配置导致Pod崩溃问题咨询](https://www.volcengine.com/article/799748) — Here's the corrected, working pod configuration: ... Without this full setup, the pod can't locate or mount the ConfigMap, which will immediately cause the container to fail on startup. 2. Validate Nginx Configuration Syntax First, confirm your site.conf has valid Nginx syntax—invalid config will crash the container instantly. Run this
- [Mender client testing on solidrun with Mender demo server - General Discussions - Mender Hub](https://hub.mender.io/t/mender-client-testing-on-solidrun-with-mender-demo-server/505) — `{
"InventoryPollIntervalSeconds": 1800,
"RetryPollIntervalSeconds": 300,
"RootfsPartA": "/dev/mmcblk0p2",
"RootfsPartB": "/dev/mmcblk0p3",
"ServerCertificate": "/etc/mender/leshan.crt",
"ServerURL": "
"TenantToken": "dummy",
"UpdatePollIntervalSeconds": 1800
}`
`root@solidrun-imx6:~# ls -lrt /etc/mender/
total 16
-rw-r--r-- 1 root root 24 Mar 18 10:11 artifact_info
-rw-r--r-- 1 root root 312 Apr 26 06:41 mender.conf
drwxr-xr-x 2 root root 4096 Apr 26 06:47 scripts
-rw-r--r-- 1 root root 2057 Apr 26 09:29 leshan.crt`
`cat /etc/hosts
127.0.0.1 localhost.localdomain localhost
10.42.0.1 leshan.com`

Edit: @mirzak: Prettified logs

Hi @ramu,

You seem to be mixing “demo environment” settings and with "production environment. [...] `root@solidrun-imx6:~# cat /var/log/kern.log | grep mender
Apr 26 09:32:26 solidrun-imx6 mender: level=info msg="Configuration file does not exist: /var/lib/mender/mender.conf" module=config
Apr 26 09:32:26 solidrun-imx6 mender: level=info msg="Loaded configuration file: /etc/mender/mender.conf" module=config
Apr 26 09:32:26 solidrun-imx6 mender: level=info msg="Mender running on partition: /dev/mmcblk0p2" module=main [...] To better understand what you are trying to do, can please confirm which server instance are you using,

or

I used mender server from  and tested mender client on raspbery board using readily available images from mender site…

Then now, I am using the same above demo server which is running on my laptop ( Created certificate with CN=leshan.com ) for mender client running on my solidrun board. I have made the above said changes like server name, certificate, ip address etc for in my yocto build for my device…

MENDER\_DEMO\_HOST\_IP\_ADDRESS = “10.42.0.223”

Above is all you need for the demo environment in your Yocto configuration.

You can remove this,

`MENDER_SERVER_URL = "
FILESEXTRAPATHS_prepend_pn-mender := "/etc/apache2/ssl:"
SRC_URI_append_pn-mender = " file://leshan.crt"`
- [Mender Client | Mender documentation](https://docs.mender.io/troubleshoot/mender-client) — To solve this issue, install mender-artifact from the Mender APT repository following the instructions in the downloads section. The problem here is most
- [Mender | Embedded Artists Developer Site](https://developer.embeddedartists.com/docs-app/ota/ota-mender) — ```
DISTRO=fsl-imx-wayland MACHINE=imx8mmea-ucom source ea-setup-mender.sh -b build_dir DISTRO =fsl-imx-wayland MACHINE =imx8mmea-ucom source ea-setup-mender.sh -b  build_dir
```

### Configure Mender​

Mender is mostly configured via the `build_dir/conf/local.conf` file. This file has been prepared with default values that can be used to test and evaluate Mender. One thing that hasn’t been enabled is however which kind of Mender server to use. If you start evaluating with the demo server you then have to uncomment the `MENDER_DEMO_HOST_IP_ADDRESS` variable and set it to the IP address of the demo server. In the example below this variable has been set to `192.168.1.11`. See the Mender demo server section for more information about the demo server. [...] Official documentation about removing the demo layer:

Make sure the mender-client is re-built by removing any cached files.

```
$ bitbake -c cleansstate mender-client $ bitbake -c cleansstate mender-client
```

Now you can build a new image which will be configured to use a hosted server.

```
$ bitbake ea-image-base$ bitbake ea-image-base
```

## On-premise server​

It is also possible to host your own server. Requirements and instructions are available in the official documentation.

## Local update of the device​

It is possible to do local updates of the device, that is, updates where the server is not involved. This could, for example, be used if the device doesn’t have network connectivity. This is called standalone deployment.

## Sign and verify the artifact file​ [...] To be able to use a hosted server you need to do a couple of changes in the `build_dir/conf/local.conf` file.

1. If you have previously built for demo server you need to comment out / remove the `MENDER_DEMO_HOST_IP_ADDRESS` variable.
2. Uncomment `MENDER_SERVER_URL = "
3. Uncomment `MENDER_TENANT_TOKEN` and set it to the token you get from your Mender account. You get this by logging in to hosted.mender.io, click on your user-name (top-right) and then select My organization.

You also need to build for production which means that the demo layer in Yocto must be removed.

In your build directory (`build_dir`) run `bitbake-layers` remove as below.

```
bitbake-layers remove-layer meta-mender-demobitbake-layers remove-layer meta-mender-demo
```
- [Mender MCU | Mender documentation](https://docs.mender.io/troubleshoot/mender-mcu) — Mender MCU debugging tips and known limitations Developing embedded systems with OTA can be complex. This section provides some tips for debugging issues that may arise and notes a few known limitations or things to keep in mind when using Mender MCU with Zephyr. Debugging tips Enable debug logs: If you suspect something is wrong in the client's behavior, enable CONFIG_MENDER_LOG_LEVEL_DBG=y
- [GitHub - mendersoftware/mender-demo-artifact · GitHub](https://github.com/mendersoftware/mender-demo-artifact) — ## Contributing

We welcome and ask for your contribution. If you would like to contribute to Mender, please read our guide on how to best get started contributing code or documentation.

## License

Mender is licensed under the Apache License, Version 2.0. See LICENSE for the full license text.

## Security disclosure

We take security very seriously. If you come across any issue regarding security, please disclose the information by sending an email to security@mender.io. Please do not create a new public issue. We thank you in advance for your cooperation.

## Connect with us [...] ## History

740 Commits

740 Commits

## Folders and files

| Name | Name | Last commit message | Last commit date |
 ---  --- |
| onboarding-site | onboarding-site |  |  |
| state-scripts | state-scripts |  |  |
| tests | tests |  |  |
| .gitignore | .gitignore |  |  |
| .gitlab-ci.yml | .gitlab-ci.yml |  |  |
| .gitmodules | .gitmodules |  |  |
| CODEOWNERS | CODEOWNERS |  |  |
| Dockerfile | Dockerfile |  |  |
| README.md | README.md |  |  |
| renovate.json5 | renovate.json5 |  |  |
|  |

## Repository files navigation

# Mender Demo Artifact

Mender is an open source over-the-air (OTA) software updater for embedded Linux devices. Mender comprises a client running at the embedded device, as well as a server that manages deployments across many devices. [...] ## Connect with us

 Join the Mender Hub discussion forum
 Follow us on Twitter. Please feel free to tweet us questions.
 Fork us on Github
 Create an issue in the bugtracker
 Email us at contact@mender.io
 Connect to the #mender IRC channel on Libera

## About

No description, website, or topics provided.

### Resources

Readme

Custom properties

### Stars

0 stars

### Watchers

11 watching

### Forks

12 forks

Report repository

## Used by

You can’t perform that action at this time.
- [Error when adding ConfigMap data into deployment yaml - Regional Discussions - Discuss Kubernetes](https://discuss.kubernetes.io/t/error-when-adding-configmap-data-into-deployment-yaml/30885) — Yours is still messed up - please do look at the API docs. Pasting mine into a YAML-to-JSON converter shows I mistyped some whitespace, too. The below passes that test, but I didn’t try to run it.

`kind: Deployment
metadata:
name: httpd-deployment-datacenter
spec:
selector:
matchLabels:
app: httpd_app_datacenter
replicas: 4
template:
metadata:
labels:
app: httpd_app_datacenter
spec:
containers:
- name: httpd-container-datacenter
image: httpd:latest
ports:
- containerPort: 80
volumeMounts:
- name: httpd-configmap-datacenter
mountPath: /usr/share/nginx/html/
volumes:
- name: httpd-configmap-datacenter`

This one worked! Thank a bunch for all of your help. Just getting started in Kubernetes, day 2 actually. Will read up more. :slightly_smiling_face: :+1:

:slightly_smiling_face:
:+1: [...] `kind: Deployment
metadata:
name: httpd-deployment-datacenter
spec:
selector:
matchLabels:
app: httpd_app_datacenter
replicas: 4
template:
metadata:
labels:
app: httpd_app_datacenter
spec:
containers:
- name: httpd-container-datacenter
image: httpd:latest
ports:
- containerPort: 80
spec:
volumeMounts:
- name: httpd-configmap-datacenter
mountPath: /usr/share/nginx/html/
volumes:
- name: httpd-configmap-datacenter`

Yeah, you have `spec` under `spec` - this is just incorrect yaml. [...] apiVersion: apps/v1  
kind: Deployment  
metadata:  
name: httpd-deployment-datacenter  
spec:  
selector:  
matchLabels:  
app: httpd\_app\_datacenter  
replicas: 4  
template:  
metadata:  
labels:  
app: httpd\_app\_datacenter  
spec:  
containers:  
- name: httpd-container-datacenter  
image: httpd:latest  
ports:  
- containerPort: 80  
spec:  
volumeMounts:  
- name: httpd-configmap-datacenter  
mountPath: /usr/share/nginx/html/  
volumes:  
- name: httpd-configmap-datacenter

Please put your YAML in a code block (triple-backquotes) – nobody can make sense of it without whitespace.

Hi thockin, sorry, but not sure how to do this.
- [Kubernetes Errors With Solution - Always learning - Medium](https://ibrahims.medium.com/kubernetes-errors-with-solution-ab3f5643c2dd) — ❓Kubernetes configuration files contain syntax errors, making them invalid and unable to be applied. ▷ Validate the YAML syntax using tools
- [Kubernetes ConfigMap: What It Is & How to Use It · Dash0](https://www.dash0.com/knowledge/kubernetes-configmap-what-it-is-and-how-to-use-it) — A few things that aren't obvious until they've bitten you.

The 1 MiB limit is a hard ceiling, not a soft guideline. ConfigMaps are stored in etcd, and etcd caps request sizes at 1 MiB with no override flag. If you're pushing large files through a ConfigMap, use a volume or a dedicated config store instead. Even well below the limit, large ConfigMaps slow pod startup and add etcd load.

Everything is a string. ConfigMaps have no type system, so a value like `true` or `3` is text, and your application has to parse it. YAML's implicit typing makes this easy to miss: write `enabled: true` without quotes and the API server coerces it, but the container still receives the string `"true"`. Quote your values. [...] envFrom:

- configMapRef:

name: app-config

```

Every key becomes an environment variable of the same name. The catch: keys with dots in them, like `feature_flags.yaml`, aren't valid environment variable names, so they get silently skipped. The kubelet logs an event rather than failing the pod. If a value seems to be missing from the environment, this is the first thing to check.

### As files in a mounted volume

Mounting the ConfigMap as a volume projects each key as a file, with the key as the filename and the value as the file contents:

yaml

```

1234567891011

spec:

containers:

- name: app

image: my-app:latest

volumeMounts:

- name: config-volume

mountPath: /etc/app/config

volumes:

- name: config-volume

configMap:

name: app-config

``` [...] A missing key silently blocks pod startup. If a pod references a ConfigMap key that doesn't exist via `configMapKeyRef`, the pod won't start. It sits unready rather than crashing, which can be baffling when you're staring at an event stream waiting for a reason. Set `optional: true` on the reference if a missing value is acceptable. The same problem applies when referencing a ConfigMap that hasn't been created yet, and depending on how your app initializes, it can surface as a CrashLoopBackOff once it eventually starts.
- [Kubernetes ConfigMaps: Examples, Benefits & How to Use Them](https://www.groundcover.com/blog/kubernetes-configmap) — ## Kubernetes ConfigMap best practices

Consider the following best practices to get the most value from ConfigMaps.

### Test ConfigMaps before deployment

Errors in a ConfigMap, such as typos or broken indentation, could cause Kubernetes to fail to read the ConfigMap data properly. To mitigate this risk, consider testing ConfigMaps prior to deployment.

Kubernetes doesn’t offer a native way of testing ConfigMaps (other than applying them and checking whether they cause problems), but you can use external YAML linters, such as YAML Lint, to validate syntax.

### Version-control ConfigMaps
- [10 Kubernetes Errors you must know(and How to Fix Them)](https://www.perfectscale.io/blog/kubernetes-errors) — roleRef:

kind: ClusterRole

name: cluster-admin

apiGroup: rbac.authorization.k8s.io

```

4. Correct namespace in RoleBinding

If you’re operating in namespace prod, ensure your RoleBinding is in prod, not default and the Role belongs there.

## YAML Misconfiguration in Kubernetes

### What is a YAML misconfiguration in Kubernetes?

A YAML misconfiguration in Kubernetes refers to errors in your manifest files such as wrong indentation, incorrect types, invalid APIs, typos, or missing required fields, that lead to failed deployments, silent misbehavior, or unexpected pod failures.

### Why does YAML misconfiguration happen in Kubernetes?

Common causes of Kubernetes YAML misconfigurations include: [...] Invalid resource relationships: Broken reference between objects (e.g., Deployment referring to a ServiceAccount that doesn’t exist) causes failed or incomplete deployment

### Example of YAML misconfiguration in Kubernetes

```

apiVerion: apps/v1

kind: Deployment

metadata:

name: demo-app

spec:

replicas: "3"

template:

metadata:

labels:

app: demo

spec:

containers:

- image: nginx

name: nginx

ports:

- containerPort: "80"

```

In above configuration, replicas and containerPort are strings instead of integers and apiVersion is misspeled. In this case, Kubernetes reject the manifest.

### Troubleshooting Steps to Resolve Kubernetes YAML Misconfiguration

a. Investigate Kubernetes YAML errors

1. Dry-run validation

```

kubectl apply --dry-run=client -f manifest.yaml

``` [...] ```

kubectl apply --dry-run=client -f manifest.yaml

```

This flags schema and validation errors proactively.

2. Lint YAML files

Use tools like yamllint, kubeconform, or monokle to catch indentation issues, wrong types, missing fields, or typos before deploying.

3. Enable CI/CD manifest validation

Incorporate YAML validation in pipelines, kubectl apply --dry-run and kubeval, so errors stop the CI job rather than hitting Kubernetes clusters .

b. Fixing Kubernetes YAML misconfiguration

1. Correct types and formatting

Ensure integers for numeric fields:

```

replicas: 3

ports:

- containerPort: 80

```

2. Consistent indentation

Always use spaces (e.g. 2 or 4 spaces consistently). Avoid tabs. YAML parsers often can’t detect invisible tab errors .