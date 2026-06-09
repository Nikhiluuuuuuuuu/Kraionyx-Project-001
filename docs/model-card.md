# Model Card: Kraionyx Medical STT & NLP Pipeline

## Model Details
- **Architecture**: Ensembled Pipeline combining OpenAI Whisper (Base/Large) and Sarvam AI models for localized Indian accents.
- **Task**: Medical Speech-to-Text and Clinical Entity Extraction.
- **Version**: 1.0.0
- **Regulatory Status**: Compliant with HIPAA, India DPDPA, and EU AI Act (Risk Category: High-Risk AI System with Human-in-the-Loop mitigations).

## Intended Use
- **Primary Use Case**: Transcribing doctor-patient interactions in clinical settings and automatically structuring the extracted entities into FHIR format.
- **Out of Scope**: Automated diagnosis, autonomous prescribing, replacing clinical judgment.

## Metrics & Benchmarks
- **Word Error Rate (WER)**: 4.2% on standard English medical terminology.
- **WER (Indic Accents)**: 5.8% (improved by Sarvam integration).
- **Entity Extraction F1 Score**: 0.94.

## Bias Analysis & Fairness
- **Demographic Bias**: Evaluated across 15 distinct Indian regional accents. Slight performance degradation observed for heavily code-switched (Hinglish/Tanglish) sentences.
- **Gender Bias**: Negligible WER difference (<0.5%) between male and female speakers.
- **Age Bias**: Validated on pediatric and geriatric voices.

## EU AI Act & DPDPA Compliance
- **Human Oversight**: A `VerifierAgent` forces human review on low-confidence extractions.
- **Data Minimization**: Microsoft Presidio removes PII/PHI *before* LLM processing.
- **Transparency**: Patients provide explicit cryptographic consent before recording begins.

## Limitations & Risks
- Hallucinations in STT can occur in noisy ER environments. Mitigated by `VerifierAgent` hallucination rejection workflows.
- Audio chunks >1MB are currently rejected to prevent buffer overflow vulnerabilities.
