import csv
from io import StringIO
from math import ceil

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, Response

from mason_snd.extensions import db
from mason_snd.models.auth import User
from mason_snd.models.admin import User_Requirements, Requirements
from mason_snd.models.tournaments import Tournament, Tournament_Performance, Tournament_Judges, Tournament_Signups
from mason_snd.models.events import Event, User_Event, Effort_Score
from mason_snd.models.metrics import MetricsSettings
from mason_snd.models.rosters import Roster_Tournament, Roster_Partner, Roster_Drops
from sqlalchemy import asc, desc, func

try:
    import pandas as pd
except ImportError:
    pd = None


rosters_bp = Blueprint('rosters', __name__, template_folder='templates')

# Index: List tournaments and access roster views
@rosters_bp.route('/')
def index():
    tournaments = Tournament.query.order_by(Tournament.date.desc()).all()
    return render_template('rosters/index.html', tournaments=tournaments)

# Judge View
@rosters_bp.route('/<int:tournament_id>/judge')
def judge_view(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)
    judges = []
    judge_entries = Tournament_Judges.query.filter_by(tournament_id=tournament_id).all()
    for entry in judge_entries:
        judge = entry.judge
        child = entry.child
        event = entry.event
        # Members brought by judge
        members = Tournament_Signups.query.filter_by(judge_id=judge.id, tournament_id=tournament_id, is_going=True).all()
        member_list = []
        for m in members:
            user = m.user
            is_drop = Roster_Drops.query.filter_by(user_id=user.id).first() is not None
            member_list.append({
                'name': f"{user.first_name} {user.last_name}",
                'is_drop': is_drop
            })
        judges.append({
            'judge_name': f"{judge.first_name} {judge.last_name}",
            'child_name': f"{child.first_name} {child.last_name}" if child else '',
            'members': member_list,
            'event_name': event.event_name if event else '',
            'info': f"Can bring: {judge.judging_reqs}"
        })
    return render_template('rosters/judge_view.html', tournament=tournament, judges=judges)

# Event View
@rosters_bp.route('/<int:tournament_id>/event')
def event_view(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)
    events = Event.query.all()
    event_tables = []
    for event in events:
        rows = []
        # Get all signups for this event in this tournament
        signups = Tournament_Signups.query.filter_by(tournament_id=tournament_id, is_going=True).all()
        for signup in signups:
            user = signup.user
            judge = signup.judge
            child = None
            judge_obj = Tournament_Judges.query.filter_by(judge_id=judge.id, tournament_id=tournament_id, event_id=event.id).first() if judge else None
            if judge_obj:
                child = judge_obj.child
            perf = Tournament_Performance.query.filter_by(user_id=user.id, tournament_id=tournament_id).first()
            rank = perf.rank if perf else ''
            is_child = judge_obj and child and user.id == child.id
            is_drop = Roster_Drops.query.filter_by(user_id=user.id).first() is not None
            rows.append({
                'rank': rank,
                'member_name': f"{user.first_name} {user.last_name}",
                'judge_name': f"{judge.first_name} {judge.last_name}" if judge else '',
                'child_name': f"{child.first_name} {child.last_name}" if child else '',
                'info': '',
                'is_child': is_child,
                'is_drop': is_drop
            })
        event_tables.append({
            'event_name': event.event_name,
            'rows': rows
        })
    return render_template('rosters/event_view.html', tournament=tournament, events=event_tables)

# Rank View
@rosters_bp.route('/<int:tournament_id>/rank')
def rank_view(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)
    signups = Tournament_Signups.query.filter_by(tournament_id=tournament_id, is_going=True).all()
    rows = []
    for signup in signups:
        user = signup.user
        judge = signup.judge
        event = Event.query.filter(Event.id.in_([e.event_id for e in User_Event.query.filter_by(user_id=user.id).all()])).first()
        child = None
        judge_obj = Tournament_Judges.query.filter_by(judge_id=judge.id, tournament_id=tournament_id).first() if judge else None
        if judge_obj:
            child = judge_obj.child
        perf = Tournament_Performance.query.filter_by(user_id=user.id, tournament_id=tournament_id).first()
        rank = perf.rank if perf else ''
        is_child = judge_obj and child and user.id == child.id
        is_drop = Roster_Drops.query.filter_by(user_id=user.id).first() is not None
        rows.append({
            'rank': rank,
            'member_name': f"{user.first_name} {user.last_name}",
            'event_name': event.event_name if event else '',
            'judge_name': f"{judge.first_name} {judge.last_name}" if judge else '',
            'child_name': f"{child.first_name} {child.last_name}" if child else '',
            'info': '',
            'is_child': is_child,
            'is_drop': is_drop
        })
    return render_template('rosters/rank_view.html', tournament=tournament, rows=rows)

# Download Roster
@rosters_bp.route('/<int:tournament_id>/download')
def download_roster(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)
    signups = Tournament_Signups.query.filter_by(tournament_id=tournament_id, is_going=True).all()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Rank', 'Member', 'Event', 'Judge', 'Child', 'Drop'])
    for signup in signups:
        user = signup.user
        judge = signup.judge
        event = Event.query.filter(Event.id.in_([e.event_id for e in User_Event.query.filter_by(user_id=user.id).all()])).first()
        child = None
        judge_obj = Tournament_Judges.query.filter_by(judge_id=judge.id, tournament_id=tournament_id).first() if judge else None
        if judge_obj:
            child = judge_obj.child
        perf = Tournament_Performance.query.filter_by(user_id=user.id, tournament_id=tournament_id).first()
        rank = perf.rank if perf else ''
        is_drop = Roster_Drops.query.filter_by(user_id=user.id).first() is not None
        writer.writerow([
            rank,
            f"{user.first_name} {user.last_name}",
            event.event_name if event else '',
            f"{judge.first_name} {judge.last_name}" if judge else '',
            f"{child.first_name} {child.last_name}" if child else '',
            'Drop' if is_drop else ''
        ])
    output.seek(0)
    return Response(output, mimetype="text/csv", headers={"Content-Disposition":f"attachment;filename={tournament.name}_roster.csv"})

# Upload Roster
@rosters_bp.route('/upload', methods=['GET', 'POST'])
def upload_roster():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file:
            flash('No file selected', 'danger')
            return redirect(url_for('rosters.upload_roster'))
        filename = file.filename
        if not filename.endswith('.xlsx'):
            flash('Invalid file type. Please upload an .xlsx file.', 'danger')
            return redirect(url_for('rosters.upload_roster'))
        df = pd.read_excel(file)
        # Expect columns: name, event, tournament, judge, child, drop
        for _, row in df.iterrows():
            # Find user, event, tournament, judge, child by name
            user = User.query.filter_by(first_name=row['Member'].split()[0], last_name=row['Member'].split()[-1]).first()
            event = Event.query.filter_by(event_name=row['Event']).first()
            tournament = Tournament.query.filter_by(name=row['Tournament']).first()
            judge = User.query.filter_by(first_name=row['Judge'].split()[0], last_name=row['Judge'].split()[-1]).first() if pd.notna(row['Judge']) else None
            child = User.query.filter_by(first_name=row['Child'].split()[0], last_name=row['Child'].split()[-1]).first() if pd.notna(row['Child']) else None
            if user and event and tournament:
                # Save to Roster_Tournament
                rt = Roster_Tournament()
                rt.user_id = user.id
                rt.tournament_id = tournament.id
                db.session.add(rt)
                # Save drop if needed
                if 'Drop' in row and row['Drop'] == 'Drop':
                    rd = Roster_Drops()
                    rd.user_id = user.id
                    db.session.add(rd)
        db.session.commit()
        flash('Roster uploaded successfully!', 'success')
        return redirect(url_for('rosters.index'))
    return render_template('rosters/upload.html')