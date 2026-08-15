from flask import render_template, url_for, flash, redirect, request, session
from flask_login import login_user, current_user, logout_user, login_required
from app import db, bcrypt
from app.models import User
from app.auth import auth
from app.auth.forms import RegistrationForm, LoginForm, ForgotPasswordForm, ResetPasswordForm
from datetime import datetime

@auth.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('customer.home'))
        
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        
        # Hash answers (normalized to lowercase & stripped for case-insensitive verification)
        hashed_a1 = bcrypt.generate_password_hash(form.sec_a1.data.strip().lower()).decode('utf-8')
        hashed_a2 = bcrypt.generate_password_hash(form.sec_a2.data.strip().lower()).decode('utf-8')
        hashed_a3 = bcrypt.generate_password_hash(form.sec_a3.data.strip().lower()).decode('utf-8')
        
        user = User(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data.strip().lower(),
            phone=form.phone.data,
            password_hash=hashed_password,
            role=form.role.data,
            sec_q1=form.sec_q1.data,
            sec_a1=hashed_a1,
            sec_q2=form.sec_q2.data,
            sec_a2=hashed_a2,
            sec_q3=form.sec_q3.data,
            sec_a3=hashed_a3
        )
        db.session.add(user)
        db.session.commit()
        flash('Account created successfully with recovery questions! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/register.html', title='Register', form=form)

@auth.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif current_user.role == 'restaurant_owner':
            return redirect(url_for('restaurant.dashboard'))
        elif current_user.role == 'delivery_partner':
            return redirect(url_for('delivery.dashboard'))
        else:
            return redirect(url_for('customer.home'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and bcrypt.check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember.data)
            user.last_login = datetime.utcnow()
            db.session.commit()
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            if user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif user.role == 'restaurant_owner':
                return redirect(url_for('restaurant.dashboard'))
            elif user.role == 'delivery_partner':
                return redirect(url_for('delivery.dashboard'))
            else:
                return redirect(url_for('customer.home'))
        else:
            flash('Login Unsuccessful. Please check email and password.', 'danger')
            
    return render_template('auth/login.html', title='Login', form=form)

@auth.route("/forgot-password", methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('customer.home'))
        
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user:
            if not user.sec_q1 or not user.sec_a1:
                flash('This account does not have security questions configured. Please contact support.', 'warning')
                return redirect(url_for('auth.login'))
            session['reset_email'] = user.email
            return redirect(url_for('auth.reset_password'))
        else:
            flash('No account found with that email address.', 'danger')
            
    return render_template('auth/forgot_password.html', title='Forgot Password', form=form)

@auth.route("/reset-password", methods=['GET', 'POST'])
def reset_password():
    if current_user.is_authenticated:
        return redirect(url_for('customer.home'))
        
    reset_email = session.get('reset_email')
    if not reset_email:
        flash('Session expired or invalid request. Please enter your email first.', 'warning')
        return redirect(url_for('auth.forgot_password'))
        
    user = User.query.filter_by(email=reset_email).first()
    if not user:
        flash('User account not found.', 'danger')
        return redirect(url_for('auth.forgot_password'))
        
    form = ResetPasswordForm()
    if form.validate_on_submit():
        ans1 = form.sec_a1.data.strip().lower()
        ans2 = form.sec_a2.data.strip().lower()
        ans3 = form.sec_a3.data.strip().lower()
        
        valid_1 = bcrypt.check_password_hash(user.sec_a1, ans1)
        valid_2 = bcrypt.check_password_hash(user.sec_a2, ans2)
        valid_3 = bcrypt.check_password_hash(user.sec_a3, ans3)
        
        if valid_1 and valid_2 and valid_3:
            user.password_hash = bcrypt.generate_password_hash(form.new_password.data).decode('utf-8')
            db.session.commit()
            session.pop('reset_email', None)
            flash('Your password has been successfully reset! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Security answers do not match. Please verify your answers and try again.', 'danger')
            
    return render_template(
        'auth/reset_password.html',
        title='Reset Password',
        form=form,
        q1=user.sec_q1,
        q2=user.sec_q2,
        q3=user.sec_q3,
        user_email=user.email
    )

@auth.route("/logout")
def logout():
    logout_user()
    session.pop('reset_email', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('customer.home'))
