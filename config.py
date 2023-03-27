import os
import json



# Load the secret_config.json file
with open("secret_config.json", "r") as f:
    secret_config = json.load(f)


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "your_default_secret_key")
    YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "your_youtube_api_key")

    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get("SQLALCHEMY_DATABASE_URI", "sqlite:///db.sqlite")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask environment configuration
    FLASK_ENV = os.environ.get("FLASK_ENV", "development")
    DEBUG = FLASK_ENV == "development"

    # OAuth2 configuration
    GOOGLE_CLIENT_ID = secret_config["web"]["client_id"]
    GOOGLE_CLIENT_SECRET = secret_config["web"]["client_secret"]
    GOOGLE_AUTH_URI = secret_config["web"]["auth_uri"]
    GOOGLE_TOKEN_URI = secret_config["web"]["token_uri"]
    GOOGLE_AUTH_PROVIDER_CERT_URL = secret_config["web"]["auth_provider_x509_cert_url"]

    # YouTube API configuration
    YOUTUBE_API_BASE_URL = "https://www.googleapis.com/youtube/v3"
