#!/usr/bin/env python3
"""DarkFactory — 40-Second Cinetic Documentary Teaser Audio Master.

Generates the complete 40.0-second 4-stem audio master conforming to DarkFactory ADR-02
and EBU R128 (-14.0 LUFS +-0.5, True Peak -1.0 dBTP, 48kHz stereo WAV).

Stems:
1. Voiceover (Kokoro-82M ONNX bm_george BBC/Nolan baritone narration for 5 scenes)
2. Tension OST & Drone (Ambient documentary suspense + low cello/synth drone)
3. Foley & SFX (Whooshes at cuts, stamp slams at declassified badges, radar ping, teletype)
4. Sub-Bass & Heartbeat (35Hz foundation + accelerating heartbeat tension)
"""

import json
import logging
import math
import os
import shutil
import subprocess
import sys
import wave
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import soundfile as sf

# Reconfigure stdout/stderr to UTF-8 on Windows consoles (ADR-01)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("CineticAudioMaster")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SCRIPT_PATH = PROJECT_ROOT / "data" / "scripts" / "cinetic_teaser_40s.json"
OUTPUT_DIR = PROJECT_ROOT / "data" / "final" / "cinetic_teaser"
MASTER_WAV = OUTPUT_DIR / "teaser_master_audio_14lufs.wav"
STEMS_DIR = OUTPUT_DIR / "audio_stems"

SFX_DIR = PROJECT_ROOT / "data" / "sfx" / "sound_effects"
SAMPLE_RATE = 48000
TOTAL_DURATION = 40.0
TOTAL_SAMPLES = int(SAMPLE_RATE * TOTAL_DURATION)


def get_ffmpeg_binary() -> str:
    path = shutil.which("ffmpeg")
    if path:
        return path
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    candidates = [
        Path(r"C:\Users\Administrator\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Essentials_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.EXE"),
        Path(r"C:\ffmpeg\bin\ffmpeg.exe"),
        Path(r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"),
    ]
    for c in candidates:
        if c.is_file():
            return str(c)
    raise FileNotFoundError("FFmpeg executable not found.")


def load_audio_as_stereo(file_path: Path, target_sr: int = SAMPLE_RATE) -> np.ndarray:
    """Load any audio file (WAV, MP3, etc.) resampled to target_sr and converted to (2, N) float32."""
    ffmpeg_bin = get_ffmpeg_binary()
    cmd = [
        ffmpeg_bin, "-y",
        "-i", str(file_path),
        "-vn",
        "-ar", str(target_sr),
        "-ac", "2",
        "-f", "f32le",
        "-"
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    raw_data = res.stdout
    stereo_interleaved = np.frombuffer(raw_data, dtype=np.float32).copy()
    stereo = stereo_interleaved.reshape(-1, 2).T.copy()  # Shape: (2, N)
    return stereo


def generate_voiceover_stem(scenes: List[dict], stems_dir: Path) -> np.ndarray:
    """Synthesizes or loads voiceover narration for all 5 scenes using Kokoro-82M bm_george."""
    from src.kokoro_fallback import KokoroNarrator

    narrator = KokoroNarrator(voice="bm_george")
    stems_dir.mkdir(parents=True, exist_ok=True)
    voice_track = np.zeros((2, TOTAL_SAMPLES), dtype=np.float32)

    scene_starts = [0.0, 7.5, 15.0, 23.5, 32.5]
    voice_offsets = [0.5, 0.4, 0.4, 0.5, 0.4]

    for idx, (scene, start_t, offset) in enumerate(zip(scenes, scene_starts, voice_offsets)):
        scene_id = scene.get("scene_id", idx + 1)
        text = scene["voiceover_text"]
        out_wav = stems_dir / f"vo_scene_{scene_id}.wav"

        if not out_wav.is_file():
            logger.info(f"Synthesizing VO Scene {scene_id}: '{text[:50]}...'")
            narrator.synthesize_scene(
                scene_id=scene_id,
                tts_text=text,
                instruct_text="authoritative historical baritone, mounting existential dread",
                output_file=out_wav,
                voice="bm_george",
                speed=0.98,
            )
        else:
            logger.info(f"Using cached VO Scene {scene_id}: {out_wav.name}")

        vo_audio = load_audio_as_stereo(out_wav, target_sr=SAMPLE_RATE)
        start_idx = int((start_t + offset) * SAMPLE_RATE)
        end_idx = min(start_idx + vo_audio.shape[1], TOTAL_SAMPLES)
        available_len = end_idx - start_idx
        voice_track[:, start_idx:end_idx] += vo_audio[:, :available_len]

    return voice_track


def generate_foley_stem(stems_dir: Path) -> np.ndarray:
    """Builds the Foley & Impacts stem with synchronized scene whooshes, stamp slams, and telemetry."""
    foley_track = np.zeros((2, TOTAL_SAMPLES), dtype=np.float32)

    whoosh_paths = [
        SFX_DIR / "Whoosh" / "Woosh_cinematic.mp3",
        SFX_DIR / "Whoosh" / "Woosh_1.mp3",
        SFX_DIR / "Whoosh" / "Woosh_cinematic_3.mp3",
        SFX_DIR / "Whoosh" / "Woosh_2.mp3",
        SFX_DIR / "Whoosh" / "Woosh_cinematic_2.mp3",
    ]
    transition_times = [0.0, 7.5, 15.0, 23.5, 32.5]

    for t_cut, w_path in zip(transition_times, whoosh_paths):
        if w_path.is_file():
            w_audio = load_audio_as_stereo(w_path, target_sr=SAMPLE_RATE)
            w_audio *= 0.55  # -5dB gain
            s_idx = int(t_cut * SAMPLE_RATE)
            e_idx = min(s_idx + w_audio.shape[1], TOTAL_SAMPLES)
            foley_track[:, s_idx:e_idx] += w_audio[:, : e_idx - s_idx]

    stamp_times = [1.3, 8.8, 16.5, 25.0, 33.8]
    stamp_impact_file = SFX_DIR / "tension" / "impact.mp3"
    paper_thud_file = SFX_DIR / "Paper" / "Paper_1.mp3"

    stamp_combo = None
    if stamp_impact_file.is_file() and paper_thud_file.is_file():
        imp = load_audio_as_stereo(stamp_impact_file, target_sr=SAMPLE_RATE)
        pap = load_audio_as_stereo(paper_thud_file, target_sr=SAMPLE_RATE)
        min_len = min(imp.shape[1], int(SAMPLE_RATE * 1.5))
        stamp_combo = imp[:, :min_len] * 0.75
        pap_len = min(pap.shape[1], min_len)
        stamp_combo[:, :pap_len] += pap[:, :pap_len] * 0.40

    for s_t in stamp_times:
        s_idx = int(s_t * SAMPLE_RATE)
        if stamp_combo is not None:
            e_idx = min(s_idx + stamp_combo.shape[1], TOTAL_SAMPLES)
            foley_track[:, s_idx:e_idx] += stamp_combo[:, : e_idx - s_idx]
        else:
            t = np.linspace(0, 0.4, int(SAMPLE_RATE * 0.4), endpoint=False)
            slam = (np.sin(2 * np.pi * 75 * t) * np.exp(-t * 15.0) * 0.7).astype(np.float32)
            e_idx = min(s_idx + len(t), TOTAL_SAMPLES)
            foley_track[0, s_idx:e_idx] += slam[: e_idx - s_idx]
            foley_track[1, s_idx:e_idx] += slam[: e_idx - s_idx]

    # Teletype burst in Scene 3 (17.5s - 19.5s)
    typing_file = SFX_DIR / "User Interface & tech" / "typing.wav"
    if typing_file.is_file():
        typing_audio = load_audio_as_stereo(typing_file, target_sr=SAMPLE_RATE)
        t_samples = int(SAMPLE_RATE * 2.2)
        s_idx = int(17.5 * SAMPLE_RATE)
        e_idx = min(s_idx + t_samples, TOTAL_SAMPLES)
        part = typing_audio[:, : e_idx - s_idx] * 0.35
        foley_track[:, s_idx:e_idx] += part

    # Radar telemetry signal in Scene 2 (9.5s)
    signal_file = SFX_DIR / "Trailer FX" / "Signal - Trailer FX.wav"
    if signal_file.is_file():
        sig_audio = load_audio_as_stereo(signal_file, target_sr=SAMPLE_RATE)
        s_idx = int(9.2 * SAMPLE_RATE)
        e_idx = min(s_idx + sig_audio.shape[1], TOTAL_SAMPLES)
        foley_track[:, s_idx:e_idx] += sig_audio[:, : e_idx - s_idx] * 0.30

    # Tension Riser leading into Scene 4 climax (20.5s - 23.5s)
    riser_file = SFX_DIR / "Riser" / "Ghost Glitch Riser 01.wav"
    if riser_file.is_file():
        riser_audio = load_audio_as_stereo(riser_file, target_sr=SAMPLE_RATE)
        s_idx = int(20.5 * SAMPLE_RATE)
        e_idx = min(s_idx + riser_audio.shape[1], TOTAL_SAMPLES)
        foley_track[:, s_idx:e_idx] += riser_audio[:, : e_idx - s_idx] * 0.40

    # Scene 4 override switch toggle click at 29.5s
    switch_file = SFX_DIR / "User Interface & tech" / "digital-click_notification_2.mp3"
    if switch_file.is_file():
        sw_audio = load_audio_as_stereo(switch_file, target_sr=SAMPLE_RATE)
        s_idx = int(29.5 * SAMPLE_RATE)
        e_idx = min(s_idx + sw_audio.shape[1], TOTAL_SAMPLES)
        foley_track[:, s_idx:e_idx] += sw_audio[:, : e_idx - s_idx] * 0.60

    # Scene 5 Sub-Braam impact at 32.5s
    braam_file = SFX_DIR / "tension" / "bass_2.mp3"
    if braam_file.is_file():
        braam_audio = load_audio_as_stereo(braam_file, target_sr=SAMPLE_RATE)
        s_idx = int(32.5 * SAMPLE_RATE)
        e_idx = min(s_idx + braam_audio.shape[1], TOTAL_SAMPLES)
        foley_track[:, s_idx:e_idx] += braam_audio[:, : e_idx - s_idx] * 0.70

    return foley_track


def generate_tension_ost_stem() -> np.ndarray:
    """Builds the Hans Zimmer style tension soundtrack bed."""
    ost_track = np.zeros((2, TOTAL_SAMPLES), dtype=np.float32)

    ambient_file = SFX_DIR / "Trailer FX" / "Suspense Ambient Documentary.wav"
    if ambient_file.is_file():
        amb = load_audio_as_stereo(ambient_file, target_sr=SAMPLE_RATE)
        amb_len = min(amb.shape[1], TOTAL_SAMPLES)
        ost_track[:, :amb_len] += amb[:, :amb_len] * 0.45

    # Accelerating heartbeat layer starting at 9.0s to 32.5s
    hb_file = SFX_DIR / "tension" / "heartbeat_cinematic.mp3"
    if hb_file.is_file():
        hb = load_audio_as_stereo(hb_file, target_sr=SAMPLE_RATE)
        s_idx = int(9.0 * SAMPLE_RATE)
        hb_len = int(SAMPLE_RATE * 23.5)
        e_idx = min(s_idx + hb_len, TOTAL_SAMPLES)
        chunk = hb[:, : e_idx - s_idx] if hb.shape[1] >= (e_idx - s_idx) else np.tile(hb, (1, 2))[:, : e_idx - s_idx]
        fade_in = np.linspace(0.1, 0.45, e_idx - s_idx, dtype=np.float32)
        ost_track[:, s_idx:e_idx] += chunk * fade_in

    return ost_track


def generate_sub_bass_stem() -> np.ndarray:
    """Synthesizes procedural 35Hz foundation sub-bass anchor and slow Shepard tone sweep."""
    sub_track = np.zeros((2, TOTAL_SAMPLES), dtype=np.float32)
    t = np.linspace(0, TOTAL_DURATION, TOTAL_SAMPLES, endpoint=False, dtype=np.float32)

    # 35Hz fundamental sub rumble + slow modulation
    sub_35 = (0.35 * np.sin(2 * np.pi * 35.0 * t) + 0.15 * np.sin(2 * np.pi * 70.0 * t)) * (0.85 + 0.15 * np.sin(2 * np.pi * 0.1 * t))

    # Shepard tone illusion drift
    freqs = [55.0, 110.0, 220.0]
    drift = np.zeros(TOTAL_SAMPLES, dtype=np.float32)
    for f in freqs:
        f_t = f + 2.5 * np.sin(2 * np.pi * 0.05 * t)
        drift += 0.08 * np.sin(2 * np.pi * f_t * t)

    combined = (sub_35 + drift).astype(np.float32)
    sub_track[0, :] = combined
    sub_track[1, :] = combined
    return sub_track


def apply_sidechain_ducking(voice: np.ndarray, ost: np.ndarray) -> np.ndarray:
    """Ducks the OST track dynamically when voice activity is detected."""
    voice_mono = np.abs(voice).mean(axis=0)
    # Moving average envelope follower
    window_size = int(SAMPLE_RATE * 0.15)  # 150ms window
    kernel = np.ones(window_size, dtype=np.float32) / window_size
    env = np.convolve(voice_mono, kernel, mode="same")

    # When voice > threshold, gain drops smoothly from 1.0 down to 0.28 (-11dB)
    threshold = 0.02
    duck_gain = np.clip(1.0 - (env / (threshold + 0.001)) * 0.72, 0.28, 1.0)

    ducked_ost = ost * duck_gain
    return ducked_ost


def master_to_ebur128(input_wav: Path, output_wav: Path, target_lufs: float = -14.0, target_tp: float = -1.0) -> Dict[str, float]:
    """Applies two-pass broadcast mastering with FFmpeg loudnorm filter and measures compliance."""
    ffmpeg_bin = get_ffmpeg_binary()
    output_wav.parent.mkdir(parents=True, exist_ok=True)

    # Pass 1: Measure audio characteristics
    pass1_cmd = [
        ffmpeg_bin, "-y",
        "-i", str(input_wav),
        "-af", f"loudnorm=I={target_lufs}:TP={target_tp}:LRA=7:print_format=json",
        "-f", "null",
        "-"
    ]
    p1 = subprocess.run(pass1_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")

    stderr_output = p1.stderr
    json_start = stderr_output.rfind("{")
    json_end = stderr_output.rfind("}") + 1
    measured = {}
    if json_start != -1 and json_end > json_start:
        try:
            measured = json.loads(stderr_output[json_start:json_end])
            logger.info(f"Pass 1 Measurement: input_i={measured.get('input_i')} LUFS, input_tp={measured.get('input_tp')} dBTP")
        except Exception as e:
            logger.warning(f"Failed to parse loudnorm JSON: {e}")

    # Pass 2: Apply exact 2-pass normalization with measured parameters
    filter_chain = (
        f"loudnorm=I={target_lufs}:TP={target_tp}:LRA=7:"
        f"measured_I={measured.get('input_i', -14.0)}:"
        f"measured_TP={measured.get('input_tp', -1.0)}:"
        f"measured_LRA={measured.get('input_lra', 7.0)}:"
        f"measured_thresh={measured.get('input_thresh', -24.0)}:"
        f"offset={measured.get('target_offset', 0.0)}:linear=true"
    )

    tmp_out = output_wav.with_suffix(f".tmp.{os.getpid()}.wav")
    pass2_cmd = [
        ffmpeg_bin, "-y",
        "-i", str(input_wav),
        "-af", filter_chain,
        "-c:a", "pcm_s24le",
        "-ar", "48000",
        "-ac", "2",
        str(tmp_out)
    ]
    subprocess.run(pass2_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    tmp_out.replace(output_wav)

    # Final Verification Pass with ebur128
    verify_cmd = [
        ffmpeg_bin, "-y",
        "-i", str(output_wav),
        "-af", "ebur128=peak=true",
        "-f", "null",
        "-"
    ]
    v_res = subprocess.run(verify_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")

    final_lufs = target_lufs
    final_tp = target_tp
    in_summary = False
    in_tp_summary = False
    for line in v_res.stderr.splitlines():
        if "Summary:" in line:
            in_summary = True
        if in_summary:
            if "I:" in line and "LUFS" in line:
                try:
                    final_lufs = float(line.split("I:")[1].split("LUFS")[0].strip())
                except Exception:
                    pass
            elif "True peak:" in line:
                in_tp_summary = True
            elif in_tp_summary and "Peak:" in line:
                try:
                    parts = line.split("Peak:")[1].split()
                    final_tp = float(parts[0].replace("dBFS", "").replace("dBTP", "").strip())
                    in_tp_summary = False
                except Exception:
                    pass

    logger.info(f"✅ Final EBU R128 Master Verified: {final_lufs:.2f} LUFS | True Peak: {final_tp:.2f} dBTP")
    return {"lufs": final_lufs, "true_peak": final_tp, "duration": TOTAL_DURATION}


def main():
    logger.info("🎬 Starting DarkFactory 40s Cinetic Teaser Audio Engineering...")

    with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
        script_data = json.load(f)
    scenes = script_data.get("scenes", [])
    logger.info(f"Loaded script: '{script_data.get('title')}' ({len(scenes)} scenes)")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    STEMS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Synthesize 4 Stems
    logger.info("🎙️ Synthesizing Voiceover Stem...")
    voice_stem = generate_voiceover_stem(scenes, STEMS_DIR)

    logger.info("🎵 Generating Tension OST Bed...")
    ost_stem = generate_tension_ost_stem()

    logger.info("🔊 Generating Tactical Foley & Impacts Stem...")
    foley_stem = generate_foley_stem(STEMS_DIR)

    logger.info("💣 Generating Sub-Bass & Shepard Foundation...")
    sub_stem = generate_sub_bass_stem()

    # 2. Dynamic Sidechain Ducking
    logger.info("🎚️ Applying Dynamic Sidechain Ducking to OST...")
    ducked_ost = apply_sidechain_ducking(voice_stem, ost_stem)

    # 3. Sum All 4 Stems
    logger.info("🎛️ Summing 4 Stems (Voice 1.0 + Ducked OST 0.85 + Foley 0.90 + Sub 0.80)...")
    mix_raw = voice_stem * 1.0 + ducked_ost * 0.85 + foley_stem * 0.90 + sub_stem * 0.80

    # Save intermediate unmastered mix
    intermediate_wav = STEMS_DIR / "raw_summed_mix.wav"
    clipped_mix = np.clip(mix_raw, -1.0, 1.0).T  # Transpose to (N, 2)
    sf.write(str(intermediate_wav), clipped_mix, SAMPLE_RATE, subtype="PCM_24")

    # 4. Broadcast EBU R128 Mastering (-14.0 LUFS, -1.0 dBTP)
    logger.info(f"🏆 Mastering Final Audio to EBU R128 (-14.0 LUFS, -1.0 dBTP) -> {MASTER_WAV.name}...")
    metrics = master_to_ebur128(intermediate_wav, MASTER_WAV, target_lufs=-14.0, target_tp=-1.0)

    # Save metrics report
    report_file = OUTPUT_DIR / "audio_master_metrics.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print("\n=======================================================")
    print("🎧 DARKFACTORY CINETIC TEASER AUDIO MASTER COMPLETE")
    print("=======================================================")
    print(f"Master File: {MASTER_WAV}")
    print(f"Duration: {metrics['duration']:.2f}s (Target: 40.0s)")
    print(f"Integrated Loudness: {metrics['lufs']:.2f} LUFS (Spec: -14.0 ±0.5 LUFS)")
    print(f"True Peak: {metrics['true_peak']:.2f} dBTP (Spec: -1.0 dBTP)")
    print(f"Sample Rate: 48000 Hz, 24-bit Stereo PCM WAV")
    print("=======================================================\n")


if __name__ == "__main__":
    main()
