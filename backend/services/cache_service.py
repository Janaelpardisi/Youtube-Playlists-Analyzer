import json
from pathlib import Path
from typing import List, Dict, Optional

DATA_DIR = Path(__file__).parent.parent.parent / "data"


def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_cache_path(session_id: str) -> Path:
    return DATA_DIR / f"{session_id}.json"


def save_results(session_id: str, videos: List[Dict]):
    """
    Saves video results to the session cache file.
    If a video already exists in the cache, it gets updated in place.
    New videos are simply appended.
    """
    _ensure_data_dir()
    cache_path = get_cache_path(session_id)

    if cache_path.exists():
        with open(cache_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
    else:
        existing = {"videos": []}

    existing_ids = {v["video_id"] for v in existing["videos"]}

    for video in videos:
        if video["video_id"] not in existing_ids:
            existing["videos"].append(video)
        else:
            for i, v in enumerate(existing["videos"]):
                if v["video_id"] == video["video_id"]:
                    existing["videos"][i] = video
                    break

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)


def load_results(session_id: str) -> List[Dict]:
    """Loads all cached results for a given session."""
    cache_path = get_cache_path(session_id)
    if not cache_path.exists():
        return []
    with open(cache_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("videos", [])


def get_analyzed_count(session_id: str) -> int:
    """Returns the number of videos that have been successfully analyzed."""
    results = load_results(session_id)
    return sum(1 for v in results if v.get("analyzed", False))


def is_video_analyzed(session_id: str, video_id: str) -> bool:
    """Checks if a specific video has already been analyzed in this session."""
    results = load_results(session_id)
    for v in results:
        if v["video_id"] == video_id and v.get("analyzed"):
            return True
    return False
