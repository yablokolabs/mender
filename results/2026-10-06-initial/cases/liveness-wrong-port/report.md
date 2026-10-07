# Root cause: Checkout service restart loop due to liveness probe port mismatch (9090 vs 8080)

Service `checkout` in namespace `shop`.

## Root cause
The liveness probe is configured to check port 9090, but the container only exposes port 8080 and the application only listens on port 8080.

## Mechanism
1. Deployment manifest specifies livenessProbe.httpGet.port=9090 [deploy.yaml]. 2. Container spec declares only containerPort 8080 (named 'http') [describe pods]. 3. Application code binds HTTP server to 0.0.0.0:8080 only [service.py]. 4. Kubelet executes liveness probe against podIP:9090/healthz. 5. TCP connection refused because no process listens on 9090 [events: 'dial tcp 10.244.0.51:9090: connect: connection refused']. 6. After failureThreshold=3 failures, kubelet kills and restarts the container [events: 'Container checkout failed liveness probe, will be restarted']. 7. New pod starts with same misconfiguration → infinite restart loop [11].

Confidence: 0.95 · Labels: probe_config, port_mismatch, liveness_probe, restart_loop, connection_refused

## Evidence relied on
- Liveness probe failed: Get "http://10.244.0.51:9090/healthz": dial tcp 10.244.0.51:9090: connect: connection refused
- Liveness: http-get http://:9090/healthz delay=5s timeout=1s period=10s
- Port: 8080/TCP (http)
- livenessProbe: httpGet: path: /healthz port: 9090
- ThreadingHTTPServer(("0.0.0.0", 8080), Handler)
- The liveness probe references a port that is not declared in the container ports array [11]

## Tavily sources
Queries: Kubernetes liveness probe port mismatch container port 8080 connection refused; Kubernetes probe configuration error wrong port number liveness readiness; containerPort 8080 livenessProbe port 9090 misconfiguration documented issues
- [Troubleshooting Kubernetes Liveness and Readiness Probe Failures](https://resolve.ai/glossary/how-to-debug-kubernetes-probe-issues) — Think about what the probe protects against. Liveness exists for conditions that don't self-resolve, like deadlocks. A container that's slow for 5 seconds and then recovers doesn't need killing. `failureThreshold: 5` with `periodSeconds: 10` requires roughly 50 seconds of continuous failure before a restart, which catches real deadlocks while tolerating transient slowness.

Wrong port, path, or scheme. A probe aimed at port 8080 while the app listens on 8081 fails instantly with "connection refused". A probe pointing at `/healthz` when the app serves `/health` gets a 404. Two subtler versions of the same problem: [...] The error message usually narrows it down fast:

 "connection refused": nothing is listening on the probe port. Wrong port, or the app hasn't started listening yet.
 "context deadline exceeded": no response within `timeoutSeconds`. The timeout is too short, or the app is too slow.
 "HTTP probe failed with statuscode: 503": the app answered, with an error. Look at what the health endpoint actually checks.
 "no such file or directory" (exec probes): the probe's command doesn't exist in the container image. [...] 1. The app serves HTTPS but the probe's scheme is HTTP
2. The health endpoint sits behind auth middleware that returns 401 or 403, both of which land outside the 200 to 399 success range.

These mismatches creep in when application code changes without the manifest, or when manifests get copied between apps. Named ports add a layer of complexity as a probe can reference a `containerPort` by name, so the mismatch hides behind the name.

```
livenessProbe: httpGet: path: /healthz # Does this path exist? port: web # Which containerPort does "web" resolve to? scheme: HTTPS # Only if the app actually serves TLS on this port 
```
- [Kubernetes liveness probe fails with "connection refused ...](https://www.reddit.com/r/kubernetes/comments/e94rae/kubernetes_liveness_probe_fails_with_connection) — If you run kubectl describe pod, you see the probe is using port 80 for livenessprobe? Is it possible that your yaml wasn't applied correctly?
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
Args: [...] 11m Normal Started pod/helm-operation-wsljx Started container proxy
<unknown> Normal Scheduled pod/rancher-cbbdf9fd5-n4cgr Successfully assigned cattle-system/rancher-cbbdf9fd5-n4cgr to fuji1
21m Normal Pulling pod/rancher-cbbdf9fd5-n4cgr Pulling image "rancher/rancher:v2.5.9"
15m Normal Pulled pod/rancher-cbbdf9fd5-n4cgr Successfully pulled image "rancher/rancher:v2.5.9"
15m Normal Created pod/rancher-cbbdf9fd5-n4cgr Created container rancher
15m Normal Started pod/rancher-cbbdf9fd5-n4cgr Started container rancher
14m Warning Unhealthy pod/rancher-cbbdf9fd5-n4cgr Readiness probe failed: Get  dial tcp 10.42.0.10:80: connect: connection refused
14m Warning Unhealthy pod/rancher-cbbdf9fd5-n4cgr Liveness probe failed: Get  dial tcp 10.42.0.10:80: connect: connection refused
- [Elastic pod is not Ready: Readiness probe failed: nc: connect to 127.0.0.1 port 8080 (tcp) failed: Connection refused - Elasticsearch - Discuss the Elastic Stack](https://discuss.elastic.co/t/elastic-pod-is-not-ready-readiness-probe-failed-nc-connect-to-127-0-0-1-port-8080-tcp-failed-connection-refused/368853) — The only option I see is diving into it together with Elastic Support further

### Related topics

| Topic |  | Replies | Views | Activity |
 ---  --- 
| Readiness probe failed: {"timestamp": "2023-05-12T08:12:09+00:00", "message": "readiness probe failed", "curl\_rc": "7"}  Elastic Cloud on Kubernetes (ECK) docker | 0 | 1557 | May 12, 2023 |
| Get "readiness probe failed" error when deploy to K8S  Elasticsearch docker | 0 | 868 | October 11, 2021 |
| Readiness probe failed & Liveness probe failed for elastic search  Elasticsearch | 0 | 1367 | September 29, 2020 |
| Pod fails to become ready after restart  Elastic Cloud on Kubernetes (ECK) | 1 | 197 | December 31, 2025 |
| Elaticsearch readiness probe failed connection refused  Elasticsearch | 1 | 3302 | October 18, 2019 | [...] While the connection to Elastic on port 9200 was successful, the connection to port 8080 failed from inside the container:

`# kubectl exec -it elastic-main -- bash
es@main-es-master-0:/usr/share/elasticsearch$ nc -z -v -w5 127.0.0.1 9200
Connection to 127.0.0.1 9200 port [tcp/] succeeded!
es@main-es-master-0:/usr/share/elasticsearch$ nc -z -v -w5 127.0.0.1 8080
nc: connect to 127.0.0.1 port 8080 (tcp) failed: Connection refused`

and indeed there was no service listening on port 8080 (while for correct Elastic there is):

`es@main-es-master-0:/usr/share/elasticsearch$ cat /proc/net/tcp6 | grep " 0A " | awk '{print $2}' | cut -d: -f2 | xargs -I{} printf "%d\n" 0x{}
9200
9300`

The cluster status was green though:

`curl -u "admin:1qazXSW@" -k "
{"status":"green"}`
- [Kubernetes Liveness Probes: Configuration & Best Practices](https://www.groundcover.com/blog/kubernetes-liveness-probe) — This liveness probe configuration tells Kubernetes to attempt to connect to TCP port 8080. It also defines an initial delay of 5 seconds, runs the check every 10 seconds, and sets a failure threshold of 3.

Here’s an example of a probe that uses HTTP:

```
livenessProbe: httpGet: path: /healthz port: 8080 scheme: HTTP initialDelaySeconds: 5 periodSeconds: 10 failureThreshold: 3 successThreshold: 1 timeoutSeconds: 2
```

This httpGet probe is an http liveness probe that issues an HTTP request to the URL /healthz and uses the initial delay, probe period, and failure threshold as the prior examples.

Finally, here’s an example of a gRPC probe:
- [Troubleshooting Kubernetes Liveness and Readiness Probe Failures](https://resolve.ai/glossary/how-to-debug-kubernetes-probe-issues) — Think about what the probe protects against. Liveness exists for conditions that don't self-resolve, like deadlocks. A container that's slow for 5 seconds and then recovers doesn't need killing. `failureThreshold: 5` with `periodSeconds: 10` requires roughly 50 seconds of continuous failure before a restart, which catches real deadlocks while tolerating transient slowness.

Wrong port, path, or scheme. A probe aimed at port 8080 while the app listens on 8081 fails instantly with "connection refused". A probe pointing at `/healthz` when the app serves `/health` gets a 404. Two subtler versions of the same problem: [...] ### gRPC probes

Native gRPC probes went stable in Kubernetes 1.27, after shipping as beta in 1.24. Before native support, the options were TCP probes, which prove nothing about gRPC health, or bundling `grpc_health_probe` into the image as an exec probe.

```
livenessProbe: grpc: port: 9090 initialDelaySeconds: 10 periodSeconds: 10 
```

Two gotchas. The `port` field takes a number only, named ports don't work here. And the kubelet dials without TLS, so the health port needs to accept plaintext connections. There's also an optional `service` field, which lets a single port back separate liveness and readiness checks by name.

## What are the common causes of probe failures?

A probe failure points at one of five places: [...] The error message usually narrows it down fast:

 "connection refused": nothing is listening on the probe port. Wrong port, or the app hasn't started listening yet.
 "context deadline exceeded": no response within `timeoutSeconds`. The timeout is too short, or the app is too slow.
 "HTTP probe failed with statuscode: 503": the app answered, with an error. Look at what the health endpoint actually checks.
 "no such file or directory" (exec probes): the probe's command doesn't exist in the container image.
- [aks kube-system readiness liveness probe keep failing - Microsoft Q&A](https://learn.microsoft.com/en-us/answers/questions/2279482/aks-kube-system-readiness-liveness-probe-keep-fail) — Hi Aniss Chohra,

The error indicates that the Kubelet API on the node (port 10250) is not responding properly. It's a node-level issue, not a problem with the pod itself.

When you run kubectl logs, the API server proxies the request to the Kubelet on the node where the pod is running, over HTTPS on port 10250.

If that fails with an EOF (End of File), it means the Kubelet is not serving logs properly or the API server can't establish a full TLS connection with the Kubelet

Kubelet is unhealthy due to a NotReady node, taint issues, or broken cloud node manager or networking.

TLS cert mismatch or bootstrap failure prevents the Kubelet from authenticating or accepting requests, often due to cloud-init issues, custom VNETs, or faulty Azure extensions.
- [Configure Liveness, Readiness and Startup Probes | Kubernetes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes) — "/var/lib/etcd",  "--listen-client-urls",  "  "--advertise-client-urls",  "  "--log-level",  "debug"]   ports:  ports:  ports:   - containerPort: 2379  - containerPort: 2379  containerPort:  2379   livenessProbe:  livenessProbe:  livenessProbe:   grpc:  grpc:  grpc:   port: 2379  port: 2379  port:  2379   initialDelaySeconds: 10  initialDelaySeconds: 10  initialDelaySeconds:  10 [...] livenessProbe:   grpc:  grpc:  grpc:   port: 8443  port: 8443  port:  8443   mode: TLS  mode: TLS  mode:  TLS   initialDelaySeconds: 5  initialDelaySeconds: 5  initialDelaySeconds:  5   periodSeconds: 10  periodSeconds: 10  periodSeconds:  10 [...] apiVersion: v1 apiVersion: v1 apiVersion:  v1  kind: Pod kind: Pod  kind:  Pod  metadata: metadata:  metadata:   name: grpc-tls-app  name: grpc-tls-app  name:  grpc-tls-app  spec: spec:  spec:   containers:  containers:  containers:   - name: app  - name: app  name:  app   image: registry.k8s.io/e2e-test-images/agnhost:2.40  image: registry.k8s.io/e2e-test-images/agnhost:2.40  image:  registry.k8s.io/e2e-test-images/agnhost:2.40   command: ["/agnhost", "grpc-health-checking", "--port=8443"]  command: ["/agnhost", "grpc-health-checking", "--port=8443"]  command:  ["/agnhost",  "grpc-health-checking",  "--port=8443"]   ports:  ports:  ports:   - containerPort: 8443  - containerPort: 8443  containerPort:  8443   livenessProbe:  livenessProbe:  livenessProbe:   grpc:  grpc:  grpc:   port:
- [Kubernetes liveness probe fails with "connection refused ...](https://www.reddit.com/r/kubernetes/comments/e94rae/kubernetes_liveness_probe_fails_with_connection) — If you run kubectl describe pod, you see the probe is using port 80 for livenessprobe? Is it possible that your yaml wasn't applied
- [Liveness, Readiness, and Startup Probes | Kubernetes](https://kubernetes.io/docs/concepts/workloads/pods/probes) — #### Note:

Unlike HTTP or TCP probes, you cannot specify the health check port by name, and you cannot configure a custom hostname.

Configuration problems (for example: incorrect port or service, unimplemented health checking protocol) are considered a probe failure, similar to HTTP and TCP probes.

Feature state: Alpha since Kubernetes v1.37; disabled by default

More information about this feature

To use this feature, you (or a cluster administrator) will need to enable the GRPCContainerProbeTLS feature gate for all relevant components in your cluster.

See Enable Or Disable Feature Gates for more information. [...] "/var/lib/etcd",  "--listen-client-urls",  "  "--advertise-client-urls",  "  "--log-level",  "debug"]   ports:  ports:  ports:   - containerPort: 2379  - containerPort: 2379  containerPort:  2379   livenessProbe:  livenessProbe:  livenessProbe:   grpc:  grpc:  grpc:   port: 2379  port: 2379  port:  2379   initialDelaySeconds: 10  initialDelaySeconds: 10  initialDelaySeconds:  10 [...] `host`: Host name to connect to, defaults to the pod IP. You probably want to set "Host" in `httpHeaders` instead.
 `scheme`: Scheme to use for connecting to the host (HTTP or HTTPS). Defaults to "HTTP".
 `path`: Path to access on the HTTP server. Defaults to "/".
 `httpHeaders`: Custom headers to set in the request. HTTP allows repeated headers.
 `port`: Name or number of the port to access on the container. Number must be in the range 1 to 65535.
 `protocol`: Protocol to use for the probe request. Defaults to `HTTP1`. Set to `HTTP2` to probe over HTTP/2 cleartext (h2c). Requires the `H2CContainerProbe` feature gate to be enabled.
- [KA-B009: Liveness probe port not in container ports](https://patrykgolabek.dev/tools/k8s-analyzer/rules/ka-b009) — The liveness probe references a port that is not declared in the container ports array. This may indicate a misconfiguration where the probe points to the
- [How to Configure Liveness and Readiness Probes Properly](https://oneuptime.com/blog/post/2026-01-24-kubernetes-liveness-readiness-probes/view) — ## Common Mistakes

### Mistake 1: Liveness Probe Checks Dependencies

`# BAD - liveness checks database
livenessProbe:
httpGet:
path: /health # Endpoint checks database
port: 8080`

If the database is down, all pods restart in a loop. Use readiness for dependencies.

`# GOOD - liveness only checks app process
livenessProbe:
httpGet:
path: /healthz # Only checks process is alive
port: 8080
readinessProbe:
httpGet:
path: /ready # Checks database connection
port: 8080`

### Mistake 2: Initial Delay Too Short

`# BAD - probe starts before app is ready
livenessProbe:
httpGet:
path: /healthz
port: 8080
initialDelaySeconds: 0 # Too aggressive`

Container restarts in a loop because probe starts before app initializes. [...] `# GOOD - use startup probe or appropriate delay
startupProbe:
httpGet:
path: /healthz
port: 8080
failureThreshold: 30
periodSeconds: 10
livenessProbe:
httpGet:
path: /healthz
port: 8080
periodSeconds: 10`

### Mistake 3: Timeout Too Short

`# BAD - 1 second timeout
livenessProbe:
httpGet:
path: /healthz
port: 8080
timeoutSeconds: 1 # Too short for slow endpoints`

Probe fails during normal load spikes.

`# GOOD - reasonable timeout
livenessProbe:
httpGet:
path: /healthz
port: 8080
timeoutSeconds: 5`

### Mistake 4: Dependency-Checking Probe for Liveness and Readiness

`# BAD - shared endpoint checks dependencies
livenessProbe:
httpGet:
path: /health
port: 8080
readinessProbe:
httpGet:
path: /health
port: 8080` [...] ## Complete Example

`apiVersion: apps/v1
kind: Deployment
metadata:
name: web-app
spec:
replicas: 3
selector:
matchLabels:
app: web
template:
metadata:
labels:
app: web
spec:
containers:
- name: app
image: myapp:v1
ports:
- containerPort: 8080
# Startup probe - allow slow initialization
startupProbe:
httpGet:
path: /healthz
port: 8080
failureThreshold: 30
periodSeconds: 10
# Liveness probe - is the process healthy?
livenessProbe:
httpGet:
path: /healthz
port: 8080
periodSeconds: 10
timeoutSeconds: 5
failureThreshold: 3
# Readiness probe - can we handle traffic?
readinessProbe:
httpGet:
path: /ready
port: 8080
periodSeconds: 5
timeoutSeconds: 3
failureThreshold: 3
resources:
requests:
memory: "256Mi"
cpu: "100m"
limits:
memory: "512Mi"
cpu: "500m"`
- [Troubleshooting Kubernetes Liveness and Readiness Probe Failures](https://resolve.ai/glossary/how-to-debug-kubernetes-probe-issues) — 1. The app serves HTTPS but the probe's scheme is HTTP
2. The health endpoint sits behind auth middleware that returns 401 or 403, both of which land outside the 200 to 399 success range.

These mismatches creep in when application code changes without the manifest, or when manifests get copied between apps. Named ports add a layer of complexity as a probe can reference a `containerPort` by name, so the mismatch hides behind the name.

```
livenessProbe: httpGet: path: /healthz # Does this path exist? port: web # Which containerPort does "web" resolve to? scheme: HTTPS # Only if the app actually serves TLS on this port 
``` [...] ### gRPC probes

Native gRPC probes went stable in Kubernetes 1.27, after shipping as beta in 1.24. Before native support, the options were TCP probes, which prove nothing about gRPC health, or bundling `grpc_health_probe` into the image as an exec probe.

```
livenessProbe: grpc: port: 9090 initialDelaySeconds: 10 periodSeconds: 10 
```

Two gotchas. The `port` field takes a number only, named ports don't work here. And the kubelet dials without TLS, so the health port needs to accept plaintext connections. There's also an optional `service` field, which lets a single port back separate liveness and readiness checks by name.

## What are the common causes of probe failures?

A probe failure points at one of five places: [...] Here's a full manifest that puts the rest together:

```
apiVersion: v1 kind: Pod metadata: name: my-app labels: app: my-app spec: containers: - name: my-app image: registry.example.com/my-app:1.4.2 ports: - name: web containerPort: 8080 readinessProbe: httpGet: path: /ready # Checks dependencies port: web periodSeconds: 5 timeoutSeconds: 3 successThreshold: 2 livenessProbe: httpGet: path: /healthz # Process health only port: web initialDelaySeconds: 30 periodSeconds: 10 timeoutSeconds: 5 failureThreshold: 3 
```
- [Configure Liveness, Readiness and Startup Probes | Kubernetes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes) — ```
ports: ports: ports:  - name: liveness-port - name: liveness-port  name:  liveness-port   containerPort: 8080  containerPort: 8080  containerPort:  8080     livenessProbe: livenessProbe:  livenessProbe:   httpGet:  httpGet:  httpGet:   path: /healthz  path: /healthz  path:  /healthz   port: liveness-port  port: liveness-port  port:  liveness-port   failureThreshold: 1  failureThreshold: 1  failureThreshold:  1   periodSeconds: 10  periodSeconds: 10  periodSeconds:  10     startupProbe: startupProbe:  startupProbe:   httpGet:  httpGet:  httpGet:   path: /healthz  path: /healthz  path:  /healthz   port: liveness-port  port: liveness-port  port:  liveness-port   failureThreshold: 30  failureThreshold: 30  failureThreshold:  30   periodSeconds: 10  periodSeconds: 10  periodSeconds:  10 [...] apiVersion: v1 apiVersion: v1 apiVersion:  v1  kind: Pod kind: Pod  kind:  Pod  metadata: metadata:  metadata:   name: goproxy  name: goproxy  name:  goproxy   labels:  labels:  labels:   app: goproxy  app: goproxy  app:  goproxy  spec: spec:  spec:   containers:  containers:  containers:   - name: goproxy  - name: goproxy  name:  goproxy   image: registry.k8s.io/goproxy:0.1  image: registry.k8s.io/goproxy:0.1  image:  registry.k8s.io/goproxy:0.1   ports:  ports:  ports:   - containerPort: 8080  - containerPort: 8080  containerPort:  8080   readinessProbe:  readinessProbe:  readinessProbe:   tcpSocket:  tcpSocket:  tcpSocket:   port: 8080  port: 8080  port:  8080   initialDelaySeconds: 15  initialDelaySeconds: 15  initialDelaySeconds:  15   periodSeconds: 10  periodSeconds: 10 [...] apiVersion: v1 apiVersion: v1 apiVersion:  v1  kind: Pod kind: Pod  kind:  Pod  metadata: metadata:  metadata:   name: h2c-app  name: h2c-app  name:  h2c-app  spec: spec:  spec:   containers:  containers:  containers:   - name: app  - name: app  name:  app   image: registry.k8s.io/e2e-test-images/agnhost:2.64.0  image: registry.k8s.io/e2e-test-images/agnhost:2.64.0  image:  registry.k8s.io/e2e-test-images/agnhost:2.64.0   command: ["/agnhost", "h2c-server", "--port=8080"]  command: ["/agnhost", "h2c-server", "--port=8080"]  command:  ["/agnhost",  "h2c-server",  "--port=8080"]   ports:  ports:  ports:   - containerPort: 8080  - containerPort: 8080  containerPort:  8080   livenessProbe:  livenessProbe:  livenessProbe:   httpGet:  httpGet:  httpGet:   path: /healthz  path: /healthz  path:
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
``` [...] ```
apiVersion: apps/v1 kind: Deployment metadata: name: api spec: replicas: 3 selector: matchLabels: app: api template: metadata: labels: app: api spec: containers: - name: api image: example/api:1.0.0 ports: - name: http containerPort: 8080 startupProbe: httpGet: path: /startupz port: http periodSeconds: 5 timeoutSeconds: 2 failureThreshold: 24 readinessProbe: httpGet: path: /readyz port: http periodSeconds: 5 timeoutSeconds: 2 failureThreshold: 3 successThreshold: 1 livenessProbe: httpGet: path: /livez port: http periodSeconds: 10 timeoutSeconds: 2 failureThreshold: 3
```