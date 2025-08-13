import csv
from io import StringIO
from math import ceil
import random

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, Response

from mason_snd.extensions import db
from mason_snd.models.auth import User
from mason_snd.models.admin import User_Requirements, Requirements
from mason_snd.models.tournaments import Tournament, Tournament_Performance, Tournament_Judges, Tournament_Signups
from mason_snd.models.events import Event, User_Event, Effort_Score
from mason_snd.models.metrics import MetricsSettings
from mason_snd.models.rosters import Roster_Judge, Roster, Roster_Competitors

from sqlalchemy import asc, desc, func

from datetime import datetime


try:
    import pandas as pd
except ImportError:
    pd = None


rosters_bp = Blueprint('rosters', __name__, template_folder='templates')

@rosters_bp.route('/')
def index():
    tournaments = Tournament.query.all()
    rosters = Roster.query.all()

    upcoming_tournaments = []
    now = datetime.now()
    for tournament in tournaments:
        if tournament.signup_deadline and tournament.signup_deadline > now:
            upcoming_tournaments.append(tournament)

    return render_template('rosters/index.html', upcoming_tournaments=upcoming_tournaments, tournaments=tournaments, rosters=rosters)



# BIG VIEW TOURNAMENT BLOCK!!!!

def get_roster_count(tournament_id):
    judges = Tournament_Judges.query.filter_by(tournament_id=tournament_id, accepted=True).all()

    speech_competitors = 0
    LD_competitors = 0
    PF_competitors = 0

    for judge in judges:
        event_id = judge.event_id

        event = Event.query.filter_by(id=event_id).first()

        if event.event_type == 0:
            speech_competitors += 6
        elif event.event_type == 1:
            LD_competitors += 2
        else:
            PF_competitors += 4

    return speech_competitors, LD_competitors, PF_competitors

# Helper: Get all signups for a tournament, grouped by event
from mason_snd.models.tournaments import Tournament_Signups

def get_signups_by_event(tournament_id):
    signups = Tournament_Signups.query.filter_by(tournament_id=tournament_id).all()
    event_dict = {}
    for signup in signups:
        if signup.event_id not in event_dict:
            event_dict[signup.event_id] = []
        event_dict[signup.event_id].append(signup)
    return event_dict

# Helper: Rank signups in each event by weighted points
def rank_signups(event_dict):
    ranked = {}
    for event_id, signups in event_dict.items():
        # Get weighted points from user, fallback to user.points or 0
        ranked[event_id] = sorted(signups, key=lambda s: getattr(s.user, 'weighted_points', getattr(s.user, 'points', 0)), reverse=True)
    return ranked

# Helper: Select competitors for speech (rotation) and LD/PF (top N with randomness)
def select_competitors_by_event_type(ranked, speech_spots, ld_spots, pf_spots, event_type_map, seed_randomness=True):
    event_view = []
    rank_view = []
    # Speech events: rotation
    speech_event_ids = [eid for eid, etype in event_type_map.items() if etype == 0]
    speech_indices = {eid: 0 for eid in speech_event_ids}
    speech_filled = 0
    while speech_filled < speech_spots and speech_event_ids:
        for eid in speech_event_ids:
            competitors = ranked.get(eid, [])
            if speech_indices[eid] < len(competitors):
                if seed_randomness:
                    mid = len(competitors) // 2
                    idx = min(speech_indices[eid], mid)
                else:
                    idx = speech_indices[eid]
                signup = competitors[idx]
                event_view.append({'user_id': signup.user_id, 'event_id': eid})
                rank_view.append({'user_id': signup.user_id, 'event_id': eid, 'rank': idx+1})
                speech_indices[eid] += 1
                speech_filled += 1
                if speech_filled >= speech_spots:
                    break
        if all(speech_indices[eid] >= len(ranked.get(eid, [])) for eid in speech_event_ids):
            break
    # LD events: take top N with randomness
    ld_event_ids = [eid for eid, etype in event_type_map.items() if etype == 1]
    for eid in ld_event_ids:
        competitors = ranked.get(eid, [])
        for i in range(min(ld_spots, len(competitors))):
            if seed_randomness:
                mid = len(competitors) // 2
                idx = min(i, mid)
            else:
                idx = i
            signup = competitors[idx]
            event_view.append({'user_id': signup.user_id, 'event_id': eid})
            rank_view.append({'user_id': signup.user_id, 'event_id': eid, 'rank': idx+1})
    # PF events: take top N with randomness
    pf_event_ids = [eid for eid, etype in event_type_map.items() if etype == 2]
    for eid in pf_event_ids:
        competitors = ranked.get(eid, [])
        for i in range(min(pf_spots, len(competitors))):
            if seed_randomness:
                mid = len(competitors) // 2
                idx = min(i, mid)
            else:
                idx = i
            signup = competitors[idx]
            event_view.append({'user_id': signup.user_id, 'event_id': eid})
            rank_view.append({'user_id': signup.user_id, 'event_id': eid, 'rank': idx+1})
    return event_view, rank_view

@rosters_bp.route('/view_tournament/<int:tournament_id>')
def view_tournament(tournament_id):
    """
    
    take all judges
    take all accepted judging

    show table of judges (judge name, child, category, number of people brought)
    show table of event, show table of rank
    
    """

    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()

    if not user_id:
        flash("Log In First")
        return redirect(url_for('auth.login'))

    if user.role < 2:
        flash("You are not authorized to access this page")
        return redirect(url_for('main.index'))
    
    speech_competitors, LD_competitors, PF_competitors = get_roster_count(tournament_id)

    event_dict = get_signups_by_event(tournament_id)
    ranked = rank_signups(event_dict)
    # Build event_type_map: event_id -> event_type
    event_type_map = {}
    for eid in event_dict.keys():
        event = Event.query.filter_by(id=eid).first()
        if event:
            event_type_map[eid] = event.event_type
    event_view, rank_view = select_competitors_by_event_type(
        ranked,
        speech_spots=speech_competitors,
        ld_spots=LD_competitors,
        pf_spots=PF_competitors,
        event_type_map=event_type_map,
        seed_randomness=True
    )

    # Build event_competitors: {event_id: [comp, ...]} with rank info
    event_competitors = {}
    for comp in event_view:
        eid = comp['event_id']
        if eid not in event_competitors:
            event_competitors[eid] = []
        # Find the corresponding rank from rank_view
        rank_info = next((r for r in rank_view if r['user_id'] == comp['user_id'] and r['event_id'] == comp['event_id']), None)
        comp_with_rank = comp.copy()
        comp_with_rank['rank'] = rank_info['rank'] if rank_info else 'N/A'
        event_competitors[eid].append(comp_with_rank)

    # Build users and events dicts for template lookup
    user_ids = set([comp['user_id'] for comp in event_view] + [row['user_id'] for row in rank_view])
    event_ids = set([comp['event_id'] for comp in event_view] + [row['event_id'] for row in rank_view])
    users = {u.id: u for u in User.query.filter(User.id.in_(user_ids)).all()}
    events = {e.id: e for e in Event.query.filter(Event.id.in_(event_ids)).all()}

    # Judges for the tournament
    judges = Tournament_Judges.query.filter_by(tournament_id=tournament_id, accepted=True).all()
    judge_user_ids = [j.judge_id for j in judges if j.judge_id]
    child_user_ids = [j.child_id for j in judges if j.child_id]
    all_judge_user_ids = list(set(judge_user_ids + child_user_ids))
    judge_users = {u.id: u for u in User.query.filter(User.id.in_(all_judge_user_ids)).all() if all_judge_user_ids}

    # Debug output
    print(f"Tournament {tournament_id}: {len(judges)} judges, {len(event_view)} competitors in event_view, {len(rank_view)} in rank_view")

    return render_template('rosters/view_tournament.html',
                          event_view=event_view,
                          rank_view=rank_view,
                          event_competitors=event_competitors,
                          users=users,
                          events=events,
                          judges=judges,
                          judge_users=judge_users,
                          upcoming_tournaments=[],
                          tournaments=[],
                          rosters=[])

@rosters_bp.route('/save_roster/<int:tournament_id>')
def save_roster(tournament_id):
    pass