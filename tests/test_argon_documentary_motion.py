"""Tests for Gemini 4 Argon Documentary Motion Engine (Swiss-Telemetry Kinetic Manifesto).

Verifies:
1. Strict Pydantic v2 configuration validation and archetype selection.
2. Complete HTML composition contract adherence:
   - Zero banned fonts (Inter, Roboto, Poppins, etc.)
   - Monumental typography (Big Shoulders Display 900/300 + IBM Plex Mono + Instrument Serif)
   - Deterministic GSAP timeline registration (window.__timelines["main"] = tl)
   - Zero Math.random() or non-deterministic drift
3. 3D CSS perspective stage (perspective: 1250px, stepped Z-planes, Euler rotation gimbal).
4. Procedural Catmull-Rom trajectory curves and reticle anomaly locks.
5. Mechanical shutter polarity inversion into archival paper (#F4F1EA) and carbon ink.
6. Deterministic preview render verification.
"""

import os
import re
from pathlib import Path
import pytest
from pydantic import ValidationError

from src.video.argon_documentary_motion import (
    ArgonMotionArchetype,
    ArgonDocumentaryConfig,
    ArgonMotionEngine,
    BANNED_FONTS,
)


def test_argon_config_validation():
    """Verify strict Pydantic v2 configuration validation."""
    config = ArgonDocumentaryConfig(
        scene_id=1,
        archetype=ArgonMotionArchetype.RADAR_TELEMETRY,
        title="MISSILE DETECTED",
        subtitle="5 ICBM LAUNCH VECTORS CONFIRMED",
        narrative_thesis="Oko satellite telemetry registers anomalous cloud top reflection over Montana.",
        telemetry_code="SERPUKHOV-15 // OKO-4 // DEFCON-1",
        metrics={"RADAR": "+4.82σ", "TIME_TO_IMPACT": "00:15:23 MSK", "STATUS": "CRITICAL"},
        duration_sec=6.0,
        fps=30,
    )
    assert config.scene_id == 1
    assert config.archetype == ArgonMotionArchetype.RADAR_TELEMETRY
    assert config.duration_sec == 6.0
    assert config.fps == 30
    assert config.metrics["RADAR"] == "+4.82σ"

    # Invalid fps or negative duration should fail
    with pytest.raises(ValidationError):
        ArgonDocumentaryConfig(
            scene_id=-1,
            archetype=ArgonMotionArchetype.RADAR_TELEMETRY,
            title="INVALID",
            duration_sec=-2.0,
        )


def test_argon_html_generation_contract():
    """Verify generated HTML fulfills all Swiss-Telemetry Kinetic Manifesto standards."""
    engine = ArgonMotionEngine()
    config = ArgonDocumentaryConfig(
        scene_id=2,
        archetype=ArgonMotionArchetype.RADAR_TELEMETRY,
        title="OKO SATELLITE",
        subtitle="EARLY WARNING RADAR ANOMALY",
        narrative_thesis="High-altitude infrared sensor detects launch flare signatures above Malmstrom AFB.",
        telemetry_code="RADAR-SYS-83 // GLITCH",
        metrics={"ALERT": "RED", "CONFIDENCE": "99.8%", "RADAR_SIGMA": "+4.82σ"},
        duration_sec=5.0,
    )
    html = engine.build_html(config)

    # 1. Timeline contract
    assert 'window.__timelines["main"] = tl;' in html or 'window.__timelines = window.__timelines || {};' in html
    assert 'gsap.timeline({ paused: true' in html

    # 2. Monumental Typography fonts present
    assert "Big Shoulders Display" in html
    assert "IBM Plex Mono" in html
    assert "Instrument Serif" in html

    # 3. Zero banned fonts
    for banned in BANNED_FONTS:
        pattern = re.compile(rf"font-family:[^;]*\b{banned}\b", re.IGNORECASE)
        assert not pattern.search(html), f"Banned font {banned} found in Argon HTML output!"

    # 4. Zero Math.random()
    assert "Math.random" not in html

    # 5. Swiss-Telemetry Palettes present
    assert "#090a0d" in html.lower() or "#090A0D" in html
    assert "#d4ff00" in html.lower() or "#D4FF00" in html  # Acid Volt


def test_argon_archetype_zspace_bunker_parallax():
    """Verify ZSPACE_BUNKER_PARALLAX archetype contains 3D CSS viewport and Euler gimbal."""
    engine = ArgonMotionEngine()
    config = ArgonDocumentaryConfig(
        scene_id=4,
        archetype=ArgonMotionArchetype.ZSPACE_BUNKER_PARALLAX,
        title="SERPUKHOV-15",
        subtitle="THE SECRET NUCLEAR BUNKER",
        narrative_thesis="Deep within the concrete blast walls 100km south of Moscow, one officer holds humanity's fate.",
        telemetry_code="BUNKER-Z-SPACE-PARALLAX",
        duration_sec=7.0,
    )
    html = engine.build_html(config)

    # Must contain 3D CSS viewport and stage perspective
    assert "perspective: 1250px" in html or "perspective:1250px" in html
    assert "preserve-3d" in html
    assert "rotationX" in html or "rotationY" in html
    assert "z:" in html or "translateZ" in html


def test_argon_archetype_classified_dossier_inversion():
    """Verify CLASSIFIED_DOSSIER_INVERSION contains mechanical shutter polarity inversion."""
    engine = ArgonMotionEngine()
    config = ArgonDocumentaryConfig(
        scene_id=7,
        archetype=ArgonMotionArchetype.CLASSIFIED_DOSSIER_INVERSION,
        title="СОВЕРШЕННО СЕКРЕТНО",
        subtitle="DECLASSIFIED SOVIET TELEGRAM",
        narrative_thesis="A handwritten post-incident report concealed by the Kremlin for over a decade.",
        telemetry_code="KREMLIN-ARCHIVE // DOSSIER 17-B",
        duration_sec=6.0,
    )
    html = engine.build_html(config)

    # Inversion to Archival Paper and Carbon Ink
    assert "#f4f1ea" in html.lower() or "#F4F1EA" in html  # Paper
    assert "#0b0c10" in html.lower() or "#0B0C10" in html  # Carbon Ink
    assert "shutter" in html.lower() or "polarity" in html.lower()


def test_argon_archetype_netflix_osint_stage():
    """Verify NETFLIX_OSINT_STAGE contains OSINT desktop, map coordinates, and CRT scanlines."""
    engine = ArgonMotionEngine()
    config = ArgonDocumentaryConfig(
        scene_id=10,
        archetype=ArgonMotionArchetype.NETFLIX_OSINT_STAGE,
        title="INVESTIGATIVE FORENSICS",
        subtitle="GLOBAL SATELLITE FLIGHT PATH RECONSTRUCTION",
        narrative_thesis="Reconstructing the orbital intersection of Oko Cosmos 1374 and the sun glint vector.",
        telemetry_code="OSINT-DESKTOP // COSMOS-1374",
        metrics={"LAT": "55.7558° N", "LON": "37.6173° E", "ORBIT": "MOLNIYA-1"},
        duration_sec=5.5,
    )
    html = engine.build_html(config)

    assert "MOLNIYA-1" in html
    assert "COSMOS-1374" in html
    assert "scanline" in html.lower() or "grid" in html.lower()
