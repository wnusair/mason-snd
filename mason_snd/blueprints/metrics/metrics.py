import csv
from io import StringIO
from math import ceil
import json
import pytz
from datetime import datetime, timedelta
from collections import defaultdict, Counter

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, Response, jsonify

from mason_snd.extensions import db
from mason_snd.models.auth import User
from mason_snd.models.admin import User_Requirements, Requirements
from mason_snd.models.tournaments import Tournament, Tournament_Performance, Tournament_Signups, Tournament_Judges
from mason_snd.models.events import Event, User_Event, Effort_Score
from mason_snd.models.metrics import MetricsSettings
from mason_snd.models.auth import Judges

from sqlalchemy import asc, desc, func, and_, or_, extract
import pytz

EST = pytz.timezone('US/Eastern')
metrics_bp = Blueprint('metrics', __name__, template_folder='templates')

def normalize_timestamp_for_comparison(timestamp):
    """
    Helper function to normalize timestamps for timezone-aware comparisons.
    If timestamp is naive, assumes it's in EST timezone.
    """
    if timestamp is None:
        return None
    if timestamp.tzinfo is None:
        return EST.localize(timestamp)
    return timestamp

def get_point_weights():
    """Helper function to get tournament and effort weights from settings"""
    settings = MetricsSettings.query.first()
    if not settings:
        settings = MetricsSettings()
        db.session.add(settings)
        db.session.commit()
    return settings.tournament_weight, settings.effort_weight

def calculate_comprehensive_stats():
    """Calculate comprehensive statistics across the entire system"""
    current_date = datetime.now(EST)
    
    # Basic stats
    total_users = User.query.count()
    total_tournaments = Tournament.query.count()
    total_events = Event.query.count()
    
    # Tournament stats
    past_tournaments = Tournament.query.filter(Tournament.date < current_date).count()
    upcoming_tournaments = Tournament.query.filter(Tournament.date >= current_date).count()
    
    # Performance stats
    total_performances = Tournament_Performance.query.count()
    avg_points_per_tournament = db.session.query(func.avg(Tournament_Performance.points)).scalar() or 0
    
    # Effort stats
    total_effort_scores = Effort_Score.query.count()
    avg_effort_score = db.session.query(func.avg(Effort_Score.score)).scalar() or 0
    
    # User engagement - since tournament_points is a property, we need to filter differently
    # Count users who have at least one tournament performance
    active_users = db.session.query(User.id).join(Tournament_Performance).distinct().count()
    users_with_bids = User.query.filter(User.bids > 0).count()
    
    # Recent activity (last 30 days)
    thirty_days_ago = current_date - timedelta(days=30)
    recent_tournaments = Tournament.query.filter(Tournament.date >= thirty_days_ago).count()
    # For effort scores, handle timezone issues by filtering on Python side
    all_recent_effort_scores = Effort_Score.query.all()
    recent_effort_scores = 0
    for es in all_recent_effort_scores:
        if es.timestamp:
            timestamp = es.timestamp
            if timestamp.tzinfo is None:
                timestamp = EST.localize(timestamp)
            if timestamp >= thirty_days_ago:
                recent_effort_scores += 1
    
    return {
        'total_users': total_users,
        'total_tournaments': total_tournaments,
        'total_events': total_events,
        'past_tournaments': past_tournaments,
        'upcoming_tournaments': upcoming_tournaments,
        'total_performances': total_performances,
        'avg_points_per_tournament': round(avg_points_per_tournament, 2),
        'total_effort_scores': total_effort_scores,
        'avg_effort_score': round(avg_effort_score, 2),
        'active_users': active_users,
        'users_with_bids': users_with_bids,
        'recent_tournaments': recent_tournaments,
        'recent_effort_scores': recent_effort_scores,
        'engagement_rate': round((active_users / total_users * 100) if total_users > 0 else 0, 1)
    }

def get_tournament_trends():
    """Get tournament performance trends over time"""
    tournaments = Tournament.query.filter(Tournament.date < datetime.now(EST)).order_by(Tournament.date).all()
    
    trend_data = []
    cumulative_points = 0
    cumulative_participants = 0
    
    for tournament in tournaments:
        performances = Tournament_Performance.query.filter_by(tournament_id=tournament.id).all()
        tournament_points = sum(p.points or 0 for p in performances)
        participant_count = len(performances)
        
        cumulative_points += tournament_points
        cumulative_participants += participant_count
        
        trend_data.append({
            'tournament_name': tournament.name,
            'date': tournament.date.strftime('%Y-%m-%d'),
            'points': tournament_points,
            'participants': participant_count,
            'avg_points_per_participant': round(tournament_points / participant_count, 2) if participant_count > 0 else 0,
            'cumulative_points': cumulative_points,
            'cumulative_participants': cumulative_participants
        })
    
    return trend_data

def get_event_performance_analytics():
    """Get detailed event performance analytics"""
    events = Event.query.all()
    event_analytics = []
    
    for event in events:
        # Get users participating in this event
        user_events = User_Event.query.filter_by(event_id=event.id, active=True).all()
        participants = [ue.user for ue in user_events]
        
        if not participants:
            continue
        
        # Calculate statistics
        tournament_points = [u.tournament_points or 0 for u in participants]
        effort_points = [u.effort_points or 0 for u in participants]
        
        # Get effort scores for this event
        effort_scores = Effort_Score.query.filter_by(event_id=event.id).all()
        # Fix timezone comparison - ensure both sides are timezone-aware
        thirty_days_ago = datetime.now(EST) - timedelta(days=30)
        recent_effort_scores = []
        for es in effort_scores:
            if es.timestamp:
                # Handle both timezone-aware and naive timestamps
                timestamp = es.timestamp
                if timestamp.tzinfo is None:
                    # If timestamp is naive, assume it's in EST
                    timestamp = EST.localize(timestamp)
                if timestamp >= thirty_days_ago:
                    recent_effort_scores.append(es.score)
        
        # Tournament participation analysis
        tournament_participations = []
        for user in participants:
            perf_count = Tournament_Performance.query.filter_by(user_id=user.id).count()
            tournament_participations.append(perf_count)
        
        event_analytics.append({
            'event': event,
            'participant_count': len(participants),
            'avg_tournament_points': round(sum(tournament_points) / len(tournament_points), 2) if tournament_points else 0,
            'avg_effort_points': round(sum(effort_points) / len(effort_points), 2) if effort_points else 0,
            'total_effort_scores': len(effort_scores),
            'recent_effort_scores': len(recent_effort_scores),
            'avg_recent_effort': round(sum(recent_effort_scores) / len(recent_effort_scores), 2) if recent_effort_scores else 0,
            'avg_tournament_participation': round(sum(tournament_participations) / len(tournament_participations), 2) if tournament_participations else 0,
            'top_performers': sorted(participants, key=lambda u: (u.tournament_points or 0) + (u.effort_points or 0), reverse=True)[:5]
        })
    
    return sorted(event_analytics, key=lambda x: x['avg_tournament_points'] + x['avg_effort_points'], reverse=True)

def get_user_performance_distribution():
    """Get distribution of user performance for analytics"""
    users = User.query.all()
    tournament_weight, effort_weight = get_point_weights()
    
    performance_buckets = {
        'high_performers': [],      # Top 20%
        'mid_performers': [],       # Middle 60%
        'low_performers': [],       # Bottom 20%
        'inactive': []             # No points
    }
    
    # Calculate weighted scores for all users
    user_scores = []
    for user in users:
        tournament_pts = user.tournament_points or 0
        effort_pts = user.effort_points or 0
        weighted_score = tournament_pts * tournament_weight + effort_pts * effort_weight
        
        if weighted_score > 0:
            user_scores.append((user, weighted_score))
        else:
            performance_buckets['inactive'].append(user)
    
    # Sort by weighted score
    user_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Distribute into buckets
    total_active = len(user_scores)
    if total_active > 0:
        high_threshold = int(total_active * 0.2)
        low_threshold = int(total_active * 0.8)
        
        performance_buckets['high_performers'] = [u[0] for u in user_scores[:high_threshold]]
        performance_buckets['mid_performers'] = [u[0] for u in user_scores[high_threshold:low_threshold]]
        performance_buckets['low_performers'] = [u[0] for u in user_scores[low_threshold:]]
    
    return performance_buckets

def next_direction(column, current_sort, current_direction):
    """Helper function to determine next sort direction"""
    if current_sort == column:
        if current_direction == 'asc':
            return 'desc'
        elif current_direction == 'desc':
            return 'default'
        else:
            return 'asc'
    else:
        return 'asc'

@metrics_bp.route('/')
def index():
    """Main metrics dashboard with comprehensive analytics"""
    user_id = session.get('user_id')
    if not user_id:
        flash("Log in first!")
        return redirect(url_for('auth.login'))
    user = User.query.filter_by(id=user_id).first()
    if not user or user.role < 2:
        flash("Restricted Access!")
        return redirect(url_for('profile.index', user_id=user_id))

    # Get comprehensive stats
    stats = calculate_comprehensive_stats()
    
    # Get performance distribution
    performance_distribution = get_user_performance_distribution()
    
    # Get recent tournament trends (last 10 tournaments)
    recent_trends = get_tournament_trends()[-10:]
    
    # Get top performers - since tournament_points and effort_points are properties, 
    # we need to get users who have either tournament performances or effort scores
    tournament_weight, effort_weight = get_point_weights()
    
    # Get users with tournament performances
    users_with_tournament_points = db.session.query(User.id).join(Tournament_Performance).distinct().subquery()
    # Get users with effort scores - specify the join condition to avoid ambiguity
    users_with_effort_points = db.session.query(User.id).join(Effort_Score, User.id == Effort_Score.user_id).distinct().subquery()
    
    # Get all users who have either type of points
    top_performers_query = User.query.filter(
        or_(
            User.id.in_(db.session.query(users_with_tournament_points.c.id)),
            User.id.in_(db.session.query(users_with_effort_points.c.id))
        )
    ).all()
    
    top_performers = []
    for u in top_performers_query:
        weighted_score = (u.tournament_points or 0) * tournament_weight + (u.effort_points or 0) * effort_weight
        top_performers.append({
            'user': u,
            'weighted_score': weighted_score,
            'total_score': (u.tournament_points or 0) + (u.effort_points or 0)
        })
    
    top_performers = sorted(top_performers, key=lambda x: x['weighted_score'], reverse=True)[:10]
    
    # Get event performance analytics
    event_analytics = get_event_performance_analytics()[:5]  # Top 5 events
    
    # Prepare chart data
    trend_labels = [t['tournament_name'][:15] + '...' if len(t['tournament_name']) > 15 else t['tournament_name'] for t in recent_trends]
    trend_points = [t['points'] for t in recent_trends]
    trend_participants = [t['participants'] for t in recent_trends]
    
    return render_template(
        'metrics/dashboard.html',
        stats=stats,
        performance_distribution=performance_distribution,
        top_performers=top_performers,
        event_analytics=event_analytics,
        trend_labels=json.dumps(trend_labels),
        trend_points=json.dumps(trend_points),
        trend_participants=json.dumps(trend_participants),
        settings=MetricsSettings.query.first()
    )

@metrics_bp.route('/user_metrics')
def user_metrics():
    user_id = session.get('user_id')
    if not user_id:
        flash("Log in first!")
        return redirect(url_for('auth.login'))
    user = User.query.filter_by(id=user_id).first()
    if not user or user.role < 2:
        flash("Restricted Access!")
        return redirect(url_for('profile.index', user_id=user_id))

    page = request.args.get('page', 1, type=int)
    per_page = 15
    sort = request.args.get('sort', 'default')
    direction = request.args.get('direction', 'default')

    tournament_weight, effort_weight = get_point_weights()

    # Map sort keys to model columns or expressions
    sort_map = {
        'name': (User.last_name, User.first_name),
        'bids': User.bids
    }

    # For computed fields, fetch all users and sort in Python
    computed_sorts = ['total_points', 'weighted_points', 'tournament_points', 'effort_points']
    if sort in computed_sorts and direction in ['asc', 'desc']:
        users = User.query.all()
        if sort == 'total_points':
            key_func = lambda u: (u.tournament_points or 0) + (u.effort_points or 0)
        elif sort == 'weighted_points':
            key_func = lambda u: (u.tournament_points or 0) * tournament_weight + (u.effort_points or 0) * effort_weight
        elif sort == 'tournament_points':
            key_func = lambda u: u.tournament_points or 0
        elif sort == 'effort_points':
            key_func = lambda u: u.effort_points or 0
        else:
            key_func = None
        reverse = direction == 'desc'
        users_sorted = sorted(users, key=key_func, reverse=reverse)
        # Paginate manually
        total = len(users_sorted)
        start = (page - 1) * per_page
        end = start + per_page
        items = users_sorted[start:end]
        class Pagination:
            def __init__(self, items, page, per_page, total):
                self.items = items
                self.page = page
                self.per_page = per_page
                self.total = total
                self.pages = (total + per_page - 1) // per_page
                self.has_prev = page > 1
                self.has_next = page < self.pages
                self.prev_num = page - 1
                self.next_num = page + 1
        users_pagination = Pagination(items, page, per_page, total)
    else:
        query = User.query
        if sort in sort_map and direction in ['asc', 'desc']:
            col = sort_map[sort]
            if isinstance(col, tuple):
                if direction == 'asc':
                    query = query.order_by(*[c.asc() for c in col])
                else:
                    query = query.order_by(*[c.desc() for c in col])
            else:
                if direction == 'asc':
                    query = query.order_by(col.asc())
                else:
                    query = query.order_by(col.desc())
        else:
            # Default ordering
            query = query.order_by(User.last_name, User.first_name)
        users_pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    settings = MetricsSettings.query.first()
    return render_template(
        'metrics/user_metrics_overview.html',
        users=users_pagination,
        settings=settings,
        sort=sort,
        direction=direction,
        next_direction=lambda col: next_direction(col, sort, direction)
    )

@metrics_bp.route('/user_metrics/download')
def download_user_metrics():
    user_id = session.get('user_id')
    if not user_id:
        flash("Log in first!")
        return redirect(url_for('auth.login'))
    user = User.query.filter_by(id=user_id).first()
    if not user or user.role < 2:
        flash("Restricted Access!")
        return redirect(url_for('profile.index', user_id=user_id))

    sort = request.args.get('sort', 'default')
    direction = request.args.get('direction', 'default')
    
    tournament_weight, effort_weight = get_point_weights()
    
    computed_sorts = ['total_points', 'weighted_points', 'tournament_points', 'effort_points']
    # Use same logic as index to get sorted users
    sort_map = {
        'name': (User.last_name, User.first_name),
        'bids': User.bids
    }
    if sort in computed_sorts and direction in ['asc', 'desc']:
        users = User.query.all()
        if sort == 'total_points':
            key_func = lambda u: (u.tournament_points or 0) + (u.effort_points or 0)
        elif sort == 'weighted_points':
            key_func = lambda u: (u.tournament_points or 0) * tournament_weight + (u.effort_points or 0) * effort_weight
        elif sort == 'tournament_points':
            key_func = lambda u: u.tournament_points or 0
        elif sort == 'effort_points':
            key_func = lambda u: u.effort_points or 0
        else:
            key_func = None
        reverse = direction == 'desc'
        users_sorted = sorted(users, key=key_func, reverse=reverse)
    else:
        query = User.query
        if sort in sort_map and direction in ['asc', 'desc']:
            col = sort_map[sort]
            if isinstance(col, tuple):
                if direction == 'asc':
                    query = query.order_by(*[c.asc() for c in col])
                else:
                    query = query.order_by(*[c.desc() for c in col])
            else:
                if direction == 'asc':
                    query = query.order_by(col.asc())
                else:
                    query = query.order_by(col.desc())
        else:
            query = query.order_by(User.last_name, User.first_name)
        users_sorted = query.all()

    # Prepare CSV
    si = StringIO()
    writer = csv.writer(si)
    # Write header row with expanded fields
    writer.writerow([
        'First Name', 'Last Name', 'Email', 'Phone Number',
        'Emergency Contact First Name', 'Emergency Contact Last Name', 'Emergency Contact Number', 'Emergency Contact Relationship', 'Emergency Contact Email',
        'Parent/Child',
        'Bids', 'Points (Tournaments)', 'Points (Effort)', 'Total Points', f'Weighted Points ({int(tournament_weight*100)}% Tournament, {int(effort_weight*100)}% Effort)'
    ])

    for user in users_sorted:
        tournament_points = user.tournament_points or 0
        effort_points = user.effort_points or 0
        total_points = tournament_points + effort_points
        weighted_points = round(tournament_points * tournament_weight + effort_points * effort_weight, 2)

        # Determine Parent/Child status
        is_parent = Judges.query.filter_by(judge_id=user.id).first() is not None
        is_child = Judges.query.filter_by(child_id=user.id).first() is not None
        if is_parent and is_child:
            parent_child_status = 'Both'
        elif is_parent:
            parent_child_status = 'Parent'
        elif is_child:
            parent_child_status = 'Child'
        else:
            parent_child_status = ''

        writer.writerow([
            user.first_name or '',
            user.last_name or '',
            user.email or '',
            user.phone_number or '',
            user.emergency_contact_first_name or '',
            user.emergency_contact_last_name or '',
            user.emergency_contact_number or '',
            user.emergency_contact_relationship or '',
            user.emergency_contact_email or '',
            parent_child_status,
            user.bids or 0,
            tournament_points,
            effort_points,
            total_points,
            weighted_points
        ])
    output = si.getvalue()
    si.close()
    return Response(
        output,
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename=user_metrics.csv'
        }
    )

@metrics_bp.route('/event/<int:event_id>')
def event_detail(event_id):
    user_id = session.get('user_id')
    if not user_id:
        flash("Log in first!")
        return redirect(url_for('auth.login'))
    user = User.query.filter_by(id=user_id).first()
    if not user or user.role < 2:
        flash("Restricted Access!")
        return redirect(url_for('profile.index', user_id=user_id))

    event = Event.query.get_or_404(event_id)
    tournament_weight, effort_weight = get_point_weights()
    
    # Get active participants
    user_events = User_Event.query.filter_by(event_id=event.id, active=True).all()
    participants = [ue.user for ue in user_events]
    
    if not participants:
        flash("No active participants found for this event.")
        return redirect(url_for('metrics.events_overview'))
    
    # Comprehensive participant analysis
    participant_analytics = []
    for user in participants:
        # Tournament performance
        all_performances = Tournament_Performance.query.filter_by(user_id=user.id).all()
        recent_performances = Tournament_Performance.query.join(Tournament).filter(
            Tournament_Performance.user_id == user.id,
            Tournament.date >= datetime.now(EST) - timedelta(days=180)
        ).all()
        
        # Effort scores for this event
        user_effort_scores = Effort_Score.query.filter_by(user_id=user.id, event_id=event.id).all()
        thirty_days_ago_est = datetime.now(EST) - timedelta(days=30)
        recent_effort_scores = []
        for es in user_effort_scores:
            if es.timestamp:
                timestamp = es.timestamp
                if timestamp.tzinfo is None:
                    timestamp = EST.localize(timestamp)
                if timestamp >= thirty_days_ago_est:
                    recent_effort_scores.append(es.score)
        
        # Calculate statistics
        total_points = (user.tournament_points or 0) + (user.effort_points or 0)
        weighted_points = (user.tournament_points or 0) * tournament_weight + (user.effort_points or 0) * effort_weight
        
        bid_count = sum(1 for p in all_performances if p.bid)
        avg_tournament_points = round(sum(p.points or 0 for p in all_performances) / len(all_performances), 2) if all_performances else 0
        
        participant_analytics.append({
            'user': user,
            'total_points': total_points,
            'weighted_points': weighted_points,
            'tournament_participations': len(all_performances),
            'recent_participations': len(recent_performances),
            'total_bids': bid_count,
            'avg_tournament_points': avg_tournament_points,
            'effort_score_count': len(user_effort_scores),
            'recent_effort_count': len(recent_effort_scores),
            'avg_effort_score': round(sum(es.score for es in user_effort_scores) / len(user_effort_scores), 2) if user_effort_scores else 0,
            'recent_avg_effort': round(sum(recent_effort_scores) / len(recent_effort_scores), 2) if recent_effort_scores else 0
        })
    
    # Sort participants by weighted points
    participant_analytics.sort(key=lambda x: x['weighted_points'], reverse=True)
    
    # Event statistics
    tournament_points_list = [p['user'].tournament_points or 0 for p in participant_analytics]
    effort_points_list = [p['user'].effort_points or 0 for p in participant_analytics]
    
    event_stats = {
        'total_participants': len(participants),
        'avg_tournament_points': round(sum(tournament_points_list) / len(tournament_points_list), 2) if tournament_points_list else 0,
        'avg_effort_points': round(sum(effort_points_list) / len(effort_points_list), 2) if effort_points_list else 0,
        'total_tournament_participations': sum(p['tournament_participations'] for p in participant_analytics),
        'total_bids': sum(p['total_bids'] for p in participant_analytics),
        'avg_participations_per_person': round(sum(p['tournament_participations'] for p in participant_analytics) / len(participant_analytics), 2),
        'event_type': {0: 'Speech', 1: 'Lincoln-Douglas', 2: 'Public Forum'}.get(event.event_type, 'Unknown')
    }
    
    # Performance distribution
    performance_distribution = [
        {'category': 'High Performers (60+ pts)', 'count': len([p for p in tournament_points_list if p >= 60])},
        {'category': 'Mid Performers (20-59 pts)', 'count': len([p for p in tournament_points_list if 20 <= p < 60])},
        {'category': 'Developing (1-19 pts)', 'count': len([p for p in tournament_points_list if 0 < p < 20])},
        {'category': 'New Members (0 pts)', 'count': len([p for p in tournament_points_list if p == 0])}
    ]
    
    # Recent activity trends (last 6 months)
    six_months_ago = datetime.now(EST) - timedelta(days=180)
    monthly_data = []
    
    for i in range(6):
        month_start = six_months_ago + timedelta(days=30*i)
        month_end = month_start + timedelta(days=30)
        
        # Count effort scores in this month for this event - handle timezone issues
        all_effort_scores = Effort_Score.query.filter(Effort_Score.event_id == event.id).all()
        month_effort_scores = 0
        for es in all_effort_scores:
            if es.timestamp:
                timestamp = es.timestamp
                if timestamp.tzinfo is None:
                    timestamp = EST.localize(timestamp)
                if month_start <= timestamp < month_end:
                    month_effort_scores += 1
        
        # Count tournament performances for event participants
        month_performances = db.session.query(Tournament_Performance).join(Tournament).filter(
            Tournament_Performance.user_id.in_([p.id for p in participants]),
            Tournament.date >= month_start,
            Tournament.date < month_end
        ).count()
        
        monthly_data.append({
            'month': month_start.strftime('%b %Y'),
            'effort_scores': month_effort_scores,
            'tournament_performances': month_performances
        })
    
    return render_template('metrics/event_detail.html',
                         event=event,
                         event_stats=event_stats,
                         participant_analytics=participant_analytics,
                         performance_distribution=performance_distribution,
                         monthly_data=monthly_data)

@metrics_bp.route('/user/<int:user_id>')
def user_detail(user_id):
    current_user_id = session.get('user_id')
    if not current_user_id:
        flash("Log in first!")
        return redirect(url_for('auth.login'))
    current_user = User.query.filter_by(id=current_user_id).first()
    if not current_user or current_user.role < 2:
        flash("Restricted Access!")
        return redirect(url_for('profile.index', user_id=current_user_id))

    user = User.query.get_or_404(user_id)
    tournament_weight, effort_weight = get_point_weights()

    # Comprehensive user analytics
    performances = Tournament_Performance.query.filter_by(user_id=user_id).join(Tournament).order_by(Tournament.date).all()
    
    total_points = (user.tournament_points or 0) + (user.effort_points or 0)
    weighted_points = (user.tournament_points or 0) * tournament_weight + (user.effort_points or 0) * effort_weight

    # Tournament progression analysis
    progression_data = []
    cumulative_points = 0
    
    for p in performances:
        cumulative_points += p.points or 0
        progression_data.append({
            'tournament': p.tournament.name,
            'date': p.tournament.date.strftime('%Y-%m-%d'),
            'points': p.points or 0,
            'cumulative_points': cumulative_points,
            'rank': p.rank,
            'stage': {0: 'No Advancement', 1: 'Double Octas', 2: 'Octas', 3: 'Quarters', 4: 'Semis', 5: 'Finals'}.get(p.stage, 'Unknown') if p.stage is not None else 'Unknown',
            'bid': p.bid
        })

    # Performance statistics
    if performances:
        points_list = [p.points or 0 for p in performances]
        performance_stats = {
            'total_tournaments': len(performances),
            'total_bids': sum(1 for p in performances if p.bid),
            'avg_points': round(sum(points_list) / len(points_list), 2),
            'best_performance': max(points_list),
            'recent_avg': round(sum(points_list[-5:]) / min(5, len(points_list)), 2),  # Last 5 tournaments
            'improvement_trend': round((sum(points_list[-3:]) / 3 - sum(points_list[:3]) / 3), 2) if len(points_list) >= 6 else 0,
            'bid_rate': round(sum(1 for p in performances if p.bid) / len(performances) * 100, 1)
        }
    else:
        performance_stats = {
            'total_tournaments': 0, 'total_bids': 0, 'avg_points': 0,
            'best_performance': 0, 'recent_avg': 0, 'improvement_trend': 0, 'bid_rate': 0
        }

    # Event participation and effort analysis
    user_events = User_Event.query.filter_by(user_id=user_id, active=True).all()
    event_analytics = []
    
    for ue in user_events:
        event = ue.event
        effort_scores = Effort_Score.query.filter_by(user_id=user_id, event_id=event.id).all()
        thirty_days_ago_est = datetime.now(EST) - timedelta(days=30)
        recent_effort_scores = []
        for es in effort_scores:
            if es.timestamp:
                timestamp = es.timestamp
                if timestamp.tzinfo is None:
                    timestamp = EST.localize(timestamp)
                if timestamp >= thirty_days_ago_est:
                    recent_effort_scores.append(es.score)
        
        event_analytics.append({
            'event': event,
            'effort_score_count': len(effort_scores),
            'recent_effort_count': len(recent_effort_scores),
            'avg_effort_score': round(sum(es.score for es in effort_scores) / len(effort_scores), 2) if effort_scores else 0,
            'recent_avg_effort': round(sum(recent_effort_scores) / len(recent_effort_scores), 2) if recent_effort_scores else 0
        })

    # Peer comparison - get users who have tournament performances
    users_with_performances = db.session.query(User.id).join(Tournament_Performance).distinct().subquery()
    all_users = User.query.filter(User.id.in_(db.session.query(users_with_performances.c.id))).all()
    user_rank = 1
    for other_user in all_users:
        other_weighted = (other_user.tournament_points or 0) * tournament_weight + (other_user.effort_points or 0) * effort_weight
        if other_weighted > weighted_points:
            user_rank += 1

    # Chart data for progression
    chart_labels = [p['tournament'][:15] + '...' if len(p['tournament']) > 15 else p['tournament'] for p in progression_data]
    chart_points = [p['points'] for p in progression_data]
    chart_cumulative = [p['cumulative_points'] for p in progression_data]
    
    # Prediction based on recent trend
    prediction_points = []
    if len(chart_points) >= 3:
        recent_trend = sum(chart_points[-3:]) / 3 - sum(chart_points[-6:-3]) / 3 if len(chart_points) >= 6 else 0
        next_predicted = chart_points[-1] + recent_trend
        prediction_points = [None] * len(chart_points) + [max(0, round(next_predicted))]
        chart_labels.append("Next (Predicted)")

    # Calculate trend direction and percentage
    trend_direction = 'flat'
    trend_percentage = 0
    if len(chart_points) >= 2:
        recent_avg = sum(chart_points[-3:]) / min(3, len(chart_points[-3:]))
        older_avg = sum(chart_points[:-3]) / len(chart_points[:-3]) if len(chart_points) > 3 else chart_points[0]
        if recent_avg > older_avg * 1.05:  # 5% improvement threshold
            trend_direction = 'up'
            trend_percentage = round(((recent_avg - older_avg) / older_avg) * 100, 1)
        elif recent_avg < older_avg * 0.95:  # 5% decline threshold
            trend_direction = 'down'
            trend_percentage = round(((older_avg - recent_avg) / older_avg) * 100, 1)

    # Recent activity (tournaments in last 6 months)
    six_months_ago = datetime.now(EST) - timedelta(days=180)
    recent_activity = []
    recent_tournaments = 0
    for perf in performances:
        # Handle potential timezone issues with tournament dates
        tournament_date = perf.tournament.date
        if tournament_date.tzinfo is None:
            tournament_date = EST.localize(tournament_date)
        if tournament_date >= six_months_ago:
            recent_tournaments += 1
            recent_activity.append({
                'type': 'Tournament',
                'name': perf.tournament.name,
                'tournament_name': perf.tournament.name,  # Template expects this key
                'tournament_id': perf.tournament.id,       # Template expects this key
                'date': perf.tournament.date,
                'points': perf.points,
                'bid': perf.bid,
                'color': 'blue'  # Add color for the template
            })

    # Top events (based on effort scores) - format for template
    top_events = []
    for event_data in sorted(event_analytics, key=lambda x: x['avg_effort_score'], reverse=True):
        # Get tournament participation count for this user in this event
        user_performances_in_event = [p for p in performances if p.tournament and any(
            ue.event_id == event_data['event'].id and ue.user_id == user_id 
            for ue in User_Event.query.filter_by(user_id=user_id, event_id=event_data['event'].id, active=True).all()
        )]
        
        top_events.append({
            'emoji': event_data['event'].event_emoji or '🎯',
            'event_name': event_data['event'].event_name,
            'participation_count': len(user_performances_in_event),
            'avg_points': event_data['avg_effort_score']
        })

    # Simple achievements based on performance
    achievements = []
    if performance_stats['total_tournaments'] >= 10:
        achievements.append({'name': 'Tournament Veteran', 'description': '10+ tournaments completed'})
    if performance_stats['bid_rate'] >= 50:
        achievements.append({'name': 'Consistent Performer', 'description': '50%+ bid rate'})
    if performance_stats['best_performance'] >= 100:
        achievements.append({'name': 'High Achiever', 'description': '100+ points in a tournament'})

    # Create the user_stats object that the template expects
    user_stats = {
        'weighted_points': weighted_points,
        'rank': user_rank,
        'total_users': len(all_users),
        'total_points': total_points,
        'avg_points_per_tournament': performance_stats['avg_points'],
        'tournament_count': performance_stats['total_tournaments'],
        'recent_tournaments': recent_tournaments,
        'trend_direction': trend_direction,
        'trend_percentage': trend_percentage,
        'recent_activity': recent_activity,
        'top_events': top_events,
        'achievements': achievements
    }

    return render_template('metrics/user_detail.html', 
                         user=user,
                         user_stats=user_stats,
                         performance_stats=performance_stats,
                         progression_data=progression_data,
                         event_analytics=event_analytics,
                         total_points=total_points, 
                         weighted_points=weighted_points,
                         user_rank=user_rank,
                         total_users=len(all_users),
                         chart_labels=json.dumps(chart_labels), 
                         chart_points=json.dumps(chart_points),
                         chart_cumulative=json.dumps(chart_cumulative),
                         prediction_points=json.dumps(prediction_points))

@metrics_bp.route('/tournaments')
def tournaments_overview():
    user_id = session.get('user_id')
    if not user_id:
        flash("Log in first!")
        return redirect(url_for('auth.login'))
    user = User.query.filter_by(id=user_id).first()
    if not user or user.role < 2:
        flash("Restricted Access!")
        return redirect(url_for('profile.index', user_id=user_id))

    page = request.args.get('page', 1, type=int)
    per_page = 15
    sort = request.args.get('sort', 'date')
    direction = request.args.get('direction', 'desc')

    # Base query - sort by date by default to show proper chronological trends
    tournaments_query = Tournament.query
    
    # Handle sorting
    if sort == 'name':
        order_by = Tournament.name.asc() if direction == 'asc' else Tournament.name.desc()
        tournaments_query = tournaments_query.order_by(order_by)
        tournaments = tournaments_query.paginate(page=page, per_page=per_page, error_out=False)
    elif sort == 'date':
        order_by = Tournament.date.asc() if direction == 'asc' else Tournament.date.desc()
        tournaments_query = tournaments_query.order_by(order_by)
        tournaments = tournaments_query.paginate(page=page, per_page=per_page, error_out=False)
    else:
        # For computed sorts (total_points, total_bids, avg_points, participation_rate), we need to fetch all and sort manually
        all_tournaments = Tournament.query.order_by(Tournament.date.desc()).all()
        all_tournament_data = {}
        
        for t in all_tournaments:
            performances = Tournament_Performance.query.filter_by(tournament_id=t.id).all()
            signups = Tournament_Signups.query.filter_by(tournament_id=t.id, is_going=True).count()
            
            total_points = sum(p.points or 0 for p in performances)
            total_bids = sum(1 for p in performances if p.bid)
            participant_count = len(performances)
            avg_points = total_points / participant_count if participant_count > 0 else 0
            participation_rate = participant_count / signups if signups > 0 else 0
            
            all_tournament_data[t.id] = {
                'tournament': t,
                'total_points': total_points,
                'total_bids': total_bids,
                'avg_points': avg_points,
                'participant_count': participant_count,
                'participation_rate': participation_rate,
                'signups': signups
            }
        
        if sort == 'total_points':
            sorted_items = sorted(all_tournament_data.values(), key=lambda x: x['total_points'], reverse=direction=='desc')
        elif sort == 'total_bids':
            sorted_items = sorted(all_tournament_data.values(), key=lambda x: x['total_bids'], reverse=direction=='desc')
        elif sort == 'avg_points':
            sorted_items = sorted(all_tournament_data.values(), key=lambda x: x['avg_points'], reverse=direction=='desc')
        elif sort == 'participation_rate':
            sorted_items = sorted(all_tournament_data.values(), key=lambda x: x['participation_rate'], reverse=direction=='desc')
        else:
            sorted_items = sorted(all_tournament_data.values(), key=lambda x: x['tournament'].date, reverse=True)
        
        # Manual pagination
        start = (page - 1) * per_page
        end = start + per_page
        paginated_items = sorted_items[start:end]

        # Create pagination object
        class Pagination:
            def __init__(self, items, page, per_page, total):
                self.items = [item['tournament'] for item in items]
                self.page = page
                self.per_page = per_page
                self.total = total
                self.pages = int(ceil(total / per_page))
                self.has_prev = page > 1
                self.has_next = page < self.pages
                self.prev_num = page - 1
                self.next_num = page + 1
        
        tournaments = Pagination(paginated_items, page, per_page, len(all_tournaments))

    # Calculate tournament analytics for display
    tournament_analytics = {}
    for t in tournaments.items:
        performances = Tournament_Performance.query.filter_by(tournament_id=t.id).all()
        signups = Tournament_Signups.query.filter_by(tournament_id=t.id, is_going=True).count()
        
        total_points = sum(p.points or 0 for p in performances)
        total_bids = sum(1 for p in performances if p.bid)
        participant_count = len(performances)
        avg_points = total_points / participant_count if participant_count > 0 else 0
        participation_rate = participant_count / signups if signups > 0 else 0
        
        # Calculate stage distribution
        stage_distribution = Counter(p.stage for p in performances if p.stage is not None)
        
        tournament_analytics[t.id] = {
            'total_points': total_points,
            'total_bids': total_bids,
            'avg_points': round(avg_points, 2),
            'participant_count': participant_count,
            'signups': signups,
            'participation_rate': round(participation_rate * 100, 1),
            'stage_distribution': dict(stage_distribution),
            'bid_rate': round((total_bids / participant_count * 100) if participant_count > 0 else 0, 1)
        }

    # Chart data for timeline (chronological order)
    chart_tournaments = Tournament.query.filter(Tournament.date < datetime.now(EST)).order_by(Tournament.date).all()
    chart_labels = []
    chart_points = []
    chart_participants = []
    chart_avg_points = []
    
    for t in chart_tournaments[-15:]:  # Last 15 tournaments for chart
        performances = Tournament_Performance.query.filter_by(tournament_id=t.id).all()
        total_points = sum(p.points or 0 for p in performances)
        participant_count = len(performances)
        avg_points = total_points / participant_count if participant_count > 0 else 0
        
        chart_labels.append(t.name[:20] + '...' if len(t.name) > 20 else t.name)
        chart_points.append(total_points)
        chart_participants.append(participant_count)
        chart_avg_points.append(round(avg_points, 2))

    return render_template('metrics/tournaments_overview.html', 
                         tournaments=tournaments, 
                         tournament_analytics=tournament_analytics,
                         sort=sort, 
                         direction=direction, 
                         chart_labels=json.dumps(chart_labels), 
                         chart_points=json.dumps(chart_points),
                         chart_participants=json.dumps(chart_participants),
                         chart_avg_points=json.dumps(chart_avg_points),
                         next_direction=lambda col: next_direction(col, sort, direction))

@metrics_bp.route('/tournament/<int:tournament_id>')
def tournament_detail(tournament_id):
    user_id = session.get('user_id')
    if not user_id:
        flash("Log in first!")
        return redirect(url_for('auth.login'))
    user = User.query.filter_by(id=user_id).first()
    if not user or user.role < 2:
        flash("Restricted Access!")
        return redirect(url_for('profile.index', user_id=user_id))

    tournament = Tournament.query.get_or_404(tournament_id)
    tournament_weight, effort_weight = get_point_weights()

    # Get all related data
    performances = Tournament_Performance.query.filter_by(tournament_id=tournament_id).all()
    signups = Tournament_Signups.query.filter_by(tournament_id=tournament_id).all()
    judges = Tournament_Judges.query.filter_by(tournament_id=tournament_id, accepted=True).all()
    
    # Basic tournament stats
    total_signups = len([s for s in signups if s.is_going])
    actual_participants = len(performances)
    participation_rate = round((actual_participants / total_signups * 100) if total_signups > 0 else 0, 1)
    
    total_points = sum(p.points or 0 for p in performances)
    total_bids = sum(1 for p in performances if p.bid)
    avg_points = round(total_points / actual_participants, 2) if actual_participants > 0 else 0
    bid_rate = round((total_bids / actual_participants * 100) if actual_participants > 0 else 0, 1)
    
    # Stage breakdown analysis
    stage_names = {0: 'No Advancement', 1: 'Double Octas', 2: 'Octas', 3: 'Quarters', 4: 'Semis', 5: 'Finals'}
    stage_distribution = Counter(p.stage for p in performances if p.stage is not None)
    stage_breakdown = [{'stage': stage_names.get(stage, f'Stage {stage}'), 'count': count} 
                      for stage, count in stage_distribution.items()]
    stage_breakdown.sort(key=lambda x: list(stage_names.keys()).index(
        next((k for k, v in stage_names.items() if v == x['stage']), 0)
    ))
    
    # Performance distribution by points
    points_distribution = []
    if performances:
        points_list = [p.points or 0 for p in performances]
        points_distribution = [
            {'range': '0-20', 'count': len([p for p in points_list if 0 <= p <= 20])},
            {'range': '21-40', 'count': len([p for p in points_list if 21 <= p <= 40])},
            {'range': '41-60', 'count': len([p for p in points_list if 41 <= p <= 60])},
            {'range': '61-80', 'count': len([p for p in points_list if 61 <= p <= 80])},
            {'range': '81+', 'count': len([p for p in points_list if p > 80])}
        ]
    
    # Event breakdown
    event_breakdown = {}
    event_signups = defaultdict(list)
    for signup in signups:
        if signup.is_going and signup.event:
            event_signups[signup.event.event_name].append(signup)
    
    for event_name, event_signups_list in event_signups.items():
        event_performances = [p for p in performances if any(
            s.user_id == p.user_id for s in event_signups_list
        )]
        
        if event_performances:
            event_points = sum(p.points or 0 for p in event_performances)
            event_bids = sum(1 for p in event_performances if p.bid)
            event_breakdown[event_name] = {
                'participants': len(event_performances),
                'total_points': event_points,
                'avg_points': round(event_points / len(event_performances), 2),
                'bids': event_bids,
                'bid_rate': round((event_bids / len(event_performances) * 100), 1)
            }
    
    # Top performers with comprehensive stats
    top_performers = []
    for p in performances:
        user = p.user
        user_signups = [s for s in signups if s.user_id == user.id and s.is_going]
        user_events = [s.event.event_name for s in user_signups if s.event]
        
        total_points = (user.tournament_points or 0) + (user.effort_points or 0)
        weighted_points = (user.tournament_points or 0) * tournament_weight + (user.effort_points or 0) * effort_weight
        
        top_performers.append({
            'user': user,
            'performance': p,
            'total_points': total_points,
            'tournament_points': user.tournament_points or 0,
            'weighted_points': weighted_points,
            'events': user_events,
            'rank': p.rank,
            'stage': stage_names.get(p.stage, 'Unknown') if p.stage is not None else 'Unknown'
        })

    # Sort by performance points first, then by weighted points
    top_performers = sorted(top_performers, key=lambda x: (x['performance'].points or 0, x['weighted_points']), reverse=True)
    
    # Comparative analysis with other tournaments
    all_tournaments = Tournament.query.filter(Tournament.date < tournament.date).order_by(Tournament.date.desc()).limit(5).all()
    comparative_data = []
    
    for other_tournament in all_tournaments:
        other_performances = Tournament_Performance.query.filter_by(tournament_id=other_tournament.id).all()
        if other_performances:
            other_total_points = sum(p.points or 0 for p in other_performances)
            other_avg_points = other_total_points / len(other_performances)
            other_total_bids = sum(1 for p in other_performances if p.bid)
            other_bid_rate = (other_total_bids / len(other_performances) * 100) if other_performances else 0
            
            comparative_data.append({
                'tournament': other_tournament,
                'avg_points': round(other_avg_points, 2),
                'bid_rate': round(other_bid_rate, 1),
                'participants': len(other_performances)
            })
    
    # Judge information
    judge_info = []
    for judge_entry in judges:
        if judge_entry.judge:
            judge_info.append({
                'name': f"{judge_entry.judge.first_name} {judge_entry.judge.last_name}",
                'type': 'Judge',
                'event': judge_entry.event.event_name if judge_entry.event else 'General'
            })
        if judge_entry.child:
            judge_info.append({
                'name': f"{judge_entry.child.first_name} {judge_entry.child.last_name}",
                'type': 'Competitor (judged)',
                'event': judge_entry.event.event_name if judge_entry.event else 'General'
            })

    return render_template('metrics/tournament_detail.html', 
                         tournament=tournament,
                         stats={
                             'total_signups': total_signups,
                             'actual_participants': actual_participants,
                             'participation_rate': participation_rate,
                             'total_points': total_points,
                             'avg_points': avg_points,
                             'total_bids': total_bids,
                             'bid_rate': bid_rate
                         },
                         top_performers=top_performers,
                         stage_breakdown=stage_breakdown,
                         points_distribution=points_distribution,
                         event_breakdown=event_breakdown,
                         comparative_data=comparative_data,
                         judge_info=judge_info)

@metrics_bp.route('/events')
def events_overview():
    user_id = session.get('user_id')
    if not user_id:
        flash("Log in first!")
        return redirect(url_for('auth.login'))
    user = User.query.filter_by(id=user_id).first()
    if not user or user.role < 2:
        flash("Restricted Access!")
        return redirect(url_for('profile.index', user_id=user_id))

    page = request.args.get('page', 1, type=int)
    per_page = 15
    sort = request.args.get('sort', 'weighted_points')
    direction = request.args.get('direction', 'desc')
    
    tournament_weight, effort_weight = get_point_weights()

    # Fetch all events and calculate comprehensive analytics
    all_events = Event.query.all()
    event_analytics = []
    
    for event in all_events:
        # Get active participants
        user_events = User_Event.query.filter_by(event_id=event.id, active=True).all()
        participants = [ue.user for ue in user_events]
        
        if not participants:
            continue
        
        # Tournament performance statistics
        tournament_points = [u.tournament_points or 0 for u in participants]
        effort_points = [u.effort_points or 0 for u in participants]
        
        total_tournament_points = sum(tournament_points)
        total_effort_points = sum(effort_points)
        total_points = total_tournament_points + total_effort_points
        weighted_points = total_tournament_points * tournament_weight + total_effort_points * effort_weight
        
        # Effort scores analysis
        effort_scores = Effort_Score.query.filter_by(event_id=event.id).all()
        thirty_days_ago_est = datetime.now(EST) - timedelta(days=30)
        recent_effort_scores = []
        for es in effort_scores:
            if es.timestamp:
                timestamp = es.timestamp
                if timestamp.tzinfo is None:
                    timestamp = EST.localize(timestamp)
                if timestamp >= thirty_days_ago_est:
                    recent_effort_scores.append(es.score)
        all_effort_scores = [es.score for es in effort_scores]
        
        # Tournament participation analysis
        tournament_participations = []
        recent_tournament_participations = []
        bid_count = 0
        
        for user in participants:
            # All-time tournament performances
            all_performances = Tournament_Performance.query.filter_by(user_id=user.id).all()
            tournament_participations.append(len(all_performances))
            
            # Recent tournament performances (last 6 months)
            six_months_ago = datetime.now(EST) - timedelta(days=180)
            recent_performances = Tournament_Performance.query.join(Tournament).filter(
                Tournament_Performance.user_id == user.id,
                Tournament.date >= six_months_ago
            ).all()
            recent_tournament_participations.append(len(recent_performances))
            
            # Count bids
            bid_count += sum(1 for p in all_performances if p.bid)
        
        # Performance distribution analysis
        performance_distribution = {
            'high_performers': len([p for p in tournament_points if p >= 60]),
            'mid_performers': len([p for p in tournament_points if 20 <= p < 60]),
            'developing_performers': len([p for p in tournament_points if 0 < p < 20]),
            'new_members': len([p for p in tournament_points if p == 0])
        }
        
        # Event type analysis
        event_type_name = {0: 'Speech', 1: 'Lincoln-Douglas', 2: 'Public Forum'}.get(event.event_type, 'Unknown')
        
        event_analytics.append({
            'event': event,
            'event_type_name': event_type_name,
            'participant_count': len(participants),
            'weighted_points': round(weighted_points, 2),
            'total_points': total_points,
            'total_tournament_points': total_tournament_points,
            'total_effort_points': total_effort_points,
            'avg_tournament_points': round(sum(tournament_points) / len(tournament_points), 2) if tournament_points else 0,
            'avg_effort_points': round(sum(effort_points) / len(effort_points), 2) if effort_points else 0,
            'total_effort_scores': len(effort_scores),
            'recent_effort_scores': len(recent_effort_scores),
            'avg_effort_score': round(sum(all_effort_scores) / len(all_effort_scores), 2) if all_effort_scores else 0,
            'avg_recent_effort': round(sum(recent_effort_scores) / len(recent_effort_scores), 2) if recent_effort_scores else 0,
            'avg_tournament_participation': round(sum(tournament_participations) / len(tournament_participations), 2) if tournament_participations else 0,
            'avg_recent_participation': round(sum(recent_tournament_participations) / len(recent_tournament_participations), 2) if recent_tournament_participations else 0,
            'total_bids': bid_count,
            'bid_rate': round((bid_count / sum(tournament_participations) * 100) if sum(tournament_participations) > 0 else 0, 1),
            'performance_distribution': performance_distribution,
            'top_performers': sorted(participants, key=lambda u: (u.tournament_points or 0) + (u.effort_points or 0), reverse=True)[:3],
            'engagement_score': round((len(recent_effort_scores) / len(participants) * 10) if participants else 0, 1)  # Effort scores per person in last 30 days * 10
        })
    
    # Sort events based on selected criteria
    sort_key_map = {
        'name': lambda e: e['event'].event_name.lower(),
        'weighted_points': lambda e: e['weighted_points'],
        'total_points': lambda e: e['total_points'],
        'effort_points': lambda e: e['total_effort_points'],
        'tournament_points': lambda e: e['total_tournament_points'],
        'participant_count': lambda e: e['participant_count'],
        'avg_tournament_participation': lambda e: e['avg_tournament_participation'],
        'bid_rate': lambda e: e['bid_rate'],
        'engagement_score': lambda e: e['engagement_score']
    }
    
    if sort in sort_key_map:
        sorted_events = sorted(event_analytics, key=sort_key_map[sort], reverse=direction=='desc')
    else:
        sorted_events = sorted(event_analytics, key=lambda e: e['weighted_points'], reverse=True)
    
    # Manual Pagination
    start = (page - 1) * per_page
    end = start + per_page
    paginated_events = sorted_events[start:end]

    class Pagination:
        def __init__(self, items, page, per_page, total):
            self.items = items
            self.page = page
            self.per_page = per_page
            self.total = total
            self.pages = int(ceil(total / per_page))
            self.has_prev = page > 1
            self.has_next = page < self.pages
            self.prev_num = page - 1
            self.next_num = page + 1
            
    events_pagination = Pagination(paginated_events, page, per_page, len(event_analytics))

    # Chart data for top events
    chart_events = sorted_events[:10]  # Top 10 events
    chart_labels = [e['event'].event_name for e in chart_events]
    chart_weighted_points = [e['weighted_points'] for e in chart_events]
    chart_participants = [e['participant_count'] for e in chart_events]
    chart_engagement = [e['engagement_score'] for e in chart_events]

    return render_template('metrics/events_overview.html', 
                         events=events_pagination, 
                         sort=sort, 
                         direction=direction,
                         chart_labels=json.dumps(chart_labels),
                         chart_weighted_points=json.dumps(chart_weighted_points),
                         chart_participants=json.dumps(chart_participants),
                         chart_engagement=json.dumps(chart_engagement),
                         next_direction=lambda col: next_direction(col, sort, direction))

@metrics_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()
    if not user or user.role < 2:
        flash("Restricted Access!")
        return redirect(url_for('profile.index', user_id=user_id))

    settings = MetricsSettings.query.first()
    if not settings:
        settings = MetricsSettings()
        db.session.add(settings)
        db.session.commit()

    if request.method == 'POST':
        tournament_weight = float(request.form.get('tournament_weight'))
        effort_weight = float(request.form.get('effort_weight'))
        
        # Round to 2 decimal places to avoid floating point issues
        if round(tournament_weight + effort_weight, 2) != 1.0:
            flash("Weights must sum to 1.0", "danger")
        else:
            settings.tournament_weight = tournament_weight
            settings.effort_weight = effort_weight
            db.session.commit()
            flash("Settings updated successfully!", "success")
        return redirect(url_for('metrics.settings'))

    return render_template('metrics/metrics_settings.html', settings=settings)

@metrics_bp.route('/download_events')
def download_events():
    user_id = session.get('user_id')
    if not user_id:
        flash("Log in first!")
        return redirect(url_for('auth.login'))
    user = User.query.filter_by(id=user_id).first()
    if not user or user.role < 2:
        flash("Restricted Access!")
        return redirect(url_for('profile.index', user_id=user_id))

    sort = request.args.get('sort', 'weighted_points')
    direction = request.args.get('direction', 'desc')
    
    tournament_weight, effort_weight = get_point_weights()
    
    # Fetch all events and calculate their points
    all_events = Event.query.all()
    events_data = []
    
    for event in all_events:
        users = [ue.user for ue in event.user_event]
        if not users:
            events_data.append({
                'event_name': event.event_name,
                'weighted_points': 0,
                'total_points': 0,
                'effort_points': 0,
                'tournament_points': 0
            })
            continue
            
        total_tournament_points = sum(u.tournament_points or 0 for u in users)
        total_effort_points = sum(u.effort_points or 0 for u in users)
        total_points = total_tournament_points + total_effort_points
        weighted_points = total_tournament_points * tournament_weight + total_effort_points * effort_weight
        
        events_data.append({
            'event_name': event.event_name,
            'weighted_points': weighted_points,
            'total_points': total_points,
            'effort_points': total_effort_points,
            'tournament_points': total_tournament_points
        })

    # Sort data
    sort_key_map = {
        'name': lambda e: e['event_name'].lower(),
        'weighted_points': lambda e: e['weighted_points'],
        'total_points': lambda e: e['total_points'],
        'effort_points': lambda e: e['effort_points'],
        'tournament_points': lambda e: e['tournament_points']
    }
    
    if sort in sort_key_map:
        events_data.sort(key=sort_key_map[sort], reverse=direction=='desc')

    # Generate CSV
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Event Name', 'Weighted Points', 'Total Points', 'Effort Points', 'Tournament Points'])
    for event_data in events_data:
        cw.writerow([
            event_data['event_name'], 
            event_data['weighted_points'], 
            event_data['total_points'], 
            event_data['effort_points'], 
            event_data['tournament_points']
        ])
    
    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=events_overview.csv"})

@metrics_bp.route('/download_tournaments')
def download_tournaments():
    user_id = session.get('user_id')
    if not user_id:
        flash("Log in first!")
        return redirect(url_for('auth.login'))
    user = User.query.filter_by(id=user_id).first()
    if not user or user.role < 2:
        flash("Restricted Access!")
        return redirect(url_for('profile.index', user_id=user_id))

    sort = request.args.get('sort', 'name')
    direction = request.args.get('direction', 'asc')
    
    # Fetch all tournaments and calculate their points/bids
    tournaments = Tournament.query.all()
    tournaments_data = []
    
    for tournament in tournaments:
        total_points = sum(p.points or 0 for p in tournament.tournament_performances)
        total_bids = sum(p.user.bids or 0 for p in tournament.tournament_performances)
        tournaments_data.append({
            'name': tournament.name,
            'total_points': total_points,
            'total_bids': total_bids
        })

    # Sort data
    sort_key_map = {
        'name': lambda t: t['name'].lower(),
        'total_points': lambda t: t['total_points'],
        'total_bids': lambda t: t['total_bids']
    }
    
    if sort in sort_key_map:
        tournaments_data.sort(key=sort_key_map[sort], reverse=direction=='desc')

    # Generate CSV
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Name', 'Total Points', 'Total Bids'])
    for tournament_data in tournaments_data:
        cw.writerow([
            tournament_data['name'], 
            tournament_data['total_points'], 
            tournament_data['total_bids']
        ])
    
    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=tournaments_overview.csv"})

# USER-FACING METRICS ROUTES
# Routes accessible to all logged-in users to view their own metrics

@metrics_bp.route('/my_metrics')
def my_metrics():
    """User's personal metrics dashboard"""
    user_id = session.get('user_id')
    if not user_id:
        flash("Log in first!")
        return redirect(url_for('auth.login'))
    
    user = User.query.get_or_404(user_id)
    tournament_weight, effort_weight = get_point_weights()
    
    # Get user's tournament performances
    performances = Tournament_Performance.query.filter_by(user_id=user_id)\
        .join(Tournament).order_by(Tournament.date.desc()).all()
    
    # Calculate basic stats
    total_tournaments = len(performances)
    total_tournament_points = user.tournament_points or 0
    total_effort_points = user.effort_points or 0
    total_points = total_tournament_points + total_effort_points
    weighted_points = total_tournament_points * tournament_weight + total_effort_points * effort_weight
    total_bids = sum(1 for p in performances if p.bid)
    
    # Performance statistics
    if performances:
        points_list = [p.points or 0 for p in performances]
        avg_points = sum(points_list) / len(points_list)
        best_performance = max(points_list)
        recent_avg = sum(points_list[:5]) / min(5, len(points_list))  # Last 5 tournaments
        bid_rate = (total_bids / total_tournaments * 100) if total_tournaments > 0 else 0
    else:
        avg_points = best_performance = recent_avg = bid_rate = 0
    
    # Calculate user ranking (without revealing other users' data)
    # Count users with higher weighted points
    users_with_tournament_points = db.session.query(User.id).join(Tournament_Performance).distinct().subquery()
    users_with_effort_points = db.session.query(User.id).join(Effort_Score, User.id == Effort_Score.user_id).distinct().subquery()
    
    all_active_users = User.query.filter(
        or_(
            User.id.in_(db.session.query(users_with_tournament_points.c.id)),
            User.id.in_(db.session.query(users_with_effort_points.c.id))
        )
    ).all()
    
    user_rank = 1
    total_active_users = len(all_active_users)
    for other_user in all_active_users:
        other_weighted = (other_user.tournament_points or 0) * tournament_weight + (other_user.effort_points or 0) * effort_weight
        if other_weighted > weighted_points:
            user_rank += 1
    
    # Recent tournaments (last 6 months)
    six_months_ago = datetime.now(EST) - timedelta(days=180)
    recent_performances = []
    for p in performances:
        tournament_date = p.tournament.date
        if tournament_date.tzinfo is None:
            tournament_date = EST.localize(tournament_date)
        if tournament_date >= six_months_ago:
            recent_performances.append(p)
    
    # Event breakdown
    from mason_snd.models.events import User_Event
    user_events = User_Event.query.filter_by(user_id=user_id, active=True).all()
    event_stats = []
    
    for ue in user_events:
        event = ue.event
        event_performances = [p for p in performances if any(
            signup.event_id == event.id for signup in Tournament_Signups.query.filter_by(
                user_id=user_id, tournament_id=p.tournament_id, is_going=True
            ).all()
        )]
        
        if event_performances:
            event_points = [p.points or 0 for p in event_performances]
            event_bids = sum(1 for p in event_performances if p.bid)
            event_stats.append({
                'event': event,
                'tournaments': len(event_performances),
                'avg_points': sum(event_points) / len(event_points),
                'total_points': sum(event_points),
                'bids': event_bids,
                'bid_rate': (event_bids / len(event_performances) * 100) if event_performances else 0
            })
    
    event_stats.sort(key=lambda x: x['avg_points'], reverse=True)
    
    stats = {
        'total_tournaments': total_tournaments,
        'total_points': total_points,
        'tournament_points': total_tournament_points,
        'effort_points': total_effort_points,
        'weighted_points': round(weighted_points, 2),
        'total_bids': total_bids,
        'avg_points': round(avg_points, 2),
        'best_performance': best_performance,
        'recent_avg': round(recent_avg, 2),
        'bid_rate': round(bid_rate, 1),
        'rank': user_rank,
        'total_active_users': total_active_users,
        'recent_tournaments': len(recent_performances)
    }
    
    return render_template('metrics/user_dashboard.html',
                         user=user,
                         stats=stats,
                         performances=performances[:10],  # Show last 10 tournaments
                         event_stats=event_stats,
                         settings=MetricsSettings.query.first())

@metrics_bp.route('/my_performance_trends')
def my_performance_trends():
    """User's performance trends over time"""
    user_id = session.get('user_id')
    if not user_id:
        flash("Log in first!")
        return redirect(url_for('auth.login'))
    
    user = User.query.get_or_404(user_id)
    
    # Get user's tournament performances in chronological order
    performances = Tournament_Performance.query.filter_by(user_id=user_id)\
        .join(Tournament).order_by(Tournament.date).all()
    
    # Prepare data for charts
    chart_data = []
    cumulative_points = 0
    
    for p in performances:
        points = p.points or 0
        cumulative_points += points
        tournament_date = p.tournament.date
        if tournament_date.tzinfo is None:
            tournament_date = EST.localize(tournament_date)
        chart_data.append({
            'tournament': p.tournament.name,
            'date': tournament_date.strftime('%Y-%m-%d'),
            'points': points,
            'cumulative_points': cumulative_points,
            'bid': p.bid,
            'rank': p.rank,
            'stage': p.stage
        })
    
    # Weekly performance analysis
    weekly_data = {}
    for p in performances:
        # Get week start date and handle timezone
        tournament_date = p.tournament.date
        if tournament_date.tzinfo is None:
            tournament_date = EST.localize(tournament_date)
        week_start = tournament_date - timedelta(days=tournament_date.weekday())
        week_key = week_start.strftime('%Y-%m-%d')
        
        if week_key not in weekly_data:
            weekly_data[week_key] = {'tournaments': 0, 'total_points': 0, 'bids': 0}
        
        weekly_data[week_key]['tournaments'] += 1
        weekly_data[week_key]['total_points'] += p.points or 0
        weekly_data[week_key]['bids'] += 1 if p.bid else 0
    
    # Calculate moving averages (5-tournament rolling average)
    moving_averages = []
    for i in range(len(chart_data)):
        start_idx = max(0, i - 4)
        avg_points = sum(d['points'] for d in chart_data[start_idx:i+1]) / (i - start_idx + 1)
        moving_averages.append(round(avg_points, 2))
    
    # Performance trend analysis
    trend_analysis = {}
    if len(chart_data) >= 3:
        recent_tournaments = chart_data[-3:]
        older_tournaments = chart_data[:-3] if len(chart_data) > 3 else chart_data[:1]
        
        recent_avg = sum(t['points'] for t in recent_tournaments) / len(recent_tournaments)
        older_avg = sum(t['points'] for t in older_tournaments) / len(older_tournaments)
        
        if recent_avg > older_avg * 1.1:
            trend_analysis['direction'] = 'improving'
            trend_analysis['percentage'] = round(((recent_avg - older_avg) / older_avg) * 100, 1)
        elif recent_avg < older_avg * 0.9:
            trend_analysis['direction'] = 'declining'  
            trend_analysis['percentage'] = round(((older_avg - recent_avg) / older_avg) * 100, 1)
        else:
            trend_analysis['direction'] = 'stable'
            trend_analysis['percentage'] = 0
    
    # Chart data for JavaScript
    chart_labels = [d['tournament'][:20] + '...' if len(d['tournament']) > 20 else d['tournament'] for d in chart_data]
    chart_points = [d['points'] for d in chart_data]
    chart_cumulative = [d['cumulative_points'] for d in chart_data]
    
    return render_template('metrics/user_trends.html',
                         user=user,
                         chart_data=chart_data,
                         weekly_data=sorted(weekly_data.items()),
                         trend_analysis=trend_analysis,
                         moving_averages=moving_averages,
                         chart_labels=json.dumps(chart_labels),
                         chart_points=json.dumps(chart_points),
                         chart_cumulative=json.dumps(chart_cumulative),
                         chart_moving_avg=json.dumps(moving_averages))

@metrics_bp.route('/my_ranking')
def my_ranking():
    """User's ranking information (without revealing others' data)"""
    user_id = session.get('user_id')
    if not user_id:
        flash("Log in first!")
        return redirect(url_for('auth.login'))
    
    user = User.query.get_or_404(user_id)
    tournament_weight, effort_weight = get_point_weights()
    
    # Calculate user's weighted score
    user_weighted_score = (user.tournament_points or 0) * tournament_weight + (user.effort_points or 0) * effort_weight
    
    # Get all users with some activity for ranking
    users_with_tournament_points = db.session.query(User.id).join(Tournament_Performance).distinct().subquery()
    users_with_effort_points = db.session.query(User.id).join(Effort_Score, User.id == Effort_Score.user_id).distinct().subquery()
    
    all_active_users = User.query.filter(
        or_(
            User.id.in_(db.session.query(users_with_tournament_points.c.id)),
            User.id.in_(db.session.query(users_with_effort_points.c.id))
        )
    ).all()
    
    # Calculate ranking
    user_rank = 1
    total_active_users = len(all_active_users)
    users_above_me = 0
    users_below_me = 0
    
    for other_user in all_active_users:
        other_weighted = (other_user.tournament_points or 0) * tournament_weight + (other_user.effort_points or 0) * effort_weight
        if other_weighted > user_weighted_score:
            user_rank += 1
            users_above_me += 1
        elif other_weighted < user_weighted_score:
            users_below_me += 1
    
    # Calculate percentile
    percentile = round(((total_active_users - user_rank + 1) / total_active_users) * 100, 1) if total_active_users > 0 else 0
    
    # Event-specific rankings
    from mason_snd.models.events import User_Event
    user_events = User_Event.query.filter_by(user_id=user_id, active=True).all()
    event_rankings = []
    
    for ue in user_events:
        event = ue.event
        # Get all active users in this event
        event_user_ids = [ue.user_id for ue in User_Event.query.filter_by(event_id=event.id, active=True).all()]
        event_users = User.query.filter(User.id.in_(event_user_ids)).all()
        
        if len(event_users) > 1:  # Only show ranking if there are other users in the event
            # Calculate user's rank in this event
            event_rank = 1
            for other_user in event_users:
                other_weighted = (other_user.tournament_points or 0) * tournament_weight + (other_user.effort_points or 0) * effort_weight
                if other_weighted > user_weighted_score:
                    event_rank += 1
            
            event_percentile = round(((len(event_users) - event_rank + 1) / len(event_users)) * 100, 1)
            
            event_rankings.append({
                'event': event,
                'rank': event_rank,
                'total_in_event': len(event_users),
                'percentile': event_percentile
            })
    
    # Recent performance comparison (last 3 months vs previous 3 months)
    three_months_ago = datetime.now(EST) - timedelta(days=90)
    six_months_ago = datetime.now(EST) - timedelta(days=180)
    
    recent_performances = []
    older_performances = []
    
    for p in Tournament_Performance.query.filter_by(user_id=user_id).join(Tournament).all():
        tournament_date = p.tournament.date
        if tournament_date.tzinfo is None:
            tournament_date = EST.localize(tournament_date)
        
        if tournament_date >= three_months_ago:
            recent_performances.append(p)
        elif tournament_date >= six_months_ago:
            older_performances.append(p)
    
    recent_avg = sum(p.points or 0 for p in recent_performances) / len(recent_performances) if recent_performances else 0
    older_avg = sum(p.points or 0 for p in older_performances) / len(older_performances) if older_performances else 0
    
    performance_change = {
        'recent_avg': round(recent_avg, 2),
        'older_avg': round(older_avg, 2),
        'change': round(recent_avg - older_avg, 2) if older_avg > 0 else 0,
        'change_percent': round(((recent_avg - older_avg) / older_avg) * 100, 1) if older_avg > 0 else 0
    }
    
    ranking_data = {
        'rank': user_rank,
        'total_active_users': total_active_users,
        'percentile': percentile,
        'users_above_me': users_above_me,
        'users_below_me': users_below_me,
        'weighted_score': round(user_weighted_score, 2),
        'performance_change': performance_change
    }
    
    return render_template('metrics/user_ranking.html',
                         user=user,
                         ranking_data=ranking_data,
                         event_rankings=event_rankings,
                         settings=MetricsSettings.query.first())

@metrics_bp.route('/download_user_metrics_for_tournament/<int:tournament_id>')
def download_user_metrics_for_tournament(tournament_id):
    user_id = session.get('user_id')
    if not user_id:
        flash("Log in first!")
        return redirect(url_for('auth.login'))
    user = User.query.filter_by(id=user_id).first()
    if not user or user.role < 2:
        flash("Restricted Access!")
        return redirect(url_for('profile.index', user_id=user_id))

    tournament = Tournament.query.get_or_404(tournament_id)
    tournament_weight, effort_weight = get_point_weights()
    
    performances = Tournament_Performance.query.filter_by(tournament_id=tournament_id).all()
    
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['Name', 'Total Points', 'Tournament Points', 'Weighted Points', 'Tournament Performance Points', 'Bid'])
    
    for p in performances:
        user = p.user
        total_points = (user.tournament_points or 0) + (user.effort_points or 0)
        weighted_points = (user.tournament_points or 0) * tournament_weight + (user.effort_points or 0) * effort_weight
        writer.writerow([
            f"{user.first_name} {user.last_name}", 
            total_points, 
            user.tournament_points or 0, 
            weighted_points, 
            p.points or 0,
            "Yes" if p.bid else "No"
        ])
        
    output = si.getvalue()
    return Response(
        output,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=tournament_{tournament.name}_user_metrics.csv'}
    )
