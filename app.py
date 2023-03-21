from flask import Flask
from models import db
from config import Config
from routes import bp as routes_bp


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

    # Register the Blueprint
    app.register_blueprint(routes_bp)


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=8000)
