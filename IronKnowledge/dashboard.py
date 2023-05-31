import io
import os
from os import abort
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory
from flask_login import current_user
from sqlalchemy import func

from models import Project, db, Document, Email

dashboard_bp = Blueprint('dashboard_bp', __name__)


@dashboard_bp.route('/dashboard_main', methods=['GET'])
def dashboard_main():
    projects = Project.query.filter_by(user_id=current_user.id).all()
    # search for user id in project_user table in column user_id if there is a match, then get the project_id in that row and add the project with that project id to projects
    otherProjects = Project.query.filter(Project.users.any(id=current_user.id)).all()
    for project in otherProjects:
        if project not in projects:
            projects.append(project)

    return render_template('dashboard.html', projects=projects)


@dashboard_bp.route('/dashboard/<int:project_id>', methods=['GET'])
def project_details(project_id):
    project = Project.query.get_or_404(project_id)
    project_domain = Project.query.get_or_404(project_id).company_domain
    if project.user_id != current_user.id:
        abort(403)
    return render_template('project_details.html', project=project, domain=project_domain)

@dashboard_bp.route('/document/<int:document_id>')
def document(document_id):
    document = Document.query.get_or_404(document_id)
    path, filename = os.path.split(document.content)
    return render_template("document.html", path=path, filename=filename)

@dashboard_bp.route('/<path:path>/<filename>')
def serve_file(path, filename):
    return send_from_directory('attachments/', filename)

@dashboard_bp.route('/email/<int:email_id>')
def email(email_id):
    email = Email.query.get_or_404(email_id)
    return render_template("email.html", email=email)

# route for all project documents. takes in project id and returns all documents for that project
@dashboard_bp.route('/dashboard/<int:project_id>/documents', methods=['GET'])
def project_documents(project_id):
    project = Project.query.get_or_404(project_id)
    documents = Document.query.filter_by(project_id=project_id).all()
    return render_template('project_documents.html', project=project, documents=documents)

@dashboard_bp.route('/project/<int:project_id>/summary', methods=['GET', 'POST'])
def project_summary(project_id):
    project = Project.query.get_or_404(project_id)
    if request.method == 'POST':
        data = request.get_json()
        action = data.get('action')  # Get the action from the request

        # Check the action type
        if action == 'update_summary':
            my_summary = data.get('updated_summary')
            print(my_summary)
            project.summary = my_summary
            db.session.commit()
            return redirect(url_for('dashboard_bp.project_summary', project_id=project.id))

    start_date = db.session.query(func.min(Email.date_of_email)).filter_by(project_id=project.id).first()
    project.start_date = start_date[0] if start_date else None

    return render_template('project_summary.html', project=project)



@dashboard_bp.route('/dashboard/<project_id>')
def dashboard_project(project_id):
    from project import get_project_details
    from version_control import get_version_history

    project = get_project_details(project_id)
    if not project:
        return redirect(url_for('index'))
    version_history = get_version_history(project_id)
    return render_template('dashboard.html', project=project, version_history=version_history)


# @dashboard_bp.route('/dashboard/update/<project_id>', methods=['POST'])
# def update_summary(project_id):
#     from summarizer import save_summary
#     from version_control import create_version
#
#     action = request.form.get('action')
#     updated_summary = request.form.get('summary')
#
#     if action == 'approve':
#         save_summary(project_id, updated_summary)
#         create_version(project_id)
#     elif action == 'adjust':
#         save_summary(project_id, updated_summary)
#     elif action == 'delete':
#         save_summary(project_id, '')
#
#     return redirect(url_for('dashboard_bp.dashboard_project', project_id=project_id))


@dashboard_bp.route('/dashboard/add', methods=['GET', 'POST'])
def add_project():
    if request.method == 'POST':
        project_name = request.form.get('project_name')
        company_domain = request.form.get('company_domain')  # Get the value of the company_domain field
        keyword = request.form.get('keyword')  # Get the value of the keyword field

        if project_name and company_domain and keyword:  # Check if all fields are filled
            new_project = Project(name=project_name, user_id=current_user.id, company_domain=company_domain, keyword=keyword)
            db.session.add(new_project)
            new_project.users.append(current_user)
            db.session.commit()
            return redirect(url_for('dashboard_bp.dashboard_main'))
        else:
            flash('Please fill in all fields.')  # Display an error message if any field is missing

    return render_template('add_project.html')



@dashboard_bp.route('/dashboard/add_document/<int:project_id>', methods=['GET', 'POST'])
def add_document(project_id):
    project = Project.query.get_or_404(project_id)

    if request.method == 'POST':
        # get the uploaded file
        file = request.files.get('document_file')

        # check if the file exists and is a text file
        if file and file.content_type.startswith('text'):
            # read the file content
            content = io.StringIO(file.read().decode('utf-8')).getvalue()

            # get the document name from the form
            document_name = request.form.get('document_name')

            if not document_name:
                document_name = file.filename

            # create a new document object
            new_document = Document(name=document_name, project_id=project_id, content=content)

            # add the new document to the database and commit the transaction
            db.session.add(new_document)
            db.session.commit()

            # Fine-tune the model for the project
            # fine_tune_project_model(project_id)

            # redirect the user to the project details page
            return redirect(url_for('dashboard_bp.project_details', project_id=project_id))
    #     otherwise if input is text only commit it to the database
        elif request.form.get('document_content'):
            document_name = request.form.get('document_name')
            document_content = request.form.get('document_content')
            if document_name:
                new_document = Document(name=document_name, project_id=project_id, content=document_content)
                db.session.add(new_document)
                db.session.commit()
                return redirect(url_for('dashboard_bp.project_details', project_id=project_id))

    return render_template('add_document.html', project=project, project_id=project_id)


# @dashboard_bp.route('/dashboard/document/<int:document_id>', methods=['GET'])
# def document(document_id):
#     document = Document.query.get_or_404(document_id)
#     project = Project.query.get_or_404(document.project_id)
#     if project.user_id != current_user.id:
#         abort(403)
#     return render_template('document.html', document=document)


@dashboard_bp.route('/dashboard/edit_document/<int:document_id>', methods=['GET', 'POST'])
def edit_document(document_id):
    document = Document.query.get_or_404(document_id)
    project = Project.query.get_or_404(document.project_id)
    if project.user_id != current_user.id:
        abort(403)

    if request.method == 'POST':
        document_name = request.form.get('document_name')
        document_content = request.form.get('document_content')
        if document_name:
            document.name = document_name
            document.content = document_content
            db.session.commit()
            return redirect(url_for('dashboard_bp.project_details', project_id=project.id))

    return render_template('edit_document.html', document=document)


@dashboard_bp.route('/dashboard/delete/<project_id>')
def delete_project(project_id):
    project = Project.query.get(project_id)
    if project and project.user_id == current_user.id:
        db.session.delete(project)
        db.session.commit()
    return redirect(url_for('dashboard_bp.dashboard_main'))
