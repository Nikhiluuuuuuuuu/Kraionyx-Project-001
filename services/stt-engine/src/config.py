from dataclasses import dataclass

@dataclass
class Config:
    kafka_brokers: str = "kafka-broker:9092"
    kafka_input_topic: str = "audio.preprocessed"
    kafka_output_topic: str = "transcription.results"
    model_name: str = "large-v3"
    compute_type: str = "int8_float16"
    device: str = "cuda"
