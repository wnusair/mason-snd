from mason_snd import create_app
from mason_snd.extensions import db
from mason_snd.models.auth import User
from mason_snd.models.tournaments import Tournament_Judges

app = create_app()

with app.app_context():
    # Test a parent accessing their judge requests
    parent1 = User.query.filter_by(first_name='Parent1', last_name='Test').first()
    print(f"Parent1 found: {parent1.first_name if parent1 else 'None'}")
    print(f"Parent1 is_parent: {parent1.is_parent if parent1 else 'None'}")
    
    # Check their judge requests
    judge_requests = Tournament_Judges.query.filter_by(judge_id=parent1.id).all()
    print(f"Judge requests for Parent1: {len(judge_requests)}")
    
    for req in judge_requests:
        child = User.query.filter_by(id=req.child_id).first()
        print(f"  Request from {child.first_name if child else 'Unknown'}, Accepted: {req.accepted}")
    
    # Test the judge_requests route via test client
    with app.test_client() as client:
        # Simulate login as parent
        with client.session_transaction() as sess:
            sess['user_id'] = parent1.id
        
        # Test the judge_requests route
        response = client.get('/tournaments/judge_requests')
        print(f"\nJudge requests page status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Judge requests page loaded successfully!")
            content = response.get_data(as_text=True)
            if "Judge Requests" in content:
                print("✅ Judge Requests header appears in the page")
            if "Student1" in content:
                print("✅ Child's name appears in the page")
        else:
            print(f"❌ Failed to load judge requests page")
            print(response.get_data(as_text=True)[:500])
