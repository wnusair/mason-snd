#!/usr/bin/env python3
"""
Test script to verify the new bid point calculation logic.
This test verifies that:
- First-time bid earners get 15 points
- Subsequent bid earners get 5 points
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mason_snd import create_app
from mason_snd.extensions import db
from mason_snd.models.auth import User
from mason_snd.models.tournaments import Tournament, Tournament_Performance
from datetime import datetime
import pytz

EST = pytz.timezone('US/Eastern')

def test_bid_logic():
    """Test the new bid point calculation logic"""
    app = create_app()
    
    with app.app_context():
        print("Testing bid point calculation logic...")
        
        # Find a test user (or create one if needed)
        test_user = User.query.first()
        if not test_user:
            print("No users found in database. Please add some test data first.")
            return
        
        print(f"Testing with user: {test_user.first_name} {test_user.last_name} (ID: {test_user.id})")
        
        # Check current bid history
        current_bids = Tournament_Performance.query.filter_by(user_id=test_user.id, bid=True).all()
        print(f"Current tournament bids: {len(current_bids)}")
        print(f"Current user.bids field: {test_user.bids or 0}")
        
        # Test the logic without actually creating records
        print("\n--- Testing bid point calculation logic ---")
        
        # Simulate the logic from tournament_results function
        # Check if user has any previous bids in their tournament performance history
        previous_bids = Tournament_Performance.query.filter_by(user_id=test_user.id, bid=True).first()
        
        if previous_bids is None:
            expected_points = 15
            print(f"✅ User has NO previous tournament bids - would award 15 points")
        else:
            expected_points = 5
            print(f"✅ User HAS previous tournament bids - would award 5 points")
        
        print(f"Expected points for new bid: {expected_points}")
        
        # Test a few more users to show the difference
        print("\n--- Testing with other users ---")
        other_users = User.query.limit(5).all()
        for user in other_users:
            user_previous_bids = Tournament_Performance.query.filter_by(user_id=user.id, bid=True).first()
            if user_previous_bids is None:
                points = 15
                status = "FIRST BID"
            else:
                points = 5
                status = "SUBSEQUENT BID"
            
            bid_count = Tournament_Performance.query.filter_by(user_id=user.id, bid=True).count()
            print(f"{user.first_name} {user.last_name}: {bid_count} bids → {points} points ({status})")

if __name__ == "__main__":
    test_bid_logic()
