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
    """Pulls the playlist ID out of a YouTube URL if there is one."""
    match = re.search(r"list=([A-Za-z0-9_-]+)", url)
    return match.group(1) if match else None


def extract_channel_handle(url: str) -> Optional[str]:
    """Pulls the @handle from a YouTube channel URL."""
    match = re.search(r"@([A-Za-z0-9_.-]+)", url)
    return match.group(1) if match else None


def search_channels(query: str) -> List[Dict]:
    """
    Searches YouTube for channels matching the given query.
    If the query is a direct playlist link we skip this and return an empty list
    since the playlist is already handled separately.
    """
    if "playlist?list=" in query or "list=" in query:
        return []

    # if the user pasted a channel URL, extract the handle and use it as the query
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
    """Fetches all playlists for a given channel, handling pagination automatically."""
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
    """Fetches all videos in a playlist with title, position and thumbnail."""
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
    """Fetches full metadata for a batch of video IDs."""
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
    """
    Tries to fetch the transcript for a video.
    Falls back to any available language if Arabic/English aren't found.
    Returns an empty string if transcripts are disabled or unavailable.
    """
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
        return " ".join([t["text"] for t in transcript_list])[:8000]
    except (NoTranscriptFound, TranscriptsDisabled):
        try:
            # last resort — grab whatever language is available
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            return " ".join([t["text"] for t in transcript_list])[:8000]
        except Exception:
            return ""
    except Exception:
        return ""


def get_playlist_info(playlist_id: str) -> Optional[Dict]:
    """Fetches metadata for a single playlist by its ID."""
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
