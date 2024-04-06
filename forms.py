from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo
from flask_wtf.file import FileField, FileAllowed 

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

class BugReportForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    severity = SelectField('Severity', choices=[('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High')], default='Low')
    status = SelectField('Status', choices=[('Open', 'Open'), ('Closed', 'Closed')], default='Open')
    submit = SubmitField('Submit Bug')
    screenshot = FileField('Upload Screenshot', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])
    screen_recording = FileField('Upload Screen Recording', validators=[FileAllowed(['mp4', 'webm'], 'Videos only!')])

class EditBugForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    status = SelectField('Status', choices=[('Open', 'Open'), ('Closed', 'Closed')])
    submit = SubmitField('Update Bug')

class BugSearchForm(FlaskForm):
    keyword = StringField('Keyword')
    status = SelectField('Status', choices=[('All', 'All'), ('Open', 'Open'), ('Closed', 'Closed')], default='All')
    severity = SelectField('Severity', choices=[('All', 'All'), ('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High')], default='All')
    submit = SubmitField('Search')

