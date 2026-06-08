from confluent_kafka import Producer as KafkaProducer
from .config import Config

class Producer:
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
        self._producer = KafkaProducer(kafka_conf)
