## 4. Safety Requirements
- **SR-01**: The system must not store audio files to disk after transcription is complete (Zero Retention).
- **SR-02**: If the NLP service fails, the system must degrade gracefully and retain the raw transcription for manual review.
- **SR-03**: The system shall strip all PII/PHI from internal metrics and telemetry.
