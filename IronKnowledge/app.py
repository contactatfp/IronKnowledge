from flask import Flask, render_template, url_for, redirect, flash, request, Blueprint
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from config import Config
from forms import LoginForm, RegistrationForm, UpdateSettingsForm
from models import User, Project, db
from dashboard import dashboard_bp

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


@login.user_loader
def load_user(id):
    return db.session.get(User, int(id))


@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard_bp.dashboard_main'))
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
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


@app.route('/settings/update', methods=['POST'])
@login_required
def update_settings():
    form = UpdateSettingsForm(request.form)
    if form.validate():
        # Add logic to update user settings here
        pass
    return redirect(url_for('settings'))


if __name__ == '__main__':
    app.run()
