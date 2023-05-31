import os


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    SQLALCHEMY_DATABASE_URI = os.environ.get("SQLALCHEMY_DATABASE_URI", "sqlite:///site.db")
    SECURITY_PASSWORD_SALT = 'askdjfh383ueioaqnvc3b2oi'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GPT4_API_KEY = os.environ.get('GPT4_API_KEY')
    HR_API_KEY = os.environ.get('HR_API_KEY') or 'your-hr-api-key-here'
    # ADMINS = ['kyle@example.com']
    GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    EMBEDDING_MODEL = "text-embedding-ada-002"
    GPT_MODEL = "gpt-3.5-turbo"
    # GPT_MODEL = "gpt-4"
