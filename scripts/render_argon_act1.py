#!/usr/bin/env python3
"""Render Act 1 test batch (Scenes 1-5) using the Gemini 4 Argon Swiss-Telemetry Motion Engine."""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.video.argon_documentary_motion import (
    ArgonMotionEngine,
    ArgonDocumentaryConfig,
    ArgonMotionArchetype,
)

SCENE_SPECS = [
    {
        "scene_id": 1,
        "archetype": ArgonMotionArchetype.RADAR_TELEMETRY,
        "title": "MISSILE ATTACK DETECTED",
        "subtitle": "5 ICBM LAUNCH VECTORS // MALMSTROM AFB",
        "narrative_thesis": "At 12:15 AM on September 26, 1983, a red siren illuminated a top-secret Soviet bunker. The early warning radar registered an American launch.",
        "telemetry_code": "SERPUKHOV-15 // 54.9158° N, 37.4116° E",
        "metrics": {"RADAR": "+4.82σ", "TIME_TO_IMPACT": "00:15:00 MSK", "STATUS": "CRITICAL"},
        "duration_sec": 4.0,
    },
    {
        "scene_id": 2,
        "archetype": ArgonMotionArchetype.ZSPACE_BUNKER_PARALLAX,
        "title": "STANISLAV PETROV",
        "subtitle": "DUTY OFFICER PSYCHE // GIMBAL 3D",
        "narrative_thesis": "Lt. Col. Stanislav Petrov sat in the commander's chair. His computer screen flashed: LAUNCH CONFIRMED.",
        "telemetry_code": "OKO SURVEILLANCE // DEFCON 1",
        "metrics": {"OFFICER": "PETROV.S", "CONFIDENCE": "99.8%", "ORBIT": "COSMOS-1374"},
        "duration_sec": 4.0,
    },
    {
        "scene_id": 3,
        "archetype": ArgonMotionArchetype.CLASSIFIED_DOSSIER_INVERSION,
        "title": "СОВЕРШЕННО СЕКРЕТНО",
        "subtitle": "DECLASSIFIED KREMLIN DISPATCH",
        "narrative_thesis": "A confidential post-incident report concealed for over a decade. Five false positive alarm triggers.",
        "telemetry_code": "DOSSIER 17-B // ARCHIVE",
        "metrics": {"CLEARANCE": "LEVEL 1", "CLASSIFICATION": "TOP SECRET", "STATUS": "EXCLUSIVO"},
        "duration_sec": 4.0,
    },
    {
        "scene_id": 4,
        "archetype": ArgonMotionArchetype.NETFLIX_OSINT_STAGE,
        "title": "POLAR ORBITAL TRACK",
        "subtitle": "OKO SATELLITE SUN-GLINT ANOMALY",
        "narrative_thesis": "Reconstructing the flight path of Cosmos 1374 and the rare alignment with high-altitude cirrus clouds.",
        "telemetry_code": "OSINT-OBSERVATORY // MALMSTROM AFB",
        "metrics": {"ORBIT": "MOLNIYA-1", "ALIGNMENT": "SUN-GLINT", "SAT": "COSMOS-1374"},
        "duration_sec": 4.0,
    },
    {
        "scene_id": 5,
        "archetype": ArgonMotionArchetype.RADAR_TELEMETRY,
        "title": "THE 20-MINUTE COUNTDOWN",
        "subtitle": "RETALIATION PROTOCOL SUSPENDED",
        "narrative_thesis": "Petrov had twenty minutes to decide whether to inform the General Staff and trigger World War Three.",
        "telemetry_code": "INTERCOM LOGS // PROTOCOL 01",
        "metrics": {"DECISION": "FALSE ALARM", "RETALIATION": "HELD", "WAR": "PREVENTED"},
        "duration_sec": 4.0,
    },
]

def main():
    engine = ArgonMotionEngine()
    print("🚀 Starting Gemini 4 Argon Swiss-Telemetry Render for Act 1 (Scenes 1-5)...")

    rendered = []
    for spec in SCENE_SPECS:
        sid = spec["scene_id"]
        cfg = ArgonDocumentaryConfig(
            scene_id=sid,
            archetype=spec["archetype"],
            title=spec["title"],
            subtitle=spec["subtitle"],
            narrative_thesis=spec["narrative_thesis"],
            telemetry_code=spec["telemetry_code"],
            metrics=spec["metrics"],
            archival_image_path=str(BASE_DIR / "data" / "broll" / f"scene_{sid}.jpg"),
            duration_sec=spec["duration_sec"],
            fps=30,
        )
        print(f"🎬 Rendering Scene {sid} [{spec['archetype'].value}]...")
        clip_path = engine.render_scene_clip(cfg)
        size_kb = clip_path.stat().st_size / 1024
        print(f"✅ Scene {sid} complete: {clip_path.name} ({size_kb:.1f} KB)")
        rendered.append((sid, clip_path))

    print(f"\n🎉 Successfully rendered {len(rendered)}/5 Argon scenes!")
    for sid, p in rendered:
        broll_p = BASE_DIR / "data" / "broll" / f"scene_{sid}.mp4"
        print(f"  - Scene {sid}: {p} -> {broll_p} (Exists: {broll_p.is_file()})")

if __name__ == "__main__":
    main()
