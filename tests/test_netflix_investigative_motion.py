"""Test suite for DarkFactory Netflix-Grade Investigative Motion Engine.

Validates the 3 Canonic Documentary Motion Archetypes:
1. CORKBOARD_CONSPIRACY (Ref Image 1: Detective cork board, polaroids, red strings with shadows, desk lamp glow)
2. TACTILE_CLASSIFIED_DOSSIER (Ref Images 2 & 3: Manila folder, brass clip, distressed rubber stamp, volumetric god rays)
3. NETFLIX_OSINT_DESKTOP (Ref Image 4: Multi-window cyber-investigation desktop, satellite route tracking, CRT scanlines)
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

from src.video.netflix_investigative_motion import (
    MotionArchetype,
    PinnedEvidenceItem,
    RedStringConnection,
    DossierConfig,
    OSINTWindow,
    NetflixInvestigativeSceneDTO,
    NetflixInvestigativeMotionEngine,
)


@pytest.fixture
def mock_workspace():
    """Create isolated test workspace with assets and directories."""
    tmp = Path(tempfile.mkdtemp(prefix="df_netflix_motion_test_"))
    broll_dir = tmp / "data" / "broll"
    output_dir = tmp / "data" / "final" / "motion_overlays"
    sfx_dir = tmp / "data" / "sfx"

    broll_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    sfx_dir.mkdir(parents=True, exist_ok=True)

    # Staged archival photo
    test_photo = np.full((1080, 1920, 3), 50, dtype=np.uint8)
    cv2.putText(test_photo, "HISTORICAL EVIDENCE TEST", (300, 540), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (220, 220, 220), 3)
    cv2.imwrite(str(broll_dir / "scene_1.jpg"), test_photo)

    # Minimal mock sfx manifest
    manifest_data = {
        "whooshes": ["data/sfx/whoosh1.wav"],
        "stamp_slam": ["data/sfx/slam1.wav"],
        "radar_ping": ["data/sfx/radar1.wav"],
        "paper": ["data/sfx/paper1.wav"],
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


def test_dto_contracts_and_validation():
    """Test Pydantic v2 schemas for all 3 archetypes."""
    dto = NetflixInvestigativeSceneDTO(
        scene_id=1,
        archetype=MotionArchetype.CORKBOARD_CONSPIRACY,
        duration_sec=5.0,
        output_mp4_path="data/output/test.mp4",
        corkboard_items=[
            PinnedEvidenceItem(
                item_id="photo_1",
                title="STANISLAV PETROV",
                item_type="photo",
                position_xy=(500, 400),
                rotation_deg=-3.0,
            ),
            PinnedEvidenceItem(
                item_id="target_radar",
                title="RADAR OKO",
                item_type="map",
                position_xy=(1000, 400),
                rotation_deg=2.5,
            ),
        ],
        red_strings=[
            RedStringConnection(
                from_item_id="photo_1",
                to_item_id="target_radar",
                sag_factor=0.2,
            )
        ],
    )
    assert dto.archetype == MotionArchetype.CORKBOARD_CONSPIRACY
    assert len(dto.corkboard_items) == 2
    assert len(dto.red_strings) == 1
    assert dto.resolution == (1920, 1080)


def test_render_corkboard_frame(mock_workspace):
    """Test synthesis of Archetype 1: Corkboard with red strings, pins, and desk lamp."""
    engine = NetflixInvestigativeMotionEngine(
        broll_dir=mock_workspace["broll"],
        output_dir=mock_workspace["output"],
        sfx_dir=mock_workspace["sfx"],
    )
    dto = NetflixInvestigativeSceneDTO(
        scene_id=1,
        archetype=MotionArchetype.CORKBOARD_CONSPIRACY,
        output_mp4_path=str(mock_workspace["output"] / "corkboard.mp4"),
        corkboard_items=[
            PinnedEvidenceItem(
                item_id="suspect_1",
                title="STANISLAV PETROV",
                item_type="photo",
                image_path=str(mock_workspace["broll"] / "scene_1.jpg"),
                position_xy=(600, 500),
            ),
            PinnedEvidenceItem(
                item_id="note_1",
                title="CHECK PROTOCOL",
                item_type="note",
                note_text="ALIBI WEAK // 5 MISSILES",
                position_xy=(1200, 450),
            ),
        ],
        red_strings=[
            RedStringConnection(from_item_id="suspect_1", to_item_id="note_1")
        ],
    )

    frame = engine.render_frame_for_scene(dto, progress=0.5)
    assert frame is not None
    assert frame.shape == (1080, 1920, 3)
    assert frame.dtype == np.uint8
    # Ensure not purely black
    assert np.mean(frame) > 15


def test_render_tactile_dossier_frame(mock_workspace):
    """Test synthesis of Archetype 2: Aged manila folder with god rays and distressed stamp."""
    engine = NetflixInvestigativeMotionEngine(
        broll_dir=mock_workspace["broll"],
        output_dir=mock_workspace["output"],
        sfx_dir=mock_workspace["sfx"],
    )
    dto = NetflixInvestigativeSceneDTO(
        scene_id=1,
        archetype=MotionArchetype.TACTILE_CLASSIFIED_DOSSIER,
        output_mp4_path=str(mock_workspace["output"] / "dossier.mp4"),
        dossier_config=DossierConfig(
            case_number="CASE FILE NO. 1983-B",
            subject_title="SERPUKHOV-15 COMMAND",
            stamp_headline="INCIDENTE 17-B",
            stamp_subtitle="ARCHIVO INCOMPLETO",
            pinned_photo_path=str(mock_workspace["broll"] / "scene_1.jpg"),
            has_volumetric_light=True,
        ),
    )

    frame = engine.render_frame_for_scene(dto, progress=0.3)
    assert frame is not None
    assert frame.shape == (1080, 1920, 3)
    # Validate color warmth and non-black content
    assert np.mean(frame[:, :, 2]) > 30  # Red/warm tones prominent


def test_render_netflix_osint_desktop_frame(mock_workspace):
    """Test synthesis of Archetype 3: Floating OSINT windows, traffic lights, and CRT scanlines."""
    engine = NetflixInvestigativeMotionEngine(
        broll_dir=mock_workspace["broll"],
        output_dir=mock_workspace["output"],
        sfx_dir=mock_workspace["sfx"],
    )
    dto = NetflixInvestigativeSceneDTO(
        scene_id=1,
        archetype=MotionArchetype.NETFLIX_OSINT_DESKTOP,
        output_mp4_path=str(mock_workspace["output"] / "osint.mp4"),
        osint_windows=[
            OSINTWindow(
                window_id="w_map",
                title="SATELLITE TELEMETRY // MOSCOW ORBIT",
                window_type="map_route",
                rect=(120, 100, 750, 520),
                content_data={"route": "Oko Sat -> Serpukhov-15"},
            ),
            OSINTWindow(
                window_id="w_evidence",
                title="EVIDENCE // CRT RADAR SCAN",
                window_type="split_evidence",
                rect=(900, 220, 900, 680),
                content_data={"image_path": str(mock_workspace["broll"] / "scene_1.jpg")},
            ),
        ],
    )

    frame = engine.render_frame_for_scene(dto, progress=0.7)
    assert frame is not None
    assert frame.shape == (1080, 1920, 3)
    assert np.mean(frame) > 10


def test_render_full_clip_and_mirror(mock_workspace):
    """Test full MP4 video clip rendering (1080p @ 15fps test) and automatic broll mirroring."""
    engine = NetflixInvestigativeMotionEngine(
        broll_dir=mock_workspace["broll"],
        output_dir=mock_workspace["output"],
        sfx_dir=mock_workspace["sfx"],
        fps=15,
    )
    dto = NetflixInvestigativeSceneDTO(
        scene_id=1,
        archetype=MotionArchetype.TACTILE_CLASSIFIED_DOSSIER,
        duration_sec=1.0,
        output_mp4_path=str(mock_workspace["output"] / "test_clip.mp4"),
        dossier_config=DossierConfig(
            case_number="CASE NO. 1983",
            stamp_headline="CONFIDENCIAL",
            pinned_photo_path=str(mock_workspace["broll"] / "scene_1.jpg"),
        ),
        mirror_to_broll=True,
    )

    out_file = engine.render_scene_clip(dto)
    assert out_file.is_file()
    assert out_file.stat().st_size > 1000

    # Ensure mirrored to broll
    broll_copy = mock_workspace["broll"] / "scene_1.mp4"
    assert broll_copy.is_file()
    assert broll_copy.stat().st_size == out_file.stat().st_size
