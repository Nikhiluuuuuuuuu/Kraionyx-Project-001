# Risk Management File (ISO 14971)

## 1. Overview
This document outlines the risk management process applied to the Kraionyx platform, aligning with ISO 14971 and IEC 62304 Software Safety Class B/C requirements.

## 2. Hazard Analysis

| Hazard ID | Description | Potential Harm | Risk Level (Pre) | Mitigation / Control | Risk Level (Post) |
|-----------|-------------|----------------|------------------|----------------------|-------------------|
| HZ-01 | Incorrect STT transcription of medication dosage (e.g., "15 mg" vs "50 mg"). | Adverse drug event, patient injury. | High | Audio playback validation in UI; confidence score thresholding; physician review loop. | Low |
| HZ-02 | NLP model extracts incorrect condition from negative phrasing (e.g., "no history of diabetes"). | Incorrect diagnosis, inappropriate treatment. | High | Advanced contextual NLP models (BGE-m3); explicit negation detection rules; human-in-the-loop review. | Low |
| HZ-03 | PHI leakage in logs or third-party APIs. | Privacy breach, HIPAA violation. | High | Zero-retention architecture; Presidio PII redactor; enterprise structured logging without payloads. | Low |
| HZ-04 | System latency causes doctor to miss critical conversation parts. | Incomplete documentation. | Medium | Global Redis rate limiting; Kafka buffering; robust Kubernetes scaling. | Low |

## 3. Risk Evaluation
All identified risks have been mitigated to an acceptable level (ALARP). The residual risks are outweighed by the clinical benefits of accurate, automated documentation.

## 4. Post-Market Surveillance
- Continuous monitoring of user correction rates in the EHR.
- Incident reporting system for transcription or NLP extraction errors.
