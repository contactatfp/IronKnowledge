import os

def get_downloaded_videos(search_query):
    video_files = []

    for root, _, files in os.walk("videos"):
        for file in files:
            if file.endswith(".mp4"):
                video_info = {
                    "filename": file,
                    "filepath": os.path.join(root, file),
                    "player_name": os.path.basename(root),
                    "thumbnail_path": os.path.join("static", search_query, file.replace('.mp4', '.jpg')),
                }
                video_files.append(video_info)

    return video_files

