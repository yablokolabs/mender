# Root cause: Checkout pods terminated due to Deployment scaled to zero replicas

Service `checkout` in namespace `shop`.

## Root cause
Deployment 'checkout' in namespace 'shop' has spec.replicas set to 0, causing the ReplicaSet to scale down to zero and terminate all pods.

## Mechanism
The Deployment controller observes spec.replicas=0 and instructs the ReplicaSet to reduce pod count to zero. The ReplicaSet deletes pods (sending SIGTERM, then SIGKILL after terminationGracePeriodSeconds) to match the desired replica count. This results in pods entering Terminating state and being deleted, as seen in events.

Confidence: 0.95 · Labels: deployment_scale_zero, replicaset_scale_down, pod_termination, config_error

## Evidence relied on
- replicas: 0 (from deploy.yaml)
- Killing pod/checkout-7b597c5cf4-lzjww Stopping container checkout (from EVENTS)
- SuccessfulDelete replicaset/checkout-7b597c5cf4 Deleted pod: checkout-7b597c5cf4-tds99 (from EVENTS)
- Deployment's spec.replicas is set to 0, causing a scale‑down that triggers pod deletion (from TRIAGE)
- Scaling a deployment to zero replicas terminates all pods managed by that deployment [2][3]

## Tavily sources
Queries: Kubernetes Deployment spec.replicas=0 pod termination scale-down behavior; ReplicaSet deletes pods when Deployment replicas set to zero; Kubernetes Deployment scale down to zero replicas pod termination grace period
- [Deployments | Kubernetes](https://kubernetes.io/docs/concepts/workloads/controllers/deployment) — Pods that become terminating due to deletion or scale down may take a long time to terminate, and may consume additional resources during that period. As a result, the total number of all pods can temporarily exceed `.spec.replicas`. Terminating pods can be tracked using the `.status.terminatingReplicas` field of the Deployment.

### Revision History Limit

A Deployment's revision history is stored in the ReplicaSets it controls. [...] ### Rollover (aka multiple updates in-flight)

Each time a new Deployment is observed by the Deployment controller, a ReplicaSet is created to bring up the desired Pods. If the Deployment is updated, the existing ReplicaSet that controls Pods whose labels match `.spec.selector` but whose template does not match `.spec.template` is scaled down. Eventually, the new ReplicaSet is scaled to `.spec.replicas` and all old ReplicaSets is scaled to 0.

If you update a Deployment while an existing rollout is in progress, the Deployment creates a new ReplicaSet as per the update and start scaling that up, and rolls over the ReplicaSet that it was scaling up previously -- it will add it to its list of old ReplicaSets and start scaling it down. [...] Should you manually scale a Deployment, example via `kubectl scale deployment deployment --replicas=X`, and then you update that Deployment based on a manifest (for example: by running `kubectl apply -f deployment.yaml`), then applying that manifest overwrites the manual scaling that you previously did.

If a HorizontalPodAutoscaler (or any similar API for horizontal scaling) is managing scaling for a Deployment, don't set `.spec.replicas`.

Instead, allow the Kubernetes control plane to manage the `.spec.replicas` field automatically.

### Selector

`.spec.selector` is a required field that specifies a label selector for the Pods targeted by this Deployment.

`.spec.selector` must match `.spec.template.metadata.labels`, or it will be rejected by the API.
- [The Ultimate Guide to `kubectl scale deployment`](https://www.plural.sh/blog/kubectl-scale-deployment-guide) — ## Should You Scale Deployments to Zero Replicas?

Scaling a deployment to zero replicas is a deliberate action that terminates all pods managed by that deployment while preserving the deployment object itself. This effectively pauses the application without deleting its configuration, allowing you to bring it back online quickly by scaling the replica count back up. While it might seem counterintuitive to intentionally take a service offline, this technique has several practical applications, particularly for managing costs and controlling non-production environments. [...] The Deployment controller manages one or more underlying ReplicaSets. On scale-up, it increases the replica count on the active ReplicaSet, which results in new Pods being created from the Deployment’s pod template. On scale-down, it reduces the ReplicaSet’s desired count, triggering Pod termination. The scheduler, kubelet, and container runtime are all involved in this process, which is why scaling failures often surface as Pending Pods, slow startups, or degraded application behavior. Platforms like Plural make these transitions observable across clusters, which is critical when diagnosing scaling-related incidents.

### The pod lifecycle during a scale event [...] ### The pod lifecycle during a scale event

During a scale-up, the ReplicaSet controller creates new Pod objects. These Pods initially enter the `Pending` state while the scheduler looks for nodes that can satisfy their resource requests. Once scheduled, the kubelet pulls container images, initializes volumes, and starts containers. Only after these steps does the Pod transition to `Running`.

During a scale-down, the ReplicaSet controller selects Pods to remove and marks them for termination. Those Pods enter the `Terminating` state, receive a SIGTERM, and are given time to shut down gracefully according to their termination grace period. Long shutdown hooks or blocked I/O paths can slow this process and delay capacity rebalancing.

### Resource allocation and scheduling pressure
- [Kubectl Scale Deployment to 0 | CloudBolt](https://www.cloudbolt.io/kubernetes-autoscaling/kubectl-scale-deployment-to-0) — ## Scaling a Kubernetes deployment to 0

Scaling a Kubernetes resource such as a deployment or stateful set to zero involves setting the number of replicas for that resource to zero. This action instructs Kubernetes to terminate all pods associated with the specified resource.

### Benefits of scaling to 0

Scaling to zero can offer significant benefits in a number of areas.

#### Cost savings [...] ## The HPA limitation when scaling deployment to 0

The Horizontal Pod Autoscaler (HPA) automatically adjusts the number of replicas in a deployment, replica set, or stateful set based on observed and configured metrics. However, there is a limitation when it comes to scaling a Kubernetes deployment to zero.

Tha HPA usually operates based on metrics like CPU utilization or custom metrics from the running pods. When the deployment is scaled to zero replicas, there are no active pods to provide these metrics. As a result, the HPA cannot make decisions about scaling up from zero. This means that HPA requires a minimum of one replica to be running, so it cannot be used to completely shut down an application. [...] | Concept | Description |
 --- |
| Using the kubectl scale command | The kubectl scale command is used to manually adjust the number of replicas for a Kubernetes resource. It does not scale the CPU, memory, or other resource allocations for individual pods. |
| Scaling a Kubernetes deployment to 0 | Scaling a Kubernetes deployment to zero is a common practice when you want to temporarily stop an application to save resources or restart your application. |
| The HPA limitation when scaling deployment to 0 | HPAs often scale based on metrics such as CPU target utilization, but when a deployment scales to zero, no pods are running, making it impossible to collect these metrics. As a result, the HPA will never be able to scale up from zero. |
- [When scale replicas==0, do K8s send SIGTERM?](https://discuss.kubernetes.io/t/when-scale-replicas-0-do-k8s-send-sigterm/11838) — It should receive SIGTERM and if its taking too long, it will eventually get a SIGKILL. You can adjust the timeout with
- [Removing spec.replicas of the Deployment resets ...](https://github.com/kubernetes/kubernetes/issues/67135) — After the updated spec was applied, Kubernetes ignored existing replicas count and scaled the RS down to 1 replica.
- [When kubernetes deployment is deleted, ReplicaSets are not being deleted - General Discussions - Discuss Kubernetes](https://discuss.kubernetes.io/t/when-kubernetes-deployment-is-deleted-replicasets-are-not-being-deleted/24625) — NAME READY UP-TO-DATE AVAILABLE AGE  
deployment.apps/my-nginx 2/2 2 2 2m32s

NAME DESIRED CURRENT READY AGE  
replicaset.apps/my-nginx-5899859b88 2 2 2 5m37s  
replicaset.apps/my-nginx-6c8fb56bf7 2 2 2 2m32s

Problem: When we delete deployment, replicaSet and Pods are not being deleted. Hence there is on services and 4 four pods. 2 pods are on version 1.16.0 and two pods are on version 1.17.0. ReplicaSet and Pods must be deleted along with deployment.

nginx-deployment.yaml:

`apiVersion: apps/v1
kind: Deployment
metadata:
name: my-nginx
spec:
revisionHistoryLimit: 0
selector:
matchLabels:
run: my-nginx
replicas: 2
template:
metadata:
labels:
run: my-nginx
spec:
containers:
- name: my-nginx
image: nginx:1.16.0
ports:
- containerPort: 80 [...] Note: I also tried spec.revisionHistoryLimit but it works only when I update the deployment with some change (for example nginx version) but on deployment deletion, replicaSets and pods are still there.  
This behavior is causing a problem, let’s say if I delete and re-create deployment four times with different nginx versions. There are 4 replicas set and each one is creating 2 pods (total 8) with different versions.

Please post complete, working YAML and console logs, so people can see exactly what is happening and try to repro.

Here is a full description of the problem.

# create test namespace  
kubectl create namespace test

# change yaml file (image: nginx:1.16.0) and apply  
kubectl -f nginx-deployment.yaml -n test apply [...] # When kubernetes deployment is deleted, ReplicaSets are not being deleted

I am using Kubernetes version: 1.25.8.  
I have a yaml to create a deployment with 2 pods of nginx. When I apply the yaml (kubecl apply), it creates the below resources:  
1 Deployment  
1 ReplicaSet  
2 Pods.  
When I delete the yaml (kubectl delete), deployment is deleted but replicaSet and pods are still there.
- [Your first Kubernetes Pod and ReplicaSet (LABS) | Learn Cloud Native](https://learncloudnative.com/blog/2021-07-10-pods-replicasets) — The ReplicaSet makes sure only five Pod replicas are running. When we manually created the `stray-pod` with the label `app.kubernetes.io/name=hello` that matches the selector label on the ReplicaSet, the ReplicaSet took that new Pod for its own. Remember, the manually created Pod didn't have the owner. With this new Pod under ReplicaSets' management, the number of replicas was six and not five, as stated in the ReplicaSet. Therefore, the ReplicaSet did what it's supposed to do; it deleted the new Pod to maintain the desired state of five replicas.

## Zero-downtime deployments [...] ## Cleanup

To delete all Pods, you need to delete the ReplicaSet by running: `kubectl delete rs hello`. `rs` is the short name for `replicaset`. If you list the Pods (`kubectl get po`) right after you issued the delete command, you will see the Pods getting terminated:

```
NAME READY STATUS RESTARTS AGE hello-fchvr 1/1 Terminating 0 18m 1 0hello-fl6hd 1/1 Terminating 0 18m 1 0hello-n667q 1/1 Terminating 0 18m 1 0hello-rftkf 1/1 Terminating 0 18m 1 0hello-vctkh 1/1 Terminating 0 7m39s 1 0
```

Once the replica set terminates all Pods, they will be gone, and so will be the ReplicaSet.

← Older postContainer Lifecycle HooksNewer post →Creating a Kubernetes cluster in Google Cloud (LAB)

Keep reading

## Related Articles

How to use kwatch to detect crashes in Kubernetes clusters [...] ```
$ kubectl get po NAME READY STATUS RESTARTS AGE hello-fchvr 1/1 Running 0 14m 1 0hello-fl6hd 1/1 Running 0 14m 1 0hello-n667q 1/1 Running 0 14m 1 0hello-rftkf 1/1 Running 0 14m 1 0hello-vctkh 1/1 Running 0 48s 1 0
```

If you look at the `AGE` column, you will notice four Pods created 14 minutes ago and one created more recently. ReplicaSet created this new Pod. When we deleted one Pod, the number of actual replicas decreased from five to four. The replica set controller detected that and created a new Pod to match the replicas' desired number (5).

Let's try something different now. We will manually create a Pod with labels that match the ReplicaSets selector labels (`app.kubernetes.io/name: hello`).
- [Deployments | Kubernetes](https://kubernetes.io/docs/concepts/workloads/controllers/deployment) — `.spec.revisionHistoryLimit` is an optional field that specifies the number of old ReplicaSets to retain to allow rollback. These old ReplicaSets consume resources in `etcd` and crowd the output of `kubectl get rs`. The configuration of each Deployment revision is stored in its ReplicaSets; therefore, once an old ReplicaSet is deleted, you lose the ability to rollback to that revision of Deployment. By default, 10 old ReplicaSets will be kept, however its ideal value depends on the frequency and stability of new Deployments.

More specifically, setting this field to zero means that all old ReplicaSets with 0 replicas will be cleaned up. In this case, a new Deployment rollout cannot be undone, since its revision history is cleaned up.

### Paused [...] ```
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

  The output is similar to this: [...] ### Rollover (aka multiple updates in-flight)

Each time a new Deployment is observed by the Deployment controller, a ReplicaSet is created to bring up the desired Pods. If the Deployment is updated, the existing ReplicaSet that controls Pods whose labels match `.spec.selector` but whose template does not match `.spec.template` is scaled down. Eventually, the new ReplicaSet is scaled to `.spec.replicas` and all old ReplicaSets is scaled to 0.

If you update a Deployment while an existing rollout is in progress, the Deployment creates a new ReplicaSet as per the update and start scaling that up, and rolls over the ReplicaSet that it was scaling up previously -- it will add it to its list of old ReplicaSets and start scaling it down.
- [ReplicaSet vs Deployment: Kubernetes Differences Explained](https://www.groundcover.com/learn/kubernetes/replicaset-vs-deployment) — Monitoring: For both types of objects, you’ll want to monitor to make sure your requested Pods have been successfully scheduled and that none are stuck in the Pod pending state. But for ReplicaSets, there’s more to monitor because you need to track this data for each Pod replica.
 Scaling: You can use the kubectl scale command to add or remove replicas from both ReplicaSets and Deployments. The process is slightly more straightforward with ReplicaSets, however, because the workload already includes replicas from the start. Note, too, that both ReplicaSets and Deployments can scale to zero - meaning you remove all Pods from them, effectively shutting down the workload.
- [Troubleshoot Kubernetes Deployment ReplicaSet Stuck at Zero Available Replicas](https://oneuptime.com/blog/post/2026-02-09-replicaset-stuck-zero-replicas/view) — ## Understanding ReplicaSet Replica Management

Deployments create ReplicaSets that manage pod replicas. The ReplicaSet controller creates pods matching the desired count and monitors their status. Available replicas are pods that are Ready for at least the Deployment's `minReadySeconds` value. When the available count stays at zero, either pods aren't being created, they're failing to start, or they're failing readiness checks.

`minReadySeconds`

Multiple layers can block replica availability. Scheduling failures prevent pods from being placed on nodes. Image pull errors stop containers from starting. Resource constraints cause OOMKills. Readiness probe failures mark running pods as unavailable. Each requires different diagnostic approaches.

## Identifying Zero Replica Deployments [...] Nawaz Dhandala

## On this page

Deployments stuck with zero available replicas prevent applications from serving traffic and indicate serious problems preventing pod creation or readiness. While the Deployment and ReplicaSet objects exist, no pods reach the Running and Ready state. This complete availability failure requires systematic diagnosis to identify and resolve the blocking issue.

This guide walks through diagnosing ReplicaSet availability problems, identifying common blockers, and implementing solutions that restore service availability.

## Understanding ReplicaSet Replica Management [...] ## Identifying Zero Replica Deployments

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
- [Horizontal Manual Scaling for a Deployment | Kubernetes](https://kubernetes.io/docs/tasks/run-application/scale-deployment) — ## Scaling down a Deployment

To reduce the number of Pods, set `--replicas` to a lower value:

```
kubectl scale deployment/nginx-deployment --replicas=2 kubectl scale deployment/nginx-deployment --replicas=2 = 2
```

Kubernetes gracefully terminates the excess Pods, respecting each Pod's `terminationGracePeriodSeconds` setting.

Verify that the Deployment has two Pods:

```
kubectl get pods -l app=nginx kubectl get pods -l app=nginx app =
```

The output is similar to:

```
NAME READY STATUS RESTARTS AGE nginx-deployment-66b6c48dd5-7gl6h 1/1 Running 0 2m nginx-deployment-66b6c48dd5-v8mkd 1/1 Running 0 2m 
```

## Scaling to zero

You can scale a Deployment to zero to temporarily suspend the workload without deleting the Deployment itself: [...] ```
kubectl scale deployment/nginx-deployment --replicas=0 kubectl scale deployment/nginx-deployment --replicas=0 = 0
```

Verify that no Pods are running:

```
kubectl get deployment nginx-deployment kubectl get deployment nginx-deployment 
```

The output is similar to:

```
NAME READY UP-TO-DATE AVAILABLE AGE nginx-deployment 0/0 0 0 5m 
```

#### Note:

Scaling to zero removes all Pods but preserves the Deployment and its ReplicaSet. Scale back up at any time by setting `--replicas` to a positive number.

Common use cases for scaling to zero include:

 Temporarily suspending a workload to save resources
 Debugging or maintenance windows
 Cost control in development or staging environments

## Other ways to change the replica count
- [Scaling to Zero in Kubernetes with Elasti and KEDA](https://www.truefoundry.com/blog/scaling-to-zero-in-kubernetes-a-deep-dive-into-elasti) — Black left pointing arrow symbol on white background, directional indicator.

## Frequently asked questions

### What does Kubernetes scale to zero mean?

Kubernetes scale to zero means reducing the number of running pods for a workload all the way down to zero replicas during periods of inactivity. When no traffic or demand is present, the deployment consumes no compute resources and incurs no cloud costs. When a new request arrives, the system automatically scales back up from zero and serves the workload.

### Which tools enable scale to zero in Kubernetes? [...] ## The Scale-to-Zero Landscape

While Kubernetes offers robust scaling capabilities through HPA and solutions like KEDA, scaling to zero replicas remains challenging. Existing approaches typically fall into two categories:

1. Native KEDA Scaling - While KEDA can scale deployments to zero using event metrics, this creates a window where incoming requests may be lost during the scale-up cold start period.
2. Full-Service Meshes (e.g., Knative) - Provide comprehensive scale-to-zero but require significant architectural changes and carry high operational overhead.
3. HTTP Proxies (e.g., KEDA HTTP Add-on) - Maintain persistent proxy layers that introduce latency even after services scale up.

## Why Elasti?

Elasti was created to address these limitations with three key design goals: [...] This configuration helps you test real-world routing scenarios and monitor the performance and metrics of your ingress traffic.  
  
To test this setup, you can send requests to the nginx load balancer and monitor the pods of our demo service.

`kubectl port-forward svc/nginx-ingress-nginx-controller \  
  -n ingress-nginx 8080:80`

Port forward to the nginx controller

`kubectl get pods -n elasti-demo -w`

Start a watch on the httpbin service

Now you can send a request to ` and you can see the service being scaled to 1 replica by elasti.

`curl -v 

Send a request to the httpbin service

The service will then be scaled down again after no activity for `cooldownPeriod` seconds specified in the ElastiService (5 seconds in this case).

## Uninstalling Elasti
- [Kubectl Scale Deployment to 0 | CloudBolt](https://www.cloudbolt.io/kubernetes-autoscaling/kubectl-scale-deployment-to-0) — ## Scaling a Kubernetes deployment to 0

Scaling a Kubernetes resource such as a deployment or stateful set to zero involves setting the number of replicas for that resource to zero. This action instructs Kubernetes to terminate all pods associated with the specified resource.

### Benefits of scaling to 0

Scaling to zero can offer significant benefits in a number of areas.

#### Cost savings [...] ## The HPA limitation when scaling deployment to 0

The Horizontal Pod Autoscaler (HPA) automatically adjusts the number of replicas in a deployment, replica set, or stateful set based on observed and configured metrics. However, there is a limitation when it comes to scaling a Kubernetes deployment to zero.

Tha HPA usually operates based on metrics like CPU utilization or custom metrics from the running pods. When the deployment is scaled to zero replicas, there are no active pods to provide these metrics. As a result, the HPA cannot make decisions about scaling up from zero. This means that HPA requires a minimum of one replica to be running, so it cannot be used to completely shut down an application. [...] | Concept | Description |
 --- |
| Using the kubectl scale command | The kubectl scale command is used to manually adjust the number of replicas for a Kubernetes resource. It does not scale the CPU, memory, or other resource allocations for individual pods. |
| Scaling a Kubernetes deployment to 0 | Scaling a Kubernetes deployment to zero is a common practice when you want to temporarily stop an application to save resources or restart your application. |
| The HPA limitation when scaling deployment to 0 | HPAs often scale based on metrics such as CPU target utilization, but when a deployment scales to zero, no pods are running, making it impossible to collect these metrics. As a result, the HPA will never be able to scale up from zero. |
- [Understanding Kubernetes Pod Termination Grace Periods](https://ftp.sleeklens.com/master-series/understanding-kubernetes-pod-termination-grace-periods-1767648289) — # Understanding Kubernetes Pod Termination Grace Periods. # Understanding Kubernetes Pod Termination Grace Periods. Hey everyone, let’s dive into something super important in Kubernetes: the **default grace period** for pod termination. * Impact of the Grace Period on Pod Lifecycle. Simply put, it’s the amount of time Kubernetes gives a pod to shut down gracefully before it’s forcefully terminated. The grace period helps prevent these issues by giving the pod time to gracefully handle its shutdown. During this process, the old pods are terminated, and they get the benefit of the grace period. When you scale down a deployment, pods are deleted, and again, the grace period comes into play. ### Impact of the Grace Period on Pod Lifecycle. The grace period has a direct impact on the pod lifecycle, specifically during the termination phase. The key is to understand how your application behaves during shutdown and set the grace period accordingly. To customize the grace period, you’ll need to use the `terminationGracePeriodSeconds` field in your pod or deployment configuration. Setting it at the deployment level applies the grace period to all pods managed by that deployment. While you want to give your application enough time to shut down, a very long grace period can delay deployments and scaling operations. By setting it at the deployment level, you can manage the grace period for a group of pods consistently. When setting the grace period at the deployment level, it overrides the default value for all pods managed by the deployment. This often happens when a pod’s shutdown process takes longer than the grace period. If the pod is consistently taking longer than the grace period to shut down, you might need to increase the `terminationGracePeriodSeconds` value. To mitigate this, monitor your application’s shutdown time and set the grace period accordingly. We’ve talked about what the **default grace period** is in Kubernetes, why it’s important, how to customize it, and how to troubleshoot related issues. Remember, the **grace period** is a critical part of your Kubernetes deployments, and understanding it is key to running a stable and reliable application. By default, Kubernetes gives your pods 30 seconds to shut down gracefully.
- [Understanding Kubernetes Pod Termination Grace Periods](https://experience.rockfeller.com.br/key-speak/understanding-kubernetes-pod-termination-grace-periods-1767648289) — # Understanding Kubernetes Pod Termination Grace Periods. # Understanding Kubernetes Pod Termination Grace Periods. Hey everyone, let’s dive into something super important in Kubernetes: the **default grace period** for pod termination. * Impact of the Grace Period on Pod Lifecycle. Simply put, it’s the amount of time Kubernetes gives a pod to shut down gracefully before it’s forcefully terminated. The grace period helps prevent these issues by giving the pod time to gracefully handle its shutdown. During this process, the old pods are terminated, and they get the benefit of the grace period. When you scale down a deployment, pods are deleted, and again, the grace period comes into play. ### Impact of the Grace Period on Pod Lifecycle. The grace period has a direct impact on the pod lifecycle, specifically during the termination phase. The key is to understand how your application behaves during shutdown and set the grace period accordingly. To customize the grace period, you’ll need to use the `terminationGracePeriodSeconds` field in your pod or deployment configuration. Setting it at the deployment level applies the grace period to all pods managed by that deployment. While you want to give your application enough time to shut down, a very long grace period can delay deployments and scaling operations. By setting it at the deployment level, you can manage the grace period for a group of pods consistently. When setting the grace period at the deployment level, it overrides the default value for all pods managed by the deployment. This often happens when a pod’s shutdown process takes longer than the grace period. If the pod is consistently taking longer than the grace period to shut down, you might need to increase the `terminationGracePeriodSeconds` value. To mitigate this, monitor your application’s shutdown time and set the grace period accordingly. Avoid setting the grace period much higher than your application actually needs. We’ve talked about what the **default grace period** is in Kubernetes, why it’s important, how to customize it, and how to troubleshoot related issues. Remember, the **grace period** is a critical part of your Kubernetes deployments, and understanding it is key to running a stable and reliable application. By default, Kubernetes gives your pods 30 seconds to shut down gracefully.