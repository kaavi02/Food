from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from app.models import User

# Predefined Security Question Options
SECURITY_QUESTIONS_1 = [
    ("What was the name of your first pet?", "What was the name of your first pet?"),
    ("What is your mother's maiden name?", "What is your mother's maiden name?"),
    ("In what city were you born?", "In what city were you born?"),
    ("What was the name of your primary/elementary school?", "What was the name of your primary/elementary school?")
]

SECURITY_QUESTIONS_2 = [
    ("What was your childhood nickname?", "What was your childhood nickname?"),
    ("What is the name of your favorite movie or book?", "What is the name of your favorite movie or book?"),
    ("What was the make and model of your first vehicle?", "What was the make and model of your first vehicle?"),
    ("What is your all-time favorite food or dish?", "What is your all-time favorite food or dish?")
]

SECURITY_QUESTIONS_3 = [
    ("What was your childhood dream profession?", "What was your childhood dream profession?"),
    ("What is the name of the street you grew up on?", "What is the name of the street you grew up on?"),
    ("What was the name of your first teacher?", "What was the name of your first teacher?"),
    ("What is your favorite vacation destination?", "What is your favorite vacation destination?")
]

class RegistrationForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[DataRequired(), Length(min=10, max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Register As', choices=[
        ('customer', 'Customer'),
        ('restaurant_owner', 'Restaurant Owner'),
        ('delivery_partner', 'Delivery Partner')
    ])
    
    # 3 Security Questions for Password Recovery
    sec_q1 = SelectField('Security Question 1', choices=SECURITY_QUESTIONS_1, validators=[DataRequired()])
    sec_a1 = StringField('Answer 1', validators=[DataRequired(), Length(min=1, max=100)])
    
    sec_q2 = SelectField('Security Question 2', choices=SECURITY_QUESTIONS_2, validators=[DataRequired()])
    sec_a2 = StringField('Answer 2', validators=[DataRequired(), Length(min=1, max=100)])
    
    sec_q3 = SelectField('Security Question 3', choices=SECURITY_QUESTIONS_3, validators=[DataRequired()])
    sec_a3 = StringField('Answer 3', validators=[DataRequired(), Length(min=1, max=100)])
    
    submit = SubmitField('Sign Up')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is taken. Please choose a different one.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class ForgotPasswordForm(FlaskForm):
    email = StringField('Enter Your Registered Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Verify Email & Continue')

class ResetPasswordForm(FlaskForm):
    sec_a1 = StringField('Answer to Question 1', validators=[DataRequired()])
    sec_a2 = StringField('Answer to Question 2', validators=[DataRequired()])
    sec_a3 = StringField('Answer to Question 3', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password', message='Passwords must match.')])
    submit = SubmitField('Reset Password')
