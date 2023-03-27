import os


def get_downloaded_videos(search_query):
    video_files = []

    for root, _, files in os.walk("videos"):
        for file in files:
            if file.endswith(".mp4"):
                video_id = file.split('_')[0]
                youtube_link = f"https://www.youtube.com/watch?v={video_id}"
                video_info = {
                    "filename": file,
                    "filepath": os.path.join(root, file),
                    "player_name": os.path.basename(root),
                    "thumbnail_path": os.path.join("static", search_query, file.replace('.mp4', '.jpg')),
                    "youtube_link": youtube_link,
                }
                video_files.append(video_info)

    return video_files


