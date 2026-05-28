# Use Cases

## Config Latest Logging Stack

Install 

- Install minio
- Loki Operator to manage your log store.
- Red Hat OpenShift Logging Operator to manage log collection and forwarding.
- Cluster Observability Operator to manage visualization.

### Install Minio

https://ai-on-openshift.io/tools-and-applications/minio/minio/

```yaml
---
kind: PersistentVolumeClaim
apiVersion: v1
metadata:
  name: minio-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 20Gi
  volumeMode: Filesystem
---
kind: Secret
apiVersion: v1
metadata:
  name: minio-secret
stringData:
  # change the username and password to your own values.
  # ensure that the user is at least 3 characters long and the password at least 8
  minio_root_user: minio
  minio_root_password: minio123
---
kind: Deployment
apiVersion: apps/v1
metadata:
  name: minio
spec:
  replicas: 1
  selector:
    matchLabels:
      app: minio
  template:
    metadata:
      creationTimestamp: null
      labels:
        app: minio
    spec:
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: minio-pvc
      containers:
        - resources:
            limits:
              cpu: 250m
              memory: 1Gi
            requests:
              cpu: 20m
              memory: 100Mi
          readinessProbe:
            tcpSocket:
              port: 9000
            initialDelaySeconds: 5
            timeoutSeconds: 1
            periodSeconds: 5
            successThreshold: 1
            failureThreshold: 3
          terminationMessagePath: /dev/termination-log
          name: minio
          livenessProbe:
            tcpSocket:
              port: 9000
            initialDelaySeconds: 30
            timeoutSeconds: 1
            periodSeconds: 5
            successThreshold: 1
            failureThreshold: 3
          env:
            - name: MINIO_ROOT_USER
              valueFrom:
                secretKeyRef:
                  name: minio-secret
                  key: minio_root_user
            - name: MINIO_ROOT_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: minio-secret
                  key: minio_root_password
          ports:
            - containerPort: 9000
              protocol: TCP
            - containerPort: 9090
              protocol: TCP
          imagePullPolicy: IfNotPresent
          volumeMounts:
            - name: data
              mountPath: /data
              subPath: minio
          terminationMessagePolicy: File
          image: >-
            quay.io/minio/minio:latest
          args:
            - server
            - /data
            - --console-address
            - :9090
      restartPolicy: Always
      terminationGracePeriodSeconds: 30
      dnsPolicy: ClusterFirst
      securityContext: {}
      schedulerName: default-scheduler
  strategy:
    type: Recreate
  revisionHistoryLimit: 10
  progressDeadlineSeconds: 600
---
kind: Service
apiVersion: v1
metadata:
  name: minio-service
spec:
  ipFamilies:
    - IPv4
  ports:
    - name: api
      protocol: TCP
      port: 9000
      targetPort: 9000
    - name: ui
      protocol: TCP
      port: 9090
      targetPort: 9090
  internalTrafficPolicy: Cluster
  type: ClusterIP
  ipFamilyPolicy: SingleStack
  sessionAffinity: None
  selector:
    app: minio
---
kind: Route
apiVersion: route.openshift.io/v1
metadata:
  name: minio-api
spec:
  to:
    kind: Service
    name: minio-service
    weight: 100
  port:
    targetPort: api
  wildcardPolicy: None
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
---
kind: Route
apiVersion: route.openshift.io/v1
metadata:
  name: minio-ui
spec:
  to:
    kind: Service
    name: minio-service
    weight: 100
  port:
    targetPort: ui
  wildcardPolicy: None
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
```

### Loki Operator to manage your log store.

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: logging-loki-s3 
  namespace: openshift-logging
stringData: 
  access_key_id: minio
  access_key_secret: minio123
  bucketnames: ocp-log-store
  endpoint: https://minio-api-minio.apps.cluster-njsll.njsll.sandbox2550.opentlc.com
  region: eu-central-1
```

```yaml
apiVersion: loki.grafana.com/v1
kind: LokiStack
metadata:
  name: logging-loki 
  namespace: openshift-logging 
spec:
  managementState: Managed
  limits:
    global: 
      retention: 
        days: 3 # Set the value as per requirement
  size: 1x.small 
  storage:
    schemas:
    - version: v13
      effectiveDate: "2025-12-01" 
    secret:
      name: logging-loki-s3 
      type: s3 
  storageClassName: gp3-csi
  tenants:
    mode: openshift-logging 

```


### Red Hat OpenShift Logging Operator to manage log collection and forwarding.

```bash
oc create sa logging-collector -n openshift-logging

# the collector is provided permissions to collect logs from both infrastructure and application logs and audit logs
oc adm policy add-cluster-role-to-user logging-collector-logs-writer -z logging-collector -n openshift-logging
oc adm policy add-cluster-role-to-user collect-application-logs -z logging-collector -n openshift-logging
oc adm policy add-cluster-role-to-user collect-infrastructure-logs -z logging-collector -n openshift-logging
oc adm policy add-cluster-role-to-user collect-audit-logs -z logging-collector -n openshift-logging

# not applied so far
oc adm policy add-cluster-role-to-user clusterlogforwarders.observability.openshift.io-v1-admin  -z logging-collector -n openshift-logging

# template command as per documentation
oc adm policy add-cluster-role-to-user <cluster_role_name> system:serviceaccount:<namespace_name>:<service_account_name>


# other forwarder roles. for PoC we can use admin or edit roles.
oc get clusterrole | egrep -i "forwarders"
clusterlogforwarders.observability.openshift.io-v1-admin                                             2025-12-02T09:03:05Z
clusterlogforwarders.observability.openshift.io-v1-crdview                                           2025-12-02T09:03:05Z
clusterlogforwarders.observability.openshift.io-v1-edit                                              2025-12-02T09:03:05Z
clusterlogforwarders.observability.openshift.io-v1-view                                              2025-12-02T09:03:05Z
```

```bash
# check if the clusterroles are binded correctly or not
oc get clusterrolebindings -o custom-columns='NAME:.metadata.name,ROLE:.roleRef.name,SERVICE_ACCOUNT:.subjects[*].name' | grep logging-collector
Found existing global alias for "| grep". You should use: "G"
collect-application-logs                                                    collect-application-logs                                                    logging-collector
collect-audit-logs                                                          collect-audit-logs                                                          logging-collector
collect-infrastructure-logs                                                 collect-infrastructure-logs                                                 logging-collector
logging-collector-logs-writer                                               logging-collector-logs-writer                                               logging-collector
metadata-reader-openshift-logging-logging-collector                         metadata-reader                                                             logging-collector

# another approach
oc get clusterrolebindings -o json | jq -r '.items[] | select(.subjects[]? | .name=="logging-collector" and .namespace=="openshift-logging") | "\(.metadata.name) -> \(.roleRef.name)"'
collect-application-logs -> collect-application-logs
collect-audit-logs -> collect-audit-logs
collect-infrastructure-logs -> collect-infrastructure-logs
logging-collector-logs-writer -> logging-collector-logs-writer
metadata-reader-openshift-logging-logging-collector -> metadata-reader

```

```bash
# command to remove the clusterrole from the logging-collector sa
oc adm policy remove-cluster-role-from-user clusterlogforwarders.observability.openshift.io-v1-edit -z logging-collector -n openshift-logging

```


```yaml
apiVersion: observability.openshift.io/v1
kind: ClusterLogForwarder
metadata:
  name: instance
  namespace: openshift-logging 
spec:
  serviceAccount:
    name: logging-collector 
  filters:
  - name: detect-multiline-exception
    type: detectMultilineException
  outputs:
  - name: lokistack-out
    type: lokiStack 
    lokiStack:
      target: 
        name: logging-loki
        namespace: openshift-logging
      authentication:
        token:
          from: serviceAccount
    tls:
      ca:
        key: service-ca.crt
        configMapName: openshift-service-ca.crt
  pipelines:
  - name: infra-app-logs
    inputRefs: 
    - audit
    - application
    - infrastructure
    filterRefs:
    - detect-multiline-exception
    outputRefs:
    - lokistack-out

```
```yaml
apiVersion: observability.openshift.io/v1
kind: ClusterLogForwarder
metadata:
  name: <log_forwarder_name>
  namespace: <log_forwarder_namespace>
spec:
  outputs:                       
    - name: <output_name>
      type: <output_type>
  inputs:                        
    - name: <input_name>
      type: <input_type>
  filters:                       
    - name: <filter_name>
      type: <filter_type>
  pipelines:
    - inputRefs:
      - <input_name>             
    - outputRefs:
      - <output_name>            
    - filterRefs:
      - <filter_name>            
  serviceAccount:
    name: <service_account_name> 
# ...

```


```bash
# check the schema of the CR 
oc explain ClusterLogForwarder.spec.inputs.audit
GROUP:      observability.openshift.io
KIND:       ClusterLogForwarder
VERSION:    v1

FIELD: audit <Object>


DESCRIPTION:
    Audit, enables `audit` logs.

FIELDS:
  sources	<[]string>
    Sources defines the list of audit sources to collect.
    This field is optional and its exclusion results in the collection of all
    audit sources.

oc explain ClusterLogForwarder.spec.inputs.application
GROUP:      observability.openshift.io
KIND:       ClusterLogForwarder
VERSION:    v1

FIELD: application <Object>


DESCRIPTION:
    Application, named set of `application` logs that
    can specify a set of match criteria

FIELDS:
  excludes	<[]Object>
    Excludes is the set of namespaces and containers to ignore when collecting
    logs.

    Takes precedence over Includes option.

  includes	<[]Object>
    Includes is the set of namespaces and containers to include when collecting
    logs.

    Note: infrastructure namespaces are still excluded for "*" values unless a
    qualifying glob pattern is specified.

  selector	<Object>
    Selector for logs from pods with matching labels.

    Only messages from pods with these labels are collected.

    If absent or empty, logs are collected regardless of labels.

  tuning	<Object>
    Tuning is the container input tuning spec for this container sources

```

```bash
application
Selects logs from all application containers, excluding those in infrastructure namespaces.
infrastructure
Selects logs from nodes and from infrastructure components running in the following namespaces:

default
kube
openshift
Containing the kube- or openshift- prefix
audit
Selects logs from the OpenShift API server audit logs, Kubernetes API server audit logs, ovn audit logs, and node audit logs from auditd.
Users can define custom inputs of type application that select logs from specific namespaces or using pod labels.
```

```bash
# to get the config that is used by the vector
oc get cm instance-config -o jsonpath='{.data.vector\.toml}' -n openshift-logging

```

```bash
# use filters
oc explain ClusterLogForwarder.spec.filters

GROUP:      observability.openshift.io
KIND:       ClusterLogForwarder
VERSION:    v1

FIELD: filters <[]Object>


DESCRIPTION:
    Filters are applied to log records passing through a pipeline.
    There are different types of filter that can select and modify log records
    in different ways.
    See [FilterTypeSpec] for a list of filter types.
    FilterSpec defines a filter for log messages.

FIELDS:
  drop	<[]Object>
    A drop filter applies a sequence of tests to a log record and drops the
    record if any test passes.
    Each test contains a sequence of conditions, all conditions must be true for
    the test to pass.
    A DropTestsSpec contains an array of tests which contains an array of
    conditions

  kubeAPIAudit	<Object>
    KubeAPIAudit filter Kube API server audit logs, as described in [Kubernetes
    Auditing].

    # Policy Filtering

    Policy event rules are the same format as the [Kube Audit Policy] with some
    minor extensions.
    The extensions are described here, see the [Kube Audit Policy] for the
    standard rule behavior.
    Rules are checked in order, checking stops at the first matching rule.

    An audit policy event contains meta-data describing who made the request.
    It can also include the full body of the API request, and the response that
    was sent.
    The `level` of an audit rule determines how much data is included in the
    event:

      - None: the event is dropped.
      - Metadata: Only the audit metadata is included, request and response
    bodies are removed.
      - Request: Audit metadata and the request body are included, the response
    body is removed.
      - RequestResponse: All data is included: metadata, request body and
    response body. Note the response body can be very large.
        For example the a command like `oc get -A pods` generates a response
    body containing the YAML description of every pod in the cluster.

    # Extensions

    The following features are extensions to the standard [Kube Audit Policy]

    ## Wildcards

    Names of users, groups, namespaces, and resources can have a leading or
    trailing '*' character.
    For example namespace 'openshift-*' matches 'openshift-apiserver' or
    'openshift-authentication.
    Resource '*/status' matches 'Pod/status' or 'Deployment/status'

    Events which include both a 'resource' and 'subresource' are evaluated by
    combing those
    fields with a forward slash.  This means rules that rely upon a resource
    type that may or
    may not include the subresource should be adjusted to cover all the required
    use-cases (i.e. ['pod','pod/*']).

    ## Default Rules

    Events that do not match any rule in the policy are filtered as follows:
    - User events (ie. non-system and non-serviceaccount) are forwarded
    - Read-only system events (get/list/watch etc) are dropped
    - Service account write events that occur within the same namespace as the
    service account are dropped
    - All other events are forwarded, subject to any configured [rate
    limits][#rate-lmiting]

    If you want to disable these defaults, end your rules list with rule that
    has only a `level` field.
    An empty rule matches any event, and prevents the defaults from taking
    effect.

    ## Omit Response Codes

    You can drop events based on the HTTP status code in the response. See the
    OmitResponseCodes field.

    [Kube Audit Policy]:
    https://kubernetes.io/docs/reference/config-api/apiserver-audit.v1/#audit-k8s-io-v1-Policy
    [Kubernetes Auditing]:
    https://kubernetes.io/docs/tasks/debug/debug-cluster/audit/

  name	<string> -required-
    Name used to refer to the filter from a "pipeline".

  openshiftLabels	<map[string]string>
    Labels applied to log records passing through a pipeline.
    These labels appear in the `openshift.labels` map in the log record.

  prune	<Object>
    The PruneFilterSpec consists of two arrays, namely in and notIn, which
    dictate the fields to be pruned.

  type	<string> -required-
  enum: openshiftLabels, detectMultilineException, drop, kubeAPIAudit, ....
    Type of filter.

    Possible filter types are:

    1. detectMultilineException - Enables multi-line error detection of
    container logs. No additional configuration required.
    2. drop - Drop whole log records based on the evaluation of a set of regex
    tests. See field `drop` for configuration.
    3. kubeAPIAudit - Remove unwanted audit events and reduce event size to
    create a manageable audit trail. See field `kubeAPIaudit` for configuration.
    4. openshiftLabels - Labels to be applied to log records passing through a
    pipeline. See field `openshiftLabels` for configuration.
    5. parse - Enables parsing of log entries into structured logs. No
    additional configuration required.
    6. prune - Prune log record fields to reduce the size of logs flowing into a
    log store. See field `prune` for configuration.

```



### Cluster Observability Operator to manage visualization.

### Integrate Splunk HEC with OpenShift Logging

https://docs.redhat.com/en/documentation/red_hat_openshift_logging/6.4/html-single/configuring_logging/index#forwarding-logs-to-splunk_configuring-log-forwarding

### Forwarding logs over HTTP endpoint

https://docs.redhat.com/en/documentation/red_hat_openshift_logging/6.3/html-single/configuring_logging/index#logging-http-forward_configuring-log-forwarding

### Filtering the audit and infrastructure log inputs by source 

https://docs.redhat.com/en/documentation/red_hat_openshift_logging/6.3/html-single/configuring_logging/index#input-spec-filter-audit-infrastructure_configuring-log-forwarding

```yaml
apiVersion: observability.openshift.io/v1
kind: ClusterLogForwarder
# ...
spec:
  serviceAccount:
    name: <service_account_name>
  inputs:
    - name: mylogs1
      type: infrastructure
      infrastructure:
        sources: 
          - node
    - name: mylogs2
      type: audit
      audit:
        sources: 
          - kubeAPI
          - openshiftAPI
          - ovn
# ...
```

```bash
Specifies the list of infrastructure sources to collect. The valid sources include:
  node: Journal log from the node
  container: Logs from the workloads deployed in the namespaces

Specifies the list of audit sources to collect. The valid sources include:
  kubeAPI: Logs from the Kubernetes API servers
  openshiftAPI: Logs from the OpenShift API servers
  auditd: Logs from a node auditd service
  ovn: Logs from an open virtual network service

```yaml

### Loki stack injestion sizes

apiVersion: loki.grafana.com/v1
kind: LokiStack
metadata:
  name: logging-loki
  namespace: openshift-logging
spec:
  limits:
    global:
      ingestion:
        ingestionBurstSize: 16 
        ingestionRate: 8 
# ...
```

### Audit logs

Here’s the same table in markdown format that you can directly copy and paste into your existing `.md` file:


| Field | Description |
|--------|--------------|
| level | The audit level at which the event was generated. |
| auditID | A unique audit ID, generated for each request. |
| stage | The stage of the request handling when this event instance was generated. |
| requestURI | The request URI as sent by the client to a server. |
| verb | The Kubernetes verb associated with the request. For non-resource requests, this is the lowercase HTTP method. |
| user | The authenticated user information. |
| impersonatedUser | Optional. The impersonated user information, if the request is impersonating another user. |
| sourceIPs | Optional. The source IPs, from where the request originated and any intermediate proxies. |
| userAgent | Optional. The user agent string reported by the client. Note that the user agent is provided by the client, and must not be trusted. |
| objectRef | Optional. The object reference this request is targeted at. This does not apply for List-type requests, or non-resource requests. |
| responseStatus | Optional. The response status, populated even when the ResponseObject is not a Status type. For successful responses, this will only include the code. For non-status type error responses, this will be auto-populated with the error message. |
| requestObject | Optional. The API object from the request, in JSON format. The RequestObject is recorded as is in the request (possibly re-encoded as JSON), prior to version conversion, defaulting, admission or merging. It is an external versioned object type, and might not be a valid object on its own. This is omitted for non-resource requests and is only logged at request level and higher. |
| responseObject | Optional. The API object returned in the response, in JSON format. The ResponseObject is recorded after conversion to the external type, and serialized as JSON. This is omitted for non-resource requests and is only logged at response level. |
| requestReceivedTimestamp | The time that the request reached the API server. |
| stageTimestamp | The time that the request reached the current audit stage. |
| annotations | Optional. An unstructured key value map stored with an audit event that may be set by plugins invoked in the request serving chain, including authentication, authorization and admission plugins. Note that these annotations are for the audit event, and do not correspond to the metadata.annotations of the submitted object. Keys should uniquely identify the informing component to avoid name collisions, for example podsecuritypolicy.admission.k8s.io/policy. Values should be short. Annotations are included in the metadata level. |

**Sample audit message**
```json
{
  "kind": "Event",
  "apiVersion": "audit.k8s.io/v1",
  "level": "Metadata",
  "auditID": "ad209ce1-fec7-4130-8192-c4cc63f1d8cd",
  "stage": "ResponseComplete",
  "requestURI": "/api/v1/namespaces/openshift-kube-controller-manager/configmaps/cert-recovery-controller-lock?timeout=35s",
  "verb": "update",
  "user": {
    "username": "system:serviceaccount:openshift-kube-controller-manager:localhost-recovery-client",
    "uid": "dd4997e3-d565-4e37-80f8-7fc122ccd785",
    "groups": [
      "system:serviceaccounts",
      "system:serviceaccounts:openshift-kube-controller-manager",
      "system:authenticated"
    ]
  },
  "sourceIPs": ["::1"],
  "userAgent": "cluster-kube-controller-manager-operator/v0.0.0 (linux/amd64) kubernetes/$Format",
  "objectRef": {
    "resource": "configmaps",
    "namespace": "openshift-kube-controller-manager",
    "name": "cert-recovery-controller-lock",
    "uid": "5c57190b-6993-425d-8101-8337e48c7548",
    "apiVersion": "v1",
    "resourceVersion": "574307"
  },
  "responseStatus": {
    "metadata": {},
    "code": 200
  },
  "requestReceivedTimestamp": "2020-04-02T08:27:20.200962Z",
  "stageTimestamp": "2020-04-02T08:27:20.206710Z",
  "annotations": {
    "authorization.k8s.io/decision": "allow",
    "authorization.k8s.io/reason": "RBAC: allowed by ClusterRoleBinding \"system:openshift:operator:kube-controller-manager-recovery\" of ClusterRole \"cluster-admin\" to ServiceAccount \"localhost-recovery-client/openshift-kube-controller-manager\""
  }
}
```

```bash
# command to get the audit logs
oc adm node-logs --role=master --path=openshift-apiserver/

```

**Get Audit level**

```bash
# https://docs.redhat.com/en/documentation/openshift_container_platform/4.18/html-single/security_and_compliance/index#about-audit-log-profiles_audit-log-policy-config
oc get  apiserver cluster -oyaml
```

```yaml
apiVersion: config.openshift.io/v1
kind: APIServer
metadata:
  annotations:
    include.release.openshift.io/ibm-cloud-managed: "true"
    include.release.openshift.io/self-managed-high-availability: "true"
    oauth-apiserver.openshift.io/secure-token-storage: "true"
    release.openshift.io/create-only: "true"
  creationTimestamp: "2025-11-26T07:47:18Z"
  generation: 1
  name: cluster
  ownerReferences:
  - apiVersion: config.openshift.io/v1
    kind: ClusterVersion
    name: version
    uid: 71724d37-2714-4710-84e3-eaf7faf18a9f
  resourceVersion: "910"
  uid: a5dbfa07-8878-4c6c-8a07-ac23791b259c
spec:
  audit:
    customRules:
      - group: system:authenticated:oauth
        profile: WriteRequestBodies
      - group: system:authenticated
        profile: AllRequestBodies
    profile: Default

```

### Anomolous Network Activity

```bash
# run from the pet clinic pod
curl -v -X GET "https://httpbin.org/get" -H "accept: application/json"
```

