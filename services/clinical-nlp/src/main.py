import logging
import os
import threading
from src.consumer import ClinicalConsumer
from src.producer import ClinicalProducer
from src.agents import ClinicalWorkflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
IN_TOPIC = os.getenv("IN_TOPIC", "clinical.notes.created")
OUT_TOPIC = os.getenv("OUT_TOPIC", "clinical.notes.processed")

workflow = ClinicalWorkflow(use_mock_llm=True)
producer = ClinicalProducer(broker=KAFKA_BROKER)

def process_message(data: dict):
    patient_id = data.get("patient_id", "unknown")
    transcript = data.get("transcript", "")
    
    result = workflow.process_transcript(patient_id, transcript)
    
    output_data = {
        "patient_id": patient_id,
        "original_transcript": transcript,
        "result": result
    }
    
    producer.produce(OUT_TOPIC, output_data)

def main():
    logger.info("Starting Clinical NLP Service (Agentic Workflow)")
    
    consumer = ClinicalConsumer(
        broker=KAFKA_BROKER,
        group_id="clinical-nlp-group",
        topic=IN_TOPIC
    )
    
    # Run consumer in the main thread (blocking)
    consumer.consume(process_message)

if __name__ == "__main__":
    main()
