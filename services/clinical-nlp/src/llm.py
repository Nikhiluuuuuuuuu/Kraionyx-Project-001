import os
import requests
import json
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class LLMBackend:
    def __init__(self, use_mock=False, model_name="sarvam-1"):
        # use_mock is kept for API signature but we forcefully default to False in workflow
        self.use_mock = use_mock
        self.model_name = model_name
        self.api_url = os.getenv("LLM_API_URL", "https://api.sarvam.ai/text-generate")
        self.api_key = os.getenv("SARVAM_API_KEY", "")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def generate(self, prompt: str) -> str:
        if self.use_mock:
            if "Extract clinical entities" in prompt:
                return '{"symptoms": ["headache"], "conditions": ["migraine"]}'
            elif "Synthesize a SOAP note" in prompt:
                return '{"subjective": "Patient has headache", "objective": "Normal", "assessment": "Migraine", "plan": "Rest"}'
            elif "Verify the following SOAP note" in prompt:
                if "broken leg" in prompt.lower():
                    return '{"status": "REJECTED", "reason": "Mentions broken leg which is not in transcript"}'
                return '{"status": "APPROVED", "reason": "No hallucinations found"}'
            return "Mock response"
        
        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["api-subscription-key"] = self.api_key
            headers["Authorization"] = f"Bearer {self.api_key}"
            
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "max_tokens": 512,
            "temperature": 0.1
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if "choices" in result:
                choice = result["choices"][0]
                if "text" in choice:
                    return choice["text"]
                elif "message" in choice and "content" in choice["message"]:
                    return choice["message"]["content"]
            elif "text" in result:
                return result["text"]
            elif "generated_text" in result:
                return result["generated_text"]
                
            return json.dumps(result)
        except Exception as e:
            logger.error(f"API request failed: {e}")
            return f'{{"error": "API generation failed: {str(e)}"}}'
