#!/usr/bin/env python3
"""DarkFactory Pilot Production Orchestrator.

One-click command center to produce the pilot documentary:
  - Step 0: Pre-Flight Auth & Session Gate (Google Flow & RunningHub session verification)
  - Step 1: Direct (Nolan Dark History Director Screenplay Synthesis)
  - Step 2: Research Engine (Wikipedia Ground-Truth Extraction)
  - Step 3: Google Flow Stealth Bot & Real AI Video Generation (Veo 3.1 & Omni Flash + MiniMax H3 fallback)
  - Step 4: TTS / Audio Ingestion (CosyVoice 3 Instruct 2, Kokoro-82M, or Edge-TTS)
  - Step 5: Broadcast Studio Mastering & SRT Synchronization
  - Step 6: 4-Stem Master Audio Mixer & Dynamic Sidechain Ducking
  - Step 7: Video B-Roll Rendering & Final 1080p Master Assembly
  - Step 8: Shorts Generator (YouTube Shorts 9:16 cuts)
  - Step 9: YouTube Compliance QC
  - Step 10: YouTube Algorithm Booster
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

# Force UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"

# Auto-resolve virtual environment Python if available
_venv_python = PROJECT_ROOT / "venv" / "Scripts" / "python.exe"
if _venv_python.exists():
    PYTHON_EXE = str(_venv_python)
else:
    PYTHON_EXE = sys.executable

DRY_RUN_SUPPORTED = {
    "auth_gate.py",
    "google_flow_bot.py",
    "generate_motion_assets.py",
    "generate_pilot_audio.py",
    "render_pilot_video.py",
    "youtube_publisher.py",
}


def run_script(script_name: str, dry_run: bool = False, extra_args: list | None = None) -> bool:
    target = SRC_DIR / script_name
    print("\n=======================================================")
    print(f"🎬 EXECUTING: {script_name}")
    print("=======================================================")
    cmd = [PYTHON_EXE, "-u", str(target)]
    if dry_run and script_name in DRY_RUN_SUPPORTED:
        cmd.append("--dry-run")
    if extra_args:
        cmd.extend(extra_args)
    res = subprocess.run(cmd)
    return res.returncode == 0


def clean_pipeline_cache(max_age_days: int = 7) -> None:
    """Purges quarantine directories older than max_age_days and cleans browser cache."""
    import shutil
    import time

    quarantine_dir = PROJECT_ROOT / "data" / "quarantine"
    now = time.time()
    cutoff = now - (max_age_days * 86400)
    purged_count = 0

    if quarantine_dir.exists():
        for item in quarantine_dir.iterdir():
            try:
                mtime = item.stat().st_mtime
                if mtime < cutoff:
                    if item.is_dir():
                        shutil.rmtree(item, ignore_errors=True)
                    else:
                        item.unlink(missing_ok=True)
                    purged_count += 1
            except Exception as e:
                print(f"Warning purging {item.name}: {e}")
    print(f"🧹 Cleaned {purged_count} expired quarantine items (> {max_age_days} days old).")

    # Clean chrome_session Cache directories
    chrome_sessions = PROJECT_ROOT / "chrome_session"
    cache_cleaned = 0
    if chrome_sessions.exists():
        for cache_path in chrome_sessions.glob("**/Cache*"):
            try:
                if cache_path.is_dir():
                    shutil.rmtree(cache_path, ignore_errors=True)
                    cache_cleaned += 1
            except Exception:
                pass
    print(f"🧹 Cleaned {cache_cleaned} browser cache directories.")


def main() -> None:
    parser = argparse.ArgumentParser(description="DarkFactory Pilot Production Orchestrator")
    parser.add_argument(
        "--step",
        choices=["auth", "direct", "research", "flow", "tts", "tts-local", "master", "sound", "motion", "video", "shorts", "qc", "boost", "publish", "all", "all-local"],
        default=None,
        help="Step to execute"
    )
    parser.add_argument(
        "--phase",
        choices=["auth", "research", "script", "visual", "audio", "video", "render", "assembly", "all"],
        default=None,
        help="Cinematic phase to execute (alias mapping to pipeline steps)"
    )
    parser.add_argument(
        "--topic",
        type=str,
        default=None,
        help="Historical topic or declassified incident title for generation",
    )
    parser.add_argument(
        "--teaser",
        action="store_true",
        help="Execute teaser slice (Scenes 1 to 3) with Google Flow + Overlays + Master",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in dry-run mode for API / browser services",
    )
    parser.add_argument(
        "--allow-procedural-fallback",
        action="store_true",
        help="Allow procedural cinematic plates when generative API is unavailable",
    )
    parser.add_argument(
        "--clean-cache",
        action="store_true",
        help="Purge quarantine artifacts older than 7 days and clear browser cache",
    )
    args = parser.parse_args()

    if args.clean_cache:
        clean_pipeline_cache()
        if not args.step and not args.phase:
            sys.exit(0)

    print("\n" + "=" * 65)
    print("🏛️ DARKFACTORY CANONICAL PRODUCTION STANDARDS (v2.0)")
    print("=" * 65)
    print("  [1] Auth Gate: Google Flow + RunningHub + Flow Music (Sessões Obrigatórias)")
    print("  [2] Video Dual-Shot: Google Flow Veo 3.1 & Omni Flash (Fallback: MiniMax H3)")
    print("  [3] Narração Estelar: CosyVoice 3 (Fallback: Kokoro-82M com Narrator Lock)")
    print("  [4] Trilha Sonora: Flow Music Hans Zimmer/Lyria (Fallback: MiniMax Music 3)")
    print("  [5] Sound Design: Biblioteca Curada CC0 Gratuita (Whooshes, Selos, Teletipos)")
    print("  [6] GPU Economy: Cancelamento Instantâneo RunningHub Pós-Download")
    print("=" * 65)
    if args.topic:
        print(f"🎯 EPISODE TOPIC: {args.topic}")
    print("=" * 65 + "\n")

    steps = []
    # If phase is specified, map to corresponding steps
    if args.phase:
        if args.phase == "auth":
            steps = ["auth_gate.py"]
        elif args.phase == "research":
            steps = ["auth_gate.py", "research_engine.py"]
        elif args.phase == "script":
            steps = ["auth_gate.py", "research_engine.py", "nolan_director.py"]
        elif args.phase == "visual":
            steps = ["auth_gate.py", "google_flow_bot.py", "generate_motion_assets.py"]
        elif args.phase == "audio":
            steps = ["auth_gate.py", "generate_pilot_audio.py", "cosyvoice_master.py", "audio_mixer_master.py"]
        elif args.phase == "video":
            steps = ["auth_gate.py", "google_flow_bot.py", "generate_motion_assets.py", "render_pilot_video.py"]
        elif args.phase in ("render", "assembly"):
            steps = ["render_pilot_video.py", "shorts_generator.py", "youtube_compliance_qc.py", "youtube_algorithm_booster.py"]
        elif args.phase in ("boost", "seo"):
            steps = ["youtube_algorithm_booster.py"]
        elif args.phase == "all":
            steps = [
                "auth_gate.py",
                "research_engine.py",
                "nolan_director.py",
                "google_flow_bot.py",
                "generate_motion_assets.py",
                "generate_pilot_audio.py",
                "cosyvoice_master.py",
                "audio_mixer_master.py",
                "render_pilot_video.py",
                "shorts_generator.py",
                "youtube_compliance_qc.py",
                "youtube_algorithm_booster.py",
            ]
    else:
        # Default step is "all" if neither step nor phase provided
        step_val = args.step or "all"
        if step_val == "auth":
            steps = ["auth_gate.py"]
        elif step_val == "research":
            steps = ["research_engine.py"]
        elif step_val == "direct":
            steps = ["nolan_director.py"]
        elif step_val == "flow":
            steps = ["google_flow_bot.py"]
        elif step_val == "motion":
            steps = ["generate_motion_assets.py"]
        elif step_val == "tts" or step_val == "tts-local":
            steps = ["generate_pilot_audio.py"]
        elif step_val == "master":
            steps = ["cosyvoice_master.py"]
        elif step_val == "sound":
            steps = ["audio_mixer_master.py"]
        elif step_val == "video":
            steps = ["google_flow_bot.py", "generate_motion_assets.py", "render_pilot_video.py"]
        elif step_val == "shorts":
            steps = ["shorts_generator.py"]
        elif step_val == "qc":
            steps = ["youtube_compliance_qc.py"]
        elif step_val == "boost":
            steps = ["youtube_algorithm_booster.py"]
        elif step_val == "publish":
            steps = ["youtube_publisher.py"]
        elif step_val in ("all", "all-local"):
            steps = [
                "auth_gate.py",
                "research_engine.py",
                "nolan_director.py",
                "google_flow_bot.py",
                "generate_motion_assets.py",
                "generate_pilot_audio.py",
                "cosyvoice_master.py",
                "audio_mixer_master.py",
                "render_pilot_video.py",
                "shorts_generator.py",
                "youtube_compliance_qc.py",
                "youtube_algorithm_booster.py",
            ]

    for s in steps:
        extra = []
        if args.topic and s in ("nolan_director.py", "research_engine.py", "youtube_algorithm_booster.py"):
            extra.extend(["--topic", args.topic])
        if s == "nolan_director.py":
            # Auto-wire pre-researched Step 1 dossier if present
            dossier_candidates = [
                PROJECT_ROOT / "data" / "scripts" / "research_soviet_glitch.json",
                PROJECT_ROOT / "data" / "processed" / "research_dossiers" / "stanislav_petrov.json",
            ]
            for dc in dossier_candidates:
                if dc.exists():
                    extra.extend(["--research-dossier", str(dc)])
                    break
        if s == "generate_pilot_audio.py" and (args.step in ("tts-local", "all-local")):
            extra.extend(["--engine", "kokoro"])
        if s == "youtube_publisher.py":
            video_file = PROJECT_ROOT / "data" / "output" / "the_1983_soviet_glitch_final_1080p.mp4"
            pub_title = args.topic or "The 1983 Glitch: 20 Minutes to Armageddon"
            extra.extend([
                "--video", str(video_file),
                "--title", pub_title,
            ])
        if s == "youtube_compliance_qc.py":
            video_file = PROJECT_ROOT / "data" / "output" / "the_1983_soviet_glitch_final_1080p.mp4"
            extra.extend([
                "--title", "The 1983 Glitch: 20 Minutes to Armageddon",
                "--video", str(video_file),
            ])
        if args.teaser:
            if s == "nolan_director.py":
                extra.extend([
                    "--mode", "teaser",
                    "--output", str(PROJECT_ROOT / "data" / "scripts" / "nolan_soviet_glitch_teaser.json"),
                ])
            elif s in ("google_flow_bot.py", "generate_motion_assets.py", "generate_pilot_audio.py", "render_pilot_video.py"):
                extra.append("--teaser")
        if args.allow_procedural_fallback:
            if s in ("google_flow_bot.py", "render_pilot_video.py"):
                extra.append("--allow-procedural-fallback")
        success = run_script(s, dry_run=args.dry_run, extra_args=extra)
        if not success:
            print(f"\n❌ Pipeline failed at step: {s}", file=sys.stderr)
            sys.exit(1)

        # ADR-HardGate: Verify 27-Book Story Audit score after nolan_director step
        if s == "nolan_director.py":
            manifest_file = PROJECT_ROOT / "data" / "scripts" / ("nolan_soviet_glitch_teaser.json" if args.teaser else "nolan_soviet_glitch.json")
            if manifest_file.exists():
                try:
                    with open(manifest_file, "r", encoding="utf-8") as mf:
                        m_data = json.load(mf)
                    audit = m_data.get("story_audit", {})
                    score = audit.get("overall_retention_score", 0)
                    is_ready = audit.get("is_production_ready", False)
                    print(f"\n📖 [HARD GATE] Story Audit: Score={score}/100, Grade={audit.get('grade')}, Ready={is_ready}")
                    if score < 70:
                        print("❌ Pipeline aborted: Story retention score below 70 threshold.", file=sys.stderr)
                        sys.exit(1)
                except Exception as ex:
                    print(f"⚠️ Warning reading story audit: {ex}")

    print("\n🎉 ALL STEPS COMPLETED SUCCESSFULLY!")
    print(f"Output video ready at: {PROJECT_ROOT / 'data' / 'output' / 'the_1983_soviet_glitch_final_1080p.mp4'}")


if __name__ == "__main__":
    main()
