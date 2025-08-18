#!/usr/bin/env python3
"""
Test that the parent can see and respond to judge requests
"""

from mason_snd import create_app
from mason_snd.extensions import db
from mason_snd.models.auth import User
from mason_snd.models.tournaments import Tournament_Judges, Tournament

app = create_app()

with app.app_context():
    # Test with Parent9 who we just created a request for
    parent = User.query.filter_by(first_name='Parent9', last_name='Test').first()
    
    print(f"Testing judge requests for: {parent.first_name if parent else 'None'}")
    print(f"Parent is_parent: {parent.is_parent if parent else 'None'}")
    
    # Check their judge requests directly from database
    judge_requests = Tournament_Judges.query.filter_by(judge_id=parent.id).all()
    print(f"Judge requests in database: {len(judge_requests)}")
    
    for req in judge_requests:
        child = User.query.get(req.child_id)
        tournament = Tournament.query.get(req.tournament_id)
        print(f"  - Request from {child.first_name}, Tournament: {tournament.name}, Accepted: {req.accepted}")
    
    # Test the judge_requests web interface
    with app.test_client() as client:
        # Simulate login as parent
        with client.session_transaction() as sess:
            sess['user_id'] = parent.id
        
        # Test GET request to judge_requests page
        response = client.get('/tournaments/judge_requests')
        print(f"\nJudge requests page status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Judge requests page loaded successfully!")
            content = response.get_data(as_text=True)
            
            # Check if the request appears on the page
            if "Student9" in content:
                print("✅ Child's name appears in the page")
            else:
                print("❌ Child's name does not appear in the page")
            
            if "princeton" in content:
                print("✅ Tournament name appears in the page")
            else:
                print("❌ Tournament name does not appear in the page")
            
            # Check for form elements to accept/deny
            if 'decision_' in content:
                print("✅ Decision form elements found")
            else:
                print("❌ No decision form elements found")
                
            # Let's see a snippet of the content
            print(f"\nPage content snippet:")
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'Student9' in line or 'princeton' in line or 'decision_' in line:
                    print(f"  Line {i}: {line.strip()}")
        else:
            print(f"❌ Failed to load judge requests page: {response.status_code}")
            print(response.get_data(as_text=True)[:500])
