import os
import googleapiclient.discovery
import googleapiclient.errors
import json
import yt_dlp
from moviepy.editor import VideoFileClip
from isodate import parse_duration

with open("secret_config.json", "r") as f:
    secret_config = json.load(f)

youtube_api_key = secret_config["youtube_api_key"]

male_names = [
    "Novak Djokovic", "Daniil Medvedev", "Rafael Nadal",
    "Stefanos Tsitsipas",
    "Alexander Zverev", "Andrey Rublev", "Matteo Berrettini", "Casper Ruud",
    "Denis Shapovalov", "Hubert Hurkacz", "Diego Schwartzman", "Pablo Carreno Busta",
    "Felix Auger-Aliassime", "Gael Monfils", "Roberto Bautista Agut", "Karen Khachanov",
    "Jannik Sinner", "Cristian Garin", "Grigor Dimitrov", "Alex de Minaur",
    "Aslan Karatsev", "David Goffin", "Reilly Opelka", "Cameron Norrie",
    "Fabio Fognini", "John Isner", "Dan Evans", "Nick Kyrgios", "Taylor Fritz",
    "Adrian Mannarino", "Ugo Humbert", "Nikoloz Basilashvili", "Alejandro Davidovich Fokina",
    "Dusan Lajovic", "Marton Fucsovics", "Jan-Lennard Struff", "Lloyd Harris",
    "Albert Ramos-Vinolas", "Kei Nishikori", "Benoit Paire", "Guido Pella",
    "Richard Gasquet", "Filip Krajinovic", "Yoshihito Nishioka", "Laslo Djere",
    "Marin Cilic", "Tommy Paul", "Jeremy Chardy", "Vasek Pospisil", "Lorenzo Sonego"
]

female_names = [
    "Ashleigh Barty", "Aryna Sabalenka", "Naomi Osaka", "Elina Svitolina",
    "Karolina Pliskova", "Bianca Andreescu", "Sofia Kenin", "Iga Swiatek",
    "Garbine Muguruza", "Petra Kvitova", "Simona Halep", "Barbora Krejcikova",
    "Jennifer Brady", "Victoria Azarenka", "Cori Gauff", "Maria Sakkari",
    "Anastasia Pavlyuchenkova", "Elena Rybakina", "Paula Badosa", "Ons Jabeur",
    "Karolina Muchova", "Jessica Pegula", "Jelena Ostapenko", "Veronika Kudermetova"
]

tennis_players = male_names + female_names


def create_folder(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)


def download_video(video_id, player_name):
    create_folder(f'videos/{player_name}')
    video_url = f'https://www.youtube.com/watch?v={video_id}'

    ydl_opts = {
        'outtmpl': f'videos/{player_name}/{video_id}.mp4',
        'format': 'bestvideo[ext=mp4]/mp4',
        'quiet': True,
        'postprocessors': [],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])


def get_video_ids(player_name, max_duration):
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=youtube_api_key)

    # Step 1: Get video IDs
    search_request = youtube.search().list(
        part="id",
        type="video",
        q=player_name,
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



def get_size(start_path='.'):
    total_size = 0
    for dirpath, _, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size


def slice_video(player_name, video_id):
    input_path = f'videos/{player_name}/{video_id}.mp4'
    video = VideoFileClip(input_path)
    video_duration = video.duration

    start_time = 0
    end_time = 60  # 1 minute in seconds
    counter = 1

    while start_time < video_duration:
        clip = video.subclip(start_time, min(end_time, video_duration))
        output_path = f'videos/{player_name}/{video_id}_part{counter}.mp4'
        clip.write_videofile(output_path, codec='libx264', audio_codec='aac')
        clip.close()

        start_time += 60
        end_time += 60
        counter += 1

    # Remove the original video file
    os.remove(input_path)


def main():
    for player_name in tennis_players:
        video_ids = get_video_ids(player_name, max_duration=30)  # Pass the max_duration
        videos_downloaded = 0
        for video_id in video_ids:
            if videos_downloaded >= 10:
                break

            download_video(video_id, player_name)
            slice_video(player_name, video_id)
            videos_downloaded += 1

        print(f'{player_name} videos downloaded: {videos_downloaded}')


if __name__ == "__main__":
    main()
