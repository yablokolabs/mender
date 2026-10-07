# Root cause: Checkout pod failing readiness probe due to missing /ready endpoint after manifest change

Service `checkout` in namespace `shop`.

## Root cause
The deployment manifest was updated to configure the readiness probe with path `/ready`, but the application code only implements `/healthz` and `/amount` endpoints — no `/ready` handler exists.

## Mechanism
1. A deployment rollout created new ReplicaSet checkout-6558b8b689 with updated readinessProbe.path=/ready (while livenessProbe remains /healthz). 2. New pod checkout-6558b8b689-98gf6 started and kubelet began probing HTTP GET /ready every 5s. 3. The application's HTTP handler (service.py) only routes /healthz and /amount; all other paths return 404. 4. Each probe receives 404, so the pod never becomes Ready (events show "Readiness probe failed: HTTP probe failed with statuscode: 404"). 5. Older pods on ReplicaSet checkout-7b4fcf8959 still use /healthz for both probes and remain Ready.

Confidence: 0.95 · Labels: probe_config, manifest_drift, missing_endpoint

## Evidence relied on
- Events: "Readiness probe failed: HTTP probe failed with statuscode: 404"
- Describe failing pod: "Readiness: http-get http://:http/ready delay=2s timeout=1s period=5s"
- Describe working pods: "Readiness: http-get http://:http/healthz delay=2s timeout=1s period=5s"
- Logs failing pod: "GET /ready HTTP/1.1" 404 (repeated) vs "GET /healthz HTTP/1.1" 200
- Service code (service.py): Handler only implements /healthz and /amount; no /ready route
- Deployment manifest (deploy.yaml): readinessProbe.httpGet.path: /ready

## Tavily sources
Queries: Kubernetes readiness probe 404 endpoint mismatch deployment configuration; Kubernetes probe path configuration application endpoint mismatch troubleshooting; readiness probe HTTP 404 not found endpoint missing application
- [Spring Boot Actuator 404 Liveness/Readiness Fix for Kubernetes Deployments | CodeArchPedia.com](https://openillumi.com/en/en-spring-boot-actuator-liveness-readiness-404-fix) — Title: Spring Boot Actuator 404 Liveness/Readiness Fix for Kubernetes Deployments | CodeArchPedia.com
# Spring Boot Actuator 404 Liveness/Readiness Fix for Kubernetes Deployments. spring boot actuator liveness readiness 404 fix code abstract technology. This technical summary addresses the common issue where **Spring Boot Actuator Liveness and Readiness probes return 404 Not Found**, particularly in **Kubernetes** deployments. Dedicated probe endpoints were officially introduced starting with **Spring Boot 2.3.0**. The definitive solution is to **upgrade to Spring Boot 2.3.0 or higher** and implement the minimal required configuration. Additionally, developers must ensure the `health` endpoint is included in the web exposure settings. For robustness and compliance with 2.3.2+, the recommended configuration is:. ## Troubleshooting Spring Boot Actuator: Why Liveness and Readiness Probes Return 404 Not Found. Configuring **Liveness and Readiness probes** is mandatory for operating **Spring Boot applications** in cloud-native environments like **Kubernetes**. A frequently reported issue during deployment is encountering a **404 Not Found** error when accessing critical Actuator endpoints, such as `/actuator/health/liveness` or `/actuator/health/readiness`, despite seemingly correct `application.yaml` settings. The dedicated probe endpoints were not fully supported until Spring Boot 2.3.0. **Recommended Action:** Upgrade the project dependency to **Spring Boot 2.3.0 or later**. **Recommended Code (Spring Boot 2.3.2+):** This minimal configuration is sufficient to enable the dedicated probe endpoints. This configuration must be accompanied by ensuring the `health` endpoint is exposed via the web interface:. When this detailed configuration still results in a 404, the factor most commonly overlooked is the **Spring Boot framework version** itself. The dedicated Liveness and Readiness state management mechanism, which creates paths like `/actuator/health/liveness`, was officially incorporated starting with **Spring Boot version 2.3.0**. If the application uses an older version (e.g., 2.2.x or prior), the application context simply does not contain the necessary components to map these URIs, rendering the configuration for `probes.enabled` ineffective. Before version 2.3.0, custom logic or accessing the main `/actuator/health` endpoint was necessary for probes, which lacked the necessary separation for Liveness/Readiness semantics. | **Dedicated Probes (2.3.0+)** | Clear separation of Liveness (is the app running?) and Readiness (is the app ready to handle traffic?), essential for Kubernetes. | Requires Spring Boot 2.3.0 or higher. If the version is correct and the YAML syntax is flawless, yet the 404 persists, the configuration file itself may not be correctly loaded into the Spring Context.
- [Spring Boot custom Kubernetes readiness probe | Codemia](https://codemia.io/knowledge-hub/path/spring_boot_custom_kubernetes_readiness_probe) — Title: Spring Boot custom Kubernetes readiness probe | Codemia
### Spring Boot custom Kubernetes readiness probe. Kubernetes readiness probes determine whether a pod is ready to accept traffic. When a readiness probe fails, the pod is removed from the Service endpoints, so no new requests are routed to it. Spring Boot provides built-in Actuator health infrastructure that integrates directly with Kubernetes probes, and you can extend it with custom health checks to cover your application's specific dependencies. ## Default Readiness Support in Spring Boot. Starting with Spring Boot 2.3, the framework natively supports Kubernetes probe endpoints. When you add the Actuator dependency and enable the probe endpoints, Spring Boot exposes `/actuator/health/readiness` and `/actuator/health/liveness` automatically. Add the dependency to your `pom.xml`:. Then enable the probe endpoints in `application.yml`:. 1 management:  2  endpoint:  3  health:  4  probes:  5  enabled:  true  6  show-details:  always 7  health:  8  readinessstate:  9  enabled:  true  10  livenessstate:  11  enabled:  true. With this configuration, Spring Boot reports the readiness state based on the application lifecycle. The readiness endpoint returns `UP` once the application context is fully loaded and all startup tasks are complete. The default readiness probe only checks the application lifecycle state. Spring Boot automatically includes all `HealthIndicator` beans in the readiness group. When any indicator reports `DOWN`, the readiness endpoint returns a 503 status, causing Kubernetes to stop routing traffic to that pod. You can control exactly which indicators belong to the readiness probe by defining health groups:. This configuration ensures that the readiness endpoint checks the database, Redis, and a custom external service, while the liveness probe only checks whether the application process is alive. Spring Boot 2.3+ also lets you change the readiness state programmatically. Once your Spring Boot application exposes the readiness endpoint, configure the Kubernetes deployment manifest to use it:. * **Putting slow checks in the liveness probe**: If a database timeout causes the liveness probe to fail, Kubernetes restarts the pod instead of just removing it from traffic. * **Missing the Actuator dependency**: Without `spring-boot-starter-actuator`, the `/actuator/health/readiness` endpoint does not exist and Kubernetes probes return 404. * Spring Boot 2.3+ natively supports Kubernetes readiness and liveness probe endpoints through Actuator. * Implement `HealthIndicator` beans to add custom dependency checks to the readiness probe.
- [Troubleshooting Kubernetes Liveness and Readiness Probe Failures](https://resolve.ai/glossary/how-to-debug-kubernetes-probe-issues) — 1. The app serves HTTPS but the probe's scheme is HTTP
2. The health endpoint sits behind auth middleware that returns 401 or 403, both of which land outside the 200 to 399 success range.

These mismatches creep in when application code changes without the manifest, or when manifests get copied between apps. Named ports add a layer of complexity as a probe can reference a `containerPort` by name, so the mismatch hides behind the name.

```
livenessProbe: httpGet: path: /healthz # Does this path exist? port: web # Which containerPort does "web" resolve to? scheme: HTTPS # Only if the app actually serves TLS on this port 
``` [...] The test is to `kubectl exec` into the pod and curl the health endpoint twice, once on `localhost` and once on the pod IP, because the pod IP is what the kubelet actually probes. Localhost passing while the pod IP fails usually means the app is bound to 127.0.0.1. Both passing while probes still fail points outside the pod. Check the mesh first, then the CNI. And if the image has no curl, `kubectl debug` with an ephemeral container gets you a shell.

### Probe misconfiguration [...] Think about what the probe protects against. Liveness exists for conditions that don't self-resolve, like deadlocks. A container that's slow for 5 seconds and then recovers doesn't need killing. `failureThreshold: 5` with `periodSeconds: 10` requires roughly 50 seconds of continuous failure before a restart, which catches real deadlocks while tolerating transient slowness.

Wrong port, path, or scheme. A probe aimed at port 8080 while the app listens on 8081 fails instantly with "connection refused". A probe pointing at `/healthz` when the app serves `/health` gets a 404. Two subtler versions of the same problem:
- [Liveness and Readiness Probe Configuration - Wiki - wiki.jmehan.com](https://wiki.jmehan.com/display/KNOW/Liveness+and+Readiness+Probe+Configuration) — Title: Liveness and Readiness Probe Configuration - Wiki - wiki.jmehan.com
## Space shortcuts. ## Page tree. # Liveness and Readiness Probe Configuration. * Created by  John on Nov 30, 2021. We can add a liveness/rediness probe in our kubernetes deployment assuming we have a rest service to call. For this to work, we need an endpoint that will respond with a **200 OK** when called. In the following example, we have a container containing an endpoint the the following specifications:. To configure this in our kubernetes deployment, we will need to add the following:. apiVersion: v1 kind: Service metadata: name: myapp labels: app: myapp spec: ports: - name: http port: 8080 targetPort: 8080. apiVersion: apps/v1 kind: Deployment metadata: name: myapp labels: app: myapp spec: replicas: 1 selector: matchLabels: app: myapp template: metadata: labels: app: myapp spec: containers: - name: myapp image: myapp:1.0.0-SNAPSHOT ... readinessProbe: httpGet: path: /monitor/health port: 8080 initialDelaySeconds: 5 periodSeconds: 5 livenessProbe: httpGet: path: /monitor/health port: 8080 initialDelaySeconds: 5 periodSeconds: 5. * Powered by Atlassian Confluence 8.5.31. * Printed by Atlassian Confluence 8.5.31.
- [Availability | Ensure Container readiness probe is configured](https://www.stream.security/rules/ensure-container-readiness-probe-is-configured) — # Ensure Container readiness probe is configured. In Kubernetes, a readiness probe is a configuration option for a container that enables Kubernetes to determine if a container is ready to start accepting traffic. The readiness probe is typically used to delay traffic routing to a container until it has completed some initialization tasks or until the container has finished loading its dependencies. The "Ensure Container readiness probe is configured" means that the readiness probe has been properly defined in the container's Kubernetes deployment or pod specification. This configuration can include specifying an endpoint for the probe, a timeout period, and a success criteria that must be met for the container to be considered ready. When the readiness probe is properly configured, Kubernetes will use it to determine when a container is ready to receive traffic and can begin routing requests to it.‍. The following are the remediation steps to ensure that the container readiness probe is properly configured in Kubernetes:. 1. Edit the Kubernetes deployment or pod specification file for the container that needs a readiness probe. 2. Add a readiness probe configuration to the container specification. The readiness probe should specify an endpoint that Kubernetes can use to determine if the container is ready to receive traffic. 3. Configure the readiness probe to include a timeout period that is appropriate for the container and its dependencies. The timeout period should be long enough to allow the container to complete its initialization tasks, but not so long that it causes delays in traffic routing. 4. Specify a success criteria that the container must meet in order to be considered ready. This criteria can be based on the response from the endpoint specified in the readiness probe, or it can be based on other conditions that indicate the container is ready. 6. Verify that the container readiness probe is properly configured by checking the Kubernetes logs or using Kubernetes commands to monitor the container's status. By following these steps, you can ensure that the container readiness probe is properly configured in Kubernetes, allowing Kubernetes to determine when a container is ready to receive traffic and begin routing requests to it.
- [Troubleshooting Kubernetes Liveness and Readiness Probe Failures](https://resolve.ai/glossary/how-to-debug-kubernetes-probe-issues) — 1. The app serves HTTPS but the probe's scheme is HTTP
2. The health endpoint sits behind auth middleware that returns 401 or 403, both of which land outside the 200 to 399 success range.

These mismatches creep in when application code changes without the manifest, or when manifests get copied between apps. Named ports add a layer of complexity as a probe can reference a `containerPort` by name, so the mismatch hides behind the name.

```
livenessProbe: httpGet: path: /healthz # Does this path exist? port: web # Which containerPort does "web" resolve to? scheme: HTTPS # Only if the app actually serves TLS on this port 
``` [...] The test is to `kubectl exec` into the pod and curl the health endpoint twice, once on `localhost` and once on the pod IP, because the pod IP is what the kubelet actually probes. Localhost passing while the pod IP fails usually means the app is bound to 127.0.0.1. Both passing while probes still fail points outside the pod. Check the mesh first, then the CNI. And if the image has no curl, `kubectl debug` with an ephemeral container gets you a shell.

### Probe misconfiguration [...] A probe failure points at one of five places:

1. The application itself
2. Its resources
3. Its dependencies
4. The network path between the kubelet and the pod
5. The probe's configuration

In the first three, something real is wrong and the probe caught it, though a restart isn't always the right response. The last two are false positives. In those cases, the app is fine and the probe just can't see it.

### The application is genuinely unhealthy

Sometimes the probe is right. A deadlocked process, a blocked event loop, or an exhausted thread pool. The container is up, the health endpoint can't answer, and a restart is the correct response. This is the case probes exist for, so rule it in before assuming a false alarm.
- [Kubernetes Probes- livenessProbe, readinessProbe, startupProbe |How to use kubernetes probes-part 14](https://www.youtube.com/watch?v=aTlQBofihJQ) — [1:21] our first configuration parameter that is path and this is going to be your status health endpoint and this is just an example today which i am taking
[1:29] that's why i have created only single rest and point that is hello so in my whole application there exist only one restarting point but in your application
[1:37] there might be multiple rest restraint point and one of them might be a health status so please put this health status endpoint over here
[1:46] second parameter which we need to define is the port so if any of your rest application is running then it should
[1:53] have some port so for my current example i am running on a port 8080 so just replace the port number with some
- [How to Configure Kubernetes Liveness Probes Without Causing Restart Loops · MeteorOps](https://meteorops.com/blog/how-to-configure-kubernetes-liveness-probes-without-causing-restart-loops) — Health endpoints should avoid authentication middleware, redirects, rate limits, and expensive request logging. If your probe receives a `301`, `302`, `401`, or `403`, the kubelet may treat it as a failure depending on the probe behavior and response.

Make health routes boring:

 Return directly from the application.
 Do not require tokens.
 Do not redirect HTTP to HTTPS inside the pod unless the probe is configured for HTTPS.
 Do not call external services from liveness.

### Trap 5: Probe port does not match the container

Named ports reduce mistakes when container ports change:

```
ports: - name: http containerPort: 8080 livenessProbe: httpGet: path: /livez port: http
``` [...] Probe tuning should live next to deployment configuration, not in someone’s notes. If your platform team provisions services and dependencies through Kubernetes-native control planes, document probe defaults in the same place you manage patterns such as deploying AWS resources using Crossplane on Kubernetes.

## Design health endpoints that match probe intent

The endpoint behind the probe matters more than the YAML. A clean probe configuration still fails if `/health` does too much work.

A good pattern is to expose separate endpoints:

 `/livez`: checks that the process can respond and has not entered a fatal internal state.
 `/readyz`: checks whether the application can serve traffic right now.
 `/startupz`: checks whether initialization has completed.
- [Readiness Probe Failed in Kubernetes: How to Fix It](https://nudgebee.com/resources/blog/readiness-probe-failed-in-kubernetes) — ### 1. Application Started Slowly

This is one of the most common causes.

The container starts successfully, but the application inside is still:

\ loading dependencies  
\ warming caches  
\ establishing database connections  
\ compiling assets  
\ starting background workers

Kubernetes begins probing too early and marks the pod as Not Ready.

This happens frequently with:

\ Java applications  
\ Spring Boot services  
\ large Node.js applications  
\ AI/ML workloads

#### Common Fix

Increase:

\ initialDelaySeconds  
\ failureThreshold  
\ timeoutSeconds

to give the application more startup time.

### 2. Wrong Readiness Probe Path

Sometimes the readiness endpoint itself is incorrect.

Example: [...] Example:

\ /health does not exist  
\ application returns 404  
\ endpoint requires authentication  
\ wrong port configured

Kubernetes sees probe failures continuously.

#### Common Fix

Verify:

\ endpoint path  
\ port  
\ protocol  
\ response status

using:

> kubectl describe pod

and:

kubectl logs

### 3. Database or Dependency Failures

Many applications fail readiness checks because dependencies are unavailable.

Examples:

 PostgreSQL unavailable
 Redis connection timeout
 Kafka unreachable
 external API failure

The application stays running but fails readiness validation internally.

This is extremely common in microservice environments.

### 4. Resource Starvation

Under high load:

 CPU throttling
 memory pressure
 disk IO contention

can delay readiness responses. [...] This is a common source of confusion.

### Readiness Probe

Controls:

 whether traffic reaches the pod

Failure result:

 pod removed from service endpoints

Container keeps running.

### Liveness Probe

Controls:

 whether Kubernetes should restart the container

Failure result:

 container restart

Liveness failures are usually more severe.

How teams actually run it

Four AI assistants sharing one context across SRE, FinOps, Kubernetes and CloudOps, with every change gated on human approval.

Read the case studies  Free on GitHub

## Best Practices for Readiness Probes

### Use Dedicated Health Endpoints

Do not use heavy application endpoints for readiness checks.

Use lightweight endpoints like:

/ready  
/healthz  
/status

### Avoid Expensive Dependency Checks
- [Kubernetes Readiness Probes - Examples & Common Pitfalls](https://www.vcluster.com/blog/kubernetes-readiness-probes-examples-and-common-pitfalls) — Save this configuration to a file called k8s-probes-deployment.yaml and apply it with `kubectl apply -f k8s-probes-deployment.yaml`.

`apiVersion: v1  
kind: Service  
metadata:  
 labels:  
 app: nginx  
 name: nginx  
 namespace: default  
spec:  
 ports:  
 - name: nginx-http-port  
 port: 80  
 selector:  
 app: nginx  
 sessionAffinity: None  
 type: NodePort`

Save this configuration to a file called k8s-probes-svc.yaml and apply it with `kubectl apply -f k8s-probes-svc.yaml`.

There is no separate endpoint for readiness probes, but we can access events using the `kubectl describe pods`  command, for example, to get the current status.

Use `kubectl get pods` command to see the pods' status.

`kubectl get pods` [...] Let's look at the endpoints with `kubectl get endpoints` command.

`kubectl get endpoints`

We can see Nginx service has an endpoint.

`NAME ENDPOINTS AGE  
kubernetes 10.132.0.42:16443 8h  
nginx 10.1.85.203:80 6m11s`

To see more detail we can use `kubectl describe endpoints nginx` command.

`Name: nginx  
Namespace: default  
Labels: app=nginx  
Annotations: endpoints.kubernetes.io/last-change-trigger-time: 2020-11-13T20:34:13Z  
Subsets:  
 Addresses: 10.1.85.203  
 NotReadyAddresses:   
 Ports:  
 Name Port Protocol-------------  
 nginx-http-port 80 TCP`

Configure the readiness probe's `port` parameter to 81 and apply the configuration.

Again let's check the pods status

`kubectl get pods` [...] ## Example: Sample Nginx Deployment

To see readiness probes in action, we can configure a sample app, a simple NGINX web server in this case. Here we have defined a simple deployment configuration:

`apiVersion: apps/v1  
kind: Deployment  
metadata:  
 name: k8s-probes  
 labels:  
 app: nginx  
spec:  
 replicas: 1  
 selector:  
 matchLabels:  
 app: nginx  
 template:  
 metadata:  
 labels:  
 app: nginx  
 spec:  
 containers:  
 - name: nginx  
 image: nginx  
 ports:  
 - containerPort: 80  
 readinessProbe:  
 initialDelaySeconds: 1  
 periodSeconds: 2  
 timeoutSeconds: 1  
 successThreshold: 1  
 failureThreshold: 1  
 httpGet:  
 host:  
 scheme: HTTP  
 path: /  
 httpHeaders:  
 - name: Host  
 value: myapplication1.com  
 port: 80`
- [Kubernetes readiness and liveness probe failures | NOFire AI](https://www.nofire.ai/glossary/kubernetes-probe-failures) — Common event messages and what they mean:

 `Liveness probe failed: HTTP probe failed with statuscode: 404`: the probe path does not exist on this container. The application may have changed its health endpoint.
 `Readiness probe failed: connection refused`: the container is not yet listening on the probe port. `initialDelaySeconds` may be too short.
 `Unhealthy` with an increasing restart count: the liveness probe is failing after startup, likely due to a timeout, misconfigured path, or CPU throttling.

## Root causes

### 1. Wrong probe path or port

The most common cause. The application moved its health endpoint from `/healthz` to `/health` but the probe spec was not updated. To verify what the container actually exposes:
- [Kubernetes Readiness Probe Failed: HTTP Probe Failed with ...](https://hatchjs.com/readiness-probe-failed-http-probe-failed-with-statuscode-404) — Readiness probe failed: HTTP probe failed with status code 404 * Learn what a readiness probe is and how it works. * Understand the causes of HTTP probe failures and how to fix them. * Get tips on how to improve your readiness probes so that your applications are always available.
- [503 - readiness probe failed - Microsoft Q&A](https://learn.microsoft.com/en-us/answers/questions/2280612/503-readiness-probe-failed) — Make sure that the /health endpoint is available and correctly configured in your application.

   Ensure the `path` and `port` specified in your readiness probe match the actual application service's health endpoint. You can test this by manually curling the health endpoint:

   curl 

   Make sure the endpoint responds as expected. Additionally, monitor the pod’s resource usage to ensure it is not being terminated due to resource constraints.

   If the issue persists, please share the container logs and the output of `kubectl describe pod`  to help diagnose the problem further.

   Please refer the document for your referance:   
    

   If you have any further queries, let me know. If the information is helpful, please click on Upvote.

   Thank you.
2. 

   Anonymous [...] 2025-06-03T01:56:35.64+00:00

   Hi Fauzan,

   The readiness probe for your pod is failing because the application inside the pod is responding with an HTTP 503 "Service Unavailable" status. This indicates that while the pod is running, it is temporarily unable to handle incoming requests at the time the probe checks its health.

   To troubleshoot this:   
    Inspect the logs of the affected container to identify any startup issues or configuration problems. Run the following command:

   ```
   kubectl logs  -c  
   ```

   Check the readinessProbe configuration in your deployment YAML file. Ensure the `httpGet`, `port`, and `path` fields are correctly set, like so:

   ```
   readinessProbe: httpGet: path: /health port: 8080 initialDelaySeconds: 5 periodSeconds: 10 
   ``` [...] 2025-06-03T04:16:51.7466667+00:00

   Hi Fauzan,

   Based on the logs and the error message you've provided, it seems the issue is related to an SSL handshake failure caused by a missing or invalid certificate in your environment. The error message:

   `PKIX path building failed: sun.security.provider.certpath.SunCertPathBuilderException: unable to find valid certification path to requested target`

   indicates that the Java application is unable to establish a secure SSL/TLS connection because it cannot validate the certificate presented by the endpoint. This typically occurs when the Certificate Authority (CA) that issued the server's certificate is not trusted by the Java runtime’s truststore.
- [Kubernetes Readiness Probes - Examples & Common Pitfalls](https://www.vcluster.com/blog/kubernetes-readiness-probes-examples-and-common-pitfalls) — Save this configuration to a file called k8s-probes-deployment.yaml and apply it with `kubectl apply -f k8s-probes-deployment.yaml`.

`apiVersion: v1  
kind: Service  
metadata:  
 labels:  
 app: nginx  
 name: nginx  
 namespace: default  
spec:  
 ports:  
 - name: nginx-http-port  
 port: 80  
 selector:  
 app: nginx  
 sessionAffinity: None  
 type: NodePort`

Save this configuration to a file called k8s-probes-svc.yaml and apply it with `kubectl apply -f k8s-probes-svc.yaml`.

There is no separate endpoint for readiness probes, but we can access events using the `kubectl describe pods`  command, for example, to get the current status.

Use `kubectl get pods` command to see the pods' status.

`kubectl get pods` [...] ### External Dependencies

Let's assume that you have a key/value store used for caching, and your readiness probe endpoint checks this connection as well. The application is capable of running without the key/value store as it will only slow down but it will run a full database query every time it needs to access data. In this case, if the readiness probe fails because of the key/value store not being available, your whole application will be down for some time -until you fix the key/value store which is certainly not desirable.

You need to clearly design your probes considering how your application behaves and how the application responds when there is a failure. You might want to restart the pod (via liveness checks) or remove it from service with a readiness probe. [...] Let's look at the endpoints with `kubectl get endpoints` command.

`kubectl get endpoints`

We can see Nginx service has an endpoint.

`NAME ENDPOINTS AGE  
kubernetes 10.132.0.42:16443 8h  
nginx 10.1.85.203:80 6m11s`

To see more detail we can use `kubectl describe endpoints nginx` command.

`Name: nginx  
Namespace: default  
Labels: app=nginx  
Annotations: endpoints.kubernetes.io/last-change-trigger-time: 2020-11-13T20:34:13Z  
Subsets:  
 Addresses: 10.1.85.203  
 NotReadyAddresses:   
 Ports:  
 Name Port Protocol-------------  
 nginx-http-port 80 TCP`

Configure the readiness probe's `port` parameter to 81 and apply the configuration.

Again let's check the pods status

`kubectl get pods`
- [is there any way to resolve liveness probe failure issue in ...](https://stackoverflow.com/questions/74960530/is-there-any-way-to-resolve-liveness-probe-failure-issue-in-kubernetes-environme) — But, after deploying the same code to Kubernetes cluster we are getting error as "Readiness probe failed. 404 not found". It is not able to call health endpoints and giving 404 error.