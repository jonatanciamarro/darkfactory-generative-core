"""TDD Suite: DarkFactory YouTube & Cinematic Sound Effects Library Ingestion & Automation."""

from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pytest
from fastapi.testclient import TestClient

from src.dashboard.app import app
from src.video.foley_library import FoleyCue, FoleyLibrary


def test_sfx_item_and_catalog_models():
    """Verify SFXItem and SFXCatalog Pydantic v2 models."""
    from src.video.sfx_manager import SFXItem, SFXCatalog

    item = SFXItem(
        id="whoosh_fast_01",
        name="Whoosh Fast 01",
        category="transition",
        subcategory="whoosh",
        relative_path="youtube_fasteditor/whoosh_01.wav",
        format="wav",
        tags=["whoosh", "transition", "fast", "swoosh"],
        origin_pack="1000+UR.FASTEDITOR SFX",
        duration_sec=0.75,
    )
    assert item.id == "whoosh_fast_01"
    assert item.format == "wav"
    assert "transition" in item.tags

    catalog = SFXCatalog(
        total_count=1,
        categories={"transition": 1},
        items=[item],
    )
    assert catalog.total_count == 1
    assert catalog.categories["transition"] == 1
    catalog_dict = catalog.model_dump()
    assert "items" in catalog_dict
    assert len(catalog_dict["items"]) == 1


def test_sfx_manager_indexing_and_search(tmp_path):
    """Verify SFXManager indexing of audio files and semantic tag searching."""
    from src.video.sfx_manager import SFXManager

    sfx_dir = tmp_path / "sfx"
    cat_dir = sfx_dir / "cinematic" / "sub_drops"
    cat_dir.mkdir(parents=True, exist_ok=True)

    dummy_wav = cat_dir / "sub_drop_heavy.wav"
    # Create simple valid 16-bit PCM WAV
    import wave
    with wave.open(str(dummy_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        wf.writeframes(b"\x00\x00" * 4410)  # 0.1s

    manager = SFXManager(sfx_dir=sfx_dir)
    manifest = manager.scan_and_build_manifest()

    assert manifest.total_count == 1
    assert "cinematic" in manifest.categories

    # Search by tag
    results = manager.search(query="sub_drop")
    assert len(results) >= 1
    assert results[0].subcategory == "sub_drops"

    # Search by category
    cinematic_results = manager.search(category="cinematic")
    assert len(cinematic_results) == 1


def test_foley_library_seamless_integration_with_sfx_manager(tmp_path):
    """Verify FoleyLibrary uses SFXManager for auto-matching cues to real library audio."""
    from src.video.sfx_manager import SFXManager

    sfx_dir = tmp_path / "sfx"
    trans_dir = sfx_dir / "transitions"
    trans_dir.mkdir(parents=True, exist_ok=True)
    wav_file = trans_dir / "cinematic_whoosh_01.wav"

    import wave
    # 0.2s of 440Hz tone
    t = np.linspace(0, 0.2, int(44100 * 0.2), endpoint=False, dtype=np.float32)
    tone = (np.sin(2 * np.pi * 440 * t) * 16000).astype(np.int16)
    with wave.open(str(wav_file), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        wf.writeframes(tone.tobytes())

    manager = SFXManager(sfx_dir=sfx_dir)
    manager.scan_and_build_manifest()

    lib = FoleyLibrary(custom_sfx_dir=sfx_dir)
    cat = lib.list_catalog()
    assert "cinematic_whoosh_01" in cat

    # Test synthesizing/loading real audio
    pcm = lib.synthesize_sfx("cinematic_whoosh_01", sample_rate=44100)
    assert len(pcm) > 0
    assert isinstance(pcm, np.ndarray)


def test_foley_automatic_semantic_triggers():
    """Verify build_cues_from_triggers maps expanded vocabulary to real SFX categories."""
    triggers = [
        {"keyword": "Soviet radar anomaly detected", "timestamp_sec": 1.5},
        {"keyword": "Confidential paper dossier opened", "timestamp_sec": 4.0},
        {"keyword": "Screen glitch tape interference", "timestamp_sec": 7.2},
        {"keyword": "Sub drop massive bass boom", "timestamp_sec": 10.0},
        {"keyword": "Camera shutter snapshot", "timestamp_sec": 12.5},
        {"keyword": "Dramatic brass horn swell", "timestamp_sec": 15.0},
        {"keyword": "Fast whoosh transition to next scene", "timestamp_sec": 18.0},
    ]

    cues = FoleyLibrary.build_cues_from_triggers(triggers)
    assert len(cues) == 7

    cue_names = [c.sfx_name for c in cues]
    assert "radar_ping" in cue_names
    assert any("paper" in name or "stamp" in name for name in cue_names)
    assert any("glitch" in name for name in cue_names)
    assert any("sub" in name or "riser" in name for name in cue_names)
    assert any("camera" in name for name in cue_names)
    assert any("horn" in name or "sub_riser" in name for name in cue_names)
    assert any("whoosh" in name for name in cue_names)


def test_dashboard_sfx_api_endpoints():
    """Verify FastAPI routes for SFX catalog exploration."""
    client = TestClient(app)

    resp_cat = client.get("/api/sfx/catalog")
    assert resp_cat.status_code == 200
    data_cat = resp_cat.json()
    assert "total_count" in data_cat
    assert "categories" in data_cat

    resp_search = client.get("/api/sfx/search?q=whoosh")
    assert resp_search.status_code == 200
    data_search = resp_search.json()
    assert "results" in data_search


def test_foley_library_builds_stem_with_live_catalog(tmp_path):
    """Verify FoleyLibrary generates a synchronized multi-cue audio stem with the live SFX library."""
    lib = FoleyLibrary()
    catalog = lib.list_catalog()
    assert len(catalog) > 10

    cues = [
        FoleyCue(sfx_name="whoosh_subtle", timestamp_sec=0.2, gain_db=-12.0),
        FoleyCue(sfx_name="glitch_transition", timestamp_sec=1.0, gain_db=-10.0),
        FoleyCue(sfx_name="sub_drop", timestamp_sec=1.8, gain_db=-8.0),
    ]

    out_wav = tmp_path / "live_foley_stem.wav"
    res = lib.build_foley_stem(cues=cues, total_duration_sec=3.0, output_wav_path=out_wav)
    assert res.success is True
    assert out_wav.is_file()
    assert res.cues_applied == 3
