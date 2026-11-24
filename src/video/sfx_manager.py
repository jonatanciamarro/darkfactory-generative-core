"""DarkFactory — Professional YouTube & Cinematic SFX Manager.

Provides Pydantic v2 data models, recursive catalog scanning, semantic tagging,
and fast search / retrieval for 1,200+ YouTube and cinematic sound effects.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import wave
from pathlib import Path

from pydantic import BaseModel, Field

# Reconfigure stdout/stderr to UTF-8 on Windows consoles (ADR-01)
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001, S110
        pass

logger = logging.getLogger("darkfactory.video.sfx_manager")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_SFX_DIR = BASE_DIR / "data" / "sfx"
MANIFEST_FILENAME = "sfx_manifest.json"

CATEGORY_KEYWORDS = {
    "cinematic": ["cinematic", "trailer fx", "epic", "dramatic"],
    "transition": ["whoosh", "swoosh", "swish", "transição", "transicao", "transicoes", "wipe"],
    "sub_drop": ["sub drop", "subdrop", "sub_drop", "sub bass", "low end", "drop"],
    "riser": ["riser", "tension swell", "sweep", "buildup"],
    "impact": ["hit", "impact", "slam", "boom", "strike"],
    "glitch": ["glitch", "static", "tape", "distortion", "noise", "error"],
    "hud_tech": ["hud", "tech", "interface", "digital", "button", "click", "teletype", "radar", "beep"],
    "horn": ["horn", "brass", "braam", "inception"],
    "foley_paper": ["paper", "dossier", "page", "stamp", "document", "sheet"],
    "camera": ["camera", "shutter", "flash", "photo", "snapshot"],
    "tension": ["tension", "horror", "countdown", "eerie", "drone"],
    "youtube_memes": ["meme", "famous", "bell", "coin", "coins"],
}


class SFXItem(BaseModel):
    """Data model for a single sound effect item in the DarkFactory library."""

    id: str
    name: str
    category: str = "general"
    subcategory: str = "general"
    relative_path: str
    format: str = "wav"
    duration_sec: float = 0.0
    sample_rate: int = 44100
    tags: list[str] = Field(default_factory=list)
    origin_pack: str = "unknown"
    absolute_path: str | None = None

    def matches(self, query: str) -> bool:
        """Check whether the item matches a search query against id, name, category, or tags."""
        q = (query or "").strip().lower()
        if not q:
            return True
        tokens = [t for t in re.split(r"\s+", q) if t]
        searchable_text = f"{self.id} {self.name} {self.category} {self.subcategory} {' '.join(self.tags)}".lower()
        return all(token in searchable_text for token in tokens)


class SFXCatalog(BaseModel):
    """Data model representing the entire indexed SFX catalog."""

    total_count: int = 0
    categories: dict[str, int] = Field(default_factory=dict)
    items: list[SFXItem] = Field(default_factory=list)


def _slugify(text: str) -> str:
    """Normalize text into safe identifier."""
    clean = re.sub(r"[^a-zA-Z0-9]+", "_", (text or "").strip().lower()).strip("_")
    return clean or "sfx"


def _safe_path_str(p: Path) -> str:
    """Return path with Windows extended-length prefix if on Windows."""
    resolved = str(p.resolve())
    if sys.platform.startswith("win") and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


class SFXManager:
    """Manages ingestion, manifest caching, and retrieval of sound effects."""

    def __init__(self, sfx_dir: Path | str | None = None) -> None:
        self.sfx_dir = Path(sfx_dir).resolve() if sfx_dir else DEFAULT_SFX_DIR.resolve()
        self.manifest_path = self.sfx_dir / MANIFEST_FILENAME
        self._catalog: SFXCatalog | None = None

    def _infer_category_and_tags(self, relative_path: str, filename: str) -> tuple[str, str, list[str]]:
        """Infer category, subcategory, and semantic tags from path and filename."""
        path_lower = relative_path.replace("\\", "/").lower()
        file_lower = filename.lower()
        full_context = f"{path_lower} {file_lower}"

        tags = set(re.findall(r"[a-zA-Z0-9]{3,}", full_context))

        assigned_category = "general"
        assigned_subcategory = "general"

        for cat, keywords in CATEGORY_KEYWORDS.items():
            if any(kw in full_context for kw in keywords):
                assigned_category = cat
                tags.add(cat)
                for kw in keywords:
                    if kw in full_context:
                        tags.add(_slugify(kw))
                break

        parts = path_lower.split("/")
        if len(parts) > 1:
            assigned_subcategory = _slugify(parts[-2])
        else:
            assigned_subcategory = _slugify(assigned_category)

        return assigned_category, assigned_subcategory, sorted(tags)

    def scan_and_build_manifest(self) -> SFXCatalog:
        """Scan directory recursively, register audio files, and write manifest JSON."""
        self.sfx_dir.mkdir(parents=True, exist_ok=True)
        items: list[SFXItem] = []
        categories: dict[str, int] = {}
        supported_exts = {".wav", ".mp3", ".ogg", ".flac"}

        for root, _, files in os.walk(self.sfx_dir):
            for file in sorted(files):
                ext = Path(file).suffix.lower()
                if ext not in supported_exts:
                    continue

                abs_file = Path(root) / file
                try:
                    rel_path = abs_file.relative_to(self.sfx_dir).as_posix()
                except Exception:  # noqa: BLE001
                    rel_path = abs_file.name

                category, subcategory, tags = self._infer_category_and_tags(rel_path, file)
                stem = abs_file.stem
                sfx_id = _slugify(f"{subcategory}_{stem}")

                # Determine origin pack
                origin_pack = "custom"
                if "fasteditor" in rel_path.lower():
                    origin_pack = "1000+UR.FASTEDITOR SFX"
                elif "sound_effects" in rel_path.lower() or "sound effects" in rel_path.lower():
                    origin_pack = "SOUND EFFECTS"

                duration = 0.0
                sr = 44100
                if ext == ".wav":
                    try:
                        with wave.open(_safe_path_str(abs_file), "rb") as wf:
                            sr = wf.getframerate()
                            frames = wf.getnframes()
                            duration = round(frames / float(sr), 3)
                    except Exception:  # noqa: BLE001
                        duration = 0.5
                else:
                    duration = 1.0

                item = SFXItem(
                    id=sfx_id,
                    name=stem,
                    category=category,
                    subcategory=subcategory,
                    relative_path=rel_path,
                    format=ext.lstrip("."),
                    duration_sec=duration,
                    sample_rate=sr,
                    tags=tags,
                    origin_pack=origin_pack,
                    absolute_path=abs_file.as_posix(),
                )
                items.append(item)
                categories[category] = categories.get(category, 0) + 1

        catalog = SFXCatalog(
            total_count=len(items),
            categories=categories,
            items=items,
        )

        with open(self.manifest_path, "w", encoding="utf-8") as f:
            f.write(catalog.model_dump_json(indent=2))

        self._catalog = catalog
        logger.info(f"Indexed {len(items)} SFX across {len(categories)} categories into {self.manifest_path}")
        return catalog

    def load_catalog(self, force_refresh: bool = False) -> SFXCatalog:
        """Load manifest from disk or scan if not present."""
        if self._catalog and not force_refresh:
            return self._catalog

        if self.manifest_path.is_file() and not force_refresh:
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._catalog = SFXCatalog.model_validate(data)
                return self._catalog
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Error loading {self.manifest_path}: {exc}. Rebuilding...")

        return self.scan_and_build_manifest()

    def search(
        self,
        query: str | None = None,
        category: str | None = None,
        limit: int = 50,
    ) -> list[SFXItem]:
        """Search sound effects by text query and/or category."""
        catalog = self.load_catalog()
        results: list[SFXItem] = []

        for item in catalog.items:
            if category and item.category != category and item.subcategory != category:
                continue
            if query and not item.matches(query):
                continue
            results.append(item)
            if len(results) >= limit:
                break

        return results

    def find_best_match(self, query: str, category: str | None = None) -> SFXItem | None:
        """Find the single most relevant SFX for a given query/keyword."""
        matches = self.search(query=query, category=category, limit=5)
        return matches[0] if matches else None

    def get_audio_path(self, item_or_id: SFXItem | str) -> Path | None:
        """Resolve absolute path to the audio file."""
        if isinstance(item_or_id, SFXItem):
            if item_or_id.absolute_path and Path(item_or_id.absolute_path).is_file():
                return Path(item_or_id.absolute_path)
            cand = self.sfx_dir / item_or_id.relative_path
            if cand.is_file():
                return cand
            gen_dir = self.sfx_dir / "generated_foley"
            if gen_dir.is_dir():
                for tag in item_or_id.tags:
                    if len(tag) > 3:
                        for f in sorted(gen_dir.glob("*.wav")):
                            if tag in f.stem.lower():
                                return f
            return None

        catalog = self.load_catalog()
        for item in catalog.items:
            if item.id == item_or_id:
                cand = self.sfx_dir / item.relative_path
                if cand.is_file():
                    return cand
                gen_dir = self.sfx_dir / "generated_foley"
                if gen_dir.is_dir():
                    for tag in item.tags:
                        if len(tag) > 3:
                            for f in sorted(gen_dir.glob("*.wav")):
                                if tag in f.stem.lower():
                                    return f
                return None
        return None
