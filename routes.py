from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, current_user
from models import User, Event, Tournament, Statistics
from app import db
from utils import allowed_file, parse_csv, generate_sample_csv
from sqlalchemy import func
from datetime import datetime, timedelta
from collections import defaultdict
import os
import math
from analytics import (
    get_user_performance_trend,
    get_team_improvement_rate,
    get_team_next_predicted_score,
    calculate_weighted_score,
    get_user_next_predicted_score,
    projected_movements
)

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if current_user.role in ['Head of Metrics', 'Chair', 'Chairman', 'Data Chairman', 'Event Leader']:
        team_stats = get_team_stats()
        top_performers = get_top_performers()
        team_improvement_rate = get_team_improvement_rate()
        team_next_predicted_score = get_team_next_predicted_score()

        # personal stats
        user_stats = get_user_stats(current_user.id)
        user_trend_tuple = get_user_performance_trend(current_user.id)  # Adjusted this line
        user_trend = user_trend_tuple[0]  # Extracting the trend
        next_predicted_score = get_user_next_predicted_score(current_user.id) # Assuming you have this function

        member_stats = Statistics.query.filter_by(user_id=current_user.id).all()
        total_points_user = sum(stat.score for stat in member_stats)

        # Calculate the total points for all users
        total_points_team = db.session.query(func.sum(Statistics.score)).scalar() or 0

        return render_template(
            'dashboard.html',
            team_stats=team_stats,
            top_performers=top_performers,
            team_improvement_rate=team_improvement_rate,
            team_next_predicted_score=team_next_predicted_score,
            total_points_user=total_points_user,
            total_points_team=total_points_team,
            user_stats=user_stats,
            user_trend=user_trend,
            next_predicted_score=next_predicted_score
        )

    elif current_user.role == 'Member':
        user_stats = get_user_stats(current_user.id)
        user_trend = get_user_performance_trend(current_user.id)  # Adjusted this line
        next_predicted_score = get_user_next_predicted_score(current_user.id)  # Assuming you have this function
        member_stats = Statistics.query.filter_by(user_id=current_user.id).all()
        total_points = sum(stat.score for stat in member_stats)

        return render_template(
            'dashboard.html',
            user_stats=user_stats,
            user_trend=user_trend,
            next_predicted_score=next_predicted_score,
            total_points=total_points
        )
    else:
        return render_template('dashboard.html')




@main.route('/analytics')
@login_required
def analytics():
    flash('The analytics have been moved to the dashboard.')
    return redirect(url_for('main.dashboard'))

def get_team_stats():
    total_events = Event.query.count()
    total_tournaments = Tournament.query.count()
    average_score = db.session.query(func.avg(Statistics.score)).scalar() or 0
    total_members = User.query.filter(User.role != 'Head of Metrics').count()

    return {
        'total_events': total_events,
        'total_tournaments': total_tournaments,
        'average_score': average_score,
        'total_members': total_members
    }

def get_user_stats(user_id):
    user_stats = Statistics.query.filter_by(user_id=user_id).order_by(Statistics.date.desc()).limit(5).all()
    return user_stats

def get_top_performers():
    return Statistics.query.order_by(Statistics.score.desc()).limit(5).all()

def get_upcoming_tournaments():
    today = datetime.now().date()
    return Tournament.query.filter(Tournament.date >= today).order_by(Tournament.date).limit(5).all()

def get_team_performance():
    stats = Statistics.query.join(Tournament).order_by(Tournament.date).all()
    labels = [stat.tournament.name for stat in stats]
    data = [stat.score for stat in stats]
    return {'labels': labels, 'data': data}

def get_event_distribution():
    events = Event.query.all()
    labels = [event.name for event in events]
    data = [len(event.statistics) for event in events]
    return {'labels': labels, 'data': data}

def get_tournament_performance():
    tournaments = Tournament.query.order_by(Tournament.date).all()
    labels = [tournament.name for tournament in tournaments]
    data = [sum(stat.score for stat in tournament.statistics) / len(tournament.statistics) if tournament.statistics else 0 for tournament in tournaments]
    return {'labels': labels, 'data': data}

def get_team_progress():
    stats = Statistics.query.join(Tournament).order_by(Tournament.date).all()
    labels = [stat.tournament.name for stat in stats]
    data = [sum(s.score for s in stats[:i+1]) / (i+1) for i in range(len(stats))]
    return {'labels': labels, 'data': data}

def update_ranks_and_groups(event_id):
    stats = Statistics.query.filter_by(event_id=event_id).order_by(Statistics.score.desc()).all()
    total_participants = len(stats)
    
    for index, stat in enumerate(stats, start=1):
        stat.rank = index
        
        if index <= 4:
            stat.group = "Ultra Competitive"
        elif index <= math.ceil(total_participants * 0.3) + 4:
            stat.group = "Competitive"
        else:
            stat.group = "Moderate"
    
    db.session.commit()

@main.route('/events')
@login_required
def events():
    events = Event.query.all()
    return render_template('events.html', events=events)

@main.route('/event/<int:event_id>', methods=['GET'])
@login_required
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)

    if current_user.role not in ['Event Leader', 'Head of Metrics', 'Chair', 'Chairman', 'Data Chairman']:
        flash('You do not have permission to view this page.')
        return redirect(url_for('main.events'))

    participant_points = {}
    weighted_scores = {}
    participant_trends = {}
    participant_predictions = {}

    for participant in event.participants:
        stats = Statistics.query.filter_by(user_id=participant.id).all()
        total_points = sum(stat.score for stat in stats)

        # Calculate weighted scores
        weighted_scores[participant.id] = calculate_weighted_score(total_points, participant.id)
        participant_points[participant.id] = total_points

        # Calculate the trend for each participant
        trend, prediction = get_user_performance_trend(participant.id)
        participant_trends[participant.id] = trend
        participant_predictions[participant.id] = prediction

    sorted_participants = sorted(
        event.participants,
        key=lambda participant: weighted_scores[participant.id],
        reverse=True
    )

    # Calculate projected movements using weighted scores
    projected_changes = projected_movements(event.participants, participant_predictions, weighted_scores)

    return render_template(
        'event_detail.html',
        event=event,
        users=User.query.all(),
        participant_points=participant_points,
        weighted_scores=weighted_scores,
        sorted_participants=sorted_participants,
        participant_trends=participant_trends,
        projected_changes=projected_changes,  # Pass projected changes
        enumerate=enumerate
    )

@main.route('/leave_event/<int:event_id>', methods=['POST'])
@login_required
def leave_event(event_id):
    event = Event.query.get_or_404(event_id)

    # Check if the user is a participant
    if current_user not in event.participants:
        flash('You are not a participant of this event.')
        return redirect(url_for('main.events'))

    # Remove the current user from the participants of the event
    event.participants.remove(current_user)
    db.session.commit()
    flash('You have successfully left the event.')
    return redirect(url_for('main.events'))

@main.route('/join_event/<int:event_id>', methods=['POST'])
@login_required
def join_event(event_id):
    event = Event.query.get_or_404(event_id)

    # Check if the user is already a participant
    if current_user in event.participants:
        flash('You are already a participant of this event.')
        return redirect(url_for('main.events'))

    # Add the current user as a participant of the event
    event.participants.append(current_user)
    db.session.commit()
    flash('You have successfully joined the event.')
    return redirect(url_for('main.events'))

@main.route('/add_event', methods=['GET', 'POST'])
@login_required
def add_event():
    if current_user.role not in ['Head of Metrics', 'Chair', 'Chairman', 'Data Chairman', 'Event Leader']:
        flash('You do not have permission to add events.')
        return redirect(url_for('main.events'))

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        new_event = Event(name=name, description=description)
        db.session.add(new_event)
        
        participants = request.form.getlist('participants')
        for participant_id in participants:
            participant = User.query.get(participant_id)
            if participant:
                new_event.participants.append(participant)
        
        db.session.commit()
        flash('Event added successfully.')
        return redirect(url_for('main.events'))

    users = User.query.filter_by(role='Member').all()
    return render_template('add_event.html', users=users)

@main.route('/edit_event/<int:event_id>', methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    if current_user.role not in ['Head of Metrics', 'Chair', 'Chairman', 'Data Chairman', 'Event Leader']:
        flash('You do not have permission to edit events.')
        return redirect(url_for('main.events'))

    event = Event.query.get_or_404(event_id)
    if request.method == 'POST':
        event.name = request.form.get('name')
        event.description = request.form.get('description')
        
        event.participants.clear()
        participants = request.form.getlist('participants')
        for participant_id in participants:
            participant = User.query.get(participant_id)
            if participant:
                event.participants.append(participant)
        
        db.session.commit()
        flash('Event updated successfully.')
        return redirect(url_for('main.events'))

    users = User.query.all()
    return render_template('edit_event.html', event=event, users=users)

@main.route('/delete_event/<int:event_id>')
@login_required
def delete_event(event_id):
    if current_user.role not in ['Head of Metrics', 'Chair', 'Chairman', 'Data Chairman']:
        flash('You do not have permission to delete events.')
        return redirect(url_for('main.events'))

    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    flash('Event deleted successfully.')
    return redirect(url_for('main.events'))

@main.route('/tournaments')
@login_required
def tournaments():
    if current_user.role == 'Member':
        tournaments = Tournament.query.join(Statistics).filter(Statistics.user_id == current_user.id).distinct().all()
    else:
        tournaments = Tournament.query.all()
    return render_template('tournaments.html', tournaments=tournaments)

@main.route('/add_tournament', methods=['GET', 'POST'])
@login_required
def add_tournament():
    if current_user.role not in ['Head of Metrics', 'Chair', 'Chairman', 'Data Chairman']:
        flash('You do not have permission to add tournaments.')
        return redirect(url_for('main.tournaments'))

    if request.method == 'POST':
        name = request.form.get('name')
        date = request.form.get('date')
        location = request.form.get('location')
        new_tournament = Tournament(name=name, date=date, location=location)
        db.session.add(new_tournament)
        
        participants = request.form.getlist('participants')
        for participant_id in participants:
            participant = User.query.get(participant_id)
            if participant:
                new_tournament.participants.append(participant)
        
        db.session.commit()
        flash('Tournament added successfully.')
        return redirect(url_for('main.tournaments'))

    users = User.query.filter_by(role='Member').all()
    return render_template('add_tournament.html', users=users)

@main.route('/edit_tournament/<int:tournament_id>', methods=['GET', 'POST'])
@login_required
def edit_tournament(tournament_id):
    if current_user.role not in ['Head of Metrics', 'Chair', 'Chairman', 'Data Chairman']:
        flash('You do not have permission to edit tournaments.')
        return redirect(url_for('main.tournaments'))

    tournament = Tournament.query.get_or_404(tournament_id)
    if request.method == 'POST':
        tournament.name = request.form.get('name')
        tournament.date = request.form.get('date')
        tournament.location = request.form.get('location')
        db.session.commit()
        flash('Tournament updated successfully.')
        return redirect(url_for('main.tournaments'))

    return render_template('edit_tournament.html', tournament=tournament)

@main.route('/delete_tournament/<int:tournament_id>')
@login_required
def delete_tournament(tournament_id):
    if current_user.role not in ['Head of Metrics', 'Chair', 'Chairman', 'Data Chairman']:
        flash('You do not have permission to delete tournaments.')
        return redirect(url_for('main.tournaments'))

    tournament = Tournament.query.get_or_404(tournament_id)
    db.session.delete(tournament)
    db.session.commit()
    flash('Tournament deleted successfully.')
    return redirect(url_for('main.tournaments'))

@main.route('/team_members', methods=['GET', 'POST'])
@login_required
def team_members():
    if current_user.role == 'Member':
        members = [current_user]
    else:
        members = User.query.filter(User.role != 'Head of Metrics').all()

    events = Event.query.all()

    if request.method == 'POST' and current_user.role in ['Head of Metrics', 'Chair', 'Chairman', 'Data Chairman', 'Event Leader']:
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        event_id = request.form.get('event')

        if username and email and password and role:
            existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
            if existing_user:
                flash('Username or email already exists.', 'error')
            else:
                new_user = User(username=username, email=email, role=role)
                new_user.set_password(password)
                db.session.add(new_user)

                if event_id and (role == 'Member' or role == 'Event Leader' or role == 'Chairman'):
                    event = Event.query.get(event_id)
                    if event:
                        new_user.events.append(event)

                db.session.commit()
                flash('New team member added successfully.', 'success')
                return redirect(url_for('main.team_members'))
        else:
            flash('Please fill in all fields.', 'error')

    return render_template('team_members.html', members=members, events=events)

@main.route('/edit_member/<int:member_id>', methods=['GET', 'POST'])
@login_required
def edit_member(member_id):
    # Ensure only Data Chairman can access this page
    if current_user.role != 'Data Chairman':
        flash('You do not have permission to view or edit this member.')
        return redirect(url_for('main.team_members'))

    member = User.query.get_or_404(member_id)

    if request.method == 'POST':
        member.username = request.form.get('username')
        member.email = request.form.get('email')
        password = request.form.get('password')

        if password:
            member.set_password(password)

        db.session.commit()
        flash('Member details updated successfully.', 'success')
        return redirect(url_for('main.team_members'))

    return render_template('edit_member.html', member=member)

def has_permission_to_edit(user):
    return user.role in ['Event Leader', 'Head of Metrics', 'Chair', 'Chairman', 'Data Chairman']

@main.route('/statistic/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_statistic(id):
    if not has_permission_to_edit(current_user):
        flash('You do not have permission to edit statistics.')
        return redirect(url_for('main.dashboard'))

    stat = Statistics.query.get_or_404(id)
    if request.method == 'POST':
        score = request.form.get('score')
        notes = request.form.get('notes')
        if score:
            stat.score = float(score)
            stat.notes = notes
            stat.added_by_user_id = current_user.id
            db.session.commit()
            flash('Statistics updated successfully', 'success')
            return redirect(url_for('main.member_detail', member_id=stat.user_id))
        else:
            flash('Please enter a valid score', 'danger')
    return render_template('edit_statistic.html', stat=stat)

@main.route('/statistic/delete/<int:id>', methods=['POST'])
@login_required
def delete_statistic(id):
    if not has_permission_to_edit(current_user):
        flash('You do not have permission to edit statistics.')
        return redirect(url_for('main.dashboard'))
    
    stat = Statistics.query.get_or_404(id)
    db.session.delete(stat)
    db.session.commit()
    flash('Statistic deleted successfully', 'success')
    return redirect(url_for('main.member_detail', member_id=stat.user_id))

@main.route('/tournament/<int:tournament_id>', methods=['GET', 'POST'])
@login_required
def tournament_detail(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)
    users = User.query.filter(User.role == 'Member').all()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add_participant' and current_user.role in ['Data Chairman', 'Chairman']:
            participant_id = request.form.get('participant')
            participant = User.query.get(participant_id)
            if participant and participant not in tournament.participants:
                tournament.participants.append(participant)
                db.session.commit()
                flash('Participant added successfully.')

        elif action == 'end_tournament' and current_user.role in ['Data Chairman', 'Chairman']:
            tournament.status = 'ended'
            db.session.commit()
            flash('Tournament ended successfully.')

        elif action == 'add_scores' and current_user.role in ['Data Chairman', 'Chairman']:
            for participant in tournament.participants:
                score = request.form.get(f'score_{participant.id}')
                if score:
                    stat = Statistics(user_id=participant.id, tournament_id=tournament.id, score=float(score))
                    db.session.add(stat)
            db.session.commit()
            
            for participant in tournament.participants:
                if participant.events:
                    update_ranks_and_groups(participant.events[0].id)
            
            flash('Scores added successfully.')

        elif action == 'remove_participant' and current_user.role in ['Data Chairman', 'Chairman']:
            participant_id = request.form.get('participant_id')
            participant = User.query.get(participant_id)
            if participant and participant in tournament.participants:
                tournament.participants.remove(participant)
                db.session.commit()
                flash('Participant removed successfully.')

        return redirect(url_for('main.tournament_detail', tournament_id=tournament.id))

    return render_template('tournament_detail.html', tournament=tournament, users=users)

@main.route('/search_participants/<int:tournament_id>')
@login_required
def search_participants(tournament_id):
    query = request.args.get('query', '')
    tournament = Tournament.query.get_or_404(tournament_id)
    participants = tournament.participants.filter(User.username.ilike(f'%{query}%')).all()
    return jsonify([{'id': p.id, 'username': p.username, 'event': p.events[0].name if p.events else 'No Event'} for p in participants])

@main.route('/member/<int:member_id>', methods=['GET', 'POST'])
@login_required
def member_detail(member_id):
    member = User.query.get_or_404(member_id)

    if current_user.role == 'Member' and current_user.id != member_id:
        flash('You do not have permission to view this profile.')
        return redirect(url_for('main.team_members'))

    if request.method == 'POST':
        metric_type = request.form.get('metric_type')
        score = request.form.get('score')
        notes = request.form.get('notes')

        if score:
            score = float(score)
            new_stat = Statistics(user_id=member.id, score=score, notes=notes, added_by_user_id=current_user.id)

            if metric_type == 'tournament':
                event_id = request.form.get('event_id')
                tournament_id = request.form.get('tournament_id')
                if event_id and tournament_id:
                    new_stat.event_id = event_id
                    new_stat.tournament_id = tournament_id
                else:
                    flash('Please select both event and tournament for tournament metrics.')
                    return redirect(url_for('main.member_detail', member_id=member.id))
            else:
                new_stat.event_id = None
                new_stat.tournament_id = None

            db.session.add(new_stat)
            db.session.commit()

            if new_stat.event_id:
                update_ranks_and_groups(new_stat.event_id)

            flash('Statistics added successfully')
        else:
            flash('Please enter a score')

    member_stats = Statistics.query.filter_by(user_id=member_id).order_by(Statistics.date.desc()).all()
    statistics_info = []
    for stat in member_stats:
        stat_info = {
            'id': stat.id,  # Ensure 'id' is included
            'event_name': stat.event.name if stat.event else "N/A",
            'tournament_name': stat.tournament.name if stat.tournament else "N/A",
            'score': stat.score,
            'rank': stat.rank if stat.rank else "N/A",
            'group': stat.group if stat.group else "N/A",
            'notes': stat.notes,
            'date': stat.date.strftime('%Y-%m-%d'),
        }
        statistics_info.append(stat_info)

    events = Event.query.all()
    return render_template('member_detail.html', member=member, events=events, statistics_info=statistics_info)

@main.route('/delete_team_member/<int:member_id>')
@login_required
def delete_team_member(member_id):
    # Only a Data Chairman can delete a Head of Metrics, Chairman, or Data Chairman
    can_delete_roles = ['Head of Metrics', 'Chairman', 'Data Chairman']
    
    member = User.query.get_or_404(member_id)
    
    if member.role in can_delete_roles:
        if current_user.role != 'Data Chairman':
            flash('Only a Data Chairman can delete these roles.')
            return redirect(url_for('main.team_members'))
    elif current_user.role not in can_delete_roles:
        flash('You do not have permission to delete team members.')
        return redirect(url_for('main.team_members'))

    # Delete associated statistics to avoid the foreign key violation
    Statistics.query.filter_by(user_id=member.id).delete()

    db.session.delete(member)
    db.session.commit()
    flash('Team member and their statistics deleted successfully.')
    return redirect(url_for('main.team_members'))

@main.route('/generate_sample_csv')
@login_required
def generate_sample_csv_route():
    if current_user.role in ['Head of Metrics', 'Chair', 'Chairman', 'Data Chairman']:
        return generate_sample_csv()
    else:
        flash('You do not have permission to generate sample CSV')
        return redirect(url_for('main.dashboard'))

@main.route('/add_participant/<int:event_id>', methods=['GET', 'POST'])
@login_required
def add_participant(event_id):
    if current_user.role not in ['Event Leader', 'Head of Metrics', 'Chair', 'Chairman', 'Data Chairman']:
        flash('You do not have permission to add participants.')
        return redirect(url_for('main.events'))

    event = Event.query.get_or_404(event_id)
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            event.participants.append(existing_user)
        else:
            new_participant = User(username=username, email=email, role='Participant', is_participant=True)
            db.session.add(new_participant)
            event.participants.append(new_participant)
        
        db.session.commit()
        flash('Participant added successfully.')
        return redirect(url_for('main.event_detail', event_id=event.id))

    return render_template('add_participant.html', event=event)

@main.route('/tournament/<int:tournament_id>/add_participants', methods=['GET', 'POST'])
@login_required
def add_tournament_participants(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)
    page = request.args.get('page', 1, type=int)
    events = Event.query.paginate(page=page, per_page=1, error_out=False)
    
    if request.method == 'POST':
        participant_id = request.form.get('participant_id')
        participant = User.query.get(participant_id)
        if participant and participant not in tournament.participants:
            tournament.participants.append(participant)
            db.session.commit()
            flash('Participant added successfully.')
    
    return render_template('add_tournament_participants.html', tournament=tournament, events=events)