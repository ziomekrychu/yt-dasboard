from googleapiclient.discovery import build
from datetime import datetime, timezone, timedelta
import pandas as pd
import streamlit as st


def get_youtube_service(api_key):
    return build("youtube", "v3", developerKey=api_key)


@st.cache_data(ttl=1200)
def get_latest_videos(_youtube, channel_id, max_results=50):
    uploads_playlist = _youtube.channels().list(
        part="contentDetails",
        id=channel_id
    ).execute()

    uploads_id = uploads_playlist["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    videos = []
    next_page_token = None
    cutoff = datetime.utcnow() - timedelta(days=21)

    while True:
        playlist_items = _youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=uploads_id,
            maxResults=max_results,
            pageToken=next_page_token
        ).execute()

        for item in playlist_items["items"]:
            video_id = item["contentDetails"]["videoId"]
            title = item["snippet"]["title"]
            published_at_str = item["contentDetails"]["videoPublishedAt"]
            published_at = datetime.strptime(published_at_str, "%Y-%m-%dT%H:%M:%SZ")

            if published_at < cutoff:
                return videos  # zakończ pętlę, jeśli jesteśmy poza zakresem 21 dni

            thumbnail_url = item["snippet"]["thumbnails"]["high"]["url"]
            videos.append({
                "video_id": video_id,
                "title": title,
                "published_at": published_at_str,
                "channel_id": channel_id,
                "thumbnail": thumbnail_url
            })

        next_page_token = playlist_items.get("nextPageToken")
        if not next_page_token:
            break

    return videos


@st.cache_data(ttl=1200)
def get_video_stats(_youtube, video_ids):
    stats_response = _youtube.videos().list(
        part="statistics,snippet",
        id=",".join(video_ids)
    ).execute()

    now = datetime.now(timezone.utc)
    three_weeks_ago = now - timedelta(days=21)

    video_data = []
    channel_hsums = {}
    channel_hcounts = {}

    for item in stats_response["items"]:
        views = int(item["statistics"].get("viewCount", 0))
        published_at = item["snippet"]["publishedAt"]
        published_at_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))

        if published_at_dt < three_weeks_ago:
            continue

        hours_since = (now - published_at_dt).total_seconds() / 3600
        hot_score = views / hours_since if hours_since > 0 else 0
        channel_id = item["snippet"].get("channelId", "")

        # Update channel stats
        if channel_id not in channel_hsums:
            channel_hsums[channel_id] = 0
            channel_hcounts[channel_id] = 0

        channel_hsums[channel_id] += hot_score
        channel_hcounts[channel_id] += 1

        video_data.append({
            "title": item["snippet"]["title"],
            "video_id": item["id"],
            "views": views,
            "published_at": published_at_dt.strftime("%Y-%m-%d %H:%M"),
            "hours_since": round(hours_since, 2),
            "hot_score": round(hot_score, 2),
            "thumbnail": item["snippet"]["thumbnails"]["high"]["url"],
            "video_url": f"https://www.youtube.com/watch?v={item['id']}",
            "channel_id": channel_id
        })

    df = pd.DataFrame(video_data)

    if not df.empty:
        # Oblicz średnią HotScore kanału
        df["channel_avg"] = df["channel_id"].apply(lambda cid: round(channel_hsums[cid] / channel_hcounts[cid], 2))
        # Oblicz wzrost HotScore względem średniej kanału
        df["growth"] = ((df["hot_score"] - df["channel_avg"]) / df["channel_avg"] * 100).round(2)

    return df
