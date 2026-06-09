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

if __name__ == "__main__":
    main()
