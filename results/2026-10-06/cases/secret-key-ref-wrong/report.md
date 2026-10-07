# Root cause: checkout pods fail CreateContainerConfigError due to missing secret key 'token'

Service `checkout` in namespace `shop`.

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

## Tavily sources
Queries: Kubernetes CreateContainerConfigError "couldn't find key" secretKeyRef; Kubernetes secretKeyRef key mismatch deployment secret missing key; Kubernetes pod CreateContainerConfigError secret reference failure
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
- [[CreateContainerConfigError secret not found] sync secrets option · Issue #236 · kubernetes-sigs/secrets-store-csi-driver · GitHub](https://github.com/kubernetes-sigs/secrets-store-csi-driver/issues/236) — pod definition

```
kind: Pod apiVersion: v1 metadata: name: nginx-secrets-store-env-var namespace: kube-infrastructure labels: aadpodidbinding: $IDENTITY_NAME spec: containers: - name: nginx image: nginx volumeMounts: - name: secrets-store-inline mountPath: "/mnt/secrets-store" readOnly: true env: - name: SECRET_PASSWORD valueFrom: secretKeyRef: name: $SECRET_NAME key: password volumes: - name: secrets-store-inline csi: driver: secrets-store.csi.k8s.io readOnly: true volumeAttributes: secretProviderClass: "azure-kv-test-env-vars" 
```

when trying to create the pod, the pod is stuck in `CreateContainerConfigError` state due to the first failure of secret volume mount and secret is not found.

Here's the log
- [How to fix Kubernetes CreateContainerConfigError?](https://www.sherlocks.ai/guides/kubernetes/createcontainerconfigerror) — ## Kubernetes CreateContainerConfigError FAQ#

Is CreateContainerConfigError an image problem? No. The image pulled fine. Kubernetes could not assemble the container's config from its Secrets or ConfigMaps.

How do I find what is missing? Run kubectl describe pod and read the Events. It usually names the exact Secret, ConfigMap, or key that could not be resolved.

Why does the object exist but the pod still fails? Either the specific key it references is absent, or the object is in a different namespace than the pod.

Do Secret and ConfigMap references cross namespaces? No. A pod can only reference Secrets and ConfigMaps in its own namespace, so a mismatch leaves the reference unresolvable. [...] ## What causes CreateContainerConfigError?#

Three causes cover nearly every case, and they map to your spec's references.

A missing Secret. The pod references a Secret that does not exist in the namespace. Maybe it was never created, maybe it was created in a different namespace, maybe a deploy order left the pod starting before the Secret was applied. The event reads secret not found, and the container waits.

An absent key in a ConfigMap or Secret. The object exists, but the specific key the container asks for is not in it. The ConfigMap is there, but the DATABASE\_URL key the spec references is missing or misspelled. The event names the key. This one is easy to miss because the object shows up in `kubectl get`, so a quick glance suggests everything is fine. [...] bash

```
# Every Secret and ConfigMap this pod's containers referencekubectl get pod  -n  -o json | jq -r ' .spec.containers[] | (.envFrom[]? | "envFrom \((.secretRef // .configMapRef).name)"), (.env[]? | select(.valueFrom) | .valueFrom | (.secretKeyRef // .configMapKeyRef) | select(.) | "valueFrom \(.name).\(.key)")'  
```

Then confirm each one exists in the pod's namespace and holds the key that was asked for:

bash

```
kubectl get secret  -n  -o jsonpath='{.data}' | jq -r 'keys[]'kubectl get configmap  -n  -o jsonpath='{.data}' | jq -r 'keys[]'  
```

Listing the keys beats `describe` here, because it shows the exact strings, trailing spaces and case included, and a key that is nearly right is the whole failure.

## What causes CreateContainerConfigError?#
- [Fixing CreateContainerConfigError & CreateContainerError](https://spacelift.io/blog/createcontainerconfigerror) — ### Step 3: Fix the Configuration Issue

Now you can proceed to fix the issue. The action to take will depend on the specific cause of the `CreateContainerConfigError`:

#### 1. ConfigMap not found

This means a `configMapRef` or `configMapKeyRef` field in your Pod manifest references a ConfigMap that doesn’t exist in your cluster or namespace. To resolve the problem, create a new ConfigMap with the correct name, then reapply your Pod’s manifest.

#### 2. Secret not found

In the same way, the issue can also occur when you try to access a Secret that doesn’t exist. Solve the problem by first adding the Secret to your cluster, then recreating your Pod.

#### 3. Couldn’t find key in ConfigMap or secret [...] #### 3. Couldn’t find key in ConfigMap or secret

Finally, you’ll also get a `CreateContainerConfigError` when you reference a specific key inside a ConfigMap or Kubernetes Secret, but that key doesn’t exist. For example, the following Pod manifest will cause the error if the `app-config` ConfigMap exists but is empty:

```
apiVersion:  v1  kind:  Pod  metadata:   name:  app  spec:   containers:   -  image:  nginx: latest  name:  app  env:   -  name:  TEST_KEY  valueFrom:   configMapKeyRef:   name:  app - config  key:  test_key
```

### Step 4: Reapply the Manifest [...] ### Common causes of CreateContainerConfigError

The common causes of `CreateContainerConfigError` include missing Kubernetes ConfigMaps and Secrets.

 Missing ConfigMap – Referencing a ConfigMap that doesn’t exist will cause this error to occur. The missing ConfigMap will prevent Kubernetes from assembling the configuration data to supply to the container. (Read more about Kubernetes ConfigMap.)
 Missing Secret – Similarly, the error will also occur when your container manifest references an invalid Secret.

### Checking for CreateContainerConfigError

You can easily check whether any of your Pods have experienced `CreateContainerConfigError` by checking the `STATUS` values reported by Kubectl’s `get pods` command:

```
$ kubectl get pods app 0/1 CreateContainerConfigError 0  10s
```
- [Understanding Kubernetes `CreateContainerConfigError`: Causes and Solutions | by Michael Arauza | Medium](https://medium.com/@michaelarauza/understanding-kubernetes-createcontainerconfigerror-causes-and-solutions-e5d8f834970d) — #### 1. \\Missing or Incorrect Environment Variables\\

Kubernetes allows you to pass environment variables to containers using the `env` or `envFrom` fields in the pod spec. If the container requires a specific environment variable that is not defined or is incorrectly configured, you may encounter this error.

 \\Example\\:
 . ```yaml
 . env:
 . — name: DATABASE\_URL
 . valueFrom:
 . secretKeyRef:
 . name: my-db-secret
 . key: database-url
 . ```
 . If `my-db-secret` or `database-url` is missing, the container won’t be able to start, causing a `CreateContainerConfigError`.

#### 2. \\Incorrect Secret or ConfigMap Reference\\
- [Allow Retrieval of PlainText ExternalSecret (no key value) In Container Spec · external-secrets/kubernetes-external-secrets · Discussion #573 · GitHub](https://github.com/external-secrets/kubernetes-external-secrets/discussions/573) — NAME LAST SYNC STATUS AGE  gmail-pk-secret 4s SUCCESS 35m  But when its time to grab this secret and inject into the pod I get this error. The config is expecting a "key" value. But I don't have one to give it:  Error: unable to build kubernetes objects from release manifest: error validating "": error validating data: ValidationError(Deployment.spec.template.spec.containers.env.valueFrom.secretKeyRef): missing required field "key" in io.k8s.api.core.v1.SecretKeySelector  Here is my. container spec (helm chart):  ``` spec: serviceAccountName: a-service-account containers: {{- if eq .Release.Namespace "default"}} - name: service-internal {{ else }} - name: "service-internal-container-{{.Release.Namespace}}" {{- end }} image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default [...] ### Flydiverny Dec 8, 2020 Maintainer

|  |

| I'm not really following what exactly you are expecting?  secretKeyRef requires a key, this is k8s specification and outside of KES.  Did you inspect the generated secret to see if it results in what you you expected?  Don't use dataFrom like this, it is for generating secrets from an object, a plain string value would yield an empty secret.  If you use data you would specify the key, as required by KES spec and you would know what key to specify in your container spec.  It you check your KES pod logs you will probably see log warnings stating that your private key is not an json object or something. |

You must be logged in to vote

All reactions

0 replies

Comment options

### Uh oh!
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

### Solution [...] CreateContainerConfigError indicates an error in container configuration before it even starts. The problem often comes from referenced Secrets or ConfigMaps.

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
| Incorrect subPath | Verify path spelling | [...] ### Causes and Solutions

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

## ImagePullBackOff: Image Not Found {#imagepullbackoff}
- [CreateContainerConfigError — Resolve Missing Secrets, ConfigMaps and Keys | Gronex](https://gronex.org/errors/kubernetes-createcontainerconfigerror-secret-configmap) — Linux / shell

# CreateContainerConfigError from a missing Secret or ConfigMap

Written and reviewed bySahil Srivastav

KubernetesConfiguration referencesStartup

```
CreateContainerConfigError
```

## What this error actually means

Kubelet cannot construct the configuration needed to start a container. A frequent cause is an environment variable whose secretKeyRef or configMapKeyRef points to a missing object or key. The process has not reached application initialisation, so changing its log level or restarting its dependency will not repair this reference. [...] 1. 1A required object was never created in this namespace. The deployment assumes configuration provisioning has already happened. An external secret controller may still be reconciling, or its provider access may have failed. The desired external secret resource is not the same thing as the generated Kubernetes Secret the pod consumes.
2. 2The object exists but a required key does not. A credentials migration changes key spelling or case while the pod retains the earlier reference. Environment-variable names and data keys need not be identical, so compare the source key explicitly rather than scanning only the variable visible to the application. [...] ### Inspect reference fields without exposing values

This prints valueFrom and envFrom references, not literal environment values or Secret contents. Also inspect init containers when they are the ones waiting. Compare object names with the event rather than guessing from the deployment name.

```
kubectl -n demo get pod app-pod -o jsonpath='{range .spec.containers[]}{.name}{"\n"}{range .env[]}{.name}{"\t"}{.valueFrom}{"\n"}{end}{.envFrom}{"\n"}{end}'
```

Step 3

### List key names, not credential values

Replace app-config with the exact name from the failed reference. The Go template enumerates keys only. A NotFound response establishes an object or namespace mismatch; a present object without the required key establishes a schema mismatch.
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
``` [...] Check that the Secret contains the referenced key.

```
# List keys in Secret kubectl get secret app-secrets -n default -o jsonpath='{.data}' | jq keys # Output should include: ["api-key", "database-password"] # If key is missing, update the Secret kubectl create secret generic app-secrets \ --from-literal=database-password=secretpass123 \ --from-literal=api-key=key_abc123xyz \ --dry-run=client -o yaml | kubectl apply -f -
```

## Resolving ConfigMap Reference Errors

ConfigMap errors follow similar patterns to Secret errors. Verify ConfigMaps exist and contain referenced keys.
- [Fix CreateContainerConfigError & CreateContainerError](https://www.groundcover.com/kubernetes-troubleshooting/createcontainerconfigerror-createcontainererror) — ## Common Causes for CreateContainerConfigError

The most common cause for CreateContainerConfigError is a failure by Kubernetes to locate resources that are part of a container's configuration. Specifically, this event usually happens when Kubernetes can't locate either a ConfigMap or a secret.

| Cause | Description |
 --- |
| Missing ConfigMap | A ConfigMap referenced by the Pod's configuration does not exist or is not accessible to the Pod. |
| Missing secret | A secret referenced by the Pod's configuration does not exist or is not accessible to the Pod. |

### Missing ConfigMap [...] Those commands list the ConfigMaps and secrets that are actually configured. Also confirm those resources exist in the same namespace as the Pod. If your Pod references any ConfigMaps or secrets that don’t appear when you ask kubectl to describe ConfigMaps and secrets, you’ve found the source of your CreateContainerConfigError.

### Step 4: Verify Permissions and Namespace Settings

You may sometimes encounter a CreateContainerConfigError even though all of the ConfigMaps and secrets referenced in a Pod's configuration exist. If this is the case, the problem is most likely that the resource in question is not accessible to the Pod due either to misconfigured permissions or because it's associated with a different namespace from the Pod. [...] Then, you reference the secret when configuring a Pod. Here's an example (also borrowed from the Kubernetes documentation) that points to a secret named secret-dockercfg:

Here again, everything will be peachy so long as your secret exists. The Secret must also be correctly configured in the same namespace as the Pod. But if the secret does not exist or is not accessible to the Pod, you’ll encounter a CreateContainerConfigError event.

## How to Troubleshoot CreateContainerConfigError

When troubleshooting CreateContainerConfigError events, start by looking at relevant logs and events to confirm that a CreateContainerConfigError has indeed occurred. Then, compare your Pod configuration to your actual configuration to determine what triggered the error.
- [How to Fix CreateContainerConfigError from Misconfigured Secrets](https://oneuptime.com/blog/post/2026-02-09-createcontainerconfigerror-secrets/view) — ## Understanding CreateContainerConfigError

CreateContainerConfigError occurs during the container configuration phase, after scheduling and before the container starts. Kubernetes checks that referenced configuration objects can be resolved. When this fails, the container never starts and the pod shows CreateContainerConfigError status.

Common causes include referencing nonexistent Secrets or ConfigMaps, using incorrect keys within those objects, and missing keys in projected volumes. Schema errors in environment variable definitions are usually rejected by the API server before the pod is created. Unlike runtime errors that might be transient, CreateContainerConfigError indicates a configuration problem that won't resolve without intervention. [...] ## On this page

CreateContainerConfigError prevents pods from starting by blocking container creation before the container can run. This error typically indicates problems with how containers reference Secrets, ConfigMaps, or volumes. The pod reaches the phase where Kubernetes tries to configure the container runtime, but validation fails due to missing or misconfigured references.

Understanding the specific causes and implementing proper validation prevents these configuration errors from reaching production environments.

## Understanding CreateContainerConfigError [...] View container status for additional details.

```
kubectl get pod myapp-6f8d9c7b5-x4k2h -o jsonpath='{.status.containerStatuses.state.waiting}' | jq # Output: # { # "message": "secret \"app-secrets\" not found", # "reason": "CreateContainerConfigError" # }
```

## Fixing Missing Secret References

When pods reference Secrets that don't exist, create the Secret before the pod can start.

```
# Check if Secret exists kubectl get secret app-secrets -n default # If not found, check the pod specification for what's needed kubectl get pod myapp-6f8d9c7b5-x4k2h -o yaml | grep -A 10 secretRef # Create the missing Secret kubectl create secret generic app-secrets \ --from-literal=database-password=secretpass123 \ --from-literal=api-key=key_abc123xyz \ -n default
```
- [Fix Kubernetes CreateContainerConfigError: Causes and Fixes | Coding Protocols](https://codingprotocols.com/blog/fix-kubernetes-createcontainerconfigerror) — 8 min read · Kubernetes

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

Fix — option A: create the missing object (see Cause 1). [...] CodingProtocols

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

8 min read · Kubernetes
- [CreateContainerConfigError vs CreateContainerError in K8s](https://www.perfectscale.io/blog/createcontainerconfigerror) — kubectl create secret generic my-secret

```

1. Configure Permissions Properly: Verify that the permissions for the resources are correctly set, allowing the pod to access them. Adjust the permissions if necessary.
2. Double-check Resource Configuration: Review the pod's configuration and ensure that all references to ConfigMaps and Secrets are accurate and properly spelled. Avoid typos that may cause the pod to look for resources in the wrong place.

## What is CreateContainerError?

CreateContainerError is an error that occurs when Kubernetes fails to create a container within a pod. It indicates failure in the containerization process. It means the issue is related to the container's creation itself. [...] Tania Duggal

By Tania DuggalMay 26, 202410 min read

TLDR: Both errors happen before your container ever starts, so there are no application logs to check, only Kubernetes events and pod descriptions. `CreateContainerConfigError` means Kubernetes couldn't assemble the container's configuration (usually a missing ConfigMap or Secret). `CreateContainerError` means the config was fine but the container runtime (containerd, Docker) failed to actually create the container (bad image, resource constraints, bad volume mounts, or a runtime problem). Fix by creating the missing ConfigMap/Secret, checking image and entrypoint, and comparing requested resources against what's available. [...] ## FAQ

What's the difference between CreateContainerConfigError and CreateContainerError? `CreateContainerConfigError` happens earlier: Kubernetes can't assemble the container's configuration, usually because a referenced ConfigMap or Secret is missing. `CreateContainerError` happens after the config is ready, when the container runtime itself fails to create the container (bad image, resource limits, bad volume mounts, or a runtime issue).

Why are there no application logs for these errors? Both errors occur before the container actually starts, so the application inside it never runs and never produces logs. You have to rely on `kubectl describe pod` and `kubectl get events` instead.
- [Resolve Common Kubernetes Deployment Errors | SFEIR Institute](https://institute.sfeir.com/en/kubernetes-training/resolve-errors-deployment-kubernetes) — CreateContainerConfigError indicates an error in container configuration before it even starts. The problem often comes from referenced Secrets or ConfigMaps.

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