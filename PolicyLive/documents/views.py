from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from . import documents_bp
from .forms import UploadDocumentForm, SearchDocumentForm
from .models import Document
from app import db


@documents_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_document():
    form = UploadDocumentForm()
    if form.validate_on_submit():
        document = Document(title=form.title.data, content=form.content.data, user_id=current_user.id)
        db.session.add(document)
        db.session.commit()
        flash('Your document has been uploaded.')
        return redirect(url_for('documents.my_documents'))
    return render_template('documents/upload.html', form=form)


@documents_bp.route('/my_documents')
@login_required
def my_documents():
    documents = current_user.documents.all()
    return render_template('documents/my_documents.html', documents=documents)


@documents_bp.route('/search', methods=['GET', 'POST'])
@login_required
def search_documents():
    form = SearchDocumentForm()
    documents = []
    if form.validate_on_submit():
        # Implement your search logic here
        pass
    return render_template('documents/search.html', form=form, documents=documents)
