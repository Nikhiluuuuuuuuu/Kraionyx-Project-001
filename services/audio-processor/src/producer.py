"""Kafka producer wrapper for the audio-processor service.

Publishes preprocessed audio chunks and pipeline error events.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from confluent_kafka import Producer

from kraionyx_common.models import PipelineError

from .config import Config

logger = logging.getLogger(__name__)


def _delivery_callback(err: Any, msg: Any) -> None:
    """Confluent-kafka delivery report callback.

    Args:
        err: Error object (``None`` on success).
        msg: The delivered (or failed) message.
    """
    if err is not None:
        logger.error(
            "Message delivery failed: topic=%s err=%s", msg.topic(), err
        )
    else:
        logger.debug(
            "Message delivered: topic=%s partition=%d offset=%d",
            msg.topic(),
            msg.partition(),
            msg.offset(),
        )


class AudioProducer:
    """Thin wrapper around :class:`confluent_kafka.Producer`."""

    def __init__(self, config: Config) -> None:
        """Create the Kafka producer.

        Args:
            config: Service configuration containing broker addresses.
        """
        kafka_conf: dict[str, str | int] = {
            "bootstrap.servers": config.kafka_brokers,
            "acks": "all",
            "retries": "5",
            "retry.backoff.ms": "500",
            "linger.ms": "10",
            "compression.type": "lz4",
            "message.max.bytes": "10485760",  # 10 MiB
        }
        self._producer = Producer(kafka_conf)
        self._error_topic = config.kafka_error_topic
        logger.info("AudioProducer created: brokers=%s", config.kafka_brokers)

    def produce(self, topic: str, key: str, message: dict[str, Any]) -> None:
        """Serialize and produce a message to the given topic.

        Args:
            topic: Kafka topic name.
            key: Message key (typically ``session_id``).
            message: JSON-serialisable dictionary.
        """
        payload = json.dumps(message, separators=(",", ":")).encode("utf-8")
        self._producer.produce(
            topic=topic,
            key=key.encode("utf-8"),
            value=payload,
            callback=_delivery_callback,
        )
        # Trigger delivery callbacks for already-queued messages.
        self._producer.poll(0)
        logger.debug("Produced message to topic=%s key=%s", topic, key)

    def produce_error(self, error: PipelineError) -> None:
        """Publish a :class:`PipelineError` to the error topic.

        Args:
            error: The pipeline error event.
        """
        self.produce(
            topic=self._error_topic,
            key=error.session_id,
            message=error.to_dict(),
        )
        logger.warning(
            "Pipeline error produced: session_id=%s stage=%s",
            error.session_id,
            error.stage,
        )

    def flush(self, timeout: float = 10.0) -> None:
        """Flush pending messages, blocking until delivered or timed out.

        Args:
            timeout: Maximum seconds to wait.
        """
        remaining = self._producer.flush(timeout=timeout)
        if remaining > 0:
            logger.warning(
                "%d messages still in queue after flush(timeout=%s)",
                remaining,
                timeout,
            )

    def close(self) -> None:
        """Flush and release producer resources."""
        logger.info("AudioProducer closing — flushing pending messages")
        self.flush(timeout=30.0)
