#!/usr/bin/env python3
"""
Script to test the drop penalty functionality
"""

from mason_snd import create_app
from mason_snd.extensions import db
from mason_snd.models.auth import User
import random

def test_drop_penalty():
    """Test the drop penalty functionality"""
    app = create_app()
    
    with app.app_context():
        try:
            # Find a few test users
            users = User.query.limit(5).all()
            
            if not users:
                print("No users found in database")
                return
                
            print("Current user drops:")
            for user in users:
                print(f"  {user.first_name} {user.last_name}: {user.drops} drops")
            
            # Add a drop to the first user
            if users:
                test_user = users[0]
                original_drops = test_user.drops
                test_user.drops += 1
                db.session.commit()
                
                print(f"\nAdded drop penalty to {test_user.first_name} {test_user.last_name}")
                print(f"  Drops: {original_drops} -> {test_user.drops}")
            
        except Exception as e:
            print(f"Error testing drop penalty: {e}")

if __name__ == "__main__":
    test_drop_penalty()
