"""Unit and integration tests for DarkFactory Hybrid Studio & Neural Foley Engine.

Tests:
  1. Pydantic v2 contract integrity.
  2. Acoustic Room Impulse Response (IR) convolution (Bunker, Archive Vault, Control Room).
  3. Tier 1: Real studio asset retrieval from 1,224 SFX library.
  4. Tier 2: Neural fallback synthesis and atomic library caching.
  5. FoleyLibrary integration ensuring complete elimination of amateur sine waves.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import wave
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.video.foley_contracts import (
    AcousticSpace,
    FoleyCueRequest,
    FoleyExecutionResult,
    FoleySourceTier,
)


def test_foley_contracts_pydantic_validation() -> None:
    """Validate Pydantic v2 constraints on cue requests and execution results."""
    req = FoleyCueRequest(
        cue_id="cue_01",
        semantic_prompt="heavy industrial switch clank",
        timestamp_sec=2.5,
        target_duration_sec=0.8,
        acoustic_space=AcousticSpace.BUNKER_CONCRETE,
        gain_db=-6.0,
        pan=-0.2,
    )
    assert req.cue_id == "cue_01"
    assert req.gain_db == -6.0
    assert req.acoustic_space == AcousticSpace.BUNKER_CONCRETE

    res = FoleyExecutionResult(
        success=True,
        cue_id="cue_01",
        audio_path="/fake/path.wav",
        source_tier=FoleySourceTier.STUDIO_SAMPLE,
        matched_asset_name="switch_01.wav",
        similarity_score=0.92,
        acoustic_space_applied=AcousticSpace.BUNKER_CONCRETE,
        duration_sec=0.75,
        cached_to_catalog=False,
    )
    assert res.success is True
    assert res.source_tier == FoleySourceTier.STUDIO_SAMPLE
    assert res.similarity_score == 0.92


def test_ir_convolver_room_acoustics() -> None:
    """Verify FoleyIRConvolver applies authentic early reflections without distortion."""
    from src.video.foley_ir_convolver import FoleyIRConvolver

    convolver = FoleyIRConvolver(sample_rate=44100)
    dry_signal = np.zeros(44100, dtype=np.float32)
    # Impulso seco inicial de 10ms
    dry_signal[:441] = np.sin(np.linspace(0, 10 * np.pi, 441, dtype=np.float32))

    # Convolução no Bunker
    bunker_audio = convolver.apply_space(dry_signal, AcousticSpace.BUNKER_CONCRETE)
    assert len(bunker_audio) >= len(dry_signal)
    assert not np.isnan(bunker_audio).any()
    assert np.max(np.abs(bunker_audio)) <= 1.0
    # O decaimento deve estender a cauda sonora além do impulso seco
    assert np.sum(np.abs(bunker_audio[1000:5000])) > 0.01

    # Convolução no Cofre de Arquivo (Vault)
    vault_audio = convolver.apply_space(dry_signal, AcousticSpace.ARCHIVE_VAULT)
    assert len(vault_audio) >= len(dry_signal)
    assert not np.isnan(vault_audio).any()
    assert np.max(np.abs(vault_audio)) <= 1.0


def test_hybrid_engine_tier1_studio_match(tmp_path: Path) -> None:
    """Verify Tier 1 retrieves authentic broadcast SFX from catalog and applies IR."""
    from src.video.hybrid_foley_engine import HybridFoleyEngine

    engine = HybridFoleyEngine(output_dir=tmp_path / "foley_out")
    req = FoleyCueRequest(
        cue_id="test_whoosh_01",
        semantic_prompt="whoosh transition sweep",
        acoustic_space=AcousticSpace.ARCHIVE_VAULT,
        gain_db=-10.0,
    )
    result = engine.resolve_cue(req)
    assert result.success is True
    assert result.source_tier == FoleySourceTier.STUDIO_SAMPLE
    assert Path(result.audio_path).is_file()
    assert result.similarity_score >= 0.50
    assert result.acoustic_space_applied == AcousticSpace.ARCHIVE_VAULT


def test_hybrid_engine_tier2_neural_fallback_and_cache(tmp_path: Path) -> None:
    """Verify Tier 2 synthesizes rare uncataloged sound and atomically caches to library."""
    from src.video.hybrid_foley_engine import HybridFoleyEngine

    custom_sfx_dir = tmp_path / "sfx"
    custom_sfx_dir.mkdir(parents=True, exist_ok=True)
    engine = HybridFoleyEngine(output_dir=tmp_path / "foley_out", sfx_dir=custom_sfx_dir)

    req = FoleyCueRequest(
        cue_id="test_neural_geiger",
        semantic_prompt="rare_plutonium_geiger_burst_classified_anomaly_xyz",
        target_duration_sec=0.6,
        acoustic_space=AcousticSpace.BUNKER_CONCRETE,
        allow_neural_fallback=True,
    )

    result = engine.resolve_cue(req)
    assert result.success is True
    assert result.source_tier in (FoleySourceTier.NEURAL_MMAUDIO, FoleySourceTier.NEURAL_AUDIOGEN)
    assert Path(result.audio_path).is_file()
    assert result.cached_to_catalog is True

    # Verificar que o arquivo foi adicionado ao diretório de gerados
    cached_file = custom_sfx_dir / "generated_foley" / f"{result.cue_id}.wav"
    assert cached_file.is_file()


def test_foley_library_zero_sines_guarantee(tmp_path: Path) -> None:
    """Verify FoleyLibrary uses the hybrid engine and has zero crude sine waves."""
    from src.video.foley_library import FoleyLibrary

    lib = FoleyLibrary(output_dir=tmp_path / "lib_out")
    pcm = lib.synthesize_sfx("teletype_burst", sample_rate=44100, duration_sec=0.5)

    assert isinstance(pcm, np.ndarray)
    assert len(pcm) > 0
    assert not np.isnan(pcm).any()
    # Verifica que o sinal tem densidade espectral rica (não é uma onda senoidal pura)
    fft_vals = np.abs(np.fft.rfft(pcm))
    non_zero_bins = np.count_nonzero(fft_vals > (np.max(fft_vals) * 0.05))
    # Uma senoide pura teria ~1 a 3 bins significativos; áudio de estúdio / ruído moldado tem dezenas
    assert non_zero_bins >= 15, "O áudio gerado ainda se parece com uma onda senoidal pura!"
