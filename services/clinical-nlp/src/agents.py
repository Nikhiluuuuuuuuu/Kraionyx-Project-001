import json
import structlog
import re
from typing import List, Optional
from pydantic import BaseModel, Field, ValidationError
from tenacity import RetryError

from src.llm import LLMBackend
from src.vector_db import PatientHistoryDB

logger = structlog.get_logger(__name__)

class ExtractedData(BaseModel):
    symptoms: List[str] = Field(default_factory=list)
    conditions: List[str] = Field(default_factory=list)
    medications: List[str] = Field(default_factory=list)
    raw_extracted: Optional[str] = None

class SoapNote(BaseModel):
    subjective: str = ""
    objective: str = ""
    assessment: str = ""
    plan: str = ""
    raw_soap: Optional[str] = None

class VerificationResult(BaseModel):
    status: str
    reason: str

def sanitize_transcript(transcript: str) -> str:
    # Defend against prompt injection: strip out special control sequences
    sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', transcript)
    return sanitized

class ExtractorAgent:
    def __init__(self, llm: LLMBackend):
        self.llm = llm

    def extract(self, transcript: str) -> dict:
        safe_transcript = sanitize_transcript(transcript)
        prompt = f"Extract clinical entities (symptoms, conditions, medications) from the transcript. Output strictly in JSON format matching {{\"symptoms\": [], \"conditions\": [], \"medications\": []}}.\nTranscript:\n{safe_transcript}"
        response = self.llm.generate(prompt)
        try:
            parsed = ExtractedData.model_validate_json(response)
            return parsed.model_dump(exclude_none=True)
        except ValidationError as e:
            logger.warning(f"Extractor validation failed: {e}")
            return ExtractedData(raw_extracted=response).model_dump(exclude_none=True)

class SynthesizerAgent:
    def __init__(self, llm: LLMBackend, vector_db: PatientHistoryDB):
        self.llm = llm
        self.vector_db = vector_db

    def synthesize(self, patient_id: str, transcript: str, extracted_data: dict) -> dict:
        safe_transcript = sanitize_transcript(transcript)
        history = self.vector_db.retrieve_history(patient_id, safe_transcript)
        history_text = "\n".join(history) if history else "No relevant history."
        
        prompt = f"Synthesize a SOAP note based on the following.\nHistory:\n{history_text}\n\nTranscript:\n{safe_transcript}\n\nExtracted Data:\n{json.dumps(extracted_data)}\n\nOutput strictly in JSON format matching {{\"subjective\": \"\", \"objective\": \"\", \"assessment\": \"\", \"plan\": \"\"}}."
        response = self.llm.generate(prompt)
        try:
            parsed = SoapNote.model_validate_json(response)
            return parsed.model_dump(exclude_none=True)
        except ValidationError as e:
            logger.warning(f"Synthesizer validation failed: {e}")
            return SoapNote(raw_soap=response).model_dump(exclude_none=True)

class VerifierAgent:
    def __init__(self, llm: LLMBackend):
        self.llm = llm

    def verify(self, transcript: str, soap_note: dict) -> dict:
        safe_transcript = sanitize_transcript(transcript)
        prompt = f"Verify the following SOAP note against the transcript to ensure no medical hallucinations. Output strictly in JSON format matching {{\"status\": \"APPROVED\"|\"REJECTED\", \"reason\": \"\"}}.\nTranscript:\n{safe_transcript}\n\nSOAP Note:\n{json.dumps(soap_note)}"
        response = self.llm.generate(prompt)
        try:
            parsed = VerificationResult.model_validate_json(response)
            return parsed.model_dump()
        except ValidationError as e:
            logger.warning(f"Verifier validation failed: {e}")
            return {"status": "ERROR", "reason": f"Could not parse verifier response: {response}"}

class ClinicalWorkflow:
    def __init__(self, model_name="sarvam-1"):
        self.llm = LLMBackend(model_name=model_name)
        self.vector_db = PatientHistoryDB()
        self.extractor = ExtractorAgent(self.llm)
        self.synthesizer = SynthesizerAgent(self.llm, self.vector_db)
        self.verifier = VerifierAgent(self.llm)

    def process_transcript(self, patient_id: str, transcript: str) -> dict:
        logger.info(f"Processing transcript for patient {patient_id}")
        
        try:
            extracted = self.extractor.extract(transcript)
            logger.info("Extraction complete")
            
            soap_note = self.synthesizer.synthesize(patient_id, transcript, extracted)
            logger.info("Synthesis complete")
            
            verification = self.verifier.verify(transcript, soap_note)
            logger.info(f"Verification complete: {verification.get('status')}")
        except RetryError as e:
            logger.error(f"LLM API generation failed after retries: {e}")
            return {
                "status": "ESCALATION_REQUIRED",
                "reason": "LLM API generation failed after retries."
            }
        
        if verification.get("status") == "REJECTED":
            logger.warning(f"SOAP note rejected due to hallucination: {verification.get('reason')}")
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
