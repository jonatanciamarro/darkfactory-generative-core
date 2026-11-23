#!/usr/bin/env python3
"""Cinetic 40-Second Cinematic Documentary Teaser Renderer.

Renders 5 motion graphics scenes following Christopher Nolan / Cinetic aesthetics:
- Deep noir canvas: inkStage (#0D0B0A)
- Center-band kinetic statements (35%-65% frame height) with #F2EFEF and #DC2626 accents
- Multi-layer Ken Burns zoom on archival photos (data/broll/scene_{1..5}.jpg)
- Declassified stamp slam animation
- Real telemetry, timecodes, and radar reticles
- 1080p @ 30 fps output to data/final/cinetic_teaser/scene_{1..5}.mp4
- Standalone HTML/GSAP companions to data/final/cinetic_teaser/scene_{1..5}.html
"""
from __future__ import annotations

import json
import logging
import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

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

from src.video.cinetic_episode_motion import (
    CineticEpisodeMotionEngine,
    CineticSceneConfig,
    INK_STAGE_PALETTE,
    hex_to_bgr,
    hex_to_rgb,
    smooth_cubic_ease,
)
from src.video.ffmpeg_processor import get_ffmpeg_binary

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("CineticTeaserRenderer")


def generate_scene_html(cfg: CineticSceneConfig, output_html: Path, broll_rel_path: str) -> None:
    """Generates standalone HyperFrames HTML/GSAP companion preview file."""
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
    <img src="{broll_rel_path}" class="ken-burns-img" id="photo" alt="Historical Archival Photo">
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
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_content)


def render_teaser_scenes(
    script_path: Path,
    output_dir: Path,
    broll_dir: Path,
    fps: int = 30,
) -> List[Tuple[Path, Path, float]]:
    """Renders all scenes in script to scene_{id}.mp4 and scene_{id}.html.

    Returns:
        List of tuples: (mp4_path, html_path, actual_duration)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    engine = CineticEpisodeMotionEngine(
        broll_dir=broll_dir,
        output_dir=output_dir,
        fps=fps,
    )

    with open(script_path, "r", encoding="utf-8") as f:
        script_data = json.load(f)

    scenes = script_data.get("scenes", [])
    logger.info(f"Loaded {len(scenes)} scenes from {script_path.name}")

    results = []

    for s in scenes:
        scene_id = int(s.get("scene_id", 1))
        duration_sec = float(s.get("duration_sec", 7.5))
        headline = s.get("headline", f"SCENE {scene_id} ALERT")
        accent_word = s.get("accent_word", "ALERT")
        stamp_text = s.get("stamp_text", "TOP SECRET // DECLASSIFIED")
        telemetry = s.get("telemetry", "SERPUKHOV-15 // 55°45'N 37°37'E")
        timecode = s.get("timecode", "00:15:23 MSK")
        dossier_code = s.get("dossier_code", "SOVIET-ARCHIVE-83")

        # Resolve image
        broll_img_raw = s.get("broll_image", f"data/broll/scene_{scene_id}.jpg")
        broll_img_path = PROJECT_ROOT / broll_img_raw
        if not broll_img_path.is_file():
            broll_img_path = broll_dir / f"scene_{scene_id}.jpg"

        cfg = CineticSceneConfig(
            scene_id=scene_id,
            headline=headline,
            accent_word=accent_word,
            stamp_text=stamp_text,
            telemetry=telemetry,
            duration_sec=duration_sec,
            base_image=broll_img_path if broll_img_path.is_file() else None,
            timecode=timecode,
            dossier_code=dossier_code,
        )

        logger.info(f"Rendering Scene {scene_id}: '{headline}' (Accent: '{accent_word}') - {duration_sec}s")

        # 1. Render Video Clip
        raw_clip = engine.render_scene_motion_clip(cfg, mirror_to_broll=False)

        # Target file: scene_{id}.mp4
        target_mp4 = output_dir / f"scene_{scene_id}.mp4"
        if raw_clip != target_mp4:
            shutil.copy2(raw_clip, target_mp4)

        # 2. Generate HTML / GSAP file: scene_{id}.html
        target_html = output_dir / f"scene_{scene_id}.html"
        broll_rel = f"../../broll/{broll_img_path.name}"
        generate_scene_html(cfg, target_html, broll_rel)

        # Also generate cinetic_scene_{id}.html for compatibility
        shutil.copy2(target_html, output_dir / f"cinetic_scene_{scene_id}.html")

        # Verify video metrics
        cap = cv2.VideoCapture(str(target_mp4))
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        v_fps = cap.get(cv2.CAP_PROP_FPS) or fps
        cap.release()
        actual_dur = frame_count / v_fps

        logger.info(
            f"✅ Scene {scene_id} Ready: {target_mp4.name} ({w}x{h} @ {v_fps:.1f}fps, "
            f"{frame_count} frames, {actual_dur:.2f}s)"
        )
        results.append((target_mp4, target_html, actual_dur))

    return results


def main():
    script_path = PROJECT_ROOT / "data" / "scripts" / "cinetic_teaser_40s.json"
    output_dir = PROJECT_ROOT / "data" / "final" / "cinetic_teaser"
    broll_dir = PROJECT_ROOT / "data" / "broll"

    if not script_path.is_file():
        logger.error(f"Script file not found: {script_path}")
        sys.exit(1)

    t0 = time.time()
    results = render_teaser_scenes(script_path, output_dir, broll_dir, fps=30)
    elapsed = time.time() - t0

    print("\n" + "=" * 60)
    print("🎬 CINETIC 40-SECOND TEASER RENDERING SUMMARY")
    print("=" * 60)
    total_dur = 0.0
    for mp4_path, html_path, dur in results:
        total_dur += dur
        print(f"- {mp4_path.name}: {dur:.2f}s | HTML: {html_path.name}")
    print(f"Total Video Duration: {total_dur:.2f}s (Target: 40.0s)")
    print(f"Render Time: {elapsed:.1f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()
