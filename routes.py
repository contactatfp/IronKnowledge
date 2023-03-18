from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, YouTubeChannel, YouTubeVideo

bp = Blueprint("routes", __name__)


@bp.route("/")
@login_required
def index():
    channels = YouTubeChannel.query.all()
    return render_template("index.html", channels=channels)


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
@login_required
def logout():
    logout_user()
    flash("You have been logged out", "success")
    return redirect(url_for("routes.login"))

# Add more routes for your specific application requirements
