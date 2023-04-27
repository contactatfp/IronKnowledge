import os
import json
from scraper import get_video_ids


def get_video_info(search_query):
    video_ids = []
    with open(f'static/{search_query}/video_ids.json', 'r') as f:
        video_ids = json.load(f)
    video_ids = get_video_ids(search_query, max_duration=30)
    video_info_list = []

    for video_id in video_ids:
        youtube_link = f"https://www.youtube.com/watch?v={video_id}"
        thumbnail_path = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
        video_info = {
            "video_id": video_id,
            "thumbnail_path": thumbnail_path,
            "youtube_link": youtube_link,
        }
        video_info_list.append(video_info)

    return video_info_list


def get_downloaded_videos(search_query):
    video_files = []

    for root, _, files in os.walk("static"):
        for file in files:
            if file.endswith(".jpg"):
                video_id = file.split('_')[0]
                youtube_link = f"https://www.youtube.com/watch?v={video_id}"
                video_info = {
                    "filename": file,
                    "player_name": os.path.basename(root),
                    "thumbnail_path": os.path.join(root, file),
                    "youtube_link": youtube_link,
                }
                video_files.append(video_info)

    return video_files
