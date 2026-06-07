import json
import logging
from src.llm import LLMBackend
from src.vector_db import MockPatientHistoryDB

logger = logging.getLogger(__name__)

class ExtractorAgent:
    def __init__(self, llm: LLMBackend):
        self.llm = llm

    def extract(self, transcript: str) -> dict:
        prompt = f"Extract clinical entities (symptoms, conditions, medications) from the transcript:\n{transcript}"
        response = self.llm.generate(prompt)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            logger.warning("Extractor response was not valid JSON")
            return {"raw_extracted": response}

class SynthesizerAgent:
    def __init__(self, llm: LLMBackend, vector_db: MockPatientHistoryDB):
        self.llm = llm
        self.vector_db = vector_db

    def synthesize(self, patient_id: str, transcript: str, extracted_data: dict) -> dict:
        history = self.vector_db.retrieve_history(patient_id, transcript)
        history_text = "\\n".join(history) if history else "No relevant history."
        
        prompt = f"Synthesize a SOAP note based on the following.\\nHistory:\\n{history_text}\\n\\nTranscript:\\n{transcript}\\n\\nExtracted Data:\\n{json.dumps(extracted_data)}"
        response = self.llm.generate(prompt)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            logger.warning("Synthesizer response was not valid JSON")
            return {"raw_soap": response}

class VerifierAgent:
    def __init__(self, llm: LLMBackend):
        self.llm = llm

    def verify(self, transcript: str, soap_note: dict) -> dict:
        prompt = f"Verify the following SOAP note against the transcript to ensure no medical hallucinations.\\nTranscript:\\n{transcript}\\n\\nSOAP Note:\\n{json.dumps(soap_note)}"
        response = self.llm.generate(prompt)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            logger.warning("Verifier response was not valid JSON")
            return {"status": "ERROR", "reason": "Could not parse verifier response"}

class ClinicalWorkflow:
    def __init__(self, use_mock_llm=True, model_name="llama-3.1-8b"):
        # We can switch model_name to 'sarvam-1' for Indic languages support
        self.llm = LLMBackend(use_mock=use_mock_llm, model_name=model_name)
        self.vector_db = MockPatientHistoryDB()
        self.extractor = ExtractorAgent(self.llm)
        self.synthesizer = SynthesizerAgent(self.llm, self.vector_db)
        self.verifier = VerifierAgent(self.llm)

    def process_transcript(self, patient_id: str, transcript: str) -> dict:
        logger.info(f"Processing transcript for patient {patient_id}")
        
        # Step 1: Extract
        extracted = self.extractor.extract(transcript)
        logger.info(f"Extraction complete: {extracted}")
        
        # Step 2: Synthesize
        soap_note = self.synthesizer.synthesize(patient_id, transcript, extracted)
        logger.info(f"Synthesis complete: {soap_note}")
        
        # Step 3: Verify
        verification = self.verifier.verify(transcript, soap_note)
        logger.info(f"Verification complete: {verification}")
        
        if verification.get("status") == "REJECTED":
            logger.warning(f"SOAP note rejected due to hallucination: {verification.get('reason')}")
            # Optionally retry or fallback
            return {
                "status": "REJECTED",
                "reason": verification.get("reason"),
                "soap_note": None
            }
            
        return {
            "status": "APPROVED",
            "soap_note": soap_note,
            "extracted_data": extracted
        }
