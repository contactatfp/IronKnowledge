from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)

    def __str__(self):
        return self.username

    def check_password(self, password):
        # Update this with your password hashing logic
        return password == self.password


class YouTubeChannel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.String(40), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    thumbnail_url = db.Column(db.String(255), nullable=True)
    subscriber_count = db.Column(db.Integer, nullable=True)
    video_count = db.Column(db.Integer, nullable=True)
    view_count = db.Column(db.BigInteger, nullable=True)
    created_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, nullable=True)

    videos = db.relationship("YouTubeVideo", backref="channel", lazy=True)

    def __str__(self):
        return self.title


class YouTubeVideo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.String(40), unique=True, nullable=False)
    channel_id = db.Column(db.Integer, db.ForeignKey("you_tube_channel.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    thumbnail_url = db.Column(db.String(255), nullable=True)
    published_at = db.Column(db.DateTime, nullable=True)
    view_count = db.Column(db.BigInteger, nullable=True)
    like_count = db.Column(db.Integer, nullable=True)
    dislike_count = db.Column(db.Integer, nullable=True)
    comment_count = db.Column(db.Integer, nullable=True)
    search_query = db.Column(db.String(255))


def __str__(self):
        return self.title
