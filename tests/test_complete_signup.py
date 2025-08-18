#!/usr/bin/env python3
"""
Test the complete signup flow with proper CSRF handling
"""

from mason_snd import create_app
from mason_snd.extensions import db
from mason_snd.models.auth import User, Judges
from mason_snd.models.tournaments import Tournament, Tournament_Signups, Tournament_Judges, Form_Fields, Form_Responses
from mason_snd.models.events import Event, User_Event
import re

app = create_app()

with app.app_context():
    # Find a student and parent who can test the signup flow
    student = User.query.filter_by(first_name='Student9', last_name='Test').first()
    parent = User.query.filter_by(first_name='Parent9', last_name='Test').first()
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
    
    # Clean up any existing data for this test
    existing_signup = Tournament_Signups.query.filter_by(
        user_id=student.id,
        tournament_id=tournament.id,
        event_id=student_events[0].id
    ).first()
    if existing_signup:
        db.session.delete(existing_signup)
    
    existing_judges = Tournament_Judges.query.filter_by(
        child_id=student.id,
        tournament_id=tournament.id,
        event_id=student_events[0].id
    ).all()
    for judge in existing_judges:
        db.session.delete(judge)
    
    existing_responses = Form_Responses.query.filter_by(
        tournament_id=tournament.id,
        user_id=student.id
    ).all()
    for resp in existing_responses:
        db.session.delete(resp)
    
    db.session.commit()
    print("✅ Cleaned up existing test data")
    
    # Test the signup process via web interface simulation
    with app.test_client() as client:
        # Simulate login as student
        with client.session_transaction() as sess:
            sess['user_id'] = student.id
        
        # First, get the signup page to extract CSRF token
        get_response = client.get(f'/tournaments/signup?tournament_id={tournament.id}')
        print(f"GET signup page status: {get_response.status_code}")
        
        if get_response.status_code != 200:
            print("❌ Failed to get signup page")
            exit(1)
        
        # Extract CSRF token from the page
        content = get_response.get_data(as_text=True)
        csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', content)
        if not csrf_match:
            print("❌ Could not find CSRF token")
            exit(1)
        
        csrf_token = csrf_match.group(1)
        print(f"✅ Extracted CSRF token: {csrf_token[:20]}...")
        
        # Prepare form data with CSRF token
        form_data = {
            'tournament_id': str(tournament.id),
            'user_event': [str(student_events[0].id)],  # Select first event
            'field_1': 'yes',  # The exact value expected by the dropdown
            'csrf_token': csrf_token
        }
        
        print(f"Submitting signup form with data: {form_data}")
        
        # Submit the form
        response = client.post('/tournaments/signup', data=form_data, follow_redirects=False)
        print(f"Signup POST status: {response.status_code}")
        
        if response.status_code == 302:
            print(f"Redirect location: {response.headers.get('Location', 'None')}")
            
            # Check if redirected to bringing_judge
            redirect_location = response.headers.get('Location', '')
            if 'bringing_judge' in redirect_location:
                print("✅ Redirected to bringing_judge page")
                
                # Follow the redirect to bringing_judge page
                judge_response = client.get(redirect_location)
                print(f"Bringing judge page status: {judge_response.status_code}")
                
                if judge_response.status_code == 200:
                    judge_content = judge_response.get_data(as_text=True)
                    if parent.first_name in judge_content:
                        print("✅ Parent appears in judge selection")
                    
                    # Extract CSRF token from judge page
                    judge_csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', judge_content)
                    if judge_csrf_match:
                        judge_csrf_token = judge_csrf_match.group(1)
                        
                        # Submit judge selection
                        judge_form_data = {
                            'judge_id': str(parent.id),
                            'csrf_token': judge_csrf_token
                        }
                        
                        judge_submit = client.post(redirect_location, data=judge_form_data, follow_redirects=False)
                        print(f"Judge selection POST status: {judge_submit.status_code}")
                        
                        if judge_submit.status_code == 302:
                            print("✅ Judge selection submitted successfully")
                        else:
                            print(f"❌ Judge selection failed: {judge_submit.status_code}")
                            print(judge_submit.get_data(as_text=True)[:500])
                else:
                    print(f"❌ Failed to load bringing_judge page: {judge_response.status_code}")
            else:
                print(f"❌ Expected redirect to bringing_judge, got: {redirect_location}")
        else:
            print(f"❌ Signup failed with status: {response.status_code}")
            print(response.get_data(as_text=True)[:500])
        
        # Check final results
        print(f"\n--- Final Results ---")
        final_signup = Tournament_Signups.query.filter_by(
            user_id=student.id,
            tournament_id=tournament.id,
            event_id=student_events[0].id
        ).first()
        print(f"Tournament signup exists: {final_signup is not None}")
        if final_signup:
            print(f"  is_going: {final_signup.is_going}")
            print(f"  bringing_judge: {final_signup.bringing_judge}")
            print(f"  judge_id: {final_signup.judge_id}")
        
        final_judges = Tournament_Judges.query.filter_by(
            child_id=student.id,
            tournament_id=tournament.id,
            event_id=student_events[0].id
        ).all()
        print(f"Tournament judge entries: {len(final_judges)}")
        for judge_entry in final_judges:
            judge_name = User.query.get(judge_entry.judge_id).first_name if judge_entry.judge_id else "None"
            print(f"  judge_id: {judge_entry.judge_id} ({judge_name}), accepted: {judge_entry.accepted}")
        
        # Check judge requests from parent's perspective
        parent_requests = Tournament_Judges.query.filter_by(judge_id=parent.id).all()
        print(f"Judge requests for {parent.first_name}: {len(parent_requests)}")
        for req in parent_requests:
            child = User.query.get(req.child_id)
            tournament_name = Tournament.query.get(req.tournament_id).name
            event_name = Event.query.get(req.event_id).event_name if req.event_id else "No event"
            print(f"  - Request from {child.first_name}, Tournament: {tournament_name}, Event: {event_name}, Accepted: {req.accepted}")
