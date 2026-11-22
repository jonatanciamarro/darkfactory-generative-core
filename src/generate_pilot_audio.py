#!/usr/bin/env python3
"""DarkFactory Pilot Audio Engine.

Generates broadcast-mastered neural narration for the pilot documentary using:
1. Kokoro-82M ONNX (Local Zero-Cost Neural Engine) — Default: bm_george (BBC / Nolan style)
2. Dynamic voice selection (--voice bm_george / bm_lewis / am_adam)
3. Broadcast EQ & Compression filter chain (Ableton Live Complex Pro curve, -14 LUFS)
4. Synchronized SRT Subtitles
5. Edge-TTS RyanNeural (en-GB) fallback proxy
"""
import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

# Force UTF-8 on Windows stdout/stderr (ADR-01)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SCRIPTS_DIR = PROJECT_ROOT / "data" / "scripts"
AUDIO_DIR = PROJECT_ROOT / "data" / "audio"
SUBS_DIR = PROJECT_ROOT / "data" / "subtitles"
MODEL_DIR = PROJECT_ROOT / "data" / "models" / "kokoro"

# Fallback path to local models if not inside PROJECT_ROOT/data/models
if not (MODEL_DIR / "kokoro-v0_19.onnx").exists():
    ALT_MODEL_DIR = PROJECT_ROOT.parent / "data" / "models" / "kokoro"
    if (ALT_MODEL_DIR / "kokoro-v0_19.onnx").exists():
        MODEL_DIR = ALT_MODEL_DIR

SCRIPT_FILE = SCRIPTS_DIR / "pilot_soviet_glitch.json"
DEFAULT_VOICE = "bm_george"
DEFAULT_SPEED = 0.98


def get_ffmpeg_bin() -> str:
    """Finds ffmpeg executable."""
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        try:
            import imageio_ffmpeg
            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            pass
        candidates = [
            PROJECT_ROOT / "venv" / "Lib" / "site-packages" / "imageio_ffmpeg" / "binaries" / "ffmpeg-win-x86_64-v9.0.2.exe",
            Path(r"C:\ffmpeg\bin\ffmpeg.exe"),
            Path(r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"),
        ]
        for c in candidates:
            if c.is_file():
                return str(c)
    return ffmpeg_bin or "ffmpeg"


def get_audio_duration_probe(file_path: Path) -> float:
    """Probe audio duration in seconds via FFmpeg."""
    cmd = [get_ffmpeg_bin(), "-i", str(file_path), "-f", "null", "-"]
    res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        logger.warning(f"FFmpeg audio duration probe failed on {file_path}: {res.stderr}")
        return 0.0
    for line in res.stderr.splitlines():
        if "Duration:" in line:
            try:
                part = line.split("Duration:")[1].split(",")[0].strip()
                h, m, s = part.split(":")
                return float(h) * 3600 + float(m) * 60 + float(s)
            except Exception:
                break
    return 0.0


def format_srt_time(seconds: float) -> str:
    """Format seconds into SRT timestamp: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_srt(scenes: List[dict], durations: List[float], output_srt: Path) -> str:
    """Generates broadcast documentary SRT subtitles aligned to scene timings."""
    srt_entries = []
    current_time = 0.0
    counter = 1

    for scene, dur in zip(scenes, durations):
        text = scene["audio_text"]
        clauses = []
        for sentence in text.replace("...", ".").split(". "):
            sentence = sentence.strip()
            if not sentence:
                continue
            if not sentence.endswith("."):
                sentence += "."
            if len(sentence) > 60 and ", " in sentence:
                parts = sentence.split(", ", 1)
                clauses.append(parts[0].strip() + ",")
                clauses.append(parts[1].strip())
            else:
                clauses.append(sentence)

        total_chars = sum(len(c) for c in clauses)
        scene_start = current_time

        for clause in clauses:
            portion = len(clause) / max(total_chars, 1)
            clause_dur = dur * portion
            start_str = format_srt_time(current_time)
            end_str = format_srt_time(current_time + clause_dur - 0.08)

            srt_entries.append(f"{counter}\n{start_str} --> {end_str}\n{clause}\n")
            current_time += clause_dur
            counter += 1

        current_time = scene_start + dur

    full_srt = "\n".join(srt_entries)
    with open(output_srt, "w", encoding="utf-8") as f:
        f.write(full_srt)
    return full_srt


def master_audio(input_wav: Path, output_file: Path) -> None:
    """Applies documentary broadcast mastering (Ableton Live Complex Pro curve, -14 LUFS)."""
    filter_chain = (
        "highpass=f=60,"
        "equalizer=f=90:width_type=q:w=1.0:g=2.5,"
        "equalizer=f=350:width_type=q:w=1.5:g=-1.5,"
        "highshelf=f=3500:width_type=q:w=1.0:g=2.0,"
        "acompressor=threshold=-18dB:ratio=3:attack=15:release=120:makeup=2dB,"
        "loudnorm=I=-14:TP=-1.0:LRA=7"
    )

    cmd = [
        get_ffmpeg_bin(),
        "-y",
        "-i", str(input_wav),
        "-af", filter_chain,
    ]
    if output_file.suffix.lower() == ".mp3":
        cmd.extend(["-c:a", "libmp3lame", "-b:a", "320k", "-ar", "44100"])
    else:
        cmd.extend(["-c:a", "pcm_s24le", "-ar", "48000"])
    cmd.append(str(output_file))

    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg mastering error: {res.stderr}")


async def generate_scene_edge_fallback(text: str, output_mp3: Path, voice: str = "en-GB-RyanNeural") -> bytes:
    """Fallback to Edge-TTS if Kokoro is unavailable."""
    import edge_tts
    comm = edge_tts.Communicate(text, voice, rate="-2%", pitch="-1Hz")
    audio_data = bytearray()
    async for chunk in comm.stream():
        if chunk["type"] == "audio":
            audio_data.extend(chunk["data"])
    with open(output_mp3, "wb") as f:
        f.write(audio_data)
    return bytes(audio_data)


def run_pipeline(
    voice: str = DEFAULT_VOICE,
    speed: float = DEFAULT_SPEED,
    dry_run: bool = False,
    teaser: bool = False,
    preferred_engine: str = "cosyvoice",
) -> dict:
    """Executes full pilot audio synthesis, broadcast mastering, and SRT generation."""
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    SUBS_DIR.mkdir(parents=True, exist_ok=True)

    target_file = SCRIPT_FILE
    if teaser:
        teaser_file = SCRIPTS_DIR / "nolan_soviet_glitch_teaser.json"
        if teaser_file.exists():
            target_file = teaser_file
    if not target_file.exists():
        target_file = SCRIPTS_DIR / "nolan_soviet_glitch.json"
    if not target_file.exists():
        candidates = list(SCRIPTS_DIR.glob("*soviet_glitch*.json"))
        if candidates:
            target_file = candidates[0]
    if not target_file.exists():
        print(f"Error: Script file not found: {SCRIPT_FILE}", file=sys.stderr)
        sys.exit(1)

    with open(target_file, "r", encoding="utf-8") as f:
        script_data = json.load(f)

    project_id = script_data.get("project_id", "pilot_soviet_glitch")

    # Enforce MasterVoiceRouter and Single-Narrator Lock
    router = None
    target_engine = None
    try:
        from src.video.voice_router import (
            MasterVoiceRouter,
            ENGINE_COSYVOICE,
            ENGINE_KOKORO_LOCAL,
            NarratorConsistencyViolationError,
        )
        router = MasterVoiceRouter(locks_persistence_path=AUDIO_DIR / "narrator_locks.json", output_dir=AUDIO_DIR)
        existing_lock = router.get_lock(project_id)
        if existing_lock:
            target_engine = existing_lock.engine
            voice = existing_lock.voice_id
            print(f"🔒 Enforcing existing narrator lock for '{project_id}': {target_engine} ({voice})")
        else:
            if preferred_engine == "kokoro":
                target_engine = ENGINE_KOKORO_LOCAL
            elif preferred_engine == "cosyvoice":
                target_engine = ENGINE_COSYVOICE
                voice = "cosyvoice_instruct"
    except Exception as e:
        print(f"Voice router lock warning: {e}")

    scenes = script_data.get("scenes", [])
    if teaser:
        scenes = scenes[:3]
    print(f"Loaded script: {script_data.get('title')} ({len(scenes)} scenes)")
    print(f"Voice: {voice} (Speed: {speed}x) | Target Engine: {target_engine or 'CosyVoice (RunningHub) -> Kokoro-82M ONNX Fallback'}")

    # Check Kokoro ONNX model
    onnx_path = MODEL_DIR / "kokoro-v0_19.onnx"
    voices_path = MODEL_DIR / "voices.bin"
    kokoro = None

    if onnx_path.is_file() and voices_path.is_file():
        try:
            from kokoro_onnx import Kokoro
            kokoro = Kokoro(str(onnx_path), str(voices_path))
            print("✅ Initialized Kokoro-82M ONNX local neural runtime.")
        except Exception as e:
            print(f"⚠️ Kokoro ONNX init warning: {e}. Falling back to Edge-TTS proxy.")

    raw_dir = AUDIO_DIR / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    full_text_parts = []
    durations = []
    scene_mastered_files = []

    active_engine = target_engine

    # Synthesize individual scenes
    for scene in scenes:
        s_id = scene["scene_id"]
        text = scene["audio_text"]
        emotion = scene.get("cosyvoice_instruct", "Speak with controlled urgency, deep baritone documentary tone.")
        full_text_parts.append(text)

        scene_raw = raw_dir / f"scene_{s_id}_raw.wav"
        scene_mastered = AUDIO_DIR / f"scene_{s_id}.wav"
        scene_mp3 = AUDIO_DIR / f"scene_{s_id}.mp3"

        engine_used = None
        voice_used = voice

        if dry_run:
            print(f"  -> [Dry-Run] Simulating Scene {s_id} with voice '{voice}'...")
            if scene_mp3.exists() and scene_mp3.stat().st_size > 1000:
                dur = get_audio_duration_probe(scene_mp3)
            else:
                dur = float(scene.get("estimated_duration_sec", 12.0))
                subprocess.run(
                    [get_ffmpeg_bin(), "-y", "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=mono", "-t", str(dur), str(scene_mp3)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            durations.append(dur)
            scene_mastered_files.append(scene_mp3)
            print(f"     [OK-DryRun] Scene {s_id}: {dur:.2f}s | Saved: {scene_mp3.name}")
            continue

        # Real synthesis with CosyVoice-first -> Kokoro fallback hierarchy
        # Tier 1: CosyVoice via RunningHub ComfyUI
        if active_engine == "cosyvoice" or active_engine is None:
            try:
                print(f"  -> Attempting Tier 1: CosyVoice via RunningHub for Scene {s_id}...")
                from src.factory.runninghub_bot import run_narration_bot
                res = run_narration_bot(script=text, emotion=emotion, speed=speed)
                saved_files = res.get("saved_files", [])
                if not saved_files:
                    raise RuntimeError("CosyVoice workflow returned empty saved_files")
                cosy_file = Path(saved_files[-1])
                if not cosy_file.exists() or cosy_file.stat().st_size < 1000:
                    raise RuntimeError(f"CosyVoice audio output invalid: {cosy_file}")
                shutil.copy2(cosy_file, scene_raw)
                engine_used = "cosyvoice"
                voice_used = "cosyvoice_instruct"
                print(f"     ✅ Scene {s_id} generated via CosyVoice (RunningHub)!")
            except Exception as e:
                if active_engine == "cosyvoice":
                    raise RuntimeError(f"LOCKED NARRATOR FAILURE: Locked CosyVoice failed on Scene {s_id}: {e}")
                print(f"     ⚠️ CosyVoice unavailable ({e}). Falling back to Tier 2: Kokoro-82M ONNX local...")
                engine_used = None

        # Tier 2: Kokoro-82M ONNX Local Neural Runtime
        if engine_used is None:
            if kokoro is not None:
                print(f"  -> Generating Scene {s_id} via Kokoro-82M ONNX ({voice})...")
                import soundfile as sf
                lang = "en-gb" if voice.startswith("b") else "en-us"
                samples, sr = kokoro.create(text, voice=voice, speed=speed, lang=lang)
                sf.write(str(scene_raw), samples, sr)
                engine_used = "kokoro_local"
                voice_used = voice
                print(f"     ✅ Scene {s_id} generated via Kokoro-82M ONNX ({voice})")
            else:
                # Tier 3: Edge-TTS Proxy
                scene_edge_raw = raw_dir / f"scene_{s_id}_edge_raw.mp3"
                if not scene_mp3.exists() or scene_mp3.stat().st_size < 1000:
                    asyncio.run(generate_scene_edge_fallback(text, scene_edge_raw))
                    try:
                        master_audio(scene_edge_raw, scene_mp3)
                    except Exception:
                        shutil.copy2(scene_edge_raw, scene_mp3)
                engine_used = "edge_tts"
                voice_used = "en-GB-RyanNeural"

        # On Scene 1, establish single-narrator lock for the rest of the documentary
        if active_engine is None and engine_used:
            active_engine = engine_used
            if router:
                router.lock_narrator(project_id, engine_used, voice_used)
                print(f"🔒 Locked documentary narrator for '{project_id}' to {engine_used} ({voice_used})")

        master_audio(scene_raw, scene_mastered)
        master_audio(scene_raw, scene_mp3)
        dur = get_audio_duration_probe(scene_mp3)
        if dur <= 0.0:
            dur = float(scene.get("estimated_duration_sec", 12.0))

        durations.append(dur)
        scene_mastered_files.append(scene_mp3)
        if router:
            try:
                l = router.get_lock(project_id)
                if l and f"scene_{s_id}" not in l.scenes_completed:
                    l.scenes_completed.append(f"scene_{s_id}")
                    router._save_locks()
            except Exception:
                pass
        print(f"     [OK] Scene {s_id}: {dur:.2f}s | Saved: {scene_mp3.name}")

    # Synthesize Full Combined Intro
    full_text = " ".join(full_text_parts)
    full_raw = raw_dir / f"pilot_{voice}_full_raw.wav"
    full_wav = AUDIO_DIR / f"pilot_{voice}_mastered.wav"
    full_mp3 = AUDIO_DIR / f"pilot_{voice}_mastered.mp3"
    full_srt = SUBS_DIR / f"pilot_{voice}_full.srt"

    # Also keep standard generic filenames for downstream editors
    generic_wav = AUDIO_DIR / "pilot_intro_mastered.wav"
    generic_mp3 = AUDIO_DIR / "pilot_intro_full.mp3"
    generic_srt = SUBS_DIR / "pilot_intro_full.srt"

    print(f"\n  -> Synthesizing and mastering full documentary intro ({voice})...")
    if dry_run and full_mp3.exists() and full_mp3.stat().st_size > 1000:
        print(f"     [OK-DryRun] Full intro master already exists: {full_mp3.name}")
    elif kokoro is not None and not dry_run:
        import soundfile as sf
        lang = "en-gb" if voice.startswith("b") else "en-us"
        full_samples, full_sr = kokoro.create(full_text, voice=voice, speed=speed, lang=lang)
        sf.write(str(full_raw), full_samples, full_sr)
        master_audio(full_raw, full_wav)
        master_audio(full_raw, full_mp3)
        shutil.copy2(full_wav, generic_wav)
        shutil.copy2(full_mp3, generic_mp3)
    elif not dry_run:
        full_edge_raw = raw_dir / "pilot_full_edge_raw.mp3"
        asyncio.run(generate_scene_edge_fallback(full_text, full_edge_raw))
        try:
            master_audio(full_edge_raw, full_mp3)
        except Exception:
            shutil.copy2(full_edge_raw, full_mp3)
        shutil.copy2(full_mp3, generic_mp3)

    # Subtitles
    srt_content = generate_srt(scenes, durations, full_srt)
    shutil.copy2(full_srt, generic_srt)

    print("\n🎉 Broadcast Narration Pipeline Complete!")
    print(f"   Voice: {voice}")
    print(f"   Master WAV (24-bit 48kHz): {full_wav}")
    print(f"   Master MP3 (320kbps): {full_mp3}")
    print(f"   Subtitles SRT: {full_srt}")
    print(f"   Total Duration: {sum(durations):.2f}s across {len(scenes)} scenes")

    return {
        "voice": voice,
        "wav": str(full_wav),
        "mp3": str(full_mp3),
        "srt": str(full_srt),
        "durations": durations,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="DarkFactory Pilot Audio Engine")
    parser.add_argument("--voice", type=str, default=DEFAULT_VOICE, help=f"Kokoro voice ID (default: {DEFAULT_VOICE}, or bm_lewis, am_adam)")
    parser.add_argument("--speed", type=float, default=DEFAULT_SPEED, help=f"Playback speed (default: {DEFAULT_SPEED})")
    parser.add_argument("--dry-run", action="store_true", help="Simulate fast audio generation using existing stems or silent plates")
    parser.add_argument("--teaser", action="store_true", help="Synthesize only 3-scene teaser")
    parser.add_argument("--engine", type=str, choices=["cosyvoice", "kokoro"], default="cosyvoice", help="Preferred TTS engine: cosyvoice (RunningHub Tier 1 with Kokoro fallback) or kokoro (direct local ONNX)")
    args = parser.parse_args()

    run_pipeline(
        voice=args.voice,
        speed=args.speed,
        dry_run=args.dry_run,
        teaser=args.teaser,
        preferred_engine=args.engine,
    )


if __name__ == "__main__":
    main()
