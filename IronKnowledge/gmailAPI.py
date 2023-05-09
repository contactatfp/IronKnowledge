from __future__ import print_function

import base64
import tempfile
from pathlib import Path

from flask import current_app
import json
import os.path
import openai
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from models import db, Email



# models
EMBEDDING_MODEL = "text-embedding-ada-002"
GPT_MODEL = "gpt-3.5-turbo"

with open('config.json') as f:
    config = json.load(f)

openai.api_key = config['api_secret']

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


def get_emails(service, domain):
    query = f"to:{domain} OR from:{domain}"
    emails = []
    result = service.users().messages().list(userId='me', q=query).execute()
    messages = result.get('messages', [])

    for message in messages:
        msg = service.users().messages().get(userId='me', id=message['id']).execute()
        emails.append(msg)

    return emails


def scrape():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail emails to or from a specific domain.
    """
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('gmail', 'v1', credentials=creds)
        domain = 'bloomacademy.org'

        query = f"to:{domain} OR from:{domain}"
        emails = []
        result = service.users().messages().list(userId='me', q=query).execute()
        messages = result.get('messages', [])

        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()

            # Check for attachments
            attachments = []
            for part in msg.get('payload', {}).get('parts', []):
                if part.get('filename') and part.get('body', {}).get('attachmentId'):
                    attachment_id = part['body']['attachmentId']
                    attachment = service.users().messages().attachments().get(
                        userId='me', messageId=message['id'], id=attachment_id
                    ).execute()
                    data = attachment.get('data')
                    file_data = base64.urlsafe_b64decode(data.encode('UTF-8'))
                    file_name = part.get('filename')

                    # Save the attachment to a temporary folder
                    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file_name).suffix) as tmp_file:
                        tmp_file.write(file_data)
                        attachments.append({'file_path': tmp_file.name, 'file_name': file_name})

            msg['attachments'] = attachments
            emails.append(msg)

        if not emails:
            print(f'No emails found to or from {domain}.')
            return
        print(f'Emails to or from {domain}:')

        email_data = []
        for email in emails:
            headers = email['payload']['headers']
            snippet = email['snippet']
            subject = next(h['value'] for h in headers if h['name'] == 'Subject')
            sender = next(h['value'] for h in headers if h['name'] == 'From')
            to = next(h['value'] for h in headers if h['name'] == 'To')
            date = next(h['value'] for h in headers if h['name'] == 'Date')  # Extract date from headers

            modified_snippet = f"Date: {date} From: {sender} To: {to} {snippet}"  # Prepend date to the modified snippet
            email_data.append({'subject': subject, 'snippet': modified_snippet})


        return email_data

        # for data in email_data:
        #     print(f"Subject: {data['subject']}\nSnippet: {data['snippet']}\n")

    except HttpError as error:
        print(f'An error occurred: {error}')


#
# if __name__ == '__main__':
#     main()

# Function to generate embeddings for email subjects and snippets
def generate_email_embeddings(email_data):
    subjects = [email["subject"] for email in email_data]
    snippets = [email["snippet"] for email in email_data]

    embeddings = []

    # Combine subjects and snippets
    combined_text = [f"{subject}\n\n{snippet}" for subject, snippet in zip(subjects, snippets)]

    # Generate embeddings for combined text
    for text in combined_text:
        response = openai.Embedding.create(model="text-embedding-ada-002", input=text)
        embeddings.append(response["data"][0]["embedding"])

    return embeddings


def scrape_and_store_emails():
    email_data = scrape()

    if email_data:
        email_embeddings = generate_email_embeddings(email_data)

        with current_app.app_context():
            for email, embedding in zip(email_data, email_embeddings):
                new_email = Email(subject=email['subject'], snippet=email['snippet'], embedding=embedding)
                db.session.add(new_email)
            db.session.commit()

    else:
        print("No emails found.")



