import os
import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent / "data"
SESSIONS_FILE = DATA_DIR / "sessions.json"


def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_sessions() -> Dict:
    _ensure_data_dir()
    if SESSIONS_FILE.exists():
        with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"sessions": []}


def _save_sessions(data: Dict):
    _ensure_data_dir()
    with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def create_session(channel_name: str, channel_id: str, playlist_name: str,
                   playlist_id: str, total_videos: int) -> str:
    """Create a new analysis session and return session_id."""
    data = _load_sessions()
    session_id = str(uuid.uuid4())[:8]

    session = {
        "session_id": session_id,
        "channel_name": channel_name,
        "channel_id": channel_id,
        "playlist_name": playlist_name,
        "playlist_id": playlist_id,
        "total_videos": total_videos,
        "analyzed_count": 0,
        "last_batch": 0,
        "last_updated": datetime.now().isoformat(),
        "status": "in_progress",
        "summary": None,
        "learning_path": None
    }

    data["sessions"].append(session)
    _save_sessions(data)
    return session_id


def update_session(session_id: str, analyzed_count: int, last_batch: int):
    """Update session progress after each batch."""
    data = _load_sessions()
    for session in data["sessions"]:
        if session["session_id"] == session_id:
            session["analyzed_count"] = analyzed_count
            session["last_batch"] = last_batch
            session["last_updated"] = datetime.now().isoformat()
            if analyzed_count >= session["total_videos"]:
                session["status"] = "completed"
            break
    _save_sessions(data)


def complete_session(session_id: str):
    """Mark session as completed."""
    data = _load_sessions()
    for session in data["sessions"]:
        if session["session_id"] == session_id:
            session["status"] = "completed"
            session["last_updated"] = datetime.now().isoformat()
            break
    _save_sessions(data)


# ── Feature 2 — Summary ──────────────────────

def save_session_summary(session_id: str, summary: str):
    """Save AI-generated playlist summary to session."""
    data = _load_sessions()
    for session in data["sessions"]:
        if session["session_id"] == session_id:
            session["summary"] = summary
            session["last_updated"] = datetime.now().isoformat()
            break
    _save_sessions(data)


def get_session_summary(session_id: str) -> Optional[str]:
    """Get saved summary for a session."""
    data = _load_sessions()
    for session in data["sessions"]:
        if session["session_id"] == session_id:
            return session.get("summary")
    return None


# ── Feature 3 — Learning Path ────────────────

def save_learning_path(session_id: str, learning_path: Dict):
    """Save AI-generated learning path to session."""
    data = _load_sessions()
    for session in data["sessions"]:
        if session["session_id"] == session_id:
            session["learning_path"] = learning_path
            session["last_updated"] = datetime.now().isoformat()
            break
    _save_sessions(data)


def get_learning_path(session_id: str) -> Optional[Dict]:
    """Get saved learning path for a session."""
    data = _load_sessions()
    for session in data["sessions"]:
        if session["session_id"] == session_id:
            return session.get("learning_path")
    return None


# ── General ──────────────────────────────────

def get_all_sessions() -> List[Dict]:
    """Get all sessions (both in_progress and completed)."""
    data = _load_sessions()
    return sorted(data["sessions"], key=lambda x: x["last_updated"], reverse=True)


def get_active_sessions() -> List[Dict]:
    """Get only in-progress sessions."""
    return [s for s in get_all_sessions() if s["status"] == "in_progress"]


def get_session(session_id: str) -> Optional[Dict]:
    """Get a specific session by ID."""
    data = _load_sessions()
    for session in data["sessions"]:
        if session["session_id"] == session_id:
            return session
    return None


def delete_session(session_id: str):
    """Delete a session."""
    data = _load_sessions()
    data["sessions"] = [s for s in data["sessions"] if s["session_id"] != session_id]
    _save_sessions(data)

    # Also delete cached results
    result_file = DATA_DIR / f"{session_id}.json"
    if result_file.exists():
        result_file.unlink()
