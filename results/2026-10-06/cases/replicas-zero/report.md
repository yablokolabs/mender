# Root cause: Checkout deployment scaled to zero replicas causing pod termination

Service `checkout` in namespace `shop`.

## Root cause
Deployment.spec.replicas is set to 0 in the manifest, which instructs Kubernetes to terminate all managed pods.

## Mechanism
The Deployment manifest (deploy.yaml) explicitly sets spec.replicas: 0. The ReplicaSet controller continuously reconciles actual pod count with desired replicas. Seeing 0 desired replicas, it selects all running pods for deletion, issuing SIGTERM (Killing events) and then removing them (SuccessfulDelete events). Pods were healthy — passing readiness/liveness probes and serving traffic — but are terminated because the control loop's target state is zero. This is expected Kubernetes behavior when scaling a Deployment to zero [1][3][5].

Confidence: 0.95 · Labels: replica_count_zero, deployment_scale_down, intentional_termination, manifest_misconfig

## Evidence relied on
- deploy.yaml: spec.replicas: 0
- EVENTS: Killing pod/checkout-d6f4887c4-m6f2g Stopping container checkout
- EVENTS: SuccessfulDelete Deleted pod: checkout-d6f4887c4-wmb7w
- PODS: Status: Terminating
- LOGS: continuous 200 healthz responses showing pods were healthy before termination

## Tavily sources
Queries: Kubernetes deployment replicas=0 pods immediately terminating after creation; Kubernetes replica set scales down to zero pods deleted SuccessfulDelete event; Kubernetes deployment zero replicas pod lifecycle termination behavior
- [Deployments | Kubernetes](https://kubernetes.io/docs/concepts/workloads/controllers/deployment) — For example, suppose you create a Deployment to create 5 replicas of `nginx:1.14.2`, but then update the Deployment to create 5 replicas of `nginx:1.16.1`, when only 3 replicas of `nginx:1.14.2` had been created. In that case, the Deployment immediately starts killing the 3 `nginx:1.14.2` Pods that it had created, and starts creating `nginx:1.16.1` Pods. It does not wait for the 5 replicas of `nginx:1.14.2` to be created before changing course.

### Label selector updates

It is generally discouraged to make label selector updates and it is suggested to plan your selectors up front. A Deployment's label selector is immutable after creation; it cannot be updated via `kubectl patch`, `kubectl edit`, `kubectl apply`, or tools like `helm upgrade`. [...] #### Note:

This will only guarantee Pod termination previous to creation for upgrades. If you upgrade a Deployment, all Pods of the old revision will be terminated immediately. Successful removal is awaited before any Pod of the new revision is created. If you manually delete a Pod, the lifecycle is controlled by the ReplicaSet and the replacement will be created immediately (even if the old Pod is still in a Terminating state). If you need an "at most" guarantee for your Pods, you should consider using a StatefulSet.

#### Rolling Update Deployment [...] ```
  NAME READY UP-TO-DATE AVAILABLE AGE nginx-deployment 3/3 3 3 36s 
  ```
 Run `kubectl get rs` to see that the Deployment updated the Pods by creating a new ReplicaSet and scaling it up to 3 replicas, as well as scaling down the old ReplicaSet to 0 replicas.

  ```
  kubectl get rs kubectl get rs 
  ```

  The output is similar to this:

  ```
  NAME DESIRED CURRENT READY AGE nginx-deployment-1564180365 3 3 3 6s nginx-deployment-2035384211 0 0 0 36s 
  ```
 Running `get pods` should now show only the new Pods:

  ```
  kubectl get pods kubectl get pods 
  ```

  The output is similar to this:
- [Troubleshoot Kubernetes Deployment ReplicaSet Stuck at Zero Available Replicas](https://oneuptime.com/blog/post/2026-02-09-replicaset-stuck-zero-replicas/view) — Fix by correcting the image reference or adding authentication.

`apiVersion: apps/v1
kind: Deployment
metadata:
name: myapp
spec:
selector:
matchLabels:
app: myapp
template:
metadata:
labels:
app: myapp
spec:
containers:
- name: app
image: myregistry.com/myapp:v1.0 # Correct image path
imagePullPolicy: IfNotPresent
imagePullSecrets:
- name: regcred # Add registry credentials`

## Resolving CrashLoopBackOff Issues

Pods that start but immediately crash indicate application or configuration problems. [...] Fix scheduling failures by adjusting resource requests.

`apiVersion: apps/v1
kind: Deployment
metadata:
name: myapp
spec:
replicas: 3
selector:
matchLabels:
app: myapp
template:
metadata:
labels:
app: myapp
spec:
containers:
- name: app
image: myapp:v1.0
resources:
requests:
cpu: "500m" # Reduced from 4 cores
memory: "1Gi" # Reduced from 16Gi
limits:
cpu: "1"
memory: "2Gi"`

Apply the fix.

`kubectl apply -f deployment.yaml
# Watch pod creation
kubectl get pods -n default -l app=myapp -w`

## Fixing Image Pull Errors

ImagePullBackOff prevents containers from starting. Check image configuration and registry access. [...] ## Identifying Zero Replica Deployments

Check Deployment status to confirm zero available replicas.

`# List deployments
kubectl get deployments -A
# Output showing problem:
# NAMESPACE NAME READY UP-TO-DATE AVAILABLE AGE
# default myapp 0/3 3 0 10m
# Get detailed Deployment information
kubectl describe deployment myapp -n default`

Check the ReplicaSet status.

`# Find ReplicaSet for Deployment
kubectl get replicaset -n default -l app=myapp
# Output:
# NAME DESIRED CURRENT READY AGE
# myapp-6f8d9c7b5 3 3 0 10m
# Describe ReplicaSet for events
kubectl describe replicaset myapp-6f8d9c7b5 -n default`

Check pod status to understand what's failing.
- [Kubectl Scale Deployment to 0 | CloudBolt](https://www.cloudbolt.io/kubernetes-autoscaling/kubectl-scale-deployment-to-0) — ## Scaling a Kubernetes deployment to 0

Scaling a Kubernetes resource such as a deployment or stateful set to zero involves setting the number of replicas for that resource to zero. This action instructs Kubernetes to terminate all pods associated with the specified resource.

### Benefits of scaling to 0

Scaling to zero can offer significant benefits in a number of areas.

#### Cost savings [...] Scaling a deployment to 0 has several direct consequences:

 Application unavailability: The most immediate effect is that the application will no longer be accessible. All running instances (pods) of the application will be terminated, so no new requests can be processed.
 Service disruption: Any ongoing sessions or connections will be immediately terminated. This could lead to a poor user experience if not managed carefully.
 Impact on state and data: For stateless applications, scaling to 0 is straightforward. However, for stateful applications, it’s important to ensure that the state is preserved, if necessary. This might involve persisting data to external storage before scaling down to avoid data loss.

## The HPA limitation when scaling deployment to 0 [...] ## The HPA limitation when scaling deployment to 0

The Horizontal Pod Autoscaler (HPA) automatically adjusts the number of replicas in a deployment, replica set, or stateful set based on observed and configured metrics. However, there is a limitation when it comes to scaling a Kubernetes deployment to zero.

Tha HPA usually operates based on metrics like CPU utilization or custom metrics from the running pods. When the deployment is scaled to zero replicas, there are no active pods to provide these metrics. As a result, the HPA cannot make decisions about scaling up from zero. This means that HPA requires a minimum of one replica to be running, so it cannot be used to completely shut down an application.
- [Kubernetes pod gets recreated when deleted](https://stackoverflow.com/questions/40686151/kubernetes-pod-gets-recreated-when-deleted) — There is basically two ways to remove PODS kubectl scale --replicas=0. This will set the number of replica to 0 and hence it will not restart
- [When scale replicas==0, do K8s send SIGTERM? - General Discussions - Discuss Kubernetes](https://discuss.kubernetes.io/t/when-scale-replicas-0-do-k8s-send-sigterm/11838) — `terminationGracePeriodSeconds`

For a detailed explanation of the process and how to modify it, checkout the Termination of Pods section of the docs.

This SIGTERM and SIGKILL is when we are talking about:

`kubectl delete...`

`kubectl delete...`

But when we are talking about set replicas==0, I don’t think it will be the same, right?

What K8s do behind the wall? He just stop serving?

replicas == 0 scales it down to 0, deleting the running pods.

So, all the prehook stop and so on will be called!?

Hmm… So I’ll need to check why my application is not being gracefully shutdown…

Thanks!

Correct - there’s nothing hidden - “delete pod” happens in both paths.

When we do --replicas=0 that means it will repeat or treat same as delete process? [...] It will delete the pod. There’s only one delete.

DELETE request ----send----- API server  
API server ------set deletionTimestamp ------ Pod  
Kubelet ----------observe this settings on-------- Pod  
Kubelet started to terminate Pod.  
I draw a deletion process arch. can you correct me is it right or may be need more integration added?

### Related topics
- [Scale Kubernetes Pods to Zero, Without Cold Starts](https://loopholelabs.io/blog/scale-to-zero) — Many discussions make it appear as if scaling pods to zero is a solved problem and operates as simply as the light switch. This is misleading at best. Sure Kubernetes has had the primitives and vendors have made promises for years now. You set up an autoscaler, traffic drops, pods disappear, your bill shrinks. Simple, right?

Except it is not simple, because scale to zero has a dirty secret in many cases: the moment traffic returns, you are starting an application from scratch. Your pods have been deleted. Kubernetes has to reschedule them onto a node, pull the container image, run init containers, wait for the application runtime to initialize or database cache to be warmed up, and serve a health check before a single request gets through. [...] Deletion-based scale-to-zero treats pods as disposable. Every wake cycle is a full pod creation: schedule, pull, init, boot. The cold start latency is baked into the architecture. For stateless micro-services with fast boot times this is sometimes acceptable. For anything stateful, JVM-based, or with meaningful initialization logic, it is not. [...] Architect does not delete pods. It hibernates them.

When a pod has been idle (for a configurable duration), Architect checkpoints the running container and preserves its execution state to local node storage, and reduces the pod's resource requests to zero. The pod remains registered with the Kubernetes API, stays attached to its Services, and keeps its PVCs mounted. This subtle difference between a hibernated pod and a deleted pod is actually quite important because from Kubernetes' perspective the pod still exists but from the node's perspective it is consuming no CPU or memory.

If this sounds like much better bin packing, that's because it is.
- [When scale replicas==0, do K8s send SIGTERM? - General Discussions - Discuss Kubernetes](https://discuss.kubernetes.io/t/when-scale-replicas-0-do-k8s-send-sigterm/11838) — `terminationGracePeriodSeconds`

For a detailed explanation of the process and how to modify it, checkout the Termination of Pods section of the docs.

This SIGTERM and SIGKILL is when we are talking about:

`kubectl delete...`

`kubectl delete...`

But when we are talking about set replicas==0, I don’t think it will be the same, right?

What K8s do behind the wall? He just stop serving?

replicas == 0 scales it down to 0, deleting the running pods.

So, all the prehook stop and so on will be called!?

Hmm… So I’ll need to check why my application is not being gracefully shutdown…

Thanks!

Correct - there’s nothing hidden - “delete pod” happens in both paths.

When we do --replicas=0 that means it will repeat or treat same as delete process? [...] It will delete the pod. There’s only one delete.

DELETE request ----send----- API server  
API server ------set deletionTimestamp ------ Pod  
Kubelet ----------observe this settings on-------- Pod  
Kubelet started to terminate Pod.  
I draw a deletion process arch. can you correct me is it right or may be need more integration added?

### Related topics [...] ### Related topics

| Topic |  | Replies | Views | Activity |
 ---  --- 
| Application still receives requests after SIGTERM  General Discussions network | 1 | 467 | December 6, 2023 |
| Know whether pod deletion is triggered by scaling down  General Discussions | 0 | 673 | July 3, 2019 |
| Pod End of Life: Still serving after sigterm?  General Discussions development | 4 | 3439 | December 13, 2022 |
| Deployments scaling down without user intervention  General Discussions | 0 | 1013 | April 12, 2021 |
| Replica down  General Discussions | 1 | 453 | April 15, 2022 |

Powered by Discourse, best viewed with JavaScript enabled
- [ReplicaSet | Kubernetes](https://kubernetes.io/docs/concepts/workloads/controllers/replicaset) — ### Scaling a ReplicaSet

A ReplicaSet can be easily scaled up or down by simply updating the `.spec.replicas` field. The ReplicaSet controller ensures that a desired number of Pods with a matching label selector are available and operational.

When scaling down, the ReplicaSet controller chooses which pods to delete by sorting the available pods to prioritize scaling down pods based on the following general algorithm: [...] Pods that become terminating due to deletion or scale down may take a long time to terminate, and may consume additional resources during that period. As a result, the total number of all pods can temporarily exceed `.spec.replicas`. Terminating pods can be tracked using the `.status.terminatingReplicas` field of the ReplicaSet.

### Isolating Pods from a ReplicaSet

You can remove Pods from a ReplicaSet by changing their labels. This technique may be used to remove Pods from service for debugging, data recovery, etc. Pods that are removed in this way will be replaced automatically ( assuming that the number of replicas is not also changed).

### Scaling a ReplicaSet [...] ### Deleting just a ReplicaSet

You can delete a ReplicaSet without affecting any of its Pods using `kubectl delete` with the `--cascade=orphan` option. When using the REST API or the `client-go` library, you must set `propagationPolicy` to `Orphan`. For example:
- [The Ultimate Guide to `kubectl scale deployment`](https://www.plural.sh/blog/kubectl-scale-deployment-guide) — ## Should You Scale Deployments to Zero Replicas?

Scaling a deployment to zero replicas is a deliberate action that terminates all pods managed by that deployment while preserving the deployment object itself. This effectively pauses the application without deleting its configuration, allowing you to bring it back online quickly by scaling the replica count back up. While it might seem counterintuitive to intentionally take a service offline, this technique has several practical applications, particularly for managing costs and controlling non-production environments.
- [Kubernetes: how to scale my pods](https://stackoverflow.com/questions/38344896/kubernetes-how-to-scale-my-pods) — Copy

```yaml
34s       34s     1   {replicaset-controller }            Normal      SuccessfulCreate    Created pod: my-nginx-1908062973-lylsz
  34s       34s     1   {replicaset-controller }            Normal      SuccessfulCreate    Created pod: my-nginx-1908062973-5rv8u
  34s       34s     1   {replicaset-controller }            Normal      SuccessfulDelete    Deleted pod: my-nginx-1908062973-lylsz
  34s       34s     1   {replicaset-controller }            Normal      SuccessfulDelete    Deleted pod: my-nginx-1908062973-5rv8u
```

   kubernetes

Share

Share a link to this question 

Copy linkCC BY-SA 3.0

Short permalink to this question

Improve this question

 Follow 

Follow this question to receive notifications

edited Jul 13, 2016 at 13:23

 asked Jul 13, 2016 at 7:11
- [Understanding the Kubernetes Pod Lifecycle and Graceful Shutdown](https://medium.com/@sharathkumarlokesh/understanding-the-kubernetes-pod-lifecycle-and-graceful-shutdown-acd5a56fce06) — _Pod termination and transition events._

Understanding the Pod lifecycle in Kubernetes is essential if you want reliable applications and zero-downtime deployments.

Let’s break down how Pods actually behave from creation to termination — and why graceful shutdown matters so much.

## First: Pods Are Ephemeral

This is one of the most important Kubernetes concepts.

Pods are not permanent machines.

They are:

_Disposable runtime instances._

Kubernetes may terminate Pods because of:

   Deployments
   Node failures
   Scaling events
   Resource pressure
   Evictions
   Maintenance operations

Applications must be designed with this reality in mind.

## The High-Level Pod Lifecycle

A Pod typically moves through these phases: [...] Think of Kubernetes Pod lifecycle like a hotel stay:

   Pending → Check-in process
   Running → Guest occupying room
   Ready → Guest available for meetings
   Terminating → Checkout process
   Graceful shutdown → Allowing guest to pack before leaving

Kubernetes is constantly managing transitions —   
not just runtime.

## Final Takeaway

Understanding the Pod lifecycle is fundamental to running reliable Kubernetes systems.

Because production stability depends heavily on:

   Startup behavior
   Traffic readiness
   Graceful shutdown
   Controlled termination

Applications that handle lifecycle transitions correctly become:

   Easier to deploy
   Easier to scale
   Easier to recover
   Far more resilient

And in Kubernetes: [...] Typical rollout flow:

New Pod starts  
↓  
Readiness succeeds  
↓  
Traffic shifts  
↓  
Old Pod begins graceful shutdown  
↓  
Termination completes
This choreography enables:

_Zero-downtime deployments._

## CrashLoopBackOff: Lifecycle Gone Wrong

One of the most common Pod lifecycle problems.

Meaning:

   Container repeatedly crashes
   Kubernetes repeatedly restarts it

Typical causes:

   Application errors
   Bad probes
   Missing configs
   Startup failures

## Real Example

Liveness probe too aggressive:

Startup time = 60s  
Probe timeout = 10s
Kubernetes thinks app is dead:

   Restarts continuously

This creates:

CrashLoopBackOff
## Best Practices That Actually Matter

## Handle SIGTERM Properly

Applications should:
- [Best Practices for Scaling Kubernetes Pods to Zero with ...](https://devgex.com/en/article/00021246) — This command controls the number of running pods by modifying the replicas field of deployment resources. When set to 0, the Kubernetes controller gradually terminates all running pod instances while preserving complete deployment configurations. The traditional command format is: kubectl scale deployment <deployment-name> --replicas=0.
- [Exploring the Termination Process in Kubernetes – IT Exams Training – Pass4Sure](https://www.pass4sure.com/blog/exploring-the-termination-process-in-kubernetes) — Termination is a natural part of a Pod’s lifecycle. Ideally, it should be brief, allowing the container to shut down gracefully while Kubernetes releases resources and updates cluster state. However, there are times when this termination phase extends indefinitely, leaving the Pod stuck and unresponsive. This behavior not only leads to resource leaks but also impairs the broader functionality of the system by preventing new Pods from being scheduled or updated correctly.

Understanding why a Pod might enter and remain in this liminal state is critical. The root causes are often subtle, tied to misconfigurations, timing issues, or overlooked design decisions. Addressing the problem demands both insight into Kubernetes internals and practical troubleshooting techniques. [...] This ensures:

 Application availability is preserved during maintenance
 Rolling updates happen gradually and safely
 Auto-scaling and node draining events do not overload services

Setting a conservative disruption budget aligns with production uptime requirements and reduces the likelihood of unintended terminations causing service degradation.

## Improving Observability Around Termination Behavior

One of the most effective long-term strategies to avoid stuck Pods is to monitor termination behavior as a first-class metric. Kubernetes generates several useful events during Pod deletion, including:

 Termination signals sent
 Hook execution results
 Exit codes and error messages
 Grace period expiration warnings [...] If orphaned processes are already present and causing termination delays, manual cleanup may be necessary. This could involve logging into the node where the Pod was scheduled, identifying the lingering processes, and terminating them directly. Use this approach with care and only when you are confident about the scope and identity of the rogue processes.

## Monitoring Termination Metrics in Real-Time

While manual interventions provide immediate relief, monitoring long-term trends in Pod termination behaviors helps in proactively addressing future incidents. Kubernetes emits events and metrics related to lifecycle transitions, including termination signals, hook execution time, and container exits.
- [Kubectl Scale Deployment to 0 | CloudBolt](https://www.cloudbolt.io/kubernetes-autoscaling/kubectl-scale-deployment-to-0) — ## Scaling a Kubernetes deployment to 0

Scaling a Kubernetes resource such as a deployment or stateful set to zero involves setting the number of replicas for that resource to zero. This action instructs Kubernetes to terminate all pods associated with the specified resource.

### Benefits of scaling to 0

Scaling to zero can offer significant benefits in a number of areas.

#### Cost savings [...] ## The HPA limitation when scaling deployment to 0

The Horizontal Pod Autoscaler (HPA) automatically adjusts the number of replicas in a deployment, replica set, or stateful set based on observed and configured metrics. However, there is a limitation when it comes to scaling a Kubernetes deployment to zero.

Tha HPA usually operates based on metrics like CPU utilization or custom metrics from the running pods. When the deployment is scaled to zero replicas, there are no active pods to provide these metrics. As a result, the HPA cannot make decisions about scaling up from zero. This means that HPA requires a minimum of one replica to be running, so it cannot be used to completely shut down an application.
- [When scale replicas==0, do K8s send SIGTERM? - General Discussions - Discuss Kubernetes](https://discuss.kubernetes.io/t/when-scale-replicas-0-do-k8s-send-sigterm/11838) — `terminationGracePeriodSeconds`

For a detailed explanation of the process and how to modify it, checkout the Termination of Pods section of the docs.

This SIGTERM and SIGKILL is when we are talking about:

`kubectl delete...`

`kubectl delete...`

But when we are talking about set replicas==0, I don’t think it will be the same, right?

What K8s do behind the wall? He just stop serving?

replicas == 0 scales it down to 0, deleting the running pods.

So, all the prehook stop and so on will be called!?

Hmm… So I’ll need to check why my application is not being gracefully shutdown…

Thanks!

Correct - there’s nothing hidden - “delete pod” happens in both paths.

When we do --replicas=0 that means it will repeat or treat same as delete process?