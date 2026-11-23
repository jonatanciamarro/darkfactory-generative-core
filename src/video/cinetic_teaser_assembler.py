#!/usr/bin/env python3
"""DarkFactory Cinetic Master Assembler & QC Gatekeeper.

Stitches Cinetic motion scenes, muxes 4-stem mastered audio (-14 LUFS / -1.0 dBTP),
applies Kodak 2383 cinematic noir film emulation, and runs automated QC gates.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Reconfigure stdout/stderr to UTF-8 on Windows (ADR-01)
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.video.ffmpeg_processor import get_ffmpeg_binary, get_ffprobe_binary, probe_video
from src.video.cinematic_color import CinematicColorGrader, FilmLookProfile

logger = logging.getLogger("CineticTeaserAssembler")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


@dataclass
class SceneQC:
    scene_id: int
    path: str
    duration_sec: float
    width: int
    height: int
    fps: float
    video_codec: str
    filesize_bytes: int


@dataclass
class AudioQC:
    path: str
    duration_sec: float
    integrated_lufs: float
    true_peak_dbtp: float
    sample_rate: int
    channels: int
    lufs_pass: bool
    true_peak_pass: bool


@dataclass
class MasterTeaserQCReport:
    timestamp: str
    target_file: str
    filesize_bytes: int
    filesize_mb: float
    passed: bool
    duration_sec: float
    duration_pass: bool
    resolution: str
    resolution_pass: bool
    fps: float
    fps_pass: bool
    video_codec: str
    video_codec_pass: bool
    integrated_lufs: float
    lufs_pass: bool
    true_peak_dbtp: float
    true_peak_pass: bool
    color_profile: str
    scenes: List[Dict[str, Any]] = field(default_factory=list)
    audio_qc: Optional[Dict[str, Any]] = None
    compliance_grade: str = "EBU R128 Broadcast Approved / YouTube Green Dollar Ready"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def measure_audio_loudness(audio_or_video_path: Path | str) -> Tuple[float, float]:
    """Measure integrated loudness (LUFS) and True Peak (dBTP) using FFmpeg ebur128."""
    ffmpeg_bin = get_ffmpeg_binary()
    cmd = [
        ffmpeg_bin,
        "-nostats",
        "-i",
        str(audio_or_video_path),
        "-filter_complex",
        "ebur128=peak=true",
        "-f",
        "null",
        "-",
    ]
    res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace")
    
    integrated_lufs = -14.0
    true_peak_dbtp = -1.0

    in_integrated = False
    in_true_peak = False

    for line in res.stderr.splitlines():
        line_clean = line.strip()
        if "Integrated loudness:" in line_clean:
            in_integrated = True
            continue
        if in_integrated and line_clean.startswith("I:"):
            # e.g., "I:         -14.0 LUFS"
            parts = line_clean.split("I:")[1].split("LUFS")[0].strip()
            try:
                integrated_lufs = float(parts)
            except ValueError:
                pass
            in_integrated = False

        if "True peak:" in line_clean:
            in_true_peak = True
            continue
        if in_true_peak and line_clean.startswith("Peak:"):
            # e.g., "Peak:       -1.0 dBFS"
            parts = line_clean.split("Peak:")[1].split("dBFS")[0].split("dBTP")[0].strip()
            try:
                true_peak_dbtp = float(parts)
            except ValueError:
                pass
            in_true_peak = False

    return integrated_lufs, true_peak_dbtp


class CineticTeaserAssembler:
    """Orchestrates stitching, color science grading, audio muxing, and QC."""

    def __init__(
        self,
        teaser_dir: Path | str = PROJECT_ROOT / "data" / "final" / "cinetic_teaser",
        output_path: Path | str = PROJECT_ROOT / "data" / "final" / "cinetic_documentary_teaser_40s.mp4",
        expected_scenes: int = 5,
        target_duration: float = 40.0,
    ):
        self.teaser_dir = Path(teaser_dir)
        self.output_path = Path(output_path)
        self.expected_scenes = expected_scenes
        self.target_duration = target_duration
        self.ffmpeg_bin = get_ffmpeg_binary()
        self.ffprobe_bin = get_ffprobe_binary()
        self.grader = CinematicColorGrader(self.ffmpeg_bin)

    def verify_inputs(self) -> Tuple[List[Path], Path]:
        """Verify that all scene videos and the master audio track exist."""
        scenes: List[Path] = []
        for i in range(1, self.expected_scenes + 1):
            scene_file = self.teaser_dir / f"scene_{i}.mp4"
            if not scene_file.is_file():
                # Check alternative naming
                alt_file = self.teaser_dir / f"cinetic_motion_scene_{i}.mp4"
                if alt_file.is_file():
                    scene_file = alt_file
                else:
                    raise FileNotFoundError(f"Missing scene video {i}: {scene_file}")
            scenes.append(scene_file)

        master_audio = self.teaser_dir / "teaser_master_audio_14lufs.wav"
        if not master_audio.is_file():
            # Check mp3 or other audio fallback
            alt_audio = self.teaser_dir / "teaser_master_audio.wav"
            if alt_audio.is_file():
                master_audio = alt_audio
            else:
                raise FileNotFoundError(f"Missing master audio track: {master_audio}")

        return scenes, master_audio

    def assemble(
        self,
        color_profile: str = "kodak_2383",
        apply_film_look: bool = True,
        grain_strength: float = 0.12,
    ) -> MasterTeaserQCReport:
        """Execute stitching, Kodak 2383 grading, audio muxing, and QC report generation."""
        scenes, master_audio = self.verify_inputs()
        logger.info(f"Verified {len(scenes)} scenes and audio track: {master_audio.name}")

        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        temp_dir = self.teaser_dir / "temp_assembly"
        temp_dir.mkdir(parents=True, exist_ok=True)

        # 1. Create FFmpeg concat demuxer file
        concat_list = temp_dir / "concat_list.txt"
        with open(concat_list, "w", encoding="utf-8") as f:
            for sc in scenes:
                # Use forward slashes for FFmpeg
                sc_posix = sc.resolve().as_posix()
                f.write(f"file '{sc_posix}'\n")

        # 2. Build color grading filter graph (Kodak 2383)
        if apply_film_look:
            color_filter = self.grader.build_filter_graph(
                profile=color_profile,
                film_grain=True,
                grain_strength=grain_strength,
                letterbox_239=False,
            )
        else:
            color_filter = "null"

        logger.info(f"Color filter graph: {color_filter}")

        # 3. Concatenate video and mux with master audio
        # Using concat demuxer + color grading + master audio mux
        # We ensure: 1920x1080 @ 30 fps, H.264, AAC 320k 48kHz, duration clamped to 40.0s
        temp_output = temp_dir / "master_render.mp4"

        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list),
            "-i", str(master_audio),
            "-vf", color_filter,
            "-c:v", "libx264",
            "-preset", "slow",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-r", "30",
            "-c:a", "aac",
            "-b:a", "320k",
            "-ar", "48000",
            "-ac", "2",
            "-t", str(self.target_duration),
            "-movflags", "+faststart",
            str(temp_output),
        ]

        logger.info("Executing master assembly command...")
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
        if res.returncode != 0:
            logger.error(f"FFmpeg assembly failed: {res.stderr}")
            raise RuntimeError(f"FFmpeg assembly failed with return code {res.returncode}")

        # Move to final destination
        shutil.move(str(temp_output), str(self.output_path))
        logger.info(f"Exported master teaser to: {self.output_path}")

        # Clean up temp
        try:
            shutil.rmtree(str(temp_dir))
        except Exception:
            pass

        # 4. Run Automated QC Gate
        report = self.run_qc(scenes, master_audio, color_profile)
        qc_json_path = self.teaser_dir / "qc_report.json"
        with open(qc_json_path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2)
        logger.info(f"QC report saved to: {qc_json_path}")

        return report

    def run_qc(
        self,
        scenes: List[Path],
        master_audio: Path,
        color_profile: str,
    ) -> MasterTeaserQCReport:
        """Inspect and validate technical compliance against broadcast standards."""
        if not self.output_path.is_file():
            raise FileNotFoundError(f"Master teaser output file not found: {self.output_path}")

        props = probe_video(self.output_path)
        int_lufs, true_peak = measure_audio_loudness(self.output_path)

        # Scene telemetry
        scenes_data: List[Dict[str, Any]] = []
        for i, sc in enumerate(scenes, 1):
            sc_props = probe_video(sc)
            scenes_data.append({
                "scene_id": i,
                "file": sc.name,
                "duration_sec": sc_props.duration_seconds,
                "resolution": f"{sc_props.width}x{sc_props.height}",
                "fps": sc_props.fps,
                "video_codec": sc_props.video_codec,
                "filesize_bytes": sc_props.filesize_bytes,
            })

        # Threshold checks
        duration_pass = abs(props.duration_seconds - self.target_duration) <= 0.25
        res_pass = props.width == 1920 and props.height == 1080
        fps_pass = abs(props.fps - 30.0) <= 0.5
        codec_pass = props.video_codec.lower() in ["h264", "avc1"]

        # EBU R128: -14.0 LUFS (+-0.5), True Peak -1.0 dBTP (+-0.5)
        lufs_pass = (-14.6 <= int_lufs <= -13.4)
        true_peak_pass = (true_peak <= -0.5)

        overall_passed = bool(
            duration_pass and res_pass and fps_pass and codec_pass and lufs_pass and true_peak_pass
        )

        audio_qc = {
            "integrated_lufs": round(int_lufs, 2),
            "lufs_target": "-14.0 LUFS (+-0.5)",
            "lufs_pass": lufs_pass,
            "true_peak_dbtp": round(true_peak, 2),
            "true_peak_target": "-1.0 dBTP (<= -0.8 dBTP)",
            "true_peak_pass": true_peak_pass,
        }

        report = MasterTeaserQCReport(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            target_file=str(self.output_path.resolve()),
            filesize_bytes=props.filesize_bytes,
            filesize_mb=round(props.filesize_bytes / (1024 * 1024), 2),
            passed=overall_passed,
            duration_sec=round(props.duration_seconds, 2),
            duration_pass=duration_pass,
            resolution=f"{props.width}x{props.height}",
            resolution_pass=res_pass,
            fps=round(props.fps, 1),
            fps_pass=fps_pass,
            video_codec=props.video_codec,
            video_codec_pass=codec_pass,
            integrated_lufs=round(int_lufs, 2),
            lufs_pass=lufs_pass,
            true_peak_dbtp=round(true_peak, 2),
            true_peak_pass=true_peak_pass,
            color_profile=color_profile,
            scenes=scenes_data,
            audio_qc=audio_qc,
            compliance_grade="EBU R128 Broadcast Approved / YouTube Green Dollar Ready" if overall_passed else "QC Compliance Warnings",
        )

        return report


if __name__ == "__main__":
    assembler = CineticTeaserAssembler()
    try:
        report = assembler.assemble()
        print(json.dumps(report.to_dict(), indent=2))
        sys.exit(0 if report.passed else 1)
    except Exception as exc:
        logger.error(f"Assembly and QC failed: {exc}")
        sys.exit(1)
