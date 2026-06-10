# Software Requirements Specification (SRS)

## 1. Purpose
Defines the functional, non-functional, and safety requirements for the Kraionyx platform.

## 2. Functional Requirements
- **FR-01**: The system shall ingest real-time audio via WebSocket.
- **FR-02**: The system shall perform speaker diarization (Doctor vs. Patient).
- **FR-03**: The system shall transcribe audio to text using Whisper-based models.
- **FR-04**: The system shall extract clinical entities (SOAP format) using NLP.
- **FR-05**: The system shall format the output as FHIR R4 DocumentReference resources.

## 3. Non-Functional Requirements
- **NFR-01 (Performance)**: End-to-end latency shall not exceed 1.5 seconds per utterance.
- **NFR-02 (Scalability)**: The system shall handle up to 100 concurrent streams per Gateway pod.
- **NFR-03 (Security)**: All data in transit shall be encrypted via TLS 1.3 / mTLS.

## 4. Safety Requirements
- **SR-01**: The system must not store audio files to disk after transcription is complete (Zero Retention).
- **SR-02**: If the NLP service fails, the system must degrade gracefully and retain the raw transcription for manual review.
- **SR-03**: The system shall strip all PII/PHI from internal metrics and telemetry.
