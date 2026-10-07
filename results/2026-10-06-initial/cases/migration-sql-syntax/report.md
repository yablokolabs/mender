# Root cause: Checkout service health checks validate only configuration, not database connectivity

Service `checkout` in namespace `shop`.

## Root cause
Both readiness and liveness probes target /healthz, which only checks that DB_HOST ends with '.shop.svc.cluster.local' and log_level is allowed — it never verifies actual database reachability [3].

## Mechanism
1. Deployment defines identical readinessProbe and livenessProbe both hitting HTTP GET /healthz on port 8080. 2. The handler's healthcheck() function (service.py) returns 200 if the configured DB_HOST has the expected suffix and log_level is valid, without opening a connection to the database. 3. Kubernetes marks pods Ready and alive based on these 200 responses. 4. If the database becomes unreachable (wrong DNS, network partition, DB down), the probes still succeed, so traffic continues to be routed to pods that cannot serve checkout requests — exactly the 'healthy but broken' scenario described in [3].

Confidence: 0.85 · Labels: probe_config, healthcheck_design, false_healthy, readiness_liveness_conflation

## Evidence relied on
- readinessProbe.httpGet.path == /healthz
- livenessProbe.httpGet.path == /healthz
- healthcheck() only validates db_host suffix and log_level
- search result [3]: health checks return 200 while 0 successful payments, 100% failure rate

## Tavily sources
Queries: Kubernetes readiness probe liveness probe /healthz 200 but service unhealthy known issues; mender-demo-app:1.0.0 healthcheck returns 500 for valid config secret key length; ConfigMap secretKeyRef env validation failure Kubernetes deployment
- [Troubleshooting Kubernetes Liveness and Readiness Probe Failures](https://resolve.ai/glossary/how-to-debug-kubernetes-probe-issues) — 1. The app serves HTTPS but the probe's scheme is HTTP
2. The health endpoint sits behind auth middleware that returns 401 or 403, both of which land outside the 200 to 399 success range.

These mismatches creep in when application code changes without the manifest, or when manifests get copied between apps. Named ports add a layer of complexity as a probe can reference a `containerPort` by name, so the mismatch hides behind the name.

```
livenessProbe: httpGet: path: /healthz # Does this path exist? port: web # Which containerPort does "web" resolve to? scheme: HTTPS # Only if the app actually serves TLS on this port 
``` [...] When liveness failures repeat, `kubectl get pods` shows the pod in `CrashLoopBackOff` with a climbing restart count. CrashLoopBackOff means the kubelet is backing off exponentially between restarts; the `Unhealthy` events above tell you why the restarts keep happening. And if the pod is stuck in Pending, its probes haven't run at all and the problem sits earlier in the lifecycle, in scheduling, image pulls, or volumes, not in the health checks.

If the pod is running but probes fail, test the endpoint by hand:

```
kubectl exec -it my-app-xyz123 -- curl -v  
```

Success here with failing probes points to timing (probes fire before the app is ready), timeout (curl will wait longer than the 1-second default), or interception (the network bucket above). [...] ## What mechanisms can probes use?

Each probe uses one of four mechanisms:

 HTTP GET: the kubelet sends a request to a path and port. Status codes 200 through 399 count as success, everything else fails.
 TCP socket: the kubelet tries to open a connection to a port. If the socket opens, the probe passes. That's the entire check, so TCP probes pass on applications that accept connections but can't serve anything, which makes them a weak liveness signal for hung apps.
 Exec: the kubelet runs a command inside the container. Exit code 0 is success, anything else fails.
 gRPC: the kubelet calls the container's gRPC health checking service on a port and treats a `SERVING` response as success.

### gRPC probes
- [Probes (Health Checks) | The Kubernetes Visual Handbook](https://k8s.info/docs/intermediate/health-checks) — 4. Use different endpoints for liveness and readiness. A `/healthz` endpoint that returns 200 if the process is alive, and a `/ready` endpoint that also verifies database connections and downstream dependencies.
5. Set PDBs on all production workloads. Even if you have 10 replicas, a node drain can evict multiple pods on the same node simultaneously. PDBs ensure controlled disruption.
6. Monitor probe failures. Frequent readiness probe failures often indicate your application is under-provisioned or has dependency problems. Track these metrics in your monitoring stack.
7. Test your probes. Run `kubectl describe pod`  and look at the Events section. Failed probes appear as `Unhealthy` events with details about which probe failed and why. [...] 1. Always use readiness probes for any pod that receives traffic through a Service. Without readiness probes, pods receive traffic the moment the container starts, before your application is ready.
2. Use startup probes instead of large `initialDelaySeconds` values. Startup probes give your application as long as it needs to start while still allowing fast failure detection after startup.
3. Keep health endpoints fast. Liveness endpoints should respond in under 200ms. If your health check takes multiple seconds, increase `timeoutSeconds` accordingly and investigate why it is slow. [...] ## Common Pitfalls​

1. Liveness probe checks external dependencies. If your liveness probe calls the database and the database goes down, every pod restarts in a cascade. The database comes back, all pods start simultaneously and overwhelm it. Use readiness probes for dependency checks.

2. Liveness probe is too aggressive. Setting `periodSeconds: 1` with `failureThreshold: 1` means one slow response triggers a restart. Applications under load may occasionally have slow health check responses. Give your application room to breathe with `failureThreshold: 3` and a reasonable `timeoutSeconds`.
- [The Health Check That Always Returned 200 OK (Even When Everything Was Broken)](https://medium.com/lets-code-future/the-health-check-that-always-returned-200-ok-even-when-everything-was-broken-ba92b7a8b1d5) — 14:01:33 GET /health → 200 OK  
14:01:43 GET /health → 200 OK  
... [every 10 seconds, perfectly healthy]  
``` Kubernetes saw:   
- Pod responding to health checks ✓  
- Liveness probe passing ✓  
- Readiness probe passing ✓  
- Pod status: Healthy ✓ Reality:   
- 0 successful payments  
- 2,847 failed transactions  
- $47,000 in lost sales  
- 100% payment failure rate For 47 minutes, Kubernetes thought everything was fine. Red flag #2: When your monitoring says "healthy" but customers can't use your service, your health checks are checking the wrong things.## 2:48 PM: The Customer Support Alert2:48 PM: Customer support couldn't ignore it anymore.  
```  
@channel Urgent: Multiple users reporting checkout broken  
"Payment page won't load"  
"Card declined but I know it works" [...] No alerts. No pod restarts. No indication anything was wrong.

Why?

1.   Liveness probe passing → Kubernetes didn’t restart pods
2.   Readiness probe passing → Load balancer kept sending traffic
3.   Health check returning 200 → Monitoring showed green
4.   No external service checks → Nobody knew Stripe was unreachable

The perfect storm of false positives.

## What the Health Check Should Have Been

The WRONG way (what we had):

java

@GetMapping("/health")  
public ResponseEntity<String> health() {  
 // Just confirms HTTP server is responding  
 return ResponseEntity.ok("OK");  
}
The RIGHT way:

java [...] Sitemap

Open in app

Sign up

Sign in



## Liveness vs readiness probes — and why ‘return OK’ is not a health check strategy

Image 4: Software Systems Notes

Software Systems Notes

Follow

12 min read

·

Mar 30, 2026

  
public ResponseEntity<String> health() {  
 return ResponseEntity.ok("OK");  
}
It always returned 200 OK. Even when the payment gateway was unreachable. Even when payments were failing. Even when everything was broken.

2:55 PM: Realized Kubernetes thought the service was healthy because the health check said so.

3:00 PM: Discovered we’d lost $47,000 in sales during those 47 minutes because customers couldn’t check out.

3:15 PM: Learned the difference between “server is responding” and “service is working.”
- [LivenessProbe is unhealthy but Kubernetes Health Check still success? - Consul - HashiCorp Discuss](https://discuss.hashicorp.com/t/livenessprobe-is-unhealthy-but-kubernetes-health-check-still-success/33680) — `kubectl get pods`

Thanks for your reply.  
TTL health check mainly sync readiness status of K8s.

If I want to add another more probes and listed in Consul UI, I should to write the ‘Checks’ and import it through by -config-dir, right?

At the moment, we don’t allow you to specify custom checks for your service on the service mesh. We haven’t seen a use case when you’d need to do that. You can’t provide it via config-dir because the controller that auto-registers services on the service mesh will overwrite that.

If you need that as a feature, then could you create an issue in the hashicorp/consul-k8s repo and describe your use case?

Thanks for your reply again. [...] Thanks a lot!

Hey @chiyt27

We only sync the readiness status of the pod to Consul as described in these docs. This is also consistent with how Kubernetes shows status of your pod if your run `kubectl get pods` . When a liveness probe is failing, it’ll still show that your container status is running and that the containers are ready. You should also configure a readiness probe for your use case which will signal to both the Kubernetes cluster and the Consul service mesh when your application can receive traffic. This is consistent with how Kubernetes will route traffic to pods as well if you were just to deploy your applications without the mesh. Please see these docs on the purpose of each probe.

`kubectl get pods` [...] ### Related topics

| Topic |  | Replies | Views | Activity |
 ---  --- 
| Unhealthy pods are not removed from consul on k8s  Consul k8s ,  azure | 4 | 1256 | December 11, 2020 |
| Intermittent 503 Liveness and Readiness Probe Health Check  Consul service-mesh | 3 | 2417 | August 23, 2025 |
| Install consul by helm chart - Readiness probe failed  Consul | 1 | 289 | April 12, 2024 |
| Custom health check with consul helm and k8s  Consul | 2 | 399 | September 8, 2020 |
| Healthcheck failed on main container after integrating consul  Consul | 3 | 1120 | April 1, 2023 |

Powered by Discourse, best viewed with JavaScript enabled
- [Kubernetes Health Probes Done Right: Liveness, Readiness, and Startup (2026 Guide) - DEV Community](https://dev.to/young_gao/kubernetes-health-probes-done-right-liveness-readiness-and-startup-5g7g) — (err){return{status: ' unhealthy ', message:(err as Error). message};}} export function registerHealthRoutes(app: FastifyInstance, deps: HealthDeps){// Liveness: is the process alive and not deadlocked? app. get('/healthz ', async (_req, reply) =>{reply. code(200). send({status: ' alive '});});// Readiness: can we serve traffic? app. get('/readyz ', async (_req, reply) =>{const[db, redis] = await Promise. all([checkDb(deps. db), checkRedis(deps. redis),]); const ready = db. status === ' healthy ' && redis. status === ' healthy '; reply. code(ready ? 200: 503). send({status: ready ? ' ready ': ' not_ready ', checks:{db, redis},});});// Startup: has initialization completed? let startupComplete = false; app. get('/startupz ', async (_req, reply) =>{if (startupComplete){return reply. [...] Notice: the liveness probe does zero I/O. It confirms the HTTP server can respond. That's it.

## A Better Liveness Probe

The basic version above works, but you can detect event loop stalls:

```
// event-loop-monitor.ts let lastTick = Date. now(); const MAX_DELAY_MS = 3000; setInterval(() =>{lastTick = Date. now();}, 1000); export function isEventLoopHealthy(): boolean{return Date. now() - lastTick< MAX_DELAY_MS;}// In your route: app. get('/healthz ', async (_req, reply) =>{if (! isEventLoopHealthy()){return reply. code(503). send({status: ' stuck ', detail: ' event loop stalled '});} reply. code(200). send({status: ' alive '});});
```

This catches the real failure mode: CPU-bound work or a synchronous call blocking the loop.

## Graceful Degradation [...] ```
function timeout(ms: number): Promise< never>{return new Promise((_, reject) => setTimeout(() => reject(new Error(`Timeout after ${ms} ms`)), ms));} async function checkWithTimeout(check:() => Promise< CheckResult>, ms: number): Promise< CheckResult>{try{return await Promise. race([check(), timeout(ms)]);} catch{return{status: ' unhealthy ', message: `timed out after ${ms} ms`};}}
```

Set check timeouts lower than the probe's `timeoutSeconds`. If your probe times out at 3s, timeout your checks at 2s so you return a meaningful error instead of a generic timeout.

## Common Mistakes

1. Liveness probe checks the database. Database goes down, all pods restart in a loop, now you have zero capacity when the DB recovers.
- [Mender Server Enterprise | Mender documentation](https://docs.mender.io/release-information/release-notes-changelog/mender-server-enterprise) — Resetting the password for an email that does not exist no longer renders an error. All internal error messages are masked and return 500 instead of 400.
 Stop user from having similar email and password (MEN-6462) (3fa4a43) by @bahaa-ghazal
 Implement signal handler for `server` commands (QA-782) (6e17ada) by @bahaa-ghazal
 Implement signal handler for tenantadm's `server` command (QA-782) (927d9a2) by @bahaa-ghazal
 Deviceauth healthcheck panics malformed inventory address (70d493a) by @alfrunes
 Use internal URLs for storage backend when generating artifacts (MEN-7939) (3d72d5e) by @alfrunes

  + BREAKING: Generate artifacts API ignores `storage.proxy_uri` and `aws.external_url` configuration values and instead access the API using the same URL as deployments service. [...] New changes in tenantadm since 1.0.0:

 stripe-go library updated
 api/http: New endpoint for creating inactive organization.
 Endpoint for removing inactive organization
 api/http: management endpoint for activating organization and updating org CC info
 store: Update to official mongodb driver

#### useradm (1.10.0)

New changes in useradm since 1.9.1:

 store/mongo: handle mongodb client creation error

#### useradm-enterprise (1.10.0)

New changes in useradm-enterprise since 1.9.1:

 Support for older Google authenticators on iOS, trimming secret length
 FIX: Create user panics when tenant-id is not specified
 store/mongo: handle mongodb client creation error

#### workflows (1.0.0) [...] The generated key is serialized using (RFC5915) ASN.1 encoding, but encoded to PEM using PKCS8 (RFC5208) block header/trailer. (MEN-7478, SEC 1)
 (tenantadm) New flag automigrate to run migrations before starting server. (MEN-6999)
 (tenantadm) Organization name can be maximum 100 characters and email can be no longer than 254 characters. (MEN-6883)
 (tenantadm) Too long HTTP errors causes `sync-tenants` CLI command to hang (MEN-7105)
 (tenantadm) Prevent syncing multi-tenant users more than once (MEN-7173)
 (tenantadm) Incorrect timestamp parsing when creating organization (MEN-7399)
 (tenantadm) Proper server-side recaptcha response validation (MEN-7400)
 (tenantadm) internal tenant removal endpoint should not return 500 on not found error (MEN-7321)
- [Mender Server on ODYSSEY - X86 | Seeed Studio Wiki](https://wiki.seeedstudio.com/Mender-Server-ODYSSEY-X86) — ### Minio​

The keys MINIO\_ACCESS\_KEY and MINIO\_SECRET\_KEY control credentials for uploading artifacts into the object store. Since Minio is a S3 API compatible service, these settings correspond to Amazon's AWS Access Key ID and Secret Access Key respectively

 Step 1. We need to generate a secret key with length 16. There are 2 ways to do this

Method 1:

1. If you have access to a Linux machine, install pwgen utlity first

```
sudo apt install pwgen sudo  apt  install  pwgen
```

1. After that generate a 16 length random secret key

```
pwgen 16 1 pwgen 16  1
```

Method 2:

Type a random 16-length secret key by yourself. It needs to have numbers, upper and lower case characters

 Step 2. Replace the above secret key with this command [...] Step 2. Replace the above secret key with this command

```
MINIO_SECRET_KEY_GENERATED=<secret key-generated> MINIO_SECRET_KEY_GENERATED =<secret key-generated>
```

 Step 3. Insert the access and secret keys into config/prod.yml with the following commands

```
sed -i.bak "s/MINIO_ACCESS_KEY:./MINIO_ACCESS_KEY: mender-deployments/g" config/prod.yml sed  -i.bak  "s/MINIO_ACCESS_KEY:./MINIO_ACCESS_KEY: mender-deployments/g" config/prod.ymlsed -i.bak "s/MINIO_SECRET_KEY:./MINIO_SECRET_KEY: $MINIO_SECRET_KEY_GENERATED/g" config/prod.yml sed  -i.bak  "s/MINIO_SECRET_KEY:./MINIO_SECRET_KEY: $MINIO_SECRET_KEY_GENERATED/g" config/prod.yml
```

### Deployments Service​
- [Mender Server | Mender documentation](https://docs.mender.io/release-information/release-notes-changelog/mender-server) — New changes in tenantadm since 1.0.0:

 stripe-go library updated
 api/http: New endpoint for creating inactive organization.
 Endpoint for removing inactive organization
 api/http: management endpoint for activating organization and updating org CC info
 store: Update to official mongodb driver

#### useradm (1.10.0)

New changes in useradm since 1.9.1:

 store/mongo: handle mongodb client creation error

#### useradm-enterprise (1.10.0)

New changes in useradm-enterprise since 1.9.1:

 Support for older Google authenticators on iOS, trimming secret length
 FIX: Create user panics when tenant-id is not specified
 store/mongo: handle mongodb client creation error

#### workflows (1.0.0) [...] demo script, include docker-compose.connect.yml by default (MEN-4357)
 Add auditlogs and deviceconnect to production templates
 migrated gateway service to use traefik
 production template: configure mender-api-gateway as a storage proxy
 Include the configuration add-on in the demo script
 Remove nginx-based api-gateway and replace with Traefik.
 fix auth verification on useradm APIs (MEN-4623)
 Upgrade auditlogs to 1.1.0.
 Upgrade create-artifact-worker to 1.0.2.
 Upgrade deployments to 2.3.0.
 Upgrade deployments-enterprise to 2.3.0.
 Upgrade deviceauth to 2.6.0.
 Add deviceconfig 1.0.0.
 Upgrade deviceconnect to 1.1.0.
 Upgrade gui to 2.7.0.
 Upgrade integration to 2.7.0.
 Upgrade inventory to 2.3.0.
 Upgrade inventory-enterprise to 2.3.0.
 Upgrade mender to 2.6.0. [...] (deployments) Compatibility with MongoDB > 5.0 (MEN-6956)
 (deviceauth) Handling preauthorized auth set when device is accepted
 (deviceauth) The previous behavior was putting the device in a conflicting state and returning 500 errors on auth requests. With this commit, the preauthorized auth set will take precedence and take over as the accepted auth set. (ALV-213)
 (deviceauth) Wrong Content-Type header on successful authentication
 (deviceauth) On success, the Content-Type header is set to `application/jwt` instead of invalid `application/json` on 200 responses to POST /api/devices/v1/authentication/auth\_requests (MEN-6912)
 (deviceauth) Preauthorize force behavior applies to existing auth sets
- [Certificates and keys | Mender documentation](https://docs.mender.io/server-installation/overview/certificates-and-keys) — ##### Generate the key

Let's choose a key of type RSA, length `2048` bits, and id `5539`. The latter being arbitrary, positive, non-zero integer which uniquely identifies the key in the file.

```
openssl genrsa -out /etc/useradm/rsa/private.id.5539.pem 2048
```

In the above command, the file name format `private.id.XXXX.pem` is no accident. This default (and configurable) pattern that allows the service to determine where the id is in the file name. Please note that setting id to `0` can make the old JWTs (from before the introduction of `kid`) not work anymore.

There is no limitation on the keys' type; you can use and mix all the supported types.

##### Configure the service [...] Clear History   
  Mender on Github

Server installation     Overview     Certificates and keys

Edit

# Certificates and keys

tutorial

In order to secure the client-server and inter-service communication, Mender leverages public key cryptography. Several key pairs are used and each key pair consists of a public key, which in some cases has a certificate that is shared with other services, and a private key, which is kept secret by the service. All keys are encoded in the PEM format. The public keys are shared in the standard X.509 certificate format, `cert.crt` below, while private keys are seen as `private.key` below.

See the architecture for schematics of the service communication flow. An overview of the components that use keys and for which purpose can be seen below. [...] ##### Configure the service

Once done, we can configure the User Administration Service to use the new key by setting `USERADM_SERVER_PRIV_KEY_PATH="/etc/useradm/rsa/private.id.5539.pem"`. Please note that we did not touch the existing default key, which (by default) rests in `/etc/useradm/rsa/private.pem` (this is also configurable). At this point we will sign all new JWTs with the key of id `5539` and they will carry `kid=5539`, and all the JWTs that do not have `kid` or have `kid=0` will be verified against the default `/etc/useradm/rsa/private.pem`.
- [Mender client testing on solidrun with Mender demo server](https://hub.mender.io/t/mender-client-testing-on-solidrun-with-mender-demo-server/505) — We already provide “demo certificates” for usage with demo environment and you can not use custom keys/certificates in this case. ramu April 26,
- [Resolve Common Kubernetes Deployment Errors | SFEIR Institute](https://institute.sfeir.com/en/kubernetes-training/resolve-errors-deployment-kubernetes) — ### Causes and Solutions

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

## ImagePullBackOff: Image Not Found {#imagepullbackoff} [...] ```
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
| Incorrect subPath | Verify path spelling |
- [How to Fix CreateContainerConfigError from Misconfigured Secrets](https://oneuptime.com/blog/post/2026-02-09-createcontainerconfigerror-secrets/view) — ## On this page

CreateContainerConfigError prevents pods from starting by blocking container creation before the container can run. This error typically indicates problems with how containers reference Secrets, ConfigMaps, or volumes. The pod reaches the phase where Kubernetes tries to configure the container runtime, but validation fails due to missing or misconfigured references.

Understanding the specific causes and implementing proper validation prevents these configuration errors from reaching production environments.

## Understanding CreateContainerConfigError [...] ```
# Check for ConfigMap kubectl get configmap app-config -n default # View ConfigMap keys kubectl get configmap app-config -n default -o jsonpath='{.data}' | jq keys # Create missing ConfigMap kubectl create configmap app-config \ --from-literal=log-level=info \ --from-file=config.yaml=./config.yaml \ -n default
```

For environment variables from ConfigMaps, verify key names.

```
apiVersion: v1 kind: Pod metadata: name: myapp spec: containers: - name: app image: myapp:v1.0 env: - name: LOG_LEVEL valueFrom: configMapKeyRef: name: app-config key: log-level # Must match key in ConfigMap
```

When mounting ConfigMaps as volumes, ensure referenced ConfigMaps exist. [...] Check that the Secret contains the referenced key.

```
# List keys in Secret kubectl get secret app-secrets -n default -o jsonpath='{.data}' | jq keys # Output should include: ["api-key", "database-password"] # If key is missing, update the Secret kubectl create secret generic app-secrets \ --from-literal=database-password=secretpass123 \ --from-literal=api-key=key_abc123xyz \ --dry-run=client -o yaml | kubectl apply -f -
```

## Resolving ConfigMap Reference Errors

ConfigMap errors follow similar patterns to Secret errors. Verify ConfigMaps exist and contain referenced keys.
- [Kubernetes Configmap Error validating data: unknown](https://stackoverflow.com/questions/72844844/kubernetes-configmap-error-validating-data-unknown) — one way to trigger some validation error here, would be to forget some quotes in your ConfigMap: If values for any given key could be casted as
- [ConfigMap error handling in deployments : r/kubernetes](https://www.reddit.com/r/kubernetes/comments/j0zjcd/configmap_error_handling_in_deployments) — ConfigMap error handling in deployments. In my depoyment file I mount a ConfigMap in a volume and set environment variables in my container.
- [How to Fix 'Configuration Management' Issues](https://oneuptime.com/blog/post/2026-01-24-configuration-management-issues/view) — Fix the key reference in your deployment:

```
# Problem: Key name mismatch env: - name: DATABASE_HOST valueFrom: configMapKeyRef: name: myapp-config key: database_host # Wrong: uses underscore # Fix: Use the correct key name env: - name: DATABASE_HOST valueFrom: configMapKeyRef: name: myapp-config key: database.host # Correct: uses dot
```

### ConfigMap Updates Not Reflected

By default, environment variables from ConfigMaps are not updated when the ConfigMap changes. Pods must be restarted.

```
# Force a rolling restart to pick up ConfigMap changes kubectl rollout restart deployment/myapp # Or use a hash annotation to trigger updates automatically
```

For automatic updates in a Helm chart, add a ConfigMap hash to your deployment: [...] ## Fixing ConfigMap Issues

ConfigMaps are a common source of configuration problems. Here are the most frequent issues and their solutions.

### ConfigMap Not Found

```
# Check if ConfigMap exists kubectl get configmap myapp-config -n myapp # If missing, the pod events will show the error kubectl describe pod myapp-pod | grep -A5 Events # Create the missing ConfigMap kubectl create configmap myapp-config \ --from-literal=database.host=postgres.db.svc \ --from-literal=cache.host=redis.cache.svc
```

### ConfigMap Key Not Found

```
# List all keys in a ConfigMap kubectl get configmap myapp-config -o json | jq '.data | keys' # Check the exact key name (watch for typos) kubectl get configmap myapp-config -o yaml
```

Fix the key reference in your deployment: [...] ## Best Practices for Configuration Management

Follow these practices to avoid configuration issues:

Use a single source of truth - Store all configuration in version control. Never modify ConfigMaps directly in the cluster.

Validate early and often - Add schema validation to your CI pipeline. Catch type errors and missing required fields before deployment.

Separate secrets from configuration - Use Kubernetes Secrets or external secret managers for sensitive data. Never store passwords in ConfigMaps.

Document configuration options - Maintain documentation for each configuration key, including defaults and valid values: