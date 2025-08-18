import csv
from io import StringIO
from math import ceil

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, Response

from mason_snd.extensions import db
from mason_snd.models.auth import User
from mason_snd.models.admin import User_Requirements, Requirements
from mason_snd.models.tournaments import Tournament, Tournament_Performance
from mason_snd.models.events import Event, User_Event, Effort_Score
from mason_snd.models.metrics import MetricsSettings
from sqlalchemy import asc, desc, func

metrics_bp = Blueprint('metrics', __name__, template_folder='templates')

def get_point_weights():
    """Helper function to get tournament and effort weights from settings"""
    settings = MetricsSettings.query.first()
    if not settings:
        settings = MetricsSettings()
        db.session.add(settings)
        db.session.commit()
    return settings.tournament_weight, settings.effort_weight

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

@metrics_bp.route('/user_metrics')
def index():
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
    # Write header row
    writer.writerow([
        'Name', 'Bids', 'Points (Tournaments)', 'Points (Effort)', 'Total Points', f'Weighted Points ({int(tournament_weight*100)}% Tournament, {int(effort_weight*100)}% Effort)'
    ])
    for user in users_sorted:
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

@metrics_bp.route('/user/<int:user_id>')
def user_detail(user_id):
    user_id = session.get('user_id')
    if not user_id:
        flash("Log in first!")
        return redirect(url_for('auth.login'))
    user = User.query.filter_by(id=user_id).first()
    if not user or user.role < 2:
        flash("Restricted Access!")
        return redirect(url_for('profile.index', user_id=user_id))

    performances = Tournament_Performance.query.filter_by(user_id=user_id).join(Tournament).order_by(Tournament.date).all()
    
    tournament_weight, effort_weight = get_point_weights()
    
    total_points = (user.tournament_points or 0) + (user.effort_points or 0)
    weighted_points = (user.tournament_points or 0) * tournament_weight + (user.effort_points or 0) * effort_weight

    # Prepare chart data
    labels = [p.tournament.name for p in performances]
    data = [p.points for p in performances]
    
    # Simple prediction - if we have at least 2 data points
    prediction = []
    if len(data) >= 2:
        # Create a list with None for existing data points, and the predicted value at the end
        prediction_data = [None] * len(data)
        prediction_data.append(data[-1] + (data[-1] - data[-2]))
        prediction = prediction_data
        labels.append("Next (Predicted)")

    return render_template('metrics/user_detail.html', 
                         user=user, 
                         performances=performances, 
                         total_points=total_points, 
                         weighted_points=weighted_points, 
                         labels=labels, 
                         data=data, 
                         prediction=prediction)

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
    sort = request.args.get('sort', 'name')
    direction = request.args.get('direction', 'asc')

    # Base query
    tournaments_query = Tournament.query
    
    # Handle sorting
    if sort == 'name':
        order_by = Tournament.name.asc() if direction == 'asc' else Tournament.name.desc()
        tournaments_query = tournaments_query.order_by(order_by)
        tournaments = tournaments_query.paginate(page=page, per_page=per_page, error_out=False)
    else:
        # For computed sorts (total_points, total_bids), we need to fetch all and sort manually
        all_tournaments = Tournament.query.all()
        all_tournament_points = {}
        all_tournament_bids = {}
        
        for t in all_tournaments:
            all_tournament_points[t.id] = sum(p.points or 0 for p in t.tournament_performances)
            all_tournament_bids[t.id] = sum(p.user.bids or 0 for p in t.tournament_performances)
        
        if sort == 'total_points':
            sorted_ids = sorted(all_tournament_points.keys(), key=lambda t_id: all_tournament_points[t_id], reverse=direction=='desc')
        elif sort == 'total_bids':
            sorted_ids = sorted(all_tournament_bids.keys(), key=lambda t_id: all_tournament_bids[t_id], reverse=direction=='desc')
        else:
            sorted_ids = [t.id for t in all_tournaments]
        
        # Manual pagination
        start = (page - 1) * per_page
        end = start + per_page
        paginated_ids = sorted_ids[start:end]
        
        items = Tournament.query.filter(Tournament.id.in_(paginated_ids)).all()
        # Re-order items based on sorted_ids
        items_map = {item.id: item for item in items}
        sorted_items = [items_map[id] for id in paginated_ids if id in items_map]

        # Create pagination object
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
        
        tournaments = Pagination(sorted_items, page, per_page, len(all_tournaments))

    # Calculate tournament points and bids for display
    tournament_points = {}
    tournament_bids = {}
    for t in tournaments.items:
        tournament_points[t.id] = sum(p.points or 0 for p in t.tournament_performances)
        tournament_bids[t.id] = sum(p.user.bids or 0 for p in t.tournament_performances)

    # Chart data
    chart_labels = [t.name for t in tournaments.items]
    chart_data = [tournament_points.get(t.id, 0) for t in tournaments.items]
    
    # Simple prediction for chart
    chart_prediction = []
    if len(chart_data) >= 2:
        prediction_data = [None] * len(chart_data)
        prediction_data.append(chart_data[-1] + (chart_data[-1] - chart_data[-2]))
        chart_prediction = prediction_data
        chart_labels.append("Next (Predicted)")

    return render_template('metrics/tournaments_overview.html', 
                         tournaments=tournaments, 
                         tournament_points=tournament_points, 
                         tournament_bids=tournament_bids, 
                         sort=sort, 
                         direction=direction, 
                         chart_labels=chart_labels, 
                         chart_data=chart_data, 
                         chart_prediction=chart_prediction,
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

    performances = Tournament_Performance.query.filter_by(tournament_id=tournament_id).all()
    
    top_performers = []
    for p in performances:
        user = p.user
        total_points = (user.tournament_points or 0) + (user.effort_points or 0)
        weighted_points = (user.tournament_points or 0) * tournament_weight + (user.effort_points or 0) * effort_weight
        top_performers.append({
            'user': user,
            'total_points': total_points,
            'tournament_points': user.tournament_points or 0,
            'weighted_points': weighted_points
        })

    top_performers = sorted(top_performers, key=lambda x: x['weighted_points'], reverse=True)

    # Calculate average event performance for users who attended this tournament
    # This is a simplified calculation
    user_ids_in_tournament = [p.user_id for p in performances]
    if user_ids_in_tournament:
        event_performance_avg = db.session.query(func.avg(Effort_Score.score)).filter(
            Effort_Score.user_id.in_(user_ids_in_tournament)
        ).scalar() or 0
    else:
        event_performance_avg = 0

    return render_template('metrics/tournament_detail.html', 
                         tournament=tournament, 
                         top_performers=top_performers, 
                         event_performance_avg=round(event_performance_avg, 2))

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

    # Fetch all events and calculate their points
    all_events = Event.query.all()
    event_points = {}
    
    for event in all_events:
        users = [ue.user for ue in event.user_event]
        if not users:
            event_points[event.id] = {
                'weighted_points': 0, 
                'total_points': 0, 
                'effort_points': 0, 
                'tournament_points': 0
            }
            continue
            
        total_tournament_points = sum(u.tournament_points or 0 for u in users)
        total_effort_points = sum(u.effort_points or 0 for u in users)
        total_points = total_tournament_points + total_effort_points
        weighted_points = total_tournament_points * tournament_weight + total_effort_points * effort_weight
        
        event_points[event.id] = {
            'weighted_points': weighted_points,
            'total_points': total_points,
            'effort_points': total_effort_points,
            'tournament_points': total_tournament_points
        }
    
    # Sort events based on selected criteria
    sort_key_map = {
        'name': lambda e: e.event_name.lower(),
        'weighted_points': lambda e: event_points[e.id]['weighted_points'],
        'total_points': lambda e: event_points[e.id]['total_points'],
        'effort_points': lambda e: event_points[e.id]['effort_points'],
        'tournament_points': lambda e: event_points[e.id]['tournament_points']
    }
    
    if sort in sort_key_map:
        sorted_events = sorted(all_events, key=sort_key_map[sort], reverse=direction=='desc')
    else:
        sorted_events = sorted(all_events, key=lambda e: event_points[e.id]['weighted_points'], reverse=True)
    
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
            
    events_pagination = Pagination(paginated_events, page, per_page, len(all_events))

    return render_template('metrics/events_overview.html', 
                         events=events_pagination, 
                         event_points=event_points, 
                         sort=sort, 
                         direction=direction,
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
