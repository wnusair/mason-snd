from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from mason_snd.extensions import db
from mason_snd.models.events import Event, User_Event
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

    user_events = []
    event_relationships = User_Event.query.all()

    for row in event_relationships:
        if row.user_id == user_id:
            event_id = row.event_id
            user_event = Event.query.filter_by(id=event_id).first()
            if user_event:
                user_events.append(user_event.event_name)
    
    print(user_events)

    return render_template('events/index.html', events=events, user=user, user_events=user_events)

@events_bp.route('/leave_event/<int:event_id>', methods=['POST'])
def leave_event(event_id):
    user_id = session.get('user_id')
    if not user_id:
        flash("You must be logged in to leave an event", "error")
        return redirect(url_for('auth.login'))
    
    existing_entry = User_Event.query.filter_by(user_id=user_id, event_id=event_id).first()
    if not existing_entry:
        flash("You have not joined this event to leave it", "error")
        return redirect(url_for('events.index'))

    db.session.delete(existing_entry)
    db.session.commit()

    flash("You have successfully left the event", "success")
    return redirect(url_for('events.index'))
    
@events_bp.route('/edit_event/<int:event_id>', methods=['GET', 'POST'])
def edit_event(event_id):
    user_id = session.get('user_id')
    if not user_id:
        flash('You must be logged in to edit an event', 'error')
        return redirect(url_for('auth.login'))

    # Fetch the event to edit
    event = Event.query.filter_by(id=event_id).first()
    if not event:
        flash('Event not found', 'error')
        return redirect(url_for('events.index'))

    # Ensure the logged-in user is the owner of the event
    if event.owner_id != user_id:
        flash('You are not authorized to edit this event', 'error')
        return redirect(url_for('events.index'))

    if request.method == 'POST':
        # Update event details
        event.event_name = request.form.get('event_name')
        event.event_description = request.form.get('event_description')
        event.event_emoji = request.form.get('event_emoji')

        db.session.commit()
        flash('Event updated successfully', 'success')
        return redirect(url_for('events.index'))

    return render_template('events/edit_event.html', event=event)

@events_bp.route('/manage_members/<int:event_id>', methods=['POST', 'GET'])
def manage_members(event_id):
    # Check if the user is logged in
    user_id = session.get('user_id')
    if not user_id:
        flash('You must be logged in to manage members.', 'error')
        return redirect(url_for('auth.login'))

    # Fetch the event
    event = Event.query.get(event_id)
    if not event:
        flash('Event not found.', 'error')
        return redirect(url_for('events.index'))

    # Ensure the logged-in user is the owner of the event
    if event.owner_id != user_id:
        flash('You are not authorized to manage this event.', 'error')
        return redirect(url_for('events.index'))

    # Get all members of the event
    user_events = User_Event.query.filter_by(event_id=event_id).all()
    members = [
        {
            "user": User.query.get(ue.user_id),
            "effort_score": ue.effort_score,
        }
        for ue in user_events
    ]

    if request.method == "POST":
        # Update effort scores for each member
        for ue in user_events:
            new_score = request.form.get(f"effort_score_{ue.user_id}")
            if new_score and new_score.isdigit():
                new_score = int(new_score)
                ue.effort_score += new_score

                # Update the user's total score
                user = User.query.get(ue.user_id)
                if user:
                    user.total_score = (user.total_score or 0) + new_score

        db.session.commit()
        flash("Effort scores updated successfully.", "success")
        return redirect(url_for("events.manage_members", event_id=event_id))

    return render_template('events/manage_members.html', members=members, event=event)

@events_bp.route('/join_event/<int:event_id>', methods=['POST'])
def join_event(event_id):
    user_id = session.get('user_id')
    if not user_id:
        flash('You must be logged in to join an event', 'error')
        return redirect(url_for('auth.login'))

    # Check if the user has already joined the event
    existing_entry = User_Event.query.filter_by(user_id=user_id, event_id=event_id).first()
    if existing_entry:
        flash('You have already joined this event', 'info')
        return redirect(url_for('events.index'))

    # Add the user to the event with a default effort_score of 0
    new_user_event = User_Event(
        user_id=user_id,
        event_id=event_id
    )
    db.session.add(new_user_event)
    db.session.commit()

    flash('You have successfully joined the event', 'success')
    return redirect(url_for('events.index'))
    

@events_bp.route('/add_event', methods=['POST', 'GET'])
def add_event():
    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()

    if not user_id or user is None or user.role < 2:
        flash('Bruzz is not logged in and/or isn\'t an admin')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        event_name = request.form.get('event_name')
        event_description = request.form.get('event_description')
        owner_first_name = request.form.get('owner_first_name')
        owner_last_name = request.form.get('owner_last_name')
        event_emoji = request.form.get('event_emoji')

        owner = User.query.filter_by(first_name=owner_first_name.lower(), last_name=owner_last_name.lower()).first()
        
        if not owner:
            flash("This person does not exist", "error")
            return redirect(url_for("events.add_event"))

        new_event = Event(
            event_name=event_name,
            event_description=event_description,
            event_emoji=event_emoji,
            owner_id=owner.id
        )

        db.session.add(new_event)
        db.session.commit()
        return redirect(url_for('events.index'))

    return render_template('events/add_event.html')