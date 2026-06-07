"""Audio Processor service configuration loaded from environment variables."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


@dataclass
class Config:
    """Typed configuration for the audio-processor service.

    All values have sensible defaults for local development and can be
    overridden via environment variables or a ``.env`` file.
    """

    kafka_brokers: str = "kafka-broker:9092"
    kafka_consumer_group: str = "audio-processors"
    kafka_input_topic: str = "audio.raw.chunks"
    kafka_output_topic: str = "audio.preprocessed"
    kafka_error_topic: str = "pipeline.errors"
    redis_url: str = "redis://redis:6379/0"
    redis_password: str = ""
    encryption_key: str = ""        # base64-encoded AES-256 key
    hf_token: str = ""              # HuggingFace token for pyannote models
    sample_rate: int = 16000
    device: str = "cuda"            # "cuda" or "cpu"
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> Config:
        """Load configuration from environment variables.

        A ``.env`` file in the working directory is loaded automatically
        (but never overrides variables already set in the environment).

        Returns:
            A fully-populated ``Config`` instance.

        Raises:
            ValueError: If *encryption_key* is empty (critical for HIPAA).
        """
        load_dotenv()

        cfg = cls(
            kafka_brokers=os.getenv("KAFKA_BROKERS", cls.kafka_brokers),
            kafka_consumer_group=os.getenv("KAFKA_CONSUMER_GROUP", cls.kafka_consumer_group),
            kafka_input_topic=os.getenv("KAFKA_INPUT_TOPIC", cls.kafka_input_topic),
            kafka_output_topic=os.getenv("KAFKA_OUTPUT_TOPIC", cls.kafka_output_topic),
            kafka_error_topic=os.getenv("KAFKA_ERROR_TOPIC", cls.kafka_error_topic),
            redis_url=os.getenv("REDIS_URL", cls.redis_url),
            redis_password=os.getenv("REDIS_PASSWORD", cls.redis_password),
            encryption_key=os.getenv("ENCRYPTION_KEY", cls.encryption_key),
            hf_token=os.getenv("HF_TOKEN", cls.hf_token),
            sample_rate=int(os.getenv("SAMPLE_RATE", str(cls.sample_rate))),
            device=os.getenv("DEVICE", cls.device),
            log_level=os.getenv("LOG_LEVEL", cls.log_level),
        )

        if not cfg.encryption_key:
            raise ValueError(
                "ENCRYPTION_KEY environment variable is required — "
                "audio data must be encrypted at rest and in transit."
            )

        logger.info(
            "Config loaded: brokers=%s group=%s device=%s sample_rate=%d",
            cfg.kafka_brokers,
            cfg.kafka_consumer_group,
            cfg.device,
            cfg.sample_rate,
        )
        return cfg
