# Risk Management File (ISO 14971)

## 1. Overview
This document outlines the risk management process applied to the Kraionyx platform, aligning with ISO 14971 and IEC 62304 Software Safety Class C requirements.

## 2. Hazard Analysis (ISO 14971 Mappings)

| Hazard ID | ISO 14971 Category | Description | Potential Harm | Risk Level (Pre) | Mitigation / Control | Risk Level (Post) |
|-----------|--------------------|-------------|----------------|------------------|----------------------|-------------------|
| HZ-01 | Data / Information | Incorrect STT transcription of medication dosage (e.g., "15 mg" vs "50 mg"). | Adverse drug event, patient injury. | High | Audio playback validation in UI; confidence score thresholding; physician review loop. | Low |
| HZ-02 | Data / Information | NLP model extracts incorrect condition from negative phrasing (e.g., "no history of diabetes"). | Incorrect diagnosis, inappropriate treatment. | High | Advanced contextual NLP models (BGE-m3); explicit negation detection rules; human-in-the-loop review. | Low |
| HZ-03 | Security / Privacy | PHI leakage in logs or third-party APIs. | Privacy breach, HIPAA violation. | High | Zero-retention architecture; Presidio PII redactor; enterprise structured logging without payloads. | Low |
| HZ-04 | Performance | System latency causes doctor to miss critical conversation parts. | Incomplete documentation. | Medium | Redis rate limiting; Kafka buffering; robust Kubernetes scaling. | Low |
| HZ-05 | Software Failure | Missing integration across Kafka microservices causes data drop. | Clinical note missing in EHR. | High | Automated e2e integration tests (test_kafka_integration.py); DLQ setup. | Low |
| HZ-06 | Supply Chain | Malicious dependency version injection via PyPI or NPM. | System compromise. | High | Strict `pip-compile --generate-hashes` for dependencies; Trivy scanning. | Low |

## 3. Risk Evaluation
All identified risks have been mitigated to an acceptable level (ALARP). The residual risks are outweighed by the clinical benefits of accurate, automated documentation.

## 4. Software Unit Verification Records
Software unit verification is documented in CI/CD logs. All units have a strict >=80% code coverage requirement enforced by `gotestsum` (Go) and `pytest-cov` (Python).

## 5. Post-Market Surveillance
- Continuous monitoring of user correction rates in the EHR.
- Incident reporting system for transcription or NLP extraction errors.
