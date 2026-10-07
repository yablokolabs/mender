# Root cause: checkout pod CreateContainerConfigError due to missing secret checkout-secrets-x

Service `checkout` in namespace `shop`.

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

## Tavily sources
Queries: Kubernetes CreateContainerConfigError secret not found secretKeyRef name mismatch; Pod Pending CreateContainerConfigError referenced secret does not exist troubleshooting; Kubernetes deployment secretKeyRef wrong secret name container startup failure
- [How to Fix CreateContainerConfigError from Misconfigured Secrets](https://oneuptime.com/blog/post/2026-02-09-createcontainerconfigerror-secrets/view) — For Secrets referenced in environment variables, verify the exact key names match.

```
apiVersion: v1 kind: Pod metadata: name: myapp spec: containers: - name: app image: myapp:v1.0 env: # This must match an actual key in the Secret - name: DB_PASSWORD valueFrom: secretKeyRef: name: app-secrets key: database-password # Must exist in Secret optional: false # Fail if missing (default behavior)
```

Check that the Secret contains the referenced key. [...] View container status for additional details.

```
kubectl get pod myapp-6f8d9c7b5-x4k2h -o jsonpath='{.status.containerStatuses.state.waiting}' | jq # Output: # { # "message": "secret \"app-secrets\" not found", # "reason": "CreateContainerConfigError" # }
```

## Fixing Missing Secret References

When pods reference Secrets that don't exist, create the Secret before the pod can start.

```
# Check if Secret exists kubectl get secret app-secrets -n default # If not found, check the pod specification for what's needed kubectl get pod myapp-6f8d9c7b5-x4k2h -o yaml | grep -A 10 secretRef # Create the missing Secret kubectl create secret generic app-secrets \ --from-literal=database-password=secretpass123 \ --from-literal=api-key=key_abc123xyz \ -n default
``` [...] ```
# Check for ConfigMap kubectl get configmap app-config -n default # View ConfigMap keys kubectl get configmap app-config -n default -o jsonpath='{.data}' | jq keys # Create missing ConfigMap kubectl create configmap app-config \ --from-literal=log-level=info \ --from-file=config.yaml=./config.yaml \ -n default
```

For environment variables from ConfigMaps, verify key names.

```
apiVersion: v1 kind: Pod metadata: name: myapp spec: containers: - name: app image: myapp:v1.0 env: - name: LOG_LEVEL valueFrom: configMapKeyRef: name: app-config key: log-level # Must match key in ConfigMap
```

When mounting ConfigMaps as volumes, ensure referenced ConfigMaps exist.
- [Fixing CreateContainerConfigError & CreateContainerError](https://spacelift.io/blog/createcontainerconfigerror) — ### Step 3: Fix the Configuration Issue

Now you can proceed to fix the issue. The action to take will depend on the specific cause of the `CreateContainerConfigError`:

#### 1. ConfigMap not found

This means a `configMapRef` or `configMapKeyRef` field in your Pod manifest references a ConfigMap that doesn’t exist in your cluster or namespace. To resolve the problem, create a new ConfigMap with the correct name, then reapply your Pod’s manifest.

#### 2. Secret not found

In the same way, the issue can also occur when you try to access a Secret that doesn’t exist. Solve the problem by first adding the Secret to your cluster, then recreating your Pod.

#### 3. Couldn’t find key in ConfigMap or secret [...] ### Common causes of CreateContainerConfigError

The common causes of `CreateContainerConfigError` include missing Kubernetes ConfigMaps and Secrets.

 Missing ConfigMap – Referencing a ConfigMap that doesn’t exist will cause this error to occur. The missing ConfigMap will prevent Kubernetes from assembling the configuration data to supply to the container. (Read more about Kubernetes ConfigMap.)
 Missing Secret – Similarly, the error will also occur when your container manifest references an invalid Secret.

### Checking for CreateContainerConfigError

You can easily check whether any of your Pods have experienced `CreateContainerConfigError` by checking the `STATUS` values reported by Kubectl’s `get pods` command:

```
$ kubectl get pods app 0/1 CreateContainerConfigError 0  10s
``` [...] #### 3. Couldn’t find key in ConfigMap or secret

Finally, you’ll also get a `CreateContainerConfigError` when you reference a specific key inside a ConfigMap or Kubernetes Secret, but that key doesn’t exist. For example, the following Pod manifest will cause the error if the `app-config` ConfigMap exists but is empty:

```
apiVersion:  v1  kind:  Pod  metadata:   name:  app  spec:   containers:   -  image:  nginx: latest  name:  app  env:   -  name:  TEST_KEY  valueFrom:   configMapKeyRef:   name:  app - config  key:  test_key
```

### Step 4: Reapply the Manifest
- [Kubernetes CreateContainerConfigError and CreateContainerError | Sysdig](https://www.sysdig.com/blog/kubernetes-createcontainerconfigerror-createcontainererror) — ### Not found Secret

Secrets are a more secure manner to store sensitive information in Kubernetes. Remember, though, this is just raw data encoded in base64, so it's not really encrypted, just obfuscated.

In case a Pod contains a reference to a non-existent secret, Kubelet will throw a CreateContainerConfigError, indicating that necessary data couldn't be retrieved in order to form container config.

### Container name already in use

While an unusual situation, in some cases a conflict might occur because a particular container name is already being used. Since every docker container should have a unique name, you will need to either delete the original or rename the new one being created.

## How to troubleshoot CreateContainerError and CreateContainerConfigError [...] 1. Pull the image.
2. Generate container configuration.
3. Precreate container.
4. Create container.
5. Pre-start container.
6. Start container.

As you can see, steps 2 and 4 are where a CreateContainerConfig and CreateContainerErorr might appear, respectively.

## Common causes for CreateContainerError and CreateContainerConfigError

### Not found ConfigMap

Kubernetes ConfigMaps are a key element to store non-confidential information to be used by Pods as key-value pairs.

When adding a ConfigMap reference in a Pod, you are effectively indicating that it should retrieve specific data from it. But, if a Pod references a non-existent ConfigMap, Kubernetes will return a CreateContainerConfigError.

### Not found Secret [...] Container command and arguments
 Relevant persistent volumes for the container
 Relevant ConfigMaps for the container
 Relevant secrets for the container

Any problem in the elements above will result in a CreateContainerConfigError.

## What is CreateContainerError?

Kubernetes throws a CreateContainerError when there's a problem in the creation of the container, but unrelated with configuration, like a referenced volume not being accessible or a container name already being used.

Similar to other problems like CrashLoopBackOff, this article only covers the most common causes, but there are many others depending on your current application.

## How you can detect CreateContainerConfigError and CreateContainerError

You can detect both errors by running kubectl get pods:
- [CreateContainerConfigError vs CreateContainerError in K8s](https://www.perfectscale.io/blog/createcontainerconfigerror) — metadata:

name: my-secret

type: Opaque

data:

password: cGFzc3dvcmQ= # Base64 encoded value of 'password'

```

Pod's Configuration Referencing the Secret:

```

apiVersion: v1

kind: Pod

metadata:

name: my-pod

spec:

containers:

- name: my-container

image:

env:

- name: DATABASE_PASSWORD

valueFrom:

secretKeyRef:

name: my-secret

key: password

```

The same error you get if you configure a container to use secrets that don't exist.

So make sure to set up the ConfigMaps and secrets before launching the pod and referencing them in Pod's configuration.

## Troubleshooting CreateContainerConfigError

To troubleshoot CreateContainerConfigError, start first looking at relevant logs and events to confirm it is an error due to a configuration mistake or missing something. [...] kind: Pod

metadata:

name: my-pod

spec:

containers:

- name: my-container

image:

volumeMounts:

- name: config-volume

mountPath: /etc/config

volumes:

- name: config-volume

configMap:

name: my-configmap

```

When creating a Pod, you have to reference the ConfigMap in your Pod's configuration. If that ConfigMap exists, the Pod can access it. But if not, you'll encounter the CreateContainerConfigError.

Missing Secrets

Secrets in Kubernetes are a way to securely store sensitive information that is used by applications running in a cluster.

Now, let's consider an example where a Pod is configured to use a Secret for storing sensitive information.

```

apiVersion: v1

kind: Secret

metadata:

name: my-secret

type: Opaque

data:
- [Fix CreateContainerConfigError & CreateContainerError](https://www.groundcover.com/kubernetes-troubleshooting/createcontainerconfigerror-createcontainererror) — ## Common Causes for CreateContainerConfigError

The most common cause for CreateContainerConfigError is a failure by Kubernetes to locate resources that are part of a container's configuration. Specifically, this event usually happens when Kubernetes can't locate either a ConfigMap or a secret.

| Cause | Description |
 --- |
| Missing ConfigMap | A ConfigMap referenced by the Pod's configuration does not exist or is not accessible to the Pod. |
| Missing secret | A secret referenced by the Pod's configuration does not exist or is not accessible to the Pod. |

### Missing ConfigMap [...] If you suspect this might be the issue, inspect the output of the following commands again, being sure to check that all of your Pod's ConfigMaps and secrets are properly configured:

## How to Fix CreateContainerConfigError

Once you’ve pinpointed the cause of a CreateContainerConfigError event, fixing it is usually easy enough: To resolve CreateContainerConfigError, create whichever ConfigMap or Secret your container configuration points to but which does not actually exist. After correcting a missing or inaccessible ConfigMap or Secret, you may also need to reapply the Pod manifest. Or, if the resource does exist but is not accessible to a Pod that needs it due to a misconfiguration, you can redeploy the resource with the proper settings. [...] For example, consider the following spec (which we've borrowed from the Kubernetes documentation):

This references values defined in a ConfigMap named game-demo. This is good and well if that ConfigMap exists and the Pod is able to access it. But if not, you’ll get a CreateContainerConfigError when Kubernetes attempts to start the Pod, so check that the ConfigMap exists before startup.

### Missing Secrets

The same error will result if you configure a container to use a secret, which Kubernetes uses to store sensitive information, and that secret doesn’t exist.

Like ConfigMaps, any secrets that you want a Pod to use must be set up before you launch the Pod, and Secrets are the standard way to securely store sensitive information for Pods. You can generate secrets using a command like:
- [Fix CreateContainerConfigError & CreateContainerError](https://www.groundcover.com/kubernetes-troubleshooting/createcontainerconfigerror-createcontainererror) — Then, you reference the secret when configuring a Pod. Here's an example (also borrowed from the Kubernetes documentation) that points to a secret named secret-dockercfg:

Here again, everything will be peachy so long as your secret exists. The Secret must also be correctly configured in the same namespace as the Pod. But if the secret does not exist or is not accessible to the Pod, you’ll encounter a CreateContainerConfigError event.

## How to Troubleshoot CreateContainerConfigError

When troubleshooting CreateContainerConfigError events, start by looking at relevant logs and events to confirm that a CreateContainerConfigError has indeed occurred. Then, compare your Pod configuration to your actual configuration to determine what triggered the error. [...] If you suspect this might be the issue, inspect the output of the following commands again, being sure to check that all of your Pod's ConfigMaps and secrets are properly configured:

## How to Fix CreateContainerConfigError

Once you’ve pinpointed the cause of a CreateContainerConfigError event, fixing it is usually easy enough: To resolve CreateContainerConfigError, create whichever ConfigMap or Secret your container configuration points to but which does not actually exist. After correcting a missing or inaccessible ConfigMap or Secret, you may also need to reapply the Pod manifest. Or, if the resource does exist but is not accessible to a Pod that needs it due to a misconfiguration, you can redeploy the resource with the proper settings. [...] Those commands list the ConfigMaps and secrets that are actually configured. Also confirm those resources exist in the same namespace as the Pod. If your Pod references any ConfigMaps or secrets that don’t appear when you ask kubectl to describe ConfigMaps and secrets, you’ve found the source of your CreateContainerConfigError.

### Step 4: Verify Permissions and Namespace Settings

You may sometimes encounter a CreateContainerConfigError even though all of the ConfigMaps and secrets referenced in a Pod's configuration exist. If this is the case, the problem is most likely that the resource in question is not accessible to the Pod due either to misconfigured permissions or because it's associated with a different namespace from the Pod.
- [CreateContainerConfigError vs CreateContainerError in K8s](https://www.perfectscale.io/blog/createcontainerconfigerror) — metadata:

name: my-secret

type: Opaque

data:

password: cGFzc3dvcmQ= # Base64 encoded value of 'password'

```

Pod's Configuration Referencing the Secret:

```

apiVersion: v1

kind: Pod

metadata:

name: my-pod

spec:

containers:

- name: my-container

image:

env:

- name: DATABASE_PASSWORD

valueFrom:

secretKeyRef:

name: my-secret

key: password

```

The same error you get if you configure a container to use secrets that don't exist.

So make sure to set up the ConfigMaps and secrets before launching the pod and referencing them in Pod's configuration.

## Troubleshooting CreateContainerConfigError

To troubleshoot CreateContainerConfigError, start first looking at relevant logs and events to confirm it is an error due to a configuration mistake or missing something. [...] ## FAQ

What's the difference between CreateContainerConfigError and CreateContainerError? `CreateContainerConfigError` happens earlier: Kubernetes can't assemble the container's configuration, usually because a referenced ConfigMap or Secret is missing. `CreateContainerError` happens after the config is ready, when the container runtime itself fails to create the container (bad image, resource limits, bad volume mounts, or a runtime issue).

Why are there no application logs for these errors? Both errors occur before the container actually starts, so the application inside it never runs and never produces logs. You have to rely on `kubectl describe pod` and `kubectl get events` instead. [...] Warning Failed 56s (x6 over 1m45s)

kubelet Error: configmap "my-configmap" not found

```

1. Verify Permissions and Namespace Settings: If all the resources are properly configured but still encounter CreateContainerConfigError, check the permissions and namespace settings. Ensure that the resources are accessible to the pod and are in the same namespace.

## Fixing CreateContainerConfigError

To resolve CreateContainerConfigError, follow these best practices:

1. Create Missing ConfigMaps and Secrets: If a referenced ConfigMap or Secret is missing, create it using the appropriate kubectl create command. Ensure that the resource is created in the same namespace as the pod.

```

~ kubectl create configmap my-configmap

kubectl create secret generic my-secret

```
- [Fixing CreateContainerConfigError & CreateContainerError](https://spacelift.io/blog/createcontainerconfigerror) — ### Step 3: Fix the Configuration Issue

Now you can proceed to fix the issue. The action to take will depend on the specific cause of the `CreateContainerConfigError`:

#### 1. ConfigMap not found

This means a `configMapRef` or `configMapKeyRef` field in your Pod manifest references a ConfigMap that doesn’t exist in your cluster or namespace. To resolve the problem, create a new ConfigMap with the correct name, then reapply your Pod’s manifest.

#### 2. Secret not found

In the same way, the issue can also occur when you try to access a Secret that doesn’t exist. Solve the problem by first adding the Secret to your cluster, then recreating your Pod.

#### 3. Couldn’t find key in ConfigMap or secret [...] ### Common causes of CreateContainerConfigError

The common causes of `CreateContainerConfigError` include missing Kubernetes ConfigMaps and Secrets.

 Missing ConfigMap – Referencing a ConfigMap that doesn’t exist will cause this error to occur. The missing ConfigMap will prevent Kubernetes from assembling the configuration data to supply to the container. (Read more about Kubernetes ConfigMap.)
 Missing Secret – Similarly, the error will also occur when your container manifest references an invalid Secret.

### Checking for CreateContainerConfigError

You can easily check whether any of your Pods have experienced `CreateContainerConfigError` by checking the `STATUS` values reported by Kubectl’s `get pods` command:

```
$ kubectl get pods app 0/1 CreateContainerConfigError 0  10s
``` [...] #### 3. Couldn’t find key in ConfigMap or secret

Finally, you’ll also get a `CreateContainerConfigError` when you reference a specific key inside a ConfigMap or Kubernetes Secret, but that key doesn’t exist. For example, the following Pod manifest will cause the error if the `app-config` ConfigMap exists but is empty:

```
apiVersion:  v1  kind:  Pod  metadata:   name:  app  spec:   containers:   -  image:  nginx: latest  name:  app  env:   -  name:  TEST_KEY  valueFrom:   configMapKeyRef:   name:  app - config  key:  test_key
```

### Step 4: Reapply the Manifest
- [Kubernetes CreateContainerConfigError and CreateContainerError | Sysdig](https://www.sysdig.com/blog/kubernetes-createcontainerconfigerror-createcontainererror) — ### Not found Secret

Secrets are a more secure manner to store sensitive information in Kubernetes. Remember, though, this is just raw data encoded in base64, so it's not really encrypted, just obfuscated.

In case a Pod contains a reference to a non-existent secret, Kubelet will throw a CreateContainerConfigError, indicating that necessary data couldn't be retrieved in order to form container config.

### Container name already in use

While an unusual situation, in some cases a conflict might occur because a particular container name is already being used. Since every docker container should have a unique name, you will need to either delete the original or rename the new one being created.

## How to troubleshoot CreateContainerError and CreateContainerConfigError [...] 1. Pull the image.
2. Generate container configuration.
3. Precreate container.
4. Create container.
5. Pre-start container.
6. Start container.

As you can see, steps 2 and 4 are where a CreateContainerConfig and CreateContainerErorr might appear, respectively.

## Common causes for CreateContainerError and CreateContainerConfigError

### Not found ConfigMap

Kubernetes ConfigMaps are a key element to store non-confidential information to be used by Pods as key-value pairs.

When adding a ConfigMap reference in a Pod, you are effectively indicating that it should retrieve specific data from it. But, if a Pod references a non-existent ConfigMap, Kubernetes will return a CreateContainerConfigError.

### Not found Secret
- [How to Fix CreateContainerConfigError from Misconfigured Secrets](https://oneuptime.com/blog/post/2026-02-09-createcontainerconfigerror-secrets/view) — View container status for additional details.

```
kubectl get pod myapp-6f8d9c7b5-x4k2h -o jsonpath='{.status.containerStatuses.state.waiting}' | jq # Output: # { # "message": "secret \"app-secrets\" not found", # "reason": "CreateContainerConfigError" # }
```

## Fixing Missing Secret References

When pods reference Secrets that don't exist, create the Secret before the pod can start.

```
# Check if Secret exists kubectl get secret app-secrets -n default # If not found, check the pod specification for what's needed kubectl get pod myapp-6f8d9c7b5-x4k2h -o yaml | grep -A 10 secretRef # Create the missing Secret kubectl create secret generic app-secrets \ --from-literal=database-password=secretpass123 \ --from-literal=api-key=key_abc123xyz \ -n default
``` [...] For Secrets referenced in environment variables, verify the exact key names match.

```
apiVersion: v1 kind: Pod metadata: name: myapp spec: containers: - name: app image: myapp:v1.0 env: # This must match an actual key in the Secret - name: DB_PASSWORD valueFrom: secretKeyRef: name: app-secrets key: database-password # Must exist in Secret optional: false # Fail if missing (default behavior)
```

Check that the Secret contains the referenced key. [...] ## Understanding CreateContainerConfigError

CreateContainerConfigError occurs during the container configuration phase, after scheduling and before the container starts. Kubernetes checks that referenced configuration objects can be resolved. When this fails, the container never starts and the pod shows CreateContainerConfigError status.

Common causes include referencing nonexistent Secrets or ConfigMaps, using incorrect keys within those objects, and missing keys in projected volumes. Schema errors in environment variable definitions are usually rejected by the API server before the pod is created. Unlike runtime errors that might be transient, CreateContainerConfigError indicates a configuration problem that won't resolve without intervention.
- [Resolve Common Kubernetes Deployment Errors | SFEIR Institute](https://institute.sfeir.com/en/kubernetes-training/resolve-errors-deployment-kubernetes) — ### Causes and Solutions

| Cause | Diagnostic Indicator | Solution |
 --- 
| Application crash at startup | Stack trace in logs | Fix code, verify dependencies |
| Missing environment variable | `KeyError`, `undefined` | Add variable in Deployment |
| Missing config file | `FileNotFoundError` | Verify ConfigMaps and Secrets mounts |
| Port already in use | `Address already in use` | Modify `containerPort` or kill process |
| Invalid command | `exec format error` | Check `command:` and `args:` in spec |

```
# Fix example: adding a missing variable spec: containers: - name: api env: - name: DATABASE_URL valueFrom: secretKeyRef: name: db-credentials key: url 
```

## ImagePullBackOff: Image Not Found {#imagepullbackoff} [...] CreateContainerConfigError indicates an error in container configuration before it even starts. The problem often comes from referenced Secrets or ConfigMaps.

### Diagnosis

```
kubectl describe pod my-pod | grep -A3 "Warning" # Verify Secret exists kubectl get secret my-secret # Verify key exists in Secret kubectl get secret my-secret -o jsonpath='{.data}' 
```

### Causes and Solutions

| Cause | Solution |
 --- |
| Non-existent Secret | Create Secret before Deployment |
| Missing key in Secret | Add key with `kubectl edit secret` |
| Missing referenced ConfigMap | Create required ConfigMap |
| Incorrect subPath | Verify path spelling | [...] ```
# Create missing secret kubectl create secret generic app-secret \ --from-literal=API_KEY=abc123 # Check references in deployment kubectl get deployment my-app -o yaml | grep -A5 "secretKeyRef" 
```

ConfigMaps and Secrets management is covered in detail in our Kubernetes Application Development guides.

## OOMKilled: Memory Exceeded {#oomkilled}

OOMKilled means the container exceeded its memory limit and was killed by the Linux kernel. This is a protection to prevent the entire node from becoming unstable.

### Diagnosis

```
# See termination reason kubectl describe pod my-pod | grep -A3 "Last State" # See restart history kubectl get pod my-pod -o jsonpath='{.status.containerStatuses.lastState}' # Monitor memory consumption kubectl top pod my-pod 
```

### Solution
- [Secrets | Kubernetes](https://kubernetes.io/docs/concepts/configuration/secret) — By default, Secrets are required. None of a Pod's containers will start until all non-optional Secrets are available.

If a Pod references a specific key in a non-optional Secret and that Secret does exist, but is missing the named key, the Pod fails during startup.

### Using Secrets as files from a Pod

If you want to access data from a Secret in a Pod, one way to do that is to have Kubernetes make the value of that Secret be available as a file inside the filesystem of one or more of the Pod's containers.

For instructions, refer to Create a Pod that has access to the secret data through a Volume.

When a volume contains data from a Secret, and that Secret is updated, Kubernetes tracks this and updates the data in the volume, using an eventually-consistent approach.

#### Note: [...] For instructions, refer to Define container environment variables using Secret data.

It's important to note that the range of characters allowed for environment variable names in pods is restricted. If any keys do not meet the rules, those keys are not made available to your container, though the Pod is allowed to start.

### Container image pull Secrets

If you want to fetch container images from a private repository, you need a way for the kubelet on each node to authenticate to that repository. You can configure image pull Secrets to make this possible. These Secrets are configured at the Pod level.

#### Using imagePullSecrets [...] apiVersion: v1 apiVersion: v1 apiVersion:  v1  kind: Secret kind: Secret  kind:  Secret  metadata: metadata:  metadata:   name: dotfile-secret  name: dotfile-secret  name:  dotfile-secret  data: data:  data:   .secret-file: dmFsdWUtMg0KDQo=  .secret-file: dmFsdWUtMg0KDQo=  .secret-file:  dmFsdWUtMg0KDQo=  --- ---  ---  apiVersion: v1 apiVersion: v1  apiVersion:  v1  kind: Pod kind: Pod  kind:  Pod  metadata: metadata:  metadata:   name: secret-dotfiles-pod  name: secret-dotfiles-pod  name:  secret-dotfiles-pod  spec: spec:  spec:   volumes:  volumes:  volumes:   - name: secret-volume  - name: secret-volume  name:  secret-volume   secret:  secret:  secret:   secretName: dotfile-secret  secretName: dotfile-secret  secretName:  dotfile-secret   containers:  containers:  containers:   - name:
- [10 Most Common Reasons Kubernetes Deployments Fail (Part 1)](https://kukulinski.com/10-most-common-reasons-kubernetes-deployments-fail-part-1) — Once again, the `Events` section explains the problem.  It's telling us that the Kubelet failed to mount a volume from the secret, `myothersecret`.  To fix this problem, create `myothersecret` containing the necessary secure credentials.  Once `myothersecret` has been created, the container will start correctly.

## 4. Liveness/Readiness Probe Failure

An important lesson for developers to learn when working with containers and Kubernetes is that just because your application container is running, doesn't mean that it's working. [...] ```
 # missing-secret.yaml apiVersion: v1 kind: Pod metadata: name: secret-pod spec: containers: - name: test-container image: gcr.io/google_containers/busybox command: [ "/bin/sh", "-c", "env" ] volumeMounts: - mountPath: /etc/secret/ name: myothersecret restartPolicy: Never volumes: - name: myothersecret secret: secretName: myothersecret 
```

Let's create this Pod with `kubectl create -f missing-secret.yaml`.

After a few minutes, when we get our Pods, we'll see that it still is in the state of `ContainerCreating`.

```
 $ kubectl get pods NAME READY STATUS RESTARTS AGE secret-pod 0/1 ContainerCreating 0 4h 
```

That's odd ... let's `describe` the Pod to see whats going on. [...] The last item in the `Events` section explains what went wrong.  The Pod is attempting to access a ConfigMap named `special-config`, but it's not found in this namespace.  Once we create the ConfigMap, the Pod should restart and pull in the runtime data.

Accessing Secrets as environmental variables within your Pod specification will result in similar errors, like we've seen here with ConfigMaps.

But what if you're accessing a Secret or a ConfigMap via a volume?

### Missing Secret

Here's a Pod spec that references a Secret named `myothersecret` and attempts to mount it as a volume.
- [How to Fix CreateContainerConfigError from Misconfigured Secrets](https://oneuptime.com/blog/post/2026-02-09-createcontainerconfigerror-secrets/view) — ```
# WRONG - mixing value and valueFrom env: - name: BAD_CONFIG value: "something" valueFrom: secretKeyRef: name: app-secrets key: api-key # WRONG - typo in valueFrom env: - name: BAD_CONFIG valuFrom: # Should be valueFrom secretKeyRef: name: app-secrets key: api-key
```

## Validating Volume Mount Configuration

Missing Secret or ConfigMap data used by volumes can prevent startup, while mismatched `volumeMount` names are rejected by API validation. Verify volume definitions and mount paths. [...] For Secrets referenced in environment variables, verify the exact key names match.

```
apiVersion: v1 kind: Pod metadata: name: myapp spec: containers: - name: app image: myapp:v1.0 env: # This must match an actual key in the Secret - name: DB_PASSWORD valueFrom: secretKeyRef: name: app-secrets key: database-password # Must exist in Secret optional: false # Fail if missing (default behavior)
```

Check that the Secret contains the referenced key. [...] ```
apiVersion: v1 kind: Pod metadata: name: myapp spec: containers: - name: app image: myapp:v1.0 env: # Required configuration (default behavior) - name: DATABASE_URL valueFrom: secretKeyRef: name: app-secrets key: database-url optional: false # Pod won't start if missing # Optional configuration - name: FEATURE_FLAG valueFrom: configMapKeyRef: name: optional-config key: feature-enabled optional: true # Pod starts even if missing
```

For volumes, set `optional: true` to allow the pod to start even if the ConfigMap or Secret doesn't exist.

```
volumes: - name: optional-config configMap: name: app-config optional: true - name: optional-secret secret: secretName: app-secrets optional: true
```

## Fixing Environment Variable Syntax Errors
- [Day 16/100 : Secret not found](https://medium.com/@shaikmustafa8991/day-16-100-secret-not-found-ab6cdab8ecd4) — it refuses to start the container. It's a configuration issue. If Kubernetes says a Secret is missing, trust it and check the namespace first.