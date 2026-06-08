# Observability & Tracing

This document covers the observability stack used in the Kraionyx platform, providing insights into distributed tracing, metrics collection, and logging.

## Stack Overview

The observability stack is located in `deploy/observability/` and consists of the following tools:

- **OpenTelemetry (OTel)**: Collects, processes, and exports traces and metrics from all services.
- **Prometheus**: Time-series database for storing metrics.
- **Grafana**: Visualization and dashboards for metrics and traces.
- **Jaeger/Tempo**: Backend for storing and querying distributed traces.

## OpenTelemetry Integration

All microservices (Go and Python) are instrumented with OpenTelemetry SDKs. Traces include the entire lifecycle of an audio chunk, from ingestion at the API Gateway to final FHIR payload delivery.

- **Go Services** (`api-gateway`, `fhir-adapter`): Use `go.opentelemetry.io/otel`.
- **Python Services** (`audio-processor`, `stt-engine`, `clinical-nlp`): Use `opentelemetry-api` and `opentelemetry-sdk`.

## Metrics & Dashboards

Prometheus scrapes metrics from the OTel Collector and individual services. Pre-configured Grafana dashboards are provided to monitor:

- **API Gateway**: WebSocket connection counts, ingestion latency, and message drop rates.
- **Kafka**: Topic lag, throughput, and error rates.
- **STT Engine**: Inference latency (WER is tracked separately via benchmarking tools).
- **Clinical NLP**: Model response times and cache hit/miss rates.
- **Hardware Metrics**: GPU VRAM utilization, CPU/Memory per pod.

## Deployment Steps

The observability stack can be deployed using Docker Compose or Helm (for Kubernetes).

### Using Docker Compose (Development)

```bash
cd deploy/observability
docker-compose up -d
```

### Using Helm (Production)

To deploy the observability stack via Helm in your Kubernetes cluster:

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts

# Install the stack in the observability namespace
helm upgrade --install prometheus prometheus-community/kube-prometheus-stack -n observability --create-namespace
helm upgrade --install otel-collector open-telemetry/opentelemetry-collector -n observability
```

## Accessing Grafana

Once deployed, access Grafana via port-forwarding or your ingress controller:

```bash
kubectl port-forward svc/grafana 3000:80 -n observability
```
Login with the default credentials configured in your Helm values or Docker Compose setup.
