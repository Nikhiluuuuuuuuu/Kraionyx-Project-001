# Clinical Validation Plan

## 1. Objective
To validate the clinical efficacy and safety of the Kraionyx STT and NLP pipelines in real-world or simulated clinical environments.

## 2. Scope
Validation covers:
- Accuracy of the transcription (Word Error Rate).
- Accuracy of clinical entity extraction (Conditions, Medications, Procedures).
- Proper mapping of clinical notes to FHIR R4 resources.

## 3. Dataset Requirements
- **Size**: Minimum 1,000 distinct, physician-reviewed, simulated patient encounters.
- **Diversity**: Covers at least 50 common medical conditions and 200 distinct medications across various demographics and accents.
- *Note: Synthetic data generation is strictly controlled. Previous inadequate datasets have been deprecated and replaced with rigorous clinical datasets in `tests/fixtures/`.*

## 4. Acceptance Criteria
- **Speech-to-Text**: WER ≤ 8% overall, ≤ 5% for critical medical terminology.
- **NLP NER**: F1 Score ≥ 96% for Medications and Dosages; F1 ≥ 94% for Diagnoses.
- **Safety**: 0% false positive rate for critical contraindication detection.

## 5. Execution
- Validation will be executed by a panel of 3 independent certified physicians.
- Results will be documented in the Final Clinical Evaluation Report (CER).
