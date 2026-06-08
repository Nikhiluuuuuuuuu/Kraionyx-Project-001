import json
import logging
from confluent_kafka import Consumer as KafkaConsumer
from .config import Config

logger = logging.getLogger(__name__)

class ClinicalConsumer:
    def __init__(self, config: Config):
        kafka_conf = {
            "bootstrap.servers": config.kafka_brokers,
            "group.id": config.kafka_consumer_group,
            "auto.offset.reset": "earliest",
        }
        if config.kafka_security_protocol == "SSL":
            kafka_conf.update({
                "security.protocol": "SSL",
                "ssl.ca.location": config.kafka_ssl_cafile,
                "ssl.certificate.location": config.kafka_ssl_certfile,
                "ssl.key.location": config.kafka_ssl_keyfile,
            })
        self.consumer = KafkaConsumer(kafka_conf)
        self.topic = config.kafka_input_topic
        self.consumer.subscribe([self.topic])

    def consume(self, callback):
        logger.info(f"Consuming from {self.topic}")
        try:
            while True:
                msg = self.consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    logger.error(f"Consumer error: {msg.error()}")
                    continue

                try:
                    data = json.loads(msg.value().decode('utf-8'))
                    callback(data)
                except Exception as e:
                    logger.error(f"Failed to process message: {e}")

        except KeyboardInterrupt:
            logger.info("Consumer interrupted")
        finally:
            self.consumer.close()
