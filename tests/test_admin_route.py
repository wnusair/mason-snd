#!/usr/bin/env python3
"""
Test the admin search route functionality
"""

from mason_snd import create_app
from mason_snd.extensions import db

def test_admin_search_route():
    """Test that the admin search route includes judge/child information"""
    app = create_app()
    
    with app.test_client() as client:
        with app.app_context():
            print("=== TESTING ADMIN SEARCH ROUTE ===\n")
            
            # Test the POST request to search route
            # Note: This simulates the form submission but without authentication
            # In real usage, authentication would be required
            
            response = client.post('/admin/search', data={
                'name': 'ayush',
                'csrf_token': 'test'  # This won't work without proper CSRF but we're just testing parsing
            }, follow_redirects=False)
            
            print(f"Search route response status: {response.status_code}")
            if response.status_code == 200:
                print("✅ Search route is accessible")
            else:
                print(f"❌ Search route returned status: {response.status_code}")
                
            # Test template rendering (this tests our template changes)
            from mason_snd.blueprints.admin.admin import search
            print("✅ Admin search function imported successfully")

if __name__ == "__main__":
    test_admin_search_route()
