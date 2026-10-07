# Root cause: Checkout service selector label mismatch prevents endpoint population

Service `checkout` in namespace `shop`.

## Root cause
Service selector specifies app=checkout-v2 but pod template labels have app=checkout, so the Service matches zero pods and creates no endpoints [3][5][12]

## Mechanism
1. Deployment creates pods with label app=checkout (from deploy.yaml template metadata.labels) [deploy.yaml]. 2. Service spec.selector requires app=checkout-v2 (from service.yaml) [service.yaml]. 3. Service controller evaluates selector against pod labels; no pod carries app=checkout-v2. 4. Endpoints controller finds no matching pods, so the checkout Service gets zero endpoints. 5. Clients cannot reach the checkout pods even though pods are Running and health checks pass [LOGS]. 6. The terminating pod (checkout-77f44f76d9-jwbj8) is unrelated — it is the old ReplicaSet scaling down during a normal rolling update [EVENTS].

Confidence: 0.95 · Labels: service_selector_mismatch, label_mismatch, service_endpoints_empty, rolling_update

## Evidence relied on
- service.yaml: selector.app=checkout-v2
- deploy.yaml: template.metadata.labels.app=checkout
- check_service_selector_and_ports() assertion: 'service selector app=checkout-v2 matches no pod label {'app': 'checkout', 'version': 'v1'}'
- LOGS: all pods return HTTP 200 on /healthz
- EVENTS: new ReplicaSet 74cdd5f78f creating pods, old 77f44f76d9 terminating pods normally

## Tavily sources
Queries: Kubernetes service selector mismatch pod labels rolling update deployment; pod stuck Terminating state deployment rollout service endpoint mismatch; Kubernetes deployment rolling update service selector label mismatch known issue
- [GitHub - khaledeltaweel1/Kubernetes-Rolling-Update-Deployment-Strategy: Rolling Update Deployment In Kubernetes](https://github.com/khaledeltaweel1/Kubernetes-Rolling-Update-Deployment-Strategy) — Title: GitHub - khaledeltaweel1/Kubernetes-Rolling-Update-Deployment-Strategy: Rolling Update Deployment In Kubernetes
You signed in with another tab or window. You signed out in another tab or window. You switched accounts on another tab or window. khaledeltaweel1   /  **Kubernetes-Rolling-Update-Deployment-Strategy**  Public. Rolling Update Deployment In Kubernetes. 0 stars   0 forks   Branches   Tags   Activity. # khaledeltaweel1/Kubernetes-Rolling-Update-Deployment-Strategy. ## Folders and files. | Name | Name | Last commit message | Last commit date |. | Latest commit   History1 Commit 1 Commit |. ## Repository files navigation. # What's the Rolling Update Deployment strategy in kubernetes? Rolling updates incrementally replace your resource's Pods with new ones, which are then scheduled on nodes with available resources. Rolling updates are designed to update your workloads without downtime. # In this example we will implement the Rolling Update deployment on a node js application. # 1- Create `deployment.yml` file and make sure to define your `strategy type` to be `RollingUpdate`. apiVersion: apps/v1 kind: Deployment metadata: name: RollingUpdate-deployment labels: app: helloserver spec: replicas: 8 selector: matchLabels: app: helloserver strategy: type: RollingUpdate template: metadata: labels: app: helloserver spec: containers: - name: helloserver image: khaledeltaweel/k8s-web-server # image: khaledeltaweel/k8s-web-server:1.0 ports: - containerPort: 3000. Create the deployment using the command. `kubectl apply -f deployment.yml`. # 2- Create `service.yml` file. apiVersion: v1 kind: Service metadata: name: RollingUpdate spec: selector: app: helloserver ports: - port: 80 targetPort: 3000 type: NodePort. Create the service using the command. `kubectl apply -f service.yml`. # Now we have created a normal application and you can run the application using the command. The web browser will open and the application will be running on ip looks like this ip `172.26.177.67:30374`. # 3- Start the rolling update deployment strategy process. We used the image `khaledeltaweel/k8s-web-server` in the `deployment.yml` file, so we will change the image version in the `Dockerfile` to be `khaledeltaweel/k8s-web-server:1.0` and then run the deployment again using the command. `kubectl apply -f deployment.yml`. # What will happen when we run this above command? * A minor performance reduction will happed during the update process (One active pod short of the desired number of pods). If you would like to see the update process you can run the command `kubectl rollout status deployment/RollingUpdate-deployment` after running the new deployment immediately. Rolling Update Deployment In Kubernetes. ### Stars. ### Forks.
- [Deployment fails to perform rolling update · Issue #29760 · kubernetes/kubernetes · GitHub](https://github.com/kubernetes/kubernetes/issues/29760) — Title: Deployment fails to perform rolling update · Issue #29760 · kubernetes/kubernetes · GitHub
You signed in with another tab or window. Reload to refresh your session. You switched accounts on another tab or window. * Notifications  You must be signed in to change notification settings. # Deployment fails to perform rolling update #29760. area/workload-api/deploymentsig/appsCategorizes an issue or PR as relevant to SIG Apps.Categorizes an issue or PR as relevant to SIG Apps. opened on Jul 28, 2016. I'm using GKE (Kubernetes 1.2), and most of the time everything works smoothly when performing a rolling update via a deployment config change. When they don't, the deployment is correctly upgraded, but no corresponding RS is created and so the old pod (with a mismatched image to the deployment) lives on. I'm using circle ci to perform a `kubectl apply -f` with the only thing changed in the new configuration being the `image`, to make it point to a new tag. ### Deployment. $ kubectl get deployments ployst-ui-live-deployment -o=yaml apiVersion: extensions/v1beta1 kind: Deployment metadata: annotations: deployment.kubernetes.io/revision: "95" kubectl.kubernetes.io/last-applied-configuration: '{"kind":"Deployment","apiVersion":"extensions/v1beta1","metadata":{"name":"ployst-ui-live-deployment","creationTimestamp":null},"spec":{"replicas":1,"template":{"metadata":{"creationTimestamp":null,"labels":{"app":"ployst-ui","mode":"live"}},"spec":{"containers":[{"name":"ployst-ui","image":"eu.gcr.io/ployst-proto/ployst-ui:1.1445","ports":[{"containerPort":80}],"resources":{},"imagePullPolicy":"IfNotPresent"}],"restartPolicy":"Always","dnsPolicy":"ClusterFirst"}},"strategy":{"type":"RollingUpdate"}},"status":{}}' creationTimestamp: 2016-04-02T09:34:35Z generation: 202 labels: app: ployst-ui mode: live name: ployst-ui-live-deployment namespace: default resourceVersion: "7467578" selfLink: /apis/extensions/v1beta1/namespaces/default/deployments/ployst-ui-live-deployment uid: 1c9fc5a2-f8b6-11e5-ae8f-42010af0000a spec: replicas: 1 selector: matchLabels: app: ployst-ui mode: live strategy: rollingUpdate: maxSurge: 1 maxUnavailable: 1 type: RollingUpdate template: metadata: creationTimestamp: null labels: app: ployst-ui mode: live spec: containers: - image: eu.gcr.io/ployst-proto/ployst-ui:1.1445 imagePullPolicy: IfNotPresent name: ployst-ui ports: - containerPort: 80 protocol: TCP resources: {} terminationMessagePath: /dev/termination-log dnsPolicy: ClusterFirst restartPolicy: Always securityContext: {} terminationGracePeriodSeconds: 30 status: availableReplicas: 1 observedGeneration: 200 replicas: 1 updatedReplicas: 1. ### Pod. This pod should have been upgraded to. $ kubectl get pods ployst-ui-live-deployment-1482854615-w6hsg -o=yaml apiVersion: v1 kind: Pod metadata: annotations: kubernetes.io/created-by: | {"kind":"SerializedReference","apiVersion":"v1","reference":{"kind":"ReplicaSet","namespace":"default","name":"ployst-ui-live-deployment-1482854615","uid":"ba2714da-5343-11e6-8d11-42010af0000a","apiVersion":"extensions","resourceVersion":"7392451"}} kubernetes.io/limit-ranger: 'LimitRanger plugin set: cpu request for container ployst-ui; cpu limit for container ployst-ui' creationTimestamp: 2016-07-26T15:15:03Z generateName: ployst-ui-live-deployment-1482854615- labels: app: ployst-ui mode: live pod-template-hash: "1482854615" ... spec: containers: - image: eu.gcr.io/ployst-proto/ployst-ui:1.1422 imagePullPolicy: IfNotPresent name: ployst-ui ... The deployment seems fine, it's just that it seems to think it has some matching pods. Does it not detect image change tags? I'm trying to find the scheduler logs - perhaps they're not available to me on GKE? No branches or pull requests. ## Issue actions. You can’t perform that action at this time.
- [How to Fix a Kubernetes Selector Label Mismatch - HeyDevJob](https://heydevjob.com/projects/kubernetes-selector-label-mismatch) — If you need a different selector you must delete the old Deployment and create a new one, or use a rolling replacement strategy.
- [After rolling update, old pod still lying around · Issue #27721 · kubernetes/kubernetes · GitHub](https://github.com/kubernetes/kubernetes/issues/27721) — Title: After rolling update, old pod still lying around · Issue #27721 · kubernetes/kubernetes · GitHub
You signed in with another tab or window. You signed out in another tab or window. Whenever I do a rolling update of a replication controller with an image, the originally deployed pod is kept alive on the cluster. If I describe the pods in question, they each are in a different replication controller (the original rc with the original pod, and a new one with the new pod). But if I go into the kubernetes kube-ui dashboard, the OLD rc is linked to the NEW pod. I'm roll-updating via `kubectl rolling-update rc-name --image=new/image:version`. ## PHP Service and replication controllers # apiVersion v1 kind Service metadata nameapi-runtime labels appapi-runtime spec type NodePort ports port 9000 protocol TCP selector appapi-runtime-pod apiVersion v1 kind ReplicationController metadata nameapi-runtime-rc spec replicas 1 template metadata labels appapi-runtime-pod spec containers nameapi-runtime-pod imagePullPolicy Always imagexxxxx.amazonaws.com/xxxxxx:master-20 ports containerPort 9000 env name APP_DEV_MODE value '0' ' ' # Pod horizontal autoscaling # apiVersionextensions/v1beta1 kind HorizontalPodAutoscaler metadata nameapi-runtime-hpa namespace default spec scaleRef kind ReplicationController nameapi-runtime-rc subresource scale minReplicas 1 maxReplicas 4 cpuUtilization targetPercentage 70. [development@localhost ~/B/b/kubernetes] (master) kubectl describe service api-runtime Name: api-runtime Namespace: default Labels: app=api-runtime Selector: app=api-runtime-pod Type: NodePort IP: 10.0.54.148 Port:  9000/TCP NodePort:  31131/TCP Endpoints: 10.244.1.5:9000,10.244.2.7:9000 Session Affinity: None No events. [development@localhost ~/B/b/kubernetes] (master) kubectl describe pod api-runtime-rc Name: api-runtime-rc-a11ad91f9295fecc40b2424c94fbc86e-j2knj Namespace: default Node: ip-172-20-0-177.eu-west-1.compute.internal/172.20.0.177 Start Time: Mon, 20 Jun 2016 14:55:28 +0100 Labels: app=api-runtime-pod,deployment=a11ad91f9295fecc40b2424c94fbc86e Status: Running IP: 10.244.2.7 Controllers: ReplicationController/api-runtime-rc-a11ad91f9295fecc40b2424c94fbc86e Containers: api-runtime-pod: Container ID: docker://a3bba0dffce65b73ea5ef54e2df17420bc411c932bde216793c215667425d40a Image: xxxxxx.amazonaws.com/xxxxxx:master-23 Image ID: docker://06617122419a7741728b0117bc327b6cc85990d68f1bcbb8671b71c6db396ca9 Port: 9000/TCP QoS Tier: cpu: Burstable memory: BestEffort Requests: cpu: 100m State: Running Started: Mon, 20 Jun 2016 14:55:32 +0100 Ready: True Restart Count: 0 Environment Variables: APP_DEV_MODE: 0 Conditions: Type Status Ready True Volumes: default-token-g84wh: Type: Secret (a volume populated by a Secret) SecretName: default-token-g84wh No events. Name: api-runtime-rc-hmuo7 Namespace: default Node: ip-172-20-0-228.eu-west-1.compute.internal/172.20.0.228 Start Time: Mon, 20 Jun 2016 14:56:38 +0100 Labels: app=api-runtime-pod,deployment=ee9a49bd7a578f054e7c31762f47cdf0 Status: Running IP: 10.244.1.5 Controllers: ReplicationController/api-runtime-rc Containers: api-runtime-pod: Container ID: docker://1d586edc2dbd051e5010274145355f5c19191663daf7524d0b2dc6e4c6d3cb34 Image: xxxxx.amazonaws.com/xxxxx:master-20 Image ID: docker://7506e66c6df9a32d048a76b29287376f3619ea8e03b52d7f91beb9180f6e1bc2 Port: 9000/TCP QoS Tier: cpu: Burstable memory: BestEffort Requests: cpu: 100m State: Running Started: Mon, 20 Jun 2016 14:56:39 +0100 Ready: True Restart Count: 0 Conditions: Type Status Ready True Volumes: default-token-g84wh: Type: Secret (a volume populated by a Secret) SecretName: default-token-g84wh No events.
- [kubernetes - service selector vs deployment selector matchlabels - Stack Overflow](https://stackoverflow.com/questions/63875585/service-selector-vs-deployment-selector-matchlabels) — # service selector vs deployment selector matchlabels. I understand that services use a selector to identify which pods to route traffic to by thier labels. Now what is the difference between this selector and the one of the `spec.selector` from the deployment. apiVersion: apps/v1 kind: Deployment metadata: name: nginx spec: selector: matchLabels: app: nginx replicas: 1 template: metadata: labels: app: nginx spec: containers: - name: nginx image: nginx. ## 3 Answers 3. In the `Service`'s `spec.selector`, you can identify which pods to route traffic to only by their labels. On the other hand, in the `Deployment`'s `spec.selector` you have two options to decide on which node the pods will be scheduled on, which are: `matchExpressions`, `matchLabels`. answered Sep 13, 2020 at 23:05. I don't thing this make sense... I have deployments with `spec.selector` that is not defined in nodes and the service is scheduled anyway... ## How Deployment uses spec.selector. It uses the `spec.selector` to know what Pods it should manage. `replicas: 2` a new `ReplicaSet` is created, and it *observes* the Pods using `spec.selector` to match Pods with matching labels. There is two ways to declare the `labels` under the `spec.selector` in `Deployment. ## Labels and Selectors. answered Sep 13, 2020 at 21:18. It explained the `spec.selector`. Because `service` spec only support *equality-based* selectors and the `deployment` is a newer resource that supports two syntax (*equality-based* and *set-based*). The `Service` spec uses just the "equality-based" label selector syntax. My understanding is that earlier the only supported syntax was the equality-based one, like we have on the `service` spec, and that now, when the resource you are using supports the new syntax, you are required to use `matchLabels` or `matchExpressions`. Find the answer to your question by asking. kubernetes : Single service definition with multiple pod selectors. 1") Why would I label Services and Deployments in kubernetes? kubernetes: Role of selector in service vs deployment. 0") Kubernetes Service selector to a container. Kubernetes service selector used to select another service and not deployment? In Kubernetes, how does one select a pod by name in a service selector? What is the difference between Label and Selector in kubernetes?
- [Kubernetes Pods Stuck in Terminating: A Resolution Guide](https://kodekloud.com/blog/kubernetes-pods-stuck-in-terminating-a-resolution-guide) — In this article, I will explain why this happens, how to diagnose the problem, and how to resolve it in a few simple steps.

## Why do Pods get stuck in terminating?

When you delete a Pod, either manually or through deployment, the Pod enters the terminating phase. This means that the Pod is scheduled to be deleted, but it is not yet removed from the node.

The terminating phase is supposed to be a short-lived transitional state, where the Pod gracefully shuts down its containers, releases its resources, and sends a termination signal to the kubelet. The kubelet then removes the Pod from the API server and deletes its local data. [...] Check out our Kubernetes Learning Path to start learning Kubernetes today

## Conclusion

In this article, we have explained why Kubernetes Pods get stuck in the ‘Terminating’ phase, how to diagnose the problem, and how to resolve it in a few simple steps.

I hope you found this article helpful and interesting. If you have any questions or feedback, please feel free to leave a comment below.

Are you ready for practical learning? Subscribe now on our plan and pricing page to unlock 70+ top DevOps courses. Begin your DevOps journey today!

## FAQs

#### Q1: Is it safe to force delete a pod? [...] ```
apiVersion: v1 kind: Pod metadata: name: prestop-demo spec: terminationGracePeriodSeconds: 3600 containers: - name: prestop-demo image: nginx:latest ports: - containerPort: 80 lifecycle: preStop: exec: command: - /bin/sh - -c - sleep 3600 
```

Create a Pod by running the following command:

```
kubectl create -f deployment.yaml
```

Verify the Pod has been created using the following command:

```
kubectl get pods
```

After the Pod creation process is complete, delete it by running the following command:

```
kubectl delete pod prestop-demo
```
- [Explore Termination Behavior for Pods And Their Endpoints | Kubernetes](https://kubernetes.io/docs/tutorials/services/pods-and-endpoint-termination-flow) — The output is similar to this:

`{
"addressType": "IPv4",
"apiVersion": "discovery.k8s.io/v1",
"endpoints": [
{
"addresses": [
"10.12.1.201"
],
"conditions": {
"ready": true,
"serving": true,
"terminating": false`

Now let's terminate the Pod and validate that the Pod is being terminated
respecting the graceful termination period configuration:

`kubectl delete pod nginx-deployment-7768647bf9-b4b9s`

All pods:

`kubectl get pods`

The output is similar to this:

`NAME READY STATUS RESTARTS AGE
nginx-deployment-7768647bf9-b4b9s 1/1 Terminating 0 4m1s
nginx-deployment-7768647bf9-rkxlw 1/1 Running 0 8s`

You can see that the new pod got scheduled.

While the new endpoint is being created for the new Pod, the old endpoint is
still around in the terminating state: [...] `apiVersion: v1
kind: Service
metadata:
 name: nginx-service
spec:
 selector:
 app: nginx
 ports:
 - protocol: TCP
 port: 80
 targetPort: 80`

Now create the Deployment Pod and Service using the above files:

`kubectl apply -f pod-with-graceful-termination.yaml
kubectl apply -f explore-graceful-termination-nginx.yaml`

Once the Pod and Service are running, you can get the name of any associated EndpointSlices:

`kubectl get endpointslice`

The output is similar to this:

`NAME ADDRESSTYPE PORTS ENDPOINTS AGE
nginx-service-6tjbr IPv4 80 10.12.1.199,10.12.1.201 22m`

You can see its status, and validate that there is one endpoint registered:

`kubectl get endpointslices -o json -l kubernetes.io/service-name=nginx-service`

The output is similar to this:
- [Pods stuck in Terminating status. When Kubernetes pods get stuck in the… | by Harold Finch | Medium](https://medium.com/@haroldfinch01/pods-stuck-in-terminating-status-083168c6b7e8) — Sitemap

Open in app

Sign in

Sign in

Harold Finch

## Harold Finch

A DevOps Engineer Looking for new challenges

Kubernetes

DevOps

Linux

Terraform

AWS

# Pods stuck in Terminating status

Harold Finch

Harold Finch

2 min read

·

May 25, 2024

Press enter or click to view image in full size

Pods stuck in Terminating status

When Kubernetes pods get stuck in the “Terminating” status, it can be frustrating and disruptive. This issue often arises when the Kubernetes API server cannot fully complete the termination process for the pods. Here are some common causes and steps to resolve the problem:

> Common Causes

1. Finalizers [...] Proper Resource Management
 Ensure resources are appropriately managed and there are sufficient system resources to handle pod operations.
 Graceful Termination Handling
 Implement proper handling in your applications to ensure they terminate gracefully within the allowed time.

Pods getting stuck in the “Terminating” status can often be resolved by forcefully deleting the pods, removing finalizers, or addressing underlying node issues. Regular monitoring and proactive management of resources can help prevent these issues from occurring. By following these steps, you can effectively manage and troubleshoot stuck pods in your Kubernetes environment.

## Get Harold Finch’s stories in your inbox

Join Medium for free to get updates from this writer. [...] > Common Causes

1. Finalizers

 Finalizers are functions that Kubernetes must execute before deleting resources. If a pod has a finalizer that cannot complete, it will remain in the “Terminating” state.

2. Stuck Volumes

 Persistent volumes attached to the pod might be stuck in the unmount process.

3. Network Issues

 Network disruptions can prevent the Kubernetes API server from communicating with the node where the pod is running.

4. Graceful Termination Timeout

 The pod might be taking longer to terminate gracefully than the allowed termination grace period.

> Steps to Resolve

1. Check Pod Details

 Inspect the pod details to identify potential issues.

```
kubectl describe pod <pod-name><pod-name>pod-name
```

2. Force Delete the Pod
- [Kubernetes Pods Are Stuck in the Terminating Status](https://techdocs.broadcom.com/us/en/vmware-cis/nsx/nsxt-dc/3-2/deployment-guide/troubleshooting-errors/kubernetes-pods-are-stuck-in-the-terminating-status.html) — - NSX Application Platform Deployment Failed
    - NSX Application Platform Upgrade Failed
    - Unstable NSX Application Platform Upgrade UI
    - Collect the NSX Application Platform Support Bundles Using the CLI
    - Attempt to Add or Modify the Helm Repository Failed
    - Attempt to Upload the kubeconfig File Failed
    - Kubernetes Cluster is Inaccessible
    - Service Name/FQDN Information is Invalid
    - Deployment Precheck Failed
    - Upload of the Kubernetes Tools Failed
    - NSX Application Platform Deployment Failed When Using Harbor Registry with HTTP
    - NSX Application Platform Failed During the Helm Cert-Manager Installation
    - Kubernetes Pods Are Stuck in the Terminating Status
    - Clean up the Kubernetes Cluster After an Incomplete Delete Action [...] - Metrics Postgres Database Deployment Failed
    - NSX Metrics Feature Deployment Failed
    - Metrics Feature Post-Deployment Failure
    - Failed to Scale Out the NSX Application Platform Services
    - Failed to Increase the Volume Size of the Data Storage Disk
    - User-Imported CA-Signed Certificate is Expired
 Security Quick Start
 Related Resources
 Documentation Legal Notice [...] # Kubernetes Pods Are Stuck in the Terminating Status

After the system experiences a very high rate of events in a short period of time, some of the pods in the TKG Cluster on Supervisor or upstream Kubernetes cluster are stuck in the 

Terminating

 status.

# Kubernetes Pods Are Stuck in the Terminating Status

After the system experiences a very high rate of events in a short period of time, some of the pods in the TKG Cluster on Supervisor or upstream Kubernetes cluster are stuck in the 

Terminating

 status.

After the system recovered from a very high rate of events occurring, the 

System

NSX Application Platform

 UI displays that the 

NSX Application Platform

 is in a 

Degraded
- [Pod is Stuck in the Terminating State | Managed Kubernetes](https://platform9.com/kb/pmk/frequently-asked-questions/pod-is-stuck-in-the-terminating-state) — A pod is stuck in the Terminating state after you try to delete it. You must manually delete the pod. Run the following command: --grace-period
- [Rolling Updates with Kubernetes Deployments | Kubernetes](https://tachingchen.com/blog/kubernetes-rolling-update-with-deployment) — Please add labels to the `spec.template.metadata.labels`

```
The Deployment "nginx" is invalid. The Deployment "nginx" is invalid. "nginx"    spec.selector: Required value  spec.selector: Required value  spec.template.metadata.labels: Invalid value: null: `selector` does not match template `labels`  spec.template.metadata.labels: Invalid value: null: `selector` does not match template `labels` ` ` ` `
```

# Reference

 
 
 
 
 

# See Also

 Kubernetes - Two Steps Installation
 Kubernetes - Installation
 Kubernetes - Pod
 Kubernetes - High Availability
 Adopting Container and Kubernetes in Production

`To reproduce, republish or re-use the content, please attach with link: 

comments powered by Disqus [...] ```
$ kubectl rollout history deployment/nginx $ kubectl rollout history deployment/nginx deployments "nginx": deployments "nginx": "nginx"REVISION CHANGE-CAUSE REVISION CHANGE-CAUSE 2 kubectl set image deployment nginx nginx=nginx:1.11 --record 2 kubectl set image deployment nginx nginx=nginx:1.11 --record 2 =3 kubectl set image deployment nginx nginx=nginx:1.11.5 --record 3 kubectl set image deployment nginx nginx=nginx:1.11.5 --record 3 =4 kubectl set image deployment nginx nginx=nginx:1.10 --record 4 kubectl set image deployment nginx nginx=nginx:1.10 --record 4 =5 kubectl set image deployment nginx nginx=nginx:1.10.2 --record 5 kubectl set image deployment nginx nginx=nginx:1.10.2 --record 5 =
```

# Troubleshooting

 Please add labels to the `spec.template.metadata.labels` [...] apiVersion: extensions/v1beta1 apiVersion: extensions/v1beta1 apiVersionextensions/v1beta1kind: Deployment kind: Deployment kind Deploymentmetadata: metadata: metadata name: nginx-test  name: nginx-test namenginx-testspec: spec: spec replicas: 10  replicas: 10 replicas 10 selector:  selector: selector matchLabels:  matchLabels: matchLabels service: http-server  service: http-server servicehttp-server strategy:  strategy: strategy type: RollingUpdate  type: RollingUpdate type RollingUpdate rollingUpdate:  rollingUpdate: rollingUpdate maxSurge: 1  maxSurge: 1 maxSurge 1 maxUnavailable: 1  maxUnavailable: 1 maxUnavailable 1 minReadySeconds: 5  minReadySeconds: 5 minReadySeconds 5 template:  template: template metadata:  metadata: metadata labels:  labels: labels service: http-server
- [Updating "-selector-labels" breaks existing deployments · Issue #809 · fluxcd/flagger · GitHub](https://github.com/fluxcd/flagger/issues/809) — Flagger updated all existing k8s services (including `-primary`) to use the newly configured `deploy` label/selector.
 The `svc/{app_name}-primary` and `svc/{app_name}` stopped working (responding with 503) because the `deploy/{app_name}-primary` doesn't have the `deploy` selector label (since it seems like Flagger only copies one selector instead of all the specified selectors on `deploy/{app_name}`).
 After triggering a new (canary) deployment the Flagger operator gets stuck and isn't able to update primary deployment: [...] ```
{"level":"info","ts":"2021-02-10T13:08:37.725Z","caller":"controller/events.go:33","msg":"Advance podinfo.test canary weight 50","canary":"podinfo.test"} {"level":"info","ts":"2021-02-10T13:09:37.459Z","caller":"controller/events.go:33","msg":"Copying podinfo.test template spec to podinfo-primary.test","canary":"podinfo.test"} {"level":"info","ts":"2021-02-10T13:09:37.490Z","caller":"controller/events.go:45","msg":"updating deployment podinfo-primary.test template spec failed: Deployment.apps \"podinfo-primary\" is invalid: spec.template.metadata.labels: Invalid value: map[string]string{\"app\":\"podinfo\", \"deploy\":\"podinfo-primary\"}: `selector` does not match template `labels`","canary":"podinfo.test"} 
``` [...] None yet

No branches or pull requests

## Issue actions

You can’t perform that action at this time.
- [Deployment Fail: Fixing the "Label Selector" Mismatch! (CKA/CKAD Lab 12)](https://www.youtube.com/watch?v=9CFH9tcX2J8) — # Deployment Fail: Fixing the "Label Selector" Mismatch! (CKA/CKAD Lab 12)
## Channel: SavageCamp
1.59K subscribers
1 likes

### Description
9 views
Posted: 2026-01-15
Broken Yaml: 
Why is your Kubernetes Deployment stuck at 0 replicas? Even if your Pods are perfect, a single typo in your Label Selector will break the link between the Deployment and its Pods.

In this SavageCamp lab, we troubleshoot 'Orphaned Deployments.' We’ll show you why the matchLabels and template.metadata.labels must be a perfect match for the controller to function.

What we cover:

How the Deployment controller 'finds' its Pods.

Decoding API validation errors during kubectl apply.

The 2 Ways to Fix It: Updating selectors vs. updating template labels. [...] [3:27] how kubernetes would know that these three ports deployed with this label is connected to this deployment. So let's
[3:34] save and quit and apply again. And you will see that it created it properly.
[3:39] And if I do kit deploy and kit ports, you will see that the deployment has three ready ports and they are coming up
[3:48] right now. So if I do this, one of them is still running. I'll give it some time. And if I do it now, you can see
[3:56] all of them are running. So the way the deployment knows that these three pods belong to that deployment is through
[4:04] that label. That is why when the labels are incorrect, the Kubernetes cannot understand which deployment is handling [...] [2:32] v1 and it is telling you that the selector does not match the template. I will copy this message. We will go back
[2:39] and at the end of this line at the end of this file I'm going to paste the
[2:47] error message. So we can go over it right here. So it said spec template over here.
[2:56] Metadata labels has an invalid value.
[2:58] This value is invalid. And it says that selector which is over here does not match template label. So the selector label does not match the template label.
[3:10] So a very easy fix. You go over here and change this to v1. Now what this
[3:18] deployment would do is it would deploy three ports and those three ports would have a label of front end v1. This is
- [Service: label mapping does not work - General Discussions - Discuss Kubernetes](https://discuss.kubernetes.io/t/service-label-mapping-does-not-work/23939) — `---
apiVersion: apps/v1
kind: Deployment
metadata:
namespace: test
name: nginx-t
labels:
app: nginx-t
spec:
selector:
matchLabels:
app: nginx-t
replicas: 2
strategy:
type: RollingUpdate
template:
metadata:
labels:
app: nginx-t
name: nginx-t
spec:
containers:
- name: nginx-t
image: nginx
ports:
- name: http
containerPort: 80
hostPort: 80
protocol: TCP`

Now I’m trying to setup a service:

`---
apiVersion: apps/v1
kind: Service
metadata:
namespace: test
name: nginx-t-service
spec:
selector:
matchLabels:
app: nginx-t
ports:
- protocol: TCP
port: 80
name: web`

But this fails with:

`error: resource mapping not found for name: "nginx-t-service" namespace: "test" from "nNginx-service.yaml": no matches for kind "Service" in version "apps/v1"
ensure CRDs are installed first`

WHY ? [...] You have this:

`spec:
selector:
matchLabels:
app: nginx-t`

It should be:

`spec:
selector:
app: nginx-t`

uh … thank you

### Related topics

| Topic |  | Replies | Views | Activity |
 ---  --- 
| Selector does not match template labels  General Discussions service ,  deployment | 3 | 7232 | March 13, 2023 |
| Get service by label selector did not match the real label  General Discussions | 6 | 1742 | May 24, 2022 |
| Why kubernetes services do not support matchExpressions?  General Discussions service | 1 | 1652 | April 24, 2023 |
| Kubectl kustomize conundrum  General Discussions | 1 | 1147 | July 29, 2021 |
| [Failed to find target with or without namespaces being specified [Kustomization]](  General Discussions | 0 | 1610 | December 22, 2023 | [...] WHY ?

`kubectl get pods --show-labels -n test
NAME READY STATUS RESTARTS AGE LABELS
nginx-t-775fdf9546-9fkph 1/1 Running 0 31s app=nginx-t,name=nginx-t,pod-template-hash=775fdf9546
nginx-t-775fdf9546-wdkh7 1/1 Running 0 31s app=nginx-t,name=nginx-t,pod-template-hash=775fdf9546`

`apiVersion: apps/v1`

`apiVersion: apps/v1`

It should just be v1  
Services are not in the apps api group

Hi, thanks for the quick reply. Unfortunately I still got errors:

`Error from server (BadRequest): error when creating "nNginx-service.yaml": Service in version "v1" cannot be handled as a Service: json: cannot unmarshal object into Go struct field ServiceSpec.spec.selector of type string`

oh derp, should have kept looking at the spec, services don’t have matchLabels under their selector.
- [Fixing the "Label Selector" Mismatch! (CKA/CKAD Lab 12)](https://www.youtube.com/watch?v=9CFH9tcX2J8&xstg=CAMSBhUDze3xHw%3D%3D) — Even if your Pods are perfect, a single typo in your Label Selector will break the link between the Deployment and its Pods. Updating selectors