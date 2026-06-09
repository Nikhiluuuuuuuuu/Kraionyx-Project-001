import os
import requests
import json
import logging

logger = logging.getLogger(__name__)

class LLMBackend:
    def __init__(self, use_mock=False, model_name="sarvam-1"):
        self.use_mock = use_mock
        self.model_name = model_name
        self.api_key = os.getenv("SARVAM_API_KEY", "")
        self.api_url = os.getenv("LLM_API_URL", "https://api.sarvam.ai/text-generate")
        
        if not self.use_mock and not self.api_key:
            logger.warning("SARVAM_API_KEY environment variable is not set. API calls will likely fail.")

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
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        # Invoke actual LLM (e.g., Sarvam-1)
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "max_tokens": 512,
            "temperature": 0.1
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            
            # The exact response format depends on Sarvam AI. 
            # Often it's similar to OpenAI: {"choices": [{"text": "..."}]} or similar.
            result = response.json()
            
            # Attempt to handle common response formats
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
            logger.error(f"Failed to invoke {self.model_name}: {e}")
            return f'{{"error": "Failed to invoke {self.model_name}: {str(e)}"}}'
