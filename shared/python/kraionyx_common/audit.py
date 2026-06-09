"""HIPAA-compliant audit logger that publishes AuditEvent messages to Kafka.

Usage::

    audit = AuditLogger(producer, "audio-processor")
    await audit.log_access(user_id="u-123", resource_type="AudioChunk",
                           resource_id="chunk-456", outcome="success")
"""

from __future__ import annotations

import asyncio
import json
import structlog
import uuid
from datetime import datetime, timezone
from typing import Any, Protocol

from svaani_common.models import AuditEvent

logger = structlog.get_logger(__name__)

_AUDIT_TOPIC = "audit.events"


class _KafkaProducerLike(Protocol):
    """Structural type so we don't hard-couple to a concrete producer."""

    def produce(self, topic: str, key: str, message: dict[str, Any]) -> None:
        """Produce a message to a Kafka topic."""
        ...

    def flush(self) -> None:
        """Flush pending messages."""
        ...


class AuditLogger:
    """Publishes HIPAA-grade audit events to the ``audit.events`` Kafka topic.

    The logger deliberately avoids including any PHI/PII in the event
    payloads — only opaque identifiers (session IDs, user IDs, resource
    IDs) are recorded.
    """

    def __init__(self, producer: _KafkaProducerLike, service_name: str) -> None:
        """Initialise the audit logger.

        Args:
            producer: A Kafka producer instance (must expose ``produce``
                and ``flush``).
            service_name: Logical name of the calling service, used as
                the ``source_ip`` field (or the actual IP if available).
        """
        self._producer = producer
        self._service_name = service_name
        logger.info("AuditLogger initialised for service=%s", service_name)

    def _build_event(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        outcome: str,
        detail: str = "",
    ) -> AuditEvent:
        """Construct a fully populated :class:`AuditEvent`.

        Args:
            user_id: The acting user's opaque identifier.
            action: Verb describing the action (e.g. ``READ``).
            resource_type: Type of the affected resource.
            resource_id: Opaque identifier of the affected resource.
            outcome: ``"success"`` or ``"failure"``.
            detail: Optional free-text detail (must NOT contain PHI).

        Returns:
            A new ``AuditEvent`` ready for publishing.
        """
        return AuditEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=outcome,
            detail=detail,
            source_ip=self._service_name,
        )

    def _publish(self, event: AuditEvent) -> None:
        """Publish an audit event synchronously.

        Args:
            event: The event to publish.
        """
        try:
            self._producer.produce(
                topic=_AUDIT_TOPIC,
                key=event.event_id,
                message=event.to_dict(),
            )
            self._producer.flush()
            logger.debug(
                "Audit event published: event_id=%s action=%s",
                event.event_id,
                event.action,
            )
        except Exception:
            # Audit failures must never crash the main pipeline.
            logger.exception(
                "Failed to publish audit event event_id=%s", event.event_id
            )

    # ------------------------------------------------------------------
    # Public async API
    # ------------------------------------------------------------------

    async def log_access(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        outcome: str,
        detail: str = "",
    ) -> None:
        """Log a data-access event (e.g. reading a clinical note).

        Args:
            user_id: Who accessed the resource.
            resource_type: Kind of resource accessed.
            resource_id: Identifier of the resource.
            outcome: ``"success"`` or ``"failure"``.
            detail: Optional extra context (NO PHI).
        """
        event = self._build_event(
            user_id=user_id,
            action="ACCESS",
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=outcome,
            detail=detail,
        )
        # Offload the blocking Kafka produce to a thread so the event
        # loop is not stalled.
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._publish, event)

    async def log_processing(
        self,
        session_id: str,
        stage: str,
        outcome: str,
        detail: str = "",
    ) -> None:
        """Log a pipeline processing event.

        Args:
            session_id: The pipeline session identifier.
            stage: Pipeline stage name (e.g. ``"noise-reduction"``).
            outcome: ``"success"`` or ``"failure"``.
            detail: Optional extra context (NO PHI).
        """
        event = self._build_event(
            user_id=f"system/{self._service_name}",
            action="PROCESS",
            resource_type="PipelineSession",
            resource_id=session_id,
            outcome=outcome,
            detail=f"stage={stage} {detail}".strip(),
        )
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._publish, event)
