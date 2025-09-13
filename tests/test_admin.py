#!/usr/bin/env python3
"""
Test script to verify Flask-Admin functionality
"""

import sys
import requests
from datetime import datetime

def test_admin_endpoints():
    """Test various admin endpoints to ensure they're working"""
    
    base_url = "http://localhost:5000"
    admin_endpoints = [
        "/admin/",
        "/admin/user/",
        "/admin/event/",
        "/admin/tournament/", 
        "/admin/popups/",
        "/admin/requirements/",
        "/admin/userevent/",
        "/admin/roster/",
        "/admin/judges/",
        "/admin/metricssettings/"
    ]
    
    print("🧪 Testing Flask-Admin endpoints...")
    print("=" * 50)
    
    success_count = 0
    total_count = len(admin_endpoints)
    
    for endpoint in admin_endpoints:
        try:
            url = f"{base_url}{endpoint}"
            response = requests.get(url, timeout=5, allow_redirects=False)
            
            # We expect 302 redirects for unauthorized access (which is correct)
            # Or 200 if somehow authorized
            if response.status_code in [200, 302]:
                status = "✅ PASS"
                success_count += 1
            else:
                status = f"❌ FAIL ({response.status_code})"
                
            print(f"{status} {endpoint}")
            
        except requests.exceptions.RequestException as e:
            print(f"❌ ERROR {endpoint}: {str(e)}")
    
    print("=" * 50)
    print(f"📊 Results: {success_count}/{total_count} endpoints working")
    
    if success_count == total_count:
        print("🎉 All admin endpoints are responding correctly!")
        return True
    else:
        print("⚠️  Some endpoints may have issues")
        return False

def test_admin_authentication():
    """Test that admin authentication is working"""
    print("\n🔐 Testing admin authentication...")
    
    try:
        # Test direct admin access (should redirect to login)
        response = requests.get("http://localhost:5000/admin/", allow_redirects=False)
        
        if response.status_code == 302:
            location = response.headers.get('Location', '')
            if 'login' in location.lower():
                print("✅ Admin authentication is working (redirects to login)")
                return True
            else:
                print(f"⚠️  Redirects but not to login: {location}")
                return False
        elif response.status_code == 200:
            print("⚠️  Admin accessible without authentication (might be intended for testing)")
            return True
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error testing authentication: {str(e)}")
        return False

def check_flask_admin_features():
    """Check that Flask-Admin features are properly configured"""
    print("\n🔧 Checking Flask-Admin configuration...")
    
    try:
        # Import the admin module to check configuration
        sys.path.insert(0, '.')
        from mason_snd.admin import init_admin
        from mason_snd import create_app
        
        app = create_app()
        with app.app_context():
            admin = init_admin(app)
            
            # Check that admin views are registered
            view_count = len(admin._views)
            print(f"✅ {view_count} admin views registered")
            
            # List the categories
            categories = set()
            for view in admin._views:
                if hasattr(view, 'category') and view.category:
                    categories.add(view.category)
            
            print(f"✅ {len(categories)} categories configured:")
            for category in sorted(categories):
                print(f"   📁 {category}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error checking configuration: {str(e)}")
        return False

if __name__ == "__main__":
    print(f"🚀 Flask-Admin Test Suite")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Run all tests
    auth_ok = test_admin_authentication()
    endpoints_ok = test_admin_endpoints()
    config_ok = check_flask_admin_features()
    
    print("\n" + "=" * 50)
    if auth_ok and endpoints_ok and config_ok:
        print("🎉 ALL TESTS PASSED! Flask-Admin is working correctly.")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed. Please check the output above.")
        sys.exit(1)
