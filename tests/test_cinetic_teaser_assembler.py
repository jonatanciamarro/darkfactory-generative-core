"""Unit tests for CineticTeaserAssembler & Master QC Gatekeeper."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from src.video.cinetic_teaser_assembler import (
    CineticTeaserAssembler,
    MasterTeaserQCReport,
    measure_audio_loudness,
)
from src.video.ffmpeg_processor import VideoProperties


def test_measure_audio_loudness_parsing():
    """Verify regex parsing of ebur128 stdout/stderr."""
    mock_stderr = """
[Parsed_ebur128_0 @ 000001]
  Integrated loudness:
    I:         -14.1 LUFS
    Threshold: -24.1 LUFS

  True peak:
    Peak:       -1.0 dBFS
"""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stderr=mock_stderr, returncode=0)
        lufs, tp = measure_audio_loudness("dummy.wav")
        assert lufs == -14.1
        assert tp == -1.0


def test_cinetic_teaser_assembler_verify_inputs_missing(tmp_path):
    """Verify FileNotFoundError is raised if scenes are missing."""
    assembler = CineticTeaserAssembler(teaser_dir=tmp_path, output_path=tmp_path / "out.mp4")
    with pytest.raises(FileNotFoundError):
        assembler.verify_inputs()


def test_master_teaser_qc_report_to_dict():
    """Verify MasterTeaserQCReport serialization."""
    report = MasterTeaserQCReport(
        timestamp="2026-11-22T20:00:00Z",
        target_file="/path/to/test.mp4",
        filesize_bytes=1000000,
        filesize_mb=0.95,
        passed=True,
        duration_sec=40.0,
        duration_pass=True,
        resolution="1920x1080",
        resolution_pass=True,
        fps=30.0,
        fps_pass=True,
        video_codec="h264",
        video_codec_pass=True,
        integrated_lufs=-14.0,
        lufs_pass=True,
        true_peak_dbtp=-1.0,
        true_peak_pass=True,
        color_profile="kodak_2383",
        scenes=[],
    )
    d = report.to_dict()
    assert d["passed"] is True
    assert d["duration_sec"] == 40.0
    assert d["color_profile"] == "kodak_2383"
    assert "EBU R128" in d["compliance_grade"]
