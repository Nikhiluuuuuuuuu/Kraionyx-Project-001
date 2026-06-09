"""Audio Processor service configuration loaded from environment variables."""

from __future__ import annotations

import structlog
import os
from dataclasses import dataclass

from dotenv import load_dotenv

logger = structlog.get_logger(__name__)


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
    kafka_security_protocol: str = "PLAINTEXT"
    kafka_ssl_cafile: str = ""
    kafka_ssl_certfile: str = ""
    kafka_ssl_keyfile: str = ""

    redis_url: str = "redis://redis:6379/0"
    redis_password: str = ""
    redis_ssl: bool = False
    redis_ssl_ca_certs: str = ""
    redis_ssl_certfile: str = ""
    redis_ssl_keyfile: str = ""

    encryption_key: str = ""        # base64-encoded AES-256 key
    hf_token: str = ""              # HuggingFace token for pyannote models
    sample_rate: int = 16000
    device: str = "cuda"            # "cuda" or "cpu"
    log_level: str = "INFO"

    prometheus_port: int = 8000

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
            kafka_security_protocol=os.getenv("KAFKA_SECURITY_PROTOCOL", cls.kafka_security_protocol),
            kafka_ssl_cafile=os.getenv("KAFKA_SSL_CAFILE", cls.kafka_ssl_cafile),
            kafka_ssl_certfile=os.getenv("KAFKA_SSL_CERTFILE", cls.kafka_ssl_certfile),
            kafka_ssl_keyfile=os.getenv("KAFKA_SSL_KEYFILE", cls.kafka_ssl_keyfile),

            redis_url=os.getenv("REDIS_URL", cls.redis_url),
            redis_password=os.getenv("REDIS_PASSWORD", cls.redis_password),
            redis_ssl=os.getenv("REDIS_SSL", "").lower() in ("true", "1", "yes"),
            redis_ssl_ca_certs=os.getenv("REDIS_SSL_CA_CERTS", cls.redis_ssl_ca_certs),
            redis_ssl_certfile=os.getenv("REDIS_SSL_CERTFILE", cls.redis_ssl_certfile),
            redis_ssl_keyfile=os.getenv("REDIS_SSL_KEYFILE", cls.redis_ssl_keyfile),

            encryption_key=os.getenv("ENCRYPTION_KEY", cls.encryption_key),
            hf_token=os.getenv("HF_TOKEN", cls.hf_token),
            sample_rate=int(os.getenv("SAMPLE_RATE", str(cls.sample_rate))),
            device=os.getenv("DEVICE", cls.device),
            log_level=os.getenv("LOG_LEVEL", cls.log_level),
            prometheus_port=int(os.getenv("PROMETHEUS_PORT", str(cls.prometheus_port))),
        )

        # HashiCorp Vault Integration
        vault_url = os.getenv("VAULT_URL")
        if vault_url:
            try:
                import hvac
                client = hvac.Client(url=vault_url, token=os.getenv("VAULT_TOKEN"))
                if client.is_authenticated():
                    mount_point = os.getenv("VAULT_MOUNT_POINT", "secret")
                    secret_path = os.getenv("VAULT_SECRET_PATH", "audio-processor")
                    secret_version_response = client.secrets.kv.v2.read_secret_version(
                        mount_point=mount_point,
                        path=secret_path,
                    )
                    secrets = secret_version_response["data"]["data"]
                    
                    if "encryption_key" in secrets:
                        cfg.encryption_key = secrets["encryption_key"]
                    if "hf_token" in secrets:
                        cfg.hf_token = secrets["hf_token"]
                    if "redis_password" in secrets:
                        cfg.redis_password = secrets["redis_password"]
            except Exception as e:
                logger.error("Failed to fetch secrets from HashiCorp Vault: %s", e)

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
