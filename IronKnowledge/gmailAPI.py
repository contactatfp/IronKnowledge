from __future__ import print_function

import json
import os.path
import openai
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pandas as pd



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


def main():
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
        emails = get_emails(service, domain)

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


# Run the Gmail API script and get email data
email_data = main()

# Check if email_data is not empty
if email_data:
    # Generate embeddings for email subjects and snippets
    email_embeddings = generate_email_embeddings(email_data)

    # Save email data and embeddings to a DataFrame
    email_df = pd.DataFrame({"email": [f"Subject: {email['subject']}\nSnippet: {email['snippet']}" for email in email_data],
                             "embedding": email_embeddings})


    # Save the DataFrame to a CSV file
    email_df.to_csv("email_embeddings.csv", index=False)
else:
    print("No emails found.")

