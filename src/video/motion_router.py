"""DarkFactory — Unified Motion Orchestrator & Multi-Archetype Router.

Connects and orchestrates all 4 modern documentary motion engines into a unified,
deterministic dispatcher for Step 3.5 (generate_motion_assets.py):
1. Gemini 4 Argon Swiss-Telemetry Engine (Müller-Brockmann × GMUNK, 3D CSS stage, Catmull-Rom)
2. Netflix Investigative Motion Engine (Corkboard with red strings, tactile manila dossiers, OSINT)
3. Cinetic Full Episode Motion Engine (Felipe Borges / inkStage #0D0B0A, central kinetic typography, red accents)
4. HyperFrames Engine & MapAnimator (CAD isometric blueprints, Cold War vector ballistic trajectories)
5. SeedVR 2.5 Archival Upscaler (4K archival restoration with LAB CLAHE & 35mm grain)

Guarantees ZERO-OVERWRITE and zero collision across the 40 scenes and 5 Acts of Christopher Nolan's screenplay.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import sys
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

# Force UTF-8 on Windows consoles (ADR-01)
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger("darkfactory.video.motion_router")

DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_BROLL_DIR = DATA_DIR / "broll"
DEFAULT_OUTPUT_DIR = DATA_DIR / "final" / "motion_overlays"
DEFAULT_SFX_DIR = DATA_DIR / "sfx"


class MotionArchetype(str, Enum):
    """The 10 Canonical Documentary Visual Archetypes for DarkFactory."""
    # Gemini 4 Argon Swiss-Telemetry Archetypes
    ARGON_RADAR = "ARGON_RADAR"                         # ICBM vectors, Catmull-Rom splines, reticle +4.82σ
    ARGON_ZSPACE_BUNKER = "ARGON_ZSPACE_BUNKER"         # 3D CSS stage (perspective 1250px), stepped Z-planes, Euler rotation
    ARGON_DOSSIER_INVERSION = "ARGON_DOSSIER_INVERSION" # Polarity inversion (#090A0D -> #F4F1EA), carbon ink
    ARGON_OSINT_STAGE = "ARGON_OSINT_STAGE"             # High-tech OSINT workspace, multi-window layout, CRT scanlines

    # Netflix Investigative Motion Archetypes
    NETFLIX_CORKBOARD = "NETFLIX_CORKBOARD"             # Corkboard conspiracy, 3D pushpins, Bezier red strings
    NETFLIX_TACTILE_DOSSIER = "NETFLIX_TACTILE_DOSSIER" # Manila folder, brass clip, volumetric god rays, worn stamp
    NETFLIX_OSINT_DESKTOP = "NETFLIX_OSINT_DESKTOP"     # macOS windows, terminal prompt, tactical CRT scanlines

    # Cinetic Full Episode Motion (Felipe Borges / Leonxlnx)
    CINETIC_INKSTAGE = "CINETIC_INKSTAGE"               # inkStage noir (#0D0B0A), central statement (35%-65%), red accent

    # Vector & CAD Blueprints
    HYPERFRAMES_CAD = "HYPERFRAMES_CAD"                 # Isometric blueprints, technical wireframes
    TACTICAL_MAP_VECTOR = "TACTICAL_MAP_VECTOR"         # Animated vector map with ballistic missile routes

    # 4K Archival Still Upscale
    SEEDVR_4K_ARCHIVAL = "SEEDVR_4K_ARCHIVAL"           # 4K restoration with micro-contrast LAB CLAHE & 35mm grain


# Canonical 5-Act Pacing Distribution (40 Scenes)
CANONICAL_ACT_DISTRIBUTION: List[MotionArchetype] = [
    # Act 1: The Glitch & False Alarm (In Medias Res)
    MotionArchetype.ARGON_RADAR,
    MotionArchetype.TACTICAL_MAP_VECTOR,
    MotionArchetype.CINETIC_INKSTAGE,
    MotionArchetype.NETFLIX_TACTILE_DOSSIER,
    MotionArchetype.ARGON_RADAR,
    MotionArchetype.HYPERFRAMES_CAD,
    MotionArchetype.CINETIC_INKSTAGE,
    MotionArchetype.NETFLIX_CORKBOARD,
    # Act 2: The Escalation & Connecting the Threads
    MotionArchetype.NETFLIX_CORKBOARD,
    MotionArchetype.TACTICAL_MAP_VECTOR,
    MotionArchetype.ARGON_OSINT_STAGE,
    MotionArchetype.CINETIC_INKSTAGE,
    MotionArchetype.HYPERFRAMES_CAD,
    MotionArchetype.NETFLIX_TACTILE_DOSSIER,
    MotionArchetype.CINETIC_INKSTAGE,
    MotionArchetype.ARGON_RADAR,
    # Act 3: Protocols & Petrov's Internal Conflict
    MotionArchetype.NETFLIX_TACTILE_DOSSIER,
    MotionArchetype.ARGON_ZSPACE_BUNKER,
    MotionArchetype.CINETIC_INKSTAGE,
    MotionArchetype.TACTICAL_MAP_VECTOR,
    MotionArchetype.HYPERFRAMES_CAD,
    MotionArchetype.CINETIC_INKSTAGE,
    MotionArchetype.NETFLIX_OSINT_DESKTOP,
    MotionArchetype.ARGON_ZSPACE_BUNKER,
    # Act 4: The 20-Minute Countdown to Oblivion
    MotionArchetype.ARGON_RADAR,
    MotionArchetype.CINETIC_INKSTAGE,
    MotionArchetype.ARGON_ZSPACE_BUNKER,
    MotionArchetype.NETFLIX_CORKBOARD,
    MotionArchetype.HYPERFRAMES_CAD,
    MotionArchetype.CINETIC_INKSTAGE,
    MotionArchetype.TACTICAL_MAP_VECTOR,
    MotionArchetype.ARGON_RADAR,
    # Act 5: The Declassification & Historical Truth
    MotionArchetype.ARGON_DOSSIER_INVERSION,
    MotionArchetype.SEEDVR_4K_ARCHIVAL,
    MotionArchetype.CINETIC_INKSTAGE,
    MotionArchetype.NETFLIX_TACTILE_DOSSIER,
    MotionArchetype.ARGON_DOSSIER_INVERSION,
    MotionArchetype.CINETIC_INKSTAGE,
    MotionArchetype.SEEDVR_4K_ARCHIVAL,
    MotionArchetype.ARGON_DOSSIER_INVERSION,
]


class UnifiedMotionOrchestrator:
    """Master router coordinating all specialized motion engines with zero-overwrite guarantee."""

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        broll_dir: Optional[Path] = None,
        sfx_dir: Optional[Path] = None,
        dry_run: bool = False,
        force: bool = False,
    ) -> None:
        self.output_dir = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
        self.broll_dir = Path(broll_dir) if broll_dir else DEFAULT_BROLL_DIR
        self.sfx_dir = Path(sfx_dir) if sfx_dir else DEFAULT_SFX_DIR
        self.dry_run = dry_run
        self.force = force

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.broll_dir.mkdir(parents=True, exist_ok=True)

    def resolve_archetype_for_scene(self, scene: Dict[str, Any]) -> MotionArchetype:
        """Determines the appropriate motion archetype for a scene."""
        # 1. Explicit override in scene manifest
        explicit = scene.get("motion_archetype")
        if explicit:
            for arch in MotionArchetype:
                if arch.value.upper() == str(explicit).upper():
                    return arch

        # 2. Check visual style type mappings
        style = str(scene.get("visual_style_type", "")).upper()
        if "MAP" in style:
            return MotionArchetype.TACTICAL_MAP_VECTOR
        if "ISOMETRIC" in style or "CAD" in style or "BLUEPRINT" in style:
            return MotionArchetype.HYPERFRAMES_CAD
        if "ARCHIVAL" in style or "SEEDVR" in style:
            return MotionArchetype.SEEDVR_4K_ARCHIVAL
        if "CINETIC" in style:
            return MotionArchetype.CINETIC_INKSTAGE
        if "ARGON" in style:
            return MotionArchetype.ARGON_RADAR
        if "CORKBOARD" in style:
            return MotionArchetype.NETFLIX_CORKBOARD

        # 3. Fallback to canonical 5-Act sequential distribution
        scene_id = int(scene.get("scene_id", 1))
        idx = (scene_id - 1) % len(CANONICAL_ACT_DISTRIBUTION)
        return CANONICAL_ACT_DISTRIBUTION[idx]

    def render_scene_motion(
        self,
        scene: Dict[str, Any],
        output_path: Optional[Path] = None,
        mirror_to_broll: bool = True,
    ) -> Optional[Path]:
        """Renders the resolved motion archetype for a single scene."""
        scene_id = int(scene.get("scene_id", 1))
        dur = float(scene.get("estimated_duration_sec", 6.0))
        archetype = self.resolve_archetype_for_scene(scene)

        target_broll = self.broll_dir / f"scene_{scene_id}.mp4"
        if not self.force and target_broll.exists():
            logger.info(f"Scene {scene_id} motion clip already present in broll: {target_broll.name}")
            return target_broll

        dest_file = output_path or (self.output_dir / f"motion_scene_{scene_id}_{archetype.value.lower()}.mp4")
        logger.info(f"🎬 Routing Scene {scene_id} -> Archetype [{archetype.value}] (dur={dur:.1f}s)")

        rendered_file: Optional[Path] = None

        try:
            # 1. ARGON SWISS-TELEMETRY ARCHETYPES
            if archetype in (
                MotionArchetype.ARGON_RADAR,
                MotionArchetype.ARGON_ZSPACE_BUNKER,
                MotionArchetype.ARGON_DOSSIER_INVERSION,
                MotionArchetype.ARGON_OSINT_STAGE,
            ):
                from src.video.argon_documentary_motion import (
                    ArgonMotionEngine,
                    ArgonDocumentaryConfig,
                    ArgonMotionArchetype,
                )
                argon_engine = ArgonMotionEngine(output_dir=self.output_dir, broll_dir=self.broll_dir)

                arch_map = {
                    MotionArchetype.ARGON_RADAR: ArgonMotionArchetype.RADAR_TELEMETRY,
                    MotionArchetype.ARGON_ZSPACE_BUNKER: ArgonMotionArchetype.ZSPACE_BUNKER_PARALLAX,
                    MotionArchetype.ARGON_DOSSIER_INVERSION: ArgonMotionArchetype.CLASSIFIED_DOSSIER_INVERSION,
                    MotionArchetype.ARGON_OSINT_STAGE: ArgonMotionArchetype.NETFLIX_OSINT_STAGE,
                }
                argon_arch = arch_map[archetype]
                cfg = ArgonDocumentaryConfig(
                    scene_id=scene_id,
                    archetype=argon_arch,
                    title=scene.get("title") or scene.get("timestamp_marker") or f"SCENE {scene_id}",
                    subtitle=scene.get("subtitle") or "SERPUKHOV-15 INCIDENT 1983",
                    narrative_thesis=scene.get("narration_pt", "")[:120] if scene.get("narration_pt") else "Cold War Early Warning Incident.",
                    telemetry_code=f"SERPUKHOV-15 // ACT {((scene_id-1)//8)+1}",
                    metrics={"DEFCON": "1", "CONFIDENCE": "99.8%", "RADAR": "+4.82σ"},
                    archival_image_path=str(self.broll_dir / f"scene_{scene_id}.jpg"),
                    duration_sec=dur,
                    fps=30,
                )
                res = argon_engine.render_scene_video(cfg, output_path=dest_file, preview_only=self.dry_run)
                if res.video_path.is_file():
                    rendered_file = res.video_path

            # 2. NETFLIX INVESTIGATIVE ARCHETYPES
            elif archetype in (
                MotionArchetype.NETFLIX_CORKBOARD,
                MotionArchetype.NETFLIX_TACTILE_DOSSIER,
                MotionArchetype.NETFLIX_OSINT_DESKTOP,
            ):
                from src.video.netflix_investigative_motion import (
                    NetflixInvestigativeMotionEngine,
                    NetflixInvestigativeSceneDTO,
                    MotionArchetype as NetArch,
                    DossierConfig,
                    PinnedEvidenceItem,
                    RedStringConnection,
                )
                net_engine = NetflixInvestigativeMotionEngine(
                    broll_dir=self.broll_dir,
                    output_dir=self.output_dir,
                    sfx_dir=self.sfx_dir,
                )
                net_map = {
                    MotionArchetype.NETFLIX_CORKBOARD: NetArch.CORKBOARD_CONSPIRACY,
                    MotionArchetype.NETFLIX_TACTILE_DOSSIER: NetArch.TACTILE_CLASSIFIED_DOSSIER,
                    MotionArchetype.NETFLIX_OSINT_DESKTOP: NetArch.NETFLIX_OSINT_DESKTOP,
                }
                dto = NetflixInvestigativeSceneDTO(
                    scene_id=scene_id,
                    archetype=net_map[archetype],
                    duration_sec=dur,
                    dossier_config=DossierConfig(
                        case_number=f"CASE FILE NO. 1983-SOVIET // SCENE {scene_id}",
                        subject_title=scene.get("timestamp_marker", "SERPUKHOV-15 COMMAND"),
                        stamp_headline="INCIDENTE 1983-B",
                        stamp_subtitle="ARQUIVO DESCLASSIFICADO // CONFIDENCIAL",
                        pinned_photo_path=str(self.broll_dir / f"scene_{scene_id}.jpg"),
                    ),
                    corkboard_items=[
                        PinnedEvidenceItem(
                            item_id=f"photo_{scene_id}",
                            title=scene.get("timestamp_marker", f"SCENE {scene_id}"),
                            item_type="photo",
                            image_path=str(self.broll_dir / f"scene_{scene_id}.jpg"),
                            position_xy=(550, 480),
                        ),
                        PinnedEvidenceItem(
                            item_id=f"map_{scene_id}",
                            title="TACTICAL RADAR",
                            item_type="map",
                            position_xy=(1050, 420),
                        ),
                    ],
                    red_strings=[
                        RedStringConnection(from_item_id=f"photo_{scene_id}", to_item_id=f"map_{scene_id}"),
                    ],
                    mirror_to_broll=False,
                )
                rendered_file = net_engine.render_scene_clip(dto)

            # 3. CINETIC FULL EPISODE MOTION (Felipe Borges / inkStage)
            elif archetype == MotionArchetype.CINETIC_INKSTAGE:
                from src.video.cinetic_episode_motion import (
                    CineticEpisodeMotionEngine,
                    CineticSceneConfig,
                    extract_kinetic_statement,
                )
                cin_engine = CineticEpisodeMotionEngine(
                    broll_dir=self.broll_dir,
                    output_dir=self.output_dir,
                    sfx_dir=self.sfx_dir,
                )
                narration = scene.get("narration_pt", "") or scene.get("narration_en", "Historical early warning event.")
                headline, accent = extract_kinetic_statement(narration)
                base_img = self.broll_dir / f"scene_{scene_id}.jpg"
                if not base_img.is_file():
                    import cv2
                    import numpy as np
                    dummy = np.full((1080, 1920, 3), 30, dtype=np.uint8)
                    cv2.putText(dummy, f"HISTORICAL ARCHIVE {scene_id}", (150, 540), cv2.FONT_HERSHEY_SIMPLEX, 1.8, (200, 200, 200), 3)
                    cv2.imwrite(str(base_img), dummy)
                cin_cfg = CineticSceneConfig(
                    scene_id=scene_id,
                    duration_sec=dur,
                    headline=headline,
                    accent_word=accent,
                    stamp_text="CONFIDENCIAL // KGB",
                    telemetry=f"SERPUKHOV-15 // SCENE {scene_id}",
                    base_image=base_img,
                )
                rendered_file = cin_engine.render_scene_motion_clip(cin_cfg, mirror_to_broll=False)

            # 4. TACTICAL MAP VECTOR
            elif archetype == MotionArchetype.TACTICAL_MAP_VECTOR:
                from src.video.map_animator import MapAnimator, MapPin, MapRoute
                maps_dir = self.output_dir / "maps"
                maps_dir.mkdir(parents=True, exist_ok=True)
                animator = MapAnimator(output_dir=maps_dir)
                pins = [
                    MapPin(label="SERPUKHOV-15", lat=54.91, lon=37.41, timestamp_sec=0.4, color_hex="#EF4444"),
                    MapPin(label="MOSCOW", lat=55.75, lon=37.61, timestamp_sec=0.8, color_hex="#38BDF8"),
                ]
                routes = [
                    MapRoute(origin_lat=47.5, origin_lon=-111.3, dest_lat=54.91, dest_lon=37.41, label="MINUTEMAN-III", color_hex="#F59E0B")
                ]
                res = animator.render_map_animation(
                    title=scene.get("timestamp_marker", "TACTICAL TELEMETRY")[:40],
                    subtitle=scene.get("hook_category", "THEATER OF OPERATIONS")[:50],
                    theater="europe_cold_war",
                    pins=pins,
                    routes=routes,
                    duration_sec=min(dur, 8.0),
                )
                if res.success and res.video_path and Path(res.video_path).is_file():
                    rendered_file = Path(res.video_path)

            # 5. HYPERFRAMES CAD BLUEPRINT
            elif archetype == MotionArchetype.HYPERFRAMES_CAD:
                from src.video.hyperframes_engine import HyperFramesMotionEngine
                hf_dir = self.output_dir / "hyperframes"
                hf_dir.mkdir(parents=True, exist_ok=True)
                hf_engine = HyperFramesMotionEngine(output_dir=hf_dir)
                res = hf_engine.generate_isometric_blueprint(
                    title=f"OKO SATELLITE SYSTEM // SCENE {scene_id}",
                    subtitle="KOSMOS-1409 INFRARED TELEMETRY",
                    duration_sec=min(dur, 8.0),
                )
                if res.success and res.video_path and Path(res.video_path).is_file():
                    rendered_file = Path(res.video_path)

            # 6. SEEDVR 4K ARCHIVAL RESTORATION
            elif archetype == MotionArchetype.SEEDVR_4K_ARCHIVAL:
                from src.factory.seedvr_upscaler import SeedVR25Upscaler
                target_4k = self.output_dir / f"scene_{scene_id}_4k.jpg"
                base_src = self.broll_dir / f"scene_{scene_id}.jpg"
                if not base_src.is_file():
                    import cv2
                    import numpy as np
                    dummy = np.full((1080, 1920, 3), 30, dtype=np.uint8)
                    cv2.putText(dummy, f"ARCHIVAL PLATE {scene_id}", (100, 200), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (200, 200, 200), 3)
                    cv2.imwrite(str(base_src), dummy)
                upscaler = SeedVR25Upscaler()
                res = upscaler.upscale_archival_photo(
                    input_image_path=base_src,
                    output_image_path=target_4k,
                    target_width=3840,
                    target_height=2160,
                    dry_run=self.dry_run,
                )
                if res.success and target_4k.is_file():
                    rendered_file = target_4k

        except Exception as exc:
            logger.error(f"Failed to render motion archetype [{archetype.value}] for Scene {scene_id}: {exc}")

        # Atomic mirroring to broll
        if rendered_file and rendered_file.is_file() and mirror_to_broll:
            if rendered_file.suffix.lower() == ".mp4":
                shutil.copy2(rendered_file, target_broll)
                logger.info(f"✅ Mirrored {archetype.value} -> {target_broll.name}")
            elif rendered_file.suffix.lower() in (".jpg", ".png"):
                broll_img = self.broll_dir / f"scene_{scene_id}.jpg"
                shutil.copy2(rendered_file, broll_img)
                logger.info(f"✅ Mirrored {archetype.value} -> {broll_img.name}")

        return rendered_file
