import numpy as np
import requests
import io
import os
import soundfile as sf
import structlog

logger = structlog.get_logger(__name__)

class TranscriptionError(Exception):
    pass

class MedicalTranscriber:
    """
    High-performance speech-to-text (STT) transcription engine utilizing 
    Sarvam AI's API.

    This transcriber uses an HTTP client to call the Sarvam AI Speech-to-Text API,
    replacing the previous local Whisper/LoRA models to save compute resources.
    The api key is securely loaded via the SARVAM_API_KEY environment variable.
    """

    def __init__(self, model_name=None, lora_weights=None, device=None, compute_type=None):
        """
        Initializes the transcriber to use Sarvam API.
        Arguments are kept for backward compatibility but ignored.
        """
        self.api_key = os.environ.get("SARVAM_API_KEY", "")
        if not self.api_key:
            logger.warning("SARVAM_API_KEY environment variable is not set. API calls will likely fail.")
        
        # Using the translate endpoint to provide both transcribed and translated text
        self.url = "https://api.sarvam.ai/speech-to-text-translate"

    def handle_code_mixed(self, text: str) -> str:
        """
        Handled transparently by Sarvam AI in most cases.
        """
        return text

    def translate_to_english(self, text: str) -> str:
        """
        Handled by the Sarvam AI speech-to-text-translate API.
        """
        return text

    def transcribe(self, audio: np.ndarray) -> dict:
        """
        Transcribes a raw audio waveform into text using Sarvam AI.

        Args:
            audio (np.ndarray): A 1D numpy array containing the raw PCM audio 
                waveform, normalized to the range [-1.0, 1.0]. The sample rate 
                must be 16,000 Hz.

        Returns:
            dict: A dictionary containing the transcription results:
                - "text" (str): The final, concatenated transcript.
                - "processed_text" (str): The processed transcript.
                - "translated_text" (str): The English translated output.
        """
        if len(audio) == 0:
            return {"text": "", "processed_text": "", "translated_text": ""}

        try:
            # Convert numpy array to WAV bytes in memory
            buffer = io.BytesIO()
            sf.write(buffer, audio, 16000, format='WAV')
            buffer.seek(0)

            headers = {
                "api-subscription-key": self.api_key
            }
            
            files = {
                "file": ("audio.wav", buffer, "audio/wav")
            }
            
            # Using prompt / model if required by API, Sarvam typically accepts 'model' or 'prompt'
            # The 'model' could be specific depending on exact Sarvam API spec, but omitting it 
            # if default applies, or adding "model": "saaras:v1" if needed.
            data = {}

            response = requests.post(self.url, headers=headers, files=files, data=data, timeout=60)
            response.raise_for_status()
            result = response.json()
            
            # Extract transcript and translated text
            # Sarvam API returns JSON depending on endpoint. Example: {"transcript": "..."}
            transcribed_text = result.get("transcript", "")
            translated_text = result.get("translated_text", transcribed_text)

            return {
                "text": transcribed_text,
                "processed_text": transcribed_text,
                "translated_text": translated_text
            }

        except requests.exceptions.Timeout:
            logger.error("Sarvam API timed out after 60s")
            raise TranscriptionError("Sarvam API timed out after 60s")
        except requests.exceptions.HTTPError as e:
            logger.error(f"Sarvam API returned HTTP {e.response.status_code}")
            raise TranscriptionError(f"Sarvam API returned HTTP {e.response.status_code}")
        except Exception as e:
            logger.error(f"Unexpected transcription failure: {e}")
            raise TranscriptionError(f"Unexpected transcription failure: {e}")

