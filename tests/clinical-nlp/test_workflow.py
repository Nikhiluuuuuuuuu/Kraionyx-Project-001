from unittest.mock import patch
from src.agents import ClinicalWorkflow

class TestClinicalWorkflow:
    def setup_method(self):
        self.workflow = ClinicalWorkflow(use_mock_llm=False)
        self.workflow.vector_db.add_history("patient_123", "Patient has a history of chronic migraines.")

    @patch('src.llm.LLMBackend.generate')
    def test_successful_workflow(self, mock_generate):
        mock_generate.side_effect = [
            '{"symptoms": ["headache"]}', # Extract
            '{"subjective": "Headache", "assessment": "Migraine"}', # Synthesize
            '{"status": "APPROVED"}' # Verify
        ]
        
        transcript = "Patient complains of severe headache. Prescribed rest."
        result = self.workflow.process_transcript("patient_123", transcript)
        
        assert result["status"] == "APPROVED"
        assert "soap_note" in result
        assert "extracted_data" in result
        
    @patch('src.llm.LLMBackend.generate')
    def test_hallucination_rejection(self, mock_generate):
        mock_generate.side_effect = [
            '{"conditions": ["broken leg"]}', # Extract
            '{"subjective": "Broken leg", "assessment": "Fracture"}', # Synthesize
            '{"status": "REJECTED", "reason": "Hallucination detected"}' # Verify
        ]
        
        transcript = "Patient has a minor scratch."
        result = self.workflow.process_transcript("patient_123", transcript)
        
        assert result["status"] == "REJECTED"
        assert result.get("soap_note") is None
        assert result["reason"] == "Hallucination detected"
