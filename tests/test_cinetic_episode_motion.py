"""Test suite for DarkFactory Cinetic Full Episode Motion Engine.

Validates the Netflix/BBC investigative documentary motion graphics standard
inspired by Felipe Borges (Felpborges/claude-video) and Cinetic:
- 1080p canvas with inkStage (#0D0B0A) background
- Center-band kinetic statements (35%-65% frame height)
- High-contrast typography (#F2EFEF) with vivid tactical red accents (#DC2626)
- Multi-layer Ken Burns zoom/pan on archival photos
- Declassified stamp slam animations with synchronized SFX
- Automatic mirroring to data/broll/ for seamless master video assembly
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import cv2
import numpy as np
import pytest

from src.video.cinetic_episode_motion import (
    CineticEpisodeMotionEngine,
    CineticSceneConfig,
    extract_kinetic_statement,
    INK_STAGE_PALETTE,
)


@pytest.fixture
def temp_workspace():
    """Create a temporary isolated test workspace."""
    tmp = Path(tempfile.mkdtemp(prefix="df_cinetic_test_"))
    broll_dir = tmp / "data" / "broll"
    output_dir = tmp / "data" / "final" / "motion_overlays"
    sfx_dir = tmp / "data" / "sfx"
    broll_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    sfx_dir.mkdir(parents=True, exist_ok=True)

    # Create dummy base archival photo
    dummy_img = np.full((1080, 1920, 3), 40, dtype=np.uint8)
    cv2.putText(dummy_img, "ARCHIVAL TEST PHOTO", (200, 540), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (220, 220, 220), 3)
    cv2.imwrite(str(broll_dir / "scene_1.jpg"), dummy_img)

    # Create minimal mock sfx manifest
    manifest_data = {
        "whooshes": ["data/sfx/whoosh1.wav"],
        "stamp_slam": ["data/sfx/slam1.wav"],
        "radar_ping": ["data/sfx/radar1.wav"],
    }
    with open(sfx_dir / "sfx_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest_data, f)

    yield {
        "root": tmp,
        "broll": broll_dir,
        "output": output_dir,
        "sfx": sfx_dir,
    }
    shutil.rmtree(tmp, ignore_errors=True)


def test_cinetic_palette_constants():
    """Ensure standard inkStage documentary palette meets Cinetic specs."""
    assert INK_STAGE_PALETTE["bg_ink"] == "#0D0B0A"
    assert INK_STAGE_PALETTE["text_primary"] == "#F2EFEF"
    assert INK_STAGE_PALETTE["accent_red"] == "#DC2626"
    assert "border_dark" in INK_STAGE_PALETTE


def test_extract_kinetic_statement():
    """Test punchy headline extraction and operative keyword identification."""
    text = "At 12:15 AM on September 26, 1983, a red siren illuminated a top-secret Soviet bunker. Five nuclear missiles were reported in flight."
    headline, accent_word = extract_kinetic_statement(text, scene_id=1)
    
    assert len(headline.split()) >= 1
    assert len(headline.split()) <= 8
    assert isinstance(accent_word, str)
    assert len(accent_word) > 0


def test_cinetic_engine_initialization(temp_workspace):
    """Test engine setup with custom paths and defaults."""
    engine = CineticEpisodeMotionEngine(
        broll_dir=temp_workspace["broll"],
        output_dir=temp_workspace["output"],
        sfx_dir=temp_workspace["sfx"],
        width=1920,
        height=1080,
        fps=30,
    )
    assert engine.width == 1920
    assert engine.height == 1080
    assert engine.fps == 30
    assert engine.broll_dir == temp_workspace["broll"].resolve()
    assert engine.output_dir == temp_workspace["output"].resolve()


def test_cinetic_synthesize_frame(temp_workspace):
    """Test generating a single frame with Ken Burns zoom and centered kinetic typography."""
    engine = CineticEpisodeMotionEngine(
        broll_dir=temp_workspace["broll"],
        output_dir=temp_workspace["output"],
        sfx_dir=temp_workspace["sfx"],
    )
    cfg = CineticSceneConfig(
        scene_id=1,
        headline="FIVE NUCLEAR MISSILES",
        accent_word="MISSILES",
        stamp_text="TOP SECRET // DECLASSIFIED",
        telemetry="SERPUKHOV-15 // 55°45'N 37°37'E",
        duration_sec=3.0,
    )

    frame = engine.render_motion_frame(
        cfg=cfg,
        progress=0.5,
        base_img_path=temp_workspace["broll"] / "scene_1.jpg",
    )
    assert frame is not None
    assert frame.shape == (1080, 1920, 3)
    assert frame.dtype == np.uint8


def test_cinetic_render_clip(temp_workspace):
    """Test rendering a short documentary motion clip to MP4."""
    engine = CineticEpisodeMotionEngine(
        broll_dir=temp_workspace["broll"],
        output_dir=temp_workspace["output"],
        sfx_dir=temp_workspace["sfx"],
        fps=15,
    )
    cfg = CineticSceneConfig(
        scene_id=1,
        headline="FIVE MISSILES DETECTED",
        accent_word="MISSILES",
        stamp_text="DECLASSIFIED // SOVIET ARCHIVE",
        telemetry="00:15:23 MSK // 26 SEP 1983",
        duration_sec=1.0,
    )

    out_mp4 = engine.render_scene_motion_clip(
        cfg=cfg,
        mirror_to_broll=True,
    )
    assert out_mp4.is_file()
    assert out_mp4.stat().st_size > 1000

    # Verify mirroring to broll
    broll_target = temp_workspace["broll"] / "scene_1.mp4"
    assert broll_target.is_file()
    assert broll_target.stat().st_size == out_mp4.stat().st_size


def test_cinetic_hyperframes_html(temp_workspace):
    """Test generation of standalone HyperFrames HTML/GSAP companion preview."""
    engine = CineticEpisodeMotionEngine(
        broll_dir=temp_workspace["broll"],
        output_dir=temp_workspace["output"],
        sfx_dir=temp_workspace["sfx"],
    )
    cfg = CineticSceneConfig(
        scene_id=1,
        headline="WORLD ON THE BRINK",
        accent_word="BRINK",
        stamp_text="TOP SECRET // EYES ONLY",
        telemetry="SERPUKHOV-15",
        duration_sec=4.0,
    )

    html_path = engine.generate_hyperframes_html(cfg=cfg)
    assert html_path.is_file()
    content = html_path.read_text(encoding="utf-8")
    assert "gsap" in content.lower()
    assert "#0D0B0A" in content or "#0d0b0a" in content
    assert "#DC2626" in content or "#dc2626" in content
    assert "BRINK" in content
