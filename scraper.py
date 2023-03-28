import os
import googleapiclient.discovery
import googleapiclient.errors
import json
import yt_dlp
from moviepy.editor import *
from isodate import parse_duration
import requests

with open("secret_config.json", "r") as f:
    secret_config = json.load(f)

youtube_api_key = secret_config["youtube_api_key"]


def save_thumbnail(video_path, thumbnail_path):
    clip = VideoFileClip(video_path)
    thumbnail = clip.get_frame(1)  # Get the first frame of the video
    thumbnail_image = ImageClip(thumbnail, duration=clip.duration)
    thumbnail_image.save_frame(thumbnail_path)


def create_folder(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)


def download_video(video_id, search_query):
    create_folder(f'videos/{search_query}')
    video_url = f'https://www.youtube.com/watch?v={video_id}'

    ydl_opts = {
        'outtmpl': f'videos/{search_query}/{video_id}.mp4',
        'format': 'best',
        'quiet': False,
        'postprocessors': [],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])


def get_video_ids(search_query, max_duration=60):
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=youtube_api_key)

    # Step 1: Get video IDs
    search_request = youtube.search().list(
        part="id",
        type="video",
        q=search_query,
        videoDefinition="high",
        maxResults=50,
    )
    search_response = search_request.execute()
    video_ids = [item['id']['videoId'] for item in search_response['items']]

    # Step 2: Get video durations
    videos_request = youtube.videos().list(
        part="contentDetails",
        id=",".join(video_ids),
        fields="items(id,contentDetails(duration))"
    )
    videos_response = videos_request.execute()
    valid_video_ids = [
        item['id']
        for item in videos_response['items']
        if parse_duration(item['contentDetails']['duration']).total_seconds() <= max_duration
    ]

    return valid_video_ids


def slice_video(search_query, video_id):
    input_path = f'videos/{search_query}/{video_id}.mp4'
    video = VideoFileClip(input_path)
    video_duration = video.duration

    start_time = 0
    end_time = 60  # 1 minute in seconds
    counter = 1

    while start_time < video_duration:
        clip = video.subclip(start_time, min(end_time, video_duration))
        create_folder(f'static/{search_query}/')
        output_path = f'videos/{search_query}/{video_id}_part{counter}.mp4'
        thumbnail_path = f'static/{search_query}/{video_id}_part{counter}.jpg'
        clip.write_videofile(output_path, codec='libx264', audio_codec='mp3')
        save_thumbnail(output_path, thumbnail_path)  # Save the thumbnail
        clip.close()

        start_time += 60
        end_time += 60
        counter += 1

    # Remove the original video file
    os.remove(input_path)


def download_thumbnail(url, save_path):
    response = requests.get(url, stream=True)
    response.raise_for_status()

    with open(save_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)


def scrape_youtube(search_query):
    video_ids = get_video_ids(search_query, max_duration=30)
    videos_downloaded = 0
    directory = f'static/{search_query}'
    if not os.path.exists(directory):
        os.makedirs(directory)
    with open(f'static/{search_query}/video_ids.json', 'w') as f:
        json.dump(video_ids, f)
    print(f'Videos found for {search_query}: {len(video_ids)}')

    for video_id in video_ids:
        thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
        thumbnail_path = f'static/{search_query}/{video_id}.jpg'
        download_thumbnail(thumbnail_url, thumbnail_path)


if __name__ == "__main__":
    search_query = input("Enter a search query: ")
    scrape_youtube(search_query)
