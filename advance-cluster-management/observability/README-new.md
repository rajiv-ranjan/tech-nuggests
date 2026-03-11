# Red Hat Advanced Cluster Management 2.15 - Observability Architecture

## Complete Component Diagram

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#ffffff', 'primaryTextColor': '#000000', 'primaryBorderColor': '#000000', 'lineColor': '#000000', 'secondaryColor': '#ffffff', 'tertiaryColor': '#ffffff' }}}%%
flowchart TB
    subgraph MANAGED["Managed Cluster(s)"]
        direction TB
        PROM["OpenShift Prometheus"]
        NE["Node Exporter"]
        KSM["Kube State Metrics"]
        UWM["User Workload Monitoring"]
        
        NE -->|"exposes node metrics"| PROM
        KSM -->|"exposes k8s object metrics"| PROM
        UWM -->|"exposes app metrics"| PROM
        
        subgraph ADDON["Observability Add-on (open-cluster-management-addon-observability)"]
            MC["metrics-collector<br/>(endpoint-metrics-operator)"]
            PA["Prometheus Agent<br/>(COO-based, optional)"]
        end
        
        PROM -->|"scrapes metrics"| MC
        PROM -->|"federates metrics"| PA
    end
    
    subgraph HUB["Hub Cluster (open-cluster-management-observability namespace)"]
        direction TB
        
        subgraph OPERATORS["Operators"]
            MHO["multiclusterhub-operator"]
            MCO["multicluster-observability-operator"]
            OAC["observability-addon-controller"]
            OO["observatorium-operator"]
        end
        
        MHO -->|"deploys"| MCO
        MCO -->|"deploys observability stack"| OO
        MCO -->|"creates ManifestWorks for"| OAC
        OAC -->|"manages add-on lifecycle on<br/>managed clusters"| ADDON
        
        subgraph INGEST["Metrics Ingestion"]
            TRC["thanos-receive-controller"]
            TRD["thanos-receive-default"]:::storage
        end
        
        MC -->|"remote-write metrics via HTTPS"| TRC
        PA -->|"remote-write metrics via HTTPS"| TRC
        TRC -->|"routes & load balances<br/>incoming writes"| TRD
        
        subgraph STORAGE_LAYER["Long-term Storage"]
            OS[("Object Storage<br/>(S3 API Compatible)")]:::storage
            TC["thanos-compactor"]:::storage
        end
        
        TRD -->|"writes to local TSDB,<br/>uploads blocks every 2hrs"| OS
        OS -->|"reads blocks for<br/>compaction & downsampling"| TC
        TC -->|"writes compacted blocks"| OS
        
        subgraph QUERY["Query Path"]
            TSS["thanos-store-shard"]:::storage
            TSM["thanos-store-memcached"]
            TQ["thanos-query"]
            TQF["thanos-query-frontend"]
            TQFM["thanos-query-frontend-memcached"]
        end
        
        OS -->|"serves historical data"| TSS
        TSS -->|"caches block metadata"| TSM
        TQ -->|"fanout queries to<br/>store shards"| TSS
        TQ -->|"queries recent data"| TRD
        TQF -->|"splits & caches<br/>query results"| TQFM
        TQF -->|"forwards optimized queries"| TQ
        
        subgraph RULES["Rule Evaluation"]
            TR["thanos-rule"]:::storage
        end
        
        TR -->|"issues PromQL queries<br/>for rule evaluation"| TQ
        TR -->|"writes rule results<br/>to local TSDB"| TR
        
        subgraph ALERTING["Alerting"]
            AM["alertmanager"]:::storage
        end
        
        TR -->|"sends firing alerts"| AM
        AM -->|"routes notifications"| EXT["External Systems<br/>(Slack, Email, PagerDuty)"]
        
        subgraph API["API & Access Layer"]
            OA["observatorium-api"]
            RBAC["rbac-query-proxy"]
        end
        
        OA -->|"receives API requests"| RBAC
        RBAC -->|"authorized queries"| TQF
        
        subgraph VIZ["Visualization"]
            GR["Grafana"]
        end
        
        GR -->|"queries metrics via<br/>authenticated proxy"| RBAC
    end
    
    %% Storage class styling - colored components
    classDef storage fill:#4a90d9,stroke:#2c5282,stroke-width:3px,color:#ffffff,font-weight:bold
    
    %% Default styling - black and white
    classDef default fill:#ffffff,stroke:#000000,stroke-width:1px,color:#000000
```

## Component Legend

| Symbol | Meaning |
|--------|---------|
| 🔵 Blue boxes | Components requiring persistent storage |
| ⬜ White boxes | Stateless components |
| Arrows | Data flow with relationship description |

## Components Requiring Storage (Colored Blue)

| Component | Storage Type | Purpose |
|-----------|--------------|---------|
| **thanos-receive-default** | Persistent Volume | Writes incoming metrics to local Prometheus TSDB. Acts as a local cache before uploading to object storage every 2 hours. |
| **thanos-compactor** | Persistent Volume | Needs local disk for intermediate data during compaction, downsampling, and bucket state cache. |
| **thanos-rule** | Persistent Volume | Stores rule evaluation results on disk in Prometheus 2.0 storage format. Retention configurable via `RetentionInLocal`. |
| **thanos-store-shard** | Persistent Volume | Keeps small amount of remote block metadata locally. Syncs with bucket on startup. |
| **alertmanager** | Persistent Volume | Stores nflog (notification log) data and silenced alerts. nflog is an append-only log of active/resolved notifications. |
| **Object Storage** | S3-compatible | Primary long-term storage for all metrics and metadata. Stores TSDB blocks uploaded by thanos-receive. |

## Stateless Components

| Component | Description |
|-----------|-------------|
| **multiclusterhub-operator** | Root operator that deploys multicluster-observability-operator |
| **multicluster-observability-operator** | Deploys and manages the entire observability stack |
| **observability-addon-controller** | Manages observability add-on lifecycle on managed clusters via ManifestWorks |
| **observatorium-operator** | Manages Observatorium components |
| **thanos-receive-controller** | Routes and load-balances incoming remote-write requests to receive replicas |
| **thanos-query** | Performs distributed queries across store shards and receivers |
| **thanos-query-frontend** | Query caching, splitting, and optimization layer |
| **thanos-store-memcached** | In-memory cache for store shard block metadata |
| **thanos-query-frontend-memcached** | In-memory cache for query results |
| **observatorium-api** | API gateway for external access |
| **rbac-query-proxy** | Enforces RBAC policies on metric queries |
| **Grafana** | Visualization dashboards (config stored as ConfigMaps) |
| **metrics-collector** | Collects metrics from OCP Prometheus and remote-writes to hub |
| **Prometheus Agent** | COO-based collector for new multicluster observability add-on |

## Data Flow Summary

### Metrics Collection Flow
1. **Node Exporter** & **Kube State Metrics** expose system and Kubernetes object metrics
2. **OpenShift Prometheus** scrapes metrics from exporters and user workloads
3. **metrics-collector** (or **Prometheus Agent**) federates/scrapes from OCP Prometheus
4. Metrics are **remote-written via HTTPS** to **thanos-receive-controller** on hub cluster
5. **thanos-receive-default** writes to local TSDB and uploads blocks to **Object Storage** every 2 hours

### Query Flow
1. **Grafana** user initiates query
2. Query passes through **rbac-query-proxy** for authorization
3. **thanos-query-frontend** caches and optimizes query
4. **thanos-query** fans out to:
   - **thanos-receive-default** for recent data (< 2 hours)
   - **thanos-store-shard** for historical data from Object Storage
5. Results are aggregated and returned

### Alerting Flow
1. **thanos-rule** evaluates Prometheus alerting/recording rules
2. Rules query data via **thanos-query**
3. Firing alerts are sent to **alertmanager**
4. **alertmanager** deduplicates, groups, and routes notifications to external systems

## Component Versions (ACM 2.15)

| Component | Version |
|-----------|---------|
| Grafana | 12.2.0 |
| Thanos | 0.39.2 |
| Prometheus Alertmanager | 0.28.1 |
| Prometheus | 3.5.0 |
| Prometheus Operator | 0.85.0 |
| Kube State Metrics | 2.17.0 |
| Node Exporter | 1.9.1 |
| Memcached Exporter | 0.15.3 |
