# Kraionyx Platform

[![License: Proprietary](https://img.shields.io/badge/License-Proprietary-blue.svg)](LICENSE)
[![Compliance: HIPAA](https://img.shields.io/badge/Compliance-HIPAA-green.svg)](docs/security.md)
[![Compliance: DPDPA](https://img.shields.io/badge/Compliance-DPDPA-green.svg)](docs/security.md)
[![Build Status](https://img.shields.io/badge/build-passing-success)](#)

**Enterprise-Grade, HIPAA-Compliant Medical Speech-to-Text & EHR Integration Platform**

Kraionyx is a state-of-the-art, real-time clinical documentation system designed for modern healthcare environments. It captures doctor–patient conversations with high-fidelity, performs multi-speaker diarization, generates structured SOAP notes using specialized medical AI models, and pushes the final records seamlessly to Electronic Health Record (EHR) systems via the FHIR R4 standard. 

Engineered for extreme reliability, the platform targets Tier-1 Production standards, processing heavy workloads via a distributed microservices architecture. It features full CI/CD pipelines, Kubernetes Helm charts for scalable orchestration, enterprise-grade Keycloak RBAC, HashiCorp Vault for secrets management, and strict zero-trust mTLS enforcement across all internal communications, all while enforcing strict zero-retention policies.

> ⚠️ **MISSION CRITICAL & PHI ALERT:** This software processes Protected Health Information (PHI). Production deployments are strictly governed by HIPAA (US), DPDPA (India), and other global privacy laws. Refer to the comprehensive [Security Documentation](docs/security.md) for enforcement guidelines.

---

## System Architecture

```mermaid
graph TB
    subgraph Client
        MIC["🎤 Microphone"]
    end

    subgraph "Frontend Network"
        GW["API Gateway<br/><i>Go · WebSocket · TLS 1.3</i>"]
        KC["Keycloak<br/><i>IAM & RBAC</i>"]
    end

    subgraph "Backend Network (Internal / mTLS)"
        direction TB
        KAFKA["Apache Kafka<br/><i>KRaft Mode (mTLS)</i>"]
        REDIS["Redis 7<br/><i>Audio Buffer (mTLS)</i>"]

        AP["Audio Processor<br/><i>Python · Pyannote</i>"]
        STT["STT Engine<br/><i>Whisper Large-V3</i>"]
        NLP["Clinical NLP<br/><i>Llama-3.1 & BGE-m3</i>"]
        FHIR["FHIR Adapter<br/><i>Go · FHIR R4</i>"]
        
        VAULT["HashiCorp Vault<br/><i>Secrets & PKI</i>"]
    end

    subgraph "External Systems"
        EHR["EHR / FHIR Server"]
    end

    MIC -->|"Auth / JWT"| KC
    MIC -->|"WSS Binary Frames"| GW
    GW -->|"Validates JWT"| KC
    GW -->|"Fetches mTLS Certs"| VAULT
    GW -->|"audio.raw.chunks (mTLS)"| KAFKA
    GW <-->|"Session State (mTLS)"| REDIS
    KAFKA -->|"audio.raw.chunks"| AP
    AP -->|"audio.preprocessed"| KAFKA
    AP <-->|"Audio Buffer"| REDIS
    KAFKA -->|"audio.preprocessed"| STT
    STT -->|"transcription.results"| KAFKA
    KAFKA -->|"transcription.results"| NLP
    NLP -->|"clinical.notes.created"| KAFKA
    KAFKA -->|"fhir.outbound"| FHIR
    FHIR -->|"FHIR R4 REST"| EHR

    style GW fill:#2563eb,color:#fff
    style KC fill:#f59e0b,color:#fff
    style KAFKA fill:#e11d48,color:#fff
    style REDIS fill:#dc2626,color:#fff
    style AP fill:#7c3aed,color:#fff
    style STT fill:#7c3aed,color:#fff
    style NLP fill:#7c3aed,color:#fff
    style FHIR fill:#2563eb,color:#fff
    style VAULT fill:#059669,color:#fff
    style EHR fill:#059669,color:#fff
```

### Data Flow

| Stage | Kafka Topic | Service | Technology |
|-------|-------------|---------|------------|
| 1. Ingest | `audio.raw.chunks` | API Gateway | Go, WebSocket, TLS 1.3, 100 msg/sec limit |
| 2. Preprocess | `audio.preprocessed` | Audio Processor | Python, pyannote (500ms chunks to 10s windows, O(1) role hash map) |
| 3. Transcribe | `transcription.results` | STT Engine | Python, OpenAI Whisper Large-V3 w/ LoRA (IndicTrans2/IndicXlit) |
| 4. Generate Notes | `clinical.notes.created` | Clinical NLP | Python, Multi-Agent (Llama-3.1-8B-Instruct/Sarvam-1), BGE-m3 + LRU Eviction |
| 5. Push to EHR | `fhir.outbound` | FHIR Adapter | Go, FHIR R4, Exp Backoff & DLQ |

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| **Go** | 1.22+ | API Gateway, FHIR Adapter |
| **Python** | 3.11+ | Audio Processor, STT Engine, Clinical NLP |
| **Docker** | 24+ | Containerized deployment |
| **Docker Compose** | v2.20+ | Service orchestration |
| **CUDA Toolkit** | 12.x | GPU acceleration for ML models |
| **NVIDIA Container Toolkit** | Latest | GPU passthrough to Docker |
| **mkcert** | Latest | TLS certificate generation (dev) |
| **protoc** | 3.x | Protobuf code generation |
| **HashiCorp Vault** | 1.15+ | Secrets and dynamic certificate management |
| **Keycloak** | 22+ | Identity, access management, and RBAC |
| **Kubernetes / Helm** | 1.28+ | Production orchestration and deployment |

### GPU Requirements

| Service | VRAM Required | Notes |
|---------|--------------|-------|
| Audio Processor (pyannote) | ~2 GB | Speaker diarization |
| STT Engine (Whisper Large-V3 + LoRA) | ~12 GB | Speech recognition (Indic Support) |
| Clinical NLP (Llama-3.1-8B-Instruct/Sarvam-1) | ~24 GB | SOAP note generation via RAG (BGE-m3) |

> **Minimum**: NVIDIA GPU with 24 GB VRAM (e.g., RTX 3090, RTX 4090)
> **Recommended**: 48 GB VRAM (e.g., 2x RTX 4090, A6000, A40) for running all services concurrently.

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/kraionyx/kraionyx.git
cd kraionyx

# 2. Configure environment
cp .env.example .env
# Edit .env with your HuggingFace token and credentials

# 3. One-command setup (generates certs, starts infra, creates topics)
make setup

# 4. Start the full stack
make up

# 5. Verify services are running
make ps
```

### Verify the system

```bash
# Check API Gateway health
curl -k https://localhost:8443/health

# View Kafka topics
open http://localhost:8080

# Check Redis
redis-cli -a "${REDIS_PASSWORD}" ping
```

---

## Project Structure

```
kraionyx/
├── certs/                          # TLS certificates (gitignored except .gitkeep)
├── deploy/
│   ├── docker-compose.yml          # Full development stack
│   └── docker-compose.infra.yml    # Infrastructure only (Kafka, Redis)
├── docs/
│   ├── architecture.md             # Architecture decision records
│   ├── security.md                 # Security & compliance documentation
│   └── api.md                      # API reference
├── proto/
│   └── kraionyx/v1/
│       ├── audio.proto             # Audio ingestion message definitions
│       ├── transcription.proto     # Transcription & SOAP note definitions
│       └── fhir.proto              # FHIR push request/response definitions
├── scripts/
│   ├── create-kafka-topics.sh      # Kafka topic provisioning
│   └── generate-certs.sh           # TLS certificate generation
├── services/
│   ├── api-gateway/                # Go — WebSocket ingestion + REST API (100 msg/sec rate limit)
│   ├── audio-processor/            # Python — 500ms chunking into 10s windows, O(1) hash map speaker roles, Pyannote
│   ├── stt-engine/                 # Python — Whisper Large-V3 (LoRA) + IndicTrans2/IndicXlit
│   ├── clinical-nlp/               # Python — Llama-3.1-8B-Instruct/Sarvam-1 + BGE-m3 LRU Cache
│   └── fhir-adapter/               # Go — FHIR R4 EHR integration (Backoff & DLQ)
├── shared/                         # Shared libraries + generated protobuf code
├── tests/
│   └── qa/                         # Load testing, chaos engineering, and fuzzing
├── .env.example                    # Environment variable template
├── .gitignore                      # Comprehensive gitignore
├── Makefile                        # Build, test, and deployment automation
└── README.md                       # This file
```

---

## Development Workflow

### Available Make Targets

```bash
make help              # Show all available targets
make setup             # First-time setup (certs + infra + topics)
make infra-up          # Start only infrastructure
make infra-down        # Stop infrastructure
make up                # Build and start everything
make down              # Stop everything and remove volumes
make topics            # Create Kafka topics (idempotent)
make certs             # Generate TLS dev certificates
make build             # Build all Go binaries
make test              # Run all tests
make lint              # Run all linters
make proto             # Generate protobuf Go code
make clean             # Remove build artifacts and caches
```

### Running Individual Services Locally

```bash
# Start infrastructure only
make infra-up

# Run the API Gateway locally (requires Go)
cd services/api-gateway
go run ./cmd/server

# Run the STT Engine locally (requires Python + CUDA)
cd services/stt-engine
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m stt_engine.main
```

### Protobuf Workflow

```bash
# Edit proto files in proto/kraionyx/v1/
# Then regenerate Go code:
make proto

# Generated code appears in shared/gen/kraionyx/v1/
```

---

## Security Considerations

This system is designed for HIPAA and DPDPA compliance:

- **Encryption at rest**: AES-256-GCM for all audio data and clinical notes
- **Encryption in transit**: TLS 1.3 for all inter-service communication
- **Zero retention**: Audio data is deleted after transcription; configurable retention
- **PII redaction**: Microsoft Presidio (regex behavior) for automated PHI stripping
- **Audit logging**: All data access events are published to `audit.events` Kafka topic
- **Network segmentation**: Backend services are on an internal-only Docker network

For full security documentation, see [docs/security.md](docs/security.md).

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Commit with conventional commits (`git commit -m 'feat: add new feature'`)
4. Push to the branch (`git push origin feat/my-feature`)
5. Open a Pull Request

---

## License

This project is proprietary software. All rights reserved.

See [LICENSE](LICENSE) for details.
