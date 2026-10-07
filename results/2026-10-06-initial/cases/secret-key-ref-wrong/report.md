# Root cause: Checkout pods fail with CreateContainerConfigError due to missing secret key 'token'

Service `checkout` in namespace `shop`.

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

## Tavily sources
Queries: Kubernetes CreateContainerConfigError couldn't find key in Secret secretKeyRef mismatch; Kubernetes deployment secret key reference error missing key token secretKeyRef; Kubernetes pod pending CreateContainerConfigError secret key not found
- [Kubernetes Error Guide: 'CreateContainerConfigError' Missing](https://devopsaitoolkit.com/blog/kubernetes-error-createcontainerconfigerror) — ## Conclusion

`CreateContainerConfigError` means the image is fine but the kubelet could not build the container’s config because a referenced ConfigMap, Secret, or key is missing. The usual root causes:

1. `envFrom`/`configMapRef`/`secretRef` names an object that does not exist.
2. The object exists, but a `configMapKeyRef`/`secretKeyRef` key is absent.
3. The object lives in the wrong namespace (references are namespace-local).
4. The Secret/ConfigMap is created after the pod — an ordering race.
5. A genuinely optional reference is missing `optional: true`.
6. A typo in the object name or key string sends the lookup nowhere. [...] ```
kubectl get pod api-6c8f9d7b54-q9w2r -n shop -o jsonpath='{range .spec.containers.env[]}{.name}{" <- "}{.valueFrom.secretKeyRef.name}{"/"}{.valueFrom.secretKeyRef.key}{"\n"}{end}' kubectl  get  pod api-6c8f9d7b54-q9w2r -n  shop -o jsonpath='{range .spec.containers.env[]}{.name}{" <- "}{.valueFrom.secretKeyRef.name}{"/"}{.valueFrom.secretKeyRef.key}{"\n"}{end}'
```

```
DB_PASSWORD <- db-credentials/postgres-paswordDB_PASSWORD <- db-credentials/postgres-pasword
```

The key `postgres-pasword` is a typo for `postgres-password`, so the lookup yields `couldn't find key`.

## Diagnostic Workflow

### Step 1: Confirm the status and read the exact error [...] ### Step 1: Confirm the status and read the exact error

```
kubectl get pod <POD> -n <NS> kubectl  get  pod < PO D> -n < N S>kubectl describe pod <POD> -n <NS> | sed -n '/Events/,$p' kubectl  describe  pod < PO D> -n < N S>  |  sed -n '/Events/,$p'
```

The event message tells you whether it is a missing object (`... not found`) or a missing key (`couldn't find key ...`).

### Step 2: Identify every config source the container references

```
kubectl get pod <POD> -n <NS> -o yaml | grep -nE 'configMapRef|secretRef|configMapKeyRef|secretKeyRef|name:|key:|optional' kubectl  get  pod < PO D> -n < N S> -o  yaml  |  grep -nE 'configMapRef|secretRef|configMapKeyRef|secretKeyRef|name:|key:|optional'
```

List the exact names and keys the spec expects.
- [Fix Kubernetes CreateContainerConfigError: Causes and Fixes | Coding Protocols](https://codingprotocols.com/blog/fix-kubernetes-createcontainerconfigerror) — CodingProtocols

Get Started

Back to Blog

8 min readJuly 2, 2026Updated August 19, 2026

# Fix Kubernetes CreateContainerConfigError

Part ofTroubleshooting GuidesKubernetes

AJ

Ajeet Yadav

Platform & Cloud Engineer

Fix Kubernetes CreateContainerConfigError

## Quick answer

CreateContainerConfigError means the kubelet can't build your container's config because it references a ConfigMap or Secret that's missing, misnamed, or missing a key. Here's how to find the exact reference that's broken and fix it.

 What this error means
 Step 1: See the actual error
 Cause 1: The referenced ConfigMap or Secret does not exist
 Cause 2: The key doesn't exist in the ConfigMap or Secret
 Cause 3: The ConfigMap or Secret is in a different namespace

8 min read · Kubernetes [...] 8 min read · Kubernetes

## Fix Kubernetes CreateContainerConfigError

You run `kubectl get pods` and see this:

```
NAME READY STATUS RESTARTS AGE api-7d9f8b 0/1 CreateContainerConfigError 0 40s 
```

CreateContainerConfigError means the kubelet tried to build the container's configuration and couldn't — because the pod references a ConfigMap or Secret that doesn't exist, is misnamed, lives in the wrong namespace, or is missing a key you asked for. The container never starts, so there are no logs to read. Everything you need is in the pod's Events.

This is not the same as your app crashing. The failure happens before the container process ever runs.

### What this error means [...] If they don't match, create the ConfigMap in the pod's namespace. Copy it across if needed:

bash

```
kubectl get configmap app-config -n default -o yaml \  | sed 's/namespace: default/namespace: staging/'  \ 
```

### Cause 4: A required envFrom reference is missing

`envFrom` bulk-loads every key from a ConfigMap or Secret as environment variables. By default the reference is required — if the object is missing, the whole pod fails with `CreateContainerConfigError`, exactly like a single keyRef.

Broken spec:

yaml

```
envFrom:   -  configMapRef:   name:  shared-config  # missing → CreateContainerConfigError   -  secretRef:   name:  shared-secrets
```

Fix — option A: create the missing object (see Cause 1).
- [CreateContainerConfigError: Causes and Fix | Kubernetes](https://devopslesson.com/troubleshooting/createcontainerconfigerror) — The Events line names it precisely. Secret "payments-db-credentials" not found, or couldn't find key DATABASE\_URL in ConfigMap app-config. That string is the entire diagnosis.
2. 2

   ### Check whether it exists, and in which namespace

   $

   ```
   kubectl get secret payments-db-credentials -A
   ```

   Secrets and ConfigMaps never cross namespaces. If it exists in another one you have to copy it into this namespace. A reference will not reach it.
3. 3

   ### If the object exists, the key name is wrong

   $

   ```
   kubectl get configmap app-config -o jsonpath='{.data}' | python3 -m json.tool
   ```

   Compare the keys listed here against the configMapKeyRef or secretKeyRef in the Pod spec. Key names are case-sensitive and a missing key fails the whole container. [...] Almost always a namespace mismatch. Secrets and ConfigMaps are namespaced and cannot be referenced across namespaces, so a Secret in `default` is invisible to a Pod in `payments`. Run `kubectl get secret  -A` to see every namespace at once. Finding it somewhere else is the answer. The other causes are a typo in the reference and the Deployment having been applied before the Secret existed.

What does "couldn't find key X in ConfigMap" mean? [...] ## A checklist

1. `kubectl describe pod  | tail -10`. The `Error:` line names the object.
2. "not found" → does it exist? `kubectl get secret  -A` to check every namespace.
3. Found elsewhere → namespace mismatch; there is no cross-namespace reference.
4. "couldn't find key" → list the actual keys and compare case exactly.
5. Genuinely optional → add `optional: true`.
6. "serviceaccount not found" → create it in the Pod's namespace.
7. Many Pods affected → one missing object, likely a failed secret sync.
8. Fix the object and the Pod recovers on its own; no restart needed.

## Frequently Asked Questions

What causes CreateContainerConfigError in Kubernetes?
- [Fix Kubernetes CreateContainerConfigError (2026)](https://lucaberton.com/blog/fix-kubernetes-createcontainerconfigerror) — ## Common Mistakes

1. Wrong namespace — most common cause. ConfigMap in `default`, Pod in `production`
2. Typo in ConfigMap/Secret name — Kubernetes is case-sensitive
3. Forgot to apply ConfigMap — your Helm chart or Kustomize overlay did not include it
4. Secret key mismatch — the key in `secretKeyRef.key` must exactly match a key in the Secret data
5. Base64 encoding issues — Secrets with newlines or special characters in base64

## When It Is Not CreateContainerConfigError

If you see similar symptoms but different status: [...] ## Cause 3: Missing Secret Key

Error message:

```
Warning Failed couldn't find key "password" in Secret default/db-credentialsWarning Failed couldn't find key "password" in Secret default/db-credentials
```

The Secret exists but is missing the specific key your Pod references.

Diagnose:

```
kubectl get secret db-credentials -o jsonpath='{.data}' | jq kubectl  get  secret db-credentials -o jsonpath='{.data}'  |  jq
```

Fix — Add the missing key:

```
kubectl patch secret db-credentials -p '{"data":{"password":"czNjdXIzcDRzcw=="}}' kubectl  patch  secret db-credentials -p '{"data":{"password":"czNjdXIzcDRzcw=="}}'
```

Note: Secret values must be base64-encoded:

```
echo -n "s3cur3p4ss" | base64 echo -n  "s3cur3p4ss"  |  base64
```
- [How to Fix CreateContainerConfigError from Misconfigured Secrets](https://oneuptime.com/blog/post/2026-02-09-createcontainerconfigerror-secrets/view) — For Secrets referenced in environment variables, verify the exact key names match.

```
apiVersion: v1 kind: Pod metadata: name: myapp spec: containers: - name: app image: myapp:v1.0 env: # This must match an actual key in the Secret - name: DB_PASSWORD valueFrom: secretKeyRef: name: app-secrets key: database-password # Must exist in Secret optional: false # Fail if missing (default behavior)
```

Check that the Secret contains the referenced key. [...] Check that the Secret contains the referenced key.

```
# List keys in Secret kubectl get secret app-secrets -n default -o jsonpath='{.data}' | jq keys # Output should include: ["api-key", "database-password"] # If key is missing, update the Secret kubectl create secret generic app-secrets \ --from-literal=database-password=secretpass123 \ --from-literal=api-key=key_abc123xyz \ --dry-run=client -o yaml | kubectl apply -f -
```

## Resolving ConfigMap Reference Errors

ConfigMap errors follow similar patterns to Secret errors. Verify ConfigMaps exist and contain referenced keys. [...] ## Identifying CreateContainerConfigError Issues

Check pod status to confirm the error.

```
# List pods showing errors kubectl get pods # Output: # NAME READY STATUS RESTARTS AGE # myapp-6f8d9c7b5-x4k2h 0/1 CreateContainerConfigError 0 2m # Get detailed error information kubectl describe pod myapp-6f8d9c7b5-x4k2h
```

The Events section shows the specific configuration problem.

```
# Example events: # Events: # Warning Failed 1m kubelet Error: secret "app-secrets" not found # Warning Failed 1m kubelet Error: couldn't find key api-key in Secret default/app-secrets # Warning Failed 1m kubelet Error: configmap "app-config" not found
```

View container status for additional details.
- [Resolve Common Kubernetes Deployment Errors | SFEIR Institute](https://institute.sfeir.com/en/kubernetes-training/resolve-errors-deployment-kubernetes) — ```
# Create missing secret kubectl create secret generic app-secret \ --from-literal=API_KEY=abc123 # Check references in deployment kubectl get deployment my-app -o yaml | grep -A5 "secretKeyRef" 
```

ConfigMaps and Secrets management is covered in detail in our Kubernetes Application Development guides.

## OOMKilled: Memory Exceeded {#oomkilled}

OOMKilled means the container exceeded its memory limit and was killed by the Linux kernel. This is a protection to prevent the entire node from becoming unstable.

### Diagnosis

```
# See termination reason kubectl describe pod my-pod | grep -A3 "Last State" # See restart history kubectl get pod my-pod -o jsonpath='{.status.containerStatuses.lastState}' # Monitor memory consumption kubectl top pod my-pod 
```

### Solution [...] ### Causes and Solutions

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
| Incorrect subPath | Verify path spelling |
- [CreateContainerConfigError — Resolve Missing Secrets, ConfigMaps and Keys | Gronex](https://gronex.org/errors/kubernetes-createcontainerconfigerror-secret-configmap) — Linux / shell

# CreateContainerConfigError from a missing Secret or ConfigMap

Written and reviewed bySahil Srivastav

KubernetesConfiguration referencesStartup

```
CreateContainerConfigError
```

## What this error actually means

Kubelet cannot construct the configuration needed to start a container. A frequent cause is an environment variable whose secretKeyRef or configMapKeyRef points to a missing object or key. The process has not reached application initialisation, so changing its log level or restarting its dependency will not repair this reference. [...] 1. 1A required object was never created in this namespace. The deployment assumes configuration provisioning has already happened. An external secret controller may still be reconciling, or its provider access may have failed. The desired external secret resource is not the same thing as the generated Kubernetes Secret the pod consumes.
2. 2The object exists but a required key does not. A credentials migration changes key spelling or case while the pod retains the earlier reference. Environment-variable names and data keys need not be identical, so compare the source key explicitly rather than scanning only the variable visible to the application. [...] ## When you see it

 The image is available but the container has no application logs
 Events name a Secret, ConfigMap or key that kubelet cannot resolve
 A deployment succeeds in one namespace and stalls in another
 A renamed or hash-suffixed configuration object exists, but pods reference the old name

## How to diagnose it

Step 1

### Read the kubelet’s exact unresolved reference

Substitute the affected namespace and pod for demo and app-pod. The event should name the object or key. If it instead names runAsNonRoot or another validation rule, follow that evidence rather than creating unrelated Secrets.

```
kubectl -n demo describe pod app-pod
```

Step 2

### Inspect reference fields without exposing values
- [Unable to use secretKeyRef when key is not value #2329](https://github.com/kubernetes-sigs/kustomize/issues/2329) — Unable to use secretKeyRef when key is not value · Issue #2329 · kubernetes-sigs/kustomize ... Error from server: error when applying patch:
- [How to Fix 'Secret Management' Issues](https://oneuptime.com/blog/post/2026-01-24-secret-management-issues/view) — ```
# List all keys in a secret kubectl get secret myapp-secrets -n myapp -o jsonpath='{.data}' | jq 'keys' # View decoded secret values (be careful with this in production) kubectl get secret myapp-secrets -n myapp -o jsonpath='{.data.db-password}' | base64 -d
```

Fix the key reference in your deployment:

```
# Problem: Wrong key name env: - name: DATABASE_PASSWORD valueFrom: secretKeyRef: name: myapp-secrets key: database_password # Key does not exist # Fix: Use the correct key name env: - name: DATABASE_PASSWORD valueFrom: secretKeyRef: name: myapp-secrets key: db-password # Correct key name
```

## Fixing External Secrets Operator Issues

External Secrets Operator syncs secrets from external providers. Common issues include authentication failures and sync problems. [...] Create the missing secret:

```
# Create secret from literal values kubectl create secret generic myapp-secrets \ --from-literal=db-password='secretpassword123' \ --from-literal=api-key='abc123xyz' \ -n myapp # Create secret from files kubectl create secret generic myapp-secrets \ --from-file=tls.crt=./server.crt \ --from-file=tls.key=./server.key \ -n myapp # Create secret from env file kubectl create secret generic myapp-secrets \ --from-env-file=.env.production \ -n myapp
```

## Fixing Secret Key Not Found Errors

Sometimes the secret exists but the referenced key does not. [...] ## Fixing Missing Kubernetes Secrets

When a pod fails to start because of a missing secret, you will see errors like "secret not found" or pods stuck in ContainerCreating status.

```
# Check if the secret exists kubectl get secret myapp-secrets -n myapp # View pod events to find secret-related errors kubectl describe pod myapp-pod -n myapp | grep -A10 Events # Common error message: # Warning FailedMount secret "myapp-secrets" not found
```

Create the missing secret:
- [Resolve the 10 Most Common Kubernetes Deployment Errors | SFEIR Institute](https://institute.sfeir.com/en/kubernetes-training/resolve-errors-deployment-kubernetes-common) — ### Diagnosis

```
kubectl describe pod api-server | grep -A 10 Events 
```

### Solutions

Missing Secret or ConfigMap:

```
# Verify the secret exists kubectl get secret db-credentials kubectl get configmap app-config # Create the missing secret kubectl create secret generic db-credentials \ --from-literal=username=admin \ --from-literal=password=secret 
```

Non-existent key in ConfigMap:

```
# Error: DATABASE_URL key doesn't exist env: - name: DB_URL valueFrom: configMapKeyRef: name: app-config key: DATABASE_URL # Verify this key exists 
```

> Remember: CreateContainerConfigError almost always means a missing or incorrectly referenced Secret or ConfigMap.

## Error 6: Service Not Accessible

### Symptom

```
curl  curl: (7) Failed to connect to api-service port 8080 
```
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
 The pod should be up and running with the secret exposed as ENV variable. [...] Skip to content   
 
 

## Navigation Menu

Sign in

Appearance settings

Sign in

Sign up

Appearance settings

You signed in with another tab or window. Reload to refresh your session. You signed out in another tab or window. Reload to refresh your session. You switched accounts on another tab or window. Reload to refresh your session. Dismiss alert

{{ message }}

kubernetes-sigs   /  secrets-store-csi-driver  Public

 Notifications  You must be signed in to change notification settings
 Fork 337
 Star  1.6k

# [CreateContainerConfigError secret not found] sync secrets option #236

Copy link

Copy link

Closed

#238

Closed

[[CreateContainerConfigError secret not found] sync secrets option](/kubernetes-sigs/secrets-store-csi-driver/issues/236#top)#236

#238

Copy link

Assignees
- [How to Fix CreateContainerConfigError from Misconfigured Secrets](https://oneuptime.com/blog/post/2026-02-09-createcontainerconfigerror-secrets/view) — View container status for additional details.

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

View container status for additional details. [...] For Secrets referenced in environment variables, verify the exact key names match.

```
apiVersion: v1 kind: Pod metadata: name: myapp spec: containers: - name: app image: myapp:v1.0 env: # This must match an actual key in the Secret - name: DB_PASSWORD valueFrom: secretKeyRef: name: app-secrets key: database-password # Must exist in Secret optional: false # Fail if missing (default behavior)
```

Check that the Secret contains the referenced key.
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
- [Fix the "CreateContainerConfigError" (CKA/CKAD Lab 10)](https://www.youtube.com/watch?v=1V8egFEmqdk) — 'CreateContainerConfigError'? It usually means your Pod is looking for a Secret or ConfigMap key that simply doesn't exist. In this
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