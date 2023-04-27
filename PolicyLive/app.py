from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
from flask_login import LoginManager
from views import main_bp
from auth import auth_bp
from documents import documents_bp
from faq import faq_bp

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
migrate = Migrate()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(documents_bp, url_prefix='/documents')
    app.register_blueprint(faq_bp, url_prefix='/faq')

    return app


app = create_app()

if __name__ == '__main__':
    app.run()
