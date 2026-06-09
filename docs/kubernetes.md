# Kubernetes & Helm Deployment

This document outlines the deployment strategy for the Svaani platform on Kubernetes, utilizing Helm, Istio for mTLS, and HashiCorp Vault for secrets management and sidecar injection.

## Overview

The Svaani platform uses a microservices architecture deployed via Helm charts. The deployment is designed to be highly available, secure, and observable.

**Key Components:**
- **Helm Charts**: Located in `deploy/helm/`, providing templated Kubernetes manifests for all services.
- **Istio Service Mesh**: Enforces strict zero-trust mTLS for all inter-service communications.
- **HashiCorp Vault**: Manages secrets and dynamically injects them into pods using the Vault Agent Injector.

## Prerequisites

- Kubernetes cluster (v1.28+)
- `kubectl` configured
- `helm` (v3+)
- Istio installed and configured
- HashiCorp Vault installed with Kubernetes auth enabled

## Directory Structure

```
deploy/helm/
├── svaani/
│   ├── Chart.yaml
│   ├── values.yaml
│   ├── templates/
│   │   ├── api-gateway-deployment.yaml
│   │   ├── audio-processor-deployment.yaml
│   │   ├── stt-engine-deployment.yaml
│   │   ├── clinical-nlp-deployment.yaml
│   │   └── fhir-adapter-deployment.yaml
```

## Deployment Steps

### 1. Configure Vault

Ensure Vault is running and the Kubernetes auth method is enabled. The Vault Agent Injector will automatically inject secrets based on pod annotations.

### 2. Install Istio

Ensure the `istio-injection=enabled` label is present on the namespace where Svaani will be deployed.

```bash
kubectl create namespace svaani-prod
kubectl label namespace svaani-prod istio-injection=enabled
```

### 3. Deploy using Helm

Customize the `values.yaml` file according to your environment. Specifically, update Vault addresses, image tags, and resource limits. 
**Note:** With the migration to Sarvam AI APIs, GPU node pools are no longer required. All services are CPU-bound.

```bash
helm upgrade --install svaani ./deploy/helm/svaani \
  --namespace svaani-prod \
  -f ./deploy/helm/svaani/values-prod.yaml
```

### 4. Verify Deployment

Check the status of the pods and ensure all containers (including Istio proxy and Vault sidecars) are running.

```bash
kubectl get pods -n svaani-prod
```

## Persistent Storage

The Clinical NLP service uses ChromaDB for RAG, which requires persistent storage across pod restarts. The Helm charts utilize `PersistentVolumeClaim` (PVC) mounts mapped to the `CHROMA_PERSIST_DIR` environment variable to ensure vector database resilience.

## Security Posture

- **mTLS**: Automatically enforced by Istio. Services will reject non-mTLS traffic.
- **Secrets**: No secrets are stored in Kubernetes ConfigMaps or Secrets. Vault Agent injects them directly into the pod's memory.
- **Network Policies**: Default deny-all, explicitly allowing only required traffic.
