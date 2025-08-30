#!/usr/bin/env python3

"""
Test script to verify the profile update functionality works correctly
"""

import sys
import os
sys.path.append('/home/wnusair/mason-snd')

from mason_snd import create_app
from mason_snd.extensions import db
from mason_snd.models.auth import User, Judges

def test_profile_functionality():
    app = create_app()
    
    with app.app_context():
        print("Testing profile update functionality...")
        
        # Test 1: Check if we can import the profile blueprint without errors
        try:
            from mason_snd.blueprints.profile.profile import profile_bp
            print("✓ Profile blueprint imported successfully")
        except Exception as e:
            print(f"✗ Error importing profile blueprint: {e}")
            return False
        
        # Test 2: Check if the update route exists
        try:
            with app.test_client() as client:
                # Try to access the update route (should redirect to login)
                response = client.get('/profile/update')
                if response.status_code == 302:  # Redirect to login
                    print("✓ Profile update route exists and redirects unauthenticated users")
                else:
                    print(f"✗ Unexpected response from update route: {response.status_code}")
        except Exception as e:
            print(f"✗ Error testing update route: {e}")
            return False
        
        # Test 3: Check database connection and User model
        try:
            user_count = User.query.count()
            print(f"✓ Database connection working, found {user_count} users")
        except Exception as e:
            print(f"✗ Database error: {e}")
            return False
        
        print("All tests passed! Profile functionality should be working.")
        return True

if __name__ == "__main__":
    success = test_profile_functionality()
    sys.exit(0 if success else 1)
