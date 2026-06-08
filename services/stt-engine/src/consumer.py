from confluent_kafka import Consumer as KafkaConsumer
from .config import Config

class Consumer:
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
        self._consumer = KafkaConsumer(kafka_conf)
