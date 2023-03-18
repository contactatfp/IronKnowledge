from flask import Blueprint, request, redirect, url_for, flash
from flask_login import login_user, logout_user
from requests_oauthlib import OAuth2Session
import json
from models import User, db


bp = Blueprint('oauth2', __name__, template_folder='templates')

# Load the secret_config.json file
with open("secret_config.json", "r") as f:
    secret_config = json.load(f)

authorization_base_url = 'https://accounts.google.com/o/oauth2/auth'
token_url = 'https://oauth2.googleapis.com/token'
scope = ['https://www.googleapis.com/auth/youtube.readonly']

@bp.route('/login')
def login():
    oauth2 = OAuth2Session(secret_config['web']['client_id'], scope=scope, redirect_uri=secret_config['web']['redirect_uris'][0])
    authorization_url, state = oauth2.authorization_url(authorization_base_url)

    return redirect(authorization_url)

@bp.route('/callback')
def callback():
    oauth2 = OAuth2Session(secret_config['web']['client_id'], scope=scope, redirect_uri=secret_config['web']['redirect_uris'][0])
    token = oauth2.fetch_token(
        token_url,
        client_secret=secret_config['web']['client_secret'],
        authorization_response=request.url
    )

    user_info = oauth2.get('https://www.googleapis.com/oauth2/v1/userinfo').json()

    user = User.query.filter_by(email=user_info['email']).first()

    if user is None:
        user = User(
            email=user_info['email'],
            name=user_info['name'],
            profile_pic=user_info['picture']
        )
        db.session.add(user)
        db.session.commit()

    login_user(user)

    return redirect(url_for('routes.index'))

