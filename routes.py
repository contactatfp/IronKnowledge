from flask import Blueprint, render_template, request, flash, redirect, url_for, Response, send_file
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, YouTubeChannel, YouTubeVideo
from flask import request
from scraper import scrape_youtube, slice_video, get_video_ids, download_thumbnail, download_video as dl_video, \
    download_video
from utils import get_video_info, get_downloaded_videos
from flask import send_from_directory
import requests, tempfile, os
import yt_dlp

bp = Blueprint("routes", __name__)


@bp.route('/download_all_videos/<search_query>')
def download_all_videos(search_query):
    video_ids = get_video_ids(search_query)
    for video_id in video_ids:
        download_video(video_id, search_query)
        slice_video(search_query, video_id)
        thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
        thumbnail_path = f'static/{search_query}/{video_id}_part1.jpg'  # Assuming you want to save the first part's thumbnail
        download_thumbnail(thumbnail_url, thumbnail_path)
    return redirect(url_for("routes.home", search_query=search_query))


@bp.route("/search", methods=["POST"])
def search():
    search_query = request.form['search_query']
    scrape_youtube(search_query)
    return redirect(url_for("routes.home", search_query=search_query))


@bp.route('/download_video/<video_id>/<search_query>')
def download_video_route(video_id, search_query):

    download_video(video_id, search_query)
    video_path = f'videos/{search_query}/{video_id}.mp4'

    # Return a response to let the user know the download is complete
    return send_file(video_path, as_attachment=True)


@bp.route('/thumbnails/<path:path>')
def send_thumbnail(path):
    return send_from_directory('thumbnails', path)


@bp.route("/")
def home():
    search_query = request.args.get('search_query', '')
    channels = YouTubeChannel.query.all()
    videos = get_video_info(search_query) if search_query else []

    return render_template("home.html", channels=channels, videos=videos, search_query=search_query)


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()

        flash("User registered successfully", "success")
        return redirect(url_for("routes.login"))

    return render_template("register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()
        if user is not None and user.check_password(password):
            login_user(user)
            flash("Login successful", "success")
            return redirect(url_for("routes.index"))

        flash("Invalid username or password", "danger")

    return render_template("login.html")


@bp.route("/logout")
def logout():
    logout_user()
    flash("You have been logged out", "success")
    return redirect(url_for("routes.login"))

# Add more routes for your specific application requirements
