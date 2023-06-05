from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# Auxiliary table for many-to-many relationship
project_user_table = db.Table('project_user',
                              db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
                              db.Column('project_id', db.Integer, db.ForeignKey('project.id'))
                              )


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    projects = db.relationship('Project', secondary=project_user_table, backref='users', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    summary = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    version = db.Column(db.String(20), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    documents = db.relationship('Document', backref='project', lazy=True)
    model_name = db.Column(db.String(100), nullable=True)
    company_domain = db.Column(db.String(100), nullable=True)  # New field for company domain
    keyword = db.Column(db.String(100), nullable=True)  # New field for keyword

    def __repr__(self):
        return f'<Project {self.name}>'


class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)

    def __repr__(self):
        return f'<Document {self.name}>'


class Email(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(200), nullable=False)
    snippet = db.Column(db.Text, nullable=False)
    embedding = db.Column(db.PickleType, nullable=True)  # Store the embeddings as a pickled object
    date_of_email = db.Column(db.DateTime, nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)


class Attachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_name = db.Column(db.String(200))
    file_text = db.Column(db.Text)
    embedding = db.Column(db.PickleType)

    def __repr__(self):
        return f"<Attachment {self.file_name}>"


class Invitation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)

    def __repr__(self):
        return f'<Invitation to {self.email} for project {self.project_id}>'
