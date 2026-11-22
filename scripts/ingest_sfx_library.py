"""DarkFactory — Automated YouTube & Cinematic Sound Effects Ingestion.

Extracts, normalizes, and catalogs external sound effect libraries:
- 1000+UR.FASTEDITOR SFX.zip
- SOUND EFFECTS-20261122T060016Z-1-001.zip
Into data/sfx/ with full manifest indexing and nested archive unpacking.
"""

from __future__ import annotations

import argparse
import io
import logging
import os
import re
import sys
import zipfile
from pathlib import Path
from typing import List, Optional

# Reconfigure stdout/stderr to UTF-8 on Windows consoles (ADR-01)
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("darkfactory.ingest_sfx")

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

DEFAULT_TARGET_DIR = BASE_DIR / "data" / "sfx"

DEFAULT_SOURCES = [
    Path.home() / "Downloads" / "1000+UR.FASTEDITOR SFX.zip",
    Path.home() / "Downloads" / "SOUND EFFECTS-20261122T060016Z-1-001.zip",
    Path(r"C:\Users\Administrator\Downloads\1000+UR.FASTEDITOR SFX.zip"),
    Path(r"C:\Users\Administrator\Downloads\SOUND EFFECTS-20261122T060016Z-1-001.zip"),
    Path(r"C:\Users\WDAGUtilityAccount\Downloads\1000+UR.FASTEDITOR SFX.zip"),
    Path(r"C:\Users\WDAGUtilityAccount\Downloads\SOUND EFFECTS-20261122T060016Z-1-001.zip"),
]


def resolve_existing_sources(specified_sources: Optional[List[Path]] = None) -> List[Path]:
    """Resolve and deduplicate existing source zip archives."""
    if specified_sources:
        return [p for p in specified_sources if p.is_file()]

    found_by_name: dict[str, Path] = {}
    for candidate in DEFAULT_SOURCES:
        if candidate.is_file() and candidate.name not in found_by_name:
            found_by_name[candidate.name] = candidate

    return list(found_by_name.values())


def _sanitize_path_segment(seg: str) -> str:
    """Sanitize directory or file name segment for Windows compatibility."""
    cleaned = re.sub(r'[<>:"/\\|?*]', "_", seg).strip()
    return cleaned or "item"


def _safe_open_path(p: Path) -> str:
    """Return path with Windows extended-length prefix if on Windows."""
    resolved = str(p.resolve())
    if sys.platform.startswith("win") and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def extract_zip_safely(zip_path: Path, destination: Path) -> int:
    """Extract all files from zip_path to destination, returning file count."""
    if not zip_path.is_file():
        logger.error(f"Archive not found: {zip_path}")
        return 0

    destination.mkdir(parents=True, exist_ok=True)
    count = 0

    logger.info(f"Extracting {zip_path.name} to {destination}...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            if member.is_dir():
                continue

            raw_path = member.filename.replace("\\", "/")
            parts = [_sanitize_path_segment(p) for p in raw_path.split("/") if p]
            if not parts:
                continue

            # Strip redundant top-level container folders if present
            if len(parts) > 1 and parts[0].lower() in (
                "1000_ur.fasteditor sfx",
                "1000+ur.fasteditor sfx",
                "sound effects",
                "sound_effects",
            ):
                parts = parts[1:]

            target_path = destination.joinpath(*parts)
            safe_target = _safe_open_path(target_path)
            Path(target_path.parent).mkdir(parents=True, exist_ok=True)

            with zf.open(member) as src, open(safe_target, "wb") as dst:
                dst.write(src.read())
            count += 1

    logger.info(f"Extracted {count} files from {zip_path.name}")
    return count


def unpack_nested_zips(target_dir: Path) -> int:
    """Scan directory recursively for any .zip files, extract them and remove the zip."""
    unpacked_count = 0
    nested_zips = list(target_dir.rglob("*.zip"))
    for nz in nested_zips:
        logger.info(f"Unpacking nested archive: {nz.relative_to(target_dir)}")
        dest = nz.parent
        try:
            with zipfile.ZipFile(str(nz), "r") as zf:
                for member in zf.infolist():
                    if member.is_dir():
                        continue
                    raw_parts = [_sanitize_path_segment(p) for p in member.filename.replace("\\", "/").split("/") if p]
                    dest_path = dest.joinpath(*raw_parts)
                    safe_dest = _safe_open_path(dest_path)
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as src, open(safe_dest, "wb") as dst:
                        dst.write(src.read())
                    unpacked_count += 1
            nz.unlink(missing_ok=True)
        except Exception as exc:
            logger.warning(f"Failed to unpack nested zip {nz}: {exc}")
    return unpacked_count


def ingest_sfx_libraries(
    sources: Optional[List[Path]] = None,
    target_dir: Optional[Path] = None,
    force_reextract: bool = False,
) -> dict:
    """End-to-end ingestion of sound effect zip libraries into target_dir."""
    target = target_dir or DEFAULT_TARGET_DIR
    source_list = resolve_existing_sources(sources)

    if not source_list:
        logger.warning("No SFX zip archives found in default download locations or specified sources.")

    total_extracted = 0
    for src in source_list:
        sub_folder = "fasteditor" if "fasteditor" in src.name.lower() else "sound_effects"
        dest_folder = target / sub_folder
        if not force_reextract and dest_folder.is_dir() and any(dest_folder.iterdir()):
            logger.info(f"Target directory {dest_folder} already populated. Skipping re-extraction.")
        else:
            total_extracted += extract_zip_safely(src, dest_folder)

    nested_count = unpack_nested_zips(target)
    logger.info(f"Unpacked {nested_count} files from nested archives.")

    # Re-index with SFXManager
    from src.video.sfx_manager import SFXManager

    manager = SFXManager(sfx_dir=target)
    catalog = manager.scan_and_build_manifest()

    result = {
        "success": True,
        "total_extracted": total_extracted,
        "nested_unpacked": nested_count,
        "catalog_total": catalog.total_count,
        "categories": catalog.categories,
        "manifest_path": manager.manifest_path.as_posix(),
    }
    logger.info(f"Ingestion Complete: {catalog.total_count} effects cataloged in {manager.manifest_path}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest YouTube & Cinematic SFX libraries into DarkFactory.")
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET_DIR, help="Destination directory for SFX")
    parser.add_argument("--force", action="store_true", help="Force re-extraction even if target directory is populated")
    args = parser.parse_args()

    res = ingest_sfx_libraries(target_dir=args.target, force_reextract=args.force)
    print(f"Status: SUCCESS | Total SFX: {res['catalog_total']} | Categories: {list(res['categories'].keys())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
