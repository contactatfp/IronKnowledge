from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from .models import db, User, Account, Event, Alert, Comment, Metrics, Partner
from .forms import LoginForm, RegisterForm, CommentForm, AccountForm
from werkzeug.security import generate_password_hash, check_password_hash
from dateutil.parser import parse as parse_date
from dateutil import parser

from datetime import datetime
import pytz



main = Blueprint('main', __name__)


@main.route('/')
def index():
    return render_template('index.html')


@main.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))


@main.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data, method='sha256')
        new_user = User(username=form.username.data, password=hashed_password, role=form.role.data)
        db.session.add(new_user)
        db.session.commit()
        flash('New user has been created!')
        return redirect(url_for('main.login'))
    return render_template('register.html', form=form)


@main.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if check_password_hash(user.password, form.password.data):
                login_user(user, remember=form.remember.data)
                return redirect(url_for('main.account_list'))
            else:
                flash('Invalid password.')
        else:
            flash('Username does not exist.')
    return render_template('login.html', form=form)


@main.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'Sales Rep':
        return redirect(url_for('main.sales_rep_dashboard'))
    elif current_user.role == 'Frontline Manager':
        return redirect(url_for('main.frontline_manager_dashboard'))
    # handle other roles
    else:
        return redirect(url_for('main.index'))


@main.route('/update_account', methods=['POST'])
def update_account():
    from . import db
    from .models import Account
    account_id = request.form.get('account_id')
    field = request.form.get('field')
    value = request.form.get('value')
    type = request.form.get('type')

    # Convert string to appropriate data type
    if type == 'date':
        try:
            value = parser.parse(value)
            # Convert to timezone-aware datetime
            value = value.replace(tzinfo=pytz.UTC)
        except:
            return jsonify({'status': 'error', 'message': 'Invalid date format'}), 400
    elif type in ['int', 'float']:
        try:
            value = int(value) if type == 'int' else float(value)
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Invalid number format'}), 400

    account = Account.query.get(account_id)

    if account:
        setattr(account, field, value)
        db.session.commit()
        return jsonify({'status': 'success'}), 200

    return jsonify({'status': 'error', 'message': 'Account not found'}), 400





@main.route('/frontline_manager_dashboard')
@login_required
def frontline_manager_dashboard():
    return render_template('frontline_manager_dashboard.html')


@main.route('/account_list')
@login_required
def account_list():
    accounts = current_user.accounts
    return render_template('account_list.html', accounts=accounts)


@main.route('/account/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_account(id):
    account = Account.query.get_or_404(id)
    form = AccountForm()

    if form.validate_on_submit():
        account.name = form.name.data
        account.state = form.state.data
        db.session.commit()
        flash('Account updated.')
        return redirect(url_for('main.account_list'))

    form.name.data = account.name
    form.state.data = account.state
    return render_template('edit_account.html', form=form)

# More routes to handle events, alerts, comments, metrics etc.
