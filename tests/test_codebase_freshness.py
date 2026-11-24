"""DarkFactory Shift-Left TDD: Codebase Freshness & Zero-Zombie Test Suite.

Enforces corporate invariants:
1. Obsolete / orphan files are purged.
2. ADR-09 Zero-Sines Guarantee: No procedural sine wave synthesis (np.sin) in production foley.
3. UniversalTimelineExporter uses canonical track names (A1_Voiceover_EBUR128).
4. All root facades delegate to modern engines and zero orphan scripts exist.
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_obsolete_files_purged():
    """Verify that identified dead/orphan files are completely removed."""
    obsolete_files = [
        PROJECT_ROOT / "src" / "generate_cinetic_teaser_audio.py",
        PROJECT_ROOT / "src" / "video" / "render_cinetic_teaser.py",
    ]
    for dead_file in obsolete_files:
        assert not dead_file.exists(), f"Obsolete file must be purged: {dead_file}"


def test_zero_sine_generation_in_foley_bot():
    """ADR-09: Production foley must delegate to FoleyLibrary and never synthesize crude sines."""
    foley_bot_path = PROJECT_ROOT / "src" / "runninghub_foley_bot.py"
    assert foley_bot_path.is_file()
    content = foley_bot_path.read_text(encoding="utf-8")

    # Invariant: No procedural math sines generating foley
    assert "np.sin(" not in content, "ADR-09 Violation: Procedural sine wave synthesis detected in runninghub_foley_bot.py"
    assert "FoleyLibrary" in content or "foley_library" in content, (
        "runninghub_foley_bot.py must delegate free foley to FoleyLibrary / HybridFoleyEngine"
    )


def test_otio_exporter_voiceover_track_name_consistency():
    """Verify that otio_exporter uses A1_Voiceover_EBUR128 in both native lib and JSON schema."""
    otio_path = PROJECT_ROOT / "src" / "video" / "otio_exporter.py"
    content = otio_path.read_text(encoding="utf-8")

    assert '"A1_Voiceover"' not in content, (
        'Truncated track name "A1_Voiceover" found; must be "A1_Voiceover_EBUR128"'
    )
    assert '"A1_Voiceover_EBUR128"' in content


def test_codebase_freshness_sentinel_audit():
    """Runs the audit_codebase_freshness sentinel functions and asserts zero violations."""
    from scripts.audit_codebase_freshness import (
        audit_facade_bridges,
        audit_orphan_files,
        audit_pipeline_wiring,
    )

    facade_issues = audit_facade_bridges()
    assert not facade_issues, f"Facade delegation issues found: {facade_issues}"

    pipeline_issues = audit_pipeline_wiring()
    assert not pipeline_issues, f"Pipeline wiring issues found: {pipeline_issues}"

    orphan_files = audit_orphan_files()
    assert not orphan_files, f"Orphan files detected in src/: {orphan_files}"
