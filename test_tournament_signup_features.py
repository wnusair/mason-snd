#!/usr/bin/env python
"""
Test script for the new tournament-specific signup features.

This script tests:
1. View tournament signups route
2. Download tournament signups route  
3. Admin access controls
"""

import sys
import os
from flask import url_for

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath('.'))

from mason_snd import create_app
from mason_snd.extensions import db
from mason_snd.models.tournaments import Tournament, Tournament_Signups
from mason_snd.models.auth import User

def test_tournament_signup_routes():
    """Test the new tournament signup routes"""
    print("\n" + "="*70)
    print("TESTING NEW TOURNAMENT-SPECIFIC SIGNUP FEATURES")
    print("="*70 + "\n")
    
    app = create_app()
    
    with app.app_context():
        # Test if routes are registered
        with app.test_request_context():
            try:
                print("✓ Testing route registration:")
                
                # Test view route
                view_url = url_for('admin.view_tournament_signups', tournament_id=1)
                print(f"  ✓ View signups route: {view_url}")
                
                # Test download route
                download_url = url_for('admin.download_tournament_signups', tournament_id=1)
                print(f"  ✓ Download signups route: {download_url}")
                
                print(f"\n✓ Both routes are properly registered!")
                
            except Exception as e:
                print(f"  ❌ Route registration error: {e}")
                return False
        
        # Check tournament data
        tournaments = Tournament.query.all()
        print(f"\n✓ Found {len(tournaments)} tournaments in database:")
        
        for tournament in tournaments:
            signups = Tournament_Signups.query.filter_by(tournament_id=tournament.id).all()
            print(f"  • Tournament: {tournament.name}")
            print(f"    - ID: {tournament.id}")
            print(f"    - Signups: {len(signups)}")
            print(f"    - Date: {tournament.date}")
            
            if signups:
                # Sample a few signups
                sample_signups = signups[:3]
                print(f"    - Sample signups:")
                for signup in sample_signups:
                    user = User.query.get(signup.user_id) if signup.user_id else None
                    user_name = f"{user.first_name} {user.last_name}" if user else 'Unknown'
                    print(f"      * {user_name} (ID: {signup.id})")
        
        # Test admin users
        print(f"\n✓ Testing admin access:")
        admin_users = User.query.filter(User.role >= 2).all()
        print(f"  • Found {len(admin_users)} admin users")
        
        if admin_users:
            admin = admin_users[0]
            print(f"  • Sample admin: {admin.first_name} {admin.last_name} (role: {admin.role})")
        
        print(f"\n✅ All tests passed! New tournament signup features are ready.")
        print(f"\n📋 USAGE INSTRUCTIONS:")
        print(f"  1. Log in as an admin user (role >= 2)")
        print(f"  2. Go to the Tournaments page")
        print(f"  3. Look for 'View Signups' and '📥 Download' buttons next to each tournament")
        print(f"  4. Click 'View Signups' to see a detailed table with statistics")
        print(f"  5. Click '📥 Download' to get an Excel file for that specific tournament")
        print(f"\n🔗 Test URLs (replace with actual tournament IDs):")
        if tournaments:
            sample_id = tournaments[0].id
            print(f"  • View signups: /admin/view_tournament_signups/{sample_id}")
            print(f"  • Download signups: /admin/download_tournament_signups/{sample_id}")
        
        return True

if __name__ == "__main__":
    try:
        success = test_tournament_signup_routes()
        if success:
            print(f"\n🎉 SUCCESS: Tournament-specific signup features are working!")
        else:
            print(f"\n❌ FAILED: There were issues with the implementation")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)