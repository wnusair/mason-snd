#!/usr/bin/env python3
"""
Debug script to simulate tournament signup process
"""

from mason_snd import create_app
from mason_snd.extensions import db
from mason_snd.models.auth import User, Judges
from mason_snd.models.tournaments import Tournament, Tournament_Signups, Tournament_Judges
from mason_snd.models.events import Event, User_Event

app = create_app()

with app.app_context():
    # Find a student who hasn't signed up yet
    student = User.query.filter_by(first_name='Student3', last_name='Test').first()
    parent = User.query.filter_by(first_name='Parent3', last_name='Test').first()
    tournament = Tournament.query.first()
    event = Event.query.first()
    
    print(f"Student: {student.first_name if student else 'None'}")
    print(f"Parent: {parent.first_name if parent else 'None'}")
    print(f"Tournament: {tournament.name if tournament else 'None'}")
    print(f"Event: {event.event_name if event else 'None'}")
    
    if not all([student, parent, tournament, event]):
        print("❌ Missing required data")
        exit(1)
    
    # Check existing judge requests before signup
    print(f"\n--- BEFORE SIGNUP ---")
    existing_requests = Tournament_Judges.query.filter_by(judge_id=parent.id).all()
    print(f"Existing judge requests for {parent.first_name}: {len(existing_requests)}")
    
    # Check existing Tournament_Judges entries for this combination
    existing_judge_entries = Tournament_Judges.query.filter_by(
        child_id=student.id,
        tournament_id=tournament.id,
        event_id=event.id
    ).all()
    print(f"Existing Tournament_Judges entries for this student/tournament/event: {len(existing_judge_entries)}")
    for entry in existing_judge_entries:
        judge_name = User.query.get(entry.judge_id).first_name if entry.judge_id else "None"
        print(f"  - Judge: {judge_name}, Accepted: {entry.accepted}")
    
    # Simulate the signup process
    print(f"\n--- SIMULATING SIGNUP PROCESS ---")
    
    # First, create/update Tournament_Signups
    signup = Tournament_Signups.query.filter_by(
        user_id=student.id, 
        tournament_id=tournament.id, 
        event_id=event.id
    ).first()
    
    if not signup:
        signup = Tournament_Signups(
            user_id=student.id,
            tournament_id=tournament.id,
            event_id=event.id,
            is_going=True
        )
        db.session.add(signup)
        print(f"Created new Tournament_Signups entry")
    else:
        signup.is_going = True
        print(f"Updated existing Tournament_Signups entry")
    
    # Then create Tournament_Judges entry with judge_id=None (as done in signup())
    existing_judge = Tournament_Judges.query.filter_by(
        child_id=student.id,
        tournament_id=tournament.id,
        event_id=event.id
    ).first()
    
    if not existing_judge:
        judge_acceptance = Tournament_Judges(
            accepted=False,
            judge_id=None,  # Initially None
            child_id=student.id,
            tournament_id=tournament.id,
            event_id=event.id
        )
        db.session.add(judge_acceptance)
        print(f"Created Tournament_Judges entry with judge_id=None")
    else:
        print(f"Tournament_Judges entry already exists")
    
    db.session.commit()
    
    # Now simulate the bringing_judge selection
    print(f"\n--- SIMULATING JUDGE SELECTION ---")
    
    # Update Tournament_Signups with judge info
    signup.bringing_judge = True
    signup.judge_id = parent.id
    
    # Update Tournament_Judges entries where judge_id is None
    judge_rows = Tournament_Judges.query.filter_by(
        child_id=student.id, 
        tournament_id=tournament.id, 
        judge_id=None
    ).all()
    
    print(f"Found {len(judge_rows)} Tournament_Judges entries with judge_id=None")
    
    for judge_row in judge_rows:
        judge_row.judge_id = parent.id
        print(f"Updated Tournament_Judges entry to have judge_id={parent.id}")
    
    db.session.commit()
    
    # Check the result
    print(f"\n--- AFTER SIGNUP ---")
    judge_requests = Tournament_Judges.query.filter_by(judge_id=parent.id).all()
    print(f"Judge requests for {parent.first_name}: {len(judge_requests)}")
    
    for req in judge_requests:
        child = User.query.get(req.child_id)
        tournament_name = Tournament.query.get(req.tournament_id).name
        event_name = Event.query.get(req.event_id).event_name if req.event_id else "No event"
        print(f"  - Request from {child.first_name}, Tournament: {tournament_name}, Event: {event_name}, Accepted: {req.accepted}")
