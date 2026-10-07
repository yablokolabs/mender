# Root cause: Checkout service pods terminating during overlapping rolling updates

Service `checkout` in namespace `shop`.

## Root cause
Rapid successive deployment updates caused overlapping rolling updates, terminating pods from two previous replica sets while they were still healthy.

## Mechanism
1. Deployment updated to revision b4dfc8f77 (pod-template-hash=b4dfc8f77) at ~17:00:24, creating new pods. 2. Before that rollout completed, a second update to revision 9c78769bf (pod-template-hash=9c78769bf) was applied at ~17:00:41, creating another pod set. 3. The new 9c78769bf pods passed readiness probes (events show SuccessfulCreate, Started, Ready=True). 4. The deployment controller then terminated pods from both previous replica sets (b4dfc8f77 and 9f49f8b65) because they were no longer needed, even though they still reported Ready=True. 5. Terminating pods remain in Ready=True state until the termination grace period expires, which is normal Kubernetes rolling update behavior [1][2].

Confidence: 0.90 · Labels: rolling_update, rapid_successive_updates, terminating_pods_ready, normal_behavior, false_alarm

## Evidence relied on
- Status: Terminating (lasts <invalid>) for checkout-9f49f8b65-*, checkout-b4dfc8f77-*
- Ready: True for all terminating pods
- Events: Killing pod/checkout-b4dfc8f77-zdqzm, SuccessfulDelete replicaset/checkout-b4dfc8f77
- Events: SuccessfulCreate replicaset/checkout-9c78769bf, Started pod/checkout-9c78769bf-glzqr
- Logs: healthz 200 responses from pods of all three replica sets

## Tavily sources
Queries: Kubernetes rolling update race condition pods terminating while Ready=true liveness readiness probe; Kubernetes deployment rollout pods killed despite passing health checks termination grace period; Kubernetes ReplicaSet deletion race condition pod terminating ready status true known issue
- [Kubernetes Health Probes: Liveness, Readiness, and Startup ...](https://dev.to/toothbrush/kubernetes-health-probes-liveness-readiness-and-startup-explained-5app) — Jul 21, 2026 · Readiness probes also control rolling update behavior. During a deployment, Kubernetes waits for the new pod's readiness probe to pass before terminating the old pod.
- [Kubernetes Rolling Update Configuration](https://www.bluematador.com/blog/kubernetes-deployments-rolling-update-configuration) — ## Ready Pods in Kubernetes

Deployments implement the concept of ready pods to aide rolling updates. Readiness probes allow the deployment to gradually update pods while giving you the control to determine when the rolling update can proceed; it is also used by Services to determine which pods should be included in a service’s endpoints. Readiness probes are similar to, but not the same as liveness probes. Liveness probes allow the kubelet to determine which pods need to be restarted according to their Restart Policy, and they are configured separate from readiness probes. They do not impact the update process for Deployments. [...] This strategy says that we want to add pods one at a time, and that there must always be 3 pods ready in the deployment. The following gif will illustrate what happens in every step of the rolling update. Pods are marked as Ready if the Deployment sees them as fully deployed, NotReady if they are being created, and Terminating if they are being removed.

## Ready Pods in Kubernetes [...] or a percentage (e.g. 50%), and they cannot both be zero. When specified as an integer, it represents the actual number of pods; when specifying a percentage, that percentage of the desired number of pods is used, rounded down. For example, If you were using the default values of 25% for both maxSurge and maxUnavailable, and applied an update to a Deployment with 8 pods, then maxSurge would be 2 pods, and maxUnavailable would also be 2 pods. That means that during the update process, the following conditions will be met:

 At most 10 pods (8 desired pods + 2 maxSurge pods) will be Ready during the update
 At least 6 pods (8 desired pods - 2 maxUnavailable pods) will always be Ready during the update
- [Kubernetes Rolling Updates Stalled by Readiness Probes](https://www.linkedin.com/posts/kshitijhatwar_kubernetes-devops-sre-activity-7459448463534137344-soS9) — Your rolling update is stuck. No new pods are ready. Old pods won't terminate. And Kubernetes is just... waiting.
- [Client is disconnected when the pod is terminating or fails the readiness probe - General Discussions - Discuss Kubernetes](https://discuss.kubernetes.io/t/client-is-disconnected-when-the-pod-is-terminating-or-fails-the-readiness-probe/19408) — # Client is disconnected when the pod is terminating or fails the readiness probe

Hi,

I’m managing one server on k8s which serves HTTP API consuming quite a long time to respond to it.  
Pods are deployed as `StatefulSet` and use `RollingUpdate` as an update strategy.  
Also, the type of service is `LoadBalancer`.  
For the maintenance, when I update my server, the pod should wait for all the requests to be responded before exiting. (I mean graceful shutdown.)

`StatefulSet`
`RollingUpdate`
`LoadBalancer`

I read following articles:

After I read them, my understanding about the process of pod termination is here:

`Terminating`
`LoadBalancer`
`preStop`
`SIGTERM`
`terminationGracePeriod`
`terminationGracePeriod`
`SIGKILL` [...] Is there any update on this?

To do that cleanly, we have open KEPs to track that intermediate state.

Do you have any links to these?

We’ve built an update recently on the assumption that in-progress connections would not be closed and they would be given some time to complete, so this has caught us out. It’s fair to say we made a mistake in our understanding, but it was also a “reasonable” assumption for connections to stay open, when phrasing like “remove the Pod from the list of endpoints” is used. If there have been any updates that might allow us to configure how this works, that would be extremely helpful. Or any suggested alternative solutions.

We’re using k8s version 1.29.1 (DigitalOcean’s DOKS).

Thank you. Any help will be much appreciated. [...] `Terminating`
`Not-Ready`

Thanks!

### Cluster information:

Kubernetes version: v1.15.10  
I’m sorry but, as I’m using the internal k8s platform in my company as I said above, the detailed cluster information is invisible to me.

Hi Junghoon:

From the Pod Lifecycle you’ve provided:

Pods that shut down slowly cannot continue to serve traffic as load balancers (like the service proxy) remove the Pod from the list of endpoints as soon as the termination grace period begins.

As the pod is removed as a valid endpoint, your client gets a `connection reset by peer`.

`connection reset by peer`

I am no developer, but regarding the 12 factor app
- [Kubernetes Rolling Update: Deploy Without Service Interruption | SFEIR Institute](https://institute.sfeir.com/en/kubernetes-training/rolling-update-kubernetes-deploy-zero-downtime) — ## Troubleshooting Common Errors

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

Solution: Check your readiness probe configuration and application logs. [...] ### Required Environment

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

A rolling update is a Kubernetes progressive update strategy that replaces pods one by one. Kubernetes creates a new ReplicaSet, starts pods with the new version there, then progressively terminates pods from the old ReplicaSet. [...] `maxSurge`

## Best Practices for Reliable Rolling Updates

| Practice | Reason | Configuration |
 --- 
| Readiness probes | Avoids routing to non-ready pods | `initialDelaySeconds: 10` |
| Resource requests | Guarantees scheduling | CPU and memory defined |
| PodDisruptionBudget | Protects availability | `minAvailable: 50%` |
| Graceful shutdown | Properly terminates connections | `terminationGracePeriodSeconds: 30` |

`initialDelaySeconds: 10`
`minAvailable: 50%`
`terminationGracePeriodSeconds: 30`

These configurations are part of the skills evaluated in the CKA certification. Teams spend 88% more each year on Kubernetes TCO (Spectro Cloud): investing in best practices reduces these costs.

## Take Action: Master Kubernetes Deployments
- [`kubectl rollout restart deployment`: The Right Way](https://www.plural.sh/blog/kubectl-rollout-restart-deployment) — ## Frequently Asked Questions

What happens if a new pod fails to become ready during a rollout restart? The deployment process will pause automatically. Kubernetes waits for new pods to pass their readiness probes before it continues the update and terminates old pods. If a new pod fails these health checks, the rollout will halt to prevent a faulty version from being fully deployed. You can then investigate the failing pod and decide whether to fix the issue or use `kubectl rollout undo` to revert to the previous stable version.

`kubectl rollout undo`
- [Kubernetes Deployment Strategies: Tutorial & Examples - Apptio](https://www.apptio.com/blog/kubernetes-deployment-strategy) — ```
❯ kubectl rollout status deploy/sample-app Waiting for deployment "sample-app" rollout to finish: 1 old replicas are pending termination... Waiting for deployment "sample-app" rollout to finish: 1 old replicas are pending termination... Waiting for deployment "sample-app" rollout to finish: 3 of 4 updated replicas are available... deployment "sample-app" successfully rolled out 
```

As you can see in the above outputs, v1 pods are gradually terminated as new v2 pods become available, passing health probes.

`kubectl get pod --watch`: Continuously watches for any pod status update

`kubectl rollout status deploy/sample-app`: Get deployment status for sample-app deployment

## Strategy #2—Canary Deployments
- [How to Configure Pod Termination Grace Period](https://oneuptime.com/blog/post/2026-01-25-pod-termination-grace-period/view) — ### Check Container Exit Code

`kubectl get pod myapp-pod -n production -o jsonpath='{.status.containerStatuses.lastState.terminated}'
# Exit codes:
# 0 - Normal exit (SIGTERM handled)
# 137 - SIGKILL (128 + 9)
# 143 - SIGTERM (128 + 15) - if not caught`

## Testing Graceful Shutdown

### Simulate Termination

`# Send SIGTERM to container process
kubectl exec myapp-pod -n production -- kill -SIGTERM 1
# Watch logs
kubectl logs myapp-pod -n production -f`

### Load Test During Rolling Update

`# Start load test
hey -z 2m -c 50 
# Trigger rolling update in another terminal
kubectl rollout restart deployment/myapp -n production
# Check for errors in load test output` [...] ### Set Grace Period Longer Than preStop + Shutdown Time

`# preStop: 15s
# App shutdown: 20s
# Buffer: 10s
terminationGracePeriodSeconds: 45`

## Debugging Termination Issues

### Check Termination Events

`kubectl get events --field-selector reason=Killing -n production`

### View Pod Termination

`# Watch pod status during termination
kubectl get pod myapp-pod -n production -w
# Check pod phase
kubectl get pod myapp-pod -n production -o jsonpath='{.status.phase}'`

### Force Delete Stuck Pods

`# Only use when pod is truly stuck
kubectl delete pod myapp-pod -n production --grace-period=0 --force`

### Check Container Exit Code
- [Deployments | Kubernetes](https://kubernetes.io/docs/concepts/workloads/controllers/deployment) — #### Note:

Kubernetes doesn't count terminating Pods when calculating the number of `availableReplicas`, which must be between `replicas - maxUnavailable` and `replicas + maxSurge`. As a result, you might notice that there are more Pods than expected during a rollout, and that the total resources consumed by the Deployment is more than `replicas + maxSurge` until the `terminationGracePeriodSeconds` of the terminating Pods expires.

### Rollover (aka multiple updates in-flight) [...] ```
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

  The output is similar to this: [...] To fix this, you need to rollback to a previous revision of Deployment that is stable.

### Checking Rollout History of a Deployment

Follow the steps given below to check the rollout history:

1. First, check the revisions of this Deployment:

   ```
   kubectl rollout history deployment/nginx-deployment kubectl rollout history deployment/nginx-deployment history
   ```

   The output is similar to this:

   ```
   deployments "nginx-deployment" REVISION CHANGE-CAUSE 1  2  3  
   ```

   `CHANGE-CAUSE` is copied from the Deployment annotation `kubernetes.io/change-cause` to its revisions upon creation. You can specify the`CHANGE-CAUSE` message by:
- [Exploring the Termination Process in Kubernetes – IT Exams Training – Pass4Sure](https://www.pass4sure.com/blog/exploring-the-termination-process-in-kubernetes) — There are two practical options to resolve the situation:

1. Wait until the hook completes, especially if it was intentionally designed to last for an extended period.
2. Forcefully terminate the Pod by overriding the grace period. This sends an immediate kill signal to the container and bypasses any remaining lifecycle events.

Use the second option only when data loss or incomplete shutdown is acceptable. Otherwise, it’s safer to diagnose and revise the logic of the preStop hook to ensure future instances don’t face the same issue.

## Force Deletion to Reclaim Resources [...] To prevent this, it’s advisable to use proper process management tools within containers. Lightweight init systems such as tini or dumb-init can help manage child processes effectively by catching signals and reaping orphans. Additionally, running containers in their own PID namespaces ensures that signal propagation and process isolation are enforced more strictly, reducing the risk of lingering operations.

## Forceful Termination and Its Trade-Offs

In critical cases, where normal termination stalls and all remediation steps fail, forceful termination becomes the only viable option. Kubernetes provides mechanisms to forcibly remove Pods by bypassing the grace period and issuing a kill command directly to the containers. [...] Termination is a natural part of a Pod’s lifecycle. Ideally, it should be brief, allowing the container to shut down gracefully while Kubernetes releases resources and updates cluster state. However, there are times when this termination phase extends indefinitely, leaving the Pod stuck and unresponsive. This behavior not only leads to resource leaks but also impairs the broader functionality of the system by preventing new Pods from being scheduled or updated correctly.

Understanding why a Pod might enter and remain in this liminal state is critical. The root causes are often subtle, tied to misconfigurations, timing issues, or overlooked design decisions. Addressing the problem demands both insight into Kubernetes internals and practical troubleshooting techniques.
- [ReplicaSet | Kubernetes](https://kubernetes.ac.cn/docs/reference/kubernetes-api/apps/replica-set-v1) — Title: ReplicaSet | Kubernetes
# ReplicaSet. ReplicaSet ensures that a specified number of pod replicas are running at any given time. `import "k8s.io/api/apps/v1"`. | `metadata` *ObjectMeta* | If the Labels of a ReplicaSet are empty, they are defaulted to be the same as the Pod(s) that the ReplicaSet manages. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#metadata |. | `spec` *ReplicaSetSpec* | Spec defines the specification of the desired behavior of the ReplicaSet. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status |. | `status` *ReplicaSetStatus* | Status is the most recently observed status of the ReplicaSet. This data may be out of date by some window of time. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status |. ReplicaSetSpec is the specification of a ReplicaSet. | `minReadySeconds` *integer* | Minimum number of seconds for which a newly created pod should be ready without any of its container crashing, for it to be considered available. Defaults to 0 (pod will be considered available as soon as it is ready) |. | `replicas` *integer* | Replicas is the number of desired pods. | `selector` **\*** *LabelSelector* | Selector is a label query over pods that should match the replica count. Label keys and values that must match in order to be controlled by this replica set. | `template` *PodTemplateSpec* | Template is the object that describes the pod that will be created if insufficient replicas are detected. More info: https://kubernetes.io/docs/concepts/workloads/controllers/replicaset/#pod-template |. ReplicaSetStatus represents the current status of a ReplicaSet. | `availableReplicas` *integer* | The number of available non-terminating pods (ready for at least minReadySeconds) for this replica set. | `conditions` *ReplicaSetCondition array* *patch strategy: merge on key `type`* | Represents the latest available observations of a replica set's current state. | `fullyLabeledReplicas` *integer* | The number of non-terminating pods that have labels matching the labels of the pod template of the replicaset. | `readyReplicas` *integer* | The number of non-terminating pods targeted by this ReplicaSet with a Ready Condition. | `replicas` **\*** *integer* | Replicas is the most recently observed number of non-terminating pods. | `terminatingReplicas` *integer* | The number of terminating pods for this replica set. ReplicaSetList is a collection of ReplicaSets. | `status` **\*** *string* | Status of the condition, one of True, False, Unknown. POST /apis/apps/v1/namespaces/{namespace}/replicasets. PATCH /apis/apps/v1/namespaces/{namespace}/replicasets/{name}.
- [Unable to delete pod in terminating state. : r/kubernetes](https://www.reddit.com/r/kubernetes/comments/1eb4lhc/unable_to_delete_pod_in_terminating_state) — Unable to delete pod in terminating state. I have deployed a deployment with replicaset of 1 using helm. There is a controller already
- [ReplicaSet | Kubernetes](https://v1-33.docs.kubernetes.io/docs/reference/kubernetes-api/workload-resources/replica-set-v1) — Title: ReplicaSet | Kubernetes
### You are viewing documentation for Kubernetes version: v1.33. # ReplicaSet. If the Labels of a ReplicaSet are empty, they are defaulted to be the same as the Pod(s) that the ReplicaSet manages. Spec defines the specification of the desired behavior of the ReplicaSet. More info:. Status is the most recently observed status of the ReplicaSet. This data may be out of date by some window of time. ReplicaSetSpec is the specification of a ReplicaSet. Selector is a label query over pods that should match the replica count. Label keys and values that must match in order to be controlled by this replica set. Template is the object that describes the pod that will be created if insufficient replicas are detected. Replicas is the number of desired pods. ReplicaSetStatus represents the current status of a ReplicaSet. Replicas is the most recently observed number of non-terminating pods. Replicas is the most recently observed number of non-terminating pods. The number of available non-terminating pods (ready for at least minReadySeconds) for this replica set. The number of non-terminating pods targeted by this ReplicaSet with a Ready Condition. The number of terminating pods for this replica set. Terminating pods have a non-null .metadata.deletionTimestamp and have not yet reached the Failed or Succeeded .status.phase. The number of non-terminating pods that have labels matching the labels of the pod template of the replicaset. Type of replica set condition. The last time the condition transitioned from one status to another. ObservedGeneration reflects the generation of the most recently observed ReplicaSet. ReplicaSetList is a collection of ReplicaSets. ### `get` read the specified ReplicaSet. GET /apis/apps/v1/namespaces/{namespace}/replicasets/{name}. ### `get` read status of the specified ReplicaSet. GET /apis/apps/v1/namespaces/{namespace}/replicasets/{name}/status. ### `list` list or watch objects of kind ReplicaSet. GET /apis/apps/v1/namespaces/{namespace}/replicasets. ### `list` list or watch objects of kind ReplicaSet. GET /apis/apps/v1/replicasets. ### `create` create a ReplicaSet. POST /apis/apps/v1/namespaces/{namespace}/replicasets. ### `update` replace the specified ReplicaSet. PUT /apis/apps/v1/namespaces/{namespace}/replicasets/{name}. ### `update` replace status of the specified ReplicaSet. PUT /apis/apps/v1/namespaces/{namespace}/replicasets/{name}/status. ### `patch` partially update the specified ReplicaSet. PATCH /apis/apps/v1/namespaces/{namespace}/replicasets/{name}. ### `patch` partially update status of the specified ReplicaSet. PATCH /apis/apps/v1/namespaces/{namespace}/replicasets/{name}/status. ### `delete` delete a ReplicaSet. DELETE /apis/apps/v1/namespaces/{namespace}/replicasets/{name}. ### `deletecollection` delete collection of ReplicaSet. DELETE /apis/apps/v1/namespaces/{namespace}/replicasets.
- [ReplicaSet | Kubernetes](https://www.kubernetes.io/docs/reference/kubernetes-api/workload-resources/replica-set-v1) — Title: ReplicaSet | Kubernetes
# ReplicaSet. # ReplicaSet. If the Labels of a ReplicaSet are empty, they are defaulted to be the same as the Pod(s) that the ReplicaSet manages. Spec defines the specification of the desired behavior of the ReplicaSet. More info:. Status is the most recently observed status of the ReplicaSet. This data may be out of date by some window of time. ReplicaSetSpec is the specification of a ReplicaSet. Selector is a label query over pods that should match the replica count. Label keys and values that must match in order to be controlled by this replica set. Template is the object that describes the pod that will be created if insufficient replicas are detected. Replicas is the number of desired pods. ReplicaSetStatus represents the current status of a ReplicaSet. Replicas is the most recently observed number of non-terminating pods. Replicas is the most recently observed number of non-terminating pods. The number of available non-terminating pods (ready for at least minReadySeconds) for this replica set. The number of non-terminating pods targeted by this ReplicaSet with a Ready Condition. The number of terminating pods for this replica set. Terminating pods have a non-null .metadata.deletionTimestamp and have not yet reached the Failed or Succeeded .status.phase. The number of non-terminating pods that have labels matching the labels of the pod template of the replicaset. Type of replica set condition. The last time the condition transitioned from one status to another. ObservedGeneration reflects the generation of the most recently observed ReplicaSet. ReplicaSetList is a collection of ReplicaSets. ### `get` read the specified ReplicaSet. GET /apis/apps/v1/namespaces/{namespace}/replicasets/{name}. ### `get` read status of the specified ReplicaSet. GET /apis/apps/v1/namespaces/{namespace}/replicasets/{name}/status. ### `list` list or watch objects of kind ReplicaSet. GET /apis/apps/v1/namespaces/{namespace}/replicasets. ### `list` list or watch objects of kind ReplicaSet. GET /apis/apps/v1/replicasets. ### `create` create a ReplicaSet. POST /apis/apps/v1/namespaces/{namespace}/replicasets. ### `update` replace the specified ReplicaSet. PUT /apis/apps/v1/namespaces/{namespace}/replicasets/{name}. ### `update` replace status of the specified ReplicaSet. PUT /apis/apps/v1/namespaces/{namespace}/replicasets/{name}/status. ### `patch` partially update the specified ReplicaSet. PATCH /apis/apps/v1/namespaces/{namespace}/replicasets/{name}. ### `patch` partially update status of the specified ReplicaSet. PATCH /apis/apps/v1/namespaces/{namespace}/replicasets/{name}/status. ### `delete` delete a ReplicaSet. DELETE /apis/apps/v1/namespaces/{namespace}/replicasets/{name}. ### `deletecollection` delete collection of ReplicaSet. DELETE /apis/apps/v1/namespaces/{namespace}/replicasets. For a list of trademarks of The Linux Foundation, please see our Trademark Usage page.
- [ReplicaSet | Kubernetes](http://kubernetes.io/docs/reference/kubernetes-api/workload-resources/replica-set-v1) — Title: ReplicaSet | Kubernetes
# ReplicaSet. ReplicaSet ensures that a specified number of pod replicas are running at any given time. ## ReplicaSet. ReplicaSet ensures that a specified number of pod replicas are running at any given time. If the Labels of a ReplicaSet are empty, they are defaulted to be the same as the Pod(s) that the ReplicaSet manages. Spec defines the specification of the desired behavior of the ReplicaSet. More info:. Status is the most recently observed status of the ReplicaSet. This data may be out of date by some window of time. ReplicaSetSpec is the specification of a ReplicaSet. Selector is a label query over pods that should match the replica count. Label keys and values that must match in order to be controlled by this replica set. Template is the object that describes the pod that will be created if insufficient replicas are detected. Replicas is the number of desired pods. ReplicaSetStatus represents the current status of a ReplicaSet. Replicas is the most recently observed number of non-terminating pods. The number of available non-terminating pods (ready for at least minReadySeconds) for this replica set. The number of non-terminating pods targeted by this ReplicaSet with a Ready Condition. The number of terminating pods for this replica set. The number of non-terminating pods that have labels matching the labels of the pod template of the replicaset. Type of replica set condition. The last time the condition transitioned from one status to another. ObservedGeneration reflects the generation of the most recently observed ReplicaSet. ReplicaSetList is a collection of ReplicaSets. ### `get` read the specified ReplicaSet. GET /apis/apps/v1/namespaces/{namespace}/replicasets/{name}. ### `get` read status of the specified ReplicaSet. GET /apis/apps/v1/namespaces/{namespace}/replicasets/{name}/status. ### `list` list or watch objects of kind ReplicaSet. GET /apis/apps/v1/namespaces/{namespace}/replicasets. ### `list` list or watch objects of kind ReplicaSet. GET /apis/apps/v1/replicasets. ### `create` create a ReplicaSet. POST /apis/apps/v1/namespaces/{namespace}/replicasets. ### `update` replace the specified ReplicaSet. PUT /apis/apps/v1/namespaces/{namespace}/replicasets/{name}. ### `update` replace status of the specified ReplicaSet. PUT /apis/apps/v1/namespaces/{namespace}/replicasets/{name}/status. ### `patch` partially update the specified ReplicaSet. PATCH /apis/apps/v1/namespaces/{namespace}/replicasets/{name}. ### `patch` partially update status of the specified ReplicaSet. PATCH /apis/apps/v1/namespaces/{namespace}/replicasets/{name}/status. ### `delete` delete a ReplicaSet. DELETE /apis/apps/v1/namespaces/{namespace}/replicasets/{name}. ### `deletecollection` delete collection of ReplicaSet. DELETE /apis/apps/v1/namespaces/{namespace}/replicasets.