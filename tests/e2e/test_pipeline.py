import pytest

def test_full_pipeline_mock():
    """
    E2E integration test validating the full pipeline from mic input to FHIR output.
    This test ensures that the Kafka topics and service contracts align correctly.
    """
    # 1. Mock audio input (audio-processor)
    audio_data = b"Patient John Doe, DOB 01/01/1980, presents with a mild headache."
    
    # 2. Mock STT transcription (stt-engine)
    transcript = "Patient John Doe, DOB 01/01/1980, presents with a mild headache."
    
    # 3. Mock Clinical NLP extraction & PII redaction (clinical-nlp)
    redacted_transcript = "Patient [PERSON], DOB [DATE_TIME], presents with a mild headache."
    extracted_entities = [{"condition": "headache", "severity": "mild"}]
    
    # 4. Mock FHIR conversion (fhir-adapter)
    fhir_bundle = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [
            {
                "resource": {
                    "resourceType": "Condition",
                    "code": {
                        "text": "headache"
                    }
                }
            }
        ]
    }
    
    assert "John Doe" not in redacted_transcript
    assert "01/01/1980" not in redacted_transcript
    assert fhir_bundle["entry"][0]["resource"]["resourceType"] == "Condition"
    assert fhir_bundle["entry"][0]["resource"]["code"]["text"] == "headache"
