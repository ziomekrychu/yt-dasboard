import json
import os
from datetime import datetime, timedelta
from youtube_api import get_latest_videos, get_video_stats


CACHE_PATH = "video_cache.json"
CACHE_TTL_HOURS = 3
MAX_VIDEO_AGE_DAYS = 21


def load_cache():
    if not os.path.exists(CACHE_PATH):
        return {"_last_check": "2000-01-01T00:00:00"}, {}
    with open(CACHE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    meta = {"_last_check": data.pop("_last_check", "2000-01-01T00:00:00")}
    return meta, data


def save_cache(meta, video_dict):
    # usuń stare filmy z cache
    cutoff = datetime.utcnow() - timedelta(days=MAX_VIDEO_AGE_DAYS)
    cleaned_dict = {
        vid: v for vid, v in video_dict.items()
        if datetime.strptime(v["published_at"], "%Y-%m-%d %H:%M") >= cutoff
    }

    all_data = {**cleaned_dict, "_last_check": meta["_last_check"]}
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)


def should_update_cache(meta):
    last_check = datetime.strptime(meta["_last_check"], "%Y-%m-%dT%H:%M:%S")
    return datetime.utcnow() - last_check > timedelta(hours=CACHE_TTL_HOURS)


def update_cache_if_needed(youtube, channel_ids):
    meta, video_dict = load_cache()

    if not should_update_cache(meta):
        return video_dict  # nie odświeżamy, używamy cache

    for cid in channel_ids:
        try:
            new_videos = get_latest_videos(youtube, cid, max_results=3)
            for video in new_videos:
                vid = video["video_id"]
                pub_dt = datetime.strptime(video["published_at"], "%Y-%m-%dT%H:%M:%SZ")
                if vid not in video_dict and pub_dt >= datetime.utcnow() - timedelta(days=MAX_VIDEO_AGE_DAYS):
                    stats_df = get_video_stats(youtube, [vid])
                    if not stats_df.empty:
                        row = stats_df.iloc[0]
                        video_dict[vid] = {
                            "title": row["title"],
                            "views": int(row["views"]),
                            "published_at": row["published_at"],
                            "hot_score": float(row["hot_score"]),
                            "hours_since": float(row["hours_since"]),
                            "thumbnail": row["thumbnail"],
                            "video_url": row["video_url"],
                            "channel_id": row["channel_id"],
                            "channel_avg": float(row["channel_avg"]),
                            "growth": float(row["growth"])
                        }
        except Exception as e:
            print(f"Błąd przy aktualizacji kanału {cid}: {e}")

    meta["_last_check"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    save_cache(meta, video_dict)
    return video_dict
