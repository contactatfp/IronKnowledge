from __future__ import print_function

import base64
import json
import os.path
from datetime import timezone

import docx2txt
import fitz
import openai
import pandas as pd
import tiktoken
from dateutil.parser import parse
from flask import Flask, render_template, url_for, redirect, flash, request, jsonify
from flask import current_app
from flask_bootstrap import Bootstrap
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from flask_migrate import Migrate
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from scipy import spatial
from sqlalchemy import func

from config import Config
from conversation import Conversation
from dashboard import dashboard_bp
from forms import LoginForm, RegistrationForm, UpdateSettingsForm
from models import User, Project, db, Email, Document

app = Flask(__name__)
app.register_blueprint(dashboard_bp)

app.app_context().push()
app.config.from_object(Config)
bootstrap = Bootstrap(app)
db.init_app(app)
db.create_all()
migrate = Migrate(app, db)
login = LoginManager(app)
login.login_view = 'login'
app.app_context().push()

# models
EMBEDDING_MODEL = "text-embedding-ada-002"
# GPT_MODEL = "gpt-3.5-turbo"
GPT_MODEL = "gpt-4"

with open('config.json') as f:
    config = json.load(f)

openai.api_key = config['api_secret']

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


def get_all_emails():
    return Email.query.all()


@login.user_loader
def load_user(id):
    return db.session.get(User, int(id))


@app.route('/')
def index():
    if current_user.is_authenticated:
        load_user(current_user.id)
        return redirect(url_for('dashboard_bp.dashboard_main'))
    return render_template('index.html')


def extract_text_from_pdf(file_path):
    if not file_path.endswith('.pdf'):
        return None

    doc = fitz.open(file_path)  # open a document
    page = doc.load_page(0)
    text = page.get_text("text")

    return text


def extract_text_from_docx(file_path):
    if not file_path.endswith('.docx'):
        return None

    text = docx2txt.process(file_path)

    return text


@app.route('/refresh_emails', methods=['POST'])
@login_required
def refresh_emails():
    project_id = request.args.get('project_id')  # Get the project id from the URL parameters
    project_domain = request.args.get('project_domain')  # Get the project domain from the URL parameters
    email_data = scrape_and_store_emails(project_id, project_domain)
    if email_data:
        # Generate embeddings for emails and attachments
        embeddings = generate_email_embeddings(email_data)

        # Save emails and attachments data in the database
        with current_app.app_context():
            for email, embedding in zip(email_data, embeddings):
                new_email = Email(subject=email['subject'], snippet=email['snippet'], embedding=embedding,
                                  project_id=project_id)
                db.session.add(new_email)

                for attachment in email['attachments']:
                    with open(attachment['file_path'], "r") as file:
                        file_content = file.read()
                    new_attachment = Email(subject=attachment['file_name'], snippet=file_content, embedding=embedding,
                                           project_id=project_id)
                    db.session.add(new_attachment)

            db.session.commit()
        # if the project summary for this project is empty, then call def project_summary(project_id)
    if not Project.query.filter_by(id=project_id).first().summary:
        user_input = "Write out a detailed summary about everything you know about this. Write it out in bullet point format."
        trainedAsk = ask(int(project_id), user_input)
        Project.query.filter_by(id=project_id).first().summary = trainedAsk
        db.session.commit()

        return jsonify({"email_data": email_data})
    else:
        email_data = []
        return jsonify({"email_data": email_data})


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard_bp.dashboard_main'))  # change this line
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password')
    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.form.get('user_input')
    project_id = int(request.form.get('project_id'))

    if not user_input:
        return jsonify({"error": "User input is empty"}), 400

    # try:
    # trainedAsk = embedTrain.ask(user_input)
    trainedAsk = ask(project_id, user_input)
    # completion = openai.ChatCompletion.create(
    #     model="gpt-3.5-turbo",
    #     messages=[{"role": "user", "content": user_input}]
    # )
    #
    # assistant_message = completion.choices[0].message.content
    print("Assistant message:", trainedAsk)
    return jsonify({"assistant_message": trainedAsk})

    # except Exception as e:
    #     return jsonify({"error": str(e)}), 500


@app.route('/project/<int:project_id>/chat', methods=['GET'])
@login_required
def project_chat(project_id):
    project = Project.query.get_or_404(project_id)
    return render_template('chat.html', project=project)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    form = UpdateSettingsForm()
    if form.validate_on_submit():
        # Add settings update logic here
        pass
    return render_template('settings.html', form=form)


# EMBED API
# search function
def strings_ranked_by_relatedness(
        query: str,
        project_id: int,
        df: pd.DataFrame,
        relatedness_fn=lambda x, y: 1 - spatial.distance.cosine(x, y),
        top_n: int = 100
) -> tuple[list[str], list[float]]:
    """Returns a list of strings and relatednesses, sorted from most related to least."""
    df = df[df['project_id'] == project_id]
    print(f"Dataframe size after filtering by project_id: {df.shape}")

    query_embedding_response = openai.Embedding.create(
        model=EMBEDDING_MODEL,
        input=query,
    )
    query_embedding = query_embedding_response["data"][0]["embedding"]

    strings_and_relatednesses = [
        (row["email"], relatedness_fn(query_embedding, row["embedding"]))  # Change 'text' to 'email' here
        for i, row in df.iterrows()
    ]

    print(f"Number of strings and relatednesses: {len(strings_and_relatednesses)}")

    strings_and_relatednesses.sort(key=lambda x: x[1], reverse=True)

    if not strings_and_relatednesses:
        print("strings_and_relatednesses is empty.")
        return [], []

    strings, relatednesses = zip(*strings_and_relatednesses)
    return strings[:top_n], relatednesses[:top_n]


def num_tokens(text: str, model: str = GPT_MODEL) -> int:
    """Return the number of tokens in a string."""
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))


def query_message(
        project_id: int,
        query: str,
        df: pd.DataFrame,
        model: str,
        token_budget: int
) -> str:
    """Return a message for GPT, with relevant source texts pulled from a dataframe."""
    strings, relatednesses = strings_ranked_by_relatedness(query, project_id, df)
    introduction = 'Use the emails and attachments below. If the answer cannot be found in the emails or attachments, explain why not and what the closest answer would be.'
    question = f"\n\nQuestion is about the {Project.query.get_or_404(project_id).name} project: {query}"
    message = introduction
    company_name = Project.query.get_or_404(project_id).name
    for string in strings:
        next_article = f'\n\n${company_name} Email and attachment thread:\n"""\n{string}\n"""'
        if (
                num_tokens(message + next_article + question, model=model)
                > token_budget
        ):
            break
        else:
            message += next_article
    return message + question


# route that renders the project_documents.html page
@app.route('/project/<int:project_id>/documents', methods=['GET'])
@login_required
def project_documents(project_id):
    project = Project.query.get_or_404(project_id)
    return render_template('project_documents.html', project=project)


@app.route('/ask', methods=['POST'])
def ask_route():
    data = request.json
    project_id = data.get('project_id')
    user_input = data.get('user_input')
    updated_summary = ask(project_id, user_input)

    return jsonify({'updated_summary': updated_summary})


def ask(
        project_id: int,
        query: str,
        model: str = GPT_MODEL,
        token_budget: int = 4096 - 500,
        print_message: bool = False,
) -> str:
    emails = get_all_emails()
    data = [{
        "email": email.subject + " " + email.snippet,
        "embedding": email.embedding,
        "project_id": email.project_id,
    } for email in emails]

    df = pd.DataFrame(data)

    message = query_message(project_id, query, df, model=model, token_budget=token_budget)
    if print_message:
        print(message)

    # Initialize the conversation when the session begins
    conversation = Conversation(project_id)

    # Add the user's message to the conversation
    conversation.add_user_message(message)

    # Generate the model's response
    response = openai.ChatCompletion.create(
        model=model,
        messages=list(conversation.messages),  # Convert deque to list before passing to the API
        temperature=0
    )

    # Extract the response message
    response_message = response["choices"][0]["message"]["content"]

    # Try to find a document relevant to the response
    document = get_relevant_document(response_message, project_id)
    if document is not None:
        path, filename = os.path.split(document.content)
        document_link = url_for('dashboard_bp.serve_file', path=path, filename=filename)
        response_message += f' You can view the related document at <a href="{document_link}">{filename}</a>.'

    # Try to find an email relevant to the response
    email = get_relevant_email(response_message, project_id)
    if email is not None:
        email_link = url_for('dashboard_bp.email', email_id=email.id)
        response_message += f' You can view the related email at <a href="{email_link}">email thread</a>.'

    # Add the model's response to the conversation
    conversation.add_model_message(response_message)

    print(response_message)
    return response_message


def get_relevant_document(message, project_id):
    documents = Document.query.filter_by(project_id=project_id).all()
    for document in documents:
        if document.name.lower() in message.lower():
            return document
    return None


def get_relevant_email(message, project_id):
    emails = Email.query.filter_by(project_id=project_id).all()
    for email in emails:
        if email.snippet.lower() in message.lower():
            return email
    return None


def sanitize_filename(filename):
    filename = filename.strip()  # Remove leading/trailing spaces
    filename = filename.replace(' ', '_')  # Replace spaces with underscores
    return filename


def scrape(project_id, project_domain):
    local_folder = 'attachments'
    latest_email_date = (
        db.session.query(func.max(Email.date_of_email))
        .filter(Email.project_id == project_id)
        .scalar()
    )

    if latest_email_date is not None:
        latest_email_date = latest_email_date.astimezone(timezone.utc)
        latest_email_date_str = latest_email_date.strftime("%Y/%m/%d")
    else:
        latest_email_date_str = ""

    if not os.path.exists(local_folder):
        os.makedirs(local_folder)

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
        domain = project_domain

        query = f"to:{domain} OR from:{domain}"
        if latest_email_date_str:
            query += f" after:{latest_email_date_str}"

        emails = []
        result = service.users().messages().list(userId='me', q=query).execute()
        messages = result.get('messages', [])

        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()

            attachments = []
            for part in msg.get('payload', {}).get('parts', []):
                if part.get('filename') and part.get('body', {}).get('attachmentId'):
                    attachment_id = part['body']['attachmentId']
                    attachment = service.users().messages().attachments().get(
                        userId='me', messageId=message['id'], id=attachment_id
                    ).execute()
                    data = attachment.get('data')
                    file_data = base64.urlsafe_b64decode(data.encode('UTF-8'))
                    file_name = sanitize_filename(part.get('filename'))  # Sanitize the filename

                    with open(os.path.join(local_folder, file_name), 'wb') as local_file:
                        local_file.write(file_data)
                        attachments.append({'file_path': local_file.name, 'file_name': file_name})

                        new_document = Document(
                            name=file_name,
                            content=local_file.name,  # store the file path
                            project_id=project_id,
                        )
                        db.session.add(new_document)
            db.session.commit()

            msg['attachments'] = attachments
            emails.append(msg)

        if not emails:
            print(f'No emails found to or from {domain}.')
            return

        email_data = []

        for email in emails:
            headers = email['payload']['headers']
            snippet = email['snippet']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), None)
            sender = next((h['value'] for h in headers if h['name'] == 'From'), None)
            to = next((h['value'] for h in headers if h['name'] == 'To'), None)
            date = next(h['value'] for h in headers if h['name'] == 'Date')

            modified_snippet = f"Date: {date} From: {sender} To: {to} {snippet}"
            email_data.append({'subject': subject, 'snippet': modified_snippet, 'date_of_email': date})

            for attachment in email['attachments']:
                file_path = attachment['file_path']
                file_name = attachment['file_name']
                file_content = None

                if file_path.endswith('.pdf'):
                    file_content = extract_text_from_pdf(file_path)
                elif file_path.endswith('.docx'):
                    file_content = extract_text_from_docx(file_path)

                if file_content:
                    email_data.append({
                        'subject': file_name,
                        'snippet': file_content,
                        'date_of_email': date
                    })

        return email_data

    except HttpError as error:
        print(f'An error occurred: {error}')


# Function to generate embeddings for email subjects and snippets
def generate_email_embeddings(email_data):
    texts = []

    for email in email_data:
        texts.append(f"{email['subject']}\n\n{email['snippet']}")  # Add emails

        # Check if 'attachments' key exists in the email dictionary
        if 'attachments' in email:
            for attachment in email['attachments']:
                # try:
                #     with open(attachment['file_path'], "r", encoding='utf-8') as file:
                #         file_content = file.read()
                #     texts.append(f"{attachment['file_name']}\n\n{file_content}")  # Add attachments
                # except UnicodeDecodeError:
                #     print(f"Attempting to process non-text attachment: {attachment['file_name']}")

                extracted_text = None
                if attachment['file_name'].endswith('.pdf'):
                    extracted_text = extract_text_from_pdf(attachment['file_path'])
                elif attachment['file_name'].endswith('.docx'):
                    extracted_text = extract_text_from_docx(attachment['file_path'])

                if extracted_text is not None:
                    texts.append(f"{attachment['file_name']}\n\n{extracted_text}")

    embeddings = []
    for text in texts:
        response = openai.Embedding.create(model="text-embedding-ada-002", input=text)
        embeddings.append(response["data"][0]["embedding"])

    return embeddings


def scrape_and_store_emails(project_id, project_domain):
    email_data = scrape(project_id, project_domain)

    if email_data:
        email_embeddings = generate_email_embeddings(email_data)

        with current_app.app_context():
            for email, embedding in zip(email_data, email_embeddings):
                date_str = email[
                    'date_of_email']  # Assuming email['date_of_email'] is a string in the format 'Mon, 24 Apr 2023 16:16:58 -0500'
                # date_obj = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
                # convert date_str to python datetime object
                date_obj = parse(date_str)
                new_email = Email(subject=email['subject'], snippet=email['snippet'], embedding=embedding,
                                  date_of_email=date_obj, project_id=project_id)
                db.session.add(new_email)
                #
                # for attachment in email['attachments']:
                #     with open(attachment['file_path'], "r") as file:
                #         file_content = file.read()
                #     new_attachment = Email(subject=attachment['file_name'], snippet=file_content, embedding=embedding)
                #     db.session.add(new_attachment)
            db.session.commit()

    else:
        print("No emails found.")


if __name__ == '__main__':
    app.run()
