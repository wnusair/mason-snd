#!/usr/bin/env python3
"""
Debug the signup POST request
"""

from mason_snd import create_app
from mason_snd.extensions import db
from mason_snd.models.auth import User, Judges
from mason_snd.models.tournaments import Tournament, Tournament_Signups, Tournament_Judges, Form_Fields, Form_Responses
from mason_snd.models.events import Event, User_Event

app = create_app()

with app.app_context():
    # Find a student and parent who can test the signup flow
    student = User.query.filter_by(first_name='Student6', last_name='Test').first()
    parent = User.query.filter_by(first_name='Parent6', last_name='Test').first()
    tournament = Tournament.query.first()
    
    print(f"Student: {student.first_name if student else 'None'}")
    print(f"Parent: {parent.first_name if parent else 'None'}")
    print(f"Tournament: {tournament.name if tournament else 'None'}")
    
    # Get student events
    student_events = Event.query.join(User_Event, Event.id == User_Event.event_id).filter(
        User_Event.user_id == student.id,
        User_Event.active == True
    ).all()
    
    if not student_events:
        print("❌ Student has no events")
        exit(1)
    
    # Test the signup process via web interface simulation
    with app.test_client() as client:
        # Simulate login as student
        with client.session_transaction() as sess:
            sess['user_id'] = student.id
        
        # Test POST request to submit signup
        form_data = {
            'tournament_id': str(tournament.id),
            'user_event': [str(student_events[0].id)],  # Select first event
            'field_1': 'yes'  # The exact value expected by the dropdown
        }
        
        print(f"Submitting signup form with data: {form_data}")
        
        # Check if any existing Tournament_Signups exist
        existing_signup = Tournament_Signups.query.filter_by(
            user_id=student.id,
            tournament_id=tournament.id,
            event_id=student_events[0].id
        ).first()
        print(f"Existing signup: {existing_signup is not None}")
        
        # Check if any existing Tournament_Judges entries exist
        existing_judges = Tournament_Judges.query.filter_by(
            child_id=student.id,
            tournament_id=tournament.id,
            event_id=student_events[0].id
        ).all()
        print(f"Existing judge entries: {len(existing_judges)}")
        
        # Submit the form
        response = client.post('/tournaments/signup', data=form_data, follow_redirects=False)
        print(f"Signup POST status: {response.status_code}")
        
        if response.status_code != 302:
            print(f"Response data: {response.get_data(as_text=True)[:500]}")
        else:
            print(f"Redirect location: {response.headers.get('Location', 'None')}")
            
            # Check what was created
            print(f"\n--- After signup attempt ---")
            new_signup = Tournament_Signups.query.filter_by(
                user_id=student.id,
                tournament_id=tournament.id,
                event_id=student_events[0].id
            ).first()
            print(f"Tournament signup exists: {new_signup is not None}")
            if new_signup:
                print(f"  is_going: {new_signup.is_going}")
                print(f"  bringing_judge: {new_signup.bringing_judge}")
                print(f"  judge_id: {new_signup.judge_id}")
            
            new_judges = Tournament_Judges.query.filter_by(
                child_id=student.id,
                tournament_id=tournament.id,
                event_id=student_events[0].id
            ).all()
            print(f"Tournament judge entries: {len(new_judges)}")
            for judge_entry in new_judges:
                judge_name = User.query.get(judge_entry.judge_id).first_name if judge_entry.judge_id else "None"
                print(f"  judge_id: {judge_entry.judge_id} ({judge_name}), accepted: {judge_entry.accepted}")
            
            # Check form responses
            form_responses = Form_Responses.query.filter_by(
                tournament_id=tournament.id,
                user_id=student.id
            ).all()
            print(f"Form responses: {len(form_responses)}")
            for resp in form_responses:
                field = Form_Fields.query.get(resp.field_id)
                print(f"  {field.label}: {resp.response}")
