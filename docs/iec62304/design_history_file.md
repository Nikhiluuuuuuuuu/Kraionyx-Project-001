# Design History File (DHF)

## 1. Introduction
This Design History File (DHF) demonstrates that the Kraionyx platform was developed in accordance with the approved Design Plan and meets the requirements of 21 CFR Part 820.30 and ISO 13485.

## 2. Design Inputs
- **Clinical Need**: Automated, real-time speech-to-text and clinical NLP entity extraction for doctor-patient interactions.
- **Regulatory Requirements**: HIPAA, DPDPA, zero-retention policy, and PHI redaction.
- **Performance Requirements**: WER < 10%, NER F1 Score > 95%, Latency < 1.5s.

## 3. Design Outputs
- Source code in the repository (`services/`, `shared/`).
- System architecture (see `docs/architecture.md`).
- Container images and Kubernetes Helm charts.

## 4. Design Verification
- Unit and integration testing strategies (`tests/`).
- CI/CD pipelines enforcing 80% test coverage for Go and Python services.
- Automated security scanning (Trivy, gosec, Bandit).

## 5. Design Validation
- Clinical evaluation of NLP outputs against physician-reviewed datasets.
- See [Clinical Validation Plan](clinical_validation.md).

## 6. Design Transfer
- Deployment via automated Helm charts to production Kubernetes clusters.
- Versioned release tags mapped to specific DHF revisions.
