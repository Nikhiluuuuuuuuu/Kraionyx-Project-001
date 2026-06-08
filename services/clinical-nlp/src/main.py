import logging
import os
import threading
import redis
from prometheus_client import start_http_server, Counter

from src.consumer import ClinicalConsumer
from src.producer import ClinicalProducer
from src.agents import ClinicalWorkflow
from .config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MESSAGES_PROCESSED = Counter("clinical_nlp_messages_processed_total", "Total Clinical NLP messages processed")
PROCESSING_ERRORS = Counter("clinical_nlp_processing_errors_total", "Total Clinical NLP processing errors")

workflow = ClinicalWorkflow(use_mock_llm=True)

def main():
    config = Config.from_env()
    logger.info("Starting Clinical NLP Service (Agentic Workflow)")
    
    # Prometheus metrics
    start_http_server(config.prometheus_port)
    logger.info(f"Prometheus metrics exposed on port {config.prometheus_port}")

    # Redis mTLS connection logic
    redis_kwargs = {}
    if config.redis_ssl:
        redis_kwargs.update({
            "ssl": True,
            "ssl_cert_reqs": "required",
            "ssl_ca_certs": config.redis_ssl_ca_certs,
            "ssl_certfile": config.redis_ssl_certfile,
            "ssl_keyfile": config.redis_ssl_keyfile,
        })
    redis_client = redis.Redis.from_url(config.redis_url, password=config.redis_password, **redis_kwargs)
    try:
        redis_client.ping()
        logger.info("Connected to Redis successfully.")
    except Exception as e:
        logger.warning(f"Failed to connect to Redis: {e}")
        
    producer = ClinicalProducer(config)

    def process_message(data: dict):
        try:
            patient_id = data.get("patient_id", "unknown")
            transcript = data.get("transcript", "")
            
            result = workflow.process_transcript(patient_id, transcript)
            
            output_data = {
                "patient_id": patient_id,
                "original_transcript": transcript,
                "result": result
            }
            
            producer.produce(config.kafka_output_topic, output_data)
            MESSAGES_PROCESSED.inc()
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            PROCESSING_ERRORS.inc()

    consumer = ClinicalConsumer(config)
    
    # Run consumer in the main thread (blocking)
    consumer.consume(process_message)

if __name__ == "__main__":
    main()
