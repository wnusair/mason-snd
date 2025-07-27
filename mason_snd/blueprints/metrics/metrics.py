import csv
from io import StringIO

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, Response

from mason_snd.extensions import db
from mason_snd.models.auth import User
from mason_snd.models.admin import User_Requirements, Requirements
from mason_snd.models.tournaments import Tournament_Performance
from sqlalchemy import asc, desc

metrics_bp = Blueprint('metrics', __name__, template_folder='templates')

@metrics_bp.route('/user_metrics')
def index():
    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()
    if not user or user.role < 2:
        flash("Restricted Access!")
        return redirect(url_for('profile.user', user_id=user_id))

    page = request.args.get('page', 1, type=int)
    per_page = 15
    sort = request.args.get('sort', 'default')
    direction = request.args.get('direction', 'default')

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
            key_func = lambda u: (u.tournament_points or 0) * 0.7 + (u.effort_points or 0) * 0.3
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

    return render_template(
        'metrics/user_metrics_overview.html',
        users=users_pagination,
        sort=sort,
        direction=direction
    )

@metrics_bp.route('/user_metrics/download')
def download_user_metrics():
    sort = request.args.get('sort', 'default')
    direction = request.args.get('direction', 'default')
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
            key_func = lambda u: (u.tournament_points or 0) * 0.7 + (u.effort_points or 0) * 0.3
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
        'Name', 'Bids', 'Points (Tournaments)', 'Points (Effort)', 'Total Points', 'Weighted Points (70% Perf, 30% Effort)'
    ])
    for user in users_sorted:
        tournament_points = user.tournament_points or 0
        effort_points = user.effort_points or 0
        total_points = tournament_points + effort_points
        weighted_points = round(tournament_points * 0.7 + effort_points * 0.3, 2)
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