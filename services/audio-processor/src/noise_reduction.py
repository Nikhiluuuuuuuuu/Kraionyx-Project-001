"""GPU-accelerated spectral-gating noise reduction.

Uses :pypi:`noisereduce` with its ``TorchGate`` backend so that the
denoising computation runs on the GPU (when available) rather than falling
back to CPU-only ``scipy`` / ``librosa`` routines.
"""

from __future__ import annotations

import structlog
from typing import Optional

import numpy as np
import torch

logger = structlog.get_logger(__name__)


class NoiseReducer:
    """Spectral-gating noise reduction using noisereduce TorchGate.

    The reducer operates on single-channel (mono) PCM audio represented as
    a 1-D ``numpy.ndarray`` of ``float32`` samples normalised to [-1, 1].
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        device: str = "cuda",
    ) -> None:
        """Initialise the noise reducer.

        Args:
            sample_rate: Expected sample rate of incoming audio.
            device: PyTorch device string (``"cuda"`` or ``"cpu"``).
                    Falls back to CPU automatically if CUDA is unavailable.
        """
        self._sample_rate = sample_rate

        if device == "cuda" and not torch.cuda.is_available():
            logger.warning("CUDA requested but unavailable — falling back to CPU")
            device = "cpu"

        self._device = torch.device(device)
        self._noise_profile: Optional[np.ndarray] = None

        # Lazy-import TorchGate to keep startup fast.
        self._gate: Optional[object] = None

        logger.info(
            "NoiseReducer initialised: sample_rate=%d device=%s",
            self._sample_rate,
            self._device,
        )

    def _ensure_gate(self) -> None:
        """Lazy-load the TorchGate instance on first use."""
        if self._gate is not None:
            return

        try:
            from noisereduce.torchgate import TorchGate  # type: ignore[import-untyped]

            self._gate = TorchGate(
                sr=self._sample_rate,
                nonstationary=True,
            ).to(self._device)
            logger.info("TorchGate model loaded on device=%s", self._device)
        except ImportError:
            logger.warning(
                "noisereduce.torchgate unavailable — using stationary fallback"
            )
            self._gate = None

    def reduce_noise(self, audio: np.ndarray) -> np.ndarray:
        """Apply spectral-gating noise reduction.

        Args:
            audio: 1-D float32 numpy array of audio samples.

        Returns:
            Denoised audio as a 1-D float32 numpy array (same length).
        """
        if audio.size == 0:
            logger.debug("Empty audio buffer — nothing to denoise")
            return audio

        self._ensure_gate()

        # --- TorchGate path (GPU-accelerated) ---
        if self._gate is not None:
            try:
                # TorchGate expects shape (batch, channels, samples)
                tensor = torch.from_numpy(audio.astype(np.float32))
                tensor = tensor.unsqueeze(0).unsqueeze(0).to(self._device)

                with torch.no_grad():
                    denoised_tensor = self._gate(tensor)  # type: ignore[operator]

                denoised = denoised_tensor.squeeze().cpu().numpy().astype(np.float32)
                logger.debug(
                    "TorchGate noise reduction applied: %d samples", len(denoised)
                )
                return denoised
            except Exception:
                logger.exception(
                    "TorchGate failed — falling back to stationary method"
                )

        # --- Stationary fallback (CPU) ---
        try:
            import noisereduce as nr  # type: ignore[import-untyped]

            denoised: np.ndarray = nr.reduce_noise(
                y=audio,
                sr=self._sample_rate,
                y_noise=self._noise_profile,
                stationary=self._noise_profile is not None,
                prop_decrease=0.8,
                n_fft=2048,
                hop_length=512,
            )
            logger.debug(
                "Stationary noise reduction applied: %d samples", len(denoised)
            )
            return denoised.astype(np.float32)
        except Exception:
            logger.exception(
                "All noise reduction methods failed — returning original audio"
            )
            return audio

    def calibrate(self, noise_sample: np.ndarray) -> None:
        """Calibrate the noise profile from a silence or background sample.

        Once calibrated, the stationary fallback method uses this profile
        for more accurate noise subtraction.

        Args:
            noise_sample: 1-D float32 numpy array of background / silence
                audio used to build the noise profile.
        """
        if noise_sample.size == 0:
            logger.warning("Empty noise sample provided — calibration skipped")
            return

        self._noise_profile = noise_sample.astype(np.float32).copy()
        logger.info(
            "Noise profile calibrated from %d samples (%.2f s)",
            len(self._noise_profile),
            len(self._noise_profile) / self._sample_rate,
        )
