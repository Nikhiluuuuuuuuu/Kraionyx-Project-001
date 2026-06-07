import unittest
from unittest.mock import patch
from src.agents import ClinicalWorkflow

class TestClinicalWorkflow(unittest.TestCase):
    def setUp(self):
        # We can turn off the internal mock logic and use unittest.mock instead
        self.workflow = ClinicalWorkflow(use_mock_llm=False)
        self.workflow.vector_db.add_history("patient_123", "Patient has a history of chronic migraines.")

    @patch('src.llm.LLMBackend.generate')
    def test_successful_workflow(self, mock_generate):
        # Define mock responses for extract, synthesize, verify
        mock_generate.side_effect = [
            '{"symptoms": ["headache"]}', # Extract
            '{"subjective": "Headache", "assessment": "Migraine"}', # Synthesize
            '{"status": "APPROVED"}' # Verify
        ]
        
        transcript = "Patient complains of severe headache. Prescribed rest."
        result = self.workflow.process_transcript("patient_123", transcript)
        
        self.assertEqual(result["status"], "APPROVED")
        self.assertIn("soap_note", result)
        self.assertIn("extracted_data", result)
        
    @patch('src.llm.LLMBackend.generate')
    def test_hallucination_rejection(self, mock_generate):
        # Define mock responses for extract, synthesize, verify where verify rejects
        mock_generate.side_effect = [
            '{"conditions": ["broken leg"]}', # Extract
            '{"subjective": "Broken leg", "assessment": "Fracture"}', # Synthesize
            '{"status": "REJECTED", "reason": "Hallucination detected"}' # Verify
        ]
        
        transcript = "Patient has a minor scratch."
        result = self.workflow.process_transcript("patient_123", transcript)
        
        self.assertEqual(result["status"], "REJECTED")
        self.assertIsNone(result["soap_note"])
        self.assertEqual(result["reason"], "Hallucination detected")

if __name__ == "__main__":
    unittest.main()
