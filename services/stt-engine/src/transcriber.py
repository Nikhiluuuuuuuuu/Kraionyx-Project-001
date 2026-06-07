import numpy as np
import torch
from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq, BitsAndBytesConfig
from peft import PeftModel, PeftConfig
from indicxlit import Transliterator
from indictrans import IndicTrans
import logging

logger = logging.getLogger(__name__)

class MedicalTranscriber:
    """
    High-performance speech-to-text (STT) transcription engine utilizing 
    OpenAI Whisper Large-V3 with LoRA support.

    This transcriber is highly optimized for GPU execution and handles medical 
    domain audio robustly. It employs INT8 quantization via bitsandbytes to fit 
    into a 16GB-24GB VRAM envelope while preserving transcription and reasoning accuracy.
    Includes IndicTrans2 translation layer and IndicXlit logic for Romanized inputs.
    """

    def __init__(self, model_name="openai/whisper-large-v3", lora_weights=None, device="cuda", compute_type="int8"):
        """
        Initializes the model with INT8 quantization and optional LoRA.

        Args:
            model_name (str): The name or path of the model to load.
            lora_weights (str): Optional path to LoRA adapters.
            device (str): Execution device ("cuda", "cpu"). Defaults to "cuda".
            compute_type (str): Hardware quantization method ("int8", "fp8").
        """
        self.model_name = model_name
        self.device = device if torch.cuda.is_available() else "cpu"
        self.compute_type = compute_type

        logger.info(f"Loading processor for {self.model_name}...")
        self.processor = AutoProcessor.from_pretrained(self.model_name)

        logger.info(f"Loading model {self.model_name} with {self.compute_type} quantization...")
        
        # Configure INT8 quantization to fit within 16-24GB VRAM
        if self.compute_type == "int8" and self.device == "cuda":
            quantization_config = BitsAndBytesConfig(
                load_in_8bit=True,
                llm_int8_threshold=6.0,
            )
        elif self.compute_type == "fp8" and self.device == "cuda":
            quantization_config = BitsAndBytesConfig(
                load_in_8bit_fp32_cpu_offload=False,
                load_in_8bit=True, 
            )
        else:
            quantization_config = None

        self.model = AutoModelForSpeechSeq2Seq.from_pretrained(
            self.model_name,
            quantization_config=quantization_config,
            device_map="auto" if self.device == "cuda" else None,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            trust_remote_code=True,
        )

        if lora_weights:
            logger.info(f"Applying LoRA weights from {lora_weights}...")
            self.model = PeftModel.from_pretrained(self.model, lora_weights)

        logger.info("Initializing IndicTrans2 translation layer...")
        self.translator = IndicTrans(dir='indic-en')

        logger.info("Initializing IndicXlit transliteration logic...")
        self.transliterator = Transliterator(source="en", target="hi")

        logger.info("Whisper model with Indic support loaded successfully.")

    def handle_code_mixed(self, text: str) -> str:
        """
        Handles Romanized/code-mixed Indic language inputs.
        """
        return self.transliterator.transliterate(text)

    def translate_to_english(self, text: str) -> str:
        """
        Translates text to English via IndicTrans2.
        """
        return self.translator.translate_paragraph(text)

    def transcribe(self, audio: np.ndarray) -> dict:
        """
        Transcribes a raw audio waveform into text.

        Args:
            audio (np.ndarray): A 1D numpy array containing the raw PCM audio 
                waveform, normalized to the range [-1.0, 1.0]. The sample rate 
                must be 16,000 Hz.

        Returns:
            dict: A dictionary containing the transcription results:
                - "text" (str): The final, concatenated transcript of the audio snippet.
                - "translated_text" (str): The English translated output.
        """
        if len(audio) == 0:
            return {"text": "", "translated_text": ""}

        # Process the audio input
        inputs = self.processor(
            audio, 
            sampling_rate=16000, 
            return_tensors="pt"
        )
        
        if self.device == "cuda":
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Generate transcription
        with torch.no_grad():
            generated_ids = self.model.generate(
                **inputs,
                max_new_tokens=256,
                num_beams=3,
            )

        transcribed_text = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()
        
        # Apply IndicXlit for Romanized/code-mixed inputs
        processed_text = self.handle_code_mixed(transcribed_text)
        
        # Apply IndicTrans2 for English translation
        translated_text = self.translate_to_english(processed_text)
        
        return {
            "text": transcribed_text,
            "processed_text": processed_text,
            "translated_text": translated_text
        }

