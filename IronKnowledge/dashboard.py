import io
from os import abort
from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import current_user
from models import Project, db, Document

dashboard_bp = Blueprint('dashboard_bp', __name__)


@dashboard_bp.route('/dashboard_main', methods=['GET'])
def dashboard_main():
    projects = Project.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', projects=projects)


@dashboard_bp.route('/dashboard/<int:project_id>', methods=['GET'])
def project_details(project_id):
    project = Project.query.get_or_404(project_id)
    if project.user_id != current_user.id:
        abort(403)
    return render_template('project_details.html', project=project)


@dashboard_bp.route('/dashboard/<project_id>')
def dashboard_project(project_id):
    from project import get_project_details
    from version_control import get_version_history

    project = get_project_details(project_id)
    if not project:
        return redirect(url_for('index'))
    version_history = get_version_history(project_id)
    return render_template('dashboard.html', project=project, version_history=version_history)


@dashboard_bp.route('/dashboard/update/<project_id>', methods=['POST'])
def update_summary(project_id):
    from summarizer import save_summary
    from version_control import create_version

    action = request.form.get('action')
    updated_summary = request.form.get('summary')

    if action == 'approve':
        save_summary(project_id, updated_summary)
        create_version(project_id)
    elif action == 'adjust':
        save_summary(project_id, updated_summary)
    elif action == 'delete':
        save_summary(project_id, '')

    return redirect(url_for('dashboard_bp.dashboard_project', project_id=project_id))


@dashboard_bp.route('/dashboard/add', methods=['GET', 'POST'])
def add_project():
    if request.method == 'POST':
        project_name = request.form.get('project_name')
        if project_name:
            new_project = Project(name=project_name, user_id=current_user.id)
            db.session.add(new_project)
            db.session.commit()
            return redirect(url_for('dashboard_bp.dashboard_main'))
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

            # create a new document object
            new_document = Document(name=document_name, project_id=project_id, content=content)

            # add the new document to the database and commit the transaction
            db.session.add(new_document)
            db.session.commit()

            # redirect the user to the project details page
            return redirect(url_for('dashboard_bp.project_details', project_id=project_id))

    return render_template('add_document.html', project=project, project_id=project_id)


@dashboard_bp.route('/dashboard/document/<int:document_id>', methods=['GET'])
def document(document_id):
    document = Document.query.get_or_404(document_id)
    project = Project.query.get_or_404(document.project_id)
    if project.user_id != current_user.id:
        abort(403)
    return render_template('document.html', document=document)


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
