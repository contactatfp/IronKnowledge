from flask import Flask
from models import db
from config import Config
from routes import bp as routes_bp




def create_app(config=None):
    app = Flask(__name__)

    # Set up the app configuration using the attributes from Config
    app.config.from_object(Config)

    # If config is specified, update the app configuration with it
    if config is not None:
        app.config.update(config)

    setup_app(app)
    return app


# def get_downloaded_videos():
#     video_folder = 'videos'
#     video_files = []
#     for player_name in os.listdir(video_folder):
#         player_folder = os.path.join(video_folder, player_name)
#         for video in os.listdir(player_folder):
#             if video.endswith('.mp4'):
#                 video_id = video.split('.')[0]
#                 video_path = os.path.join(player_folder, video)
#                 thumbnail_path = f'https://i.ytimg.com/vi/{video_id}/hqdefault.jpg'
#                 youtube_link = f'https://www.youtube.com/watch?v={video_id}'
#                 video_files.append({
#                     'player_name': player_name,
#                     'video_path': video_path,
#                     'thumbnail_path': thumbnail_path,
#                     'youtube_link': youtube_link
#                 })
#     return video_files


def setup_app(app):
    # Initialize the database
    db.init_app(app)
    with app.app_context():
        db.create_all()

    # Register the Blueprint
    app.register_blueprint(routes_bp)


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=8000)
