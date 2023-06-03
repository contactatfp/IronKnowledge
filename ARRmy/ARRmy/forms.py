from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Role', validators=[DataRequired()], choices=[('Sales Rep', 'Sales Rep'), ('Frontline Manager', 'Frontline Manager')]) # add other roles
    submit = SubmitField('Sign Up')

class CommentForm(FlaskForm):
    text = StringField('Comment', validators=[DataRequired()])
    submit = SubmitField('Post')

class AccountForm(FlaskForm):
    name = StringField('Account Name', validators=[DataRequired()])
    state = StringField('State', validators=[DataRequired()])
    submit = SubmitField('Save')

# More forms to handle other data inputs like events etc.
