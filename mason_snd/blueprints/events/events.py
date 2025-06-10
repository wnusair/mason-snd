from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from mason_snd.extensions import db
from mason_snd.models.events import Event
from mason_snd.models.auth import User

from werkzeug.security import generate_password_hash, check_password_hash

events_bp = Blueprint('events', __name__, template_folder='templates')

@events_bp.route('/')
def index():
    user_id = session.get('user_id')
    if not user_id:
        flash('Bruzz is not logged in')
        return redirect(url_for('auth.login'))

    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first() if user_id else None
    print(user)
    events = Event.query.all()

    return render_template('events/index.html', events=events, user=user)

@events_bp.route('/add_event', methods=['POST', 'GET'])
def add_event():
    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()
    if not user_id and user.role <= 2:
        flash('Bruzz is not logged in and/or isnt an admin')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        event_name = request.form.get('event_name')
        event_description = request.form.get('event_description')
        owner_first_name = request.form.get('owner_first_name')
        owner_last_name = request.form.get('owner_last_name')
        event_emoji = request.form.get('event_emoji')

        owner = User.query.filter_by(first_name = owner_first_name.lower(), last_name = owner_last_name.first())
        
    return render_template('events/add_event.html')
