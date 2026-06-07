from dataclasses import dataclass

@dataclass
class Config:
    kafka_brokers: str = "kafka-broker:9092"
    kafka_input_topic: str = "transcription.results"
    kafka_output_topic: str = "clinical.notes.created"
    medgemma_model: str = "google/medgemma-4b-it"
