from mason_snd import create_app
from mason_snd.extensions import db
from mason_snd.models.auth import User
from werkzeug.security import check_password_hash

app = create_app()

with app.app_context():
    # Test the view_tournament route via test client
    with app.test_client() as client:
        # Login as admin
        admin = User.query.filter_by(email='admin@test.com').first()
        print(f"Admin found: {admin.first_name if admin else 'None'}")
        print(f"Admin role: {admin.role if admin else 'None'}")
        
        # Simulate login by setting session
        with client.session_transaction() as sess:
            sess['user_id'] = admin.id
        
        # Test the view_tournament route
        response = client.get('/rosters/view_tournament/1')
        print(f"\nResponse status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ View tournament page loaded successfully!")
            # Check if the response contains expected content
            content = response.get_data(as_text=True)
            if "Tournament Roster: princeton" in content:
                print("✅ Tournament name appears in the page")
            if "Judges" in content:
                print("✅ Judges section appears in the page")
            if "Rank View" in content:
                print("✅ Rank View section appears in the page")
            if "Event View" in content:
                print("✅ Event View section appears in the page")
        else:
            print(f"❌ Failed to load view tournament page: {response.status_code}")
            print(response.get_data(as_text=True)[:500])
