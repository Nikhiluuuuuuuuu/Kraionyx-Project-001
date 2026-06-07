import os
import requests

class LLMBackend:
    def __init__(self, use_mock=False, model_name="llama-3.1-8b"):
        self.use_mock = use_mock
        self.model_name = model_name
        self.api_url = os.getenv("LLM_API_URL", "http://localhost:8000/v1/completions")
        
        if not self.use_mock:
            # Ready for Llama-3.1-8B or Sarvam-1 (Indic languages) integration
            pass

    def generate(self, prompt: str) -> str:
        if self.use_mock:
            if "Extract clinical entities" in prompt:
                return '{"symptoms": ["headache"], "conditions": ["migraine"]}'
            elif "Synthesize a SOAP note" in prompt:
                return '{"subjective": "Patient has headache", "objective": "Normal", "assessment": "Migraine", "plan": "Rest"}'
            elif "Verify the following SOAP note" in prompt:
                # Verifier logic: if it sees hallucinated info not in transcript, say REJECTED
                if "broken leg" in prompt.lower():
                    return '{"status": "REJECTED", "reason": "Mentions broken leg which is not in transcript"}'
                return '{"status": "APPROVED", "reason": "No hallucinations found"}'
            return "Mock response"
        
        # Invoke actual LLM (e.g., Llama-3.1-8B or Sarvam-1)
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "max_tokens": 512,
            "temperature": 0.1
        }
        try:
            response = requests.post(self.api_url, json=payload, timeout=10)
            response.raise_for_status()
            return response.json().get("choices", [{}])[0].get("text", "")
        except Exception as e:
            return f'{{"error": "Failed to invoke {self.model_name}: {str(e)}"}}'
