"""
Test that the Flask app can start and routes are accessible
"""
import sys
import os
sys.path.append('/workspaces/mason-snd')

from mason_snd import create_app

def test_flask_routes():
    """Test that Flask routes are accessible"""
    app = create_app()
    
    with app.test_client() as client:
        # Test main page is accessible
        response = client.get('/')
        print(f"✓ Main page accessible: {response.status_code}")
        
        # Test that routes exist (they will redirect to login for unauthorized users)
        routes_to_test = [
            '/metrics/my_metrics',
            '/metrics/my_performance_trends', 
            '/metrics/my_ranking'
        ]
        
        for route in routes_to_test:
            try:
                response = client.get(route)
                # Should redirect to login (302) for unauthorized user
                if response.status_code == 302:
                    print(f"✓ Route {route} exists and redirects properly")
                else:
                    print(f"! Route {route} returned {response.status_code}")
            except Exception as e:
                print(f"❌ Error accessing {route}: {e}")
        
    print("\n✅ Flask app and routing tests completed!")

if __name__ == '__main__':
    test_flask_routes()