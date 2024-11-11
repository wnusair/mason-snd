from flask import Blueprint, render_template, redirect, url_for, request, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from models import User, Event
from app import db, login_manager
from forms import UpdateAccountForm

auth = Blueprint('auth', __name__)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@auth.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        # Only update the password if a new one is provided
        if form.password.data:
            current_user.set_password(form.password.data)
        try:
            db.session.commit()
            flash('Your account has been updated!', 'success')
            return redirect(url_for('auth.account'))
        except IntegrityError:
            db.session.rollback()
            flash('Username or email already exists.', 'danger')
    elif request.method == 'GET':
        # Pre-fill form with current user's data
        form.username.data = current_user.username
        form.email.data = current_user.email
    return render_template('account.html', title='Account', form=form)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('main.dashboard'))
        flash('Please check your login details and try again.')
    return render_template('login.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        event_id = request.form.get('event')

        if role not in ['Event Leader', 'Chairman', 'Member']:
            flash('Invalid role selection.')
            return redirect(url_for('auth.signup'))

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists')
            return redirect(url_for('auth.signup'))

        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('Email address already exists. Please use a different email.')
            return redirect(url_for('auth.signup'))

        new_user = User(username=username, email=email, role=role)
        new_user.set_password(password)

        if event_id and (role == 'Member' or role == 'Event Leader'):
            event = Event.query.get(event_id)
            if event:
                new_user.events.append(event)

        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully. Please log in.')
        return redirect(url_for('auth.login'))

    events = Event.query.all()
    return render_template('signup.html', events=events)

def create_data_chairman(username, email, password):
    user = User.query.filter_by(username=username).first()
    if user:
        return "Username already exists"

    new_user = User(username=username, email=email, role='Data Chairman')
    new_user.set_password(password)

    db.session.add(new_user)
    db.session.commit()

    return "Data Chairman account created successfully"
