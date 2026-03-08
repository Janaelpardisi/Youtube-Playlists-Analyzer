import os
import re
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
from dotenv import load_dotenv
from typing import List, Dict, Optional

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


def extract_playlist_id(url: str) -> Optional[str]:
    """Extract playlist ID from a YouTube playlist URL."""
    match = re.search(r"list=([A-Za-z0-9_-]+)", url)
    return match.group(1) if match else None


def extract_channel_handle(url: str) -> Optional[str]:
    """Extract channel handle from URL like youtube.com/@handle."""
    match = re.search(r"@([A-Za-z0-9_.-]+)", url)
    return match.group(1) if match else None


def search_channels(query: str) -> List[Dict]:
    """Search for YouTube channels by name or URL."""
    # If it's a direct playlist link, return empty (handled separately)
    if "playlist?list=" in query or "list=" in query:
        return []

    # If it's a channel URL with @handle
    handle = extract_channel_handle(query)
    search_query = handle if handle else query

    response = youtube.search().list(
        part="snippet",
        q=search_query,
        type="channel",
        maxResults=20
    ).execute()

    channels = []
    for item in response.get("items", []):
        channels.append({
            "channel_id": item["snippet"]["channelId"],
            "title": item["snippet"]["title"],
            "description": item["snippet"].get("description", ""),
            "thumbnail": item["snippet"]["thumbnails"].get("default", {}).get("url", "")
        })
    return channels


def get_channel_playlists(channel_id: str) -> List[Dict]:
    """Get all playlists for a given channel."""
    playlists = []
    next_page_token = None

    while True:
        response = youtube.playlists().list(
            part="snippet,contentDetails",
            channelId=channel_id,
            maxResults=50,
            pageToken=next_page_token
        ).execute()

        for item in response.get("items", []):
            playlists.append({
                "playlist_id": item["id"],
                "title": item["snippet"]["title"],
                "description": item["snippet"].get("description", ""),
                "thumbnail": item["snippet"]["thumbnails"].get("medium", {}).get("url", ""),
                "video_count": item["contentDetails"]["itemCount"]
            })

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return playlists


def get_playlist_videos(playlist_id: str) -> List[Dict]:
    """Get all videos in a playlist with their titles and positions."""
    videos = []
    next_page_token = None

    while True:
        response = youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page_token
        ).execute()

        for item in response.get("items", []):
            snippet = item["snippet"]
            video_id = snippet["resourceId"]["videoId"]
            videos.append({
                "video_id": video_id,
                "title": snippet["title"],
                "position": snippet["position"],
                "thumbnail": snippet["thumbnails"].get("medium", {}).get("url", ""),
                "description": snippet.get("description", "")
            })

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return videos


def get_video_details(video_ids: List[str]) -> Dict[str, Dict]:
    """Get full details for a batch of videos."""
    response = youtube.videos().list(
        part="snippet,contentDetails",
        id=",".join(video_ids)
    ).execute()

    details = {}
    for item in response.get("items", []):
        vid_id = item["id"]
        details[vid_id] = {
            "title": item["snippet"]["title"],
            "description": item["snippet"].get("description", ""),
            "duration": item["contentDetails"].get("duration", ""),
            "thumbnail": item["snippet"]["thumbnails"].get("medium", {}).get("url", "")
        }
    return details


def get_transcript(video_id: str, languages: List[str] = ["ar", "en"]) -> str:
    """Attempt to get transcript for a video. Returns empty string if unavailable."""
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
        return " ".join([t["text"] for t in transcript_list])[:8000]  # limit to 8000 chars
    except (NoTranscriptFound, TranscriptsDisabled):
        try:
            # Try any available language
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            return " ".join([t["text"] for t in transcript_list])[:8000]
        except Exception:
            return ""
    except Exception:
        return ""


def get_playlist_info(playlist_id: str) -> Optional[Dict]:
    """Get playlist metadata."""
    response = youtube.playlists().list(
        part="snippet,contentDetails",
        id=playlist_id
    ).execute()

    items = response.get("items", [])
    if not items:
        return None

    item = items[0]
    return {
        "playlist_id": playlist_id,
        "title": item["snippet"]["title"],
        "description": item["snippet"].get("description", ""),
        "thumbnail": item["snippet"]["thumbnails"].get("medium", {}).get("url", ""),
        "video_count": item["contentDetails"]["itemCount"],
        "channel_id": item["snippet"]["channelId"],
        "channel_name": item["snippet"]["channelTitle"]
    }
