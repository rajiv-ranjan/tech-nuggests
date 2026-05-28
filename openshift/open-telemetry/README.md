# Use Cases

## Simple Demo of OTEL

- Install sample apps using [k8s-apps.yaml](k8s-apps.yaml)
- Follow the [link](https://docs.redhat.com/en/documentation/openshift_container_platform/4.19/html-single/red_hat_build_of_opentelemetry/index#install-otel) to:
  - [Installing the Red Hat build of OpenTelemetry Operator.](https://docs.redhat.com/en/documentation/openshift_container_platform/4.19/html-single/red_hat_build_of_opentelemetry/index#installing-otel-by-using-the-web-console_install-otel)
  - Creating a namespace for an OpenTelemetry Collector instance.

    ```yml
    apiVersion: project.openshift.io/v1
    kind: Project
    metadata:
        name: tutorial-application
    ```

  - [Creating an OpenTelemetryCollector custom resource to deploy the OpenTelemetry Collector instance.]() Some useful samples to deploy OpenTelemetry are available [here](https://github.com/os-observability/redhat-rhosdt-samples). Options in brief are:
    - [Mode 1](https://github.com/os-observability/redhat-rhosdt-samples/tree/main/opentelemetry/deployment) `Deployment`: Overall, this configuration sets up an OpenTelemetry collector deployed as a Deployment that receives Jaeger, OTLP, OpenCensus and Zipkin traces, adds Kubernetes attributes, and exports the traces to Tempo via OTLP. [Sample file](https://github.com/os-observability/redhat-rhosdt-samples/blob/main/opentelemetry/deployment/otelcol.yaml) copied to [otel-deployment.yaml](otel-deployment.yaml).
    - [Mode 2]() `Multitenant`: Overall, this configuration sets up an OpenTelemetry collector deployed as a Deployment that receives Jaeger, OTLP, OpenCensus and Zipkin traces, adds Kubernetes attributes, and exports the traces to Tempo via OTLP managing multiple tenants. The OpenTelemetry Collector accepts traces from two tenants: dev and prod. The way to identify the tenants is through the X-Scope-OrgID OTLP header. When the X-Scope-OrgID header is set to dev in the trace, the tenant is dev. When the X-Scope-OrgID header is set to prod in the trace, the tenant is prod. [Sample file](https://github.com/os-observability/redhat-rhosdt-samples/blob/main/opentelemetry/multitenant/otelcol.yaml) is downloaded to [otel-deployment-multitenant.yaml](otel-deployment-multitenant.yaml).
    - [Mode 3]() `Sidecar`: Overall, this configuration sets up an OpenTelemetry collector deployed as a sidecar that receives Jaeger, OTLP, OpenCensus and Zipkin traces, adds Kubernetes attributes, and exports the traces to Tempo via OTLP. The collector is configured to run as a sidecar in the cluster. This means that each pod with the sidecar.opentelemetry.io/inject: "true" annotation will be injected with a sidecar container to treat the traces according to the receivers, processors and exporters. Follow the steps [here](https://github.com/os-observability/redhat-rhosdt-samples/tree/main/opentelemetry/sidecar). [Sample file](https://github.com/os-observability/redhat-rhosdt-samples/blob/main/opentelemetry/sidecar/otelcol.yaml) is downloaded to [otel-deployment-sidecar.yaml](otel-deployment-sidecar.yaml)
    
    ```yml
    apiVersion: opentelemetry.io/v1alpha1
    kind: OpenTelemetryCollector
    metadata:
      name: otel
      namespace: tutorial-application
    spec:
      mode: sidecar
      config: |
        receivers:
          jaeger:
            protocols:
              grpc:
              thrift_binary:
              thrift_compact:
              thrift_http:
          opencensus:
          otlp:
            protocols:
              grpc:
              http:
          zipkin:
        processors:
          batch:
            # Batching helps better compress the data and reduce the number of outgoing
            # connections required to transmit the data.
            # https://github.com/open-telemetry/opentelemetry-collector/blob/main/processor/batchprocessor
          memory_limiter:
            # Prevents out of memory situations on the collector
            # https://github.com/open-telemetry/opentelemetry-collector/tree/main/processor/memorylimiterprocessor
            check_interval: 1s
            limit_percentage: 50
            spike_limit_percentage: 30
          resourcedetection:
            # Adds information detected from the host to the traces
            # https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/processor/resourcedetectionprocessor
            detectors: [openshift]
            timeout: 2s
        exporters:
          otlp:
            # Export the traces to a Tempo instance
            endpoint: "tempo-simplest-distributor:4317"
            tls:
              insecure: true
        service:
          pipelines:
            traces:
              receivers: [jaeger, opencensus, otlp, zipkin]
              processors: [memory_limiter, resourcedetection, batch]
              exporters: [otlp]
    ```
    
- Create `instrumentation` CR

```yml
apiVersion: opentelemetry.io/v1alpha1
kind: Instrumentation
metadata:
  name: java-instrumentation
spec:
  env:
    - name: OTEL_EXPORTER_OTLP_TIMEOUT
      value: "20"
  exporter:
    endpoint: http://production-collector.observability.svc.cluster.local:4317
  propagators:
    - w3c # possible values: tracecontext, baggage, b3, b3multi, jaeger, ottrace, none
          # When using the instrumentation custom resource (CR) with Red Hat OpenShift Service Mesh, you must use the b3multi propagator. 
  sampler:
    type: parentbased_traceidratio
    argument: "0.25"
  # values: apacheHttpd, dotnet, go, java, nodejs, python
  java:
    env:
    - name: OTEL_JAVAAGENT_DEBUG
      value: "true"
```

- Add instrumentation to the app

```yml
# Java app
instrumentation.opentelemetry.io/inject-java: "true"

# NodeJS
instrumentation.opentelemetry.io/inject-nodejs: "true"
instrumentation.opentelemetry.io/otel-go-auto-target-exe: "/path/to/container/executable"

# Python
instrumentation.opentelemetry.io/inject-python: "true"

# Multi container pods
instrumentation.opentelemetry.io/container-names: "<container_1>,<container_2>"

```
