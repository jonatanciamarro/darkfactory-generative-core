#!/usr/bin/env python3
"""DarkFactory Motion Assets Pre-Synthesis Engine (Pipeline Step 3.5).

Pre-generates all vector motion graphics, tactical maps, CAD isometric blueprints,
4K archival upscaled stills, and tactical HUD overlays immediately after AI video takes:
1. Tactical Vector Maps: Offline GSAP/OpenCV map animations via MapAnimator.
2. CAD Isometric Blueprints & Dossiers: HyperFramesMotionEngine motion clips.
3. 4K Archival Photo Upscaling: SeedVR 2.5 4K enhancement via SeedVR25Upscaler.
4. Broadcast Tactical Graphics: High-DPI HUDs and classified stamps via TacticalGraphicsEngine.
5. Auto-populates data/final/motion_overlays/ and links to data/broll/ for instant video assembly.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Force UTF-8 encoding on Windows consoles (ADR-01)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("MotionAssetGenerator")

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
DATA_DIR = BASE_DIR / "data"
SCRIPTS_DIR = DATA_DIR / "scripts"
BROLL_DIR = DATA_DIR / "broll"
OUTPUT_DIR = DATA_DIR / "output"
MOTION_DIR = DATA_DIR / "final" / "motion_overlays"
MAPS_DIR = MOTION_DIR / "maps"
IMAGES_4K_DIR = DATA_DIR / "final" / "images_4k"


def resolve_script_path(specified_path: Optional[str] = None) -> Path:
    """Find the best screenplay manifest to process."""
    if specified_path:
        p = Path(specified_path).resolve()
        if p.is_file():
            return p

    candidates = [
        SCRIPTS_DIR / "pilot_soviet_glitch.json",
        SCRIPTS_DIR / "nolan_soviet_glitch.json",
        SCRIPTS_DIR / "nolan_soviet_glitch_teaser.json",
    ]
    for c in candidates:
        if c.is_file():
            return c

    all_found = list(SCRIPTS_DIR.glob("*soviet_glitch*.json"))
    if all_found:
        return all_found[0]

    raise FileNotFoundError("No screenplay manifest found in data/scripts/")


class MotionAssetPipeline:
    """Orchestrates pre-synthesis of motion graphics and tactical visual assets."""

    def __init__(
        self,
        output_dir: Optional[Path | str] = None,
        broll_dir: Optional[Path | str] = None,
        dry_run: bool = False,
        force: bool = False,
        enable_cinetic: bool = True,
        enable_argon: bool = True,
    ) -> None:
        self.output_dir = Path(output_dir).resolve() if output_dir else MOTION_DIR.resolve()
        self.broll_dir = Path(broll_dir).resolve() if broll_dir else BROLL_DIR.resolve()
        self.dry_run = dry_run
        self.force = force
        self.enable_cinetic = enable_cinetic
        self.enable_argon = enable_argon

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.broll_dir.mkdir(parents=True, exist_ok=True)
        MAPS_DIR.mkdir(parents=True, exist_ok=True)
        IMAGES_4K_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def generate_tactical_map_for_scene(
        self,
        scene: Dict[str, Any],
        duration_sec: float = 4.5,
    ) -> Optional[Path]:
        """Renders an animated tactical vector map for a scene."""
        scene_id = scene.get("scene_id", 1)
        map_out = MAPS_DIR / f"tactical_map_scene_{scene_id}.mp4"

        if map_out.is_file() and not self.force:
            logger.info(f"Tactical map for Scene {scene_id} already exists: {map_out.name}")
            return map_out

        try:
            from src.video.map_animator import MapAnimator, MapPin, MapRoute

            animator = MapAnimator(output_dir=MAPS_DIR)
            theater = "europe_cold_war"
            pins = [
                MapPin(label="SERPUKHOV-15", lat=54.91, lon=37.41, timestamp_sec=0.4, color_hex="#EF4444"),
                MapPin(label="MOSCOW", lat=55.75, lon=37.61, timestamp_sec=0.8, color_hex="#38BDF8"),
            ]
            routes = [
                MapRoute(origin_lat=47.5, origin_lon=-111.3, dest_lat=54.91, dest_lon=37.41, label="MINUTEMAN-III TRAJECTORY", color_hex="#F59E0B")
            ]

            title = scene.get("timestamp_marker", "TACTICAL TELEMETRY")
            subtitle = scene.get("hook_category", "THEATER OF OPERATIONS")

            res = animator.render_map_animation(
                title=title[:40],
                subtitle=subtitle[:50],
                theater=theater,
                pins=pins,
                routes=routes,
                duration_sec=duration_sec,
                width=1920,
                height=1080,
                fps=24,
            )

            if res.success and res.video_path and Path(res.video_path).is_file():
                # Copy or symlink to final map_out
                final_path = Path(res.video_path)
                logger.info(f"Generated tactical map video for Scene {scene_id}: {final_path.name}")
                return final_path
            else:
                logger.warning(f"Map render returned unsuccessful for Scene {scene_id}: {res.error}")
        except Exception as exc:
            logger.error(f"Failed to generate tactical map for Scene {scene_id}: {exc}")

        return None

    def generate_hyperframes_clip_for_scene(
        self,
        scene: Dict[str, Any],
        duration_sec: float = 5.0,
    ) -> Optional[Path]:
        """Renders an animated isometric CAD blueprint or declassified dossier."""
        scene_id = scene.get("scene_id", 1)
        style = scene.get("visual_style_type", "ANATOMY_ISOMETRIC")
        if style == "DECLASSIFIED_DOSSIER":
            template = "declassified_dossier"
        elif "blueprint" in style.lower():
            template = "blueprint_notebook"
        else:
            template = "anatomy_mechanical"

        clip_out = self.output_dir / f"hyperframes_scene_{scene_id}_{template}.mp4"
        if clip_out.is_file() and not self.force:
            logger.info(f"HyperFrames clip for Scene {scene_id} already exists: {clip_out.name}")
            return clip_out

        try:
            from src.video.hyperframes_engine import HyperFramesMotionEngine

            engine = HyperFramesMotionEngine(output_dir=self.output_dir)
            title = scene.get("timestamp_marker", "CLASSIFIED DOSSIER")
            subtitle = scene.get("act_title", "TACTICAL BLUEPRINT")

            res = engine.render_motion_clip(
                template=template,
                title=title[:38],
                subtitle=subtitle[:45],
                output_path=clip_out,
                duration_sec=duration_sec,
                width=1920,
                height=1080,
                fps=30,
                force_procedural=True,  # Fast offline deterministic render
                muted=True,
            )

            if res.success and res.output_video_path and Path(res.output_video_path).is_file():
                logger.info(f"Generated HyperFrames clip for Scene {scene_id}: {res.output_video_path.name}")
                return Path(res.output_video_path)
        except Exception as exc:
            logger.error(f"Failed to generate HyperFrames clip for Scene {scene_id}: {exc}")

        return None

    def generate_4k_archival_photo_for_scene(
        self,
        scene: Dict[str, Any],
    ) -> Optional[Path]:
        """Produces a 4K UHD upscaled historical photograph for Ken Burns camera moves."""
        scene_id = scene.get("scene_id", 1)
        target_4k = IMAGES_4K_DIR / f"scene_{scene_id}_archival_4k.jpg"

        if target_4k.is_file() and not self.force:
            logger.info(f"4K Archival photo for Scene {scene_id} already exists: {target_4k.name}")
            return target_4k

        # Locate base archival photo or create high-resolution source
        src_candidates = [
            self.broll_dir / f"scene_{scene_id}.jpg",
            self.broll_dir / f"scene_{scene_id}.png",
            self.broll_dir / f"cena_{scene_id}.jpg",
            DATA_DIR / "final" / f"scene_{scene_id}.jpg",
        ]
        base_src = next((p for p in src_candidates if p.is_file()), None)

        if not base_src:
            # Create a rich procedural historical plate as base
            base_src = self.broll_dir / f"scene_{scene_id}.jpg"
            try:
                from src.render_pilot_video import create_procedural_broll_image
                create_procedural_broll_image(
                    base_src,
                    scene_id=scene_id,
                    scene_title=scene.get("timestamp_marker", f"Historical Scene {scene_id}"),
                    scene_info=scene,
                )
            except Exception:
                import cv2
                import numpy as np
                dummy = np.full((1080, 1920, 3), 30, dtype=np.uint8)
                cv2.putText(dummy, f"ARCHIVAL PLATE {scene_id}", (100, 200), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (200, 200, 200), 3)
                cv2.imwrite(str(base_src), dummy)

        try:
            from src.factory.seedvr_upscaler import SeedVR25Upscaler

            upscaler = SeedVR25Upscaler(output_dir=IMAGES_4K_DIR)
            res = upscaler.upscale_image(
                input_image_path=base_src,
                output_image_path=target_4k,
                target_width=3840,
                target_height=2160,
                dry_run=self.dry_run,
                denoise=True,
                grain_strength=0.10,
            )

            if res.success and target_4k.is_file():
                logger.info(f"Generated 4K archival photo for Scene {scene_id}: {target_4k.name}")
                return target_4k
        except Exception as exc:
            logger.error(f"Failed to upscale archival photo for Scene {scene_id}: {exc}")

        return None

    def generate_tactical_overlay_stamp_for_scene(
        self,
        scene: Dict[str, Any],
    ) -> Optional[Path]:
        """Pre-renders PNG transparent tactical graphic overlay for a scene."""
        scene_id = scene.get("scene_id", 1)
        recipe = scene.get("overlay_recipe")
        if not recipe:
            return None

        out_png = self.output_dir / f"overlay_scene_{scene_id}.png"
        temp_out = OUTPUT_DIR / f"temp_overlay_{scene_id}.png"

        if out_png.is_file() and not self.force:
            return out_png

        try:
            from src.video.tactical_graphics import TacticalGraphicsEngine, LowerThirdData

            tg = TacticalGraphicsEngine(default_width=1920, default_height=1080)
            template = recipe.get("template", "tactical_hud")
            stamp_text = recipe.get("stamp_text", "TOP SECRET // DECLASSIFIED")

            if template == "declassified_dossier":
                tg.create_declassified_stamp_overlay(
                    output_png_path=out_png,
                    stamp_text=stamp_text,
                    sub_text=scene.get("timestamp_marker", "ARCHIVE ORDER NO. 49-B // EYES ONLY"),
                )
            elif template == "lower_third":
                ltd = recipe.get("lower_third_data", {})
                data = LowerThirdData(
                    title=ltd.get("title", f"SCENE {scene_id}"),
                    subtitle=ltd.get("subtitle", "HISTORICAL LOG"),
                    coordinates=ltd.get("coordinates", "55°45'06\"N 37°37'04\"E"),
                    date_timestamp=ltd.get("date_timestamp", "26 SEP 1983"),
                    classification=stamp_text,
                )
                tg.create_cinematic_lower_third(output_png_path=out_png, data=data)
            else:
                tg.create_tactical_hud_overlay(
                    output_png_path=out_png,
                    coordinates=recipe.get("coordinates", "54°54'57\"N 37°24'42\"E"),
                    target_name=scene.get("timestamp_marker", f"TARGET SCENE {scene_id}"),
                    warning_status=stamp_text,
                )

            if out_png.is_file():
                # Also keep temp_overlay in data/output/ for direct renderer compatibility
                shutil.copy2(out_png, temp_out)
                logger.info(f"Generated tactical overlay PNG for Scene {scene_id}: {out_png.name}")
                return out_png
        except Exception as exc:
            logger.error(f"Failed to generate tactical overlay for Scene {scene_id}: {exc}")

        return None

    def process_all_scenes(self, script_path: Path, limit: int = 0) -> Dict[str, Any]:
        """Iterates through all scenes in screenplay manifest and synthesizes required assets."""
        with open(script_path, "r", encoding="utf-8") as f:
            script_data = json.load(f)

        scenes: List[Dict[str, Any]] = script_data.get("scenes", [])
        if limit > 0:
            scenes = scenes[:limit]

        logger.info(
            f"🎬 Motion Asset Synthesis initiated for {len(scenes)} scenes "
            f"(script='{script_path.name}', dry_run={self.dry_run})"
        )

        results = {
            "maps_rendered": 0,
            "hyperframes_rendered": 0,
            "photos_4k_upscaled": 0,
            "overlays_rendered": 0,
            "cinetic_rendered": 0,
            "argon_rendered": 0,
            "scenes_processed": len(scenes),
        }

        for s in scenes:
            s_id = s.get("scene_id", 0)
            style = s.get("visual_style_type", "HERO_AI_DUAL_SHOT")
            dur = float(s.get("estimated_duration_sec", 6.0))

            # 1. Maps
            if style == "TACTICAL_MAP_MOTION":
                map_path = self.generate_tactical_map_for_scene(s, duration_sec=min(dur, 8.0))
                if map_path and map_path.is_file():
                    results["maps_rendered"] += 1
                    # Ensure renderer finds it in broll
                    target_broll = self.broll_dir / f"scene_{s_id}.mp4"
                    if not target_broll.exists() or self.force:
                        shutil.copy2(map_path, target_broll)

            # 2. Isometric blueprints & declassified dossiers
            elif style in ("ANATOMY_ISOMETRIC", "DECLASSIFIED_DOSSIER") or "blueprint" in style.lower():
                hf_path = self.generate_hyperframes_clip_for_scene(s, duration_sec=min(dur, 8.0))
                if hf_path and hf_path.is_file():
                    results["hyperframes_rendered"] += 1
                    target_broll = self.broll_dir / f"scene_{s_id}.mp4"
                    if not target_broll.exists() or self.force:
                        shutil.copy2(hf_path, target_broll)

            # 3. Archival Stills 4K Upscale
            elif style == "ARCHIVAL_KEN_BURNS" or "archival" in style.lower():
                img_path = self.generate_4k_archival_photo_for_scene(s)
                if img_path and img_path.is_file():
                    results["photos_4k_upscaled"] += 1
                    target_broll_img = self.broll_dir / f"scene_{s_id}.jpg"
                    if not target_broll_img.exists() or self.force:
                        shutil.copy2(img_path, target_broll_img)

            # 4. Overlays (stamps, HUDs, lower-thirds)
            if s.get("overlay_recipe"):
                ol_path = self.generate_tactical_overlay_stamp_for_scene(s)
                if ol_path and ol_path.is_file():
                    results["overlays_rendered"] += 1

            # 5. Netflix Investigative Documentary Motion Engine (3 Canonic Archetypes) - ALWAYS ON
            if self.enable_cinetic:
                target_broll = self.broll_dir / f"scene_{s_id}.mp4"
                if not target_broll.exists() or self.force:
                    try:
                        from src.video.netflix_investigative_motion import (
                            NetflixInvestigativeMotionEngine,
                            NetflixInvestigativeSceneDTO,
                            MotionArchetype,
                            DossierConfig,
                            PinnedEvidenceItem,
                            RedStringConnection,
                        )
                        inv_engine = NetflixInvestigativeMotionEngine(
                            broll_dir=self.broll_dir,
                            output_dir=self.output_dir,
                            sfx_dir=DATA_DIR / "sfx",
                        )
                        # Rotate through the 3 canonic archetypes
                        arch_idx = s_id % 3
                        if arch_idx == 1:
                            arch = MotionArchetype.TACTILE_CLASSIFIED_DOSSIER
                        elif arch_idx == 2:
                            arch = MotionArchetype.CORKBOARD_CONSPIRACY
                        else:
                            arch = MotionArchetype.NETFLIX_OSINT_DESKTOP

                        dto = NetflixInvestigativeSceneDTO(
                            scene_id=s_id,
                            archetype=arch,
                            duration_sec=dur,
                            dossier_config=DossierConfig(
                                case_number=f"CASE FILE NO. 1983-SOVIET // SCENE {s_id}",
                                subject_title=s.get("timestamp_marker", "SERPUKHOV-15 COMMAND"),
                                stamp_headline="INCIDENTE 1983-B",
                                stamp_subtitle="ARQUIVO DESCLASSIFICADO // CONFIDENCIAL",
                                pinned_photo_path=str(self.broll_dir / f"scene_{s_id}.jpg"),
                            ),
                            corkboard_items=[
                                PinnedEvidenceItem(
                                    item_id=f"photo_{s_id}",
                                    title=s.get("timestamp_marker", f"SCENE {s_id}"),
                                    item_type="photo",
                                    image_path=str(self.broll_dir / f"scene_{s_id}.jpg"),
                                    position_xy=(550, 480),
                                ),
                                PinnedEvidenceItem(
                                    item_id=f"map_{s_id}",
                                    title="TACTICAL RADAR",
                                    item_type="map",
                                    position_xy=(1050, 420),
                                ),
                                PinnedEvidenceItem(
                                    item_id=f"note_{s_id}",
                                    title="EVIDENCE NOTE",
                                    item_type="note",
                                    note_text="5 MISSILES IN FLIGHT // RETALIATION DELAY",
                                    position_xy=(1450, 520),
                                ),
                            ],
                            red_strings=[
                                RedStringConnection(from_item_id=f"photo_{s_id}", to_item_id=f"map_{s_id}"),
                                RedStringConnection(from_item_id=f"map_{s_id}", to_item_id=f"note_{s_id}"),
                            ],
                            mirror_to_broll=True,
                        )
                        c_path = inv_engine.render_scene_clip(dto)
                        if c_path and c_path.is_file():
                            results["cinetic_rendered"] += 1
                    except Exception as exc:
                        logger.warning(f"Netflix investigative motion skipped for scene {s_id}: {exc}")

            # 6. Gemini 4 Argon Swiss-Telemetry Motion Engine - ALWAYS ON
            if self.enable_argon:
                target_argon = self.output_dir / f"argon_scene_{s_id}.mp4"
                if not target_argon.exists() or self.force:
                    try:
                        from src.video.argon_documentary_motion import (
                            ArgonMotionEngine,
                            ArgonDocumentaryConfig,
                            ArgonMotionArchetype,
                        )
                        argon_engine = ArgonMotionEngine(
                            output_dir=self.output_dir,
                            broll_dir=self.broll_dir,
                        )
                        arch_map = [
                            ArgonMotionArchetype.RADAR_TELEMETRY,
                            ArgonMotionArchetype.ZSPACE_BUNKER_PARALLAX,
                            ArgonMotionArchetype.CLASSIFIED_DOSSIER_INVERSION,
                            ArgonMotionArchetype.NETFLIX_OSINT_STAGE,
                        ]
                        arch = arch_map[s_id % 4]
                        argon_cfg = ArgonDocumentaryConfig(
                            scene_id=s_id,
                            archetype=arch,
                            title=s.get("title") or s.get("timestamp_marker") or f"SCENE {s_id}",
                            subtitle=s.get("subtitle") or "SERPUKHOV-15 INCIDENT 1983",
                            narrative_thesis=s.get("narration_pt", "")[:120] if s.get("narration_pt") else "Cold War Early Warning Incident.",
                            telemetry_code=f"SERPUKHOV-15 // ACT {((s_id-1)//8)+1}",
                            metrics={"DEFCON": "1", "CONFIDENCE": "99.8%", "RADAR": "+4.82σ"},
                            archival_image_path=str(self.broll_dir / f"scene_{s_id}.jpg"),
                            duration_sec=dur,
                            fps=30,
                        )
                        a_res = argon_engine.render_scene_video(argon_cfg, output_path=target_argon, preview_only=self.dry_run)
                        if a_res.video_path.is_file():
                            results["argon_rendered"] += 1
                            # Mirror to broll for video assembler
                            broll_target = self.broll_dir / f"scene_{s_id}.mp4"
                            if not broll_target.exists() or self.force:
                                shutil.copy2(a_res.video_path, broll_target)
                    except Exception as exc:
                        logger.warning(f"Argon motion skipped for scene {s_id}: {exc}")

        logger.info(
            f"✅ Motion Asset Synthesis complete: "
            f"{results['maps_rendered']} maps, "
            f"{results['hyperframes_rendered']} blueprints, "
            f"{results['photos_4k_upscaled']} 4K stills, "
            f"{results['overlays_rendered']} overlays, "
            f"{results['cinetic_rendered']} cinetic motion clips, "
            f"{results['argon_rendered']} argon Swiss-telemetry clips."
        )
        return results


def main() -> None:
    parser = argparse.ArgumentParser(description="DarkFactory Motion Asset Generator (Step 6.5)")
    parser.add_argument("--script", type=str, default="", help="Path to screenplay JSON manifest")
    parser.add_argument("--output-dir", type=str, default="", help="Directory for motion overlays")
    parser.add_argument("--broll-dir", type=str, default="", help="Directory for B-roll clips")
    parser.add_argument("--dry-run", action="store_true", help="Simulate fast generation for testing")
    parser.add_argument("--force", action="store_true", help="Overwrite existing pre-rendered assets")
    parser.add_argument("--teaser", action="store_true", help="Only process the 3-scene teaser")
    parser.add_argument("--limit-scenes", type=int, default=0, help="Limit number of scenes (0 for all)")
    args = parser.parse_args()

    script_path = resolve_script_path(args.script)
    limit = 3 if args.teaser else args.limit_scenes

    pipeline = MotionAssetPipeline(
        output_dir=args.output_dir or MOTION_DIR,
        broll_dir=args.broll_dir or BROLL_DIR,
        dry_run=args.dry_run,
        force=args.force,
    )

    t0 = time.time()
    results = pipeline.process_all_scenes(script_path=script_path, limit=limit)
    elapsed = time.time() - t0

    print("\n" + "=" * 60)
    print("🎬 DARKFACTORY STEP 3.5: MOTION ASSETS & KINETIC VISUALS READY")
    print(f"   Screenplay: {script_path.name}")
    print(f"   Scenes Processed: {results['scenes_processed']}")
    print(f"   Tactical Maps: {results['maps_rendered']}")
    print(f"   HyperFrames Blueprints: {results['hyperframes_rendered']}")
    print(f"   4K Archival Photos: {results['photos_4k_upscaled']}")
    print(f"   Tactical Overlays: {results['overlays_rendered']}")
    print(f"   Elapsed Time: {elapsed:.2f}s")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
