import json
import logging
from confluent_kafka import Producer as KafkaProducer

logger = logging.getLogger(__name__)

class ClinicalProducer:
    def __init__(self, broker: str):
        self.producer = KafkaProducer({'bootstrap.servers': broker})

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
