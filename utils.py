import random
import string
from flask_mail import Message
from app import mail

def format_date(date):
    return date.strftime('%Y-%m-%d')

def generate_random_id(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def send_email_notification(subject, recipients, body):
    msg = Message(subject, recipients=recipients, body=body)
    mail.send(msg)
