#!/usr/bin/env python3
"""
Test the actual web signup flow
"""

from mason_snd import create_app
from mason_snd.extensions import db
from mason_snd.models.auth import User, Judges
from mason_snd.models.tournaments import Tournament, Tournament_Signups, Tournament_Judges, Form_Fields, Form_Responses
from mason_snd.models.events import Event, User_Event

app = create_app()

with app.app_context():
    # Find a student and parent who can test the signup flow
    student = User.query.filter_by(first_name='Student4', last_name='Test').first()
    parent = User.query.filter_by(first_name='Parent4', last_name='Test').first()
    tournament = Tournament.query.first()
    
    print(f"Student: {student.first_name if student else 'None'}")
    print(f"Parent: {parent.first_name if parent else 'None'}")
    print(f"Tournament: {tournament.name if tournament else 'None'}")
    
    # Check if tournament has form fields (required for signup)
    form_fields = Form_Fields.query.filter_by(tournament_id=tournament.id).all()
    print(f"Tournament form fields: {len(form_fields)}")
    for field in form_fields:
        print(f"  - {field.label} ({field.type})")
    
    # Check if student has events they can sign up for
    student_events = Event.query.join(User_Event, Event.id == User_Event.event_id).filter(
        User_Event.user_id == student.id,
        User_Event.active == True
    ).all()
    print(f"Student events: {len(student_events)}")
    for event in student_events:
        print(f"  - {event.event_name}")
    
    # Check judge relationship
    judge_rel = Judges.query.filter_by(judge_id=parent.id, child_id=student.id).first()
    print(f"Judge relationship exists: {judge_rel is not None}")
    if judge_rel:
        print(f"  Background check: {judge_rel.background_check}")
    
    # Test the signup process via web interface simulation
    with app.test_client() as client:
        # Simulate login as student
        with client.session_transaction() as sess:
            sess['user_id'] = student.id
        
        # Test GET request to signup page
        response = client.get(f'/tournaments/signup?tournament_id={tournament.id}')
        print(f"\nSignup page status: {response.status_code}")
        
        if response.status_code == 200:
            content = response.get_data(as_text=True)
            if tournament.name in content:
                print("✅ Tournament appears in signup page")
            
            # Test POST request to submit signup
            if student_events and form_fields:
                # Prepare form data
                form_data = {
                    'tournament_id': tournament.id,
                    'user_event': [student_events[0].id],  # Select first event
                }
                
                # Add responses to form fields
                for field in form_fields:
                    if field.label.strip().lower() == "are you bringing a judge?":
                        form_data[f'field_{field.id}'] = 'yes'
                    else:
                        form_data[f'field_{field.id}'] = 'test response'
                
                print(f"Submitting signup form with data: {form_data}")
                
                # Submit the form
                response = client.post('/tournaments/signup', data=form_data, follow_redirects=False)
                print(f"Signup POST status: {response.status_code}")
                print(f"Redirect location: {response.headers.get('Location', 'None')}")
                
                # Check if redirected to bringing_judge
                if response.status_code == 302 and 'bringing_judge' in response.headers.get('Location', ''):
                    print("✅ Redirected to bringing_judge page")
                    
                    # Test the bringing_judge page
                    judge_response = client.get(f'/tournaments/bringing_judge/{tournament.id}')
                    print(f"Bringing judge page status: {judge_response.status_code}")
                    
                    if judge_response.status_code == 200:
                        judge_content = judge_response.get_data(as_text=True)
                        if parent.first_name in judge_content:
                            print("✅ Parent appears in judge selection")
                        
                        # Submit judge selection
                        judge_form_data = {'judge_id': parent.id}
                        judge_submit = client.post(f'/tournaments/bringing_judge/{tournament.id}', 
                                                 data=judge_form_data, follow_redirects=False)
                        print(f"Judge selection POST status: {judge_submit.status_code}")
                        
                        # Check if judge request was created
                        judge_requests = Tournament_Judges.query.filter_by(judge_id=parent.id).all()
                        print(f"Judge requests after signup: {len(judge_requests)}")
                        
                        for req in judge_requests:
                            child = User.query.get(req.child_id)
                            print(f"  - Request from {child.first_name}, Accepted: {req.accepted}")
                else:
                    print(f"❌ Expected redirect to bringing_judge, got: {response.headers.get('Location', 'None')}")
            else:
                print("❌ Missing student events or form fields for signup test")
        else:
            print(f"❌ Failed to load signup page: {response.status_code}")
