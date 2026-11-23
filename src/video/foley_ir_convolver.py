"""DarkFactory — Cinematic Acoustic Space & Impulse Response (IR) Convolver.

Provides realistic room impulse response convolution for Soviet bunkers, archival vaults,
and telemetry control rooms using O(N log N) FFT convolution on CPU.
Includes pure NumPy fallback when SciPy is not installed.
"""

from __future__ import annotations

import logging
import math
import sys
from pathlib import Path
from typing import Dict, Optional

import numpy as np

try:
    import scipy.signal
    HAS_SCIPY = True
except ImportError:
    scipy = None  # type: ignore
    HAS_SCIPY = False

from src.video.foley_contracts import AcousticSpace

# ADR-01: Windows UTF-8 stdout/stderr reconfiguration
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logger = logging.getLogger("darkfactory.video.foley_ir_convolver")


def _fft_convolve(x: np.ndarray, h: np.ndarray) -> np.ndarray:
    """Zero-dependency FFT convolution using pure NumPy."""
    n_out = len(x) + len(h) - 1
    n_fft = 1 << (n_out - 1).bit_length()
    X = np.fft.rfft(x, n_fft)
    H = np.fft.rfft(h, n_fft)
    y = np.fft.irfft(X * H, n_fft)
    return y[:n_out].astype(np.float32)


def _lowpass_filter(sig: np.ndarray, cutoff_hz: float, sr: int) -> np.ndarray:
    """Applies lowpass filtering using SciPy if available, otherwise 1-pole IIR in NumPy."""
    if HAS_SCIPY:
        b, a = scipy.signal.butter(2, min(cutoff_hz, sr * 0.49) / (sr / 2.0), btype="low")
        return scipy.signal.lfilter(b, a, sig).astype(np.float32)
    # 1-pole recursive lowpass filter fallback
    rc = 1.0 / (2.0 * math.pi * max(100.0, cutoff_hz))
    dt = 1.0 / sr
    alpha = dt / (rc + dt)
    out = np.empty_like(sig, dtype=np.float32)
    y_prev = 0.0
    for i in range(len(sig)):
        y_prev = alpha * sig[i] + (1.0 - alpha) * y_prev
        out[i] = y_prev
    return out


class FoleyIRConvolver:
    """CPU-optimized FFT acoustic space impulse response processor."""

    def __init__(self, sample_rate: int = 44100) -> None:
        self.sample_rate = sample_rate
        self._cached_irs: Dict[AcousticSpace, np.ndarray] = {}

    def _generate_synthetic_ir(self, space: AcousticSpace) -> np.ndarray:
        """Synthesize high-fidelity physical room impulse response based on room geometry."""
        sr = self.sample_rate

        if space == AcousticSpace.BUNKER_CONCRETE:
            # Massive reinforced underground concrete bunker:
            # RT60 = 0.85s, discrete early reflections, low-end room resonances (60Hz, 120Hz)
            duration_sec = 0.90
            n = int(sr * duration_sec)
            t = np.linspace(0.0, duration_sec, n, endpoint=False, dtype=np.float32)

            # Exponential decay envelope (RT60: -60 dB at 0.85s -> ln(1e-3) / 0.85 ≈ -8.12)
            env = np.exp(-t * 8.5)

            rng = np.random.default_rng(1983)
            diffuse = rng.normal(0.0, 1.0, size=n).astype(np.float32) * env

            # High-frequency damping (air absorption and concrete surface damping)
            diffuse_filtered = _lowpass_filter(diffuse, 3500.0, sr)

            # Discrete early reflections (wall bounces at 14ms, 28ms, 45ms, 68ms)
            ir = diffuse_filtered * 0.65
            early_taps = [(0.014, 0.45), (0.028, -0.32), (0.045, 0.25), (0.068, -0.18)]
            for delay_s, gain in early_taps:
                idx = int(delay_s * sr)
                if idx < n:
                    ir[idx] += gain

        elif space == AcousticSpace.ARCHIVE_VAULT:
            # Confined document vault: tight boundaries, RT60 = 0.35s, high absorption
            duration_sec = 0.40
            n = int(sr * duration_sec)
            t = np.linspace(0.0, duration_sec, n, endpoint=False, dtype=np.float32)
            env = np.exp(-t * 18.0)

            rng = np.random.default_rng(1977)
            diffuse = rng.normal(0.0, 1.0, size=n).astype(np.float32) * env
            diffuse_filtered = _lowpass_filter(diffuse, 4500.0, sr)
            ir = diffuse_filtered * 0.70

            # Close wall reflections (4ms, 9ms, 17ms)
            for delay_s, gain in [(0.004, 0.55), (0.009, -0.35), (0.017, 0.20)]:
                idx = int(delay_s * sr)
                if idx < n:
                    ir[idx] += gain

        elif space == AcousticSpace.CONTROL_ROOM:
            # Electronic telemetry console room: metal racks, glass screens, mild flutter
            duration_sec = 0.55
            n = int(sr * duration_sec)
            t = np.linspace(0.0, duration_sec, n, endpoint=False, dtype=np.float32)
            env = np.exp(-t * 12.0)

            rng = np.random.default_rng(1984)
            diffuse = rng.normal(0.0, 1.0, size=n).astype(np.float32) * env
            diffuse_filtered = _lowpass_filter(diffuse, 5500.0, sr)
            ir = diffuse_filtered * 0.60

            # Subtle flutter reflections from console surfaces (7ms, 15ms, 23ms, 35ms)
            for delay_s, gain in [(0.007, 0.40), (0.015, -0.30), (0.023, 0.22), (0.035, -0.15)]:
                idx = int(delay_s * sr)
                if idx < n:
                    ir[idx] += gain
        else:
            # DRY_STUDIO: delta impulse (pass-through)
            ir = np.zeros(64, dtype=np.float32)
            ir[0] = 1.0

        # Normalizar energia do impulso
        peak = float(np.max(np.abs(ir)))
        if peak > 1e-6:
            ir = ir / peak
        return ir.astype(np.float32)

    def get_ir(self, space: AcousticSpace) -> np.ndarray:
        """Fetch or synthesize and cache room impulse response."""
        if space not in self._cached_irs:
            self._cached_irs[space] = self._generate_synthetic_ir(space)
        return self._cached_irs[space]

    def apply_space(
        self,
        mono_signal: np.ndarray,
        space: AcousticSpace,
        wet_mix: float = 0.35,
    ) -> np.ndarray:
        """Convolve dry mono audio signal with acoustic room impulse response.

        Args:
            mono_signal: 1D float32 array in range [-1.0, 1.0].
            space: AcousticSpace environment enum.
            wet_mix: Wet/dry mix balance (0.0 = 100% dry, 1.0 = 100% wet).

        Returns:
            Convolved float32 mono array normalized to safe broadcast peak (<= 0.95).
        """
        if space == AcousticSpace.DRY_STUDIO or wet_mix <= 0.001 or len(mono_signal) == 0:
            return np.clip(mono_signal, -0.95, 0.95).astype(np.float32)

        ir = self.get_ir(space)
        wet_mix = max(0.0, min(1.0, float(wet_mix)))
        dry_mix = 1.0 - (wet_mix * 0.5)

        # FFT convolution via SciPy or NumPy fallback: O(N log N)
        if HAS_SCIPY:
            convolved = scipy.signal.fftconvolve(mono_signal, ir, mode="full").astype(np.float32)
        else:
            convolved = _fft_convolve(mono_signal, ir)

        # Truncar cauda excessiva para evitar latência desnecessária (> 2.0s após final)
        max_len = len(mono_signal) + int(self.sample_rate * 0.90)
        if len(convolved) > max_len:
            convolved = convolved[:max_len]

        # Alinhar comprimento do dry com o sinal convoluído
        dry_padded = np.zeros(len(convolved), dtype=np.float32)
        dry_padded[: len(mono_signal)] = mono_signal

        # Mixagem estéreo/mono balanceada
        blended = (dry_padded * dry_mix) + (convolved * wet_mix)

        # Normalização suave preservando dinâmica original
        peak = float(np.max(np.abs(blended)))
        if peak > 0.95:
            blended = (blended / peak) * 0.92

        return blended.astype(np.float32)
