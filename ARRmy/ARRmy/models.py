from flask_login import UserMixin
from . import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    accounts = db.relationship('Account', backref='owner', lazy=True)
    alerts = db.relationship('Alert', backref='user', lazy=True)


class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(50), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    partner_id = db.Column(db.Integer, db.ForeignKey('partner.id'))  # Add this line
    contacts = db.relationship('Contact', backref='account', lazy=True)
    # Additional fields
    rank = db.Column(db.Integer, nullable=False)
    products_owned = db.relationship('Product', backref='account', lazy=True)
    notes = db.Column(db.String(500), nullable=True)
    last_30_days_activity = db.Column(db.String(500), nullable=True)
    most_recent_meeting_date = db.Column(db.DateTime, nullable=True)
    most_recent_opp_date = db.Column(db.DateTime, nullable=True)
    score = db.Column(db.Float, nullable=False)
    partner_reps = db.relationship('Rep', backref='account', lazy=True)
    opportunities = db.relationship('Opportunity', backref='account', lazy=True)
    tech = db.Column(db.String(100), nullable=True)
    industry = db.Column(db.String(100), nullable=True)
    sub_industry = db.Column(db.String(100), nullable=True)


class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    date = db.Column(db.DateTime, nullable=False)


class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)


class Metrics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    value = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class Partner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    accounts = db.relationship('Account', backref='partner', lazy=True)


# Additional models
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)


class Rep(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)


class Opportunity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False)  # e.g. 'open', 'closed'
    date = db.Column(db.DateTime, nullable=False)
