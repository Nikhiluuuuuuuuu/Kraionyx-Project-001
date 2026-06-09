"""Speaker diarization using pyannote.audio.

Lazily loads the ``pyannote/speaker-diarization-3.1`` pipeline and applies
it to mono 16 kHz audio.  After diarization the module assigns clinical
roles (Doctor / Patient) based on speaking-order heuristics.
"""

from __future__ import annotations

import io
import structlog
import tempfile
from typing import Any, Optional

import numpy as np
import soundfile as sf
import torch

logger = structlog.get_logger(__name__)


class SpeakerDiarizer:
    """Speaker diarization using pyannote.audio."""

    _MODEL_NAME = "pyannote/speaker-diarization-3.1"

    def __init__(self, hf_token: str, device: str = "cuda") -> None:
        """Initialise the diarizer (model is loaded lazily on first use).

        Args:
            hf_token: HuggingFace API token with access to pyannote models.
            device: ``"cuda"`` or ``"cpu"``.  Falls back to CPU if CUDA is
                unavailable.
        """
        if device == "cuda" and not torch.cuda.is_available():
            logger.warning("CUDA requested but unavailable — falling back to CPU")
            device = "cpu"

        self._device = torch.device(device)
        self._hf_token = hf_token
        self._pipeline: Optional[Any] = None
        logger.info("SpeakerDiarizer initialised: device=%s", self._device)

    def _load_model(self) -> None:
        """Lazy-load the pyannote speaker-diarization pipeline."""
        if self._pipeline is not None:
            return

        logger.info("Loading diarization model %s …", self._MODEL_NAME)
        from pyannote.audio import Pipeline  # type: ignore[import-untyped]

        self._pipeline = Pipeline.from_pretrained(
            self._MODEL_NAME,
            use_auth_token=self._hf_token,
        )
        self._pipeline.to(self._device)
        logger.info(
            "Diarization model loaded on device=%s", self._device
        )

    def diarize(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        min_speakers: int = 1,
        max_speakers: int = 5,
    ) -> list[dict[str, Any]]:
        """Perform speaker diarization on audio.

        Optimized for extreme edge cases (overlapping speakers, hospital noise).
        Pyannote 3.1 inherently handles overlapping speech through its 
        segmentation module, but constraining speaker counts helps in noisy 
        environments to prevent hallucinated speakers.

        Args:
            audio: 1-D float32 numpy array of mono audio samples.
            sample_rate: Sampling rate in Hz.
            min_speakers: Minimum number of expected speakers.
            max_speakers: Maximum number of expected speakers.

        Returns:
            List of dicts ``{"speaker": str, "start": float, "end": float}``
            sorted by start time.
        """
        self._load_model()

        if audio.size == 0:
            logger.warning("Empty audio — returning no segments")
            return []

        # pyannote expects a file-like WAV object or a path.
        buf = io.BytesIO()
        sf.write(buf, audio, sample_rate, format="WAV", subtype="FLOAT")
        buf.seek(0)

        # Write to a temporary file because some pyannote versions
        # require a seekable path.
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(buf.getvalue())
            tmp_path = tmp.name

        try:
            # Pass min_speakers and max_speakers to constrain the clustering 
            # and improve robustness against hospital noise.
            diarization = self._pipeline(
                tmp_path, 
                min_speakers=min_speakers, 
                max_speakers=max_speakers
            )  # type: ignore[misc]
        finally:
            import os
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        segments: list[dict[str, Any]] = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append(
                {
                    "speaker": str(speaker),
                    "start": round(float(turn.start), 3),
                    "end": round(float(turn.end), 3),
                }
            )

        # Sort by start time (should already be, but be safe).
        segments.sort(key=lambda s: s["start"])
        logger.info(
            "Diarization complete: %d segments, %d unique speakers",
            len(segments),
            len({s["speaker"] for s in segments}),
        )
        return segments

    def assign_roles(self, segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Assign clinical roles (Doctor / Patient) to speaker labels.

        Heuristic: the *first* speaker in the encounter is assumed to be the
        Doctor (the provider typically initiates the conversation).  All other
        speakers are labelled as Patient.  If there are more than two
        speakers the third-onwards are labelled ``Other-N``.

        Args:
            segments: List of diarization segments (mutated in place).

        Returns:
            The same list with ``speaker`` values replaced by role names.
        """
        if not segments:
            return segments

        # Determine ordering of unique speakers by their first appearance.
        seen: dict[str, None] = {}
        for seg in segments:
            spk = seg["speaker"]
            if spk not in seen:
                seen[spk] = None

        role_map: dict[str, str] = {}
        for idx, spk in enumerate(seen):
            if idx == 0:
                role_map[spk] = "Doctor"
            elif idx == 1:
                role_map[spk] = "Patient"
            else:
                role_map[spk] = f"Other-{idx - 1}"

        for seg in segments:
            seg["speaker"] = role_map[seg["speaker"]]

        logger.info("Role assignment: %s", role_map)
        return segments
