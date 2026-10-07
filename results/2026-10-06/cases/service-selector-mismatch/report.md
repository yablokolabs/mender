# Root cause: Checkout pod terminated during normal rolling update deployment

Service `checkout` in namespace `shop`.

## Root cause
Deployment controller terminated old ReplicaSet pod as part of rolling update strategy (RollingUpdate type with default maxSurge/maxUnavailable) [11,12]

## Mechanism
1. Deployment spec update triggered new ReplicaSet checkout-5579d884d4 creation [events: 38s/31s SuccessfulCreate]. 2. Controller scaled up new ReplicaSet (2 pods) while simultaneously scaling down old ReplicaSet checkout-6b8c7bd649 per RollingUpdate semantics [12]. 3. Old pod checkout-6b8c7bd649-v8mdz (age 55s, Ready=True, healthz 200) received termination signal at 25s ago [events: Killing/SuccessfulDelete]. 4. Pod entered Terminating state with 30s grace period; container remained Running and Ready until graceful shutdown [describe: State=Running, Ready=True, Termination Grace Period=30s]. 5. No OOM kill, probe failure, or selector mismatch — all health checks passed until termination [logs: 200 responses].

Confidence: 0.95 · Labels: rolling_update, normal_behavior, deployment_controller, graceful_termination

## Evidence relied on
- events: 38s Normal SuccessfulCreate replicaset/checkout-5579d884d4 Created pod: checkout-5579d884d4-j5td9
- events: 25s Normal Killing pod/checkout-6b8c7bd649-v8mdz Stopping container checkout
- describe checkout-6b8c7bd649-v8mdz: Status: Terminating, State: Running, Ready: True, Termination Grace Period: 30s
- logs: repeated "GET /healthz HTTP/1.1" 200 for all pods including terminating one

## Tavily sources
Queries: Kubernetes deployment rolling update old pod terminated immediately after Ready health checks passing ReplicaSet Killing SuccessfulDelete; Kubernetes pod Terminating after Ready liveness readiness probes success 512Mi memory limit 96Mi startup cache; ReplicaSet deletes pod shortly after containers ready during rollout maxSurge maxUnavailable
- [Kubernetes Deployments: A Guide to the Rolling Update Deployment Strategy - Semaphore](https://semaphore.io/blog/kubernetes-rolling-update-deployment) — Meanwhile, the pods from the old `replicaSet` are still running, ensuring service availability during the update. As the new `replicaSet` pods go into a Running state alongside the old `replicaSet` pods, this overlap becomes a critical phase. During this time, Kubernetes uses the `minReadySeconds` parameter to provide a buffer, ensuring the new version is fully operational and ready to take over from the old version, thereby maintaining continuous availability.

Then the appearance of another new pod entering the `Running` state while the old pods are no longer listed indicates the rolling update is proceeding to replace all old pods with new ones. [...] Finally, all pods from the initial deployment are been replaced with pods from the new `replicaSet`, all running and ready to receive traffic. You can confirm this using the following command:

```
kubectl get replicasets  

```

This confirms the completion of the rolling update, with the entire set of desired replicas now running the updated application version.

Execute the following command to see the status of the rolling update:

```
kubectl rollout status deployment/nginx-deployment
```

This will display the real-time progress of the update, indicating when the rollout is complete or if there are any errors. However, right now, you should have the following output: [...] First, we get a message indicating that the deployment image update is applied, signaling the initiation of a rolling update process for the `nginx-deployment`. Here Kubernetes starts to replace the old pods (old `replicaSets`) with new ones (new `replicaSets`), leveraging the specified `maxSurge` and `maxUnavailable` settings to manage this transition.
- [Kubernetes Deployment Explained: API Resource, YAML Example, and Use Cases](https://www.devopsschool.com/blog/kubernetes-deployment-strategy-explained-with-example) — Title: Kubernetes Deployment Explained: API Resource, YAML Example, and Use Cases
# Kubernetes Deployment Explained: API Resource, YAML Example, and Use Cases. ## Fearture of Kubernetes Deployment. Can be “Recreate” or “RollingUpdate”. .spec.strategy specifies the strategy used to replace old Pods by new ones. .spec.strategy.type can be “Recreate” or “RollingUpdate”. All existing Pods are killed before new ones are created when .spec.strategy.type==Recreate. If you upgrade a Deployment, all Pods of the old revision will be terminated immediately. If you manually delete a Pod, the lifecycle is controlled by the ReplicaSet and the replacement will be created immediately (even if the old Pod is still in a Terminating state). ## Rolling Update Deployment. The advantage of the rolling update strategy is that the update is applied Pod-by-Pod so the greater system can remain active. There is a minor performance reduction during this update process because the system is consistently one active Pod short of the desired number of Pods. The rolling update strategy is used as the default update strategy but isn’t suited for all situations. `The Deployment updates Pods in a rolling update fashion when .spec.strategy.type==RollingUpdate. You can specify maxUnavailable and maxSurge to control the rolling update process. The maximum number of pods that can be scheduled above the desired number. Value can be an absolute number (ex: 5) or a percentage of desired. when this is set to 30%, the new ReplicaSet can be scaled up immediately. when the rolling update starts, such that the total number of old and new. new ReplicaSet can be scaled up further, ensuring that total number of pods. running at any time during the update is at most 130% of desired pods. The maximum number of pods that can be unavailable during the update. can be an absolute number (ex: 5) or a percentage of desired pods (ex:. to 30%, the old ReplicaSet can be scaled down to 70% of desired pods. during the update is at least 70% of desired pods.`. ## kubernetes deployment strategy example: Recreate. ## kubernetes deployment strategy example: Rollingupdate. ## Kubernetes ConfigMap Explained: API Resource, YAML Example, and Use Cases. ## Kubernetes ReplicaSet Explained: API Resource, YAML Example, and Use Cases. ## Kubernetes ReplicationController Explained: API Resource, YAML Example, and Use Cases.
- [Kubernetes Rolling Update: Deploy Without Service Interruption | SFEIR Institute](https://institute.sfeir.com/en/kubernetes-training/rolling-update-kubernetes-deploy-zero-downtime) — ### Required Environment

| Component | Minimum Version | Verification Command |
 --- 
| kubectl | v1.28+ | `kubectl version --client` |
| Kubernetes Cluster | v1.28+ | `kubectl version` |
| Existing Deployment  `kubectl get deployments` |

`kubectl version --client`
`kubectl version`
`kubectl get deployments`
`kubectl version --client
# Expected output:
# Client Version: v1.29.0
# Kustomize Version: v5.0.4-0.20230601165947-6ce0bf390ce3`

### Prior Knowledge

You should understand:

## Step 1: Understand the Rolling Update Mechanism

A rolling update is a Kubernetes progressive update strategy that replaces pods one by one. Kubernetes creates a new ReplicaSet, starts pods with the new version there, then progressively terminates pods from the old ReplicaSet. [...] ## Troubleshooting Common Errors

Rolling updates can fail for several reasons. Identify and resolve these problems quickly.

### Pods Stuck in ImagePullBackOff

`kubectl get pods -l app=webapp
# Problem detected:
# NAME READY STATUS RESTARTS AGE
# webapp-7d4f5b8c9-abc12 0/1 ImagePullBackOff 0 2m`

Solution: Verify the image name and tag, as well as registry credentials.

`kubectl describe pod webapp-7d4f5b8c9-abc12 | grep -A 5 "Events"`

### Deployment Stuck: Readiness Probe Fails

`kubectl rollout status deployment/webapp
# Problem detected:
# Waiting for deployment "webapp" rollout to finish: 1 old replicas are pending termination...`

Old pods don't terminate because new ones never reach Ready state.

Solution: Check your readiness probe configuration and application logs.
- [Kubernetes/Deployment, ReplicaSet and Pod - Ever changing code](http://wiki.ciscolinux.co.uk/index.php/Kubernetes/Deployment,_ReplicaSet_and_Pod) — # Kubernetes/Deployment, ReplicaSet and Pod. Jump to navigation Jump to search. $ kubectl get all -owide -n sample-app NAME READY STATUS RESTARTS AGE IP NODE NOMINATED NODE READINESS GATES pod/sample-deployment-6c5948bf66-5bqhw 1/1 Running 0 114s 10.244.2.10 ip-10-0-1-102 pod/sample-deployment-6c5948bf66-t5vg5 1/1 Running 0 114s 10.244.1.11 ip-10-0-1-103 pod/sample-deployment-6c5948bf66-xv6cb 1/1 Running 0 114s 10.244.1.10 ip-10-0-1-103 NAME READY UP-TO-DATE AVAILABLE AGE CONTAINERS IMAGES SELECTOR deployment.apps/sample-deployment 3/3 3 3 114s nginx-container nginx:1.12 app=sample-app NAME DESIRED CURRENT READY AGE CONTAINERS IMAGES SELECTOR replicaset.apps/sample-deployment-6c5948bf66 3 3 3 114s nginx-container nginx:1.12 app=sample-app,pod-template-hash=6c5948bf66. Deployment creates a ReplicaSet, that manages a number of Pods. kubectl create -f kubeapp-deployment.yaml --record # records in a revision history, so it's easy to rollback kubectl rollout status deployments kubeapp # check the status of the rollout deployment "kubeapp" successfully rolled out kubectl get replicasets # name is with appended NAME DESIRED CURRENT READY AGE kubeapp-674dd4d9cd 3 3 3 93s kubectl get pods # name is with appended NAME READY STATUS RESTARTS AGE kubeapp-674dd4d9cd-f2rk8 1/1 Running 0 3m36s kubeapp-674dd4d9cd-gnq7v 1/1 Running 0 5m51s kubeapp-674dd4d9cd-kc6lt 1/1 Running 0 3m37s. #Run this curl look while the update happens: while true; do curl done #Perform the rolling update: kubectl set image deployments/kubeapp app=nginx:1.17.1 --v 6 #--v verbose output #Find that new ReplicaSet has been created kubectl describe replicasets kubeapp-[hash] kubectl get replicasets NAME DESIRED CURRENT READY AGE kubeapp-674dd4d9cd 0 0 0 43m kubeapp-99c897449 0 0 0 6m19s kubeapp-d79844ffd 3 3 3 14m #new deployment #Look at the rollout history kubectl rollout history deployment kubeapp deployment.extensions/kubeapp REVISION CHANGE-CAUSE 3 kubectl create --filename=kubeapp-deployment.yaml --record=true 4 #this is empty because no --record was set during kubectl execution 5 kubectl create --filename=kubeapp-deployment.yaml --record=true. The history is stored with underlying RelicaSet. kubectl rollout undo deployment kubeapp --to-revision=2 #specific version if needed kubectl rollout undo deployments kubeapp #this has been applied kubectl get replicasets NAME DESIRED CURRENT READY AGE kubeapp-674dd4d9cd 0 0 0 46m kubeapp-99c897449 3 3 3 8m52s #rolled back to previous replicaset kubeapp-d79844ffd 0 0 0 16m #Pause the rollout in the middle of a rolling update (canary release) kubectl rollout pause deployment kubeapp #Resume the rollout after the rolling update looks good kubectl rollout resume deployment kubeapp.
- [Kubernetes Deployment Not Updating: Causes, Fixes & Insights](https://www.groundcover.com/learn/kubernetes/deployment-not-updating) — Once the process is complete and all new Pods are running and healthy (a state checked using their Readiness Probes), the update is considered successful. The old ReplicaSet remains in the cluster, scaled to zero, preserving the revision history and enabling instant rollbacks.

## What "Deployment Not Updating" Means in Kubernetes [...] ### RollingUpdate (The Default)

The RollingUpdate strategy is the default and preferred method, designed for zero-downtime deployments. When a new Pod template is detected:

 The Deployment Controller creates a new ReplicaSet reflecting the updated configuration.
 The Deployment scales up the new ReplicaSet (creating new Pods) while simultaneously scaling down the old ReplicaSet (terminating old Pods).

This gradual, synchronized exchange continues until the new ReplicaSet reaches the desired replica count and the old one is scaled down to zero. Two parameters control the pacing:

 maxSurge: The maximum number of Pods allowed above the desired replica count during the update.
 maxUnavailable: The maximum number of Pods that can be unavailable during the update.

### Recreate
- [liveness/readiness probe is executed and failed while pod is terminated · Issue #52817 · kubernetes/kubernetes · GitHub](https://github.com/kubernetes/kubernetes/issues/52817) — #98571

Copy link

Assignees

ashleyschuettmatthyx

Labels

area/kubeletkind/bugCategorizes issue or PR as related to a bug.Categorizes issue or PR as related to a bug.priority/important-soonMust be staffed and worked on either currently, or very soon, ideally in time for the next release.Must be staffed and worked on either currently, or very soon, ideally in time for the next release.sig/nodeCategorizes an issue or PR as relevant to SIG Node.Categorizes an issue or PR as relevant to SIG Node.

## Description

@sunao-uehara

sunao-uehara

opened on Sep 20, 2017

Issue body actions

What happened:  
 liveness/readiness probe fails while pod is terminated. Also it happened only once during the pod termination. The issue started happening after upgrading version to v1.7 from v1.6.X [...] How to reproduce it (as minimally and precisely as possible):  
 execute `kubectl delete pod nginx-A1` to delete pod, so status of the nginx-podA1 is changed to `Terminating`, right after that it seems Liveness and Readiness Probe is executed and failed, but only once.  
 Nginx reverse proxy is running in the pod. so I just use `httpGet`method for liveness and readiness

Here is my Deployment config.

```
... spec terminationGracePeriodSeconds 60... livenessProbe httpGet path/healthz port 8080 initialDelaySeconds 15 timeoutSeconds 3 readinessProbe httpGet path/healthz port 8080 initialDelaySeconds 15 timeoutSeconds 3
```

Here is Events log by `kubectl describe pod nginx-A1` [...] Skip to content   
 
 

## Navigation Menu

Sign in

Appearance settings

Sign in

Sign up

Appearance settings

You signed in with another tab or window. Reload to refresh your session. You signed out in another tab or window. Reload to refresh your session. You switched accounts on another tab or window. Reload to refresh your session. Dismiss alert

{{ message }}

kubernetes   /  kubernetes  Public

 Notifications  You must be signed in to change notification settings
 Fork 46.1k
 Star  128k

# liveness/readiness probe is executed and failed while pod is terminated #52817

Copy link

Copy link

Closed

#98571

Closed

liveness/readiness probe is executed and failed while pod is terminated#52817

#98571

Copy link

Assignees

ashleyschuettmatthyx

Labels
- [Liveness, Readiness, and Startup Probes | Kubernetes](https://kubernetes.io/docs/concepts/workloads/pods/probes) — `Success`
:   The container passed the diagnostic.

`Failure`
:   The container failed the diagnostic. For liveness and startup probes, the kubelet kills the container, and the container is subjected to its restart policy. For readiness probes, the kubelet marks the container as not ready, and the Pod stops receiving traffic from matching Services.

`Unknown`
:   The diagnostic failed (no action should be taken, and the kubelet will make further checks).

If a container does not provide a particular probe, the kubelet always considers the result as `Success`. For readiness probes specifically, the result is considered `Failure` before the initial delay.

## Configuration fields [...] spec: spec: spec:   terminationGracePeriodSeconds: 3600 # pod-level  terminationGracePeriodSeconds: 3600 # pod-level  terminationGracePeriodSeconds:  3600  # pod-level   containers:  containers:  containers:   - name: test  - name: test  name:  test   image: ...  image: ...  image:  ...      ports:  ports:  ports:   - name: liveness-port  - name: liveness-port  name:  liveness-port   containerPort: 8080  containerPort: 8080  containerPort:  8080      livenessProbe:  livenessProbe:  livenessProbe:   httpGet:  httpGet:  httpGet:   path: /healthz  path: /healthz  path:  /healthz   port: liveness-port  port: liveness-port  port:  liveness-port   failureThreshold: 1  failureThreshold: 1  failureThreshold:  1   periodSeconds: 60  periodSeconds: 60  periodSeconds:  60   # Override pod-level [...] `failureThreshold`
:   After a probe fails `failureThreshold` times in a row, Kubernetes considers that the overall check has failed: the container is not ready/healthy/live. Defaults to 3. Minimum value is 1. For the case of a startup or liveness probe, if at least `failureThreshold` probes have failed, Kubernetes treats the container as unhealthy and triggers a restart for that specific container. The kubelet honors the setting of `terminationGracePeriodSeconds` for that container. For a failed readiness probe, the kubelet continues running the container that failed checks, and also continues to run more probes; because the check failed, the kubelet sets the `Ready` condition on the Pod to `false`.
- [Is probing of a Pod retried after a readiness probe fails](https://stackoverflow.com/questions/67963991/is-probing-of-a-pod-retried-after-a-readiness-probe-fails) — will the pod's readiness prob conditions checked again? yes, the condition will be checked again depends on the threshold you have set.
- [< Marvin> I am experiencing the following in Prefect 3 Since Prefect Community #ask-marvin](https://linen.prefect.io/t/33252122/ulva73b9p-i-am-experiencing-the-following-in-prefect-3-since) — PREFECT_INTEGRATIONS_KUBERNETES_OBSERVER_FORWARD_CRASHED_RUN_LOGS=false`
`livenessProbe:
exec: { command: ["sh","-c","pgrep -f prefect_kubernetes.observer >/dev/null"] }
initialDelaySeconds: 20
periodSeconds: 10
readinessProbe:
exec: { command: ["sh","-c","pgrep -f prefect_kubernetes.observer >/dev/null"] }
initialDelaySeconds: 10
periodSeconds: 10
resources:
requests: { cpu: "500m", memory: "512Mi" }
limits: { cpu: "2", memory: "2Gi" }`
`PREFECT_FLOW_RUN_EXECUTE_SIGTERM_BEHAVIOR=crash`
`spec.backoffLimit: 0`
`spec.activeDeadlineSeconds: <your wall clock limit>`
`template.spec.restartPolicy: Never`
`podFailurePolicy`
`job_manifest.spec.podFailurePolicy`
`PREFECT_SERVER_SERVICES_EVENT_PERSISTER_BATCH_SIZE=20`
- [Kubernetes Pod Terminating: Troubleshooting | AlertMend AI](https://www.alertmend.io/blog/understanding-kubernetes-terminating-state) — Title: Kubernetes Pod Terminating: Troubleshooting | AlertMend AI
Kubernetes pods enter a "Terminating" state when deletion is initiated, allowing for graceful shutdown. # Check pod status during deletion kubectl get pods -w # Output shows progression: # NAME READY STATUS RESTARTS AGE # my-pod 1/1 Running 0 5m # my-pod 1/1 Terminating 0 5m # my-pod 0/1 Terminating 0 5m # (pod removed). # Check if processes are still running kubectl exec  -- ps aux # Check pod events kubectl describe pod  | grep -A 10 Events # Check container exit codes kubectl get pod  -o jsonpath='{.status.containerStatuses[*].lastState.terminated.exitCode}'. # Only if you're sure it's safe kubectl delete pvc  --force --grace-period=0 # Or patch PVC to remove finalizers kubectl patch pvc  -p '{"metadata":{"finalizers":[]}}'. # Delete pod with force kubectl delete pod  --grace-period=0 --force # Remove finalizers first if needed kubectl patch pod  -p '{"metadata":{"finalizers":[]}}' --type=merge kubectl delete pod  --grace-period=0 --force. # Check for finalizers kubectl get pod  -o jsonpath='{.metadata.finalizers}' # If finalizers exist, investigate why they're not clearing. # Try to exec into pod (may fail if terminating) kubectl exec  -- ps aux # Check container status kubectl get pod  -o jsonpath='{.status.containerStatuses[*]}'. # Remove finalizers kubectl patch pod  -p '{"metadata":{"finalizers":[]}}' # Verify pod is deleted kubectl get pod. # Force delete with grace period 0 kubectl delete pod  --grace-period=0 --force # If that doesn't work, remove finalizers first kubectl patch pod  -p '{"metadata":{"finalizers":[]}}' kubectl delete pod  --grace-period=0 --force. # Check if PVC has finalizers kubectl get pvc  -o jsonpath='{.metadata.finalizers}' # Remove PVC finalizers if safe kubectl patch pvc  -p '{"metadata":{"finalizers":[]}}' # Then delete pod kubectl delete pod  --grace-period=0 --force. # Force delete pod kubectl delete pod  --grace-period=0 --force # If node is permanently down, you may need to: # 1. # Force delete pod kubectl delete pod  --grace-period=0 --force # If pod has finalizers, remove them first kubectl patch pod  -p '{"metadata":{"finalizers":[]}}' --type=merge kubectl delete pod  --grace-period=0 --force. # Test graceful shutdown kubectl delete pod  # Verify it terminates within grace period kubectl get pod  -w. * **Automated Remediation**: Remove finalizers or force delete stuck pods when safe. # AlertMend monitors: - Pod termination status - Finalizers blocking deletion - Volume unmount issues - Process termination problems - Grace period violations. Pods stuck in Terminating state are common issues in Kubernetes clusters.
- [Deployments | Kubernetes](https://kubernetes.io/docs/concepts/workloads/controllers/deployment) — For example, when this value is set to 30%, the old ReplicaSet can be scaled down to 70% of desired Pods immediately when the rolling update starts. Once new Pods are ready, old ReplicaSet can be scaled down further, followed by scaling up the new ReplicaSet, ensuring that the total number of Pods available at all times during the update is at least 70% of the desired Pods.

##### Max Surge [...] #### Rolling Update Deployment

The Deployment updates Pods in a rolling update fashion (gradually scale down the old ReplicaSets and scale up the new one) when `.spec.strategy.type==RollingUpdate`. You can specify `maxUnavailable` and `maxSurge` to control the rolling update process.

##### Max Unavailable

`.spec.strategy.rollingUpdate.maxUnavailable` is an optional field that specifies the maximum number of Pods that can be unavailable during the update process. The value can be an absolute number (for example, 5) or a percentage of desired Pods (for example, 10%). The absolute number is calculated from percentage by rounding down. The value cannot be 0 if `.spec.strategy.rollingUpdate.maxSurge` is 0. The default value is 25%. [...] ```
  kubectl get pods kubectl get pods 
  ```

  The output is similar to this:

  ```
  NAME READY STATUS RESTARTS AGE nginx-deployment-1564180365-70iae 1/1 Running 0 25s nginx-deployment-1564180365-jbqqo 1/1 Running 0 25s nginx-deployment-1564180365-hysrc 1/1 Running 0 25s nginx-deployment-3066724191-08mng 0/1 ImagePullBackOff 0 6s 
  ```

  #### Note:

  The Deployment controller stops the bad rollout automatically, and stops scaling up the new ReplicaSet. This depends on the rollingUpdate parameters (`maxUnavailable` specifically) that you have specified. Kubernetes by default sets the value to 25%.
 Get the description of the Deployment:

  ```
  kubectl describe deployment kubectl describe deployment 
  ```

  The output is similar to this:
- [Kubernetes Deployment Not Updating: Causes, Fixes & Insights](https://www.groundcover.com/learn/kubernetes/deployment-not-updating) — ### RollingUpdate (The Default)

The RollingUpdate strategy is the default and preferred method, designed for zero-downtime deployments. When a new Pod template is detected:

 The Deployment Controller creates a new ReplicaSet reflecting the updated configuration.
 The Deployment scales up the new ReplicaSet (creating new Pods) while simultaneously scaling down the old ReplicaSet (terminating old Pods).

This gradual, synchronized exchange continues until the new ReplicaSet reaches the desired replica count and the old one is scaled down to zero. Two parameters control the pacing:

 maxSurge: The maximum number of Pods allowed above the desired replica count during the update.
 maxUnavailable: The maximum number of Pods that can be unavailable during the update.

### Recreate [...] Failing Readiness Probes: The most common cause of a hanging rollout is a failing Readiness Probe. The Deployment Controller will not consider the new Pod available, blocking the rollout from progressing past the maxUnavailable limit.  
  + Check/Fix: Review the probe configuration in the manifest. Use kubectl describe Pod  and look for explicit Readiness probe failed messages.
 Unchanged Pod Template Hash: If you change a configuration object (like a ConfigMap) but fail to update the Pod template (e.g., changing an annotation or an environment variable that references the ConfigMap's hash), the Deployment Controller won't create a new ReplicaSet.  
  + Check/Fix: The Pod's metadata must change. Ensure you have modified a field within the .spec.template of the Deployment.
- [Rollout Spec - Argo Rollouts - Kubernetes Progressive Delivery Controller](https://argo-rollouts.readthedocs.io/en/stable/features/specification) — the  # update. +optional  maxUnavailable:  1  # The maximum number of pods that can be scheduled above the original  # number of pods. Value can be an absolute number (ex: 5) or a  # percentage of total pods at the start of the update (ex: 10%). This  # can not be 0 if MaxUnavailable is 0. Absolute number is calculated  # from percentage by rounding up. By default, a value of 1 is used.  # Example: when this is set to 30%, the new RC can be scaled up by 30%  # immediately when the rolling update starts. Once old pods have been  # killed, new RC can be scaled up further, ensuring that total number  # of pods running at any time during the update is at most 130% of  # original pods. +optional  maxSurge:  '20%'  # Adds a delay before scaling down the previous ReplicaSet when the  # canary [...] do not use Rollout workloadRef property.  template:  spec:  containers:  -  name:  guestbook  image:  argoproj/rollouts-demo:blue  # Minimum number of seconds for which a newly created pod should be ready  # without any of its container crashing, for it to be considered available.  # Defaults to 0 (pod will be considered available as soon as it is ready)  minReadySeconds:  30  # The number of old ReplicaSets to retain.  # Defaults to 10  revisionHistoryLimit:  3  # Pause allows a user to manually pause a rollout at any time. A rollout  # will not advance through its steps while it is manually paused, but HPA  # auto-scaling will still occur. Typically not explicitly set in the manifest,  # but controlled via tools (e.g. kubectl argo rollouts pause). If true at  # initial creation of [...] attached to the stable pods  stableMetadata:  annotations:  role:  stable  labels:  role:  stable  # The maximum number of pods that can be unavailable during the update.  # Value can be an absolute number (ex: 5) or a percentage of total pods  # at the start of update (ex: 10%). Absolute number is calculated from  # percentage by rounding down. This can not be 0 if MaxSurge is 0. By  # default, a fixed value of 1 is used. Example: when this is set to 30%,  # the old RC can be scaled down by 30% immediately when the rolling  # update starts. Once new pods are ready, old RC can be scaled down  # further, followed by scaling up the new RC, ensuring that at least 70%  # of original number of pods are available at all times during the  # update. +optional  maxUnavailable:  1  # The maximum
- [How to Fine-Tune Rolling Update maxSurge and maxUnavailable Parameters](https://oneuptime.com/blog/post/2026-02-09-rolling-update-maxsurge-maxunavailable/view) — For critical applications that must maintain availability:

`apiVersion: apps/v1
kind: Deployment
metadata:
name: critical-api
spec:
replicas: 20
strategy:
type: RollingUpdate
rollingUpdate:
maxSurge: 1 # Add only 1 pod at a time
maxUnavailable: 0 # Do not reduce available pods during rollout
selector:
matchLabels:
app: critical-api
template:
metadata:
labels:
app: critical-api
spec:
containers:
- name: api
image: api:v2.0
ports:
- containerPort: 8080
resources:
requests:
memory: "512Mi"
cpu: "500m"
limits:
memory: "1Gi"
cpu: "1000m"
readinessProbe:
httpGet:
path: /ready
port: 8080
initialDelaySeconds: 10
periodSeconds: 5`

This configuration:

## Aggressive Update Strategy

For development environments or non-critical services: [...] apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
name: ha-service-pdb
spec:
minAvailable: 12 # Require at least 80% available for voluntary evictions
selector:
matchLabels:
app: ha-service`

## Monitoring Rolling Updates

Track update progress:

`# Watch rollout status
kubectl rollout status deployment/my-app
# Detailed rollout history
kubectl rollout history deployment/my-app
# View replica set scaling during update
kubectl get rs -w -l app=my-app`

Monitor with metrics: [...] For services requiring maximum uptime:

`apiVersion: apps/v1
kind: Deployment
metadata:
name: ha-service
spec:
replicas: 15
strategy:
type: RollingUpdate
rollingUpdate:
maxSurge: 3
maxUnavailable: 0
selector:
matchLabels:
app: ha-service
template:
metadata:
labels:
app: ha-service
spec:
affinity:
podAntiAffinity:
preferredDuringSchedulingIgnoredDuringExecution:
- weight: 100
podAffinityTerm:
labelSelector:
matchLabels:
app: ha-service
topologyKey: kubernetes.io/hostname
containers:
- name: service
image: ha-service:v2.0
readinessProbe:
httpGet:
path: /ready
port: 8080
initialDelaySeconds: 10
periodSeconds: 5
failureThreshold: 2
livenessProbe:
httpGet:
path: /healthz
port: 8080
initialDelaySeconds: 30
periodSeconds: 10
- [Understanding maxunavailable in rolling update ...](https://www.reddit.com/r/kubernetes/comments/wijn3c/understanding_maxunavailable_in_rolling_update) — maxUnavailable defines how many pods need to be ready for traffic at least during the rollout, while maxSurge limits the resource consumption