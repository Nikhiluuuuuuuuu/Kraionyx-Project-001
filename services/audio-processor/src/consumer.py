"""Kafka consumer wrapper for the audio-processor service.

Consumes raw audio chunks from the ``audio.raw.chunks`` topic, deserialises
them into :class:`AudioChunkMessage` instances, and dispatches them to a
user-supplied handler callback.
"""

from __future__ import annotations

import json
import structlog
from typing import Callable

from confluent_kafka import Consumer, KafkaError, KafkaException, Message

from svaani_common.models import AudioChunkMessage

from .config import Config

logger = structlog.get_logger(__name__)


class AudioConsumer:
    """Blocking Kafka consumer that reads :class:`AudioChunkMessage` values."""

    def __init__(self, config: Config) -> None:
        """Create a confluent-kafka Consumer.

        Args:
            config: Service configuration containing broker addresses and
                consumer-group settings.
        """
        kafka_conf: dict[str, str | int] = {
            "bootstrap.servers": config.kafka_brokers,
            "group.id": config.kafka_consumer_group,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": "false",
            "max.poll.interval.ms": "600000",  # 10 min — ML models are slow
            "session.timeout.ms": "45000",
            "heartbeat.interval.ms": "15000",
        }
        if config.kafka_security_protocol == "SSL":
            kafka_conf.update({
                "security.protocol": "SSL",
                "ssl.ca.location": config.kafka_ssl_cafile,
                "ssl.certificate.location": config.kafka_ssl_certfile,
                "ssl.key.location": config.kafka_ssl_keyfile,
            })
        
        self._consumer = Consumer(kafka_conf)
        self._topic = config.kafka_input_topic
        self._running = True
        logger.info(
            "AudioConsumer created: topic=%s group=%s",
            self._topic,
            config.kafka_consumer_group,
        )

    def consume(self, handler: Callable[[AudioChunkMessage], None]) -> None:
        """Subscribe and start the blocking consume loop.

        Each successfully deserialised message is passed to *handler*.
        After the handler returns without error the offset is committed.

        Args:
            handler: Callback invoked with each ``AudioChunkMessage``.
        """
        self._consumer.subscribe([self._topic])
        logger.info("Subscribed to topic=%s — entering consume loop", self._topic)

        try:
            while self._running:
                msg: Message | None = self._consumer.poll(timeout=1.0)

                if msg is None:
                    continue

                error = msg.error()
                if error is not None:
                    if error.code() == KafkaError._PARTITION_EOF:
                        logger.debug(
                            "Reached end of partition %s [%d] @ offset %d",
                            msg.topic(),
                            msg.partition(),
                            msg.offset(),
                        )
                        continue
                    raise KafkaException(error)

                try:
                    raw_value = msg.value()
                    if raw_value is None:
                        logger.warning("Received tombstone message — skipping")
                        continue

                    payload: dict = json.loads(raw_value)
                    audio_msg = AudioChunkMessage.from_dict(payload)

                    logger.info(
                        "Received chunk: session_id=%s chunk_index=%d",
                        audio_msg.session_id,
                        audio_msg.chunk_index,
                    )

                    handler(audio_msg)

                    self._consumer.commit(message=msg, asynchronous=False)

                except json.JSONDecodeError:
                    logger.exception(
                        "Invalid JSON in message at offset %d — skipping",
                        msg.offset(),
                    )
                    raise
                except KeyError as exc:
                    logger.exception(
                        "Missing required field %s in message at offset %d — skipping",
                        exc,
                        msg.offset(),
                    )
                    raise
                except Exception:
                    logger.exception(
                        "Handler failed for message at offset %d — will not commit",
                        msg.offset(),
                    )
                    raise

        except KafkaException:
            logger.exception("Fatal Kafka error in consume loop")
            raise
        finally:
            logger.info("Exiting consume loop — closing consumer")
            self._consumer.close()

    def close(self) -> None:
        """Signal the consume loop to exit gracefully."""
        logger.info("AudioConsumer.close() called — stopping consume loop")
        self._running = False
