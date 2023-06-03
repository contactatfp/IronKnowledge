from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate, upgrade
import os
from datetime import datetime

from random import randint

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                                        'database', 'site.db')

    db.init_app(app)
    login_manager.init_app(app)
    from .models import User
    with app.app_context():
        db.create_all()
        generate_data()

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    login_manager.login_view = 'main.login'

    # Register the Blueprints
    from .views import main
    app.register_blueprint(main)


    return app


def generate_data():
    from .models import User, Account, Opportunity, Product, Metrics, Partner, Comment, Alert, Event, Contact

    # Check if User table is empty
    if User.query.first() is not None:
        return

    # create some dummy users
    for i in range(5):
        user = User(username=f'user{i}', password=f'password{i}', role='user')
        db.session.add(user)

    db.session.commit()

    # create some dummy partners
    for i in range(3):
        partner = Partner(name=f'partner{i}')
        db.session.add(partner)

    db.session.commit()

    # create some dummy accounts
    for i in range(20):
        account = Account(name=f'account{i}', state=f'state{i}', owner_id=randint(1, 5), partner_id=randint(1, 3), rank=randint(1, 5), score=randint(0, 100))
        db.session.add(account)

    db.session.commit()

    # create some dummy opportunities
    for i in range(5):
        opp = Opportunity(name=f'opportunity{i}', account_id=randint(1, 20), status='open', date=datetime.now())
        db.session.add(opp)

    db.session.commit()

    # create some dummy products
    for i in range(5):
        product = Product(name=f'product{i}', account_id=randint(1, 20))
        db.session.add(product)

    db.session.commit()

    # create some dummy metrics
    for i in range(2):
        metrics = Metrics(name=f'metric{i}', value=randint(0, 100), user_id=randint(1, 5))
        db.session.add(metrics)

    db.session.commit()

    # create some dummy comments
    for i in range(5):
        comment = Comment(content=f'content{i}', account_id=randint(1, 20))
        db.session.add(comment)

    db.session.commit()

    # create some dummy alerts
    for i in range(2):
        alert = Alert(content=f'content{i}', status='open', user_id=randint(1, 5))
        db.session.add(alert)

    db.session.commit()

    # create some dummy events
    for i in range(2):
        event = Event(name=f'event{i}', description=f'description{i}', date=datetime.now())
        db.session.add(event)

    db.session.commit()

    # create some dummy contacts
    for i in range(10):
        contact = Contact(name=f'contact{i}', account_id=randint(1, 20))
        db.session.add(contact)

    db.session.commit()
