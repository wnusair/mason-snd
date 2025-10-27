"""
Events Blueprint

This module manages speech and debate events, including event creation,
member management, effort scoring, and event statistics.

Key Features:
    - Event Creation: Admins create speech and debate events
    - Event Membership: Students join and leave events
    - Event Types: Speech (0), Lincoln-Douglas (1), Public Forum (2)
    - Partner Events: Support for team-based events
    - Effort Scoring: Event leaders award effort points to members
    - Member Management: View and sort members with point breakdowns
    - CSV Export: Download event rosters and statistics

Event Types:
    0 = Speech Events (Individual Speeches, Oral Interpretation)
    1 = Lincoln-Douglas Debate (LD)
    2 = Public Forum Debate (PF)

Workflow:
    1. Admin creates event with name, description, type, owner
    2. Students join events they want to participate in
    3. Event owners/leaders manage members and award effort scores
    4. Points are automatically calculated and tracked
    5. Statistics can be exported for analysis
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, Response
import csv
import csv
from io import StringIO

from mason_snd.extensions import db
from mason_snd.models.events import Event, User_Event, Effort_Score, Event_Leader
from mason_snd.models.auth import User
from mason_snd.models.metrics import MetricsSettings
from mason_snd.utils.race_protection import prevent_race_condition

from werkzeug.security import generate_password_hash, check_password_hash

events_bp = Blueprint('events', __name__, template_folder='templates')

def is_event_leader(user_id, event_id):
    """
    Check if a user is an event leader for a specific event.
    
    Args:
        user_id (int): The user ID to check
        event_id (int): The event ID to check
    
    Returns:
        bool: True if user is an event leader for this event, False otherwise
    """
    return Event_Leader.query.filter_by(
        event_id=event_id,
        user_id=user_id
    ).first() is not None

def can_manage_event(user_id, event_id):
    """
    Check if a user can manage an event (is event leader or admin).
    
    Args:
        user_id (int): The user ID to check
        event_id (int): The event ID to check
    
    Returns:
        bool: True if user can manage the event, False otherwise
    """
    user = User.query.get(user_id)
    if not user:
        return False
    
    # Admins can manage all events
    if user.role >= 2:
        return True
    
    # Check if user is an event leader for this event
    return is_event_leader(user_id, event_id)

@events_bp.route('/')
def index():
    """
    Display all events with user's membership status.
    
    Shows complete list of events in the system, highlighting which events
    the current user is actively enrolled in. Only displays active memberships
    (User_Event.active=True).
    
    Displayed Information:
        - Event name, description, emoji
        - Event type (Speech, LD, PF)
        - Event owner information
        - User's active membership status
    
    Features:
        - Join/leave event buttons
        - Visual indicators for user's events
        - Link to event details and management
    
    Access: Requires login
    
    Returns:
        Rendered events index page with event list and membership status
    """
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

    # Get events where user is a leader
    user_led_events = []
    if user_id:
        event_leader_relationships = Event_Leader.query.filter_by(user_id=user_id).all()
        for el in event_leader_relationships:
            user_led_events.append(el.event_id)

    return render_template('events/index.html', events=events, user=user, user_events=user_events, user_led_events=user_led_events)

@events_bp.route('/leave_event/<int:event_id>', methods=['POST'])
@prevent_race_condition('leave_event', min_interval=0.5, redirect_on_duplicate=lambda uid, form: redirect(url_for('events.index')))
def leave_event(event_id):
    """
    Leave an event by setting membership to inactive.
    
    Sets User_Event.active=False rather than deleting the record, preserving
    historical membership and effort scores while removing user from active roster.
    
    Args:
        event_id (int): The event to leave
    
    Validation:
        - User must be logged in
        - User must have active membership in the event
    
    Database Updates:
        - Sets User_Event.active = False
        - Preserves historical data (effort_score, etc.)
    
    Returns:
        Redirect to events index with success message
    """
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
@prevent_race_condition('edit_event', min_interval=1.0, redirect_on_duplicate=lambda uid, form: redirect(url_for('events.index')))
def edit_event(event_id):
    """
    Edit event details (owner or admin only).
    
    Allows event owners and admins to modify event information including
    name, description, type, emoji, and partner event status.
    
    Args:
        event_id (int): The event to edit
    
    GET: Display edit form pre-filled with current event data
    POST: Update event with new information
    
    Form Fields:
        - event_name: Event display name
        - event_description: Detailed event description
        - event_type: 0 (Speech), 1 (LD), 2 (PF)
        - event_emoji: Unicode emoji for visual identification
        - is_partner_event: Boolean checkbox (team event or individual)
    
    Validation:
        - All fields except emoji are required
        - event_type must be 0, 1, or 2
        - User must be event owner or admin (role >= 2)
    
    Access Control:
        - Event owner can edit their event
        - Admins (role >= 2) can edit any event
    
    Returns:
        GET: Rendered edit form with current event data
        POST: Redirect to events index with success message
    """
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

    # Ensure the logged-in user is either an event leader or an admin (role >= 2)
    if not can_manage_event(user_id, event_id):
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
        from mason_snd.models.event_types import Event_Type
        try:
            event_type_int = int(event_type)
            event_type_obj = Event_Type.query.get(event_type_int)
            if not event_type_obj:
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

    from mason_snd.models.event_types import Event_Type
    event_types = Event_Type.query.order_by(Event_Type.name).all()
    return render_template('events/edit_event.html', event=event, event_types=event_types)


@events_bp.route('/manage_members/<int:event_id>', methods=['POST', 'GET'])
@prevent_race_condition('manage_members', min_interval=1.0, redirect_on_duplicate=lambda uid, form: redirect(url_for('events.index')))
def manage_members(event_id):
    """
    Manage event members and award effort scores (owner/admin only).
    
    Comprehensive member management interface allowing event leaders to view
    all members with detailed point breakdowns and award effort scores for
    participation, leadership, and other contributions.
    
    Args:
        event_id (int): The event to manage
    
    GET: Display sortable member list with point breakdowns
    POST: Award effort scores to selected members
    
    Query Parameters:
        - sort: Sort column ('name', 'effort_score', 'tournament_points', 
                'effort_points', 'total_points', 'weighted_points')
        - direction: Sort direction ('asc' or 'desc')
    
    Member Information Displayed:
        - Name (sortable by last name, first name)
        - Current effort score for this event
        - Tournament points (from tournament results)
        - Effort points (from all events)
        - Total points (tournament + effort)
        - Weighted points (using metrics settings)
    
    Effort Score Assignment:
        - Form field: effort_score_{user_id}
        - Adds to cumulative User_Event.effort_score
        - Creates Effort_Score record for history
        - Awards bid-equivalent points:
            * First-ever bid: +15 points
            * Subsequent bids: +5 points
    
    Sorting Features:
        - Multiple column sorting
        - Ascending/descending toggle
        - Persistent sort across page refreshes
    
    Points Calculation:
        - Weighted points use MetricsSettings weights
        - Default: 70% tournament, 30% effort
        - Displayed alongside raw points
    
    Access Control:
        - Event owner can manage their event
        - Admins (role >= 2) can manage any event
    
    Returns:
        GET: Rendered member management page with sortable member list
        POST: Redirect to manage_members with updated sort parameters
    """
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

    # Ensure the logged-in user is either an event leader or an admin (role >= 2)
    if not can_manage_event(user_id, event_id):
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
@prevent_race_condition('join_event', min_interval=0.5, redirect_on_duplicate=lambda uid, form: redirect(url_for('events.index')))
def join_event(event_id):
    """
    Join an event or re-activate previous membership.
    
    Creates new User_Event membership or reactivates existing inactive membership.
    Handles both new enrollments and returning to previously-left events.
    
    Args:
        event_id (int): The event to join
    
    Scenarios:
        1. New Member: Creates User_Event with active=True
        2. Already Active: Flash info message, no changes
        3. Previously Left: Sets existing User_Event.active=True
    
    Database Operations:
        - New: Creates User_Event record with active=True
        - Rejoin: Updates existing User_Event.active to True
        - Preserves historical effort_score when rejoining
    
    Access: Requires login
    
    Returns:
        Redirect to events index with appropriate success/info message
    """
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
@prevent_race_condition('add_event', min_interval=1.5, redirect_on_duplicate=lambda uid, form: redirect(url_for('events.index')))
def add_event():
    """
    Create a new event (admin only).
    
    Admins can create new speech and debate events by specifying event details
    and assigning an owner who will manage the event.
    
    GET: Display event creation form
    POST: Create new event with specified details
    
    Form Fields:
        - event_name: Display name for the event
        - event_description: Detailed description of event
        - event_type: Integer (0=Speech, 1=LD, 2=PF)
        - owner_first_name: First name of event owner/leader
        - owner_last_name: Last name of event owner/leader
        - event_emoji: Unicode emoji for visual identification (optional)
        - is_partner_event: Checkbox (team event or individual)
    
    Event Types:
        - 0: Speech (IE, OI, etc.)
        - 1: Lincoln-Douglas Debate
        - 2: Public Forum Debate
    
    Owner Assignment:
        - Searches for user by exact first + last name (case-insensitive)
        - Owner must be existing user in system
        - Owner gains management permissions for this event
    
    Validation:
        - All fields required except emoji
        - event_type must be 0, 1, or 2
        - Owner must exist in database
    
    Access: Requires role >= 2 (Admin)
    
    Returns:
        GET: Rendered event creation form
        POST: Redirect to events index with new event visible
    """
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
        from mason_snd.models.event_types import Event_Type
        try:
            event_type_int = int(event_type)
            event_type_obj = Event_Type.query.get(event_type_int)
            if not event_type_obj:
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

    from mason_snd.models.event_types import Event_Type
    event_types = Event_Type.query.order_by(Event_Type.name).all()
    return render_template('events/add_event.html', event_types=event_types)

@events_bp.route('/delete_event/<int:event_id>', methods=['POST'])
@prevent_race_condition('delete_event', min_interval=1.0, redirect_on_duplicate=lambda uid, form: redirect(url_for('events.index')))
def delete_event(event_id):
    """
    Permanently delete an event (admin only).
    
    Removes event from system. Related data is cascade-deleted through
    database relationships.
    
    Args:
        event_id (int): The event to delete
    
    Cascade Deletions:
        - User_Event memberships (all enrollments)
        - Effort_Score records (effort score history)
        - Tournament_Signups (tournament event signups)
    
    Access: Requires role >= 2 (Admin)
    
    Warning:
        This is a destructive operation with no confirmation dialog.
        All event data and member history is permanently lost.
    
    Returns:
        Redirect to events index
    """
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
    """
    Download CSV of event members with detailed point breakdowns.
    
    Exports comprehensive roster of all event members (active and inactive)
    with their complete point statistics.
    
    Args:
        event_id (int): The event to export members for
    
    CSV Columns:
        - Name: Full name (First Last)
        - Bids: Total tournament bids received
        - Tournament Points: Points from tournament results
        - Effort Points: Points from effort scores across all events
        - Total Points: Sum of tournament + effort points
        - Weighted Points: Calculated using MetricsSettings weights
        - Event Effort Score: Cumulative effort score for this specific event
    
    Weighted Points Calculation:
        - Uses MetricsSettings.tournament_weight and effort_weight
        - Default: 70% tournament, 30% effort
        - Formula: (tournament_points × t_weight) + (effort_points × e_weight)
    
    File Format:
        - CSV with headers
        - Filename: event_{event_name}_members.csv
        - Content-Type: text/csv
        - Includes all members regardless of active status
    
    Use Cases:
        - Exporting event rosters for coaches
        - Analyzing member performance
        - Record keeping and reporting
        - Importing into spreadsheet applications
    
    Returns:
        CSV file download with member statistics
    """
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
    """
    Download CSV of all user-event statistics across entire system.
    
    Exports comprehensive dataset showing every user's membership and performance
    in every event they've joined. Useful for team-wide analysis and reporting.
    
    CSV Structure:
        - Sorted by: Event name (ascending), then User name (last, first)
        - One row per user-event combination
        - All events included, all members included
    
    CSV Columns:
        - Name: Full name (First Last)
        - Event: Event name
        - Total Points: Tournament + Effort points
        - Weighted Points: Calculated using MetricsSettings
        - Effort Points: All effort points from all events
        - Tournament Points: All tournament points
        - Bids: Total tournament bids received
    
    Weighted Points:
        - Uses MetricsSettings.tournament_weight and effort_weight
        - Default: 70% tournament, 30% effort
        - Consistent across all events
    
    Sorting:
        - Primary: Event name (alphabetical)
        - Secondary: User last name (alphabetical)
        - Tertiary: User first name (alphabetical)
    
    File Format:
        - CSV with headers
        - Filename: all_events_stats.csv
        - Content-Type: text/csv
    
    Use Cases:
        - Team-wide performance analysis
        - Comparing performance across events
        - Identifying top performers per event
        - Season-end reporting
        - Exporting to Excel for pivot tables
    
    Performance Notes:
        - Queries all events and all memberships
        - May be large file for teams with many events/members
        - Sorted in Python for consistency
    
    Returns:
        CSV file download with all user-event statistics
    """
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
