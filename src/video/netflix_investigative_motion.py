#!/usr/bin/env python3
"""DarkFactory — Netflix-Grade Investigative Documentary Motion Engine.

Implements the 3 Canonic Investigative Visual Archetypes inspired by official
Netflix, HBO, and BBC historical crime/conspiracy documentaries:

1. ARQUÉTIPO 1: CORKBOARD_CONSPIRACY
   - Photorealistic textured corkboard with dark wood bevel frame.
   - Pinned Polaroid-style suspect/satellite photos with name labels.
   - Realistic red yarn strings (Bezier splines) linking pins with 3D drop-shadows.
   - Pinned tactical maps, crime scene snapshots, handwritten post-it notes.
   - Directional warm incandescent desk lamp lighting with radial falloff.

2. ARQUÉTIPO 2: TACTILE_CLASSIFIED_DOSSIER
   - Aged manila/cardstock folder with grunge distress on dark rustic wood.
   - Vintage brass metallic paperclips holding archival portraits.
   - Distressed rubber stamps ("INCIDENTE 17-B", "TOP SECRET // DECLASSIFIED").
   - Volumetric diagonal sunlight beam (god rays) with floating micro dust motes.
   - Peeking internal declassified documents.

3. ARQUÉTIPO 3: NETFLIX_OSINT_DESKTOP
   - Cyber-investigation workspace over dark CRT grid scanlines.
   - Floating translucent windows with macOS traffic light buttons (red, yellow, green).
   - Digital vector satellite street maps with route tracing and pin clusters.
   - Split-screen forensic analysis and terminal feeds with mouse cursor interaction.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import os
import random
import shutil
import subprocess
import sys
import time
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from pydantic import BaseModel, Field

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

logger = logging.getLogger("NetflixInvestigativeMotion")

DATA_DIR = PROJECT_ROOT / "data"
BROLL_DIR = DATA_DIR / "broll"
DEFAULT_MOTION_DIR = DATA_DIR / "final" / "motion_overlays"
SFX_DIR = DATA_DIR / "sfx"


class MotionArchetype(str, Enum):
    """The 3 Canonic Investigative Documentary Visual Archetypes."""
    CORKBOARD_CONSPIRACY = "CORKBOARD_CONSPIRACY"
    TACTILE_CLASSIFIED_DOSSIER = "TACTILE_CLASSIFIED_DOSSIER"
    NETFLIX_OSINT_DESKTOP = "NETFLIX_OSINT_DESKTOP"


class PinnedEvidenceItem(BaseModel):
    """An evidence item pinned to the investigation corkboard."""
    item_id: str
    title: str
    item_type: str = Field(default="photo", description="'photo', 'map', 'note', 'document', 'footprint'")
    image_path: Optional[str] = None
    note_text: Optional[str] = None
    position_xy: Tuple[int, int] = (960, 540)
    rotation_deg: float = 0.0
    pin_color: str = "red"  # 'red', 'yellow', 'brass'


class RedStringConnection(BaseModel):
    """Red yarn connection between two pinned evidence items on corkboard."""
    from_item_id: str
    to_item_id: str
    sag_factor: float = 0.15
    color: str = "#DC2626"
    has_shadow: bool = True


class DossierConfig(BaseModel):
    """Configuration for tactile classified manila folder."""
    case_number: str = "CASE FILE NO. 1983-SOVIET"
    subject_title: str = "STANISLAV PETROV // SERPUKHOV-15"
    stamp_headline: str = "INCIDENTE 17-B"
    stamp_subtitle: str = "ARQUIVO DESCLASSIFICADO // CONFIDENCIAL"
    stamped_badge: str = "TOP SECRET // KGB ARCHIVE"
    pinned_photo_path: Optional[str] = None
    paperclip_type: str = "brass_metallic"
    has_volumetric_light: bool = True
    light_beam_angle_deg: float = 45.0
    dust_motes_enabled: bool = True


class OSINTWindow(BaseModel):
    """A floating investigation window on the OSINT desktop layout."""
    window_id: str
    title: str
    window_type: str = Field(default="map_route", description="'map_route', 'split_evidence', 'teletype', 'radar_sweep'")
    rect: Tuple[int, int, int, int] = (100, 100, 600, 400)  # x, y, width, height
    content_data: Dict[str, Any] = Field(default_factory=dict)
    z_index: int = 1


class NetflixInvestigativeSceneDTO(BaseModel):
    """Master DTO for rendering high-end investigative documentary motion scenes."""
    scene_id: int
    archetype: MotionArchetype
    duration_sec: float = 6.0
    resolution: Tuple[int, int] = (1920, 1080)
    fps: int = 30
    corkboard_items: List[PinnedEvidenceItem] = Field(default_factory=list)
    red_strings: List[RedStringConnection] = Field(default_factory=list)
    dossier_config: Optional[DossierConfig] = None
    osint_windows: List[OSINTWindow] = Field(default_factory=list)
    camera_movement: str = "slow_dramatic_push_in"
    output_mp4_path: str = ""
    mirror_to_broll: bool = True


def get_system_font(size: int = 24, bold: bool = False) -> ImageFont.ImageFont:
    """Safely retrieves a clean TrueType font or fallback."""
    candidates = (
        ["arialbd.ttf", "segoeuib.ttf", "Arial Bold.ttf"]
        if bold
        else ["arial.ttf", "segoeui.ttf", "Roboto-Regular.ttf", "Arial.ttf"]
    )
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except Exception:
            continue
    return ImageFont.load_default()


# ═════════════════════════════════════════════════════════════════════════
# ARQUÉTIPO 1: CORKBOARD CONSPIRACY (Ref Imagem 1)
# ═════════════════════════════════════════════════════════════════════════

_CACHED_CORK_TEXTURE: Optional[np.ndarray] = None
_CACHED_LIGHT_MASK: Optional[np.ndarray] = None


def generate_procedural_cork_texture(width: int, height: int) -> np.ndarray:
    """Generates a rich, textured corkboard background with wooden frame (cached for speed)."""
    global _CACHED_CORK_TEXTURE
    if _CACHED_CORK_TEXTURE is not None and _CACHED_CORK_TEXTURE.shape == (height, width, 3):
        return _CACHED_CORK_TEXTURE.copy()

    # Seeded base cork color in BGR (warm tan cork: R=185, G=140, B=95)
    base_color = np.array([95, 140, 185], dtype=np.float32)
    cork = np.zeros((height, width, 3), dtype=np.float32)
    cork[:] = base_color

    # Add multi-octave noise to simulate real cork granules
    np.random.seed(1983)
    noise_fine = np.random.normal(0, 18, (height, width, 3))
    noise_coarse = cv2.resize(
        np.random.normal(0, 24, (height // 4, width // 4, 3)).astype(np.float32),
        (width, height),
        interpolation=cv2.INTER_LINEAR,
    )
    # Dark inclusions (cork flecks)
    flecks = (np.random.uniform(0, 1, (height, width, 1)) > 0.985).astype(np.float32) * -45.0

    cork = np.clip(cork + noise_fine + noise_coarse + flecks, 0, 255).astype(np.uint8)

    # Add dark wood frame border (outer 25px)
    frame_th = 26
    cork[:frame_th, :] = [30, 45, 65]
    cork[-frame_th:, :] = [25, 38, 55]
    cork[:, :frame_th] = [28, 42, 60]
    cork[:, -frame_th:] = [24, 36, 52]

    # Inner bevel shadow
    cv2.rectangle(cork, (frame_th, frame_th), (width - frame_th, height - frame_th), (15, 20, 30), 2)
    _CACHED_CORK_TEXTURE = cork
    return _CACHED_CORK_TEXTURE.copy()


def render_corkboard_scene(
    dto: NetflixInvestigativeSceneDTO,
    progress: float,
    width: int = 1920,
    height: int = 1080,
) -> np.ndarray:
    """Renders the forensic conspiracy corkboard with pinned evidence and red strings."""
    cork = generate_procedural_cork_texture(width, height)
    pil_canvas = Image.fromarray(cv2.cvtColor(cork, cv2.COLOR_BGR2RGB))

    # Pre-calculate positions of pinned items to link red strings
    item_centers: Dict[str, Tuple[int, int]] = {}

    # 1. Render Shadow Layer for items first
    shadow_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_img)

    for item in dto.corkboard_items:
        ix, iy = item.position_xy
        item_centers[item.item_id] = (ix, iy)
        # Shadow footprint
        card_w, card_h = (320, 380) if item.item_type == "photo" else (280, 220)
        sx, sy = ix - card_w // 2 + 12, iy - card_h // 2 + 16
        shadow_draw.rectangle([sx, sy, sx + card_w, sy + card_h], fill=(0, 0, 0, 120))

    shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(10))
    pil_canvas.paste(shadow_img, (0, 0), shadow_img)

    # 2. Render Red Yarn / Strings (Bezier splines) linking pins
    string_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    string_draw = ImageDraw.Draw(string_img)

    for conn in dto.red_strings:
        p1 = item_centers.get(conn.from_item_id)
        p2 = item_centers.get(conn.to_item_id)
        if not p1 or not p2:
            continue

        # Compute catenary sag point
        mid_x = (p1[0] + p2[0]) // 2
        mid_y = (p1[1] + p2[1]) // 2 + int(math.hypot(p2[0] - p1[0], p2[1] - p1[1]) * conn.sag_factor)

        # Draw red string shadow first
        if conn.has_shadow:
            string_draw.line([p1[0] + 6, p1[1] + 12, mid_x + 6, mid_y + 16, p2[0] + 6, p2[1] + 12], fill=(20, 10, 5, 110), width=3)
        # Draw main red string
        string_draw.line([p1[0], p1[1], mid_x, mid_y, p2[0], p2[1]], fill=(220, 38, 38, 240), width=3)

    pil_canvas.paste(string_img, (0, 0), string_img)

    # 3. Render Evidence Items (Photos, Maps, Notes)
    draw = ImageDraw.Draw(pil_canvas)
    bold_font = get_system_font(18, bold=True)
    note_font = get_system_font(20, bold=False)

    for item in dto.corkboard_items:
        ix, iy = item.position_xy
        card_w, card_h = (320, 380) if item.item_type == "photo" else (280, 220)
        x1, y1 = ix - card_w // 2, iy - card_h // 2
        x2, y2 = x1 + card_w, y1 + card_h

        if item.item_type == "photo":
            # Polaroid-style photo card
            draw.rectangle([x1, y1, x2, y2], fill=(245, 242, 235), outline=(180, 175, 165), width=2)
            # Image interior
            img_interior_x1 = x1 + 18
            img_interior_y1 = y1 + 18
            img_interior_x2 = x2 - 18
            img_interior_y2 = y2 - 70

            # If real image provided, load and fit
            loaded_img = None
            if item.image_path and Path(item.image_path).is_file():
                try:
                    loaded_img = Image.open(item.image_path).convert("RGB")
                    loaded_img = loaded_img.resize((img_interior_x2 - img_interior_x1, img_interior_y2 - img_interior_y1))
                    pil_canvas.paste(loaded_img, (img_interior_x1, img_interior_y1))
                except Exception:
                    loaded_img = None

            if loaded_img is None:
                draw.rectangle([img_interior_x1, img_interior_y1, img_interior_x2, img_interior_y2], fill=(45, 42, 40))
                draw.text((img_interior_x1 + 20, img_interior_y1 + 100), "ARCHIVE EVIDENCE", fill=(200, 200, 200), font=bold_font)

            # Handwritten label underneath
            draw.text((x1 + 22, y2 - 50), item.title.upper(), fill=(20, 20, 20), font=bold_font)

        elif item.item_type == "map":
            # Tactical Map snippet
            draw.rectangle([x1, y1, x2, y2], fill=(235, 230, 215), outline=(160, 150, 135), width=2)
            # Grid lines
            for gx in range(x1 + 20, x2, 40):
                draw.line([(gx, y1), (gx, y2)], fill=(200, 190, 175), width=1)
            for gy in range(y1 + 20, y2, 40):
                draw.line([(x1, gy), (x2, gy)], fill=(200, 190, 175), width=1)
            # Route line & Target circle
            draw.line([x1 + 40, y1 + 60, ix, iy, x2 - 40, y2 - 50], fill=(220, 38, 38), width=3)
            draw.ellipse([ix - 16, iy - 16, ix + 16, iy + 16], outline=(220, 38, 38), width=3)
            draw.text((x1 + 20, y2 - 35), item.title.upper(), fill=(180, 20, 20), font=bold_font)

        else:
            # Sticky Note / Index Card (Yellow or Aged White)
            fill_col = (254, 240, 138) if "CHECK" in item.title else (255, 250, 240)
            draw.rectangle([x1, y1, x2, y2], fill=fill_col, outline=(210, 190, 120), width=1)
            draw.text((x1 + 16, y1 + 18), item.title.upper(), fill=(140, 20, 20), font=bold_font)
            txt = item.note_text or "EVIDENCE NOTE // VERIFIED"
            draw.text((x1 + 16, y1 + 60), txt, fill=(30, 30, 30), font=note_font)

        # 4. Realistic Pushpin (Pinhead with 3D specular highlight and shadow)
        pin_col = (220, 38, 38) if item.pin_color == "red" else (234, 179, 8)
        # Pin shadow
        draw.ellipse([ix + 3, y1 + 10, ix + 17, y1 + 24], fill=(20, 15, 10, 130))
        # Pin body
        draw.ellipse([ix - 8, y1 + 4, ix + 8, y1 + 20], fill=pin_col, outline=(60, 10, 10), width=1)
        # Specular shine
        draw.ellipse([ix - 5, y1 + 6, ix - 1, y1 + 10], fill=(255, 255, 255))

    # 4. Directional Warm Desk Lamp Illumination (Radial Spotlight Falloff)
    # Lamp positioned bottom-left radiating upwards
    final_np = np.array(pil_canvas).astype(np.float32)
    lx, ly = int(width * 0.15), int(height * 0.85)

    y_grid, x_grid = np.ogrid[:height, :width]
    dist_sq = (x_grid - lx) ** 2 + (y_grid - ly) ** 2
    max_r = width * 0.95
    lamp_falloff = np.clip(1.0 - (dist_sq / (max_r ** 2)), 0.0, 1.0) ** 1.8

    # Warm incandescent tint (R=1.25, G=1.12, B=0.90)
    warm_tint = np.zeros((height, width, 3), dtype=np.float32)
    warm_tint[:, :, 0] = lamp_falloff * 60.0   # Red
    warm_tint[:, :, 1] = lamp_falloff * 35.0   # Green
    warm_tint[:, :, 2] = -lamp_falloff * 15.0  # Blue

    # Vignette upper-right
    vignette = 1.0 - (np.sqrt(dist_sq) / max_r) * 0.45
    vignette = np.clip(vignette, 0.55, 1.0)[:, :, np.newaxis]

    final_np = np.clip((final_np * vignette) + warm_tint, 0, 255).astype(np.uint8)
    return cv2.cvtColor(final_np, cv2.COLOR_RGB2BGR)


# ═════════════════════════════════════════════════════════════════════════
# ARQUÉTIPO 2: TACTILE CLASSIFIED DOSSIER (Ref Imagens 2 & 3)
# ═════════════════════════════════════════════════════════════════════════

def render_tactile_dossier_scene(
    dto: NetflixInvestigativeSceneDTO,
    progress: float,
    width: int = 1920,
    height: int = 1080,
) -> np.ndarray:
    """Renders the weathered manila dossier folder with god rays, paperclip, and rubber stamp."""
    cfg = dto.dossier_config or DossierConfig()

    # 1. Dark rustic scratched wood background (Mahogany desk: BGR ~ [12, 16, 24])
    wood = np.zeros((height, width, 3), dtype=np.uint8)
    wood[:] = [14, 20, 28]

    # Add subtle wood grain
    np.random.seed(42)
    wood_grain = np.random.normal(0, 6, (height, width, 3)).astype(np.int16)
    wood = np.clip(wood.astype(np.int16) + wood_grain, 0, 255).astype(np.uint8)

    pil_canvas = Image.fromarray(cv2.cvtColor(wood, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_canvas)

    # 2. Folder Dimensions & Positioning (Centered, slight -2 deg rotation)
    folder_w, folder_h = 1380, 900
    fx1 = (width - folder_w) // 2
    fy1 = (height - folder_h) // 2 + 20
    fx2 = fx1 + folder_w
    fy2 = fy1 + folder_h

    # Folder Cast Shadow on dark wood
    shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow)
    s_draw.rectangle([fx1 + 18, fy1 + 22, fx2 + 18, fy2 + 22], fill=(0, 0, 0, 160))
    shadow = shadow.filter(ImageFilter.GaussianBlur(16))
    pil_canvas.paste(shadow, (0, 0), shadow)

    # 3. Manila Folder Cover (Aged tan cardstock: RGB ~ [196, 168, 128])
    draw = ImageDraw.Draw(pil_canvas)
    manila_fill = (194, 165, 125)
    draw.rectangle([fx1, fy1, fx2, fy2], fill=manila_fill, outline=(140, 115, 80), width=2)

    # Folder tab on the right side
    tab_w, tab_h = 50, 220
    tab_x = fx2 - 2
    tab_y = fy1 + 180
    draw.rectangle([tab_x, tab_y, tab_x + tab_w, tab_y + tab_h], fill=(180, 150, 110), outline=(130, 105, 75), width=2)

    # Peeking internal yellowed sheets on right edge
    draw.rectangle([fx2 - 15, fy1 + 60, fx2 + 15, fy2 - 60], fill=(240, 235, 215), outline=(170, 160, 140), width=1)

    # 4. Folder Edge Grunge & Creases
    grunge_overlay = Image.new("RGBA", (folder_w, folder_h), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(grunge_overlay)
    # Darkened edges
    g_draw.rectangle([0, 0, folder_w, folder_h], outline=(70, 50, 30, 80), width=24)
    # Simulated coffee stain ring
    cx, cy = int(folder_w * 0.72), int(folder_h * 0.35)
    g_draw.ellipse([cx - 70, cy - 70, cx + 70, cy + 70], outline=(100, 70, 40, 35), width=14)
    grunge_overlay = grunge_overlay.filter(ImageFilter.GaussianBlur(4))
    pil_canvas.paste(grunge_overlay, (fx1, fy1), grunge_overlay)

    # 5. Pinned / Paperclipped Historical Photo (Ref Imagem 2)
    photo_w, photo_h = 360, 440
    px = fx1 + folder_w - photo_w - 70
    py = fy1 + 55

    # Photo shadow
    draw.rectangle([px + 8, py + 10, px + photo_w + 8, py + photo_h + 10], fill=(50, 40, 30))
    # Photo white vintage border
    draw.rectangle([px, py, px + photo_w, py + photo_h], fill=(242, 238, 228), outline=(160, 150, 130), width=2)

    # Load archival photo if available
    photo_interior_x1 = px + 16
    photo_interior_y1 = py + 16
    photo_interior_x2 = px + photo_w - 16
    photo_interior_y2 = py + photo_h - 16

    loaded_broll = None
    photo_src = cfg.pinned_photo_path or (BROLL_DIR / f"scene_{dto.scene_id}.jpg")
    if photo_src and Path(photo_src).is_file():
        try:
            raw_p = Image.open(photo_src).convert("RGB")
            # Apply cold vintage B&W filter
            raw_p = raw_p.convert("L").convert("RGB")
            loaded_broll = raw_p.resize((photo_interior_x2 - photo_interior_x1, photo_interior_y2 - photo_interior_y1))
            pil_canvas.paste(loaded_broll, (photo_interior_x1, photo_interior_y1))
        except Exception:
            loaded_broll = None

    if loaded_broll is None:
        draw.rectangle([photo_interior_x1, photo_interior_y1, photo_interior_x2, photo_interior_y2], fill=(40, 40, 40))
        f_mid = get_system_font(18, bold=True)
        draw.text((photo_interior_x1 + 30, photo_interior_y1 + 180), "EVIDENCE PORTRAIT", fill=(210, 210, 210), font=f_mid)

    # Brass Paperclip over Photo
    clip_x = px + 45
    clip_y = py - 12
    # Clip shadow
    draw.rectangle([clip_x + 3, clip_y + 3, clip_x + 28, clip_y + 85], outline=(30, 25, 20, 140), width=3)
    # Metallic brass wire
    draw.rectangle([clip_x, clip_y, clip_x + 25, clip_y + 80], outline=(180, 130, 40), width=4)
    draw.rectangle([clip_x + 5, clip_y + 12, clip_x + 20, clip_y + 68], outline=(220, 180, 90), width=2)

    # 6. Typewriter Monospace Case Labels (Ref Imagem 2 & 3)
    title_font = get_system_font(22, bold=True)
    body_font = get_system_font(18, bold=False)
    draw.text((fx1 + 75, fy1 + 80), cfg.case_number.upper(), fill=(60, 50, 40), font=title_font)
    draw.text((fx1 + 75, fy1 + 115), f"SUBJECT: {cfg.subject_title.upper()}", fill=(75, 65, 55), font=body_font)

    # 7. Distressed Rubber Stamp (Ref Imagem 3: "INCIDENTE 17-B")
    stamp_x = fx1 + 75
    stamp_y = fy1 + 220
    stamp_w = 480
    stamp_h = 135

    # Red stamp double border with slight distress
    stamp_color = (175, 30, 30)
    draw.rectangle([stamp_x, stamp_y, stamp_x + stamp_w, stamp_y + stamp_h], outline=stamp_color, width=5)
    draw.rectangle([stamp_x + 6, stamp_y + 6, stamp_x + stamp_w - 6, stamp_y + stamp_h - 6], outline=stamp_color, width=2)

    big_stamp_font = get_system_font(48, bold=True)
    draw.text((stamp_x + 24, stamp_y + 35), cfg.stamp_headline.upper(), fill=stamp_color, font=big_stamp_font)

    # Handwritten cursive underline subtitle
    script_font = get_system_font(26, bold=False)
    draw.text((stamp_x + 30, stamp_y + stamp_h + 20), cfg.stamp_subtitle, fill=(40, 35, 30), font=script_font)
    draw.line([(stamp_x + 25, stamp_y + stamp_h + 58), (stamp_x + stamp_w - 60, stamp_y + stamp_h + 58)], fill=(40, 35, 30), width=2)

    # Vertical tab stamp on edge
    tab_font = get_system_font(16, bold=True)
    draw.text((tab_x + 12, tab_y + 40), "C\nO\nN\nF\nI\nD\nE\nN\nT\nI\nA\nL", fill=(160, 25, 25), font=tab_font)

    # 8. Volumetric Sunlight Beam (God Rays with Dust Particles)
    final_np = np.array(pil_canvas).astype(np.float32)

    if cfg.has_volumetric_light:
        global _CACHED_LIGHT_MASK
        if _CACHED_LIGHT_MASK is None or _CACHED_LIGHT_MASK.shape != (height, width):
            # Create diagonal beam mask (45 deg angle)
            light_mask = np.zeros((height, width), dtype=np.float32)
            # Angled beam from top-left to bottom-right
            for y in range(height):
                center_x = int(y * 0.95) + 380
                beam_radius = 420
                x1 = max(0, center_x - beam_radius)
                x2 = min(width, center_x + beam_radius)
                if x2 > x1:
                    xs = np.arange(x1, x2)
                    profile = 1.0 - ((xs - center_x) / beam_radius) ** 2
                    light_mask[y, x1:x2] = np.maximum(light_mask[y, x1:x2], profile * 0.45)
            _CACHED_LIGHT_MASK = cv2.GaussianBlur(light_mask, (101, 101), 0)

        light_mask = _CACHED_LIGHT_MASK

        # Add floating micro dust motes inside the beam
        if cfg.dust_motes_enabled:
            np.random.seed(1983 + int(progress * 30))
            num_motes = 60
            mote_xs = np.random.randint(0, width, num_motes)
            mote_ys = np.random.randint(0, height, num_motes)
            for mx, my in zip(mote_xs, mote_ys):
                if light_mask[my, mx] > 0.15:
                    cv2.circle(final_np, (mx, my), 2, (255, 245, 220), -1)

        # Apply volumetric sunlight warm wash
        beam_rgb = np.zeros((height, width, 3), dtype=np.float32)
        beam_rgb[:, :, 0] = light_mask * 90.0  # Warm Sunlight Red
        beam_rgb[:, :, 1] = light_mask * 75.0  # Sunlight Green
        beam_rgb[:, :, 2] = light_mask * 45.0  # Subtle Blue

        final_np = np.clip(final_np + beam_rgb, 0, 255).astype(np.uint8)
    else:
        final_np = final_np.astype(np.uint8)

    return cv2.cvtColor(final_np, cv2.COLOR_RGB2BGR)


# ═════════════════════════════════════════════════════════════════════════
# ARQUÉTIPO 3: NETFLIX OSINT DESKTOP (Ref Imagem 4)
# ═════════════════════════════════════════════════════════════════════════

def render_netflix_osint_desktop_scene(
    dto: NetflixInvestigativeSceneDTO,
    progress: float,
    width: int = 1920,
    height: int = 1080,
) -> np.ndarray:
    """Renders the cyber-investigation multi-window desktop with route maps and CRT scanlines."""
    # 1. Dark CRT Grid Canvas (Ref Imagem 4: Dark teal-black #071018)
    canvas = np.zeros((height, width, 3), dtype=np.uint8)
    canvas[:] = [24, 16, 7]  # BGR

    # Draw digital coordinate grid
    grid_col = (45, 32, 14)
    step = 60
    for x in range(0, width, step):
        cv2.line(canvas, (x, 0), (x, height), grid_col, 1)
    for y in range(0, height, step):
        cv2.line(canvas, (0, y), (width, y), grid_col, 1)

    pil_canvas = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_canvas)

    # 2. Netflix Red Logo in Top-Left (Ref Imagem 4)
    logo_font = get_system_font(42, bold=True)
    draw.text((45, 35), "N", fill=(229, 9, 20), font=logo_font)
    sub_logo = get_system_font(16, bold=True)
    draw.text((85, 52), "DOCUMENTARY // INVESTIGATION", fill=(140, 150, 165), font=sub_logo)

    # Default windows if none supplied
    windows = dto.osint_windows or [
        OSINTWindow(
            window_id="w_map",
            title="SATELLITE ROUTE TRACKING // MOSCOW SECTOR",
            window_type="map_route",
            rect=(120, 120, 800, 560),
            content_data={"route": "Oko Sat -> Serpukhov-15"},
            z_index=1,
        ),
        OSINTWindow(
            window_id="w_evidence",
            title="RADAR SURVEILLANCE // OKO SATELLITE",
            window_type="split_evidence",
            rect=(960, 200, 840, 720),
            content_data={"broll": True},
            z_index=2,
        ),
    ]

    # Sort windows by z-index
    windows = sorted(windows, key=lambda w: w.z_index)

    title_font = get_system_font(15, bold=True)
    data_font = get_system_font(18, bold=False)

    for win in windows:
        wx, wy, ww, wh = win.rect

        # Window Drop Shadow
        draw.rectangle([wx + 12, wy + 16, wx + ww + 12, wy + wh + 16], fill=(0, 0, 0))

        # Window Frame (macOS translucent dark glass)
        draw.rectangle([wx, wy, wx + ww, wy + wh], fill=(16, 24, 38), outline=(50, 70, 100), width=2)

        # Titlebar (Dark Header)
        th = 40
        draw.rectangle([wx, wy, wx + ww, wy + th], fill=(28, 40, 60), outline=(50, 70, 100), width=1)

        # macOS Traffic Light Buttons (Red, Yellow, Green dots)
        draw.ellipse([wx + 16, wy + 14, wx + 28, wy + 26], fill=(239, 68, 68))   # Red
        draw.ellipse([wx + 36, wy + 14, wx + 48, wy + 26], fill=(245, 158, 11))  # Yellow
        draw.ellipse([wx + 56, wy + 14, wx + 68, wy + 26], fill=(16, 185, 129))  # Green

        # Search / Window Title Address Bar
        bar_x1 = wx + 85
        bar_x2 = wx + ww - 20
        draw.rectangle([bar_x1, wy + 8, bar_x2, wy + th - 8], fill=(12, 18, 30), outline=(60, 80, 110), width=1)
        draw.text((bar_x1 + 12, wy + 11), f"search://{win.title.lower()}", fill=(160, 180, 210), font=title_font)

        # Window Interior
        cx1 = wx + 12
        cy1 = wy + th + 12
        cx2 = wx + ww - 12
        cy2 = wy + wh - 12

        if win.window_type == "map_route":
            # Digital vector satellite map
            draw.rectangle([cx1, cy1, cx2, cy2], fill=(24, 32, 45))
            # Grid
            for mx in range(cx1 + 40, cx2, 60):
                draw.line([(mx, cy1), (mx, cy2)], fill=(35, 48, 68), width=1)
            for my in range(cy1 + 40, cy2, 60):
                draw.line([(cx1, my), (cx2, my)], fill=(35, 48, 68), width=1)

            # Route line with animated drawing progress
            pts = [
                (cx1 + 60, cy1 + 120),
                (cx1 + 220, cy1 + 180),
                (cx1 + 380, cy1 + 140),
                (cx1 + 540, cy1 + 280),
                (cx2 - 80, cy2 - 100),
            ]
            num_pts = max(2, int(len(pts) * min(1.0, progress * 1.4)))
            for i in range(num_pts - 1):
                draw.line([pts[i], pts[i + 1]], fill=(56, 189, 248), width=3)

            # Red target pin
            target_pt = pts[num_pts - 1]
            draw.ellipse([target_pt[0] - 12, target_pt[1] - 12, target_pt[0] + 12, target_pt[1] + 12], fill=(239, 68, 68))
            draw.ellipse([target_pt[0] - 24, target_pt[1] - 24, target_pt[0] + 24, target_pt[1] + 24], outline=(239, 68, 68), width=2)
            draw.text((cx1 + 20, cy2 - 40), "TARGET: SERPUKHOV-15 [ACTIVE]", fill=(56, 189, 248), font=title_font)

        elif win.window_type == "split_evidence":
            # Forensic split-screen window
            half_w = (cx2 - cx1) // 2
            # Left half: historical photo
            draw.rectangle([cx1, cy1, cx1 + half_w - 6, cy2], fill=(20, 25, 35))
            # Right half: CRT wireframe vector
            draw.rectangle([cx1 + half_w + 6, cy1, cx2, cy2], fill=(10, 20, 15))

            photo_src = BROLL_DIR / f"scene_{dto.scene_id}.jpg"
            if photo_src.is_file():
                try:
                    raw_broll = Image.open(photo_src).convert("RGB")
                    raw_broll = raw_broll.resize((half_w - 6, cy2 - cy1))
                    pil_canvas.paste(raw_broll, (cx1, cy1))
                except Exception:
                    pass

            # CRT Radar wireframe on right side
            radar_cx = cx1 + half_w + 6 + half_w // 2
            radar_cy = cy1 + (cy2 - cy1) // 2
            for rad in [60, 120, 180]:
                draw.ellipse([radar_cx - rad, radar_cy - rad, radar_cx + rad, radar_cy + rad], outline=(34, 197, 94), width=1)
            draw.line([(radar_cx - 190, radar_cy), (radar_cx + 190, radar_cy)], fill=(34, 197, 94), width=1)
            draw.line([(radar_cx, radar_cy - 190), (radar_cx, radar_cy + 190)], fill=(34, 197, 94), width=1)

            # Scanning sweep line
            angle = progress * math.pi * 4.0
            sweep_x = int(radar_cx + 180 * math.cos(angle))
            sweep_y = int(radar_cy + 180 * math.sin(angle))
            draw.line([(radar_cx, radar_cy), (sweep_x, sweep_y)], fill=(74, 222, 128), width=2)
            draw.text((cx1 + half_w + 20, cy2 - 35), "CRT TELEMETRY // 5 MISSILES IN FLIGHT", fill=(34, 197, 94), font=title_font)

        else:
            # Teletype Monospace Terminal
            draw.rectangle([cx1, cy1, cx2, cy2], fill=(8, 12, 18))
            draw.text((cx1 + 20, cy1 + 20), "KGB ARCHIVE DISPATCH // DECLASSIFIED", fill=(56, 189, 248), font=title_font)
            draw.text((cx1 + 20, cy1 + 60), "12:15:00 MSK - RADAR ANOMALY DETECTED", fill=(240, 240, 240), font=data_font)
            draw.text((cx1 + 20, cy1 + 95), "5 MINUTEMAN ICBMS CONFIRMED IN FLIGHT", fill=(239, 68, 68), font=data_font)

    # 3. Interactive Mouse Pointer Cursor (Ref Imagem 4)
    # Cursor gliding across screen
    cur_x = int(600 + 400 * progress)
    cur_y = int(450 + 150 * math.sin(progress * math.pi))
    draw.polygon([(cur_x, cur_y), (cur_x + 18, cur_y + 18), (cur_x + 8, cur_y + 20), (cur_x + 12, cur_y + 28), (cur_x + 6, cur_y + 30), (cur_x + 2, cur_y + 22), (cur_x - 4, cur_y + 26)], fill=(255, 255, 255), outline=(0, 0, 0))

    # 4. Subtle CRT Scanline Overlay
    final_np = np.array(pil_canvas)
    for y in range(0, height, 4):
        final_np[y, :, :] = (final_np[y, :, :].astype(np.float32) * 0.85).astype(np.uint8)

    return cv2.cvtColor(final_np, cv2.COLOR_RGB2BGR)


# ═════════════════════════════════════════════════════════════════════════
# MASTER CINETIC INVESTIGATIVE MOTION ENGINE
# ═════════════════════════════════════════════════════════════════════════

class NetflixInvestigativeMotionEngine:
    """Master engine orchestrating the 3 Netflix investigative motion archetypes."""

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
        self.sfx_manifest = self._load_sfx_manifest()

    def _load_sfx_manifest(self) -> Dict[str, List[str]]:
        """Loads sfx_manifest.json from 1,220 SFX library."""
        manifest_file = self.sfx_dir / "sfx_manifest.json"
        if manifest_file.is_file():
            try:
                with open(manifest_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not read SFX manifest: {e}")
        return {}

    def _get_sfx_path(self, category: str) -> Optional[Path]:
        """Resolves SFX path from library."""
        files = self.sfx_manifest.get(category, [])
        if files:
            p = PROJECT_ROOT / files[0]
            if p.is_file():
                return p
        cand = list(self.sfx_dir.glob(f"**/*{category}*.*"))
        if cand:
            return cand[0]
        return None

    def render_frame_for_scene(
        self,
        dto: NetflixInvestigativeSceneDTO,
        progress: float,
    ) -> np.ndarray:
        """Renders a single frame matching the specified investigative archetype."""
        if dto.archetype == MotionArchetype.CORKBOARD_CONSPIRACY:
            return render_corkboard_scene(dto, progress, width=self.width, height=self.height)
        elif dto.archetype == MotionArchetype.TACTILE_CLASSIFIED_DOSSIER:
            return render_tactile_dossier_scene(dto, progress, width=self.width, height=self.height)
        elif dto.archetype == MotionArchetype.NETFLIX_OSINT_DESKTOP:
            return render_netflix_osint_desktop_scene(dto, progress, width=self.width, height=self.height)
        else:
            raise ValueError(f"Unknown archetype: {dto.archetype}")

    def render_scene_clip(self, dto: NetflixInvestigativeSceneDTO) -> Path:
        """Renders complete 1080p MP4 clip with synchronized SFX and mirrors to broll."""
        out_mp4 = Path(dto.output_mp4_path) if dto.output_mp4_path else (self.output_dir / f"investigative_scene_{dto.scene_id}.mp4")
        out_mp4.parent.mkdir(parents=True, exist_ok=True)
        total_frames = int(dto.duration_sec * self.fps)
        ffmpeg_bin = get_ffmpeg_binary()

        temp_video = self.output_dir / f"temp_investigative_{dto.scene_id}.mp4"

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
            frame = self.render_frame_for_scene(dto, progress=prog)
            proc.stdin.write(frame.tobytes())

        proc.stdin.close()
        proc.wait()

        # Mux SFX
        whoosh_sfx = self._get_sfx_path("whooshes")
        stamp_sfx = self._get_sfx_path("stamp_slam") or self._get_sfx_path("sub_drops")

        if whoosh_sfx and stamp_sfx and temp_video.is_file():
            mux_cmd = [
                ffmpeg_bin,
                "-y",
                "-i", str(temp_video),
                "-i", str(whoosh_sfx),
                "-i", str(stamp_sfx),
                "-filter_complex",
                "[1:a]volume=0.35[a1];[2:a]adelay=900|900,volume=0.75[a2];[a1][a2]amix=inputs=2:duration=first[aout]",
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

        # Mirror to broll for master pipeline integration
        if dto.mirror_to_broll and out_mp4.is_file():
            broll_target = self.broll_dir / f"scene_{dto.scene_id}.mp4"
            shutil.copy2(out_mp4, broll_target)
            logger.info(f"✅ Mirrored investigative clip to B-roll: {broll_target.name}")

        logger.info(f"🎬 Rendered Netflix Investigative Scene {dto.scene_id}: {out_mp4.name} ({dto.archetype})")
        return out_mp4


def main() -> None:
    parser = argparse.ArgumentParser(description="DarkFactory Netflix-Grade Investigative Motion Engine")
    parser.add_argument("--scene", type=int, default=1, help="Scene ID to render")
    parser.add_argument("--archetype", type=str, default="TACTILE_CLASSIFIED_DOSSIER", choices=["CORKBOARD_CONSPIRACY", "TACTILE_CLASSIFIED_DOSSIER", "NETFLIX_OSINT_DESKTOP"])
    parser.add_argument("--duration", type=float, default=6.0, help="Duration in seconds (default: 6.0)")
    parser.add_argument("--fps", type=int, default=30, help="Frames per second (default: 30)")
    args = parser.parse_args()

    engine = NetflixInvestigativeMotionEngine(fps=args.fps)
    arch = MotionArchetype(args.archetype)

    dto = NetflixInvestigativeSceneDTO(
        scene_id=args.scene,
        archetype=arch,
        duration_sec=args.duration,
        dossier_config=DossierConfig(
            case_number="CASE FILE NO. 1983-SOVIET",
            subject_title="STANISLAV PETROV // SERPUKHOV-15",
            stamp_headline="INCIDENTE 17-B",
            stamp_subtitle="ARQUIVO DESCLASSIFICADO // CONFIDENCIAL",
        ),
        corkboard_items=[
            PinnedEvidenceItem(
                item_id="petrov",
                title="STANISLAV PETROV",
                item_type="photo",
                image_path=str(BROLL_DIR / f"scene_{args.scene}.jpg"),
                position_xy=(550, 480),
            ),
            PinnedEvidenceItem(
                item_id="radar_map",
                title="SERPUKHOV-15 RADAR",
                item_type="map",
                position_xy=(1050, 420),
            ),
            PinnedEvidenceItem(
                item_id="note_alibi",
                title="CHECK ALIBI",
                item_type="note",
                note_text="ONLY 5 MISSILES // PROTOCOL BROKEN",
                position_xy=(1450, 520),
            ),
        ],
        red_strings=[
            RedStringConnection(from_item_id="petrov", to_item_id="radar_map"),
            RedStringConnection(from_item_id="radar_map", to_item_id="note_alibi"),
        ],
        mirror_to_broll=True,
    )

    out = engine.render_scene_clip(dto)
    print(f"\n🎉 Successfully rendered Netflix Investigative Motion Clip: {out} ({arch})")


if __name__ == "__main__":
    main()
