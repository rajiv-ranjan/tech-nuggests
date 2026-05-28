


link to follow for deployment and confioguration: https://docs.redhat.com/en/documentation/openshift_container_platform/4.20/html-single/network_observability/index#network-observability-overview


We need 
- Loki Operator
- AMQ Streams Operator

Console will have:
- Topology view
- Traffic flow table

> Network Observability CLI can be used to visualise the network flow and packet that relies on eBPF agents.

## Installation:

### [Install loki operator](https://docs.redhat.com/en/documentation/openshift_container_platform/4.20/html-single/network_observability/index#network-observability-loki-installation_network_observability)

- create the secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: netobserv-loki-store-minio-secret
  namespace: netobserv   
stringData:
  access_key_id: minio
  access_key_secret: minio123
  bucketnames: netobserv-loki-store
  endpoint: https://minio-api-minio.apps.cluster-njsll.njsll.sandbox2550.opentlc.com
  region: eu-central-1
```

- create the lokiStack object

```yaml
apiVersion: loki.grafana.com/v1
kind: LokiStack
metadata:
  name: loki
  namespace: netobserv 
spec:
  size: 1x.small 
  storage:
    schemas:
    - version: v13
      effectiveDate: '2025-12-21'
    secret:
      name: netobserv-loki-store-minio-secret
      type: s3
  storageClassName: gp3-csi 
  tenants:
    mode: openshift-network
```

- Creating a new group for the cluster-admin user role 

```bash
oc adm groups new cluster-admin
oc adm groups add-users cluster-admin admin
oc adm policy add-cluster-role-to-group cluster-admin cluster-admin
```

- Custom admin group access 

```bash

```