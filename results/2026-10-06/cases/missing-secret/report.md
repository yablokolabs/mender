# Root cause: checkout pod CreateContainerConfigError due to missing secret checkout-secrets-x

Service `checkout` in namespace `shop`.

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

## Tavily sources
Queries: Kubernetes CreateContainerConfigError secret not found deployment env secretKeyRef; pod pending CreateContainerConfigError missing secret reference mismatch manifest; Kubernetes deployment secretKeyRef name mismatch causes pod startup failure
- [[CreateContainerConfigError secret not found] sync secrets option · Issue #236 · kubernetes-sigs/secrets-store-csi-driver · GitHub](https://github.com/kubernetes-sigs/secrets-store-csi-driver/issues/236) — pod definition

```
kind: Pod apiVersion: v1 metadata: name: nginx-secrets-store-env-var namespace: kube-infrastructure labels: aadpodidbinding: $IDENTITY_NAME spec: containers: - name: nginx image: nginx volumeMounts: - name: secrets-store-inline mountPath: "/mnt/secrets-store" readOnly: true env: - name: SECRET_PASSWORD valueFrom: secretKeyRef: name: $SECRET_NAME key: password volumes: - name: secrets-store-inline csi: driver: secrets-store.csi.k8s.io readOnly: true volumeAttributes: secretProviderClass: "azure-kv-test-env-vars" 
```

when trying to create the pod, the pod is stuck in `CreateContainerConfigError` state due to the first failure of secret volume mount and secret is not found.

Here's the log [...] Here's the log

```
 Warning FailedMount 2m42s kubelet, aks-default-28105498-vmss000001 MountVolume.SetUp failed for volume "secrets-store-inline" : kubernetes.io/csi: mounter.SetupAt failed: rpc error: code = DeadlineExceeded desc = context deadline exceeded Normal Pulling 76s (x8 over 2m40s) kubelet, aks-vmss000001 Pulling image "nginx" Normal Pulled 75s (x8 over 2m39s) kubelet, aks-vmss000001 Successfully pulled image "nginx" Warning Failed 75s (x8 over 2m39s) kubelet, aks-vmss000001 Error: secret "test-aks-kv-int" not found 
```

Need to find a way to get the pod ignoring `secret not found` issue till the mount is successfully done, not sure how !

What did you expect to happen:  
 The pod should be up and running with the secret exposed as ENV variable. [...] Which provider are you using:  
 Azure Key Vault

Environment:

 Secrets Store CSI Driver version: 0.0.7
 Kubernetes version: 1.16.9

Reactions are currently unavailable

## Activity

Sign up for free to join this conversation on GitHub. Already have an account? Sign in to comment

## Metadata

## Metadata

### Assignees

### Labels

kind/bugCategorizes issue or PR as related to a bug.Categorizes issue or PR as related to a bug.

No type

No projects

No milestone

None yet

No branches or pull requests

## Issue actions

You can’t perform that action at this time.
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
``` [...] ## Identifying CreateContainerConfigError Issues

Check pod status to confirm the error.

```
# List pods showing errors kubectl get pods # Output: # NAME READY STATUS RESTARTS AGE # myapp-6f8d9c7b5-x4k2h 0/1 CreateContainerConfigError 0 2m # Get detailed error information kubectl describe pod myapp-6f8d9c7b5-x4k2h
```

The Events section shows the specific configuration problem.

```
# Example events: # Events: # Warning Failed 1m kubelet Error: secret "app-secrets" not found # Warning Failed 1m kubelet Error: couldn't find key api-key in Secret default/app-secrets # Warning Failed 1m kubelet Error: configmap "app-config" not found
```

View container status for additional details.
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
- [🚨 Day 16/100 : Secret not found](https://medium.com/@shaikmustafa8991/day-16-100-secret-not-found-ab6cdab8ecd4) — The manifest referenced database credentials:

envFrom:  
 - secretRef:  
 name: db-credentials
But the pod stayed stuck in:

CreateContainerConfigError  
Secret "db-credentials" not found
The app code was fine.  
The cluster was fine.

The configuration was not.

## 🤔 What Actually Happened

Kubernetes does not guess.  
It does not search other namespaces.  
It does not create secrets automatically.

It simply checks:

> _“Does a Secret with this exact name exist here?”_

If the answer is no → pod never starts.

## 🧠 Important Kubernetes Rule

Secrets are namespace-scoped.

## Get Shaik Mustafa’s stories in your inbox

Join Medium for free to get updates from this writer.

Subscribe

Subscribe

- [x] 

Remember me for faster sign in

 

That means:
- [Kubernetes CreateContainerConfigError and CreateContainerError | Sysdig](https://www.sysdig.com/blog/kubernetes-createcontainerconfigerror-createcontainererror) — 1. Pull the image.
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

### Not found Secret [...] ### Not found Secret

Secrets are a more secure manner to store sensitive information in Kubernetes. Remember, though, this is just raw data encoded in base64, so it's not really encrypted, just obfuscated.

In case a Pod contains a reference to a non-existent secret, Kubelet will throw a CreateContainerConfigError, indicating that necessary data couldn't be retrieved in order to form container config.

### Container name already in use

While an unusual situation, in some cases a conflict might occur because a particular container name is already being used. Since every docker container should have a unique name, you will need to either delete the original or rename the new one being created.

## How to troubleshoot CreateContainerError and CreateContainerConfigError
- [Fix CreateContainerError, CreateContainerConfigError in K8s](https://komodor.com/learn/how-to-fix-createcontainerconfigerror-and-createcontainer-errors) — If the error is `waiting to start`:

 This means that an object mounted by the container is missing. Assuming you already checked for a missing ConfigMap or Secret, there could be a storage volume or other object required by the container.
 Review the pod manifest and check all the objects mounted by the pod or the container, and verify that they are available in the same namespace. If not, create them, or change the manifest to point to an available object.

As above, please note that this procedure will only resolve the most common causes of CreateContainerError. If one of the quick fixes above did not work, you’ll need to undertake a more complex, non-linear diagnosis procedure to identify which parts of the Kubernetes environment contribute to the problem and resolve them. [...] 5 min read September 9th, 2021

Kubernetes Troubleshooting

`CreateContainerConfigError` in Kubernetes indicates an issue when transitioning a container from a pending state to running, typically due to incorrect or incomplete YAML configurations. This error frequently arises from missing or misconfigured essentials like ConfigMaps or Secrets. Additionally, factors such as improper image specifications or insufficient resources can also lead to this error. To diagnose `CreateContainerConfigError` , execute ‘kubectl get pods’ to check the pod’s status. For example:

```
NAME READY STATUS RESTARTS AGE  
my-pod-1 0/1 CreateContainerConfigError 0 1m23s  

```
- [How to Fix CreateContainerConfigError from Misconfigured Secrets](https://oneuptime.com/blog/post/2026-02-09-createcontainerconfigerror-secrets/view) — View container status for additional details.

```
kubectl get pod myapp-6f8d9c7b5-x4k2h -o jsonpath='{.status.containerStatuses.state.waiting}' | jq # Output: # { # "message": "secret \"app-secrets\" not found", # "reason": "CreateContainerConfigError" # }
```

## Fixing Missing Secret References

When pods reference Secrets that don't exist, create the Secret before the pod can start.

```
# Check if Secret exists kubectl get secret app-secrets -n default # If not found, check the pod specification for what's needed kubectl get pod myapp-6f8d9c7b5-x4k2h -o yaml | grep -A 10 secretRef # Create the missing Secret kubectl create secret generic app-secrets \ --from-literal=database-password=secretpass123 \ --from-literal=api-key=key_abc123xyz \ -n default
``` [...] ## On this page

CreateContainerConfigError prevents pods from starting by blocking container creation before the container can run. This error typically indicates problems with how containers reference Secrets, ConfigMaps, or volumes. The pod reaches the phase where Kubernetes tries to configure the container runtime, but validation fails due to missing or misconfigured references.

Understanding the specific causes and implementing proper validation prevents these configuration errors from reaching production environments.

## Understanding CreateContainerConfigError [...] ```
# Correct syntax examples apiVersion: v1 kind: Pod metadata: name: myapp spec: containers: - name: app image: myapp:v1.0 env: # Direct value - name: ENVIRONMENT value: "production" # From Secret - name: API_KEY valueFrom: secretKeyRef: name: app-secrets key: api-key # From ConfigMap - name: LOG_LEVEL valueFrom: configMapKeyRef: name: app-config key: log-level # From field reference - name: POD_NAME valueFrom: fieldRef: fieldPath: metadata.name # From resource field - name: CPU_LIMIT valueFrom: resourceFieldRef: containerName: app resource: limits.cpu
```

Common manifest errors include mixing `value` with `valueFrom`, incorrect indentation, and typos in field names.
- [Fixing CreateContainerConfigError & CreateContainerError](https://spacelift.io/blog/createcontainerconfigerror) — ### Step 4: Reapply the Manifest

Once you’ve ensured your ConfigMaps and Secrets are correctly populated, Kubernetes should be able to successfully create your containers. You can force the creation to proceed by deleting and reapplying your Pod or Deployment manifest with Kubectl:

```
$ kubectl delete -f pod.yaml $ kubectl apply -f pod.yaml
```

## What is CreateContainerError?

`CreateContainerError` is an error that can be triggered when Kubernetes begins to transition a Pod from the Pending into the Running state. It signals that although the container’s configuration is valid, the container couldn’t be created because of a runtime problem.

### Common Causes of CreateContainerError [...] ### Common causes of CreateContainerConfigError

The common causes of `CreateContainerConfigError` include missing Kubernetes ConfigMaps and Secrets.

 Missing ConfigMap – Referencing a ConfigMap that doesn’t exist will cause this error to occur. The missing ConfigMap will prevent Kubernetes from assembling the configuration data to supply to the container. (Read more about Kubernetes ConfigMap.)
 Missing Secret – Similarly, the error will also occur when your container manifest references an invalid Secret.

### Checking for CreateContainerConfigError

You can easily check whether any of your Pods have experienced `CreateContainerConfigError` by checking the `STATUS` values reported by Kubectl’s `get pods` command:

```
$ kubectl get pods app 0/1 CreateContainerConfigError 0  10s
``` [...] ### Step 3: Fix the Configuration Issue

Now you can proceed to fix the issue. The action to take will depend on the specific cause of the `CreateContainerConfigError`:

#### 1. ConfigMap not found

This means a `configMapRef` or `configMapKeyRef` field in your Pod manifest references a ConfigMap that doesn’t exist in your cluster or namespace. To resolve the problem, create a new ConfigMap with the correct name, then reapply your Pod’s manifest.

#### 2. Secret not found

In the same way, the issue can also occur when you try to access a Secret that doesn’t exist. Solve the problem by first adding the Secret to your cluster, then recreating your Pod.

#### 3. Couldn’t find key in ConfigMap or secret
- [Fix CreateContainerConfigError & CreateContainerError](https://www.groundcover.com/kubernetes-troubleshooting/createcontainerconfigerror-createcontainererror) — If you suspect this might be the issue, inspect the output of the following commands again, being sure to check that all of your Pod's ConfigMaps and secrets are properly configured:

## How to Fix CreateContainerConfigError

Once you’ve pinpointed the cause of a CreateContainerConfigError event, fixing it is usually easy enough: To resolve CreateContainerConfigError, create whichever ConfigMap or Secret your container configuration points to but which does not actually exist. After correcting a missing or inaccessible ConfigMap or Secret, you may also need to reapply the Pod manifest. Or, if the resource does exist but is not accessible to a Pod that needs it due to a misconfiguration, you can redeploy the resource with the proper settings. [...] Start by examining the manifests for the failed Pod, which detail the image and Pod configuration for your application. The manifest files are typically located in the directory /etc/kubernetes/manifests, although this can vary depending on which Kubernetes distribution you are using. If you're unsure where the manifest is located, you can try to search for it using a command like:

Read the YAML code and determine whether you've defined any storage resources for the Pod. If you have, make sure those resources exist and are accessible.

You can also read the YAML to check which container images the Pod uses. Then, you can download the container images directly and use a command like docker inspect to verify that they have a proper entrypoint. [...] ## Common Causes for CreateContainerConfigError

The most common cause for CreateContainerConfigError is a failure by Kubernetes to locate resources that are part of a container's configuration. Specifically, this event usually happens when Kubernetes can't locate either a ConfigMap or a secret.

| Cause | Description |
 --- |
| Missing ConfigMap | A ConfigMap referenced by the Pod's configuration does not exist or is not accessible to the Pod. |
| Missing secret | A secret referenced by the Pod's configuration does not exist or is not accessible to the Pod. |

### Missing ConfigMap
- [Troubleshooting and Resolving a Pod Stuck in 'CreateContainerConfigError' in Kubernetes · Coffee with Ana in the 🌩️](https://coffeewithana.cloud/posts/k8s-pod-createcontainerconfigerror) — The Events section shows a list of all the events that have occurred in the process of creating the pod.

And here we find the issue. The pod is actually missing a secret, the ClientId in my case, that it needs to start. And that is why the pod is in:

```
 State: Waiting  State: Waiting  Reason: CreateContainerConfigError Reason: CreateContainerConfigError
```

If you want to double-check that the secret is missing, you can run `kubectl get secrets -n`  and check if the secret is not there.

Or you can output it in a JSON format and check that the key is missing by running the following command:
- [Secrets | Kubernetes](https://kubernetes.io/docs/concepts/configuration/secret) — By default, Secrets are required. None of a Pod's containers will start until all non-optional Secrets are available.

If a Pod references a specific key in a non-optional Secret and that Secret does exist, but is missing the named key, the Pod fails during startup.

### Using Secrets as files from a Pod

If you want to access data from a Secret in a Pod, one way to do that is to have Kubernetes make the value of that Secret be available as a file inside the filesystem of one or more of the Pod's containers.

For instructions, refer to Create a Pod that has access to the secret data through a Volume.

When a volume contains data from a Secret, and that Secret is updated, Kubernetes tracks this and updates the data in the volume, using an eventually-consistent approach.

#### Note:
- [🚨 Day 16/100 : Secret not found](https://medium.com/@shaikmustafa8991/day-16-100-secret-not-found-ab6cdab8ecd4) — Kubernetes

K8s

Minikube

Troubleshooting

Mustafa

# 🚨 Day 16/100 : Secret not found

Image 3: Shaik Mustafa

Shaik Mustafa

Follow

2 min read

·

Jan 19, 2026

[](

2

[](

[](

Listen

Share

happens when a pod references a Kubernetes Secret that does not exist in the same namespace or is incorrectly named

If Kubernetes can’t locate the Secret, it refuses to start the container.

Press enter or click to view image in full size

Image 4

> _The pod was created.  
> The deployment looked correct.  
> Yet the container never started._

Not because of code.  
Not because of resources.  
Because Kubernetes couldn’t find a Secret it was told to use.

## 🔥 Real-Time Production Scenario

A new microservice was deployed.

The manifest referenced database credentials: [...] ## 4️⃣ Wrong Kubernetes context

Secret created on:

   Local cluster

Pod running on:

   Production cluster

Classic human mistake.

## 🛠️ How Seniors Troubleshoot It

## Step 1️⃣ Verify Namespace

kubectl config view --minify | grep namespace

## Step 2️⃣ Check if Secret Exists

kubectl get secret <name> -n <namespace>

## Step 3️⃣ Validate Manifest

Ensure the pod references:

   Correct name
   Correct namespace
   Correct key structure

## Step 4️⃣ Fix It

Choose one:

✔ Create the missing Secret  
✔ Deploy it to the correct namespace  
✔ Correct the name in deployment YAML

## 🧨 Real Production Incident

Issue:  
Pods failing after a new environment rollout.

Cause:  
Secrets were created manually in staging but not automated for production. [...] The manifest referenced database credentials:

envFrom:  
 - secretRef:  
 name: db-credentials
But the pod stayed stuck in:

CreateContainerConfigError  
Secret "db-credentials" not found
The app code was fine.  
The cluster was fine.

The configuration was not.

## 🤔 What Actually Happened

Kubernetes does not guess.  
It does not search other namespaces.  
It does not create secrets automatically.

It simply checks:

> _“Does a Secret with this exact name exist here?”_

If the answer is no → pod never starts.

## 🧠 Important Kubernetes Rule

Secrets are namespace-scoped.

## Get Shaik Mustafa’s stories in your inbox

Join Medium for free to get updates from this writer.

Subscribe

Subscribe

- [x] 

Remember me for faster sign in

 

That means:
- [Instagram](https://www.instagram.com/p/DUGL945mD7O) — 🚨 Kubernetes Failure Scenario – Can you spot the issue?  
A Secret is created and used as environment variables in a Deployment.  
The Pod starts successfully ✅  
But the application fails to authenticate with the database ❌  
Inside the container, the environment variables show unexpected values.  
So what went wrong? 🤔  
👉 Root Cause  
Kubernetes does NOT automatically update environment variables inside a running Pod when a Secret is modified.  
If the Secret was updated after the Pod was created, the container will still use the old values that were injected at startup.  
That’s why: • Pod is running  
• But DB authentication fails  
• And env vars don’t match the latest Secret  
👉 Fix  
Restart the Pods so they pick up the updated Secret values.
- [10 Most Common Reasons Kubernetes Deployments Fail (Part 1)](https://kukulinski.com/10-most-common-reasons-kubernetes-deployments-fail-part-1) — $ kubectl describe pod secret-pod Name: secret-pod Namespace: fail Node: gke-ctm-1-sysdig2-35e99c16-tgfm/10.128.0.2 Start Time: Sat, 11 Feb 2017 14:07:13 -0500 Labels: Status: Pending IP: Controllers: [...] Events: FirstSeen LastSeen Count From SubObjectPath Type Reason Message --------- -------- ----- ---- ------------- -------- ------ ------- 18s 18s 1 {default-scheduler } Normal Scheduled Successfully assigned secret-pod to gke-ctm-1-sysdig2-35e99c16-tgfm 18s 2s 6 {kubelet gke-ctm-1-sysdig2-35e99c16-tgfm} Warning FailedMount MountVolume.SetUp failed for volume "kubernetes.io/secret/337281e7-f065-11e6-bd01-42010af0012c-myothersecret" (spec.Name: "myothersecret") pod "337281e7-f065-11e6-bd01-42010af0012c" (UID: "337281e7-f065-11e6-bd01-42010af0012c") with: secrets "myothersecret" not [...] ```
 # missing-secret.yaml apiVersion: v1 kind: Pod metadata: name: secret-pod spec: containers: - name: test-container image: gcr.io/google_containers/busybox command: [ "/bin/sh", "-c", "env" ] volumeMounts: - mountPath: /etc/secret/ name: myothersecret restartPolicy: Never volumes: - name: myothersecret secret: secretName: myothersecret 
```

Let's create this Pod with `kubectl create -f missing-secret.yaml`.

After a few minutes, when we get our Pods, we'll see that it still is in the state of `ContainerCreating`.

```
 $ kubectl get pods NAME READY STATUS RESTARTS AGE secret-pod 0/1 ContainerCreating 0 4h 
```

That's odd ... let's `describe` the Pod to see whats going on. [...] Once again, the `Events` section explains the problem.  It's telling us that the Kubelet failed to mount a volume from the secret, `myothersecret`.  To fix this problem, create `myothersecret` containing the necessary secure credentials.  Once `myothersecret` has been created, the container will start correctly.

## 4. Liveness/Readiness Probe Failure

An important lesson for developers to learn when working with containers and Kubernetes is that just because your application container is running, doesn't mean that it's working.
- [Kubernetes Error Guide: 'CreateContainerConfigError' Missing](https://devopsaitoolkit.com/blog/kubernetes-error-createcontainerconfigerror) — Compare the key names against the `configMapKeyRef`/`secretKeyRef` from Step 2 — watch for typos and case.

### Step 5: Fix the source, then let the kubelet retry

```
# create the missing ConfigMap/Secret, or fix the reference, then:# create the missing ConfigMap/Secret, or fix the reference, then:kubectl rollout restart deploy/<DEPLOY> -n <NS> kubectl  rollout  restart deploy/< DEPLO Y> -n < N S>kubectl get pods -n <NS> -w kubectl  get  pods -n < N S> -w
```

The kubelet retries `CreateContainerConfigError` automatically, but a rollout restart guarantees a clean pod once the source is corrected.

## Example Root Cause Analysis

A new `api` Deployment in namespace `shop` rolls out one pod stuck in `CreateContainerConfigError`. [...] The pod uses `envFrom.configMapRef` (or `secretRef`) naming an object that was never created (or was deleted/renamed).

```
kubectl get configmap -n shop kubectl  get  configmap -n  shop
```

```
NAME DATA AGE NAME DATA AGEapp-config 6 3happ-config 6 3hkube-root-ca.crt 1 3hkube-root-ca.crt 1 3h
```

The pod references `api-config`, but only `app-config` exists — a rename that was not applied to the Deployment.

### 2. A referenced key is missing inside an existing object

The ConfigMap/Secret exists, but `configMapKeyRef`/`secretKeyRef` names a key that is not present.

```
kubectl get configmap app-config -n shop -o jsonpath='{.data}' | tr ',' '\n' kubectl  get  configmap app-config -n  shop -o jsonpath='{.data}'  |  tr ','  '\n'
``` [...] ```
kubectl get pod api-6c8f9d7b54-q9w2r -n shop -o jsonpath='{range .spec.containers.env[]}{.name}{" <- "}{.valueFrom.secretKeyRef.name}{"/"}{.valueFrom.secretKeyRef.key}{"\n"}{end}' kubectl  get  pod api-6c8f9d7b54-q9w2r -n  shop -o jsonpath='{range .spec.containers.env[]}{.name}{" <- "}{.valueFrom.secretKeyRef.name}{"/"}{.valueFrom.secretKeyRef.key}{"\n"}{end}'
```

```
DB_PASSWORD <- db-credentials/postgres-paswordDB_PASSWORD <- db-credentials/postgres-pasword
```

The key `postgres-pasword` is a typo for `postgres-password`, so the lookup yields `couldn't find key`.

## Diagnostic Workflow

### Step 1: Confirm the status and read the exact error