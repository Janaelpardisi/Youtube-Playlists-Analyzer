import os
import re
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from backend.models.schemas import (
    ChannelSearchRequest, BatchAnalyzeRequest, SessionInfo,
    ChatRequest, ChatResponse, CompareRequest
)
from backend.services import youtube_service, gemini_service, cache_service, memory_service

app = FastAPI(title="YouTube Playlist Analyzer", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
STATIC_DIR = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def root():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


# ── Sessions ───────────────────────────────────────────────────────────────────


@app.get("/api/sessions")
def get_sessions():
    return {"sessions": memory_service.get_all_sessions()}


@app.get("/api/sessions/active")
def get_active_sessions():
    return {"sessions": memory_service.get_active_sessions()}


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str):
    memory_service.delete_session(session_id)
    return {"message": "Session deleted"}


@app.get("/api/sessions/{session_id}/results")
def get_session_results(session_id: str):
    results = cache_service.load_results(session_id)
    session = memory_service.get_session(session_id)
    return {"session": session, "videos": results}


# ── Search & Discovery ─────────────────────────────────────────────────────────

@app.post("/api/search")
def search(request: ChannelSearchRequest):
    query = request.query.strip()

    # check if the user pasted a playlist URL directly
    playlist_id = youtube_service.extract_playlist_id(query)
    if playlist_id:
        info = youtube_service.get_playlist_info(playlist_id)
        if not info:
            raise HTTPException(status_code=404, detail="Playlist not found")
        return {"type": "playlist", "playlist": info, "channels": []}

    channels = youtube_service.search_channels(query)
    if not channels:
        raise HTTPException(status_code=404, detail="No channels found")
    return {"type": "channels", "channels": channels, "playlist": None}


@app.get("/api/channels/{channel_id}/playlists")
def get_playlists(channel_id: str):
    playlists = youtube_service.get_channel_playlists(channel_id)
    return {"playlists": playlists}


# ── Session Start ──────────────────────────────────────────────────────────────


@app.post("/api/sessions/start")
def start_session(data: dict):
    playlist_id = data.get("playlist_id")
    channel_id = data.get("channel_id", "")
    channel_name = data.get("channel_name", "Unknown Channel")
    playlist_name = data.get("playlist_name", "Unknown Playlist")

    videos = youtube_service.get_playlist_videos(playlist_id)
    total = len(videos)

    if total == 0:
        raise HTTPException(status_code=404, detail="No videos found in playlist")

    session_id = memory_service.create_session(
        channel_name=channel_name,
        channel_id=channel_id,
        playlist_name=playlist_name,
        playlist_id=playlist_id,
        total_videos=total
    )

    # save all videos as unanalyzed initially so we can track progress
    unanalyzed = [
        {**v, "analyzed": False, "explanation": None,
         "level": None, "type": None, "topics": [],
         "estimated_minutes": None, "requires_previous": False}
        for v in videos
    ]
    cache_service.save_results(session_id, unanalyzed)

    session = memory_service.get_session(session_id)
    return {
        "session_id": session_id,
        "total_videos": total,
        "session": session,
        "preview_videos": videos[:3]
    }


# ── Batch Analysis ─────────────────────────────────────────────────────────────


@app.post("/api/sessions/{session_id}/analyze-next")
def analyze_next_batch(session_id: str):
    session = memory_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session["status"] == "completed":
        return {"message": "All videos have been analyzed", "is_complete": True, "videos": []}

    all_videos = cache_service.load_results(session_id)
    unanalyzed = [v for v in all_videos if not v.get("analyzed", False)]

    if not unanalyzed:
        memory_service.complete_session(session_id)
        return {"message": "All videos analyzed!", "is_complete": True, "videos": []}

    # process 3 videos at a time to keep requests reasonable
    batch = unanalyzed[:3]

    enriched_batch = []
    for video in batch:
        transcript = youtube_service.get_transcript(video["video_id"])
        enriched_batch.append({**video, "transcript": transcript})

    analyzed_batch = gemini_service.analyze_batch(enriched_batch)
    cache_service.save_results(session_id, analyzed_batch)

    new_analyzed_count = cache_service.get_analyzed_count(session_id)
    new_batch_num = session["last_batch"] + 1
    memory_service.update_session(session_id, new_analyzed_count, new_batch_num)

    total = session["total_videos"]
    is_complete = new_analyzed_count >= total

    return {
        "session_id": session_id,
        "batch_number": new_batch_num,
        "videos": analyzed_batch,
        "analyzed_count": new_analyzed_count,
        "total_videos": total,
        "is_complete": is_complete
    }


# ── Single Video (on-demand) ───────────────────────────────────────────────────

@app.post("/api/sessions/{session_id}/analyze-video")
def analyze_single_video(session_id: str, data: dict):
    video_id = data.get("video_id")
    if not video_id:
        raise HTTPException(status_code=400, detail="video_id is required")

    session = memory_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    all_videos = cache_service.load_results(session_id)
    target = next((v for v in all_videos if v["video_id"] == video_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Video not found in session")

    if target.get("analyzed"):
        return {"video": target, "already_analyzed": True,
                "analyzed_count": cache_service.get_analyzed_count(session_id),
                "total_videos": session["total_videos"], "is_complete": False}

    transcript = youtube_service.get_transcript(video_id)
    enriched = [{**target, "transcript": transcript}]
    analyzed = gemini_service.analyze_batch(enriched)
    cache_service.save_results(session_id, analyzed)

    new_count = cache_service.get_analyzed_count(session_id)
    memory_service.update_session(session_id, new_count, session["last_batch"])

    is_complete = new_count >= session["total_videos"]
    if is_complete:
        memory_service.complete_session(session_id)

    return {
        "video": analyzed[0],
        "analyzed_count": new_count,
        "total_videos": session["total_videos"],
        "is_complete": is_complete
    }


# ── Playlist Summary ───────────────────────────────────────────────────────────

@app.post("/api/sessions/{session_id}/summary")
def generate_summary(session_id: str):
    session = memory_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    cached = memory_service.get_session_summary(session_id)
    if cached:
        return {"summary": cached, "cached": True}

    all_videos = cache_service.load_results(session_id)
    analyzed = [v for v in all_videos if v.get("analyzed")]

    if not analyzed:
        raise HTTPException(status_code=400, detail="No analyzed videos yet")

    summary = gemini_service.generate_playlist_summary(
        analyzed, session.get("playlist_name", "")
    )
    memory_service.save_session_summary(session_id, summary)

    return {"summary": summary, "cached": False}


# ── Learning Path ──────────────────────────────────────────────────────────────


@app.post("/api/sessions/{session_id}/learning-path")
def generate_learning_path(session_id: str):
    session = memory_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    cached = memory_service.get_learning_path(session_id)
    if cached:
        return {"learning_path": cached, "cached": True}

    all_videos = cache_service.load_results(session_id)
    analyzed = [v for v in all_videos if v.get("analyzed")]

    if not analyzed:
        raise HTTPException(status_code=400, detail="No analyzed videos yet")

    learning_path = gemini_service.generate_learning_path(analyzed)
    memory_service.save_learning_path(session_id, learning_path)

    return {"learning_path": learning_path, "cached": False}


# ── Chat ───────────────────────────────────────────────────────────────────────


@app.post("/api/sessions/{session_id}/chat")
def chat_with_playlist(session_id: str, request: ChatRequest):
    session = memory_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    all_videos = cache_service.load_results(session_id)
    analyzed = [v for v in all_videos if v.get("analyzed")]

    if not analyzed:
        raise HTTPException(status_code=400, detail="No analyzed videos yet. Analyze some videos first.")

    history = [msg.dict() for msg in (request.history or [])]

    result = gemini_service.chat_with_playlist(
        question=request.question,
        videos=analyzed,
        playlist_name=session.get("playlist_name", ""),
        chat_history=history
    )

    return ChatResponse(
        answer=result.get("answer", ""),
        referenced_videos=result.get("referenced_videos", [])
    )


# ── Compare Playlists ──────────────────────────────────────────────────────────


@app.post("/api/compare")
def compare_playlists(request: CompareRequest):
    session_a = memory_service.get_session(request.session_id_a)
    session_b = memory_service.get_session(request.session_id_b)

    if not session_a:
        raise HTTPException(status_code=404, detail=f"Session A not found: {request.session_id_a}")
    if not session_b:
        raise HTTPException(status_code=404, detail=f"Session B not found: {request.session_id_b}")

    videos_a = cache_service.load_results(request.session_id_a)
    videos_b = cache_service.load_results(request.session_id_b)

    result = gemini_service.compare_playlists(
        playlist_a={"name": session_a.get("playlist_name", "Playlist A"), "videos": videos_a},
        playlist_b={"name": session_b.get("playlist_name", "Playlist B"), "videos": videos_b}
    )

    return result
