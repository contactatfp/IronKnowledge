from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from . import faq_bp
from .forms import GenerateFAQForm
from .models import FAQ
from app import db

@faq_bp.route('/generate', methods=['GET', 'POST'])
@login_required
def generate_faq():
    form = GenerateFAQForm()
    if form.validate_on_submit():
        faq = FAQ(title=form.title.data, content=form.content.data, user_id=current_user.id)
        db.session.add(faq)
        db.session.commit()
        flash('Your FAQ has been generated.')
        return redirect(url_for('faq.my_faqs'))
    return render_template('faq/generate.html', form=form)

@faq_bp.route('/my_faqs')
@login_required
def my_faqs():
    faqs = current_user.faqs.all()
    return render_template('faq/my_faqs.html', faqs=faqs)


