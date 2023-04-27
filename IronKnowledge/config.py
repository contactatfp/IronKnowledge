import os


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    SQLALCHEMY_DATABASE_URI = os.environ.get("SQLALCHEMY_DATABASE_URI", "sqlite:///site.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GPT4_API_KEY = os.environ.get('GPT4_API_KEY')
    HR_API_KEY = os.environ.get('HR_API_KEY') or 'your-hr-api-key-here'
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'your-mail-server-here'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or 'your-mail-username-here'
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or 'your-mail-password-here'
    ADMINS = ['kyle@example.com']
