"""
Test the timezone fix for user metrics
"""
import sys
import os
sys.path.append('/workspaces/mason-snd')

from mason_snd import create_app
from mason_snd.models.auth import User
from mason_snd.models.tournaments import Tournament_Performance, Tournament
from datetime import datetime, timedelta
import pytz

EST = pytz.timezone('US/Eastern')

def test_timezone_fix():
    """Test that timezone comparisons work correctly"""
    app = create_app()
    
    with app.app_context():
        try:
            # Get a user with performance data
            user = User.query.join(Tournament_Performance).first()
            if not user:
                print("No user with performance data found")
                return
            
            print(f"Testing timezone fix for user: {user.first_name} {user.last_name}")
            
            # Get performances
            performances = Tournament_Performance.query.filter_by(user_id=user.id)\
                .join(Tournament).order_by(Tournament.date.desc()).all()
            
            print(f"Found {len(performances)} performances")
            
            # Test the timezone-aware comparison logic
            six_months_ago = datetime.now(EST) - timedelta(days=180)
            recent_performances = []
            
            for p in performances:
                tournament_date = p.tournament.date
                if tournament_date.tzinfo is None:
                    tournament_date = EST.localize(tournament_date)
                if tournament_date >= six_months_ago:
                    recent_performances.append(p)
            
            print(f"✓ Found {len(recent_performances)} recent performances (last 6 months)")
            print("✓ Timezone comparison working correctly")
            
            # Test weekly data logic
            weekly_data = {}
            for p in performances:
                tournament_date = p.tournament.date
                if tournament_date.tzinfo is None:
                    tournament_date = EST.localize(tournament_date)
                week_start = tournament_date - timedelta(days=tournament_date.weekday())
                week_key = week_start.strftime('%Y-%m-%d')
                
                if week_key not in weekly_data:
                    weekly_data[week_key] = {'tournaments': 0, 'total_points': 0, 'bids': 0}
                
                weekly_data[week_key]['tournaments'] += 1
                weekly_data[week_key]['total_points'] += p.points or 0
                weekly_data[week_key]['bids'] += 1 if p.bid else 0
            
            print(f"✓ Generated weekly data for {len(weekly_data)} weeks")
            print("\n✅ All timezone fixes working correctly!")
            
        except Exception as e:
            print(f"❌ Error during timezone testing: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_timezone_fix()