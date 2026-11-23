"""Gemini 4 Argon Documentary Motion Engine (Swiss-Telemetry Kinetic Manifesto).

Ultra-high-fidelity motion design engine unifying:
1. Swiss-Telemetry Kinetic Manifesto (Josef Müller-Brockmann × GMUNK × Kyle Cooper).
2. HyperFrames + GSAP 3.14 deterministic paused timelines (`window.__timelines["main"] = tl`).
3. Monumental typography (Big Shoulders Display 900/300 + IBM Plex Mono tabular telemetry + Instrument Serif italic).
4. 3D CSS perspective stage (perspective: 1250px, stepped Z-planes from Z=-200px to Z=+200px with 3-axis Euler gimbal).
5. Procedural Catmull-Rom trajectory splines, ±2σ confidence corridors, and +4.82σ anomaly reticle locks.
6. Mechanical shutter polarity inversions (Obsidian #090A0D -> Archival Paper #F4F1EA).
7. Playwright Headless Chromium deterministic seek-and-render pipe directly into FFmpeg.
"""

from __future__ import annotations

import base64
from enum import Enum
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.video.ffmpeg_processor import get_ffmpeg_binary

logger = logging.getLogger("argon_documentary_motion")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SKILL_DIR = BASE_DIR / ".agents" / "skills" / "gemini-4-argon-motion-design"
FONTS_DIR = SKILL_DIR / "fonts"
VENDOR_DIR = SKILL_DIR / "vendor"
DEFAULT_OUTPUT_DIR = BASE_DIR / "data" / "final" / "motion_overlays"
BROLL_DIR = BASE_DIR / "data" / "broll"

BANNED_FONTS: List[str] = [
    "Inter",
    "Roboto",
    "Open Sans",
    "Noto Sans",
    "Arimo",
    "Lato",
    "Source Sans",
    "PT Sans",
    "Nunito",
    "Poppins",
    "Outfit",
    "Sora",
    "Playfair Display",
    "Cormorant Garamond",
    "Bodoni Moda",
    "EB Garamond",
    "Cinzel",
    "Prata",
    "Syne",
]


class ArgonMotionArchetype(str, Enum):
    """Canonic investigative motion archetypes for Cold War documentaries."""
    RADAR_TELEMETRY = "radar_telemetry"          # Early-warning radar glitch, 5 ICBM vectors, Catmull-Rom splines, reticle +4.82σ
    ZSPACE_BUNKER_PARALLAX = "zspace_bunker"      # 3D CSS stage (perspective 1250px), stepped Z-planes, Euler rotation gimbal
    CLASSIFIED_DOSSIER_INVERSION = "classified_dossier" # Polarity inversion (#090A0D -> #F4F1EA), carbon ink, red stamp
    NETFLIX_OSINT_STAGE = "netflix_osint"        # High-tech OSINT workspace, multi-window layout, map coordinates, CRT scanlines


class ArgonDocumentaryConfig(BaseModel):
    """Pydantic v2 configuration schema for an Argon documentary motion scene."""
    scene_id: int = Field(gt=0, description="Identificador da cena no roteiro")
    archetype: ArgonMotionArchetype
    title: str = Field(min_length=1, description="Título monumental em Big Shoulders Display 900")
    subtitle: str = Field(default="", description="Subtítulo em Big Shoulders Display 300")
    narrative_thesis: str = Field(default="", description="Texto editorial em IBM Plex Mono + Instrument Serif")
    telemetry_code: str = Field(default="SERPUKHOV-15 // OKO-4", description="Código de cabeçalho HUD")
    metrics: Dict[str, str] = Field(default_factory=dict, description="Métricas tabulares (font-variant-numeric: tabular-nums)")
    archival_image_path: Optional[str] = None
    duration_sec: float = Field(default=6.0, gt=0.0, le=30.0)
    fps: int = Field(default=30, ge=24, le=60)
    width: int = 1920
    height: int = 1080


class ArgonRenderResult(BaseModel):
    """DTO representing the result of an Argon motion render operation."""
    video_path: Path
    html_path: Path
    preview_image_path: Optional[Path] = None
    duration_sec: float
    fps: int
    width: int
    height: int
    rendered_frames: int
    engine: str = "playwright_argon_hyperframes"


_CACHED_FONTS_BASE64: Dict[str, str] = {}
_CACHED_GSAP_CODE: Optional[str] = None


def _get_font_base64(font_filename: str) -> str:
    """Read and cache base64 encoded WOFF2 font for 100% offline self-contained HTML."""
    if font_filename in _CACHED_FONTS_BASE64:
        return _CACHED_FONTS_BASE64[font_filename]

    font_path = FONTS_DIR / font_filename
    if font_path.is_file():
        encoded = base64.b64encode(font_path.read_bytes()).decode("ascii")
        _CACHED_FONTS_BASE64[font_filename] = encoded
        return encoded
    return ""


def _get_gsap_code() -> str:
    """Read local minified GSAP 3.14.2 code."""
    global _CACHED_GSAP_CODE
    if _CACHED_GSAP_CODE is not None:
        return _CACHED_GSAP_CODE

    gsap_path = VENDOR_DIR / "gsap.min.js"
    if gsap_path.is_file():
        _CACHED_GSAP_CODE = gsap_path.read_text(encoding="utf-8", errors="ignore")
        return _CACHED_GSAP_CODE
    return ""


class ArgonMotionEngine:
    """Master Swiss-Telemetry Kinetic Engine for DarkFactory."""

    def __init__(self, output_dir: Optional[Path] = None, broll_dir: Optional[Path] = None):
        self.output_dir = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
        self.broll_dir = Path(broll_dir) if broll_dir else BROLL_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.broll_dir.mkdir(parents=True, exist_ok=True)

    def build_html(self, config: ArgonDocumentaryConfig) -> str:
        """Generate a 100% self-contained Full HD HTML composition following the Swiss-Telemetry Manifesto."""
        bs_300 = _get_font_base64("big-shoulders-300.woff2")
        bs_900 = _get_font_base64("big-shoulders-900.woff2")
        ibm_400 = _get_font_base64("ibm-plex-mono-400.woff2")
        ibm_600 = _get_font_base64("ibm-plex-mono-600.woff2")
        inst_serif = _get_font_base64("instrument-serif-italic.woff2")

        # Local GSAP file URI for completely offline execution
        gsap_local_path = VENDOR_DIR / "gsap.min.js"
        gsap_script_src = gsap_local_path.as_uri() if gsap_local_path.is_file() else "vendor/gsap.min.js"

        # Resolve archival image if present
        img_b64 = ""
        if config.archival_image_path:
            p = Path(config.archival_image_path)
            if not p.is_file():
                candidate = self.broll_dir / f"scene_{config.scene_id}.jpg"
                if candidate.is_file():
                    p = candidate
            if p.is_file():
                try:
                    img_b64 = "data:image/jpeg;base64," + base64.b64encode(p.read_bytes()).decode("ascii")
                except Exception:
                    img_b64 = ""

        # Build specific archetype HTML blocks
        if config.archetype == ArgonMotionArchetype.RADAR_TELEMETRY:
            content_html, animation_js = self._build_radar_telemetry_archetype(config, img_b64)
        elif config.archetype == ArgonMotionArchetype.ZSPACE_BUNKER_PARALLAX:
            content_html, animation_js = self._build_zspace_bunker_archetype(config, img_b64)
        elif config.archetype == ArgonMotionArchetype.CLASSIFIED_DOSSIER_INVERSION:
            content_html, animation_js = self._build_classified_dossier_archetype(config, img_b64)
        else:
            content_html, animation_js = self._build_netflix_osint_archetype(config, img_b64)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>ARGON // SCENE {config.scene_id} // {config.title}</title>
  <style>
    @font-face {{
      font-family: "Big Shoulders Display";
      src: url("data:font/woff2;base64,{bs_300}") format("woff2");
      font-weight: 300;
      font-style: normal;
    }}
    @font-face {{
      font-family: "Big Shoulders Display";
      src: url("data:font/woff2;base64,{bs_900}") format("woff2");
      font-weight: 900;
      font-style: normal;
    }}
    @font-face {{
      font-family: "IBM Plex Mono";
      src: url("data:font/woff2;base64,{ibm_400}") format("woff2");
      font-weight: 400;
      font-style: normal;
    }}
    @font-face {{
      font-family: "IBM Plex Mono";
      src: url("data:font/woff2;base64,{ibm_600}") format("woff2");
      font-weight: 600;
      font-style: normal;
    }}
    @font-face {{
      font-family: "Instrument Serif";
      src: url("data:font/woff2;base64,{inst_serif}") format("woff2");
      font-weight: 400;
      font-style: italic;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      width: 1920px;
      height: 1080px;
      overflow: hidden;
      background: #090A0D;
      font-family: "IBM Plex Mono", monospace;
      -webkit-font-smoothing: antialiased;
      user-select: none;
    }}
    #root {{
      position: relative;
      width: 1920px;
      height: 1080px;
      overflow: hidden;
    }}
    .bg-grid-dark {{
      position: absolute;
      top: 0; left: 0; width: 1920px; height: 1080px;
      background-image:
        linear-gradient(to right, rgba(163, 173, 194, 0.07) 1px, transparent 1px),
        linear-gradient(to bottom, rgba(163, 173, 194, 0.07) 1px, transparent 1px);
      background-size: 120px 120px;
      pointer-events: none;
      z-index: 0;
    }}
    .bg-watermark-dark {{
      position: absolute;
      right: -30px; bottom: -70px;
      font-family: "Big Shoulders Display", sans-serif;
      font-weight: 900;
      font-size: 440px;
      line-height: 0.8;
      letter-spacing: -0.04em;
      color: rgba(247, 246, 242, 0.035);
      pointer-events: none;
      z-index: 0;
    }}
    .hud-bar-dark {{
      display: flex; flex-direction: row; align-items: center; justify-content: space-between;
      width: 100%; height: 54px; padding: 0 24px; background: #131722; border: 1px solid #2A3246;
      color: #F7F6F2; font-family: "IBM Plex Mono", monospace; font-size: 18px; font-weight: 600;
      font-variant-numeric: tabular-nums; font-variant-ligatures: none;
    }}
    .hud-accent-volt {{ color: #D4FF00; font-weight: 600; }}
    .hud-accent-vermilion {{ color: #FF4D38; font-weight: 600; }}
    .hud-muted-dark {{ color: #A3ADC2; font-weight: 400; }}
  </style>
</head>
<body>
  <div id="root" data-scene-id="{config.scene_id}" data-fps="{config.fps}">
    {content_html}
  </div>
  <script src="{gsap_script_src}"></script>
  <script>
    window.__timelines = window.__timelines || {{}};
    var tl = gsap.timeline({{ paused: true }});
    {animation_js}
    window.__timelines["main"] = tl;
  </script>
</body>
</html>"""
        return html

    def _build_radar_telemetry_archetype(self, config: ArgonDocumentaryConfig, img_b64: str) -> tuple[str, str]:
        """Soviet Early Warning Radar Anomaly & Catmull-Rom Trajectory Splines."""
        metrics_html = "".join(
            f'<div class="kpi-box"><span class="kpi-lbl">{k}</span><span class="kpi-val">{v}</span></div>'
            for k, v in config.metrics.items()
        )
        if not metrics_html:
            metrics_html = """
              <div class="kpi-box"><span class="kpi-lbl">RADAR LOCK</span><span class="kpi-val">+4.82σ</span></div>
              <div class="kpi-box"><span class="kpi-lbl">TIME TO IMPACT</span><span class="kpi-val">00:15:23 MSK</span></div>
              <div class="kpi-box"><span class="kpi-lbl">MISSILE COUNT</span><span class="kpi-val">5 ICBMs</span></div>
            """

        content = f"""
        <div class="bg-grid-dark"></div>
        <div class="bg-watermark-dark">01</div>
        <div style="position: relative; z-index: 2; display: flex; flex-direction: column; justify-content: space-between; width: 100%; height: 100%; padding: 56px 88px;">
          <!-- Top HUD -->
          <div class="hud-bar-dark" id="radar-hud-top">
            <div><span class="hud-accent-volt">SYSTEM: SERPUKHOV-15</span> · <span class="hud-muted-dark">OKO COSMOS SATELLITE</span></div>
            <div><span class="hud-accent-vermilion">ANOMALY: +4.82σ RETICLE LOCK</span> · <span class="hud-muted-dark">{config.telemetry_code}</span></div>
          </div>

          <!-- Main Center Stage -->
          <div style="display: flex; flex-direction: row; gap: 48px; flex: 1; align-items: stretch; margin: 32px 0;">
            <!-- Left Narrative Column -->
            <div style="width: 780px; display: flex; flex-direction: column; justify-content: space-between;">
              <div style="display: flex; flex-direction: column; gap: 8px;">
                <div style="display: inline-flex; align-self: flex-start; padding: 8px 18px; background: #171D2C; border-left: 4px solid #D4FF00; color: #D4FF00; font-size: 18px; font-weight: 600;">ACT 01 // CRITICAL WARNING</div>
                <div id="radar-title-1" style="font-family: 'Big Shoulders Display', sans-serif; font-size: 112px; font-weight: 900; line-height: 0.92; color: #F7F6F2; text-transform: uppercase;">{config.title}</div>
                <div id="radar-title-2" style="font-family: 'Big Shoulders Display', sans-serif; font-size: 96px; font-weight: 300; line-height: 0.94; color: #D4FF00; text-transform: uppercase;">{config.subtitle}</div>
                <div style="font-size: 20px; color: #A3ADC2; line-height: 1.5; margin-top: 14px;">
                  {config.narrative_thesis}
                  <span style="font-family: 'Instrument Serif', serif; font-style: italic; color: #F7F6F2;"> The sirens screamed in the silence of Serpukhov-15.</span>
                </div>
              </div>
              <!-- Tabular KPIs -->
              <div style="display: flex; flex-direction: row; gap: 20px;" id="radar-kpi-row">
                {metrics_html}
              </div>
            </div>

            <!-- Right Telemetry Observatory Stage -->
            <div style="flex: 1; background: #131722; border: 1px solid #2A3246; position: relative; overflow: hidden; display: flex; align-items: center; justify-content: center;" id="radar-screen">
              <svg viewBox="0 0 860 620" style="width: 100%; height: 100%; display: block;">
                <!-- Grid coordinates -->
                <circle cx="430" cy="310" r="260" fill="none" stroke="#2A3246" stroke-width="1.5" stroke-dasharray="8 6"/>
                <circle cx="430" cy="310" r="180" fill="none" stroke="#2A3246" stroke-width="1.5"/>
                <circle cx="430" cy="310" r="90" fill="none" stroke="#2A3246" stroke-width="1.5"/>
                <line x1="430" y1="40" x2="430" y2="580" stroke="#2A3246" stroke-width="1.5"/>
                <line x1="160" y1="310" x2="700" y2="310" stroke="#2A3246" stroke-width="1.5"/>

                <!-- Normal variance ±2σ confidence corridor -->
                <polygon id="radar-corridor" points="180,310 320,240 500,190 710,130 730,170 520,240 340,300 180,330" fill="rgba(212, 255, 0, 0.08)" stroke="rgba(212, 255, 0, 0.25)" stroke-width="1"/>

                <!-- Catmull-Rom Trajectory Spline -->
                <path id="radar-spline-main" d="M 180 320 Q 360 210, 520 200 T 720 140" fill="none" stroke="#D4FF00" stroke-width="4.5" stroke-linecap="round"/>
                <path id="radar-spline-sec" d="M 180 325 Q 380 230, 530 220 T 735 155" fill="none" stroke="#FF4D38" stroke-width="3" stroke-linecap="round" stroke-dasharray="12 6"/>

                <!-- Anomaly Target Reticle Lock (+4.82σ) -->
                <g id="radar-anomaly-lock" transform="translate(720, 140)">
                  <circle cx="0" cy="0" r="32" fill="none" stroke="#FF4D38" stroke-width="3"/>
                  <circle cx="0" cy="0" r="48" fill="none" stroke="#FF4D38" stroke-width="1.5" stroke-dasharray="10 8"/>
                  <line x1="-56" y1="0" x2="-36" y2="0" stroke="#FF4D38" stroke-width="3"/>
                  <line x1="36" y1="0" x2="56" y2="0" stroke="#FF4D38" stroke-width="3"/>
                  <line x1="0" y1="-56" x2="0" y2="-36" stroke="#FF4D38" stroke-width="3"/>
                  <line x1="0" y1="36" x2="0" y2="56" stroke="#FF4D38" stroke-width="3"/>
                  <text x="64" y="8" fill="#FF4D38" font-family="IBM Plex Mono" font-size="16" font-weight="600">+4.82σ LOCK</text>
                </g>

                <!-- Rotating radar sweep beam -->
                <line id="radar-sweep" x1="430" y1="310" x2="690" y2="180" stroke="#D4FF00" stroke-width="2.5" opacity="0.85"/>
              </svg>
            </div>
          </div>

          <!-- Bottom HUD -->
          <div class="hud-bar-dark" id="radar-hud-bot">
            <span class="hud-muted-dark">STATION: MOSCOW MILITARY DISTRICT // OKO EARLY WARNING</span>
            <span class="hud-accent-volt">PROTOCOL: 120 BPM TIME CLOCK // DETERMINISTIC TIMELINE</span>
          </div>
        </div>
        """

        style_extra = """
        .kpi-box { flex: 1; padding: 18px; background: #0D111B; border: 1px solid #2A3246; display: flex; flex-direction: column; gap: 6px; }
        .kpi-lbl { font-size: 14px; color: #A3ADC2; font-weight: 600; }
        .kpi-val { font-family: 'Big Shoulders Display', sans-serif; font-size: 42px; font-weight: 900; color: #F7F6F2; font-variant-numeric: tabular-nums; }
        """
        content = f"<style>{style_extra}</style>" + content

        anim = f"""
        tl.from("#radar-hud-top", {{ y: -40, opacity: 0, duration: 0.5, ease: "power3.out" }}, 0.1);
        tl.from("#radar-hud-bot", {{ y: 40, opacity: 0, duration: 0.5, ease: "power3.out" }}, 0.15);
        tl.from("#radar-title-1", {{ x: -60, opacity: 0, duration: 0.6, ease: "expo.out" }}, 0.25);
        tl.from("#radar-title-2", {{ x: -60, opacity: 0, duration: 0.6, ease: "expo.out" }}, 0.38);
        tl.from("#radar-screen", {{ scale: 0.95, opacity: 0, duration: 0.7, ease: "power2.out" }}, 0.30);
        tl.from("#radar-spline-main", {{ strokeDashoffset: 1200, duration: 2.2, ease: "power2.inOut" }}, 0.5);
        tl.from("#radar-spline-sec", {{ strokeDashoffset: 1200, duration: 2.4, ease: "power2.inOut" }}, 0.7);
        tl.from("#radar-anomaly-lock", {{ scale: 0, opacity: 0, duration: 0.6, ease: "back.out(2)" }}, 1.8);
        tl.to("#radar-sweep", {{ rotation: 360, svgOrigin: "430 310", duration: {config.duration_sec}, ease: "none", repeat: 0 }}, 0.0);
        """
        return content, anim

    def _build_zspace_bunker_archetype(self, config: ArgonDocumentaryConfig, img_b64: str) -> tuple[str, str]:
        """3D CSS Perspective Stage & Stepped Z-Planes (perspective: 1250px) through Serpukhov-15."""
        img_tag = ""
        if img_b64:
            img_tag = f'<img src="{img_b64}" style="width: 100%; height: 100%; object-fit: cover; filter: contrast(1.2) grayscale(0.6) brightness(0.85);">'
        else:
            img_tag = '<div style="width: 100%; height: 100%; background: #101622; display: flex; align-items: center; justify-content: center; color: #A3ADC2; font-size: 24px;">SERPUKHOV-15 COMMAND CONSOLE</div>'

        content = f"""
        <div class="bg-grid-dark"></div>
        <div class="bg-watermark-dark">02</div>
        <div style="position: relative; z-index: 2; display: flex; flex-direction: column; justify-content: space-between; width: 100%; height: 100%; padding: 56px 88px;">
          <!-- Top HUD -->
          <div class="hud-bar-dark" id="zspace-hud-top">
            <div><span class="hud-accent-volt">3D SPATIAL GIMBAL</span> · <span class="hud-muted-dark">EULER 3-AXIS CAMERA</span></div>
            <div><span class="hud-accent-vermilion">STAGE PERSPECTIVE: 1250PX</span> · <span class="hud-muted-dark">{config.telemetry_code}</span></div>
          </div>

          <!-- 3D Perspective Stage -->
          <div style="perspective: 1250px; width: 100%; flex: 1; margin: 30px 0; display: flex; align-items: center; justify-content: center; overflow: hidden; background: #0B0E16; border: 1px solid #2A3246; position: relative;">
            <div id="zspace-rig" style="position: relative; width: 920px; height: 620px; transform-style: preserve-3d;">
              <!-- Plane Z=-200 (Background Radar Grid) -->
              <div id="z-plane-bg" style="position: absolute; width: 100%; height: 100%; border: 1px dashed rgba(92, 225, 230, 0.3); transform: translateZ(-200px); background: rgba(13, 17, 27, 0.7); display: flex; align-items: flex-end; padding: 24px; color: #5CE1E6; font-size: 16px;">
                PLANE L05 // Z = -200px // RADAR BACKGROUND MATRIX
              </div>

              <!-- Plane Z=-100 (Historical Archival Stills) -->
              <div id="z-plane-photo" style="position: absolute; top: 60px; left: 80px; width: 760px; height: 480px; border: 2px solid #5CE1E6; transform: translateZ(-100px); box-shadow: 0 20px 50px rgba(0,0,0,0.8); overflow: hidden;">
                {img_tag}
                <div style="position: absolute; bottom: 0; left: 0; width: 100%; padding: 12px 20px; background: rgba(9, 10, 13, 0.85); color: #F7F6F2; font-size: 16px;">
                  ARCHIVAL DOSSIER: LT. COL. STANISLAV PETROV // OKO SURVEILLANCE
                </div>
              </div>

              <!-- Plane Z=0 (HUD Reticle Frame) -->
              <div id="z-plane-hud" style="position: absolute; top: 20px; left: 40px; width: 840px; height: 560px; border: 2px solid #D4FF00; transform: translateZ(0px); pointer-events: none; padding: 20px; display: flex; flex-direction: column; justify-content: space-between;">
                <div style="display: flex; justify-content: space-between; color: #D4FF00; font-size: 18px; font-weight: 600;">
                  <span>[ TARGET LOCK // G0 ]</span>
                  <span>CONFIDENCE 99.8%</span>
                </div>
                <div style="display: flex; justify-content: space-between; color: #A3ADC2; font-size: 16px;">
                  <span>COORDINATES: 55° N, 37° E</span>
                  <span>DEFCON: 1</span>
                </div>
              </div>

              <!-- Plane Z=+100 (Monumental Typography Slab) -->
              <div id="z-plane-title" style="position: absolute; bottom: 40px; left: -60px; width: 880px; transform: translateZ(100px); pointer-events: none;">
                <div style="font-family: 'Big Shoulders Display', sans-serif; font-size: 104px; font-weight: 900; line-height: 0.9; color: #F7F6F2; text-shadow: 0 10px 30px rgba(0,0,0,0.9); text-transform: uppercase;">
                  {config.title}
                </div>
                <div style="font-family: 'Big Shoulders Display', sans-serif; font-size: 80px; font-weight: 300; line-height: 0.95; color: #D4FF00; text-transform: uppercase;">
                  {config.subtitle}
                </div>
              </div>
            </div>
          </div>

          <!-- Bottom HUD -->
          <div class="hud-bar-dark" id="zspace-hud-bot">
            <span class="hud-muted-dark">CAMERA RIG: 3-AXIS GIMBAL // PRESERVE-3D DEPTH STACK</span>
            <span class="hud-accent-volt">EULER ROTATION: X: 18° -> -12° // Y: -24° -> 22°</span>
          </div>
        </div>
        """

        anim = f"""
        tl.from("#zspace-hud-top", {{ y: -40, opacity: 0, duration: 0.5, ease: "power3.out" }}, 0.1);
        tl.from("#zspace-hud-bot", {{ y: 40, opacity: 0, duration: 0.5, ease: "power3.out" }}, 0.15);
        tl.set("#z-plane-bg", {{ z: -200 }}, 0);
        tl.set("#z-plane-photo", {{ z: -100 }}, 0);
        tl.set("#z-plane-hud", {{ z: 0 }}, 0);
        tl.set("#z-plane-title", {{ z: 100 }}, 0);
        tl.fromTo("#zspace-rig", 
          {{ rotationX: 18, rotationY: -24, rotationZ: -2 }}, 
          {{ rotationX: -12, rotationY: 22, rotationZ: 2, duration: {config.duration_sec}, ease: "sine.inOut" }}, 
          0.2
        );
        tl.from("#z-plane-photo", {{ scale: 0.85, opacity: 0, duration: 0.8, ease: "expo.out" }}, 0.3);
        tl.from("#z-plane-title", {{ x: -80, opacity: 0, duration: 0.8, ease: "expo.out" }}, 0.5);
        """
        return content, anim

    def _build_classified_dossier_archetype(self, config: ArgonDocumentaryConfig, img_b64: str) -> tuple[str, str]:
        """Mechanical Shutter Polarity Inversion into Archival Paper (#F4F1EA) & Carbon Ink."""
        img_tag = ""
        if img_b64:
            img_tag = f'<img src="{img_b64}" style="width: 260px; height: 320px; object-fit: cover; border: 4px solid #0B0C10; box-shadow: 4px 6px 16px rgba(0,0,0,0.25);">'
        else:
            img_tag = '<div style="width: 260px; height: 320px; background: #C8C2B4; border: 4px solid #0B0C10; display: flex; align-items: center; justify-content: center; font-size: 18px; color: #0B0C10; font-weight: 600;">EVIDENCE PHOTO</div>'

        content = f"""
        <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: #F4F1EA; z-index: 1;"></div>
        <!-- Archival grid -->
        <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; background-image: linear-gradient(to right, rgba(11, 12, 16, 0.08) 1px, transparent 1px), linear-gradient(to bottom, rgba(11, 12, 16, 0.08) 1px, transparent 1px); background-size: 80px 80px; z-index: 1; pointer-events: none;"></div>

        <div style="position: relative; z-index: 2; display: flex; flex-direction: column; justify-content: space-between; width: 100%; height: 100%; padding: 56px 88px;">
          <!-- Light HUD Header -->
          <div style="display: flex; justify-content: space-between; align-items: center; height: 54px; padding: 0 24px; background: #E6E1D6; border: 2px solid #0B0C10; color: #0B0C10; font-family: 'IBM Plex Mono', monospace; font-size: 18px; font-weight: 600;" id="dossier-hud-top">
            <div><span>ARCHIVE // DECLASSIFIED SOVIET TELEGRAM</span></div>
            <div style="color: #B01204; font-weight: 600;"><span>DOSSIER: {config.telemetry_code}</span></div>
          </div>

          <!-- Dossier Body Content -->
          <div style="display: flex; flex-direction: row; gap: 64px; flex: 1; margin: 36px 0; align-items: center;">
            <!-- Attached Archival Photo with Brass Clip -->
            <div style="position: relative;" id="dossier-photo-card">
              <div style="position: absolute; top: -16px; left: 40px; width: 20px; height: 44px; border: 3px solid #786C56; border-radius: 10px; z-index: 3;"></div>
              {img_tag}
              <div style="position: absolute; bottom: -30px; left: 0; font-size: 14px; font-weight: 600; color: #3E4350;">EVIDENCE ITEM 1983-04</div>
            </div>

            <!-- Dossier Paper File -->
            <div style="flex: 1; display: flex; flex-direction: column; justify-content: space-between; height: 100%;" id="dossier-text-block">
              <div>
                <div style="display: inline-block; padding: 6px 14px; background: #0B0C10; color: #F4F1EA; font-weight: 600; font-size: 16px; margin-bottom: 14px;">CASE FILE: INCIDENTE 17-B</div>
                <div id="dossier-title" style="font-family: 'Big Shoulders Display', sans-serif; font-size: 112px; font-weight: 900; line-height: 0.92; color: #0B0C10; text-transform: uppercase;">
                  {config.title}
                </div>
                <div id="dossier-subtitle" style="font-family: 'Big Shoulders Display', sans-serif; font-size: 88px; font-weight: 300; line-height: 0.95; color: #B01204; text-transform: uppercase;">
                  {config.subtitle}
                </div>
                <div style="font-size: 21px; color: #2C303B; line-height: 1.5; margin-top: 18px; max-width: 820px;">
                  {config.narrative_thesis}
                  <span style="font-family: 'Instrument Serif', serif; font-style: italic; color: #0B0C10;"> Five red warning lights illuminated the command bunker simultaneously.</span>
                </div>
              </div>

              <!-- Rubber Stamp Box -->
              <div id="dossier-stamp" style="align-self: flex-start; border: 4px solid #B01204; padding: 12px 28px; transform: rotate(-4deg); color: #B01204; font-family: 'Big Shoulders Display', sans-serif; font-weight: 900; font-size: 48px; letter-spacing: 0.08em; text-transform: uppercase;">
                СОВЕРШЕННО СЕКРЕТНО // TOP SECRET
              </div>
            </div>
          </div>

          <!-- Light HUD Footer -->
          <div style="display: flex; justify-content: space-between; align-items: center; height: 54px; padding: 0 24px; background: #E6E1D6; border: 2px solid #0B0C10; color: #0B0C10; font-family: 'IBM Plex Mono', monospace; font-size: 18px; font-weight: 600;" id="dossier-hud-bot">
            <span>SURFACE: ARCHIVAL PAPER (#F4F1EA) · INK: CARBON (#0B0C10)</span>
            <span style="color: #0033B8;">POLARITY: INVERTED MECHANICAL SHUTTER</span>
          </div>
        </div>

        <!-- Mechanical Shutter Transition Blades -->
        <div id="shutter-top" style="position: absolute; top: 0; left: 0; width: 1920px; height: 540px; background: #0B0C10; z-index: 30; border-bottom: 4px solid #B01204; display: flex; align-items: center; justify-content: center;">
          <span style="font-family: 'Big Shoulders Display', sans-serif; font-size: 72px; font-weight: 900; color: #F7F6F2; letter-spacing: 0.08em;">POLARITY INVERSION // 04</span>
        </div>
        <div id="shutter-bot" style="position: absolute; top: 540px; left: 0; width: 1920px; height: 540px; background: #0B0C10; z-index: 30; border-top: 4px solid #D4FF00; display: flex; align-items: center; justify-content: center;">
          <span style="font-family: 'IBM Plex Mono', monospace; font-size: 24px; font-weight: 600; color: #D4FF00;">OBSIDIAN #090A0D -> PAPER #F4F1EA</span>
        </div>
        """

        anim = f"""
        tl.fromTo("#shutter-top", {{ y: 0 }}, {{ y: -540, duration: 0.6, ease: "power3.inOut" }}, 0.1);
        tl.fromTo("#shutter-bot", {{ y: 0 }}, {{ y: 540, duration: 0.6, ease: "power3.inOut" }}, 0.1);
        tl.from("#dossier-hud-top", {{ y: -30, opacity: 0, duration: 0.5, ease: "power3.out" }}, 0.4);
        tl.from("#dossier-hud-bot", {{ y: 30, opacity: 0, duration: 0.5, ease: "power3.out" }}, 0.45);
        tl.from("#dossier-photo-card", {{ x: -60, opacity: 0, duration: 0.7, ease: "expo.out" }}, 0.5);
        tl.from("#dossier-title", {{ y: 40, opacity: 0, duration: 0.6, ease: "expo.out" }}, 0.55);
        tl.from("#dossier-subtitle", {{ y: 40, opacity: 0, duration: 0.6, ease: "expo.out" }}, 0.65);
        tl.from("#dossier-stamp", {{ scale: 1.8, opacity: 0, duration: 0.5, ease: "back.out(2)" }}, 0.9);
        """
        return content, anim

    def _build_netflix_osint_archetype(self, config: ArgonDocumentaryConfig, img_b64: str) -> tuple[str, str]:
        """High-Tech Netflix OSINT Desktop with Tactical Map & CRT Scanlines."""
        metrics_html = "".join(
            f'<div class="osint-kpi"><span style="color:#5CE1E6;">{k}</span><span style="font-size:28px; font-weight:900; color:#F7F6F2;">{v}</span></div>'
            for k, v in config.metrics.items()
        )
        if not metrics_html:
            metrics_html = """
            <div class="osint-kpi"><span style="color:#5CE1E6;">ORBIT</span><span style="font-size:28px; font-weight:900; color:#F7F6F2;">MOLNIYA-1</span></div>
            <div class="osint-kpi"><span style="color:#5CE1E6;">SAT-ID</span><span style="font-size:28px; font-weight:900; color:#F7F6F2;">COSMOS-1374</span></div>
            """

        content = f"""
        <div class="bg-grid-dark"></div>
        <!-- CRT scanline overlay -->
        <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%); background-size: 100% 4px; z-index: 10; pointer-events: none;"></div>

        <div style="position: relative; z-index: 2; display: flex; flex-direction: column; justify-content: space-between; width: 100%; height: 100%; padding: 56px 88px;">
          <!-- Top OSINT bar -->
          <div class="hud-bar-dark" id="osint-hud-top">
            <div><span class="hud-accent-volt">OSINT INVESTIGATIVE WORKSPACE</span> · <span class="hud-muted-dark">GEO-SPATIAL RECONSTRUCTION</span></div>
            <div><span class="hud-accent-vermilion">FEED: {config.telemetry_code}</span></div>
          </div>

          <!-- OSINT Multi-Window Desktop -->
          <div style="display: flex; flex-direction: row; gap: 36px; flex: 1; margin: 30px 0;">
            <!-- Left Narrative & Map Card -->
            <div style="width: 720px; display: flex; flex-direction: column; justify-content: space-between;">
              <div style="display: flex; flex-direction: column; gap: 6px;">
                <div style="display: inline-flex; align-self: flex-start; padding: 6px 14px; background: #131722; border-left: 4px solid #5CE1E6; color: #5CE1E6; font-size: 16px; font-weight: 600;">FORENSIC RECONSTRUCTION</div>
                <div id="osint-title" style="font-family: 'Big Shoulders Display', sans-serif; font-size: 96px; font-weight: 900; line-height: 0.92; color: #F7F6F2; text-transform: uppercase;">{config.title}</div>
                <div id="osint-subtitle" style="font-family: 'Big Shoulders Display', sans-serif; font-size: 80px; font-weight: 300; line-height: 0.95; color: #5CE1E6; text-transform: uppercase;">{config.subtitle}</div>
                <div style="font-size: 19px; color: #A3ADC2; line-height: 1.5; margin-top: 12px;">
                  {config.narrative_thesis}
                  <span style="font-family: 'Instrument Serif', serif; font-style: italic; color: #F7F6F2;"> Satellite optics aligned with rare high-altitude cloud glint.</span>
                </div>
              </div>

              <!-- Satellite Telemetry Matrix -->
              <div style="display: flex; flex-direction: row; gap: 16px; background: #131722; border: 1px solid #2A3246; padding: 18px 24px;" id="osint-matrix">
                {metrics_html}
              </div>
            </div>

            <!-- Right Terminal / Radar Canvas Card -->
            <div style="flex: 1; background: #131722; border: 1px solid #2A3246; position: relative; overflow: hidden; padding: 24px;" id="osint-screen">
              <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #2A3246; padding-bottom: 12px; margin-bottom: 16px; font-size: 16px; color: #5CE1E6;">
                <span>WINDOW: COSMOS-1374 ORBITAL TRACK</span>
                <span>STATUS: RETRIEVED</span>
              </div>
              <svg viewBox="0 0 760 480" style="width: 100%; height: 420px; display: block;">
                <rect x="0" y="0" width="760" height="480" fill="#0D111B"/>
                <!-- Global map wireframe grid -->
                <path d="M 40 120 Q 200 60, 380 140 T 720 100" fill="none" stroke="#2A3246" stroke-width="2"/>
                <path d="M 40 240 Q 220 180, 420 260 T 720 220" fill="none" stroke="#2A3246" stroke-width="2"/>
                <path d="M 40 360 Q 240 300, 440 380 T 720 340" fill="none" stroke="#2A3246" stroke-width="2"/>
                <!-- Satellite Orbit Path -->
                <path id="osint-orbit" d="M 60 420 C 180 320, 320 160, 500 120 C 620 90, 680 80, 720 70" fill="none" stroke="#5CE1E6" stroke-width="4" stroke-linecap="round"/>
                <!-- GPS Pointers -->
                <circle cx="500" cy="120" r="10" fill="#FF4D38"/>
                <circle cx="500" cy="120" r="24" fill="none" stroke="#FF4D38" stroke-width="2" stroke-dasharray="6 4"/>
                <text x="524" y="126" fill="#F7F6F2" font-family="IBM Plex Mono" font-size="16" font-weight="600">MALMSTROM AFB (SUN GLINT REFLECTION)</text>
              </svg>
            </div>
          </div>

          <!-- Bottom OSINT bar -->
          <div class="hud-bar-dark" id="osint-hud-bot">
            <span class="hud-muted-dark">SOURCE: SOVIET MILITARY ARCHIVE // RECONSTRUCTED OSINT DATASET</span>
            <span class="hud-accent-volt">FRAME LOCK: 30 FPS BROADCAST</span>
          </div>
        </div>
        """

        style_extra = """
        .osint-kpi { flex: 1; display: flex; flex-direction: column; gap: 4px; }
        """
        content = f"<style>{style_extra}</style>" + content

        anim = f"""
        tl.from("#osint-hud-top", {{ y: -40, opacity: 0, duration: 0.5, ease: "power3.out" }}, 0.1);
        tl.from("#osint-hud-bot", {{ y: 40, opacity: 0, duration: 0.5, ease: "power3.out" }}, 0.15);
        tl.from("#osint-title", {{ x: -50, opacity: 0, duration: 0.6, ease: "expo.out" }}, 0.25);
        tl.from("#osint-subtitle", {{ x: -50, opacity: 0, duration: 0.6, ease: "expo.out" }}, 0.35);
        tl.from("#osint-screen", {{ scale: 0.95, opacity: 0, duration: 0.7, ease: "power2.out" }}, 0.3);
        tl.from("#osint-orbit", {{ strokeDashoffset: 1000, duration: 2.2, ease: "power2.inOut" }}, 0.6);
        """
        return content, anim

    def render_scene_video(
        self,
        config: ArgonDocumentaryConfig,
        output_path: Optional[Path] = None,
        preview_only: bool = False,
    ) -> ArgonRenderResult:
        """Render the Argon scene composition using Playwright Headless Chromium and FFmpeg."""
        from playwright.sync_api import sync_playwright

        out_name = f"argon_scene_{config.scene_id}_{config.archetype.value}"
        if output_path:
            target_mp4 = Path(output_path)
        else:
            target_mp4 = self.output_dir / f"{out_name}.mp4"

        target_html = target_mp4.with_suffix(".html")
        target_png = target_mp4.with_suffix(".png")

        html_content = self.build_html(config)
        target_html.write_text(html_content, encoding="utf-8")

        total_frames = int(config.duration_sec * config.fps)
        ffmpeg_bin = get_ffmpeg_binary() or "ffmpeg"

        logger.info(
            f"🎬 Rendering Argon Scene {config.scene_id} [{config.archetype.value}]: "
            f"{config.duration_sec}s @ {config.fps}fps ({total_frames} frames)..."
        )

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": config.width, "height": config.height})
            page.set_content(html_content, wait_until="domcontentloaded")
            # Ensure GSAP is loaded offline without network delays
            gsap_path = VENDOR_DIR / "gsap.min.js"
            if gsap_path.is_file():
                page.add_script_tag(path=str(gsap_path))
            page.evaluate("document.fonts.ready")

            # Pause master timeline for frame-accurate seeking
            page.evaluate("if (window.__timelines && window.__timelines.main) { window.__timelines.main.pause(); }")

            if preview_only:
                # Seek to 1.5s or halfway for static preview frame
                mid_t = min(1.5, config.duration_sec / 2.0)
                page.evaluate(f"if (window.__timelines && window.__timelines.main) {{ window.__timelines.main.seek({mid_t}); }}")
                png_bytes = page.screenshot(type="png")
                target_png.write_bytes(png_bytes)
                browser.close()

                # Generate a single-frame holding MP4 if target_mp4 does not exist
                ffmpeg_cmd = [
                    ffmpeg_bin, "-y",
                    "-loop", "1",
                    "-i", str(target_png),
                    "-t", str(config.duration_sec),
                    "-r", str(config.fps),
                    "-c:v", "libx264",
                    "-preset", "ultrafast",
                    "-pix_fmt", "yuv420p",
                    str(target_mp4),
                ]
                subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)

                return ArgonRenderResult(
                    video_path=target_mp4,
                    html_path=target_html,
                    preview_image_path=target_png,
                    duration_sec=config.duration_sec,
                    fps=config.fps,
                    width=config.width,
                    height=config.height,
                    rendered_frames=1,
                    engine="playwright_argon_hyperframes_preview",
                )

            # Full multi-frame deterministic render via FFmpeg pipe
            ffmpeg_cmd = [
                ffmpeg_bin, "-y",
                "-f", "image2pipe",
                "-vcodec", "png",
                "-r", str(config.fps),
                "-i", "-",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "18",
                "-pix_fmt", "yuv420p",
                str(target_mp4),
            ]

            proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Seek frame-by-frame
            for frame_idx in range(total_frames):
                t_sec = frame_idx / float(config.fps)
                page.evaluate(f"if (window.__timelines && window.__timelines.main) {{ window.__timelines.main.seek({t_sec}); }}")
                frame_png = page.screenshot(type="png")
                try:
                    proc.stdin.write(frame_png)
                except (BrokenPipeError, OSError):
                    break

            if proc.stdin:
                proc.stdin.close()
            proc.wait()

            # Capture preview poster
            target_png.write_bytes(page.screenshot(type="png"))
            browser.close()

        logger.info(f"✅ Rendered Argon Scene MP4: {target_mp4} ({target_mp4.stat().st_size / 1024 / 1024:.2f} MB)")
        return ArgonRenderResult(
            video_path=target_mp4,
            html_path=target_html,
            preview_image_path=target_png,
            duration_sec=config.duration_sec,
            fps=config.fps,
            width=config.width,
            height=config.height,
            rendered_frames=total_frames,
            engine="playwright_argon_hyperframes",
        )

    def render_scene_clip(self, config: ArgonDocumentaryConfig, output_path: Optional[Path] = None) -> Path:
        """Helper to render scene and mirror directly to data/broll/ for montage assembly."""
        res = self.render_scene_video(config=config, output_path=output_path, preview_only=False)
        mirror_path = self.broll_dir / f"scene_{config.scene_id}.mp4"
        try:
            import shutil
            shutil.copy2(res.video_path, mirror_path)
            logger.info(f"🔄 Mirrored Argon motion scene {config.scene_id} to {mirror_path}")
        except Exception as e:
            logger.warning(f"Could not mirror to broll: {e}")
        return res.video_path
