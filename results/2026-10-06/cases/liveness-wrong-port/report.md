# Root cause: Checkout pods crash-looping due to liveness probe targeting wrong port (9090 vs 8080)

Service `checkout` in namespace `shop`.

## Root cause
Liveness probe configured with port 9090 but container only exposes port 8080

## Mechanism
1. Deployment spec defines livenessProbe.httpGet.port=9090 [deploy.yaml]. 2. Container spec declares only one port: containerPort=8080 named 'http' [deploy.yaml]. 3. Application serves /healthz on port 8080 (logs show 200 responses on :8080/healthz). 4. Kubelet starts liveness probe after initialDelaySeconds=5s targeting podIP:9090/healthz. 5. Connection refused because no process listens on 9090 [events: 'dial tcp 10.244.0.119:9090: connect: connection refused']. 6. After failureThreshold=3 failures, kubelet kills container and restarts it [events: 'Container checkout failed liveness probe, will be restarted']. 7. Cycle repeats causing crash loop. Readiness probe works because it uses named port 'http' which resolves to 8080 [pod describe: readiness=http://:http/healthz].

Confidence: 0.95 · Labels: probe_config, port_mismatch, liveness_probe, crash_loop

## Evidence relied on
- Liveness probe failed: Get "http://10.244.0.119:9090/healthz": dial tcp 10.244.0.119:9090: connect: connection refused
- Liveness: http-get http://:9090/healthz delay=5s timeout=1s period=10s
- Port: 8080/TCP (http)
- livenessProbe: httpGet: path: /healthz port: 9090
- 06/Oct/2026 19:37:36 - "GET /healthz HTTP/1.1" 200 -

## Tavily sources
Queries: Kubernetes liveness probe connection refused port mismatch container port; Kubernetes probe httpGet port configuration named port vs numeric port; Kubernetes pod restart loop liveness probe failure connection refused
- [Troubleshooting Kubernetes Liveness and Readiness Probe Failures](https://resolve.ai/glossary/how-to-debug-kubernetes-probe-issues) — Think about what the probe protects against. Liveness exists for conditions that don't self-resolve, like deadlocks. A container that's slow for 5 seconds and then recovers doesn't need killing. `failureThreshold: 5` with `periodSeconds: 10` requires roughly 50 seconds of continuous failure before a restart, which catches real deadlocks while tolerating transient slowness.

Wrong port, path, or scheme. A probe aimed at port 8080 while the app listens on 8081 fails instantly with "connection refused". A probe pointing at `/healthz` when the app serves `/health` gets a 404. Two subtler versions of the same problem: [...] 1. The app serves HTTPS but the probe's scheme is HTTP
2. The health endpoint sits behind auth middleware that returns 401 or 403, both of which land outside the 200 to 399 success range.

These mismatches creep in when application code changes without the manifest, or when manifests get copied between apps. Named ports add a layer of complexity as a probe can reference a `containerPort` by name, so the mismatch hides behind the name.

```
livenessProbe: httpGet: path: /healthz # Does this path exist? port: web # Which containerPort does "web" resolve to? scheme: HTTPS # Only if the app actually serves TLS on this port 
``` [...] The error message usually narrows it down fast:

 "connection refused": nothing is listening on the probe port. Wrong port, or the app hasn't started listening yet.
 "context deadline exceeded": no response within `timeoutSeconds`. The timeout is too short, or the app is too slow.
 "HTTP probe failed with statuscode: 503": the app answered, with an error. Look at what the health endpoint actually checks.
 "no such file or directory" (exec probes): the probe's command doesn't exist in the container image.
- [Liveness probe failed connection refused - SUSE Rancher Prime - SUSE](https://forums.suse.com/t/liveness-probe-failed-connection-refused/20837) — Warning Unhealthy 16m kubelet Liveness probe failed: Get  dial tcp 10.42.0.11:80: connect: connection refused
Name: rancher-cbbdf9fd5-pmz5b
Namespace: cattle-system
Priority: 0
Node: fuji1/192.168.157.141
Start Time: Fri, 06 Aug 2021 17:32:54 +0000
Labels: app=rancher
pod-template-hash=cbbdf9fd5
release=rancher
Annotations: cni.projectcalico.org/podIP: 10.42.0.9/32
cni.projectcalico.org/podIPs: 10.42.0.9/32
Status: Running
IP: 10.42.0.9
IPs:
IP: 10.42.0.9
Controlled By: ReplicaSet/rancher-cbbdf9fd5
Containers:
rancher:
Container ID: docker://93cd1749b5cc11a64bb9c6d88fb4e00f0e8c965c29ff8e7cf0ff61db70b12497
Image: rancher/rancher:v2.5.9
Image ID: docker-pullable://rancher/rancher@sha256:4cfd6f4ecf64a8bb117738cc30c57c63617eaf4b3bdbb49dff024f36e3e589bb
Port: 80/TCP
Host Port: 0/TCP
Args: [...] Warning Unhealthy 16m kubelet Liveness probe failed: Get  dial tcp 10.42.0.10:80: connect: connection refused
Name: rancher-cbbdf9fd5-nj99v
Namespace: cattle-system
Priority: 0
Node: fuji1/192.168.157.141
Start Time: Fri, 06 Aug 2021 17:32:54 +0000
Labels: app=rancher
pod-template-hash=cbbdf9fd5
release=rancher
Annotations: cni.projectcalico.org/podIP: 10.42.0.11/32
cni.projectcalico.org/podIPs: 10.42.0.11/32
Status: Running
IP: 10.42.0.11
IPs:
IP: 10.42.0.11
Controlled By: ReplicaSet/rancher-cbbdf9fd5
Containers:
rancher:
Container ID: docker://2ba8702efdaa5503d27804bc1a751ea661618049081dbfef530d04d0d6651546
Image: rancher/rancher:v2.5.9
Image ID: docker-pullable://rancher/rancher@sha256:4cfd6f4ecf64a8bb117738cc30c57c63617eaf4b3bdbb49dff024f36e3e589bb
Port: 80/TCP
Host Port: 0/TCP
Args: [...] `~$ kubectl describe po rancher-df6c8dcd6-2fhmf -n cattle-system
Name: rancher-df6c8dcd6-2fhmf
Namespace: cattle-system
Priority: 0
Node: joxstar/
Start Time: Sun, 01 Aug 2021 15:36:43 +0000
Labels: app=rancher
pod-template-hash=df6c8dcd6
release=rancher
Annotations: cni.projectcalico.org/podIP: 10.42.0.148/32
cni.projectcalico.org/podIPs: 10.42.0.148/32
Status: Failed
Reason: Evicted
Message: The node was low on resource: ephemeral-storage. Container rancher was using 416152Ki, which exceeds its request of 0.
IP:
IPs: <none>
Controlled By: ReplicaSet/rancher-df6c8dcd6
Containers:
rancher:
Image: rancher/rancher:v2.5.9
Port: 80/TCP
Host Port: 0/TCP
Args:
--http-listen-port=80
--https-listen-port=443
--add-local=true
- [How do I resolve Readiness probe connection refused error · Issue #10694 · helm/helm · GitHub](https://github.com/helm/helm/issues/10694) — }}" imagePullPolicy: {{ .Values.image.pullPolicy }} ports: - name: http containerPort: 80 protocol: TCP livenessProbe: tcpSocket: port: 8085 initialDelaySeconds: 300 periodSeconds: 30 timeoutSeconds: 20 readinessProbe: tcpSocket: port: 8085 initialDelaySeconds: 300 periodSeconds: 30 resources: {{- toYaml .Values.resources | nindent 12 }} {{- with .Values.nodeSelector }} nodeSelector: {{- toYaml . | nindent 8 }} {{- end }} {{- with .Values.affinity }} affinity: {{- toYaml . | nindent 8 }} {{- end }} {{- with .Values.tolerations }} {{- toYaml . | nindent 8 }} {{- end }}` [...] Warning Unhealthy 4m14s (x5 over 4m54s) kubelet Liveness probe failed: Get "": dial tcp 10.244.0.59:80: connect: connection refused  
 Warning BackOff 3s (x10 over 2m33s) kubelet Back-off restarting failed container` [...] Normal Scheduled 5m4s default-scheduler Successfully assigned default/flextoecoapi-6bb7cdd846-r6c67 to fbcdcesdn02  
 Normal Pulling 5m3s kubelet Pulling image "golide/flextoeco:1.1.1"  
 Normal Pulled 4m57s kubelet Successfully pulled image "golide/flextoeco:1.1.1" in 6.2802081s  
 Normal Killing 4m34s kubelet Container flextoeco failed liveness probe, will be restarted  
 Normal Created 4m33s (x2 over 4m57s) kubelet Created container flextoeco  
 Normal Started 4m33s (x2 over 4m56s) kubelet Started container flextoeco  
 Normal Pulled 4m33s kubelet Container image "golide/flextoeco:1.1.1" already present on machine  
 Warning Unhealthy 4m14s (x12 over 4m56s) kubelet Readiness probe failed: Get "": dial tcp 10.244.0.59:80: connect: connection refused
- [Kubernetes liveness probe fails with "connection refused ...](https://www.reddit.com/r/kubernetes/comments/e94rae/kubernetes_liveness_probe_fails_with_connection) — As others suggested, it looks like a routing issue. For this reason, I prefer to launch a liveness probe server on a dedicated port, entirely
- [Kubernetes Liveness Probes: Configuration & Best Practices](https://www.groundcover.com/blog/kubernetes-liveness-probe) — This liveness probe configuration tells Kubernetes to attempt to connect to TCP port 8080. It also defines an initial delay of 5 seconds, runs the check every 10 seconds, and sets a failure threshold of 3.

Here’s an example of a probe that uses HTTP:

```
livenessProbe: httpGet: path: /healthz port: 8080 scheme: HTTP initialDelaySeconds: 5 periodSeconds: 10 failureThreshold: 3 successThreshold: 1 timeoutSeconds: 2
```

This httpGet probe is an http liveness probe that issues an HTTP request to the URL /healthz and uses the initial delay, probe period, and failure threshold as the prior examples.

Finally, here’s an example of a gRPC probe: [...] Command execution: The probe runs a command inside the container, which Kubernetes calls an exec probe, such as attempting to create a file using touch or to read a file using ls. If the command exits with a code of 0 (which is an exit code in Linux that means no error occurred), Kubelet assumes the container is healthy.
 TCP socket: The probe attempts to open a connection to a TCP port on the container. As a tcp liveness probe, this method uses tcp probes to connect on a specified port, and a successful connection means the probe succeeds. This is also commonly described as a tcp socket liveness probe.
- [Guide to Understanding Your Kubernetes Liveness Probes Best Practices](https://www.fairwinds.com/blog/a-guide-to-understanding-kubernetes-liveness-probes-best-practices) — For HTTP and TCP probes, you can use a named port. An example is `port: http.` Note that gRPC probes must use a numeric port and do not support named ports or custom hosts.

## Best practices for using liveness probes in Kubernetes

Successful liveness probes don’t impact the health of your cluster. The probed container keeps running, and a new probe is scheduled after the `periodSeconds` delay. If you have a probe run too frequently though, it wastes your resources and can also have a negative impact on application performance. If your probes aren’t frequent enough, on the other hand, your containers may be running in an unhealthy state for extended periods of time before being addressed. [...] 4. gRPC: Applications that use gRPC can use gRPC health-check probes. These probes were introduced in earlier Kubernetes releases and are now stable in current versions, so most clusters support them without any extra configuration. If your application implements the gRPC Health Checking Protocol, you can configure kubelet to use it for liveness, readiness, or startup checks by specifying a gRPC probe on the container port. As with the upstream Kubernetes docs, gRPC probes require you to configure a numeric port; named ports and custom hosts are not supported.

## Configuring liveness probes in Kubernetes [...] + host: The host name to connect to. It defaults to the pod IP; instead, you may want to set "Host" in httpHeaders.
  + scheme: The scheme to use for connecting to the host (HTTP or HTTPS); it defaults to HTTP.
  + path: The path to access on the HTTP server; it defaults to /.
  + httpHeaders: The custom headers you can set in the request; HTTP allows repeated headers.
  + port: The name or number of the port to access on the container; this number must be in the 1 to 65535 range.

3. TCP Socket liveness probe: This probe attempts to connect to a specific TCP port inside the container. If the specified port is open, the probe is considered successful.
- [Kubernetes Liveness Probes: Configuration & Best Practices](https://www.groundcover.com/blog/kubernetes-liveness-probe) — Finally, here’s an example of a gRPC probe:

```
livenessProbe: grpc: port: 50051 service: my.grpc.Service initialDelaySeconds: 5 periodSeconds: 10 failureThreshold: 3 successThreshold: 1 timeoutSeconds: 2
```

This issues a gRPC health check using the service running at my.grpc.Service on port 50051. gRPC probes require a numeric port and do not use named ports, unlike http and tcp probes.

## Advanced probe configurations

The examples above are basic liveness checks because each of them issues just one check. To run a more advanced probe, you can configure one that performs multiple checks in the same probe. It’s also possible to perform different types of checks within the same probe. [...] This liveness probe configuration tells Kubernetes to attempt to connect to TCP port 8080. It also defines an initial delay of 5 seconds, runs the check every 10 seconds, and sets a failure threshold of 3.

Here’s an example of a probe that uses HTTP:

```
livenessProbe: httpGet: path: /healthz port: 8080 scheme: HTTP initialDelaySeconds: 5 periodSeconds: 10 failureThreshold: 3 successThreshold: 1 timeoutSeconds: 2
```

This httpGet probe is an http liveness probe that issues an HTTP request to the URL /healthz and uses the initial delay, probe period, and failure threshold as the prior examples.

Finally, here’s an example of a gRPC probe:
- [How to Configure HTTP GET Probes with Custom Headers and Paths](https://oneuptime.com/blog/post/2026-02-09-http-get-probes-custom-headers/view) — ## HTTPS Probes with TLS

Configure probes to use HTTPS:

`apiVersion: v1
kind: Pod
metadata:
name: secure-app
spec:
containers:
- name: app
image: my-app:latest
ports:
- containerPort: 8443
volumeMounts:
- name: tls-certs
mountPath: /etc/tls
readOnly: true
livenessProbe:
httpGet:
path: /healthz
port: 8443
scheme: HTTPS # Use HTTPS instead of HTTP
periodSeconds: 10
failureThreshold: 3
readinessProbe:
httpGet:
path: /ready
port: 8443
scheme: HTTPS
periodSeconds: 5
failureThreshold: 2
volumes:
- name: tls-certs
secret:
secretName: app-tls-cert`

Note that Kubernetes probes do not verify TLS certificates, they accept any certificate including self-signed ones.

## Using Named Ports in Probes

Reference ports by name for flexibility: [...] Reference ports by name for flexibility:

`apiVersion: v1
kind: Pod
metadata:
name: app-with-named-ports
spec:
containers:
- name: app
image: my-app:latest
ports:
- name: http
containerPort: 8080
protocol: TCP
- name: metrics
containerPort: 9090
protocol: TCP
- name: admin
containerPort: 8081
protocol: TCP
livenessProbe:
httpGet:
path: /healthz
port: http # Reference port by name
periodSeconds: 10
readinessProbe:
httpGet:
path: /ready
port: http
periodSeconds: 5
# Separate probe for metrics endpoint
# (though this would typically be scraped, not used as a probe)`

Named ports make configurations more readable and easier to update.

## Virtual Host Routing with Custom Host Headers

Some applications route based on Host headers: [...] Some applications route based on Host headers:

`apiVersion: v1
kind: Pod
metadata:
name: vhost-app
spec:
containers:
- name: app
image: my-app:latest
ports:
- containerPort: 8080
livenessProbe:
httpGet:
path: /healthz
port: 8080
httpHeaders:
- name: Host
value: api.example.com
- name: X-Forwarded-Proto
value: https
- name: X-Request-ID
value: health-check
periodSeconds: 10`

The probe connects to the Pod IP on port 8080 and sends `Host: api.example.com` header.

`Host: api.example.com`

## Probes with Query Parameters

Include query parameters in the path:

`livenessProbe:
httpGet:
path: /healthz?source=kubernetes&probe=liveness
port: 8080
periodSeconds: 10
readinessProbe:
httpGet:
path: /ready?source=kubernetes&probe=readiness&deep=false
port: 8080
periodSeconds: 5`
- [Configure Liveness, Readiness and Startup Probes | Kubernetes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes) — When `mode` is set to `TLS`, the `kubelet` connects over TLS with `InsecureSkipVerify` and does not verify the server certificate. This matches the behavior of HTTPS probes. Certificate verification is not supported.

If the feature gate is disabled, the `kube-apiserver` removes the `mode` field from new or updated Pods.

## Use a named port

You can use a named `port` for HTTP and TCP probes. gRPC probes do not support named ports.

For example: [...] httpGet:  httpGet:   path: /healthz  path: /healthz  path:  /healthz   port: 8080  port: 8080  port:  8080   protocol: HTTP2  protocol: HTTP2  protocol:  HTTP2   initialDelaySeconds: 5  initialDelaySeconds: 5  initialDelaySeconds:  5   periodSeconds: 10  periodSeconds: 10  periodSeconds:  10 [...] ```
ports: ports: ports:  - name: liveness-port - name: liveness-port  name:  liveness-port   containerPort: 8080  containerPort: 8080  containerPort:  8080     livenessProbe: livenessProbe:  livenessProbe:   httpGet:  httpGet:  httpGet:   path: /healthz  path: /healthz  path:  /healthz   port: liveness-port  port: liveness-port  port:  liveness-port   failureThreshold: 1  failureThreshold: 1  failureThreshold:  1   periodSeconds: 10  periodSeconds: 10  periodSeconds:  10     startupProbe: startupProbe:  startupProbe:   httpGet:  httpGet:  httpGet:   path: /healthz  path: /healthz  path:  /healthz   port: liveness-port  port: liveness-port  port:  liveness-port   failureThreshold: 30  failureThreshold: 30  failureThreshold:  30   periodSeconds: 10  periodSeconds: 10  periodSeconds:  10
- [Kubernetes probes: startupProbe, livenssProbe, and readinessProbe - DEV Community](https://dev.to/jacktt/kubernetes-probes-livenssprobe-readinessprobe-and-startupprobe-3j37) — ## Probes configuration

```
readinessProbe: httpGet: path:/health/readiness port: 8080 initialDelaySeconds: 10 periodSeconds: 5 successThreshold: 1 failureThreshold: 3 timeoutSeconds: 30
``` [...] ## Probes types

### HTTP probe

```
readinessProbe: httpGet: path:/readiness port: 8080
```

It sends an HTTP GET request to a specified endpoint on a container's IP address and port. If the endpoint returns a successful HTTP status code (2xx or 3xx), the probe considers the container as healthy. Otherwise, it assumes the container is unhealthy.

### TCP probe

```
readinessProbe: tcpSocket: port: 8080
```

It attempts to open a TCP connection to a specified port on the container. If the connection is successfully established, the container is considered healthy. Otherwise, it is considered unhealthy.

### Command probe

```
readinessProbe: exec: command: -/script/readiness.sh
``` [...] If the readiness probe returns a failed state, Kubernetes removes the pod from all matching service endpoints.

## Startup probe

A startup probe verifies whether the application within a container is started. This can be used to adopt liveness checks on slow starting containers, avoiding them getting killed by the kubelet before they are up and running.

If such a probe is configured, it disables liveness and readiness checks until it succeeds.

This type of probe is only executed at startup, unlike readiness probes, which are run periodically.

```
startupProbe: httpGet: path:/health/readiness port: 8080 failureThreshold: 30 periodSeconds: 10
```

## Probes configuration
- [Troubleshooting Kubernetes Liveness and Readiness Probe Failures](https://resolve.ai/glossary/how-to-debug-kubernetes-probe-issues) — ### Probe misconfiguration

Probes start before the application is listening. If a container needs 30 seconds to load configuration, connect to databases, and warm caches, but the liveness probe starts after 5, the probe fails, the kubelet restarts the container, and the whole cycle repeats. Sometimes the process isn't even listening yet, so instead of a timeout you get "connection refused". Either way, the events look like:

```
Warning Unhealthy Liveness probe failed: connection refused Normal Killing Container failed liveness probe, will be restarted 
``` [...] Think about what the probe protects against. Liveness exists for conditions that don't self-resolve, like deadlocks. A container that's slow for 5 seconds and then recovers doesn't need killing. `failureThreshold: 5` with `periodSeconds: 10` requires roughly 50 seconds of continuous failure before a restart, which catches real deadlocks while tolerating transient slowness.

Wrong port, path, or scheme. A probe aimed at port 8080 while the app listens on 8081 fails instantly with "connection refused". A probe pointing at `/healthz` when the app serves `/health` gets a 404. Two subtler versions of the same problem: [...] When liveness failures repeat, `kubectl get pods` shows the pod in `CrashLoopBackOff` with a climbing restart count. CrashLoopBackOff means the kubelet is backing off exponentially between restarts; the `Unhealthy` events above tell you why the restarts keep happening. And if the pod is stuck in Pending, its probes haven't run at all and the problem sits earlier in the lifecycle, in scheduling, image pulls, or volumes, not in the health checks.

If the pod is running but probes fail, test the endpoint by hand:

```
kubectl exec -it my-app-xyz123 -- curl -v  
```

Success here with failing probes points to timing (probes fire before the app is ready), timeout (curl will wait longer than the 1-second default), or interception (the network bucket above).
- [Pod in 'CrashLoopBackOff' State - 'Readiness\Liveness probe failed: Get http://{POD_IP}:8082/actuator/health: dial tcp {POD_IP}:8082: connect: connection refused | Troubleshooting | Sisense Community](https://community.sisense.com/forum/troubleshooting-39/topic/pod-in-crashloopbackoff-state-readinessliveness-probe-failed-get-httppod_ip8082actuatorhealth-dial-tcp-pod_ip8082-connect-connection-refused-4766) — What we can see from this output is that the readiness and liveness probes are not listening on the expected endpoint/port (

### What are the Readiness\Liveness probes?

The kubelet, which is the primary node agent and runs on each one of the nodes, ensures that the pods which are supposed to be running are in a healthy state. There are 3 different methods that the kubelet can check if the pods are healthy. In Sisense deployments, we use the HTTP endpoint option which checks if the endpoint is alive (by default every 20 seconds, can be changed in the pod deployment spec.containers[\].livenessProbe.periodSeconds).

Kubelet uses the liveness probe in order to know when to restart a container\pod. [...] Summary: intapiuser describes encountering a pod in a 'CrashLoopBackOff' state, indicating issues with its readiness and liveness probes. The probes failed because they couldn't access the expected HTTP endpoint, likely due to resource constraints (e.g., insufficient RAM). The discussion outlines troubleshooting steps, including probing machine resources, accessing the pod, checking for out-of-memory conditions indicated by exit code 137, and using Docker and system logs for further insights. This analysis suggests that improving resource allocation might resolve the issue.

When checking the pod status using:

`kubectl -n $(NAMESPACE) get pods`

You may encounter one of the pods in an unhealthy state: [...] Kubelet uses the readiness probe in order to know when the container is ready to accept traffic. A pod is ready when all of its containers are ready.

We can check what is configured for the management deployment:

`kubectl -n sisense get deploy management -o yaml`

`...`

`livenessProbe:`

`failureThreshold: 3`

`httpGet:`

`path: /actuator/health`

`port: 8082`

`scheme: HTTP`

`initialDelaySeconds: 60`

`periodSeconds: 20`

`successThreshold: 1`

`timeoutSeconds: 10`

`readinessProbe:`

`failureThreshold: 3`

`httpGet:`

`path: /actuator/health`

`port: 8082`

`scheme: HTTP`

`initialDelaySeconds: 10`

`periodSeconds: 10`

`successThreshold: 1`

`timeoutSeconds: 5`

`...`
- [Kubernetes readiness and liveness probe failures | NOFire AI](https://www.nofire.ai/glossary/kubernetes-probe-failures) — Common event messages and what they mean:

 `Liveness probe failed: HTTP probe failed with statuscode: 404`: the probe path does not exist on this container. The application may have changed its health endpoint.
 `Readiness probe failed: connection refused`: the container is not yet listening on the probe port. `initialDelaySeconds` may be too short.
 `Unhealthy` with an increasing restart count: the liveness probe is failing after startup, likely due to a timeout, misconfigured path, or CPU throttling.

## Root causes

### 1. Wrong probe path or port

The most common cause. The application moved its health endpoint from `/healthz` to `/health` but the probe spec was not updated. To verify what the container actually exposes: [...] Why does my pod keep restarting with a liveness probe failure?
:   The most likely causes are a probe path that changed after a deploy, an initialDelaySeconds value that is too short for the container's startup time, or the container being CPU-throttled so the health endpoint cannot respond in time. Check kubectl describe pod for the exact failure message.

Can a readiness probe failure cause 502 errors?
:   Yes. When all pods in a Service fail their readiness probe, the Service has zero endpoints. Requests reach the load balancer but are not forwarded, returning 502 or 503.

Go deeper:the AI SRE Benchmark

See it live [...] ```
kubectl exec -it <pod-name> -n <namespace> -- curl localhost:8080/health kubectl  exec -it <pod-nam e> -n < namespac e> --  curl localhost:8080/health
```

Replace `8080` and `/health` with the port and path your application uses. If this returns a non-200 response or connection refused, the probe path or port in the spec is wrong.

### 2. Probe timeout too aggressive

`timeoutSeconds` defaults to 1 second. A health endpoint that queries a database connection to verify readiness may take 2-3 seconds under normal load. The probe fails even though the application is healthy. You will see `Readiness probe failed: context deadline exceeded` or similar.

### 3. initialDelaySeconds too short
- [Debug a Pod in CrashLoopBackOff on Kubernetes: Causes and Solutions | SFEIR Institute](https://institute.sfeir.com/en/kubernetes-training/debug-pod-crashloopbackoff-kubernetes-causes-solutions) — Diagnosis:

```
# Check pull events kubectl describe pod checkout-7d4b5c6f9-x2k4n | grep -A3 "Events" # Test locally docker run --rm myregistry/checkout:v1.2.3 /bin/sh -c "echo test" 
```

Solutions:

```
# Check imagePullSecret imagePullSecrets: - name: registry-credentials # Fix command/entrypoint command: ["/app/checkout"] # Absolute path args: ["--port=8080"] 
```

### Cause 5: Misconfigured Probes

Liveness probes kill the container before it's ready.

Symptoms:

```
Events: Liveness probe failed: connection refused Container checkout-container failed liveness probe, will be restarted 
```

Diagnosis: If your application takes 30 seconds to start, your liveness probe must start at 30 seconds. Aggressive probes are the leading cause of self-inflicted CrashLoopBackOff.
- [Kubernetes Pod Restart Reasons: How to Troubleshoot](https://edgedelta.com/company/knowledge-center/kubernetes-pod-restart-reasons-explained) — Misconfigured Liveness/Readiness Probe

Probes that fail repeatedly trigger restarts.

```
Liveness probe failed: HTTP probe failed with statuscode: 404Liveness probe failed: HTTP probe failed with statuscode: 404
```

Investigation:

 Review probe config in YAML
 `kubectl exec curl` endpoints
 Confirm timeouts

Root cause: Probe pointed to `/status` instead of `/health`.

Resolution:

 Fix probe path and redeploy (short term)
 Standardize endpoints and use startup probes for slow apps (long term)

### Configuration and Dependency Restart Scenarios

Misconfigurations and dependency failures often appear during deployments. They typically manifest as immediate startup crashes or repeated restarts when external services are unavailable.

Invalid Environment Variables or Missing Secrets