from datetime import datetime
from app import db
from flask_login import UserMixin


class FAQ(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"FAQ('{self.title}', '{self.created_at}')"


class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    # ...
    faqs = db.relationship('FAQ', backref='user', lazy=True)
    __table_args__ = {'extend_existing': True}

