#!/usr/bin/env python3
"""
Test script for tournament results functionality
"""

import sys
import os
from datetime import datetime, timedelta
import pytz

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath('.'))

from mason_snd import create_app
from mason_snd.extensions import db
from mason_snd.models.tournaments import Tournament
from mason_snd.models.auth import User

EST = pytz.timezone('US/Eastern')

def test_tournament_results():
    try:
        app = create_app()
        
        with app.app_context():
            # Check if we have any tournaments
            tournaments = Tournament.query.all()
            print(f"Found {len(tournaments)} tournaments in database")
            
            for tournament in tournaments:
                now = datetime.now(EST)
                is_past = tournament.date < now
                results_submitted = tournament.results_submitted
                
                print(f"\nTournament: {tournament.name}")
                print(f"Date: {tournament.date}")
                print(f"Is Past: {is_past}")
                print(f"Results Submitted: {results_submitted}")
                
                if is_past and not results_submitted:
                    print("✓ This tournament should show 'Submit Results' button")
                elif is_past and results_submitted:
                    print("✓ This tournament should show 'View Results' button")
                elif not is_past:
                    print("✓ This tournament should show no results buttons (upcoming)")
            
            # Test creating a past tournament for demonstration
            past_date = datetime.now(EST) - timedelta(days=30)
            test_tournament = Tournament.query.filter_by(name="Test Past Tournament").first()
            
            if not test_tournament:
                test_tournament = Tournament(
                    name="Test Past Tournament",
                    date=past_date,
                    address="123 Test St, Test City",
                    signup_deadline=past_date - timedelta(days=7),
                    performance_deadline=past_date + timedelta(days=1),
                    results_submitted=False
                )
                db.session.add(test_tournament)
                db.session.commit()
                print(f"\n✓ Created test past tournament: {test_tournament.name}")
                print("  This should appear in 'Past Tournaments' section with 'Submit Results' button")
            else:
                print(f"\n✓ Test tournament already exists: {test_tournament.name}")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_tournament_results()
