import os


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    SQLALCHEMY_DATABASE_URI = os.environ.get("SQLALCHEMY_DATABASE_URI", "sqlite:///site.db")
    SECURITY_PASSWORD_SALT = 'askdjfh383ueioaqnvc3b2oi'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GPT4_API_KEY = os.environ.get('GPT4_API_KEY')
    HR_API_KEY = os.environ.get('HR_API_KEY') or 'your-hr-api-key-here'
    # MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    # MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    # MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') or True
    # MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or 'contact@fakepicasso.com'
    # MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or 'itsnotreal00'
    # ADMINS = ['kyle@example.com']
    GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    EMBEDDING_MODEL = "text-embedding-ada-002"
    GPT_MODEL = "gpt-3.5-turbo"
    # GPT_MODEL = "gpt-4"
