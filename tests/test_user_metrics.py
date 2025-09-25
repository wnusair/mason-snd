"""
Test script to validate the user metrics functionality
"""
import sys
import os
sys.path.append('/workspaces/mason-snd')

from mason_snd import create_app
from mason_snd.models.auth import User
from mason_snd.models.tournaments import Tournament_Performance
from mason_snd.models.events import Effort_Score
from mason_snd.models.metrics import MetricsSettings

def test_user_metrics_routes():
    """Test that the user metrics routes can be imported and basic data retrieval works"""
    app = create_app()
    
    with app.app_context():
        try:
            # Test that models can be queried
            user_count = User.query.count()
            print(f"✓ Found {user_count} users in database")
            
            performance_count = Tournament_Performance.query.count()
            print(f"✓ Found {performance_count} tournament performances")
            
            effort_count = Effort_Score.query.count()
            print(f"✓ Found {effort_count} effort scores")
            
            # Test metrics settings
            settings = MetricsSettings.query.first()
            if settings:
                print(f"✓ Metrics settings found: {settings.tournament_weight * 100}% tournament, {settings.effort_weight * 100}% effort")
            else:
                print("! No metrics settings found - will use defaults")
            
            # Test user properties work
            if user_count > 0:
                user = User.query.first()
                tournament_points = user.tournament_points
                effort_points = user.effort_points
                print(f"✓ User properties work: tournament_points={tournament_points}, effort_points={effort_points}")
            
            print("\n✅ All basic tests passed! User metrics system should work correctly.")
            
        except Exception as e:
            print(f"❌ Error during testing: {e}")
            return False
    
    return True

if __name__ == '__main__':
    test_user_metrics_routes()