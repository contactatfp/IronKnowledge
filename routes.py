from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, YouTubeChannel, YouTubeVideo
from flask import request
from scraper import scrape_youtube
from utils import get_downloaded_videos
from flask import send_from_directory

bp = Blueprint("routes", __name__)


@bp.route("/search", methods=["POST"])
def search():
    search_query = request.form['search_query']
    scrape_youtube(search_query)
    return redirect(url_for("routes.home", search_query=search_query))


@bp.route('/thumbnails/<path:path>')
def send_thumbnail(path):
    return send_from_directory('thumbnails', path)


@bp.route("/")
def home():
    search_query = request.args.get('search_query', '')
    channels = YouTubeChannel.query.all()
    videos = get_downloaded_videos(search_query)

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
