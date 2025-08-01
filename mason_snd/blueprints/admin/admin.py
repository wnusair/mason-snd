from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from difflib import get_close_matches

from mason_snd.extensions import db
from mason_snd.models.auth import User
from mason_snd.models.admin import User_Requirements, Requirements
from mason_snd.models.events import User_Event, Event
from mason_snd.models.tournaments import Tournament_Performance
from mason_snd.models.metrics import MetricsSettings
from mason_snd.models.admin import User_Requirements

from werkzeug.security import generate_password_hash, check_password_hash

admin_bp = Blueprint('admin', __name__, template_folder='templates')

@admin_bp.route('/')
def index():
    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()
    print(user)

    if user.role <= 1:
        flash('Restricted Access!!!!!')
        return redirect(url_for('profile.index'))
    return render_template('admin/index.html')

@admin_bp.route('/add_popup', methods=['POST', 'GET'])
def add_popup():
    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()
    print(user)

    if user.role <= 1:
        flash('Restricted Access!!!!!')
        return redirect(url_for('profile.index'))

    if request.method == 'POST':
        recipient_first_name = request.form.get('recipient_first_name')
        recipient_last_name = request.form.get('recipient_last_name')
        message = request.form.get('message')

        recipient = User.query.filter_by(first_name=recipient_first_name, last_name=recipient_last_name).first()

        if not recipient:
            flash("Recipient Does Not Exist, Please retype name")
            return redirect(url_for('admin.add_popup'))
        
        #yu need to make popups with experation dates and checking if done

    
    return render_template('admin/add_popup.html')


# Admin view of user details
@admin_bp.route('/user/<int:user_id>')
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    # Events
    user_events = User_Event.query.filter_by(user_id=user_id).all()
    events = [Event.query.get(ue.event_id) for ue in user_events]

    # Tournament points, effort points, total, weighted
    tournament_points = user.tournament_points or 0
    effort_points = user.effort_points or 0
    total_points = tournament_points + effort_points
    settings = MetricsSettings.query.first()
    if not settings:
        tournament_weight, effort_weight = 0.7, 0.3
    else:
        tournament_weight, effort_weight = settings.tournament_weight, settings.effort_weight
    weighted_points = round(tournament_points * tournament_weight + effort_points * effort_weight, 2)

    # Emergency/child info
    if user.is_parent:
        child_info = {
            'first_name': user.child_first_name,
            'last_name': user.child_last_name
        }
    else:
        child_info = None
    emergency_contact = {
        'first_name': user.emergency_contact_first_name,
        'last_name': user.emergency_contact_last_name,
        'number': user.emergency_contact_number,
        'relationship': user.emergency_contact_relationship,
        'email': user.emergency_contact_email
    }

    # Requirements
    requirements = User_Requirements.query.filter_by(user_id=user_id).all()

    return render_template(
        'admin/user_detail.html',
        user=user,
        events=events,
        tournament_points=tournament_points,
        effort_points=effort_points,
        total_points=total_points,
        weighted_points=weighted_points,
        emergency_contact=emergency_contact,
        child_info=child_info,
        requirements=requirements
    )

# Fuzzy search for users by name
@admin_bp.route('/search', methods=['GET', 'POST'])
def search():
    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()
    print(user)

    results = []
    query = ''
    if request.method == 'POST':
        query = request.form.get('name', '').strip().lower()
        if query:
            # Get all users and their full names
            users = User.query.all()
            user_map = {f"{u.first_name.lower()} {u.last_name.lower()}": u for u in users}
            names = list(user_map.keys())
            # Use difflib to get close matches
            close = get_close_matches(query, names, n=10, cutoff=0.0)  # cutoff=0.0 for all, sorted by similarity
            # If no close matches, show all users
            if not close:
                close = names
            results = [(user_map[name], name) for name in close]
    return render_template('admin/search.html', results=results, query=query)

