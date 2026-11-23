"""DarkFactory — Pydantic v2 Contracts for Hybrid Studio & Neural Foley Engine.

Defines strict types for Tier 1 (Studio SFX library retrieval) and Tier 2 (Neural synthesis),
acoustic space convolution parameters, and execution contracts.
"""

from __future__ import annotations

import sys
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

# ADR-01: Windows UTF-8 stdout/stderr reconfiguration
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


class FoleySourceTier(str, Enum):
    """Execution tier utilized for sound design rendering."""

    STUDIO_SAMPLE = "STUDIO_SAMPLE"       # Tier 1: 1,224 curated studio SFX library
    NEURAL_MMAUDIO = "NEURAL_MMAUDIO"     # Tier 2A: MMAudio model synthesis
    NEURAL_AUDIOGEN = "NEURAL_AUDIOGEN"   # Tier 2B: AudioGen model synthesis


class AcousticSpace(str, Enum):
    """Physical acoustic environments for room impulse response (IR) convolution."""

    BUNKER_CONCRETE = "bunker_concrete"   # Reinforced Soviet underground bunker (heavy early reflections)
    ARCHIVE_VAULT = "archive_vault"       # Confined document vault (close acoustic boundary, dry paper slap)
    CONTROL_ROOM = "control_room"         # Electronic radar console chamber (low-end dampening, glass flutter)
    DRY_STUDIO = "dry_studio"             # Anechoic / direct sound (zero room IR)


class FoleyCueRequest(BaseModel):
    """Input contract for resolving or synthesizing a foley event."""

    cue_id: str = Field(..., description="Unique event identifier")
    semantic_prompt: str = Field(..., description="Acoustic description, keyword, or action prompt")
    timestamp_sec: float = Field(0.0, ge=0.0, description="Timeline onset in seconds")
    target_duration_sec: Optional[float] = Field(None, gt=0.0, description="Desired sound duration in seconds")
    acoustic_space: AcousticSpace = Field(AcousticSpace.BUNKER_CONCRETE, description="Target room impulse response")
    gain_db: float = Field(-8.0, ge=-36.0, le=0.0, description="Gain attenuation relative to 0 dBFS")
    pan: float = Field(0.0, ge=-1.0, le=1.0, description="Stereo panorama (-1.0 Left to +1.0 Right)")
    allow_neural_fallback: bool = Field(True, description="Whether to dispatch to neural generation if missing")


class FoleyExecutionResult(BaseModel):
    """Output contract guaranteed after foley resolution or synthesis."""

    success: bool
    cue_id: str
    audio_path: str
    source_tier: FoleySourceTier
    matched_asset_name: Optional[str] = None
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    acoustic_space_applied: Optional[AcousticSpace] = None
    duration_sec: float = Field(..., ge=0.0)
    cached_to_catalog: bool = False
    error: Optional[str] = None
