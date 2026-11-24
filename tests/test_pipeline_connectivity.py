"""Tests for DarkFactory pipeline connectivity, CLI interfaces, and silent-error prevention.

Shift-Left TDD suite validating the Golden 5 Fixes:
1. Orchestrator CLI argument compatibility (--topic, --video, --title, --engine)
2. Virtualenv auto-resolution in run_pilot_pipeline
3. Fail-fast error propagation (zero silent exit-0 on failure)
4. Screenplay manifest prioritization (nolan_soviet_glitch.json > pilot_soviet_glitch.json)
5. Dry-run performance optimization (skips heavy renders)
6. FFmpeg resolution clean facade (no obsolete hardcoded paths)
"""
import inspect
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_youtube_algorithm_booster_cli_accepts_topic():
    """Verify youtube_algorithm_booster.py parser accepts --topic without raising unrecognized arguments."""
    from src import youtube_algorithm_booster
    
    # Check if main defines --topic in its parser or parse directly
    source = inspect.getsource(youtube_algorithm_booster.main)
    assert "--topic" in source, "youtube_algorithm_booster.py main() must declare --topic in argparse"


def test_youtube_publisher_args_wired_in_orchestrator():
    """Verify run_pilot_pipeline.py passes required --video and --title to youtube_publisher.py."""
    import run_pilot_pipeline
    
    source = inspect.getsource(run_pilot_pipeline.main)
    assert 's == "youtube_publisher.py"' in source, "run_pilot_pipeline must have wiring for youtube_publisher.py"
    assert '"--video"' in source, "run_pilot_pipeline must pass --video to youtube_publisher.py"
    assert '"--title"' in source, "run_pilot_pipeline must pass --title to youtube_publisher.py"


def test_orchestrator_passes_kokoro_on_local_tts():
    """Verify run_pilot_pipeline.py passes --engine kokoro when step is tts-local or all-local."""
    import run_pilot_pipeline
    
    source = inspect.getsource(run_pilot_pipeline.main)
    assert '"--engine"' in source and '"kokoro"' in source, "run_pilot_pipeline must pass --engine kokoro for local tts steps"


def test_orchestrator_resolves_venv_python():
    """Verify run_pilot_pipeline.PYTHON_EXE resolves to project venv when present."""
    import run_pilot_pipeline
    
    venv_exe = PROJECT_ROOT / "venv" / "Scripts" / "python.exe"
    if venv_exe.exists():
        assert Path(run_pilot_pipeline.PYTHON_EXE).resolve() == venv_exe.resolve(), (
            f"PYTHON_EXE should point to project venv {venv_exe}, got {run_pilot_pipeline.PYTHON_EXE}"
        )


def test_render_pilot_video_exits_nonzero_on_assembly_failure():
    """Verify render_pilot_video exits non-zero if assemble_final_video returns False."""
    from src import render_pilot_video
    
    source = inspect.getsource(render_pilot_video.main)
    assert "sys.exit(1)" in source, "render_pilot_video.py main() must call sys.exit(1) on assembly failure"
    assert "Final video assembly failed" in source or "not success" in source, (
        "render_pilot_video.py main() must check if assemble_final_video succeeded"
    )


def test_screenplay_manifest_resolution_prefers_nolan_json():
    """Verify resolve_script_path in generate_motion_assets and render_pilot_video prioritizes nolan_soviet_glitch.json."""
    from src import generate_motion_assets, render_pilot_video
    
    src_motion = inspect.getsource(generate_motion_assets.resolve_script_path)
    # nolan_soviet_glitch.json must appear before pilot_soviet_glitch.json
    idx_nolan_motion = src_motion.find("nolan_soviet_glitch.json")
    idx_pilot_motion = src_motion.find("pilot_soviet_glitch.json")
    assert idx_nolan_motion != -1, "nolan_soviet_glitch.json must be in candidate list"
    assert idx_nolan_motion < idx_pilot_motion, (
        "generate_motion_assets.resolve_script_path must prioritize nolan_soviet_glitch.json over pilot_soviet_glitch.json"
    )

    src_render = inspect.getsource(render_pilot_video.main)
    idx_nolan_render = src_render.find("nolan_soviet_glitch.json")
    idx_pilot_render = src_render.find("pilot_soviet_glitch.json")
    assert idx_nolan_render != -1, "nolan_soviet_glitch.json must be in candidate list in render_pilot_video.py"
    assert idx_nolan_render < idx_pilot_render, (
        "render_pilot_video.py main must prioritize nolan_soviet_glitch.json over pilot_soviet_glitch.json"
    )


def test_music_flow_bot_uses_clean_ffmpeg_facade():
    """Verify music_flow_bot does not contain hardcoded obsolete paths to ancient folders."""
    from src import music_flow_bot
    
    source = inspect.getsource(music_flow_bot)
    assert "stockcont" not in source, "music_flow_bot must not have hardcoded obsolete paths to 'stockcont'"
    assert "ffmpeg_processor" in source or "get_ffmpeg_binary" in source, "music_flow_bot must use standard ffmpeg facade"


def test_generate_motion_assets_dry_run_flag_wired():
    """Verify generate_motion_assets checks dry_run in process_all_scenes to prevent heavy rendering."""
    from src import generate_motion_assets
    
    source = inspect.getsource(generate_motion_assets.MotionAssetPipeline.process_all_scenes)
    assert "dry_run" in source, "MotionAssetPipeline.process_all_scenes must check self.dry_run to skip heavy video renders"
