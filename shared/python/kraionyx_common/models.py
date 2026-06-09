"""Shared Kafka message dataclasses — wire-compatible with Go models.

Every model exposes ``to_dict()`` for JSON serialisation and a classmethod
``from_dict(data)`` for deserialisation.  Field names use **snake_case** in
Python but serialise to the **same snake_case** keys the Go services produce
(Go structs use ``json:"snake_case"`` tags).
"""

from __future__ import annotations

import json
import structlog
from dataclasses import asdict, dataclass, field
from typing import Any

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Audio pipeline
# ---------------------------------------------------------------------------

@dataclass
class AudioChunkMessage:
    """A single chunk of encrypted audio arriving from the gateway."""

    session_id: str
    chunk_index: int
    timestamp_ms: int
    audio_data: str          # base64-encoded encrypted PCM
    format: str              # e.g. "pcm_s16le"
    sample_rate: int
    channels: int

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-compatible dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AudioChunkMessage:
        """Deserialise from a dictionary (e.g. parsed JSON)."""
        return cls(
            session_id=str(data["session_id"]),
            chunk_index=int(data["chunk_index"]),
            timestamp_ms=int(data["timestamp_ms"]),
            audio_data=str(data["audio_data"]),
            format=str(data["format"]),
            sample_rate=int(data["sample_rate"]),
            channels=int(data["channels"]),
        )

    def to_json(self) -> str:
        """Return a compact JSON string."""
        return json.dumps(self.to_dict(), separators=(",", ":"))

    @classmethod
    def from_json(cls, raw: str | bytes) -> AudioChunkMessage:
        """Parse from a JSON string or bytes."""
        return cls.from_dict(json.loads(raw))


# ---------------------------------------------------------------------------
# Transcription
# ---------------------------------------------------------------------------

@dataclass
class SpeakerSegment:
    """A single speaker-attributed segment of a transcript."""

    speaker_label: str       # e.g. "Doctor", "Patient"
    start_time: float        # seconds
    end_time: float          # seconds
    text: str
    confidence: float        # 0.0 – 1.0

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-compatible dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SpeakerSegment:
        """Deserialise from a dictionary."""
        return cls(
            speaker_label=str(data["speaker_label"]),
            start_time=float(data["start_time"]),
            end_time=float(data["end_time"]),
            text=str(data["text"]),
            confidence=float(data["confidence"]),
        )


@dataclass
class TranscriptionResultMessage:
    """Full transcription result for a session, published after STT."""

    session_id: str
    segments: list[SpeakerSegment]
    full_transcript: str
    language: str
    overall_confidence: float
    processed_at_ms: int

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-compatible dictionary."""
        d = asdict(self)
        # asdict already handles nested dataclasses
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TranscriptionResultMessage:
        """Deserialise from a dictionary."""
        segments = [
            SpeakerSegment.from_dict(s) for s in data.get("segments", [])
        ]
        return cls(
            session_id=str(data["session_id"]),
            segments=segments,
            full_transcript=str(data["full_transcript"]),
            language=str(data["language"]),
            overall_confidence=float(data["overall_confidence"]),
            processed_at_ms=int(data["processed_at_ms"]),
        )

    def to_json(self) -> str:
        """Return a compact JSON string."""
        return json.dumps(self.to_dict(), separators=(",", ":"))

    @classmethod
    def from_json(cls, raw: str | bytes) -> TranscriptionResultMessage:
        """Parse from a JSON string or bytes."""
        return cls.from_dict(json.loads(raw))


# ---------------------------------------------------------------------------
# Clinical notes
# ---------------------------------------------------------------------------

@dataclass
class SOAPNote:
    """Structured SOAP note produced by the clinical NLP service."""

    subjective: str
    objective: str
    assessment: str
    plan: str
    confidence_score: float  # 0.0 – 1.0

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-compatible dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SOAPNote:
        """Deserialise from a dictionary."""
        return cls(
            subjective=str(data["subjective"]),
            objective=str(data["objective"]),
            assessment=str(data["assessment"]),
            plan=str(data["plan"]),
            confidence_score=float(data["confidence_score"]),
        )


@dataclass
class ClinicalNoteMessage:
    """Final clinical note ready for EHR integration."""

    session_id: str
    patient_id: str
    practitioner_id: str
    encounter_id: str
    soap_note: SOAPNote
    redacted_transcript: str
    metadata: dict[str, str]
    created_at_ms: int

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-compatible dictionary."""
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ClinicalNoteMessage:
        """Deserialise from a dictionary."""
        return cls(
            session_id=str(data["session_id"]),
            patient_id=str(data["patient_id"]),
            practitioner_id=str(data["practitioner_id"]),
            encounter_id=str(data["encounter_id"]),
            soap_note=SOAPNote.from_dict(data["soap_note"]),
            redacted_transcript=str(data["redacted_transcript"]),
            metadata=dict(data.get("metadata", {})),
            created_at_ms=int(data["created_at_ms"]),
        )

    def to_json(self) -> str:
        """Return a compact JSON string."""
        return json.dumps(self.to_dict(), separators=(",", ":"))

    @classmethod
    def from_json(cls, raw: str | bytes) -> ClinicalNoteMessage:
        """Parse from a JSON string or bytes."""
        return cls.from_dict(json.loads(raw))


# ---------------------------------------------------------------------------
# Error / audit
# ---------------------------------------------------------------------------

@dataclass
class PipelineError:
    """Error event emitted when a processing stage fails."""

    session_id: str
    stage: str               # e.g. "audio-processor", "stt-engine"
    error_message: str
    original_data: str       # truncated payload for debugging (NO PHI)
    timestamp_ms: int

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-compatible dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PipelineError:
        """Deserialise from a dictionary."""
        return cls(
            session_id=str(data["session_id"]),
            stage=str(data["stage"]),
            error_message=str(data["error_message"]),
            original_data=str(data["original_data"]),
            timestamp_ms=int(data["timestamp_ms"]),
        )

    def to_json(self) -> str:
        """Return a compact JSON string."""
        return json.dumps(self.to_dict(), separators=(",", ":"))

    @classmethod
    def from_json(cls, raw: str | bytes) -> PipelineError:
        """Parse from a JSON string or bytes."""
        return cls.from_dict(json.loads(raw))


@dataclass
class AuditEvent:
    """HIPAA-grade audit log event."""

    event_id: str
    timestamp: str           # ISO-8601
    user_id: str
    action: str              # e.g. "READ", "CREATE", "UPDATE"
    resource_type: str       # e.g. "ClinicalNote", "AudioChunk"
    resource_id: str
    outcome: str             # "success" | "failure"
    detail: str = ""
    source_ip: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-compatible dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuditEvent:
        """Deserialise from a dictionary."""
        return cls(
            event_id=str(data["event_id"]),
            timestamp=str(data["timestamp"]),
            user_id=str(data["user_id"]),
            action=str(data["action"]),
            resource_type=str(data["resource_type"]),
            resource_id=str(data["resource_id"]),
            outcome=str(data["outcome"]),
            detail=str(data.get("detail", "")),
            source_ip=str(data.get("source_ip", "")),
        )

    def to_json(self) -> str:
        """Return a compact JSON string."""
        return json.dumps(self.to_dict(), separators=(",", ":"))

    @classmethod
    def from_json(cls, raw: str | bytes) -> AuditEvent:
        """Parse from a JSON string or bytes."""
        return cls.from_dict(json.loads(raw))
