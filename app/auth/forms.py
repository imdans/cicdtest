"""
Authentication forms
"""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional, EqualTo


class LoginForm(FlaskForm):
    """Login form"""
    email = StringField('Email', validators=[
        DataRequired(),
        Email(message='Please enter a valid email address')
    ])
    password = PasswordField('Password', validators=[
        DataRequired()
    ])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Log In')


class MFAVerifyForm(FlaskForm):
    """MFA verification form"""
    code = StringField('MFA Code', validators=[
        DataRequired(),
        Length(min=6, max=6)
    ])
    submit = SubmitField('Verify')


class ProfileForm(FlaskForm):
    """User profile edit form"""
    first_name = StringField('First Name', validators=[
        Optional(),
        Length(max=64)
    ])
    last_name = StringField('Last Name', validators=[
        Optional(),
        Length(max=64)
    ])
    email = StringField('Email', validators=[
        DataRequired(),
        Email(message='Please enter a valid email address')
    ])
    current_password = PasswordField('Current Password', validators=[
        Optional()
    ])
    new_password = PasswordField('New Password', validators=[
        Optional(),
        Length(min=8, message='Password must be at least 8 characters')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        Optional(),
        EqualTo('new_password', message='Passwords must match')
    ])
    submit = SubmitField('Update Profile')


class AcceptInvitationForm(FlaskForm):
    """Accept invitation form"""
    full_name = StringField('Full Name', validators=[
        DataRequired(),
        Length(min=2, max=128, message='Full name must be between 2 and 128 characters')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters')
    ])
    password_confirm = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Activate Account')
