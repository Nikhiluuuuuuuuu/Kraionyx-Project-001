import json
import structlog
from confluent_kafka import Producer as KafkaProducer
from .config import Config

logger = structlog.get_logger(__name__)

class ClinicalProducer:
    def __init__(self, config: Config):
        kafka_conf = {
            "bootstrap.servers": config.kafka_brokers,
        }
        if config.kafka_security_protocol == "SSL":
            kafka_conf.update({
                "security.protocol": "SSL",
                "ssl.ca.location": config.kafka_ssl_cafile,
                "ssl.certificate.location": config.kafka_ssl_certfile,
                "ssl.key.location": config.kafka_ssl_keyfile,
            })
        self.producer = KafkaProducer(kafka_conf)

    def delivery_report(self, err, msg):
        if err is not None:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.info(f"Message delivered to {msg.topic()} [{msg.partition()}]")

    def produce(self, topic: str, data: dict):
        self.producer.produce(
            topic,
            json.dumps(data).encode('utf-8'),
            callback=self.delivery_report
        )
        self.producer.poll(0)

    def flush(self):
        self.producer.flush()
