import os
import requests
from datetime import datetime
import isodate
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")

# Pamięć cache by nie szukać ponownie
_channel_id_cache = {}

def resolve_handle_to_channel_id(handle_or_id):
    if handle_or_id in _channel_id_cache:
        return _channel_id_cache[handle_or_id]

    if handle_or_id.startswith("UC"):
        _channel_id_cache[handle_or_id] = handle_or_id
        return handle_or_id

    if handle_or_id.startswith("@"):
        handle = handle_or_id[1:]
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&type=channel&q={handle}&key={API_KEY}"
        res = requests.get(url).json()
        if "items" in res and len(res["items"]) > 0:
            channel_id = res["items"][0]["snippet"]["channelId"]
            _channel_id_cache[handle_or_id] = channel_id
            return channel_id
        else:
            raise Exception(f"Nie znaleziono kanału dla: {handle_or_id}")
    raise Exception(f"Niepoprawny format ID/handle: {handle_or_id}")

def get_channel_uploads_id(channel_id):
    url = f"https://www.googleapis.com/youtube/v3/channels?part=contentDetails&id={channel_id}&key={API_KEY}"
    res = requests.get(url).json()
    return res["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

def fetch_shorts(handle_or_id, max_results=50):
    channel_id = resolve_handle_to_channel_id(handle_or_id)
    uploads_id = get_channel_uploads_id(channel_id)
    url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet,contentDetails&playlistId={uploads_id}&maxResults={max_results}&key={API_KEY}"
    res = requests.get(url).json()
    videos = []
    for item in res["items"]:
        video_id = item["contentDetails"]["videoId"]
        info = get_video_details(video_id)
        if info:
            videos.append(info)
    return videos

def get_video_details(video_id):
    url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics,contentDetails&id={video_id}&key={API_KEY}"
    res = requests.get(url).json()
    if not res["items"]:
        return None
    data = res["items"][0]
    snippet = data["snippet"]
    stats = data["statistics"]
    content = data["contentDetails"]

    published = snippet["publishedAt"]
    duration = isodate.parse_duration(content["duration"]).total_seconds()
    now = datetime.utcnow()
    published_dt = datetime.strptime(published, "%Y-%m-%dT%H:%M:%SZ")
    hours_since = (now - published_dt).total_seconds() / 3600
    hot_score = int(stats.get("viewCount", 0)) / hours_since if hours_since > 0 else 0

    return {
        "video_id": video_id,
        "title": snippet["title"],
        "channel_title": snippet["channelTitle"],
        "published_at": published_dt,
        "views": int(stats.get("viewCount", 0)),
        "thumbnail": snippet["thumbnails"]["high"]["url"],
        "hot_score": round(hot_score, 2),
        "title_length": len(snippet["title"]),
        "url": f"https://youtube.com/watch?v={video_id}",
    }
