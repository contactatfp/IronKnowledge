from flask_wtf import FlaskForm
from wtforms import FileField, SubmitField, StringField
from wtforms.validators import DataRequired


class UploadDocumentForm(FlaskForm):
    file = FileField("Upload Document", validators=[DataRequired()])
    submit = SubmitField("Upload")


class SearchDocumentForm(FlaskForm):
    search_query = StringField("Search", validators=[DataRequired()])
    submit = SubmitField("Search")
