import re
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, ValidationError

_UTM_EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@graduate\.utm\.my$')
_SYMBOL_RE = re.compile(r'[!@#$%^&*()\-_=+\[\]{}|;:,.<>?/]')


class RegistrationForm(FlaskForm):
    email = StringField('UTM Email', validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=12)])
    submit = SubmitField('Register')

    def validate_email(self, field):
        if not _UTM_EMAIL_RE.match(field.data.strip()):
            raise ValidationError('Only @graduate.utm.my addresses are permitted.')

    def validate_password(self, field):
        pw = field.data
        errors = []
        if not re.search(r'[A-Z]', pw):
            errors.append('one uppercase letter')
        if not re.search(r'[a-z]', pw):
            errors.append('one lowercase letter')
        if not re.search(r'\d', pw):
            errors.append('one digit')
        if not _SYMBOL_RE.search(pw):
            errors.append('one special character')
        if errors:
            raise ValidationError(f'Password must contain at least: {", ".join(errors)}.')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class OTPForm(FlaskForm):
    token = StringField('Verification Code', validators=[DataRequired(), Length(min=6, max=6)])
    submit = SubmitField('Verify')
