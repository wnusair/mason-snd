from flask import Blueprint, render_template, request, redirect, url_for, flash, session, Response
import csv
import csv
from io import StringIO

from mason_snd.extensions import db
from mason_snd.models.events import Event, User_Event, Effort_Score
from mason_snd.models.auth import User
from mason_snd.models.metrics import MetricsSettings

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
    # Only consider events where the User_Event row is active
    active_event_relationships = User_Event.query.filter_by(user_id=user_id, active=True).all()
    for row in active_event_relationships:
        event = Event.query.filter_by(id=row.event_id).first()
        if event:
            user_events.append(event.event_name)
    print(user_events)

    return render_template('events/index.html', events=events, user=user, user_events=user_events)

@events_bp.route('/leave_event/<int:event_id>', methods=['POST'])
def leave_event(event_id):
    user_id = session.get('user_id')
    if not user_id:
        flash("You must be logged in to leave an event", "error")
        return redirect(url_for('auth.login'))
    
    existing_entry = User_Event.query.filter_by(user_id=user_id, event_id=event_id).first()
    if not existing_entry or not existing_entry.active:
        flash("You are not currently part of this event", "error")
        return redirect(url_for('events.index'))

    existing_entry.active = False
    db.session.commit()

    flash("You have successfully left the event", "success")
    return redirect(url_for('events.index'))
    
@events_bp.route('/edit_event/<int:event_id>', methods=['GET', 'POST'])
def edit_event(event_id):
    user_id = session.get('user_id')
    if not user_id:
        flash('You must be logged in to edit an event', 'error')
        return redirect(url_for('auth.login'))


    user = User.query.filter_by(id=user_id).first()

    # Fetch the event to edit
    event = Event.query.filter_by(id=event_id).first()
    if not event:
        flash('Event not found', 'error')
        return redirect(url_for('events.index'))

    # Ensure the logged-in user is either the owner of the event or an admin (role >= 2)
    if not (event.owner_id == user_id or (user and user.role >= 2)):
        flash('You are not authorized to edit this event', 'error')
        return redirect(url_for('events.index'))

    if request.method == 'POST':
        # Update event details
        event_name = request.form.get('event_name')
        event_description = request.form.get('event_description')
        event_type = request.form.get('event_type')
        event_emoji = request.form.get('event_emoji')
        is_partner_event = request.form.get('is_partner_event') == 'on'

        # Validate required fields
        if not event_name or not event_description or not event_type:
            flash("Please fill in all required fields", "error")
            return redirect(url_for("events.edit_event", event_id=event_id))

        # Validate event_type
        try:
            event_type_int = int(event_type)
            if event_type_int not in [0, 1, 2]:
                flash("Invalid event type selected", "error")
                return redirect(url_for("events.edit_event", event_id=event_id))
        except (ValueError, TypeError):
            flash("Invalid event type", "error")
            return redirect(url_for("events.edit_event", event_id=event_id))

        # Update event details
        event.event_name = event_name
        event.event_description = event_description
        event.event_type = event_type_int
        event.event_emoji = event_emoji
        event.is_partner_event = is_partner_event

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

    # Get the logged-in user
    user = User.query.filter_by(id=user_id).first()

    # Fetch the event
    event = Event.query.get(event_id)
    if not event:
        flash('Event not found.', 'error')
        return redirect(url_for('events.index'))

    # Ensure the logged-in user is either the owner of the event or an admin (role >= 2)
    if not (event.owner_id == user_id or (user and user.role >= 2)):
        flash('You are not authorized to manage this event.', 'error')
        return redirect(url_for('events.index'))

    # Get metrics settings for weighted points calculation
    settings = MetricsSettings.query.first()
    if not settings:
        tournament_weight, effort_weight = 0.7, 0.3
    else:
        tournament_weight, effort_weight = settings.tournament_weight, settings.effort_weight

    # Sorting logic
    sort = request.args.get('sort', 'name')
    direction = request.args.get('direction', 'asc')

    # Get all members of the event
    user_events = User_Event.query.filter_by(event_id=event_id).all()
    members = []
    for ue in user_events:
        user = User.query.get(ue.user_id)
        tournament_points = user.tournament_points or 0
        effort_points = user.effort_points or 0
        total_points = tournament_points + effort_points
        weighted_points = round(tournament_points * tournament_weight + effort_points * effort_weight, 2)
        members.append({
            "user": user,
            "effort_score": ue.effort_score,
            "tournament_points": tournament_points,
            "effort_points": effort_points,
            "total_points": total_points,
            "weighted_points": weighted_points,
        })

    # Sorting map
    sort_key_map = {
        'name': lambda m: (m['user'].last_name.lower(), m['user'].first_name.lower()),
        'effort_score': lambda m: m['effort_score'],
        'tournament_points': lambda m: m['tournament_points'],
        'effort_points': lambda m: m['effort_points'],
        'total_points': lambda m: m['total_points'],
        'weighted_points': lambda m: m['weighted_points'],
    }
    if sort in sort_key_map:
        reverse = direction == 'desc'
        members = sorted(members, key=sort_key_map[sort], reverse=reverse)

    if request.method == "POST":
        # Update effort scores for each member
        for ue in user_events:
            new_score = request.form.get(f"effort_score_{ue.user_id}")
            if new_score and new_score.isdigit():
                new_score = int(new_score)

                # Update the User_Event table
                ue.effort_score += new_score

                # Update the Effort_Score table
                effort_score_entry = Effort_Score(
                    score=new_score,
                    user_id=ue.user_id,
                    event_id=event_id,
                    given_by_id=user_id  # The logged-in user assigning the score
                )
                db.session.add(effort_score_entry)

                # Award points and handle bids
                user = User.query.get(ue.user_id)
                if user:
                    # Check if user has any previous bids in their tournament performance history
                    from mason_snd.models.tournaments import Tournament_Performance
                    previous_bids = Tournament_Performance.query.filter_by(user_id=user.id, bid=True).first()
                    
                    if previous_bids is None:
                        # User has never received a tournament bid before - award 15 points
                        user.points = (user.points or 0) + 15
                    else:
                        # User has received tournament bid(s) before - award 5 points
                        user.points = (user.points or 0) + 5

        db.session.commit()
        flash("Effort scores and points/bids updated successfully.", "success")
        return redirect(url_for("events.manage_members", event_id=event_id, sort=sort, direction=direction))

    def next_direction(column):
        if sort == column:
            if direction == 'asc':
                return 'desc'
            elif direction == 'desc':
                return 'asc'
            else:
                return 'asc'
        else:
            return 'asc'

    return render_template(
        'events/manage_members.html',
        members=members,
        event=event,
        sort=sort,
        direction=direction,
        next_direction=next_direction
    )

@events_bp.route('/join_event/<int:event_id>', methods=['POST'])
def join_event(event_id):
    user_id = session.get('user_id')
    if not user_id:
        flash('You must be logged in to join an event', 'error')
        return redirect(url_for('auth.login'))

    existing_entry = User_Event.query.filter_by(user_id=user_id, event_id=event_id).first()
    if existing_entry:
        if existing_entry.active:
            flash('You have already joined this event', 'info')
            return redirect(url_for('events.index'))
        else:
            existing_entry.active = True
            db.session.commit()
            flash('You have successfully re-joined the event', 'success')
            return redirect(url_for('events.index'))

    new_user_event = User_Event(
        user_id=user_id,
        event_id=event_id,
        active=True
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
        event_type = request.form.get('event_type')
        owner_first_name = request.form.get('owner_first_name')
        owner_last_name = request.form.get('owner_last_name')
        event_emoji = request.form.get('event_emoji')
        is_partner_event = request.form.get('is_partner_event') == 'on'

        # Validate required fields
        if not event_name or not event_description or not event_type or not owner_first_name or not owner_last_name:
            flash("Please fill in all required fields", "error")
            return redirect(url_for("events.add_event"))

        # Validate event_type
        try:
            event_type_int = int(event_type)
            if event_type_int not in [0, 1, 2]:
                flash("Invalid event type selected", "error")
                return redirect(url_for("events.add_event"))
        except (ValueError, TypeError):
            flash("Invalid event type", "error")
            return redirect(url_for("events.add_event"))

        owner = User.query.filter_by(first_name=owner_first_name.lower(), last_name=owner_last_name.lower()).first()
        
        if not owner:
            flash("This person does not exist", "error")
            return redirect(url_for("events.add_event"))

        new_event = Event(
            event_name=event_name,
            event_description=event_description,
            event_emoji=event_emoji,
            event_type=event_type_int,
            owner_id=owner.id,
            is_partner_event=is_partner_event
        )

        db.session.add(new_event)
        db.session.commit()
        return redirect(url_for('events.index'))

    return render_template('events/add_event.html')

@events_bp.route('/delete_event/<int:event_id>', methods=['POST'])
def delete_event(event_id):
    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()
    if not user_id:
        flash("You must be logged in to delete an event", "error")
        return redirect(url_for('auth.login'))
    
    if user.role < 2:
        flash("You do not have admin permissions to delete event.", "error")
        return redirect(url_for('auth.login'))
    
    event = Event.query.filter_by(id=event_id).first()

    db.session.delete(event)
    db.session.commit()

    flash("You have successfully deleted the event", "success")
    return redirect(url_for('events.index'))

@events_bp.route('/download_event_members/<int:event_id>')
def download_event_members(event_id):
    """Download CSV of event members with their points breakdown"""
    event = Event.query.get_or_404(event_id)
    
    # Get metrics settings for weighted points calculation
    settings = MetricsSettings.query.first()
    if not settings:
        tournament_weight, effort_weight = 0.7, 0.3
    else:
        tournament_weight, effort_weight = settings.tournament_weight, settings.effort_weight
    
    # Get all members of the event
    user_events = User_Event.query.filter_by(event_id=event_id).all()
    
    # Prepare CSV
    si = StringIO()
    writer = csv.writer(si)
    # Write header row
    writer.writerow([
        'Name', 'Bids', 'Tournament Points', 'Effort Points', 'Total Points', 'Weighted Points', 'Event Effort Score'
    ])
    
    for ue in user_events:
        user = ue.user
        tournament_points = user.tournament_points or 0
        effort_points = user.effort_points or 0
        total_points = tournament_points + effort_points
        weighted_points = round(tournament_points * tournament_weight + effort_points * effort_weight, 2)
        
        writer.writerow([
            f"{user.first_name} {user.last_name}",
            user.bids or 0,
            tournament_points,
            effort_points,
            total_points,
            weighted_points,
            ue.effort_score or 0
        ])
    
    output = si.getvalue()
    si.close()
    return Response(
        output,
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=event_{event.event_name}_members.csv'
        }
    )
@events_bp.route('/download_all_events_stats')
def download_all_events_stats():
    """Download CSV of all user-event stats, sorted by event name and user name"""
    settings = MetricsSettings.query.first()
    if not settings:
        tournament_weight, effort_weight = 0.7, 0.3
    else:
        tournament_weight, effort_weight = settings.tournament_weight, settings.effort_weight

    all_events = Event.query.order_by(Event.event_name.asc()).all()
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow([
        'Name', 'Event', 'Total Points', 'Weighted Points', 'Effort Points', 'Tournament Points', 'Bids'
    ])
    for event in all_events:
        user_events = User_Event.query.filter_by(event_id=event.id).all()
        # Sort users by last, first name for each event
        users = [User.query.get(ue.user_id) for ue in user_events]
        user_event_pairs = sorted(zip(users, user_events), key=lambda pair: (pair[0].last_name.lower(), pair[0].first_name.lower()) if pair[0] else ('', ''))
        for user, ue in user_event_pairs:
            if not user:
                continue
            tournament_points = user.tournament_points or 0
            effort_points = user.effort_points or 0
            total_points = tournament_points + effort_points
            weighted_points = round(tournament_points * tournament_weight + effort_points * effort_weight, 2)
            writer.writerow([
                f"{user.first_name} {user.last_name}",
                event.event_name,
                total_points,
                weighted_points,
                effort_points,
                tournament_points,
                user.bids or 0
            ])
    output = si.getvalue()
    si.close()
    return Response(
        output,
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename=all_events_stats.csv'
        }
    )
