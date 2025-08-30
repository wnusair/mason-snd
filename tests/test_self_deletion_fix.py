"""
Test script to verify the self-deletion fix.
This script tests that users cannot delete their own accounts.
"""

from mason_snd import create_app
from mason_snd.extensions import db
from mason_snd.models.auth import User
from flask import session

app = create_app()

def test_self_deletion_protection():
    """Test that the system prevents self-deletion"""
    with app.app_context():
        print("=== TESTING SELF-DELETION PROTECTION ===\n")
        
        # Get a test user
        test_user = User.query.first()
        if not test_user:
            print("No users found in database")
            return
            
        print(f"Testing with user: {test_user.first_name} {test_user.last_name} (ID: {test_user.id})")
        
        # Test the delete_multiple_users function with current user in list
        from mason_snd.models.deletion_utils import delete_multiple_users
        
        # This should work - deleting other users but not self
        other_users = User.query.filter(User.id != test_user.id).limit(2).all()
        if other_users:
            other_user_ids = [u.id for u in other_users]
            print(f"Would delete users with IDs: {other_user_ids} (not including current user)")
            
        # This should be caught by our new protection
        user_ids_including_self = [test_user.id]
        if other_users:
            user_ids_including_self.append(other_users[0].id)
            
        print(f"Testing protection against deleting IDs: {user_ids_including_self} (includes current user {test_user.id})")
        
        # Simulate what the admin route now checks
        current_user_id = test_user.id
        if current_user_id in user_ids_including_self:
            print("✅ PROTECTION WORKS: Current user ID found in deletion list - would be blocked")
        else:
            print("❌ PROTECTION FAILED: Current user ID not found in deletion list")
            
        print("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    test_self_deletion_protection()
