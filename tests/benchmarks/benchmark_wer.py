import os
import argparse
import jiwer
import whisper
import torch
from peft import PeftModel, PeftConfig

def compute_wer(reference_texts, hypothesis_texts):
    # Flatten the lists if needed, but jiwer can handle list of strings
    wer = jiwer.wer(reference_texts, hypothesis_texts)
    return wer

def load_lora_model(base_model_name, lora_weights_path):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    base_model = whisper.load_model(base_model_name, device=device)
    # Applying LoRA weights (assuming standard HuggingFace PEFT format)
    # Whisper might need special handling, but conceptually:
    if os.path.exists(lora_weights_path):
        model = PeftModel.from_pretrained(base_model, lora_weights_path)
    else:
        print(f"Warning: LoRA weights not found at {lora_weights_path}. Using base model.")
        model = base_model
    return model

def benchmark(test_dataset, base_model_name, lora_weights_path):
    model = load_lora_model(base_model_name, lora_weights_path)
    
    reference_texts = []
    hypothesis_texts = []

    for item in test_dataset:
        audio_path = item["audio"]
        ref_text = item["text"]
        
        # Transcribe
        result = model.transcribe(audio_path)
        hyp_text = result["text"].strip()
        
        reference_texts.append(ref_text)
        hypothesis_texts.append(hyp_text)
        
    wer = compute_wer(reference_texts, hypothesis_texts)
    print(f"Word Error Rate (WER): {wer * 100:.2f}%")
    return wer

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark Whisper LoRA WER")
    parser.add_argument("--model", type=str, default="large-v3", help="Base Whisper model name")
    parser.add_argument("--lora-path", type=str, required=True, help="Path to LoRA weights")
    parser.add_argument("--dataset-dir", type=str, required=True, help="Path to test dataset containing audio files and reference texts")
    
    args = parser.parse_args()
    
    # Dummy mock dataset loading (in practice, load from manifest or directory)
    mock_dataset = [
        {"audio": os.path.join(args.dataset_dir, "sample1.wav"), "text": "the patient presented with acute abdominal pain"},
        {"audio": os.path.join(args.dataset_dir, "sample2.wav"), "text": "prescribed amoxicillin five hundred milligrams twice daily"},
    ]
    
    benchmark(mock_dataset, args.model, args.lora_path)
