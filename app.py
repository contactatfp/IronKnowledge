from flask import Flask, app
from flask_login import LoginManager
from models import db, User
from routes import bp
from config import Config
from scraper import main as scrape_youtube


@bp.route('/scrape')
def scrape():
    scrape_youtube()
    return "Scraping started. Check the 'videos' folder for the downloaded videos."


def create_app(config=None):
    app = Flask(__name__)

    # Set up the app configuration using the attributes from Config
    app.config.from_object(Config)

    # If config is specified, update the app configuration with it
    if config is not None:
        app.config.update(config)

    setup_app(app)
    return app


def setup_app(app):
    # Initialize the database
    db.init_app(app)
    with app.app_context():
        db.create_all()

    # Set up the login manager
    login_manager = LoginManager()
    login_manager.login_view = 'routes.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register the blueprint
    app.register_blueprint(bp, url_prefix='')


if __name__ == "__main__":
    app = create_app()
    app.run()
