# Root cause: Checkout pods stuck in Terminating state during rolling update due to 400s termination grace period

Service `checkout` in namespace `shop`.

## Root cause
The deployment uses a RollingUpdate strategy with maxUnavailable: 0 and terminationGracePeriodSeconds: 400, causing old pods to remain in Terminating state for up to 400 seconds while gracefully shutting down, even though new pods are already Ready [6].

## Mechanism
1. Deployment update triggers rolling rollout: new ReplicaSet (7b8f847c7b) created with 2 pods. 2. New pods start, pass readiness probes, become Ready (observed at 17:17:35-17:17:41). 3. Controller begins terminating old ReplicaSet (f9995f9f) pods. 4. Pods enter Terminating state; kubelet sends SIGTERM (Killing events at 7s/1s ago) then waits up to 400s for graceful exit. 5. Old pods also carry a liveness probe (initialDelaySeconds=5, periodSeconds=10) that was removed in the new template, but probes continue running during termination and do not block it. 6. Pods appear 'stuck' in Terminating for minutes, but are actually within the configured grace period.

Confidence: 0.75 · Labels: termination_grace_period, rolling_update, probe_config, maxunavailable_zero

## Evidence relied on
- deployment manifest: terminationGracePeriodSeconds: 400
- events: Killing events 7s/1s ago but pods Terminating for 2m+
- pod describe: old pods have liveness probe, new pods only readiness
- search result [6]: rolling update with maxUnavailable:0 and 400s grace period is the documented solution for zero-downtime rollouts

## Tavily sources
Queries: Kubernetes pod stuck terminating liveness probe rolling update; Kubernetes termination grace period pods stuck terminating replica set rollout; liveness probe configuration causes pod termination stuck Kubernetes
- [Pod Stuck in Terminating State Due to PreStop Hook. | Managed Kubernetes | Knowledge Base](https://platform9.com/kb/pmk/solutions/pod-stuck-in-terminating-state-unless-deleted-forcefully) — ## Environment

 Platform9 Managed Kubernetes - v5.4 and Higher
 Platform9 Edge Cloud - v5.3 and Higher

## Cause

PreStop hook failure is the reason for the pod to be stuck in termination state, these errors can be seen in the kubelet log.

The preStop lifecycle hook in Kubernetes pods allows for performing a specific action before a pod is terminated. It gives applications running in a pod an opportunity to gracefully shut down and clean up any resources or connections before the pod is terminated.

When a pod receives a termination signal, such as when it is being scaled down or during a rolling update, Kubernetes initiates the termination process. Before the pod is actually terminated, Kubernetes executes the preStop hook, if defined, in each container of the pod: [...] ## Solution

Possible solutions to stop pod being stuck in termination is to identify the reason why the preStop hook commands are failing, and fixing the issue associated with these commands should resolve the issue.

From the above example: Investigate why the `httpd` service is failing to stop within the `container1` of the pod `pod_name3.`

## Additional Information

For more details, please refer: 

PreviousCaching Not working for NodeLocal DNSCache.NextKubernetes Dashboard Pod Not Running

Last updated

 Problem
 Environment
 Cause
 Solution
 Additional Information [...] The preStop hook within the pod:

```
# kubectl get pod pod_name3 -n ns1 -oyaml # kubectl get pod pod_name3 -n ns1 -oyaml # kubectl  get  pod  pod_name3  - n  ns1  - oyamlapiVersion: v1 apiVersion: v1 apiVersion:  v1kind: Pod kind: Pod kind:  Podmetadata: metadata: metadata: name: pod_name3  name: pod_name3  name:  pod_name3 namespace: ns1  namespace: ns1  namespace:  ns1spec: spec: spec: containers:   containers:   containers:   preStop:   preStop:   preStop:   exec:  exec:  exec: command:  command:  command: - /bin/bash  - /bin/bash  -  / bin/ bash - -c  - -c  -  - c - service stop httpd; sleep 20 - service stop httpd; sleep 20  -  service  stop  httpd;  sleep  20
```

## Solution
- [Kubernetes Rolling Updates Stalled by Readiness Probes](https://www.linkedin.com/posts/kshitijhatwar_kubernetes-devops-sre-activity-7459448463534137344-soS9) — Old pods won't terminate. one misconfigured readiness probe can silently stall your entire rollout sometimes for the full
- [Lost requests when doing a rolling update · Issue #43576 · kubernetes/kubernetes · GitHub](https://github.com/kubernetes/kubernetes/issues/43576) — 1. Use `kubectl apply`

```
kind: Service apiVersion: v1 metadata: name: zero-downtime-test spec: type: NodePort ports: - port: 80 targetPort: 80 selector: app: zero-downtime-test --- kind: Deployment apiVersion: extensions/v1beta1 metadata: name: zero-downtime-test spec: replicas: 2 template: metadata: labels: app: zero-downtime-test spec: containers: - name: backend image: nginx:1.11 livenessProbe: httpGet: path: / port: 80 scheme: HTTP readinessProbe: httpGet: path: / port: 80 scheme: HTTP ports: - containerPort: 80 protocol: TCP 
```

1. Now do constantly request the node port and check if response is a valid 200 status code. (e.g. with JMeter and ~60 req/second)
2. Modify the deployment so that a rolling update is triggered.
3. For a few milliseconds requests won't be answered. [...] Anything else we need to know:  
 When adding the following to my deployment it works fine.

```
 lifecycle: preStop: exec: command: ["sleep, "1"] 
```

Therefore I think this might be a timing issue where the pod gets the termination signal before it is removed from the service load balancing.

Reactions are currently unavailable

## Activity

Sign up for free to join this conversation on GitHub. Already have an account? Sign in to comment

## Metadata

## Metadata

### Assignees

No one assigned

### Labels

No labels

No labels

No type

No projects

No milestone

None yet

No branches or pull requests

## Issue actions

You can’t perform that action at this time.
- [Kubernetes update results in pod stuck on terminating](https://serverfault.com/questions/986177/kubernetes-update-results-in-pod-stuck-on-terminating) — I am facing a problem with kubernetes deployment. This is probably going to be a low-quality question, I'm sorry about that: I'm new to server management
- [Diagnose Kubernetes Pod Stuck in Terminating State Due to Finalizer Issues](https://oneuptime.com/blog/post/2026-02-09-pod-stuck-terminating-finalizer/view) — `kubernetes.io/pvc-protection`
`# Check if PVC exists
PVC_NAME=$(kubectl get pod stuck-pod-abc123 -n default -o json | \
jq -r '.spec.volumes[]?.persistentVolumeClaim.claimName // empty' | head -n 1)
kubectl get pvc $PVC_NAME -n default
# If PVC is also stuck in terminating
kubectl get pvc $PVC_NAME -n default -o yaml | grep -A 5 finalizers`

Remove the pod or update it so it no longer references the PVC. If the PVC itself remains stuck after that, remove its finalizer only after ensuring no pods reference it. [...] The problem arises when the controller responsible for a finalizer no longer runs. The finalizer blocks deletion, but nothing removes it. The pod stays in Terminating state forever unless you manually intervene.

## Identifying Pods Stuck in Terminating

Check for pods stuck in Terminating state across your cluster.

`# Find terminating pods
kubectl get pods --all-namespaces | \
grep Terminating
# Get more details with custom columns
kubectl get pods -A -o custom-columns=\
NAMESPACE:.metadata.namespace,\
NAME:.metadata.name,\
STATUS:.status.phase,\
DELETION:.metadata.deletionTimestamp
# Output shows:
# NAMESPACE NAME STATUS DELETION
# default stuck-pod-abc123 Running 2024-02-09T10:00:00Z`

A pod showing a deletion timestamp but still running indicates it's stuck in termination. [...] }
// Remove finalizer
instance.ObjectMeta.Finalizers = removeString(instance.ObjectMeta.Finalizers, finalizerName)
if err := r.Update(ctx, instance); err != nil {
return ctrl.Result{}, err
}
}
return ctrl.Result{}, nil
}
// Add finalizer if not present
if !containsString(instance.ObjectMeta.Finalizers, finalizerName) {
instance.ObjectMeta.Finalizers = append(instance.ObjectMeta.Finalizers, finalizerName)
if err := r.Update(ctx, instance); err != nil {
return ctrl.Result{}, err
}
}
// Normal reconciliation logic
return ctrl.Result{}, nil
}`
- [Kubernetes Rolling Update and Termination Grace Periods | by Thomas Césaré-Herriau | Brex Tech Blog | Medium](https://medium.com/brexeng/kubernetes-rolling-update-and-termination-grace-periods-d922c6b84d88) — Join Medium for free to get updates from this writer.

And here lies the problem that caused the incident: the old and functioning ReplicaSet would be terminated before the new buggy one would finish starting up. And it never did!

### The solution

The solution was to not allow any unavailable pod:

```
spec:  revisionHistoryLimit: 1  replicas: 1  strategy:  type: RollingUpdate  rollingUpdate:  maxUnavailable: 0  maxSurge: 100%template:  spec:    terminationGracePeriodSeconds: 400
```

This ensures the new Pod is up and running (Live and Ready) before the old one is terminated. Success!

## A note on Graceful Shutdown with Elixir

Press enter or click to view image in full size

### Kubernetes Termination Period [...] The same code was used in a gRPC server and an Event Consumer, and we didn’t notice any visible impact with the RPC Server (otherwise, a bunch of synchronous operations would have started failing loudly). This was due to the fact that the old ReplicaSet was still running. After being deployed, the new ReplicaSet entered a CrashLoopBackOff state, and therefore never became available (Ready) — some of the old pods were therefore not terminated.

However, for the Event Consumer, it appeared that the old Replica Set had been terminated even though the new one was in CrashLoopBackOff! [...] You may have identified the problem — we had kept the default configuration which worked well for our RPC servers. And the Elixir application terminates itself after 20 seconds! Therefore Kubernetes will not wait the whole terminationGracePeriodSeconds period, as the pod’s process will terminate before it expires. You can configure this differently within your application but…

### There is another problem…

There is also another assumption made that defeats the purpose of having such a long termination period.
- [Kubernetes Pods Stuck in Terminating: A Resolution Guide](https://kodekloud.com/blog/kubernetes-pods-stuck-in-terminating-a-resolution-guide) — #### Highlights

 The Root Cause: Pods usually stick in the "Terminating" state due to unfulfilled Finalizers, failed PreStop hooks, or strict StatefulSet ordering.
 The Fix for Finalizers: Manually edit the Pod metadata to remove the blocking finalizer key.
 The Fix for PreStop Hooks: Use the `--force` and `--grace-period=0` flags to bypass the graceful shutdown timer.
 The Fix for StatefulSets: Change the podManagementPolicy from OrderedReady to Parallel to speed up deletion.

If you are a DevOps engineer who works with Kubernetes, you might have encountered the frustrating issue where kubernetes pods stuck in terminating state refuse to go away. This can be problematic, especially if you need to free up resources or deploy new versions of your applications. [...] ```
kubectl delete pod prestop-demo
```

If you run the `kubectl get pods` again, you’ll see the Pod is now stuck in the terminating stage. When you deleted the Pod, it was not deleted. Instead, it was modified to include deletion time. To view this, run the following command and check the `metadata` section:

```
kubectl get pod/prestop-demo -o yaml
```

You should see this in the metadata section:

Note that the deletionGracePeriodSeconds is set at 3600. This means the pod will be terminated one hour after the delete command is executed. However, you can remove it instantly and bypass the grace period. You do that by setting the new grace period to 0 using the following command:

```
kubectl delete Pod prestop-demo -n default --force --grace-period=0
``` [...] In this article, I will explain why this happens, how to diagnose the problem, and how to resolve it in a few simple steps.

## Why do Pods get stuck in terminating?

When you delete a Pod, either manually or through deployment, the Pod enters the terminating phase. This means that the Pod is scheduled to be deleted, but it is not yet removed from the node.

The terminating phase is supposed to be a short-lived transitional state, where the Pod gracefully shuts down its containers, releases its resources, and sends a termination signal to the kubelet. The kubelet then removes the Pod from the API server and deletes its local data.
- [Decoding the pod termination lifecycle in Kubernetes: a comprehensive guide | CNCF](https://www.cncf.io/blog/2024/12/19/decoding-the-pod-termination-lifecycle-in-kubernetes-a-comprehensive-guide) — Practical troubleshooting tips and solutions:

 Pods stuck in Terminating state: For pods stuck in the Terminating state, you can force delete the pod with kubectl delete pod  –grace-period=0 –force. However, this should be a last resort as it can cause data loss. It’s better to identify the root cause by checking the pod description (kubectl describe pod ) and looking for any errors.
 Pod Disruption Budgets: If you have a PDB that’s preventing pod termination, you may need to reconsider your PDB settings. If necessary, you can delete the PDB, but be aware that this may impact the availability of your application. Always consider the implications and plan downtime accordingly.

## Conclusion [...] Pods stuck in Terminating state: Sometimes, pods can get stuck in the Terminating state due to various reasons like storage issues, finalizers stuck in deletion, or network issues.
 Pod Disruption Budgets: If you have set a Pod Disruption Budget (PDB) which limits the number of pods of a replicated application that are down simultaneously from voluntary disruptions, it can prevent voluntary termination of pods.

Practical troubleshooting tips and solutions:
- [Pods termination grace period - Ansible AWX Operator Documentation](https://docs.ansible.com/projects/awx-operator/en/latest/user-guide/advanced-configuration/pods-termination-grace-period.html) — Skip to content

# Pods termination grace period¶

During deployment restarts or new rollouts, when old ReplicaSet Pods are being terminated, the corresponding jobs which are managed (executed or controlled) by old AWX Pods may end up in `Error` state as there is no mechanism to transfer them to the newly spawned AWX Pods. To work around the problem one could set `termination_grace_period_seconds` in AWX spec, which does the following:

 It sets the corresponding `terminationGracePeriodSeconds` Pod spec of the AWX Deployment to the value provided [...] One may want to set this value to the maximum duration they accept to wait for the affected Jobs to finish. Keeping in mind that such finishing jobs may increase Pods termination time in such situations as `kubectl rollout restart`, AWX upgrade by the operator, or Kubernetes API-initiatedevictions.

| Name | Description | Default |
 --- 
| termination\_grace\_period\_seconds | Optional duration in seconds pods needs to terminate gracefully | not set |
- [Some pods stuck in Terminating state and can only be removed if deleting with propagationPolicy=Background · Issue #65569 · kubernetes/kubernetes · GitHub](https://github.com/kubernetes/kubernetes/issues/65569) — Copy link

Labels

kind/bugCategorizes issue or PR as related to a bug.Categorizes issue or PR as related to a bug.sig/api-machineryCategorizes an issue or PR as relevant to SIG API Machinery.Categorizes an issue or PR as relevant to SIG API Machinery.

## Description

@frittentheke

frittentheke

opened on Jun 28, 2018

Issue body actions

/kind bug

What happened:  
 One (worker) node went OOM and pods where evicted. Before the node was "saved" the kernel OOM-killed at least some of the running containers.

The cluster came back to a save state, but a few pods got stuck in the state terminating.  
 The issue / bug is, that there is no way to delete those pods via kubectl. I was able to remove the deployment and replica-set, but the pods still waited there "Terminating".
- [Increase Kubernetes Reliability: A Best Practices Guide for Readiness Probes](https://www.fairwinds.com/blog/increase-kubernetes-reliability-a-best-practices-guide-for-readiness-probes) — Liveness probes: Use these liveness checks to assess whether an application running in a container is in a healthy state. If the liveness probe fails, Kubernetes kills the container and attempts to restart it. Liveness probes are useful when you want to ensure your application is not experiencing deadlock or silently unresponsive. Deadlock is a situation when your container is not ready but the liveness probe is performing and it exceeds the failure threshold, because of a too short delay time. To mitigate this, you should use a startup probe and set your threshold high enough. Configure liveness probes in the `spec.containers.livenessProbe` code attribute of the pod configuration. Similar to readiness probes, liveness probes also run periodically. [...] Use readiness probes and liveness probes. Liveness probes are like readiness probes, but they are liveness checks that determine whether a pod is still healthy. If a pod isn’t healthy, Kubernetes will restart it. When you use both readiness and liveness probes, it helps you ensure that your applications are always in a healthy state.
 Monitor your readiness probes. Monitor your readiness probes to make sure they are working properly. If a readiness probe fails, it could mean that your application is not healthy. Use the Kubernetes dashboard or the `kubectl` command-line tool to monitor your readiness probes.
- [Readiness vs liveliness probes: How to set them up and when to use them in your Kubernetes cluster | Google Cloud Blog](https://cloud.google.com/blog/products/containers-kubernetes/kubernetes-best-practices-setting-up-health-checks-with-readiness-and-liveness-probes) — ## Configuring the initial probing delay

Probes can be configured in many ways. You can specify how often they should run, what the success and failure thresholds are, and how long to wait for responses. The documentation on configuring probes is pretty clear about the different options and what they do.

However, there is one very important setting that you need to configure when using liveness probes. This is the initialDelaySeconds setting.

As I mentioned above, a liveness probe failure causes the pod to restart. You need to make sure the probe doesn’t start until the app is ready. Otherwise, the app will constantly restart and never be ready! [...] ### Liveness

Let’s imagine another scenario where your app has a nasty case of deadlock, causing it to hang indefinitely and stop serving requests. Because the process continues to run, by default Kubernetes thinks that everything is fine and continues to send requests to the broken pod. By using a liveness probe, Kubernetes detects that the app is no longer serving requests and restarts the offending pod.

## Type of Probes

The next step is to define the probes that test readiness and liveness. There are three types of probes: HTTP, Command, and TCP. You can use any of them for liveness and readiness checks.  

### HTTP
- [Guide to Kubernetes Liveness Probes with Examples](https://spacelift.io/blog/kubernetes-liveness-probe) — #### Troubleshooting steps:

1. Check pod logs (`kubectl logs` ) to see if the application is still initializing when the liveness probe fails.
2. Increase the `initialDelaySeconds` in the probe configuration to give the application more time to start.
3. If the application’s initialization process is slow(e.g., database migrations, loading large models), consider implementing a readiness probe to ensure traffic isn’t sent prematurely.

### 2. Incorrect probe configuration (Path, Port, or Protocol)

If the probe is configured incorrectly, such as pointing to a non-existent endpoint, using the wrong port, or expecting an incorrect response format, Kubernetes will continuously fail the liveness check and restart the container.

#### Troubleshooting steps: [...] Keep liveness probes simple and lightweight. Misconfigured probes can impact application performance if they run too frequently or cause containers to sit in an unhealthy state for extended periods of time. Some containers don’t need probes where they execute simple operations and terminate quickly, so avoid unnecessary probe configurations.
 Use a combination of readiness and liveness probes to ensure that your application is running properly and can handle incoming traffic. [...] For a command-based probe, try running the command inside the container: `kubectl exec  --`

 Check Kubernetes events – Events provide more details on probe failures: `kubectl get events --sort-by=.metadata.creationTimestamp`.

If the liveness probe is failing, review the configuration in your Pod definition and ensure the probe’s command, HTTP endpoint, or TCP socket is correctly defined and accessible. You can also try the troubleshooting tips below.

## Troubleshooting failed Kubernetes liveness probes

Let’s consider three common scenarios where Kubernetes liveness probes fail, along with troubleshooting steps.

### 1. Container startup takes too long
- [Kubernetes Liveness Probes: Configuration & Best Practices](https://www.groundcover.com/blog/kubernetes-liveness-probe) — If a liveness probe fails, Kubernetes will record the failure as an event associated with the container’s pod. You can view pod events by running:

```
kubectl describe pod 
```

Output for probes that succeed isn’t recorded anywhere by default. However, it will be recorded if you set the Kubelet log level to 4 or above. The way to change the Kubelet log level varies between Kubernetes distributions, but it typically involves editing a file with a name that includes logging.conf inside the directory /etc/systemd/system/kubelet.service.d.

## Common issues with Kubernetes liveness checks (and how to fix them)

Several issues may arise when executing probes on Kubernetes. Common challenges include the following.

### Probes that fail unexpectedly [...] Liveness checks are important because situations can arise where a pod appears to be in a healthy state (based on output from commands like kubectl get pods) even though one or more containers within the pod are failing. This can happen because kubectl doesn’t directly check the status of containers; it only checks on pods. To figure out what’s actually happening to the containers inside a pod, you need to use a liveness check, which allows you to execute commands inside individual containers.

### Liveness probes vs. readiness probes vs. startup probes [...] This liveness probe configuration tells Kubernetes to attempt to connect to TCP port 8080. It also defines an initial delay of 5 seconds, runs the check every 10 seconds, and sets a failure threshold of 3.

Here’s an example of a probe that uses HTTP:

```
livenessProbe: httpGet: path: /healthz port: 8080 scheme: HTTP initialDelaySeconds: 5 periodSeconds: 10 failureThreshold: 3 successThreshold: 1 timeoutSeconds: 2
```

This httpGet probe is an http liveness probe that issues an HTTP request to the URL /healthz and uses the initial delay, probe period, and failure threshold as the prior examples.

Finally, here’s an example of a gRPC probe:
- [Configure Liveness, Readiness and Startup Probes | Kubernetes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes) — In the configuration file, you can see that the Pod has a single container. The `periodSeconds` field specifies that the kubelet should perform a liveness probe every 3 seconds. The `initialDelaySeconds` field tells the kubelet that it should wait 3 seconds before performing the first probe. To perform a probe, the kubelet sends an HTTP GET request to the server that is running in the container and listening on port 8080. If the handler for the server's `/healthz` path returns a success code, the kubelet considers the container to be alive and healthy. If the handler returns a failure code, the kubelet kills the container and restarts it.

Any code greater than or equal to 200 and less than 400 indicates success. Any other code indicates failure. [...] ## Define a liveness command

Many applications running for long periods of time eventually transition to broken states, and cannot recover except by being restarted. Kubernetes provides liveness probes to detect and remedy such situations.

In this exercise, you create a Pod that runs a container based on the `registry.k8s.io/busybox:1.27.2` image. Here is the configuration file for the Pod:

`pods/probe/exec-liveness.yaml` [...] In the configuration file, you can see that the Pod has a single `Container`. The `periodSeconds` field specifies that the kubelet should perform a liveness probe every 5 seconds. The `initialDelaySeconds` field tells the kubelet that it should wait 5 seconds before performing the first probe. To perform a probe, the kubelet executes the command `cat /tmp/healthy` in the target container. If the command succeeds, it returns 0, and the kubelet considers the container to be alive and healthy. If the command returns a non-zero value, the kubelet kills the container and restarts it.

When the container starts, it executes this command: