from __future__ import print_function
import pandas as pd
import tiktoken
from flask import Flask, render_template, url_for, redirect, flash, request, Blueprint, jsonify, current_app, send_file
from flask_bootstrap import Bootstrap
from flask_migrate import Migrate
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from scipy import spatial
import fitz
from config import Config
from forms import LoginForm, RegistrationForm, UpdateSettingsForm
from dashboard import dashboard_bp
import docx2txt
import base64
from flask import current_app
import json
import os.path
import openai
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from models import User, Project, db, Email
from datetime import datetime

app = Flask(__name__)
app.register_blueprint(dashboard_bp)

app.app_context().push()
app.config.from_object(Config)
bootstrap = Bootstrap(app)
db.init_app(app)
migrate = Migrate(app, db)
login = LoginManager(app)
login.login_view = 'login'
app.app_context().push()

# models
EMBEDDING_MODEL = "text-embedding-ada-002"
GPT_MODEL = "gpt-3.5-turbo"

with open('config.json') as f:
    config = json.load(f)

openai.api_key = config['api_secret']

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
emails = Email.query.all()

data = [{
    "email": email.subject + " " + email.snippet,
    "embedding": email.embedding,
    "project_id": email.project_id,
} for email in emails]

df = pd.DataFrame(data)


@login.user_loader
def load_user(id):
    return db.session.get(User, int(id))


@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard_bp.dashboard_main'))
    return render_template('index.html')


# @app.route('/refresh_model')
# @login_required
# def refresh_model():
#     return render_template('refresh_model.html')


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


# @app.route('/settings/update', methods=['POST'])
# @login_required
# def update_settings():
#     form = UpdateSettingsForm(request.form)
#     if form.validate():
#         # Add logic to update user settings here
#         pass
#     return redirect(url_for('settings'))


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
    query_embedding_response = openai.Embedding.create(
        model=EMBEDDING_MODEL,
        input=query,
    )
    query_embedding = query_embedding_response["data"][0]["embedding"]
    strings_and_relatednesses = [
        (row["email"], relatedness_fn(query_embedding, row["embedding"]))  # Change 'text' to 'email' here
        for i, row in df.iterrows()
    ]
    strings_and_relatednesses.sort(key=lambda x: x[1], reverse=True)
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
    question = f"\n\nQuestion: {query}"
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


def ask(
        project_id: int,
        query: str,
        df: pd.DataFrame = df,
        model: str = GPT_MODEL,
        token_budget: int = 4096 - 500,
        print_message: bool = False,
) -> str:
    """Answers a query using GPT and a dataframe of relevant texts and embeddings."""
    message = query_message(project_id, query, df, model=model, token_budget=token_budget)
    if print_message:
        print(message)

    company_name = Project.query.get_or_404(project_id).name
    messages = [
        {"role": "system", "content": f"You answer questions about the ${company_name}."},
        {"role": "user", "content": message},
    ]
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=0
    )
    response_message = response["choices"][0]["message"]["content"]
    print(response_message)
    return response_message


def scrape(project_id, project_domain):
    local_folder = 'attachments'
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
                    file_name = part.get('filename')

                    with open(os.path.join(local_folder, file_name), 'wb') as local_file:
                        local_file.write(file_data)
                        attachments.append({'file_path': local_file.name, 'file_name': file_name})

            msg['attachments'] = attachments
            emails.append(msg)

        if not emails:
            print(f'No emails found to or from {domain}.')
            return

        email_data = []

        for email in emails:
            headers = email['payload']['headers']
            snippet = email['snippet']
            subject = next(h['value'] for h in headers if h['name'] == 'Subject')
            sender = next(h['value'] for h in headers if h['name'] == 'From')
            to = next(h['value'] for h in headers if h['name'] == 'To')
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
                date_obj = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
                # date_formatted = date_obj.strftime("%Y-%m-%d %H:%M:%S.%f")
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
