import json
from pathlib import Path
from typing import List, Dict, Optional

DATA_DIR = Path(__file__).parent.parent.parent / "data"


def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_cache_path(session_id: str) -> Path:
    return DATA_DIR / f"{session_id}.json"


def save_results(session_id: str, videos: List[Dict]):
    """Save analyzed video results to cache file."""
    _ensure_data_dir()
    cache_path = get_cache_path(session_id)

    if cache_path.exists():
        with open(cache_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
    else:
        existing = {"videos": []}

    # Build a map of existing video IDs
    existing_ids = {v["video_id"] for v in existing["videos"]}

    for video in videos:
        if video["video_id"] not in existing_ids:
            existing["videos"].append(video)
        else:
            # Update existing entry
            for i, v in enumerate(existing["videos"]):
                if v["video_id"] == video["video_id"]:
                    existing["videos"][i] = video
                    break

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)


def load_results(session_id: str) -> List[Dict]:
    """Load all cached results for a session."""
    cache_path = get_cache_path(session_id)
    if not cache_path.exists():
        return []
    with open(cache_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("videos", [])


def get_analyzed_count(session_id: str) -> int:
    """Return how many videos have been analyzed."""
    results = load_results(session_id)
    return sum(1 for v in results if v.get("analyzed", False))


def is_video_analyzed(session_id: str, video_id: str) -> bool:
    """Check if a specific video has already been analyzed."""
    results = load_results(session_id)
    for v in results:
        if v["video_id"] == video_id and v.get("analyzed"):
            return True
    return False
