import logging
import os
import threading
import time
import redis
from prometheus_client import start_http_server, Counter, Histogram

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from src.consumer import ClinicalConsumer
from src.producer import ClinicalProducer
from src.agents import ClinicalWorkflow
from .config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# RED Metrics
MESSAGES_PROCESSED = Counter("clinical_nlp_messages_processed_total", "Total Clinical NLP messages processed")
PROCESSING_ERRORS = Counter("clinical_nlp_processing_errors_total", "Total Clinical NLP processing errors")
PROCESSING_DURATION = Histogram("clinical_nlp_processing_duration_seconds", "Duration of processing in seconds")

workflow = ClinicalWorkflow(use_mock_llm=True)

def init_tracer():
    resource = Resource(attributes={"service.name": "clinical-nlp"})
    provider = TracerProvider(resource=resource)
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")
    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    return trace.get_tracer(__name__)

tracer = init_tracer()

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
        start_time = time.time()
        with tracer.start_as_current_span("process_message") as span:
            try:
                patient_id = data.get("patient_id", "unknown")
                span.set_attribute("patient_id", patient_id)
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
                span.record_exception(e)
                logger.error(f"Error processing message: {e}")
                PROCESSING_ERRORS.inc()
            finally:
                PROCESSING_DURATION.observe(time.time() - start_time)

    consumer = ClinicalConsumer(config)
    
    # Run consumer in the main thread (blocking)
    consumer.consume(process_message)

if __name__ == "__main__":
    main()
