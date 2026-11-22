"""DarkFactory Real Historical Archival Photo Ingestion.

Queries Wikimedia Commons, Wikipedia, and NASA APIs with resilient retry logic
to retrieve verified real historical photographs related to the 1983 Soviet Glitch
(Stanislav Petrov, Oko satellites, Serpukhov-15, early-warning radar arrays, and Cold War consoles).
Saves images to data/raw/historical_photos/ and stages them into data/broll/ for SeedVR 2.5 4K upscaling.
"""
from __future__ import annotations

import io
import json
import logging
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import List, Dict, Any

from PIL import Image

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("download_real_historical_photos")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_PHOTOS_DIR = DATA_DIR / "raw" / "historical_photos"
BROLL_DIR = DATA_DIR / "broll"

USER_AGENT = "DarkFactory/3.0 (https://darkfactory.ai; contact@darkfactory.ai) Python-urllib"

SEARCH_QUERIES = [
    "Stanislav Petrov",
    "Oko satellite",
    "Early warning radar",
    "Cold war bunker",
    "Intercontinental ballistic missile",
    "Soviet radar",
    "Spacecraft launch",
    "Satellite constellation",
    "Military command center",
    "Control room 1980s",
]


def robust_fetch(url: str, max_retries: int = 3, timeout: int = 15) -> bytes | None:
    """Fetch URL with retries on network/DNS glitches."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(1, max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as e:
            logger.warning(f"Fetch attempt {attempt}/{max_retries} for {url[:80]} failed: {e}")
            if attempt < max_retries:
                time.sleep(1.5 * attempt)
    return None


def query_wikimedia_images(query: str, limit: int = 4) -> List[Dict[str, str]]:
    """Query Wikimedia Commons API for image files matching the search term."""
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": f"{query} filetype:bitmap",
        "gsrlimit": str(limit),
        "prop": "imageinfo",
        "iiprop": "url|size|mime",
        "format": "json",
    }
    url = f"https://commons.wikimedia.org/w/api.php?{urllib.parse.urlencode(params)}"
    data_bytes = robust_fetch(url)
    if not data_bytes:
        return []

    results = []
    try:
        data = json.loads(data_bytes.decode("utf-8"))
        pages = (data.get("query") or {}).get("pages") or {}
        for page in pages.values():
            info_list = page.get("imageinfo") or []
            if not info_list:
                continue
            info = info_list[0]
            img_url = info.get("url")
            mime = info.get("mime", "")
            if img_url and ("image/jpeg" in mime or "image/png" in mime or "image/webp" in mime):
                results.append({
                    "title": page.get("title", ""),
                    "url": img_url,
                    "width": info.get("width", 0),
                    "height": info.get("height", 0),
                })
    except Exception as ex:
        logger.warning(f"Error parsing Wikimedia JSON: {ex}")

    return results


def query_nasa_images(query: str, limit: int = 4) -> List[Dict[str, str]]:
    """Query NASA Image and Video Library for public domain space/defense images."""
    params = {
        "q": query,
        "media_type": "image",
    }
    url = f"https://images-api.nasa.gov/search?{urllib.parse.urlencode(params)}"
    data_bytes = robust_fetch(url)
    if not data_bytes:
        return []

    results = []
    try:
        data = json.loads(data_bytes.decode("utf-8"))
        items = (data.get("collection") or {}).get("items") or []
        for item in items[:limit]:
            links = item.get("links") or []
            for link in links:
                if link.get("rel") == "preview" and link.get("href"):
                    results.append({
                        "title": ((item.get("data") or [{}])[0]).get("title", "NASA Asset"),
                        "url": link["href"],
                        "width": 1920,
                        "height": 1080,
                    })
                    break
    except Exception as ex:
        logger.warning(f"Error parsing NASA JSON: {ex}")

    return results


def download_and_verify(url: str, dest_path: Path) -> bool:
    """Download an image, verify and save as high-quality JPEG."""
    content = robust_fetch(url, max_retries=2, timeout=20)
    if not content:
        return False
    try:
        img = Image.open(io.BytesIO(content)).convert("RGB")
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(dest_path, "JPEG", quality=92)
        logger.info(f"Downloaded archival image ({img.width}x{img.height}) -> {dest_path.name}")
        return True
    except Exception as ex:
        logger.warning(f"Failed to process image from {url}: {ex}")
        return False


def main() -> int:
    RAW_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    BROLL_DIR.mkdir(parents=True, exist_ok=True)

    downloaded = []
    # 1. Query Wikimedia
    for query in SEARCH_QUERIES:
        logger.info(f"Searching Wikimedia for: '{query}'...")
        imgs = query_wikimedia_images(query, limit=3)
        for idx, item in enumerate(imgs):
            slug = re.sub(r"[^\w]", "_", query).lower()[:25]
            filename = f"wm_{slug}_{idx+1}.jpg"
            target_path = RAW_PHOTOS_DIR / filename
            if not target_path.exists():
                if download_and_verify(item["url"], target_path):
                    downloaded.append(target_path)
            else:
                downloaded.append(target_path)

    # 2. Query NASA
    nasa_queries = ["satellite orbit", "missile launch", "earth atmosphere space", "radar dish", "control room"]
    for query in nasa_queries:
        logger.info(f"Searching NASA for: '{query}'...")
        imgs = query_nasa_images(query, limit=3)
        for idx, item in enumerate(imgs):
            slug = re.sub(r"[^\w]", "_", query).lower()[:25]
            filename = f"nasa_{slug}_{idx+1}.jpg"
            target_path = RAW_PHOTOS_DIR / filename
            if not target_path.exists():
                if download_and_verify(item["url"], target_path):
                    downloaded.append(target_path)
            else:
                downloaded.append(target_path)

    logger.info(f"Total historical archival photos in pool: {len(downloaded)}")

    # Stage them into data/broll/ as scene_1.jpg ... scene_40.jpg
    if downloaded:
        import shutil
        for scene_id in range(1, 41):
            source_img = downloaded[(scene_id - 1) % len(downloaded)]
            scene_dest = BROLL_DIR / f"scene_{scene_id}.jpg"
            shutil.copy2(source_img, scene_dest)
        logger.info(f"Staged {len(downloaded)} historical photos across all 40 scenes in {BROLL_DIR}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
