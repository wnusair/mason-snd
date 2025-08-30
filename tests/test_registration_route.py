#!/usr/bin/env python3
"""
Test registration route with ghost account claiming
This tests the actual registration logic without CSRF
"""

import os
import sys
sys.path.insert(0, '/home/wnusair/mason-snd')

from flask import Flask
from mason_snd import create_app
from mason_snd.extensions import db
from mason_snd.models.auth import User, Judges

def test_registration_route_ghost_claiming():
    """Test that the registration route allows ghost account claiming"""
    
    app = create_app()
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
    
    with app.test_client() as client:
        with app.app_context():
            print("=== TESTING REGISTRATION ROUTE WITH GHOST CLAIMING ===\n")
            
            # Clear test data
            print("Clearing test data...")
            User.query.filter(User.first_name.in_(['routetest', 'routechild'])).delete(synchronize_session=False)
            db.session.commit()
            
            # Step 1: Create a ghost parent account manually (simulating child registration)
            print("📝 STEP 1: Creating ghost parent account")
            
            ghost_parent = User(
                first_name='routetest',
                last_name='parent',
                email='routetest@example.com',
                phone_number='555-9001',
                is_parent=True,
                child_first_name='routechild',
                child_last_name='test',
                account_claimed=False  # This is a ghost account
            )
            
            db.session.add(ghost_parent)
            db.session.commit()
            
            print(f"   ✅ Ghost parent created: ID={ghost_parent.id}, email={ghost_parent.email}")
            print(f"   ✅ Account claimed: {ghost_parent.account_claimed}")
            
            # Step 2: Try to register as the ghost parent using the registration route
            print(f"\n📝 STEP 2: Attempting to register as ghost parent via route")
            
            registration_data = {
                'first_name': 'RouteTest',
                'last_name': 'Parent',
                'email': 'routetest@example.com',  # Same email as ghost
                'phone_number': '555-9001',
                'is_parent': 'yes',
                'child_first_name': 'RouteChild',
                'child_last_name': 'Test',
                'password': 'testpassword123',
                'confirm_password': 'testpassword123'
            }
            
            response = client.post('/auth/register', data=registration_data, follow_redirects=True)
            
            print(f"   📊 Response status: {response.status_code}")
            
            if response.status_code == 200:
                # Check if registration was successful by looking at response or database
                updated_parent = User.query.filter_by(first_name='routetest', last_name='parent').first()
                
                if updated_parent:
                    print(f"   ✅ Parent account found: ID={updated_parent.id}")
                    print(f"   ✅ Account claimed: {updated_parent.account_claimed}")
                    print(f"   ✅ Same ID as ghost: {updated_parent.id == ghost_parent.id}")
                    print(f"   ✅ Password set: {updated_parent.password is not None}")
                    
                    if updated_parent.account_claimed:
                        print("   🎉 SUCCESS: Ghost account was successfully claimed!")
                    else:
                        print("   ❌ FAILED: Account was not claimed")
                else:
                    print("   ❌ FAILED: Parent account not found")
            else:
                print(f"   ❌ Registration failed with status {response.status_code}")
                # Try to see error message
                if b'email address already exists' in response.data:
                    print("   💡 Error: Email already exists (this is the bug we're fixing)")
                else:
                    content = response.data.decode('utf-8')
                    print(f"   💡 Response content preview: {content[:200]}...")
            
            # Step 3: Try registering a different person with the same email (should fail)
            print(f"\n📝 STEP 3: Different person tries same email")
            
            different_person_data = {
                'first_name': 'Different',
                'last_name': 'Person', 
                'email': 'routetest@example.com',  # Same email
                'phone_number': '555-9999',
                'is_parent': 'yes',
                'child_first_name': 'Other',
                'child_last_name': 'Child',
                'password': 'differentpass123',
                'confirm_password': 'differentpass123'
            }
            
            response2 = client.post('/auth/register', data=different_person_data, follow_redirects=True)
            
            print(f"   📊 Response status: {response2.status_code}")
            
            if b'email address already exists' in response2.data:
                print("   ✅ SUCCESS: Different person blocked from using same email")
            else:
                print("   ❌ FAILED: Different person was not blocked")
            
            # Check that no new user was created
            different_user = User.query.filter_by(first_name='different', last_name='person').first()
            print(f"   ✅ Different user created: {different_user is not None} (should be False)")
            
            print("\n🎉 REGISTRATION ROUTE TEST COMPLETED!")

if __name__ == '__main__':
    test_registration_route_ghost_claiming()
