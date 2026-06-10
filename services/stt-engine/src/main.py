import structlog
import os
import time
import redis
from prometheus_client import start_http_server, Counter, Histogram

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from .config import Config
from .consumer import Consumer
from .producer import Producer

MESSAGES_PROCESSED = Counter("stt_messages_processed_total", "Total STT messages processed")
PROCESSING_ERRORS = Counter("stt_processing_errors_total", "Total STT processing errors")
PROCESSING_DURATION = Histogram("stt_processing_duration_seconds", "Duration of STT processing in seconds")

def init_tracer():
    resource = Resource(attributes={"service.name": "stt-engine"})
    provider = TracerProvider(resource=resource)
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")
    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    return trace.get_tracer(__name__)

tracer = init_tracer()

def main():
    logging.info("Starting STT Engine")
    config = Config.from_env()

    # Prometheus metrics
    start_http_server(config.prometheus_port)
    logging.info(f"Prometheus metrics exposed on port {config.prometheus_port}")

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
        logging.info("Connected to Redis successfully.")
    except Exception as e:
        logging.warning(f"Failed to connect to Redis: {e}")

    # Initialize transcriber and kafka clients
    from .transcriber import MedicalTranscriber, TranscriptionError
    transcriber = MedicalTranscriber()
    consumer = Consumer(config)
    producer = Producer(config)
    
    # Subscribe to the input topic
    consumer._consumer.subscribe([config.kafka_stt_topic])
    logging.info(f"Subscribed to topic: {config.kafka_stt_topic}")
    
    try:
        while True:
            msg = consumer._consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                logging.error(f"Consumer error: {msg.error()}")
                continue
            
            with tracer.start_as_current_span("process_audio_message") as span:
                try:
                    start_time = time.time()
                    
                    # Assuming message value is audio data in bytes
                    audio_data = msg.value()
                    # (In a real scenario, we might need to parse JSON or convert bytes to np.ndarray)
                    # For this mock integration, let's assume we can pass a dummy array or process it
                    # Here we just pass an empty array to trigger the flow (to be filled properly)
                    import numpy as np
                    dummy_audio = np.zeros(16000, dtype=np.float32)
                    
                    result = transcriber.transcribe(dummy_audio)
                    
                    # Publish result to output topic
                    producer._producer.produce(
                        config.kafka_nlp_topic,
                        value=str(result).encode('utf-8')
                    )
                    producer._producer.poll(0)
                    
                    PROCESSING_DURATION.observe(time.time() - start_time)
                    MESSAGES_PROCESSED.inc()
                    logging.info("Successfully transcribed and forwarded audio.")
                    
                except TranscriptionError as e:
                    PROCESSING_ERRORS.inc()
                    span.record_exception(e)
                    logging.error(f"Transcription failed: {e}. Routing to DLQ.")
                    # Route to Dead Letter Queue
                    dlq_topic = f"{config.kafka_stt_topic}.dlq"
                    producer._producer.produce(
                        dlq_topic,
                        value=msg.value()
                    )
                    producer._producer.poll(0)
                except Exception as e:
                    PROCESSING_ERRORS.inc()
                    span.record_exception(e)
                    logging.error(f"Unexpected error processing message: {e}")
                    
    except KeyboardInterrupt:
        pass
    finally:
        consumer._consumer.close()
        producer._producer.flush()

if __name__ == "__main__":
    main()
