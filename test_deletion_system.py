"""
Test script to demonstrate the deletion utilities.
This script shows how to use the deletion system safely.
"""

from mason_snd import create_app
from mason_snd.extensions import db
from mason_snd.models.auth import User
from mason_snd.models.tournaments import Tournament
from mason_snd.models.events import Event
from mason_snd.models.deletion_utils import (
    get_user_deletion_preview, 
    get_tournament_deletion_preview,
    get_event_deletion_preview,
    delete_user_safely,
    delete_tournament_safely,
    delete_event_safely
)

app = create_app()

def test_deletion_preview():
    """Test the deletion preview functionality"""
    with app.app_context():
        print("=== DELETION SYSTEM TEST ===\n")
        
        # Get some users for testing preview
        users = User.query.limit(3).all()
        print(f"Found {len(users)} users in database")
        
        for user in users:
            print(f"\nPreviewing deletion for: {user.first_name} {user.last_name} (ID: {user.id})")
            preview = get_user_deletion_preview(user.id)
            
            if preview:
                print(f"  Total related records: {preview['total_related']}")
                for category, count in preview['counts'].items():
                    if count > 0:
                        print(f"  - {category}: {count}")
            else:
                print("  No preview available")
        
        # Get some tournaments for testing
        tournaments = Tournament.query.limit(2).all()
        print(f"\nFound {len(tournaments)} tournaments in database")
        
        for tournament in tournaments:
            print(f"\nPreviewing deletion for: {tournament.name} (ID: {tournament.id})")
            preview = get_tournament_deletion_preview(tournament.id)
            
            if preview:
                print(f"  Total related records: {preview['total_related']}")
                for category, count in preview['counts'].items():
                    if count > 0:
                        print(f"  - {category}: {count}")
            else:
                print("  No preview available")
        
        # Get some events for testing
        events = Event.query.limit(3).all()
        print(f"\nFound {len(events)} events in database")
        
        for event in events:
            print(f"\nPreviewing deletion for: {event.event_name} (ID: {event.id})")
            preview = get_event_deletion_preview(event.id)
            
            if preview:
                print(f"  Total related records: {preview['total_related']}")
                print(f"  Owner: {preview['owner_name']}")
                for category, count in preview['counts'].items():
                    if count > 0:
                        print(f"  - {category}: {count}")
            else:
                print("  No preview available")
        
        print("\n=== TEST COMPLETED ===")
        print("The deletion system is ready to use!")
        print("\nTo use the web interface:")
        print("1. Start your Flask app")
        print("2. Log in as an admin (role >= 2)")
        print("3. Go to Admin Dashboard → Deletion Management")
        print("4. Choose Users, Tournaments, or Events")
        print("5. Follow the preview → confirm workflow")

if __name__ == "__main__":
    test_deletion_preview()
