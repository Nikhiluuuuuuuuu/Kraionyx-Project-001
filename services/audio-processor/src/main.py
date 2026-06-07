"""Audio Processor pipeline entry point.

Consumes raw encrypted audio chunks from Kafka, applies noise reduction and
speaker diarization, re-encrypts the processed audio, and publishes the
result to the ``audio.preprocessed`` topic.
"""

from __future__ import annotations

import base64
import gc
import json
import logging
import signal
import struct
import sys
import time
import torch
from typing import Any

import numpy as np

from kraionyx_common.crypto import AES256GCM
from kraionyx_common.models import AudioChunkMessage, PipelineError

from .config import Config
from .consumer import AudioConsumer
from .diarization import SpeakerDiarizer
from .noise_reduction import NoiseReducer
from .producer import AudioProducer

logger = logging.getLogger(__name__)


def setup_logging(level: str) -> None:
    """Configure structured JSON logging for the service.

    Args:
        level: Logging level name (e.g. ``"INFO"``).
    """
    log_format = json.dumps({
        "time": "%(asctime)s",
        "level": "%(levelname)s",
        "logger": "%(name)s",
        "message": "%(message)s",
    })
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=log_format,
        stream=sys.stdout,
    )


def _pcm16_to_float32(raw_bytes: bytes) -> np.ndarray:
    """Convert raw PCM-16 little-endian bytes to float32 in [-1, 1].

    Args:
        raw_bytes: PCM signed 16-bit little-endian audio bytes.

    Returns:
        Numpy float32 array normalised to [-1.0, 1.0].
    """
    sample_count = len(raw_bytes) // 2
    samples = struct.unpack(f"<{sample_count}h", raw_bytes[: sample_count * 2])
    return np.array(samples, dtype=np.float32) / 32768.0


def _float32_to_pcm16(audio: np.ndarray) -> bytes:
    """Convert float32 audio array back to PCM-16 bytes.

    Args:
        audio: Float32 array in [-1.0, 1.0].

    Returns:
        Raw PCM signed 16-bit little-endian bytes.
    """
    clipped = np.clip(audio, -1.0, 1.0)
    int_samples = (clipped * 32767.0).astype(np.int16)
    return int_samples.tobytes()


def main() -> None:
    """Run the audio-processor pipeline."""
    config = Config.from_env()
    setup_logging(config.log_level)

    logger.info("=== Audio Processor starting ===")

    # Initialise components
    noise_reducer = NoiseReducer(config.sample_rate, config.device)
    diarizer = SpeakerDiarizer(config.hf_token, config.device)
    crypto = AES256GCM(AES256GCM.key_from_base64(config.encryption_key))
    consumer = AudioConsumer(config)
    producer = AudioProducer(config)

    # ------------------------------------------------------------------
    # Graceful shutdown via signals
    # ------------------------------------------------------------------
    shutdown_requested = False

    def _signal_handler(signum: int, _frame: Any) -> None:
        nonlocal shutdown_requested
        sig_name = signal.Signals(signum).name
        logger.info("Received %s — initiating graceful shutdown", sig_name)
        shutdown_requested = True
        consumer.close()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    # ------------------------------------------------------------------
    # Message handler
    # ------------------------------------------------------------------
    session_buffers: dict[str, list[np.ndarray]] = {}

    def handle_message(msg: AudioChunkMessage) -> None:
        """Process a single audio chunk through the pipeline.

        Steps:
            1. Decrypt audio data.
            2. Decode PCM-16 bytes → float32 numpy array.
            3. Buffer chunks into 10s windows.
            4. Apply noise reduction.
            5. Run speaker diarization.
            6. Re-encrypt processed audio.
            7. Publish to ``audio.preprocessed``.

        Args:
            msg: The incoming ``AudioChunkMessage``.
        """
        session_id = msg.session_id
        t0 = time.monotonic()
        logger.info(
            "Processing chunk: session_id=%s chunk_index=%d",
            session_id,
            msg.chunk_index,
        )

        try:
            # 1. Decrypt
            raw_audio_bytes = crypto.decrypt(msg.audio_data)

            # 2. PCM-16 → float32
            audio = _pcm16_to_float32(raw_audio_bytes)
            logger.debug(
                "Decoded %d samples (%.2f s) for session_id=%s",
                len(audio),
                len(audio) / config.sample_rate,
                session_id,
            )

            # 3. Buffer audio chunks
            if session_id not in session_buffers:
                session_buffers[session_id] = []
            
            session_buffers[session_id].append(audio)
            
            total_samples = sum(len(a) for a in session_buffers[session_id])
            total_seconds = total_samples / config.sample_rate
            
            if total_seconds < 10.0:
                logger.debug("Buffering chunk for %s: %.2fs / 10.0s", session_id, total_seconds)
                return
            
            buffered_audio = np.concatenate(session_buffers[session_id])
            session_buffers[session_id] = []

            # 4. Noise reduction
            cleaned_audio = noise_reducer.reduce_noise(buffered_audio)

            # 5. Speaker diarization
            diarization_segments = diarizer.diarize(
                cleaned_audio, sample_rate=config.sample_rate
            )
            diarization_segments = diarizer.assign_roles(diarization_segments)

            # 6. Re-encrypt processed audio
            processed_pcm = _float32_to_pcm16(cleaned_audio)
            encrypted_audio = crypto.encrypt(processed_pcm)

            # 7. Build and publish result
            result: dict[str, Any] = {
                "session_id": session_id,
                "chunk_index": msg.chunk_index,
                "timestamp_ms": msg.timestamp_ms,
                "audio_data": encrypted_audio,
                "format": msg.format,
                "sample_rate": config.sample_rate,
                "channels": msg.channels,
                "diarization": diarization_segments,
            }
            producer.produce(
                topic=config.kafka_output_topic,
                key=session_id,
                message=result,
            )

            elapsed = time.monotonic() - t0
            logger.info(
                "Window processed: session_id=%s chunk_index=%d "
                "speakers=%d elapsed=%.3fs",
                session_id,
                msg.chunk_index,
                len({s["speaker"] for s in diarization_segments}),
                elapsed,
            )

        except Exception as exc:
            elapsed = time.monotonic() - t0
            logger.exception(
                "Failed to process chunk: session_id=%s chunk_index=%d "
                "elapsed=%.3fs",
                session_id,
                msg.chunk_index,
                elapsed,
            )
            error = PipelineError(
                session_id=session_id,
                stage="audio-processor",
                error_message=str(exc),
                original_data=f"chunk_index={msg.chunk_index}",
                timestamp_ms=int(time.time() * 1000),
            )
            producer.produce_error(error)
            raise

    # ------------------------------------------------------------------
    # Run the blocking consume loop
    # ------------------------------------------------------------------
    try:
        consumer.consume(handle_message)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt — shutting down")
    finally:
        producer.close()
        logger.info("=== Audio Processor stopped ===")


if __name__ == "__main__":
    main()
