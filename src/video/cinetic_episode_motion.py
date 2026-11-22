#!/usr/bin/env python3
"""DarkFactory Cinetic Full Episode Motion Engine.

Implements the professional investigative documentary motion graphics standard
inspired by Felipe Borges (Felpborges/claude-video) and Cinetic:
1. Deep noir canvas: inkStage (#0D0B0A) with subtle vignette and archival border.
2. Center-band kinetic statements (35%-65% frame height) with high-contrast
   typography (#F2EFEF) and operative keywords emphasized in bold tactical red (#DC2626).
3. Multi-layer Ken Burns motion on real historical photos (smooth zoom & pan).
4. Declassified stamp slam animations with synchronized SFX impact.
5. Real telemetry and dossier callouts (coordinates, timecodes, classification).
6. Audio SFX synchronization from the 1,220 SFX library (whoosh, stamp slam, radar).
7. Automatic mirroring to data/broll/ for seamless master video assembly.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Force UTF-8 on Windows consoles (ADR-01)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.video.ffmpeg_processor import get_ffmpeg_binary

logger = logging.getLogger("CineticEpisodeMotion")

DATA_DIR = PROJECT_ROOT / "data"
SCRIPTS_DIR = DATA_DIR / "scripts"
BROLL_DIR = DATA_DIR / "broll"
DEFAULT_MOTION_DIR = DATA_DIR / "final" / "motion_overlays"
SFX_DIR = DATA_DIR / "sfx"

# Canonic inkStage Netflix/BBC Investigative Documentary Palette
INK_STAGE_PALETTE: Dict[str, str] = {
    "bg_ink": "#0D0B0A",
    "card_bg": "#141211",
    "border_dark": "#262220",
    "border_highlight": "#38BDF822",
    "text_primary": "#F2EFEF",
    "text_muted": "#A3A3A3",
    "accent_red": "#DC2626",
    "accent_amber": "#F59E0B",
    "accent_cyan": "#38BDF8",
    "stamp_red": "#EF4444",
    "grid_tint": "#181615",
}


def hex_to_bgr(hex_str: str) -> Tuple[int, int, int]:
    """Convert hex color (#RRGGBB) to BGR tuple for OpenCV."""
    h = hex_str.lstrip("#")
    if len(h) == 8:  # Handle RGBA hex
        h = h[:6]
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    return (b, g, r)


def hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    """Convert hex color (#RRGGBB) to RGB tuple for Pillow."""
    h = hex_str.lstrip("#")
    if len(h) == 8:
        h = h[:6]
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    return (r, g, b)


def smooth_cubic_ease(p: float) -> float:
    """Standard easeInOutCubic curve for documentary camera zooms."""
    if p < 0.5:
        return 4.0 * p * p * p
    f = (2.0 * p) - 2.0
    return 0.5 * f * f * f + 1.0


@dataclass
class CineticSceneConfig:
    """Configuration for a single documentary investigative motion scene."""

    scene_id: int
    headline: str
    accent_word: str
    stamp_text: str = "TOP SECRET // DECLASSIFIED"
    telemetry: str = "SERPUKHOV-15 // 55°45'N 37°37'E"
    duration_sec: float = 6.0
    base_image: Optional[Path] = None
    visual_style: str = "INVESTIGATIVE_KEN_BURNS"
    timecode: str = "00:15:23 MSK"
    dossier_code: str = "SOVIET-ARCHIVE-83"


KEYWORD_PRIORITY = [
    "MISSILE", "MISSILES", "NUCLEAR", "WARHEADS", "ALARM", "DETECTION",
    "ATTACK", "SERPUKHOV-15", "SOVIET", "OKO", "SATELLITE", "PETROV",
    "COUNTDOWN", "BUNKER", "RED", "GLITCH", "FALSE", "CRITICAL",
    "RETALIATION", "LAUNCH", "CLASSIFIED", "CONFIDENTIAL", "ORDER"
]


def extract_kinetic_statement(text: str, scene_id: int = 1) -> Tuple[str, str]:
    """Extract a punchy 2-6 word kinetic statement and operative keyword for red highlight."""
    clean_text = text.replace("...", " ").replace("—", " ").replace("-", " ")
    clean_text = re.sub(r"[^\w\s]", "", clean_text).upper()
    words = clean_text.split()

    if not words:
        return f"SCENE {scene_id} ALERT", "ALERT"

    # Identify best accent keyword
    accent_word = ""
    for kw in KEYWORD_PRIORITY:
        if kw in words:
            accent_word = kw
            break
    if not accent_word and words:
        # Pick the longest operative word
        accent_word = max(words, key=len)

    # Select a punchy slice around the accent word (max 6 words)
    if accent_word in words:
        idx = words.index(accent_word)
        start = max(0, idx - 2)
        end = min(len(words), idx + 3)
        headline = " ".join(words[start:end])
    else:
        headline = " ".join(words[:min(5, len(words))])

    if not headline:
        headline = f"CRITICAL EVENT SCENE {scene_id}"
        accent_word = "CRITICAL"

    return headline, accent_word


class CineticEpisodeMotionEngine:
    """Master engine for rendering investigative documentary motion clips."""

    def __init__(
        self,
        broll_dir: Optional[Path | str] = None,
        output_dir: Optional[Path | str] = None,
        sfx_dir: Optional[Path | str] = None,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
    ) -> None:
        self.width = width
        self.height = height
        self.fps = fps
        self.broll_dir = Path(broll_dir).resolve() if broll_dir else BROLL_DIR.resolve()
        self.output_dir = Path(output_dir).resolve() if output_dir else DEFAULT_MOTION_DIR.resolve()
        self.sfx_dir = Path(sfx_dir).resolve() if sfx_dir else SFX_DIR.resolve()

        self.broll_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.sfx_manifest: Dict[str, List[str]] = self._load_sfx_manifest()

    def _load_sfx_manifest(self) -> Dict[str, List[str]]:
        """Loads sfx_manifest.json from SFX directory if available."""
        manifest_file = self.sfx_dir / "sfx_manifest.json"
        if manifest_file.is_file():
            try:
                with open(manifest_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not read SFX manifest: {e}")
        return {}

    def _get_sfx_path(self, category: str) -> Optional[Path]:
        """Resolves a sound effect file from manifest or directly on disk."""
        files = self.sfx_manifest.get(category, [])
        if files:
            p = PROJECT_ROOT / files[0]
            if p.is_file():
                return p
        # Fallback search inside sfx directory
        cand = list(self.sfx_dir.glob(f"**/*{category}*.*"))
        if cand:
            return cand[0]
        return None

    def render_motion_frame(
        self,
        cfg: CineticSceneConfig,
        progress: float,
        base_img_path: Optional[Path] = None,
    ) -> np.ndarray:
        """Renders a single 1080p frame with Ken Burns zoom, centered text, and tactical stamps."""
        # 1. Base canvas: inkStage (#0D0B0A)
        canvas = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        bg_bgr = hex_to_bgr(INK_STAGE_PALETTE["bg_ink"])
        canvas[:] = bg_bgr

        # 2. Subtle tactical grid lines
        grid_bgr = hex_to_bgr(INK_STAGE_PALETTE["grid_tint"])
        step = 80
        for x in range(0, self.width, step):
            cv2.line(canvas, (x, 0), (x, self.height), grid_bgr, 1)
        for y in range(0, self.height, step):
            cv2.line(canvas, (0, y), (self.width, y), grid_bgr, 1)

        # 3. Archival Photo with Ken Burns Camera Motion
        img_file = base_img_path or cfg.base_image or (self.broll_dir / f"scene_{cfg.scene_id}.jpg")
        photo = None
        if img_file and Path(img_file).is_file():
            photo = cv2.imread(str(img_file))

        if photo is None:
            # Create a rich dark plate if photo is missing
            photo = np.full((1080, 1920, 3), 35, dtype=np.uint8)
            cv2.putText(
                photo,
                f"ARCHIVE CLASSIFIED PLATE {cfg.scene_id}",
                (200, 540),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.5,
                (180, 180, 180),
                2,
            )

        # Calculate smooth Ken Burns zoom (1.00 -> 1.12) and subtle pan
        zoom = 1.00 + 0.12 * smooth_cubic_ease(progress)
        ph, pw = photo.shape[:2]
        crop_w = int(pw / zoom)
        crop_h = int(ph / zoom)

        # Subtle camera drift
        pan_x = int((progress - 0.5) * (pw - crop_w) * 0.4)
        pan_y = int((progress - 0.5) * (ph - crop_h) * 0.3)

        x1 = max(0, (pw - crop_w) // 2 + pan_x)
        y1 = max(0, (ph - crop_h) // 2 + pan_y)
        x2 = min(pw, x1 + crop_w)
        y2 = min(ph, y1 + crop_h)

        cropped = photo[y1:y2, x1:x2]

        # Documentary Card Window (1520 x 855 centered inside 1920x1080)
        card_w, card_h = 1520, 855
        card_x = (self.width - card_w) // 2
        card_y = (self.height - card_h) // 2

        scaled_photo = cv2.resize(cropped, (card_w, card_h), interpolation=cv2.INTER_LINEAR)

        # Darken slightly for cinematic noir look & text contrast
        scaled_photo = (scaled_photo.astype(np.float32) * 0.72).astype(np.uint8)

        # Paste onto canvas
        canvas[card_y : card_y + card_h, card_x : card_x + card_w] = scaled_photo

        # Draw card border and corner reticles
        border_bgr = hex_to_bgr(INK_STAGE_PALETTE["border_dark"])
        cv2.rectangle(canvas, (card_x, card_y), (card_x + card_w, card_y + card_h), border_bgr, 2)

        # Corner tick marks (#38BDF8)
        cyan_bgr = hex_to_bgr(INK_STAGE_PALETTE["accent_cyan"])
        tick_len = 20
        # Top-left
        cv2.line(canvas, (card_x - 4, card_y - 4), (card_x + tick_len, card_y - 4), cyan_bgr, 2)
        cv2.line(canvas, (card_x - 4, card_y - 4), (card_x - 4, card_y + tick_len), cyan_bgr, 2)
        # Top-right
        cv2.line(canvas, (card_x + card_w + 4, card_y - 4), (card_x + card_w - tick_len, card_y - 4), cyan_bgr, 2)
        cv2.line(canvas, (card_x + card_w + 4, card_y - 4), (card_x + card_w + 4, card_y + tick_len), cyan_bgr, 2)
        # Bottom-left
        cv2.line(canvas, (card_x - 4, card_y + card_h + 4), (card_x + tick_len, card_y + card_h + 4), cyan_bgr, 2)
        cv2.line(canvas, (card_x - 4, card_y + card_h + 4), (card_x - 4, card_y + card_h - tick_len), cyan_bgr, 2)
        # Bottom-right
        cv2.line(canvas, (card_x + card_w + 4, card_y + card_h + 4), (card_x + card_w - tick_len, card_y + card_h + 4), cyan_bgr, 2)
        cv2.line(canvas, (card_x + card_w + 4, card_y + card_h + 4), (card_x + card_w + 4, card_y + card_h - tick_len), cyan_bgr, 2)

        # Convert to PIL for sharp typography rendering
        pil_canvas = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_canvas)

        # 4. Center-Band Kinetic Headline (35%-65% frame height)
        # High-contrast typography: Clean, bold, with red accent on operative word
        font_size = 54
        font = None
        # Try finding system fonts (Arial, Segoe UI, Roboto)
        font_candidates = [
            "arialbd.ttf",
            "Arial Bold.ttf",
            "segoeuib.ttf",
            "Roboto-Bold.ttf",
            "arial.ttf",
        ]
        for fc in font_candidates:
            try:
                font = ImageFont.truetype(fc, font_size)
                break
            except Exception:
                continue
        if font is None:
            font = ImageFont.load_default()

        # Split words to render with accent color
        words = cfg.headline.split()
        full_text = " ".join(words)
        accent_target = cfg.accent_word.strip().upper()

        # Compute positions
        total_w = 0
        word_widths = []
        space_w = 16
        for w in words:
            try:
                bbox = draw.textbbox((0, 0), w, font=font)
                w_len = bbox[2] - bbox[0]
            except Exception:
                w_len = len(w) * 32
            word_widths.append(w_len)
            total_w += w_len + space_w
        total_w -= space_w

        text_x = (self.width - total_w) // 2
        # Middle band (y at ~48% of screen height)
        text_y = int(self.height * 0.48) - 20

        # Background blur band / pill behind statement for 100% legibility
        pad_x, pad_y = 30, 16
        draw.rectangle(
            [text_x - pad_x, text_y - pad_y, text_x + total_w + pad_x, text_y + 60 + pad_y],
            fill=(13, 11, 10, 220),
            outline=hex_to_rgb(INK_STAGE_PALETTE["border_dark"]),
            width=1,
        )

        curr_x = text_x
        for w, w_len in zip(words, word_widths):
            is_accent = (w.upper() == accent_target or accent_target in w.upper())
            color = hex_to_rgb(INK_STAGE_PALETTE["accent_red"]) if is_accent else hex_to_rgb(INK_STAGE_PALETTE["text_primary"])
            # Text shadow for pop
            draw.text((curr_x + 2, text_y + 2), w, fill=(0, 0, 0), font=font)
            draw.text((curr_x, text_y), w, fill=color, font=font)
            curr_x += w_len + space_w

        # 5. Declassified Stamp Animation (Slam down between progress 0.15 and 0.30)
        # Stamp settled position: top-right corner of documentary card
        stamp_active = progress >= 0.18
        if stamp_active:
            stamp_progress = min(1.0, (progress - 0.18) / 0.12)
            # Slam impact: scale drops from 2.5 down to 1.0
            scale = 2.5 - 1.5 * smooth_cubic_ease(stamp_progress)
            stamp_text = cfg.stamp_text.upper()

            # Create stamp plate
            stamp_font_size = max(14, int(22 * scale))
            s_font = None
            try:
                s_font = ImageFont.truetype("arialbd.ttf", stamp_font_size)
            except Exception:
                s_font = font

            s_bbox = draw.textbbox((0, 0), stamp_text, font=s_font)
            sw = s_bbox[2] - s_bbox[0] + 24
            sh = s_bbox[3] - s_bbox[1] + 16

            sx = card_x + card_w - sw - 40
            sy = card_y + 40

            # Stamp box with double border in vivid red
            draw.rectangle(
                [sx, sy, sx + sw, sy + sh],
                outline=hex_to_rgb(INK_STAGE_PALETTE["stamp_red"]),
                width=max(2, int(3 * scale)),
            )
            draw.rectangle(
                [sx + 4, sy + 4, sx + sw - 4, sy + sh - 4],
                outline=hex_to_rgb(INK_STAGE_PALETTE["stamp_red"]),
                width=1,
            )
            draw.text(
                (sx + 12, sy + 6),
                stamp_text,
                fill=hex_to_rgb(INK_STAGE_PALETTE["stamp_red"]),
                font=s_font,
            )

        # 6. Telemetry and Metadata Overlays (BBC/Netflix style)
        small_font = None
        try:
            small_font = ImageFont.truetype("arial.ttf", 16)
        except Exception:
            small_font = font

        # Top-left: Dossier code
        draw.text(
            (card_x + 20, card_y + 20),
            f"DOSSIER: {cfg.dossier_code} // SCENE 0{cfg.scene_id}",
            fill=hex_to_rgb(INK_STAGE_PALETTE["text_muted"]),
            font=small_font,
        )

        # Bottom-left: Telemetry & radar location with blinking dot
        dot_color = (34, 197, 94) if int(progress * 10) % 2 == 0 else (239, 68, 68)
        draw.ellipse([card_x + 20, card_y + card_h - 32, card_x + 30, card_y + card_h - 22], fill=dot_color)
        draw.text(
            (card_x + 38, card_y + card_h - 35),
            cfg.telemetry,
            fill=hex_to_rgb(INK_STAGE_PALETTE["text_muted"]),
            font=small_font,
        )

        # Bottom-right: Timecode
        draw.text(
            (card_x + card_w - 220, card_y + card_h - 35),
            f"{cfg.timecode} // RECORDED",
            fill=hex_to_rgb(INK_STAGE_PALETTE["text_muted"]),
            font=small_font,
        )

        return cv2.cvtColor(np.array(pil_canvas), cv2.COLOR_RGB2BGR)

    def render_scene_motion_clip(
        self,
        cfg: CineticSceneConfig,
        mirror_to_broll: bool = True,
    ) -> Path:
        """Renders complete motion scene clip into 1080p MP4 with synchronized SFX."""
        out_mp4 = self.output_dir / f"cinetic_motion_scene_{cfg.scene_id}.mp4"
        total_frames = int(cfg.duration_sec * self.fps)
        ffmpeg_bin = get_ffmpeg_binary()

        # Temporary raw video stream
        temp_video = self.output_dir / f"temp_raw_scene_{cfg.scene_id}.mp4"

        cmd = [
            ffmpeg_bin,
            "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{self.width}x{self.height}",
            "-pix_fmt", "bgr24",
            "-r", str(self.fps),
            "-i", "-",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "veryfast",
            "-crf", "18",
            str(temp_video),
        ]

        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        for f_idx in range(total_frames):
            prog = f_idx / max(1, total_frames - 1)
            frame = self.render_motion_frame(cfg, progress=prog)
            proc.stdin.write(frame.tobytes())

        proc.stdin.close()
        proc.wait()

        # Mux SFX audio (whoosh at start, slam at t=1.0s)
        whoosh_sfx = self._get_sfx_path("whooshes")
        slam_sfx = self._get_sfx_path("stamp_slam")

        if whoosh_sfx and slam_sfx and temp_video.is_file():
            # Composite SFX tracks into MP4
            mux_cmd = [
                ffmpeg_bin,
                "-y",
                "-i", str(temp_video),
                "-i", str(whoosh_sfx),
                "-i", str(slam_sfx),
                "-filter_complex",
                "[1:a]volume=0.4[a1];[2:a]adelay=1000|1000,volume=0.7[a2];[a1][a2]amix=inputs=2:duration=first[aout]",
                "-map", "0:v",
                "-map", "[aout]",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                str(out_mp4),
            ]
            res = subprocess.run(mux_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if res.returncode == 0 and out_mp4.is_file() and out_mp4.stat().st_size > 1000:
                temp_video.unlink(missing_ok=True)
            else:
                shutil.move(temp_video, out_mp4)
        else:
            shutil.move(temp_video, out_mp4)

        # Mirror to broll directory for seamless pipeline integration
        if mirror_to_broll and out_mp4.is_file():
            broll_mp4 = self.broll_dir / f"scene_{cfg.scene_id}.mp4"
            shutil.copy2(out_mp4, broll_mp4)
            logger.info(f"✅ Mirrored cinetic motion clip to B-roll: {broll_mp4.name}")

        logger.info(f"🎬 Rendered Cinetic Motion Scene {cfg.scene_id}: {out_mp4.name} ({cfg.duration_sec}s)")
        return out_mp4

    def generate_hyperframes_html(self, cfg: CineticSceneConfig) -> Path:
        """Generates standalone HyperFrames HTML/GSAP companion preview file."""
        html_file = self.output_dir / f"cinetic_scene_{cfg.scene_id}.html"

        words = cfg.headline.split()
        rendered_words = []
        for w in words:
            if w.upper() == cfg.accent_word.upper() or cfg.accent_word.upper() in w.upper():
                rendered_words.append(f'<span class="accent">{w}</span>')
            else:
                rendered_words.append(f"<span>{w}</span>")
        headline_html = " ".join(rendered_words)

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Cinetic Motion Scene {cfg.scene_id} - DarkFactory</title>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: {INK_STAGE_PALETTE["bg_ink"]};
      width: 1920px;
      height: 1080px;
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
    }}
    .doc-card {{
      position: relative;
      width: 1520px;
      height: 855px;
      background: {INK_STAGE_PALETTE["card_bg"]};
      border: 2px solid {INK_STAGE_PALETTE["border_dark"]};
      overflow: hidden;
      box-shadow: 0 20px 50px rgba(0,0,0,0.8);
    }}
    .ken-burns-img {{
      position: absolute;
      top: 0; left: 0; width: 100%; height: 100%;
      object-fit: cover;
      filter: brightness(0.72) contrast(1.1);
      transform-origin: center center;
    }}
    .center-statement {{
      position: absolute;
      top: 50%; left: 50%;
      transform: translate(-50%, -50%);
      background: rgba(13, 11, 10, 0.88);
      border: 1px solid {INK_STAGE_PALETTE["border_dark"]};
      padding: 24px 44px;
      border-radius: 4px;
      font-size: 54px;
      font-weight: 800;
      letter-spacing: -0.5px;
      color: {INK_STAGE_PALETTE["text_primary"]};
      text-transform: uppercase;
      white-space: nowrap;
      z-index: 10;
    }}
    .accent {{
      color: {INK_STAGE_PALETTE["accent_red"]};
      text-shadow: 0 0 25px rgba(220, 38, 38, 0.4);
    }}
    .stamp {{
      position: absolute;
      top: 40px; right: 40px;
      border: 3px solid {INK_STAGE_PALETTE["stamp_red"]};
      padding: 10px 18px;
      color: {INK_STAGE_PALETTE["stamp_red"]};
      font-size: 22px;
      font-weight: 800;
      letter-spacing: 2px;
      transform: rotate(-5deg);
      z-index: 12;
      opacity: 0;
    }}
    .telemetry {{
      position: absolute;
      bottom: 25px; left: 30px;
      font-size: 16px;
      color: {INK_STAGE_PALETTE["text_muted"]};
      letter-spacing: 1px;
      z-index: 10;
    }}
  </style>
</head>
<body>
  <div class="doc-card" id="card">
    <img src="../broll/scene_{cfg.scene_id}.jpg" class="ken-burns-img" id="photo" alt="Historical Archival Photo">
    <div class="stamp" id="stamp">{cfg.stamp_text}</div>
    <div class="center-statement" id="statement">{headline_html}</div>
    <div class="telemetry">DOSSIER: {cfg.dossier_code} // {cfg.telemetry}</div>
  </div>

  <script>
    const tl = gsap.timeline({{ repeat: -1, repeatDelay: 1 }});
    tl.fromTo("#photo", {{ scale: 1.0, x: -10 }}, {{ scale: 1.12, x: 15, duration: {cfg.duration_sec}, ease: "power1.inOut" }}, 0);
    tl.fromTo("#statement", {{ opacity: 0, y: 20 }}, {{ opacity: 1, y: 0, duration: 0.8, ease: "power2.out" }}, 0.3);
    tl.fromTo("#stamp", {{ scale: 2.5, opacity: 0 }}, {{ scale: 1.0, opacity: 1, duration: 0.35, ease: "power4.out" }}, 1.0);
    tl.to("#card", {{ x: "+=4", yoyo: true, repeat: 3, duration: 0.05 }}, 1.0); // Slam impact camera shake
  </script>
</body>
</html>
"""
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        return html_file

    def render_all_scenes(
        self,
        script_path: Path,
        limit: int = 0,
        mirror_to_broll: bool = True,
    ) -> List[Path]:
        """Processes and renders all scenes in screenplay using Cinetic motion engine."""
        with open(script_path, "r", encoding="utf-8") as f:
            script_data = json.load(f)

        scenes = script_data.get("scenes", [])
        if limit > 0:
            scenes = scenes[:limit]

        logger.info(f"🎬 Processing Cinetic Motion for {len(scenes)} scenes from {script_path.name}")
        rendered_paths: List[Path] = []

        for s in scenes:
            s_id = s.get("scene_id", 1)
            audio_text = s.get("audio_text", "")
            headline, accent_word = extract_kinetic_statement(audio_text, scene_id=s_id)
            dur = float(s.get("estimated_duration_sec", 6.0))

            cfg = CineticSceneConfig(
                scene_id=s_id,
                headline=headline,
                accent_word=accent_word,
                stamp_text=s.get("stamp_text", "TOP SECRET // DECLASSIFIED"),
                telemetry=s.get("timestamp_marker", "55°45'06\"N 37°37'04\"E"),
                duration_sec=dur,
                timecode=s.get("timecode", "00:15:23 MSK"),
            )

            # Generate companion HTML
            self.generate_hyperframes_html(cfg)

            # Render video clip
            out_clip = self.render_scene_motion_clip(cfg, mirror_to_broll=mirror_to_broll)
            rendered_paths.append(out_clip)

        logger.info(f"🎉 Cinetic Episode Motion Render Complete: {len(rendered_paths)} scenes generated.")
        return rendered_paths


def main() -> None:
    parser = argparse.ArgumentParser(description="DarkFactory Cinetic Full Episode Motion Engine")
    parser.add_argument("--script", type=str, default="", help="Path to screenplay JSON")
    parser.add_argument("--teaser", action="store_true", help="Render only teaser scenes (1..3)")
    parser.add_argument("--scene", type=int, default=0, help="Render a specific single scene ID")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of scenes to render")
    parser.add_argument("--fps", type=int, default=30, help="Frames per second (default: 30)")
    args = parser.parse_args()

    script_candidates = [
        SCRIPTS_DIR / "nolan_soviet_glitch.json",
        SCRIPTS_DIR / "pilot_soviet_glitch.json",
    ]
    script_path = None
    if args.script:
        script_path = Path(args.script)
    else:
        for sc in script_candidates:
            if sc.is_file():
                script_path = sc
                break

    if not script_path or not script_path.is_file():
        print(f"Error: Screenplay manifest not found: {script_path}", file=sys.stderr)
        sys.exit(1)

    engine = CineticEpisodeMotionEngine(fps=args.fps)

    if args.scene > 0:
        with open(script_path, "r", encoding="utf-8") as f:
            s_data = json.load(f)
        found = next((s for s in s_data.get("scenes", []) if s.get("scene_id") == args.scene), None)
        if not found:
            print(f"Scene {args.scene} not found in {script_path.name}", file=sys.stderr)
            sys.exit(1)
        headline, accent = extract_kinetic_statement(found.get("audio_text", ""), scene_id=args.scene)
        cfg = CineticSceneConfig(
            scene_id=args.scene,
            headline=headline,
            accent_word=accent,
            duration_sec=float(found.get("estimated_duration_sec", 6.0)),
        )
        engine.generate_hyperframes_html(cfg)
        out = engine.render_scene_motion_clip(cfg, mirror_to_broll=True)
        print(f"✅ Rendered scene {args.scene}: {out}")
    else:
        limit = 3 if args.teaser else args.limit
        results = engine.render_all_scenes(script_path, limit=limit, mirror_to_broll=True)
        print(f"✅ Rendered {len(results)} scenes.")


if __name__ == "__main__":
    main()
