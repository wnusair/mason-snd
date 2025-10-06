import csv
from io import StringIO, BytesIO
from math import ceil
import random

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, Response, send_file

from mason_snd.extensions import db
from mason_snd.models.auth import User, User_Published_Rosters, Roster_Penalty_Entries
from mason_snd.models.admin import User_Requirements, Requirements
from mason_snd.models.tournaments import Tournament, Tournament_Performance, Tournament_Judges, Tournament_Signups
from mason_snd.models.events import Event, User_Event, Effort_Score
from mason_snd.models.metrics import MetricsSettings
from mason_snd.blueprints.metrics.metrics import get_point_weights
from mason_snd.utils.race_protection import prevent_race_condition

# Create a new Roster entry
from mason_snd.models.rosters import Roster, Roster_Competitors, Roster_Judge
from mason_snd.models.tournaments import Tournament_Judges
from datetime import datetime
from sqlalchemy import asc, desc, func

from datetime import datetime
import pytz


try:
    import pandas as pd
    import openpyxl
except ImportError:
    pd = None
    openpyxl = None


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
    signups = Tournament_Signups.query.filter_by(tournament_id=tournament_id, is_going=True).all()
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

# Helper: Filter out users with drop penalties and track them
def filter_drops_and_track_penalties(ranked):
    """
    Filter out users with drops > 0 and return both filtered rankings and penalty info
    """
    filtered_ranked = {}
    penalty_info = {}  # {event_id: [(user_id, rank, replacement_user_id), ...]}
    
    for event_id, signups in ranked.items():
        filtered_signups = []
        penalties = []
        
        for i, signup in enumerate(signups):
            if signup.user.drops > 0:
                # Find replacement (next user without drops)
                replacement = None
                for j in range(i + 1, len(signups)):
                    if signups[j].user.drops == 0:
                        replacement = signups[j].user_id
                        break
                        
                penalties.append({
                    'user_id': signup.user_id,
                    'original_rank': i + 1,
                    'replacement_user_id': replacement,
                    'drops': signup.user.drops
                })
                # Decrement user's drops by 1 (penalty applied)
                signup.user.drops -= 1
                db.session.commit()
            else:
                filtered_signups.append(signup)
        
        filtered_ranked[event_id] = filtered_signups
        if penalties:
            penalty_info[event_id] = penalties
    
    return filtered_ranked, penalty_info

# Helper: Select competitors for speech (rotation) and LD/PF (top N with randomness)
def select_competitors_by_event_type(ranked, speech_spots, ld_spots, pf_spots, event_type_map, seed_randomness=True):
    event_view = []
    rank_view = []
    random_selections = set()  # Track randomly selected competitors
    
    # Speech events: rotation with random selections
    speech_event_ids = [eid for eid, etype in event_type_map.items() if etype == 0]
    speech_judges_count = len(speech_event_ids)
    
    speech_indices = {eid: 0 for eid in speech_event_ids}
    speech_filled = 0
    random_counter = 0
    
    while speech_filled < speech_spots and speech_event_ids:
        for eid in speech_event_ids:
            competitors = ranked.get(eid, [])
            if speech_indices[eid] < len(competitors):
                # Every 5th person should be random from middle if 4+ speech judges
                should_be_random = (speech_judges_count >= 4 and random_counter % 5 == 4)
                
                if should_be_random and len(competitors) > 2:
                    # Pick from middle third of competitors
                    mid_start = len(competitors) // 3
                    mid_end = 2 * len(competitors) // 3
                    idx = random.randint(mid_start, mid_end)
                    random_selections.add((competitors[idx].user_id, eid))
                else:
                    idx = speech_indices[eid]
                
                if idx < len(competitors):
                    signup = competitors[idx]
                    event_view.append({'user_id': signup.user_id, 'event_id': eid})
                    rank_view.append({'user_id': signup.user_id, 'event_id': eid, 'rank': idx+1})
                    speech_indices[eid] += 1
                    speech_filled += 1
                    random_counter += 1
                    if speech_filled >= speech_spots:
                        break
        
        if all(speech_indices[eid] >= len(ranked.get(eid, [])) for eid in speech_event_ids):
            break
    
    # LD events: top people, or middle if 2+ judges
    ld_event_ids = [eid for eid, etype in event_type_map.items() if etype == 1]
    ld_judges_count = len(ld_event_ids)
    
    for eid in ld_event_ids:
        competitors = ranked.get(eid, [])
        for i in range(min(ld_spots, len(competitors))):
            if ld_judges_count >= 2 and len(competitors) > 2:
                # Pick from middle
                mid_idx = len(competitors) // 2
                idx = min(i + mid_idx, len(competitors) - 1)
                random_selections.add((competitors[idx].user_id, eid))
            else:
                idx = i
            
            if idx < len(competitors):
                signup = competitors[idx]
                event_view.append({'user_id': signup.user_id, 'event_id': eid})
                rank_view.append({'user_id': signup.user_id, 'event_id': eid, 'rank': idx+1})
    
    # PF events: top people, or middle if 2+ judges
    pf_event_ids = [eid for eid, etype in event_type_map.items() if etype == 2]
    pf_judges_count = len(pf_event_ids)
    
    for eid in pf_event_ids:
        competitors = ranked.get(eid, [])
        for i in range(min(pf_spots, len(competitors))):
            if pf_judges_count >= 2 and len(competitors) > 2:
                # Pick from middle
                mid_idx = len(competitors) // 2
                idx = min(i + mid_idx, len(competitors) - 1)
                random_selections.add((competitors[idx].user_id, eid))
            else:
                idx = i
            
            if idx < len(competitors):
                signup = competitors[idx]
                event_view.append({'user_id': signup.user_id, 'event_id': eid})
                rank_view.append({'user_id': signup.user_id, 'event_id': eid, 'rank': idx+1})
    
    return event_view, rank_view, random_selections

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
    
    # Filter out users with drops and track penalties
    filtered_ranked, penalty_info = filter_drops_and_track_penalties(ranked)
    
    # Build event_type_map: event_id -> event_type
    event_type_map = {}
    for eid in event_dict.keys():
        event = Event.query.filter_by(id=eid).first()
        if event:
            event_type_map[eid] = event.event_type
    event_view, rank_view, random_selections = select_competitors_by_event_type(
        filtered_ranked,  # Use filtered rankings
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

    users = {}
    events = {}

    if user_ids:
        users = {u.id: u for u in User.query.filter(User.id.in_(user_ids)).all()}
    if event_ids:
        events = {e.id: e for e in Event.query.filter(Event.id.in_(event_ids)).all()}

    # Get point weights for weighted points calculation
    tournament_weight, effort_weight = get_point_weights()

    # Add weighted_points to event_competitors for display
    for eid, competitors in event_competitors.items():
        for comp in competitors:
            user = users.get(comp['user_id'])
            if user:
                comp['weighted_points'] = getattr(user, 'weighted_points', getattr(user, 'points', 0))

    # Judges for the tournament
    judges = Tournament_Judges.query.filter_by(tournament_id=tournament_id, accepted=True).all()
    judge_user_ids = [j.judge_id for j in judges if j.judge_id]
    child_user_ids = [j.child_id for j in judges if j.child_id]
    all_judge_user_ids = list(set(judge_user_ids + child_user_ids))
    
    judge_users = {}
    if all_judge_user_ids:
        judge_users = {u.id: u for u in User.query.filter(User.id.in_(all_judge_user_ids)).all()}

    # Debug output
    print(f"Tournament {tournament_id}: {len(judges)} judges, {len(event_view)} competitors in event_view, {len(rank_view)} in rank_view")
    print(f"Event competitors: {list(event_competitors.keys())}")
    print(f"Users dict has {len(users)} users")
    print(f"Events dict has {len(events)} events")

    tournament = Tournament.query.get(tournament_id)
    return render_template('rosters/view_tournament.html',
                          tournament=tournament,
                          event_view=event_view,
                          rank_view=rank_view,
                          event_competitors=event_competitors,
                          users=users,
                          events=events,
                          judges=judges,
                          judge_users=judge_users,
                          penalty_info=penalty_info,
                          random_selections=random_selections,
                          tournament_weight=tournament_weight,
                          effort_weight=effort_weight,
                          upcoming_tournaments=[],
                          tournaments=[],
                          rosters=[])

@rosters_bp.route('/download_tournament/<int:tournament_id>')
def download_tournament(tournament_id):
    """Download a tournament view as an Excel file with multiple sheets"""
    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()

    if not user_id:
        flash("Log In First")
        return redirect(url_for('auth.login'))

    if user.role < 2:
        flash("You are not authorized to access this page")
        return redirect(url_for('main.index'))

    tournament = Tournament.query.get(tournament_id)
    if not tournament:
        flash("Tournament not found")
        return redirect(url_for('rosters.index'))

    if pd is None or openpyxl is None:
        flash("Excel functionality not available. Please install pandas and openpyxl.")
        return redirect(url_for('rosters.view_tournament', tournament_id=tournament_id))

    # Use the same algorithm as view_tournament by calling the same helper functions
    speech_competitors, LD_competitors, PF_competitors = get_roster_count(tournament_id)
    event_dict = get_signups_by_event(tournament_id)
    ranked = rank_signups(event_dict)
    event_type_map = {}
    for eid in event_dict.keys():
        event = Event.query.filter_by(id=eid).first()
        if event:
            event_type_map[eid] = event.event_type
    event_view, rank_view, random_selections = select_competitors_by_event_type(
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
        comp_with_rank['is_random'] = (comp['user_id'], comp['event_id']) in random_selections
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

    # Create Excel file with multiple sheets
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')

    # Judges sheet
    judges_data = []
    for judge in judges:
        judge_name = f"{judge_users[judge.judge_id].first_name} {judge_users[judge.judge_id].last_name}" if judge.judge_id in judge_users else 'Unknown'
        child_name = f"{judge.child.first_name} {judge.child.last_name}" if judge.child else ''
        event_type = 'Unknown'
        people_bringing = 0
        if judge.event:
            if judge.event.event_type == 0:
                event_type = 'Speech'
                people_bringing = 6
            elif judge.event.event_type == 1:
                event_type = 'LD'
                people_bringing = 2
            elif judge.event.event_type == 2:
                event_type = 'PF'
                people_bringing = 4
        
        judges_data.append({
            'Judge Name': judge_name,
            'Child': child_name,
            'Category': event_type,
            'Number People Bringing': people_bringing,
            'Judge ID': judge.judge_id,
            'Child ID': judge.child_id,
            'Event ID': judge.event_id
        })
    
    judges_df = pd.DataFrame(judges_data)
    judges_df.to_excel(writer, sheet_name='Judges', index=False)

    # Rank View sheet
    rank_data = []
    for row in rank_view:
        user = users.get(row['user_id'])
        user_name = f"{user.first_name} {user.last_name}" if user else 'Unknown'
        event_name = events[row['event_id']].event_name if row['event_id'] in events else 'Unknown Event'
        event_type = 'Unknown'
        if row['event_id'] in events:
            if events[row['event_id']].event_type == 0:
                event_type = 'Speech'
            elif events[row['event_id']].event_type == 1:
                event_type = 'LD'
            elif events[row['event_id']].event_type == 2:
                event_type = 'PF'
        weighted_points = getattr(user, 'weighted_points', getattr(user, 'points', 0)) if user else 0
        rank_data.append({
            'Rank': row['rank'],
            'Competitor Name': user_name,
            'Weighted Points': weighted_points,
            'Event': event_name,
            'Category': event_type,
            'User ID': row['user_id'],
            'Event ID': row['event_id']
        })

    rank_df = pd.DataFrame(rank_data)
    rank_df.to_excel(writer, sheet_name='Rank View', index=False)

    # Event View sheets (one for each event)
    for event_id, competitors_list in event_competitors.items():
        event_name = events[event_id].event_name if event_id in events else f'Event {event_id}'
        event_data = []

        for comp in competitors_list:
            user = users.get(comp['user_id'])
            user_name = f"{user.first_name} {user.last_name}" if user else 'Unknown'
            event_type = 'Unknown'
            if event_id in events:
                if events[event_id].event_type == 0:
                    event_type = 'Speech'
                elif events[event_id].event_type == 1:
                    event_type = 'LD'
                elif events[event_id].event_type == 2:
                    event_type = 'PF'
            weighted_points = getattr(user, 'weighted_points', getattr(user, 'points', 0)) if user else 0
            event_data.append({
                'Event': event_name,
                'Category': event_type,
                'Rank': comp['rank'],
                'Competitor': user_name,
                'Weighted Points': weighted_points,
                'User ID': comp['user_id'],
                'Event ID': comp['event_id']
            })

        event_df = pd.DataFrame(event_data)
        # Limit sheet name length and remove invalid characters
        sheet_name = event_name[:30].replace('/', '-').replace('\\', '-').replace('*', '-').replace('?', '-').replace(':', '-').replace('[', '-').replace(']', '-')
        event_df.to_excel(writer, sheet_name=sheet_name, index=False)

    writer.close()
    output.seek(0)

    filename = f"tournament_{tournament.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(output, 
                     as_attachment=True, 
                     download_name=filename,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@rosters_bp.route('/save_roster/<int:tournament_id>')
def save_tournament(tournament_id):
    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()

    if not user_id:
        flash("Log In First")
        return redirect(url_for('auth.login'))

    if user.role < 2:
        flash("You are not authorized to access this page")
        return redirect(url_for('main.index'))

    # Use the same algorithm as view_tournament by calling the same helper functions
    speech_competitors, LD_competitors, PF_competitors = get_roster_count(tournament_id)
    event_dict = get_signups_by_event(tournament_id)
    ranked = rank_signups(event_dict)
    
    # Filter out users with drops and track penalties
    filtered_ranked, penalty_info = filter_drops_and_track_penalties(ranked)
    
    event_type_map = {}
    for eid in event_dict.keys():
        event = Event.query.filter_by(id=eid).first()
        if event:
            event_type_map[eid] = event.event_type
    event_view, rank_view, random_selections = select_competitors_by_event_type(
        filtered_ranked,  # Use filtered rankings
        speech_spots=speech_competitors,
        ld_spots=LD_competitors,
        pf_spots=PF_competitors,
        event_type_map=event_type_map,
        seed_randomness=True
    )

    tz = pytz.timezone('US/Eastern')
    tournament = Tournament.query.get(tournament_id)
    roster_name = f"{tournament.name} {datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')}"
    new_roster = Roster(name=roster_name, date_made=datetime.now(tz), tournament_id=tournament_id)
    db.session.add(new_roster)
    db.session.commit()  # Commit to get the roster id

    # Save competitors using the event_view generated by the helpers
    for comp in event_view:
        rc = Roster_Competitors(
            user_id=comp['user_id'],
            event_id=comp['event_id'],
            judge_id=None,  # Optionally, could be filled if logic exists
            roster_id=new_roster.id
        )
        db.session.add(rc)

    # Save partner relationships for partner events
    from mason_snd.models.rosters import Roster_Partners
    processed_partnerships = set()  # To avoid duplicate partnerships
    
    for comp in event_view:
        # Check if this is a partner event
        event = Event.query.get(comp['event_id'])
        if event and event.is_partner_event:
            # Find the signup to get partner information
            signup = Tournament_Signups.query.filter_by(
                tournament_id=tournament_id,
                user_id=comp['user_id'],
                event_id=comp['event_id'],
                is_going=True
            ).first()
            
            if signup and signup.partner_id:
                # Check if partner is also selected for the roster
                partner_in_roster = any(
                    c['user_id'] == signup.partner_id and c['event_id'] == comp['event_id'] 
                    for c in event_view
                )
                
                if partner_in_roster:
                    # Create partnership entry (avoid duplicates)
                    partnership_key = tuple(sorted([comp['user_id'], signup.partner_id]))
                    if partnership_key not in processed_partnerships:
                        rp = Roster_Partners(
                            partner1_user_id=partnership_key[0],
                            partner2_user_id=partnership_key[1],
                            roster_id=new_roster.id
                        )
                        db.session.add(rp)
                        processed_partnerships.add(partnership_key)

    # Save judges using the current Tournament_Judges with proper people_bringing calculation
    judges = Tournament_Judges.query.filter_by(tournament_id=tournament_id, accepted=True).all()
    for judge in judges:
        # Calculate people_bringing based on event type
        people_bringing = 0
        if judge.event:
            if judge.event.event_type == 0:  # Speech
                people_bringing = 6
            elif judge.event.event_type == 1:  # LD
                people_bringing = 2
            elif judge.event.event_type == 2:  # PF
                people_bringing = 4
        
        rj = Roster_Judge(
            user_id=judge.judge_id,
            child_id=judge.child_id,
            event_id=judge.event_id,
            roster_id=new_roster.id,
            people_bringing=people_bringing
        )
        db.session.add(rj)

    # Save penalty entries
    for event_id, penalties in penalty_info.items():
        for penalty in penalties:
            rpe = Roster_Penalty_Entries(
                roster_id=new_roster.id,
                tournament_id=tournament_id,
                event_id=event_id,
                penalized_user_id=penalty['user_id'],
                original_rank=penalty['original_rank'],
                drops_applied=penalty['drops']
            )
            db.session.add(rpe)

    db.session.commit()
    flash("Roster saved!")
    return redirect(url_for('rosters.view_roster', roster_id=new_roster.id))


@rosters_bp.route('/publish_roster/<int:roster_id>')
def publish_roster(roster_id):
    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()

    if not user_id:
        flash("Log In First")
        return redirect(url_for('auth.login'))

    if user.role < 2:
        flash("You are not authorized to access this page")
        return redirect(url_for('main.index'))

    roster = Roster.query.get_or_404(roster_id)
    
    if roster.published:
        flash("This roster is already published!")
        return redirect(url_for('rosters.view_roster', roster_id=roster_id))

    # Mark roster as published
    tz = pytz.timezone('US/Eastern')
    roster.published = True
    roster.published_at = datetime.now(tz)
    
    # Create entries for all users on this roster so they can see it in their profile
    competitors = Roster_Competitors.query.filter_by(roster_id=roster_id).all()
    for competitor in competitors:
        # Check if entry already exists
        existing = User_Published_Rosters.query.filter_by(
            user_id=competitor.user_id,
            roster_id=roster_id
        ).first()
        
        if not existing:
            published_entry = User_Published_Rosters(
                user_id=competitor.user_id,
                roster_id=roster_id,
                tournament_id=roster.tournament_id,
                event_id=competitor.event_id,
                notified=False
            )
            db.session.add(published_entry)
    
    db.session.commit()
    flash("Roster has been published! Users will be notified.")
    return redirect(url_for('rosters.view_roster', roster_id=roster_id))


@rosters_bp.route('/unpublish_roster/<int:roster_id>')
def unpublish_roster(roster_id):
    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()

    if not user_id:
        flash("Log In First")
        return redirect(url_for('auth.login'))

    if user.role < 2:
        flash("You are not authorized to access this page")
        return redirect(url_for('main.index'))

    roster = Roster.query.get_or_404(roster_id)
    
    # Mark roster as unpublished
    roster.published = False
    roster.published_at = None
    
    # Remove published roster entries for users
    User_Published_Rosters.query.filter_by(roster_id=roster_id).delete()
    
    db.session.commit()
    flash("Roster has been unpublished.")
    return redirect(url_for('rosters.view_roster', roster_id=roster_id))



@rosters_bp.route('/view_roster/<int:roster_id>')
def view_roster(roster_id):
    """
    Display a saved roster, using the same layout as view_tournament, but pulling from the Roster tables.
    """
    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()

    if not user_id:
        flash("Log In First")
        return redirect(url_for('auth.login'))

    if user.role < 2:
        flash("You are not authorized to access this page")
        return redirect(url_for('main.index'))

    roster = Roster.query.get(roster_id)
    if not roster:
        flash("Roster not found")
        return redirect(url_for('rosters.index'))

    # Get competitors and judges from the roster
    competitors = Roster_Competitors.query.filter_by(roster_id=roster_id).all()
    judges = Roster_Judge.query.filter_by(roster_id=roster_id).all()
    
    # Get penalty entries for this roster
    penalty_entries = Roster_Penalty_Entries.query.filter_by(roster_id=roster_id).all()
    penalty_info = {}
    for entry in penalty_entries:
        if entry.event_id not in penalty_info:
            penalty_info[entry.event_id] = []
        penalty_info[entry.event_id].append({
            'user_id': entry.penalized_user_id,
            'original_rank': entry.original_rank,
            'drops': entry.drops_applied,
            'replacement_user_id': None  # For saved rosters, we don't track replacements
        })

    # Build event_view and rank_view from competitors
    event_view = []
    rank_view = []
    event_competitors = {}
    
    for i, comp in enumerate(competitors):
        event_view.append({'user_id': comp.user_id, 'event_id': comp.event_id})
        # Use index + 1 as rank for saved rosters
        rank_view.append({'user_id': comp.user_id, 'event_id': comp.event_id, 'rank': i + 1})
        
        eid = comp.event_id
        if eid not in event_competitors:
            event_competitors[eid] = []
        event_competitors[eid].append({'user_id': comp.user_id, 'event_id': eid, 'rank': i + 1})

    # Build users and events dicts for template lookup
    user_ids = set([comp.user_id for comp in competitors] + [j.user_id for j in judges if j.user_id] + [j.child_id for j in judges if j.child_id])
    event_ids = set([comp.event_id for comp in competitors] + [j.event_id for j in judges if j.event_id])
    
    users = {}
    events = {}
    
    if user_ids:
        users = {u.id: u for u in User.query.filter(User.id.in_(user_ids)).all()}
    if event_ids:
        events = {e.id: e for e in Event.query.filter(Event.id.in_(event_ids)).all()}

    # Get point weights for weighted points calculation
    tournament_weight, effort_weight = get_point_weights()

    # Judges for the roster
    judge_user_ids = [j.user_id for j in judges if j.user_id]
    child_user_ids = [j.child_id for j in judges if j.child_id]
    all_judge_user_ids = list(set(judge_user_ids + child_user_ids))
    
    judge_users = {}
    if all_judge_user_ids:
        judge_users = {u.id: u for u in User.query.filter(User.id.in_(all_judge_user_ids)).all()}

    # Debug information
    print(f"Roster {roster_id}: {len(competitors)} competitors, {len(judges)} judges")
    print(f"Event view has {len(event_view)} entries")
    print(f"Rank view has {len(rank_view)} entries")
    print(f"Event competitors: {list(event_competitors.keys())}")
    print(f"Users dict has {len(users)} users")
    print(f"Events dict has {len(events)} events")

    return render_template('rosters/view_roster.html',
                          roster=roster,
                          event_view=event_view,
                          rank_view=rank_view,
                          event_competitors=event_competitors,
                          users=users,
                          events=events,
                          judges=judges,
                          judge_users=judge_users,
                          penalty_info=penalty_info,
                          tournament_weight=tournament_weight,
                          effort_weight=effort_weight,
                          upcoming_tournaments=[],
                          tournaments=[],
                          rosters=[])

@rosters_bp.route('/download_roster/<int:roster_id>')
def download_roster(roster_id):
    """Download a roster as an Excel file with multiple sheets - fully editable and re-uploadable"""
    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()

    if not user_id:
        flash("Log In First")
        return redirect(url_for('auth.login'))

    if user.role < 2:
        flash("You are not authorized to access this page")
        return redirect(url_for('main.index'))

    roster = Roster.query.get(roster_id)
    if not roster:
        flash("Roster not found")
        return redirect(url_for('rosters.index'))

    if pd is None or openpyxl is None:
        flash("Excel functionality not available. Please install pandas and openpyxl.")
        return redirect(url_for('rosters.view_roster', roster_id=roster_id))

    # Get competitors and judges from the roster
    competitors = Roster_Competitors.query.filter_by(roster_id=roster_id).all()
    judges = Roster_Judge.query.filter_by(roster_id=roster_id).all()

    # Get partner information
    from mason_snd.models.rosters import Roster_Partners
    roster_partners = Roster_Partners.query.filter_by(roster_id=roster_id).all()
    
    # Build partnership map for quick lookup
    partnership_map = {}
    for partnership in roster_partners:
        partnership_map[partnership.partner1_user_id] = partnership.partner2_user_id
        partnership_map[partnership.partner2_user_id] = partnership.partner1_user_id

    # Build users and events dicts
    user_ids = set([comp.user_id for comp in competitors])
    event_ids = set([comp.event_id for comp in competitors])
    users = {u.id: u for u in User.query.filter(User.id.in_(user_ids)).all()}
    events = {e.id: e for e in Event.query.filter(Event.id.in_(event_ids)).all()}

    # Judges for the roster
    judge_user_ids = [j.user_id for j in judges if j.user_id]
    child_user_ids = [j.child_id for j in judges if j.child_id]
    all_judge_user_ids = list(set(judge_user_ids + child_user_ids))
    judge_users = {u.id: u for u in User.query.filter(User.id.in_(all_judge_user_ids)).all() if all_judge_user_ids}

    # Create Excel file with multiple sheets
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')

    # JUDGES SHEET - fully editable
    judges_data = []
    for judge in judges:
        judge_name = f"{judge_users[judge.user_id].first_name} {judge_users[judge.user_id].last_name}" if judge.user_id in judge_users else 'Unknown'
        child_name = f"{judge.child.first_name} {judge.child.last_name}" if judge.child else ''
        event_name = judge.event.event_name if judge.event else 'Unknown'
        event_type = 'Unknown'
        if judge.event:
            if judge.event.event_type == 0:
                event_type = 'Speech'
            elif judge.event.event_type == 1:
                event_type = 'LD'
            elif judge.event.event_type == 2:
                event_type = 'PF'
        
        judges_data.append({
            'Judge Name': judge_name,
            'Child': child_name,
            'Event': event_name,
            'Category': event_type,
            'Number People Bringing': judge.people_bringing or 0,
            'Judge ID': judge.user_id,
            'Child ID': judge.child_id if judge.child_id else '',
            'Event ID': judge.event_id if judge.event_id else ''
        })
    
    judges_df = pd.DataFrame(judges_data)
    judges_df.to_excel(writer, sheet_name='Judges', index=False)

    # RANK VIEW SHEET - primary sheet for competitor editing
    # Build rank_view with actual ranking
    rank_view = []
    event_competitors_dict = {}
    
    for comp in competitors:
        eid = comp.event_id
        if eid not in event_competitors_dict:
            event_competitors_dict[eid] = []
        event_competitors_dict[eid].append(comp)
    
    # Rank competitors within each event by weighted points
    for event_id, comps in event_competitors_dict.items():
        sorted_comps = sorted(
            comps, 
            key=lambda c: getattr(users[c.user_id], 'weighted_points', getattr(users[c.user_id], 'points', 0)) if c.user_id in users else 0,
            reverse=True
        )
        for rank, comp in enumerate(sorted_comps, start=1):
            rank_view.append({
                'comp': comp,
                'rank': rank,
                'event_id': event_id
            })
    
    rank_data = []
    for item in rank_view:
        comp = item['comp']
        user = users.get(comp.user_id)
        event = events.get(comp.event_id)
        
        user_name = f"{user.first_name} {user.last_name}" if user else 'Unknown'
        event_name = event.event_name if event else 'Unknown Event'
        event_type = 'Unknown'
        if event:
            if event.event_type == 0:
                event_type = 'Speech'
            elif event.event_type == 1:
                event_type = 'LD'
            elif event.event_type == 2:
                event_type = 'PF'
        
        # Get partner information
        partner_name = ''
        partner_id = ''
        if comp.user_id in partnership_map:
            partner_id = partnership_map[comp.user_id]
            if partner_id in users:
                partner_name = f"{users[partner_id].first_name} {users[partner_id].last_name}"
        
        rank_data.append({
            'Rank': item['rank'],
            'Competitor Name': user_name,
            'Partner': partner_name,
            'Weighted Points': user.weighted_points if user and hasattr(user, 'weighted_points') else (user.points if user else 0),
            'Event': event_name,
            'Category': event_type,
            'Status': 'Active',  # Could be extended to show more statuses
            'User ID': comp.user_id,
            'Partner ID': partner_id if partner_id else '',
            'Event ID': comp.event_id
        })
    
    rank_df = pd.DataFrame(rank_data)
    rank_df.to_excel(writer, sheet_name='Rank View', index=False)

    # EVENT VIEW SHEETS - one for each event
    for event_id, comps in event_competitors_dict.items():
        event = events.get(event_id)
        event_name = event.event_name if event else f'Event {event_id}'
        event_type = 'Unknown'
        if event:
            if event.event_type == 0:
                event_type = 'Speech'
            elif event.event_type == 1:
                event_type = 'LD'
            elif event.event_type == 2:
                event_type = 'PF'
        
        # Sort by weighted points for ranking
        sorted_comps = sorted(
            comps,
            key=lambda c: getattr(users[c.user_id], 'weighted_points', getattr(users[c.user_id], 'points', 0)) if c.user_id in users else 0,
            reverse=True
        )
        
        event_data = []
        for rank, comp in enumerate(sorted_comps, start=1):
            user = users.get(comp.user_id)
            user_name = f"{user.first_name} {user.last_name}" if user else 'Unknown'
            
            # Get partner information
            partner_name = ''
            partner_id = ''
            if comp.user_id in partnership_map:
                partner_id = partnership_map[comp.user_id]
                if partner_id in users:
                    partner_name = f"{users[partner_id].first_name} {users[partner_id].last_name}"
            
            event_data.append({
                'Event': event_name,
                'Category': event_type,
                'Rank': rank,
                'Competitor': user_name,
                'Partner': partner_name,
                'Weighted Points': user.weighted_points if user and hasattr(user, 'weighted_points') else (user.points if user else 0),
                'User ID': comp.user_id,
                'Partner ID': partner_id if partner_id else '',
                'Event ID': comp.event_id
            })
        
        event_df = pd.DataFrame(event_data)
        # Limit sheet name length and remove invalid characters
        sheet_name = event_name[:30].replace('/', '-').replace('\\', '-').replace('*', '-').replace('?', '-').replace(':', '-').replace('[', '-').replace(']', '-')
        event_df.to_excel(writer, sheet_name=sheet_name, index=False)

    # Add formatting to make it clear what can be edited
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
    
    # Format all sheets
    for sheet_name in writer.sheets:
        worksheet = writer.sheets[sheet_name]
        
        # Header formatting
        header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
        header_font = Font(color='FFFFFF', bold=True)
        
        # ID columns (read-only indicators) - lighter background
        id_fill = PatternFill(start_color='E8F4F8', end_color='E8F4F8', fill_type='solid')
        
        # Editable columns - white/normal
        editable_fill = PatternFill(start_color='FFFFFF', end_color='FFFFFF', fill_type='solid')
        
        for row in worksheet.iter_rows(min_row=1, max_row=1):
            for cell in row:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Apply column-specific formatting
        for col_idx, column in enumerate(worksheet.iter_cols(min_row=2), start=1):
            col_letter = get_column_letter(col_idx)
            header_value = worksheet[f'{col_letter}1'].value
            
            # Adjust column width
            max_length = 0
            for cell in column:
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except:
                    pass
            
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[col_letter].width = adjusted_width
            
            # Color code columns
            if header_value and 'ID' in str(header_value):
                # ID columns - indicate these are used for matching, but names take precedence for display
                for cell in column:
                    cell.fill = id_fill
            else:
                # Editable columns
                for cell in column:
                    if header_value in ['Rank', 'Weighted Points', 'Status', 'Category', 'Event']:
                        # These are informational/calculated - light gray
                        cell.fill = PatternFill(start_color='F0F0F0', end_color='F0F0F0', fill_type='solid')
                    else:
                        # Names and other editable fields - white
                        cell.fill = editable_fill

    writer.close()
    output.seek(0)

    filename = f"roster_{roster.name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(output, 
                     as_attachment=True, 
                     download_name=filename,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@rosters_bp.route('/rename_roster/<int:roster_id>', methods=['GET', 'POST'])
@prevent_race_condition('rename_roster', min_interval=1.0, redirect_on_duplicate=lambda uid, form: redirect(url_for('rosters.view_roster', roster_id=request.view_args.get('roster_id'))))
def rename_roster(roster_id):
    """Rename a roster"""
    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()

    if not user_id:
        flash("Log In First")
        return redirect(url_for('auth.login'))

    if user.role < 2:
        flash("You are not authorized to access this page")
        return redirect(url_for('main.index'))

    roster = Roster.query.get(roster_id)
    if not roster:
        flash("Roster not found")
        return redirect(url_for('rosters.index'))

    if request.method == 'POST':
        new_name = request.form.get('new_name')
        if new_name:
            roster.name = new_name
            db.session.commit()
            flash(f"Roster renamed to '{new_name}'")
        return redirect(url_for('rosters.view_roster', roster_id=roster_id))

    return render_template('rosters/rename_roster.html', roster=roster)

@rosters_bp.route('/delete_roster/<int:roster_id>')
def delete_roster(roster_id):
    """Delete a roster and all associated data"""
    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()

    if not user_id:
        flash("Log In First")
        return redirect(url_for('auth.login'))

    if user.role < 2:
        flash("You are not authorized to access this page")
        return redirect(url_for('main.index'))

    roster = Roster.query.get(roster_id)
    if not roster:
        flash("Roster not found")
        return redirect(url_for('rosters.index'))

    # Delete associated competitors and judges
    Roster_Competitors.query.filter_by(roster_id=roster_id).delete()
    Roster_Judge.query.filter_by(roster_id=roster_id).delete()
    
    # Delete the roster itself
    db.session.delete(roster)
    db.session.commit()
    
    flash("Roster deleted successfully")
    return redirect(url_for('rosters.index'))

@rosters_bp.route('/upload_roster', methods=['GET', 'POST'])
@prevent_race_condition('upload_roster', min_interval=2.0, redirect_on_duplicate=lambda uid, form: redirect(url_for('rosters.index')))
def upload_roster():
    """Upload an Excel file to create or update a roster with smart name reconciliation"""
    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()

    if not user_id:
        flash("Log In First")
        return redirect(url_for('auth.login'))

    if user.role < 2:
        flash("You are not authorized to access this page")
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        if 'file' not in request.files:
            flash("No file selected")
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash("No file selected")
            return redirect(request.url)
        
        if not file.filename.endswith('.xlsx'):
            flash("Please upload an Excel (.xlsx) file")
            return redirect(request.url)

        if pd is None or openpyxl is None:
            flash("Excel functionality not available. Please install pandas and openpyxl.")
            return redirect(url_for('rosters.index'))

        try:
            # Read the Excel file
            excel_file = pd.ExcelFile(file)
            
            # Get roster name and ID from form
            roster_name = request.form.get('roster_name', f"Uploaded Roster {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            roster_id = request.form.get('roster_id')  # If updating existing roster
            
            # Determine if we're updating or creating
            if roster_id:
                new_roster = Roster.query.get(int(roster_id))
                if not new_roster:
                    flash("Roster not found")
                    return redirect(url_for('rosters.index'))
                
                # Clear existing data
                Roster_Competitors.query.filter_by(roster_id=new_roster.id).delete()
                Roster_Judge.query.filter_by(roster_id=new_roster.id).delete()
                from mason_snd.models.rosters import Roster_Partners
                Roster_Partners.query.filter_by(roster_id=new_roster.id).delete()
            else:
                # Create new roster
                tz = pytz.timezone('US/Eastern')
                new_roster = Roster(name=roster_name, date_made=datetime.now(tz))
                db.session.add(new_roster)
                db.session.flush()  # Get the ID

            # Helper function to find user by ID or name with smart matching
            def find_user_smart(user_id_val, name_val):
                """
                Smart user finder:
                1. If User ID is provided and valid, use it (name changes are ignored)
                2. Otherwise, try to match by exact name
                3. Fall back to fuzzy name matching
                """
                # Try User ID first (most reliable)
                if pd.notna(user_id_val):
                    try:
                        user = User.query.get(int(user_id_val))
                        if user:
                            return user
                    except (ValueError, TypeError):
                        pass
                
                # Try exact name match
                if name_val and str(name_val).strip():
                    name_parts = str(name_val).strip().split()
                    if len(name_parts) >= 2:
                        first_name = name_parts[0]
                        last_name = ' '.join(name_parts[1:])
                        user = User.query.filter_by(first_name=first_name, last_name=last_name).first()
                        if user:
                            return user
                        
                        # Try fuzzy matching (case-insensitive)
                        user = User.query.filter(
                            db.func.lower(User.first_name) == first_name.lower(),
                            db.func.lower(User.last_name) == last_name.lower()
                        ).first()
                        if user:
                            return user
                
                return None

            # Process judges sheet with smart reconciliation
            changes_log = {'judges': [], 'competitors': [], 'warnings': []}
            
            if 'Judges' in excel_file.sheet_names:
                judges_df = pd.read_excel(file, sheet_name='Judges')
                for idx, row in judges_df.iterrows():
                    # Find judge user with smart matching
                    judge_user = find_user_smart(
                        row.get('Judge ID'),
                        row.get('Judge Name')
                    )
                    
                    # Find child user with smart matching
                    child_user = find_user_smart(
                        row.get('Child ID'),
                        row.get('Child', '')
                    )
                    
                    # Find event by ID (prioritize ID over name)
                    event = None
                    if 'Event ID' in row and pd.notna(row['Event ID']):
                        event = Event.query.get(int(row['Event ID']))
                    elif 'Event' in row and pd.notna(row['Event']):
                        event = Event.query.filter_by(event_name=str(row['Event'])).first()
                    
                    # Get people_bringing
                    people_bringing = 0
                    if 'Number People Bringing' in row and pd.notna(row['Number People Bringing']):
                        people_bringing = int(row['Number People Bringing'])
                    elif event:
                        if event.event_type == 0:
                            people_bringing = 6
                        elif event.event_type == 1:
                            people_bringing = 2
                        elif event.event_type == 2:
                            people_bringing = 4
                    
                    if judge_user:
                        rj = Roster_Judge(
                            user_id=judge_user.id,
                            child_id=child_user.id if child_user else None,
                            event_id=event.id if event else None,
                            roster_id=new_roster.id,
                            people_bringing=people_bringing
                        )
                        db.session.add(rj)
                        changes_log['judges'].append(f"Row {idx+2}: Added judge {judge_user.first_name} {judge_user.last_name}")
                    else:
                        changes_log['warnings'].append(f"Row {idx+2} in Judges: Could not find user '{row.get('Judge Name', 'Unknown')}'")

            # Process competitors from Rank View sheet with smart reconciliation
            if 'Rank View' in excel_file.sheet_names:
                rank_df = pd.read_excel(file, sheet_name='Rank View')
                
                # Sort by rank if available to preserve order
                if 'Rank' in rank_df.columns:
                    rank_df = rank_df.sort_values('Rank')
                
                for idx, row in rank_df.iterrows():
                    # Find user with smart matching
                    user = find_user_smart(
                        row.get('User ID'),
                        row.get('Competitor Name')
                    )
                    
                    # Find event by ID (prioritize ID)
                    event = None
                    if 'Event ID' in row and pd.notna(row['Event ID']):
                        event = Event.query.get(int(row['Event ID']))
                    elif 'Event' in row and pd.notna(row['Event']):
                        event = Event.query.filter_by(event_name=str(row['Event'])).first()
                    
                    if user and event:
                        rc = Roster_Competitors(
                            user_id=user.id,
                            event_id=event.id,
                            judge_id=None,
                            roster_id=new_roster.id
                        )
                        db.session.add(rc)
                        changes_log['competitors'].append(f"Row {idx+2}: Added {user.first_name} {user.last_name} to {event.event_name}")
                    else:
                        warning_msg = f"Row {idx+2} in Rank View: "
                        if not user:
                            warning_msg += f"Could not find user '{row.get('Competitor Name', 'Unknown')}'"
                        if not event:
                            warning_msg += f"Could not find event '{row.get('Event', 'Unknown')}'"
                        changes_log['warnings'].append(warning_msg)

            # Process event view sheets (for additional competitor data)
            for sheet_name in excel_file.sheet_names:
                if sheet_name not in ['Judges', 'Rank View']:
                    event_df = pd.read_excel(file, sheet_name=sheet_name)
                    
                    # Try to find the event for this sheet
                    event = None
                    if 'Event ID' in event_df.columns and len(event_df) > 0:
                        event_id = event_df.iloc[0]['Event ID']
                        if pd.notna(event_id):
                            event = Event.query.get(int(event_id))
                    
                    if not event and 'Event' in event_df.columns and len(event_df) > 0:
                        event_name = event_df.iloc[0]['Event']
                        if pd.notna(event_name):
                            event = Event.query.filter_by(event_name=str(event_name)).first()
                    
                    # Process competitors in this event sheet
                    for idx, row in event_df.iterrows():
                        user = find_user_smart(
                            row.get('User ID'),
                            row.get('Competitor')
                        )
                        
                        if user and event:
                            # Check if this competitor is already added
                            existing = Roster_Competitors.query.filter_by(
                                roster_id=new_roster.id,
                                user_id=user.id,
                                event_id=event.id
                            ).first()
                            
                            if not existing:
                                rc = Roster_Competitors(
                                    user_id=user.id,
                                    event_id=event.id,
                                    judge_id=None,
                                    roster_id=new_roster.id
                                )
                                db.session.add(rc)

            db.session.commit()
            
            # Show success message with changes summary
            success_msg = f"Roster '{new_roster.name}' {'updated' if roster_id else 'created'} successfully! "
            success_msg += f"Added {len(changes_log['competitors'])} competitors and {len(changes_log['judges'])} judges."
            if changes_log['warnings']:
                success_msg += f" {len(changes_log['warnings'])} warnings."
            
            flash(success_msg, 'success')
            
            # Show warnings if any
            for warning in changes_log['warnings'][:5]:  # Limit to first 5 warnings
                flash(warning, 'warning')
            
            return redirect(url_for('rosters.view_roster', roster_id=new_roster.id))

        except Exception as e:
            db.session.rollback()
            flash(f"Error processing file: {str(e)}", 'error')
            import traceback
            print(traceback.format_exc())
            return redirect(request.url)

    # GET request - show upload form with list of rosters
    rosters = Roster.query.order_by(Roster.date_made.desc()).all()
    return render_template('rosters/upload_roster.html', rosters=rosters)
