"""Unit tests for DarkFactory UnifiedMotionOrchestrator and Multi-Archetype Router."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.video.motion_router import (
    CANONICAL_ACT_DISTRIBUTION,
    MotionArchetype,
    UnifiedMotionOrchestrator,
)


@pytest.fixture
def temp_router_dirs():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp)
        out = p / "output"
        broll = p / "broll"
        sfx = p / "sfx"
        out.mkdir(parents=True)
        broll.mkdir(parents=True)
        sfx.mkdir(parents=True)
        yield out, broll, sfx


def test_canonical_5_act_distribution():
    assert len(CANONICAL_ACT_DISTRIBUTION) == 40
    # Act 1 starts with ARGON_RADAR
    assert CANONICAL_ACT_DISTRIBUTION[0] == MotionArchetype.ARGON_RADAR
    # Act 5 contains DOSSIER_INVERSION and SEEDVR_4K
    act5_archetypes = CANONICAL_ACT_DISTRIBUTION[32:]
    assert MotionArchetype.ARGON_DOSSIER_INVERSION in act5_archetypes
    assert MotionArchetype.SEEDVR_4K_ARCHIVAL in act5_archetypes


def test_resolve_archetype_fallback(temp_router_dirs):
    out, broll, sfx = temp_router_dirs
    router = UnifiedMotionOrchestrator(output_dir=out, broll_dir=broll, sfx_dir=sfx)

    scene_1 = {"scene_id": 1}
    assert router.resolve_archetype_for_scene(scene_1) == MotionArchetype.ARGON_RADAR

    scene_9 = {"scene_id": 9}
    assert router.resolve_archetype_for_scene(scene_9) == MotionArchetype.NETFLIX_CORKBOARD

    scene_33 = {"scene_id": 33}
    assert router.resolve_archetype_for_scene(scene_33) == MotionArchetype.ARGON_DOSSIER_INVERSION


def test_resolve_archetype_explicit_override(temp_router_dirs):
    out, broll, sfx = temp_router_dirs
    router = UnifiedMotionOrchestrator(output_dir=out, broll_dir=broll, sfx_dir=sfx)

    scene = {"scene_id": 1, "motion_archetype": "CINETIC_INKSTAGE"}
    assert router.resolve_archetype_for_scene(scene) == MotionArchetype.CINETIC_INKSTAGE


def test_resolve_archetype_style_mapping(temp_router_dirs):
    out, broll, sfx = temp_router_dirs
    router = UnifiedMotionOrchestrator(output_dir=out, broll_dir=broll, sfx_dir=sfx)

    scene_map = {"scene_id": 5, "visual_style_type": "TACTICAL_MAP_MOTION"}
    assert router.resolve_archetype_for_scene(scene_map) == MotionArchetype.TACTICAL_MAP_VECTOR

    scene_cad = {"scene_id": 6, "visual_style_type": "ANATOMY_ISOMETRIC"}
    assert router.resolve_archetype_for_scene(scene_cad) == MotionArchetype.HYPERFRAMES_CAD


def test_render_scene_motion_dry_run(temp_router_dirs):
    out, broll, sfx = temp_router_dirs
    router = UnifiedMotionOrchestrator(output_dir=out, broll_dir=broll, sfx_dir=sfx, dry_run=True)

    scene = {
        "scene_id": 1,
        "title": "SERPUKHOV-15 ALARM",
        "narration_pt": "O sistema de alerta antecipado soviético detecta o lançamento.",
        "estimated_duration_sec": 4.0,
    }
    # Should resolve without raising exceptions
    arch = router.resolve_archetype_for_scene(scene)
    assert arch == MotionArchetype.ARGON_RADAR
