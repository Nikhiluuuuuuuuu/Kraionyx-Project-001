import json
import logging
from confluent_kafka import Consumer as KafkaConsumer, KafkaError

logger = logging.getLogger(__name__)

class ClinicalConsumer:
    def __init__(self, broker: str, group_id: str, topic: str):
        self.consumer = KafkaConsumer({
            'bootstrap.servers': broker,
            'group.id': group_id,
            'auto.offset.reset': 'earliest'
        })
        self.topic = topic
        self.consumer.subscribe([self.topic])

    def consume(self, process_callback):
        logger.info(f"Started consuming from {self.topic}")
        try:
            while True:
                msg = self.consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.error(f"Consumer error: {msg.error()}")
                        break

                try:
                    value = json.loads(msg.value().decode('utf-8'))
                    process_callback(value)
                except Exception as e:
                    logger.error(f"Failed to process message: {e}")

        except KeyboardInterrupt:
            logger.info("Consumer interrupted")
        finally:
            self.consumer.close()
