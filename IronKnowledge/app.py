from __future__ import print_function

from flask import copy_current_request_context, abort
from concurrent.futures import ThreadPoolExecutor
from flask_caching import Cache
import base64
import pinecone
import os.path
from collections import OrderedDict
from datetime import timezone, datetime

from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, serializer
from scipy.spatial import distance
import numpy as np

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
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from config import Config
from conversation import Conversation
from dashboard import dashboard_bp
from forms import LoginForm, RegistrationForm, UpdateSettingsForm, NewUserForm
from models import User, Project, db, Email, Document, Invitation
import plotly
import plotly.graph_objects as go
import json

from langchain.vectorstores import Pinecone
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.chat_models import ChatOpenAI
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain.chains import RetrievalQA
from langchain.agents import Tool
from langchain.agents import initialize_agent
from dashboard import dashboard_bp


def create_app():
    app = Flask(__name__)
    app.register_blueprint(dashboard_bp)

    app.config.from_object(Config)

    Bootstrap(app)

    db.init_app(app)

    migrate = Migrate(app, db)

    cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache'})

    with app.app_context():
        db.create_all()

    return app


with open('config.json') as f:
    config = json.load(f)

app = create_app()
login = LoginManager(app)
login.login_view = 'login'
cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache'})

app.config['MAIL_SERVER'] = 'smtp.sendgrid.net'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'apikey'
app.config['MAIL_PASSWORD'] = config['send-grid-api']

mail = Mail(app)

# models
EMBEDDING_MODEL = Config.EMBEDDING_MODEL
GPT_MODEL = Config.GPT_MODEL

embed = OpenAIEmbeddings(
    model=EMBEDDING_MODEL,
    openai_api_key=config['api_secret']
)

pinecone.init(api_key=config['pinecone-api-key'], environment=config['pinecone-environment'])
pinecone_index = pinecone.Index(index_name="ironmind")

openai.api_key = config['api_secret']

# If modifying these scopes, delete the file token.json.
SCOPES = Config.GMAIL_SCOPES


@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    form = NewUserForm()
    if form.validate_on_submit():
        # Check if user already exists in the database
        project_id = request.form.get('project_id')
        user = User.query.filter_by(email=form.email.data).first()
        project = Project.query.get_or_404(project_id)
        if user is not None:
            # add user to project with project_id
            project = Project.query.get_or_404(project_id)
            project.users.append(user)
            db.session.commit()
        else:
            # Send an invitation to the new user if they are not in the system yet.
            invitation = Invitation(email=form.email.data, project_id=project_id)
            db.session.add(invitation)
            db.session.commit()
            send_invitation_email(invitation, project.name)

        flash('Congratulations, you added a new user!')
        return redirect(url_for('dashboard_bp.dashboard_main'))
    print(form.errors)
    return render_template('add_user.html', form=form)


def generate_invitation_token(email, project_id):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return serializer.dumps((email, project_id), salt=app.config['SECURITY_PASSWORD_SALT'])


def send_invitation_email(invitation, project_name):
    project_id = Project.query.filter_by(name=project_name).first().id
    token = generate_invitation_token(invitation.email, project_id)

    message = Mail(
        from_email='contact@fakepicasso.com',
        to_emails=[invitation.email],
        subject=f'''You have been added to {project_name}''',
        html_content=f'''You have been invited to join the project {project_name}.
        Please click on the following link to accept the invitation:
        {url_for('accept_invitation', token=token, _external=True)}
        ''')
    try:
        sg = SendGridAPIClient(config['send-grid-api'])
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
        print(e.message)


def verify_invitation_token(token):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        email, project_id = serializer.loads(
            token,
            salt=app.config['SECURITY_PASSWORD_SALT'],
            max_age=3600
        )
    except:
        return False
    return email, project_id


@app.route('/accept_invitation/<token>')
def accept_invitation(token):
    result = verify_invitation_token(
        token)  # Function to verify the token and get the invitation id. You need to implement this.
    if not result:
        flash('That is an invalid or expired token')
        return redirect(url_for('index'))

    # Unpack the email and project_id
    email, project_id = result

    invitation = Invitation.query.filter_by(email=email, project_id=project_id).first()
    if invitation is None:
        flash('Invalid invitation')
        return redirect(url_for('index'))

    # Redirect the user to the registration page with the token as a parameter
    return redirect(url_for('register', token=token))


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

    trainedAsk = ask(project_id, user_input)
    trainedAsk_html = trainedAsk.replace('\n', '<br/>')
    trainedAsk_html = trainedAsk_html.replace('\t', '&nbsp;&nbsp;&nbsp;&nbsp;')

    return jsonify({"assistant_message": trainedAsk_html})


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
    token = request.args.get('token')
    if token is not None:
        result = verify_invitation_token(token)
        if not result:
            flash('Invalid or expired token')
            return redirect(url_for('index'))
        # Unpack the email and project_id
        email, project_id = result

        # Pre-populate email field
        form.email.data = email
        form.token.data = token
        form.project_id.data = project_id
    email = form.email.data

    if form.validate_on_submit():
        # get token from url
        token = form.token.data
        project_id = form.project_id.data
        user = User(email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        if token is not None:
            # If there's an invitation, add user to the project and delete the invitation
            invitation = Invitation.query.filter_by(email=email, project_id=project_id).first()
            if invitation is not None:
                project = Project.query.get_or_404(invitation.project_id)
                project.users.append(user)
                db.session.delete(invitation)
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
        top_n: int = 100
) -> tuple[list[str], list[float]]:
    """Returns a list of strings and relatednesses, sorted from most related to least."""
    df = get_emails_dataframe(project_id)
    print(f"Dataframe size after filtering by project_id: {df.shape}")

    query_embedding_response = openai.Embedding.create(
        model=EMBEDDING_MODEL,
        input=query,
    )
    query_embedding = np.array(query_embedding_response["data"][0]["embedding"])

    # Convert list of embeddings to a 2D array
    embeddings_array = np.vstack(df["embedding"].values)

    # Calculate cosine distances in a vectorized way
    cosine_distances = distance.cdist([query_embedding], embeddings_array, 'cosine')[0]

    # Compute relatedness as 1 - cosine distance
    relatednesses = 1 - cosine_distances

    # Create tuples of (email, relatedness)
    strings_and_relatednesses = list(zip(df["email"], relatednesses))

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
        model: str,
        token_budget: int
) -> str:
    """Return a message for GPT, with relevant source texts pulled from a dataframe."""
    strings, relatednesses = strings_ranked_by_relatedness(query, project_id)
    introduction = 'Use the emails and attachments below. If the answer cannot be found in the emails or attachments, explain why not and what the closest answer would be.'
    question = f"\n\nYou are now an expert on the {Project.query.get_or_404(project_id).name} project: {query}"
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


# chat completion llm
# llm = ChatOpenAI(
#         openai_api_key=config['api_secret'],
#         model_name=GPT_MODEL,
#         temperature=0.0,
#         max_tokens=3000,
# )
#     # conversational memory
# conversational_memory = ConversationBufferWindowMemory(
#         memory_key='chat_history',
#         k=5,
#         return_messages=True
#
# )
def get_emails_dataframe(project_id):
    emails_cache_key = f"emails_{project_id}"
    df = cache.get(emails_cache_key)

    if df is None:
        emails = Email.query.filter_by(project_id=project_id).all()
        data = [{
            "email": email.subject + " " + email.snippet,
            "embedding": email.embedding,
            "project_id": email.project_id,
        } for email in emails]

        df = pd.DataFrame(data)
        cache.set(emails_cache_key, df)

    return df


def ask(
        project_id: int,
        query: str,
        model: str = GPT_MODEL,
        token_budget: int = 4097 - 500,
        print_message: bool = False,
) -> str:
    # get all emails from the project

    message = query_message(project_id, query, model=model, token_budget=token_budget)
    if print_message:
        print(message)

    # ******************* LANGCHAIN *******************
    # text_field = 'snippet'
    # vector_namespace = Project.query.get_or_404(project_id).name
    # vectorstore = Pinecone(
    #     pinecone_index, embed.embed_query, text_field, namespace=vector_namespace,
    # )
    #
    # # retrieval qa chain
    # qa = RetrievalQA.from_chain_type(
    #     llm=llm,
    #     chain_type="stuff",
    #     retriever=vectorstore.as_retriever()
    # )
    #
    # tools = [
    #     Tool(
    #         name='Knowledge Base',
    #         func=qa.run,
    #         description=(
    #             f'You are answering questions about the ${Project.query.get_or_404(project_id).name} '
    #             'Answer based on the documents you have.'
    #         )
    #     )
    # ]
    # agent = initialize_agent(
    #     agent='chat-conversational-react-description',
    #     tools=tools,
    #     llm=llm,
    #     verbose=True,
    #     max_iterations=3,
    #     early_stopping_method='generate',
    #     memory=conversational_memory
    # )
    #
    # message = agent(query)

    # ******************* PINECONE *******************
    # vector_namespace = Project.query.get_or_404(project_id).name
    # res = openai.Embedding.create(
    #     input=[query],
    #     engine=EMBEDDING_MODEL
    # )
    #
    # # retrieve from Pinecone
    # xq = res['data'][0]['embedding']
    # # get relevant contexts (including the questions)
    # res = pinecone_index.query(namespace=vector_namespace, top_k=10, include_metadata=True, include_values=False, vector=xq)
    # contexts = [
    #     # get snippet from metadata in x for x in res['matches'] but not if its a datetime object
    #     x['metadata']['snippet'] for x in res['matches']
    #
    # ]
    #
    # prompt_start = (
    #         "Answer the question based on the context below.\n\n"+
    #         "Context:\n"
    # )
    # prompt_end = (
    #     f"\n\nQuestion: {query}\nAnswer:"
    # )
    #
    # for i in range(1, len(contexts)):
    #     if len("\n\n---\n\n".join(contexts[:i])) >= token_budget:
    #         prompt = (
    #                 prompt_start +
    #                 "\n\n---\n\n".join(contexts[:i-1]) +
    #                 prompt_end
    #         )
    #         break
    #     elif i == len(contexts)-1:
    #         prompt = (
    #                 prompt_start +
    #                 "\n\n---\n\n".join(contexts) +
    #                 prompt_end
    #         )

    # Initialize the conversation when the session begins
    conversation = Conversation(project_id)

    # Add the user's message to the conversation
    conversation.add_user_message(message)

    # Generate the model's response
    response = openai.ChatCompletion.create(
        model=model,
        messages=list(conversation.messages),  # change to prmopt if using pinecone
        temperature=1
    )

    # Extract the response message
    response_message = response['choices'][0]['message']['content']

    # Try to find a document relevant to the response
    document = get_relevant_document(response_message, project_id)
    if document is not None:
        path, filename = os.path.split(document.content)
        document_link = url_for('dashboard_bp.serve_file', path=path, filename=filename)
        response_message += f'<br><br> You can view the related document at <a href="{document_link}">{filename}</a>.'

    # Try to find an email relevant to the response
    email = get_relevant_email(response_message, project_id)
    if email is not None:
        email_link = url_for('dashboard_bp.email', email_id=email.id)
        response_message += f'<br><br> You can view the related email at <a href="{email_link}">email thread</a>.'

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


# def scrape(project_id, project_domain):
#     local_folder = 'attachments'
#     latest_email_date = (
#         db.session.query(func.max(Email.date_of_email))
#         .filter(Email.project_id == project_id)
#         .scalar()
#     )
#
#     if latest_email_date is not None:
#         latest_email_date = latest_email_date.astimezone(timezone.utc)
#         latest_email_date_str = latest_email_date.strftime("%Y/%m/%d")
#     else:
#         latest_email_date_str = ""
#
#     if not os.path.exists(local_folder):
#         os.makedirs(local_folder)
#
#     creds = None
#     if os.path.exists('token.json'):
#         creds = Credentials.from_authorized_user_file('token.json', SCOPES)
#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             creds.refresh(Request())
#         else:
#             flow = InstalledAppFlow.from_client_secrets_file(
#                 'credentials.json', SCOPES)
#             creds = flow.run_local_server(port=0)
#         with open('token.json', 'w') as token:
#             token.write(creds.to_json())
#
#     try:
#         service = build('gmail', 'v1', credentials=creds)
#         domain = project_domain
#
#         query = f"to:{domain} OR from:{domain}"
#         if latest_email_date_str:
#             query += f" after:{latest_email_date_str}"
#
#         emails = []
#         result = service.users().messages().list(userId='me', q=query).execute()
#         messages = result.get('messages', [])
#
#         for message in messages:
#             msg = service.users().messages().get(userId='me', id=message['id']).execute()
#
#             attachments = []
#             for part in msg.get('payload', {}).get('parts', []):
#                 if part.get('filename') and part.get('body', {}).get('attachmentId'):
#                     attachment_id = part['body']['attachmentId']
#                     attachment = service.users().messages().attachments().get(
#                         userId='me', messageId=message['id'], id=attachment_id
#                     ).execute()
#                     data = attachment.get('data')
#                     file_data = base64.urlsafe_b64decode(data.encode('UTF-8'))
#                     file_name = sanitize_filename(part.get('filename'))  # Sanitize the filename
#
#                     with open(os.path.join(local_folder, file_name), 'wb') as local_file:
#                         local_file.write(file_data)
#                         attachments.append({'file_path': local_file.name, 'file_name': file_name})
#
#                         new_document = Document(
#                             name=file_name,
#                             content=local_file.name,  # store the file path
#                             project_id=project_id,
#                         )
#                         db.session.add(new_document)
#             db.session.commit()
#
#             msg['attachments'] = attachments
#             emails.append(msg)
#
#         if not emails:
#             print(f'No emails found to or from {domain}.')
#             return
#
#         email_data = []
#
#         for email in emails:
#             headers = email['payload']['headers']
#             snippet = email['snippet']
#             subject = next((h['value'] for h in headers if h['name'] == 'Subject'), None)
#             sender = next((h['value'] for h in headers if h['name'] == 'From'), None)
#             to = next((h['value'] for h in headers if h['name'] == 'To'), None)
#             date = next(h['value'] for h in headers if h['name'] == 'Date')
#
#             modified_snippet = f"Date: {date} From: {sender} To: {to} {snippet}"
#             email_data.append({'subject': subject, 'snippet': modified_snippet, 'date_of_email': date})
#
#             for attachment in email['attachments']:
#                 file_path = attachment['file_path']
#                 file_name = attachment['file_name']
#                 file_content = None
#
#                 if file_path.endswith('.pdf'):
#                     file_content = extract_text_from_pdf(file_path)
#                 elif file_path.endswith('.docx'):
#                     file_content = extract_text_from_docx(file_path)
#
#                 if file_content:
#                     email_data.append({
#                         'subject': file_name,
#                         'snippet': file_content,
#                         'date_of_email': date
#                     })
#
#         return email_data
#
#     except HttpError as error:
#         print(f'An error occurred: {error}')


# Function to generate embeddings for email subjects and snippets
def scrape(project_id, project_domain):
    with current_app.app_context():
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
            page_token = None
            while True:
                result = service.users().messages().list(userId='me', q=query, pageToken=page_token).execute()
                messages = result.get('messages', [])
                page_token = result.get('nextPageToken')

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

                if not page_token:
                    break

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


def generate_email_embeddings(email_data):
    with current_app.app_context():
        texts = []

        for email in email_data:
            texts.append(f"{email['subject']}\n\n{email['snippet']}")  # Add emails

            # Check if 'attachments' key exists in the email dictionary
            if 'attachments' in email:
                for attachment in email['attachments']:
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
            # embeddings.append(response["data"][0]["embedding"])
            embedding_values = list(response['data'][0]['embedding'])
            embeddings.append(embedding_values)

        return embeddings


@app.route('/project/<int:project_id>/members')
def project_members(project_id):
    project = Project.query.get(project_id)
    # users are all the members of this project in project.users table
    users = User.query.join(Project.users).filter(Project.id == project_id).all()
    invitations = Invitation.query.filter_by(project_id=project_id).all()

    if project is None:
        abort(404)  # Not found
    return render_template('members.html', project=project, users=users, invitations=invitations)


def scrape_and_store_emails(project_id, project_domain):
    @copy_current_request_context
    def scrape_with_context():
        return scrape(project_id, project_domain)

    @copy_current_request_context
    def generate_email_embeddings_with_context(email_data):
        return generate_email_embeddings(email_data)

    with ThreadPoolExecutor() as executor:
        email_data_future = executor.submit(scrape_with_context)
        email_data = email_data_future.result()

        email_embeddings_future = executor.submit(generate_email_embeddings_with_context, email_data)
        email_embeddings = email_embeddings_future.result()

        # vector_namespace = Project.query.get_or_404(project_id).name
        new_emails = []
        # vectors = []

        with current_app.app_context():
            for count, (email, embedding) in enumerate(zip(email_data, email_embeddings), 1):
                date_str = email['date_of_email']
                date_obj = parse(date_str)
                new_emails.append(Email(subject=email['subject'], snippet=email['snippet'],
                                        embedding=embedding, date_of_email=date_obj, project_id=project_id))

                # vector_id = vector_namespace + str(count)
                # date_of_email_str = date_obj.strftime("%Y-%m-%d %H:%M:%S")
                # vectors.append({'id': vector_id, 'values': embedding,
                #                 'metadata': {'snippet': email['snippet'], 'subject': email['subject'],
                #                              'date_of_email': date_of_email_str}})

            db.session.bulk_save_objects(new_emails)
            db.session.commit()

            # pinecone_index.upsert(vectors=vectors, namespace=vector_namespace)


if __name__ == '__main__':
    app.run()
