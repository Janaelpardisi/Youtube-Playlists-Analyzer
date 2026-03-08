from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class ChannelSearchRequest(BaseModel):
    query: str  # channel name, URL, or playlist URL


class PlaylistSelectRequest(BaseModel):
    channel_id: str
    playlist_id: str


class BatchAnalyzeRequest(BaseModel):
    session_id: str


class VideoSummary(BaseModel):
    video_id: str
    title: str
    position: int
    thumbnail: Optional[str] = None
    explanation: Optional[str] = None
    analyzed: bool = False
    # Feature 1 — Auto-Tagging
    level: Optional[str] = None
    type: Optional[str] = None
    topics: Optional[List[str]] = None
    estimated_minutes: Optional[int] = None
    requires_previous: Optional[bool] = None


class PlaylistInfo(BaseModel):
    playlist_id: str
    title: str
    description: Optional[str] = None
    thumbnail: Optional[str] = None
    video_count: int = 0


class ChannelInfo(BaseModel):
    channel_id: str
    title: str
    description: Optional[str] = None
    thumbnail: Optional[str] = None
    subscriber_count: Optional[str] = None


class SessionInfo(BaseModel):
    session_id: str
    channel_name: str
    playlist_name: str
    playlist_id: str
    channel_id: str
    total_videos: int
    analyzed_count: int
    last_batch: int
    last_updated: str
    status: str  # in_progress | completed
    summary: Optional[str] = None


class BatchResult(BaseModel):
    session_id: str
    batch_number: int
    videos: List[VideoSummary]
    analyzed_count: int
    total_videos: int
    is_complete: bool


#  Feature 4

class ChatMessage(BaseModel):
    role: str   # 'user' | 'assistant'
    content: str


class ChatRequest(BaseModel):
    question: str
    history: Optional[List[ChatMessage]] = []


class ChatResponse(BaseModel):
    answer: str
    referenced_videos: Optional[List[Dict[str, Any]]] = []


#  Feature 5

class CompareRequest(BaseModel):
    session_id_a: str
    session_id_b: str
