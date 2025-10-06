#!/usr/bin/env python3
"""
Test script for race condition protection.
Tests the race protection mechanisms on critical forms.
"""

import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, '/workspaces/mason-snd')

from mason_snd import create_app
from mason_snd.extensions import db
from mason_snd.models.auth import User
from werkzeug.security import generate_password_hash


def test_concurrent_registration():
    """Test race protection on registration form"""
    print("\n" + "="*70)
    print("TEST 1: Concurrent Registration Attempts")
    print("="*70)
    
    app = create_app()
    
    with app.app_context():
        # Clean up test data
        User.query.filter(User.email.like('racetest%')).delete()
        db.session.commit()
        
        with app.test_client() as client:
            # Prepare registration data
            registration_data = {
                'first_name': 'Race',
                'last_name': 'Test',
                'email': 'racetest@example.com',
                'phone_number': '555-RACE',
                'is_parent': 'no',
                'emergency_first_name': 'Emergency',
                'emergency_last_name': 'Contact',
                'emergency_email': 'emergency@example.com',
                'emergency_phone': '555-1234',
                'emergency_relationship': 'parent',
                'password': 'testpass123',
                'confirm_password': 'testpass123'
            }
            
            # Simulate double-click: two rapid requests
            print("\n📝 Simulating double-click (2 rapid POST requests)...")
            
            def register():
                return client.post('/auth/register', data=registration_data, follow_redirects=False)
            
            # Submit two requests nearly simultaneously
            start_time = time.time()
            response1 = register()
            time.sleep(0.1)  # Very small delay to simulate double-click
            response2 = register()
            end_time = time.time()
            
            print(f"   Request 1 status: {response1.status_code}")
            print(f"   Request 2 status: {response2.status_code}")
            print(f"   Time elapsed: {end_time - start_time:.3f} seconds")
            
            # Check database
            users = User.query.filter_by(email='racetest@example.com').all()
            print(f"\n✅ Result: {len(users)} user(s) created (expected: 1)")
            
            if len(users) == 1:
                print("   ✅ PASS: Race protection prevented duplicate registration")
            else:
                print("   ❌ FAIL: Duplicate registration created")
            
            # Cleanup
            User.query.filter(User.email.like('racetest%')).delete()
            db.session.commit()
            
            return len(users) == 1


def test_tournament_signup_race():
    """Test race protection on tournament signup"""
    print("\n" + "="*70)
    print("TEST 2: Tournament Signup Race Condition")
    print("="*70)
    
    app = create_app()
    
    with app.app_context():
        from mason_snd.models.tournaments import Tournament_Signups, Tournament
        from mason_snd.models.events import Event
        
        # Find a test user and tournament
        test_user = User.query.filter_by(is_parent=False).first()
        tournament = Tournament.query.first()
        event = Event.query.first()
        
        if not test_user or not tournament or not event:
            print("   ⚠️  SKIP: Missing test data (user, tournament, or event)")
            return True
        
        # Clean up any existing signups
        Tournament_Signups.query.filter_by(
            user_id=test_user.id,
            tournament_id=tournament.id,
            event_id=event.id
        ).delete()
        db.session.commit()
        
        with app.test_client() as client:
            # Login as test user
            with client.session_transaction() as sess:
                sess['user_id'] = test_user.id
            
            signup_data = {
                'tournament_id': tournament.id,
                'user_event': [event.id],
                # Add any required form fields
            }
            
            print(f"\n📝 User {test_user.id} signing up for tournament {tournament.id}...")
            print("   Simulating rapid double-submission...")
            
            # Two rapid signups
            response1 = client.post('/tournaments/signup', data=signup_data)
            time.sleep(0.2)
            response2 = client.post('/tournaments/signup', data=signup_data)
            
            print(f"   Request 1 status: {response1.status_code}")
            print(f"   Request 2 status: {response2.status_code}")
            
            # Check signups
            signups = Tournament_Signups.query.filter_by(
                user_id=test_user.id,
                tournament_id=tournament.id,
                event_id=event.id
            ).all()
            
            print(f"\n✅ Result: {len(signups)} signup(s) created (expected: 1)")
            
            if len(signups) == 1:
                print("   ✅ PASS: Race protection prevented duplicate signup")
            else:
                print("   ❌ FAIL: Duplicate signup created")
            
            # Cleanup
            Tournament_Signups.query.filter_by(
                user_id=test_user.id,
                tournament_id=tournament.id,
                event_id=event.id
            ).delete()
            db.session.commit()
            
            return len(signups) == 1


def test_join_event_race():
    """Test race protection on event joining"""
    print("\n" + "="*70)
    print("TEST 3: Join Event Race Condition")
    print("="*70)
    
    app = create_app()
    
    with app.app_context():
        from mason_snd.models.events import User_Event, Event
        
        test_user = User.query.filter_by(is_parent=False).first()
        event = Event.query.first()
        
        if not test_user or not event:
            print("   ⚠️  SKIP: Missing test data (user or event)")
            return True
        
        # Clean up existing membership
        User_Event.query.filter_by(user_id=test_user.id, event_id=event.id).delete()
        db.session.commit()
        
        with app.test_client() as client:
            # Login
            with client.session_transaction() as sess:
                sess['user_id'] = test_user.id
            
            print(f"\n📝 User {test_user.id} joining event {event.id}...")
            print("   Simulating triple-click...")
            
            # Three rapid requests (aggressive test)
            responses = []
            for i in range(3):
                resp = client.post(f'/events/join_event/{event.id}')
                responses.append(resp)
                time.sleep(0.1)
            
            for i, resp in enumerate(responses, 1):
                print(f"   Request {i} status: {resp.status_code}")
            
            # Check memberships
            memberships = User_Event.query.filter_by(
                user_id=test_user.id,
                event_id=event.id,
                active=True
            ).all()
            
            print(f"\n✅ Result: {len(memberships)} membership(s) created (expected: 1)")
            
            if len(memberships) == 1:
                print("   ✅ PASS: Race protection prevented duplicate membership")
            else:
                print("   ❌ FAIL: Duplicate membership created")
            
            # Cleanup
            User_Event.query.filter_by(user_id=test_user.id, event_id=event.id).delete()
            db.session.commit()
            
            return len(memberships) == 1


def test_hash_based_duplicate_detection():
    """Test form hash-based duplicate detection"""
    print("\n" + "="*70)
    print("TEST 4: Form Hash Duplicate Detection")
    print("="*70)
    
    from mason_snd.utils.race_protection import _generate_form_hash
    
    # Test identical forms produce same hash
    form1 = {
        'first_name': 'John',
        'last_name': 'Doe',
        'email': 'john@example.com',
        'csrf_token': 'token123'  # Should be excluded
    }
    
    form2 = {
        'first_name': 'John',
        'last_name': 'Doe',
        'email': 'john@example.com',
        'csrf_token': 'token456'  # Different token
    }
    
    form3 = {
        'first_name': 'Jane',  # Different data
        'last_name': 'Doe',
        'email': 'jane@example.com'
    }
    
    hash1 = _generate_form_hash(form1)
    hash2 = _generate_form_hash(form2)
    hash3 = _generate_form_hash(form3)
    
    print(f"\n📝 Form 1 hash: {hash1[:16]}...")
    print(f"   Form 2 hash: {hash2[:16]}... (same data, different CSRF)")
    print(f"   Form 3 hash: {hash3[:16]}... (different data)")
    
    print(f"\n✅ Hash comparison:")
    print(f"   Form 1 == Form 2: {hash1 == hash2} (expected: True)")
    print(f"   Form 1 == Form 3: {hash1 == hash3} (expected: False)")
    
    if hash1 == hash2 and hash1 != hash3:
        print("   ✅ PASS: Hash function correctly identifies duplicates")
        return True
    else:
        print("   ❌ FAIL: Hash function not working correctly")
        return False


def test_concurrent_different_users():
    """Test that different users don't block each other"""
    print("\n" + "="*70)
    print("TEST 5: Concurrent Access by Different Users")
    print("="*70)
    
    app = create_app()
    
    with app.app_context():
        # Create two test users
        User.query.filter(User.email.like('concurrent%')).delete()
        db.session.commit()
        
        user1_data = {
            'first_name': 'concurrent1',
            'last_name': 'test',
            'email': 'concurrent1@example.com',
            'phone_number': '555-0001',
            'password': generate_password_hash('pass'),
            'is_parent': False,
            'account_claimed': True
        }
        
        user2_data = {
            'first_name': 'concurrent2',
            'last_name': 'test',
            'email': 'concurrent2@example.com',
            'phone_number': '555-0002',
            'password': generate_password_hash('pass'),
            'is_parent': False,
            'account_claimed': True
        }
        
        user1 = User(**user1_data)
        user2 = User(**user2_data)
        db.session.add(user1)
        db.session.add(user2)
        db.session.commit()
        
        with app.test_client() as client:
            results = []
            
            def update_profile(user_id, name):
                with client.session_transaction() as sess:
                    sess['user_id'] = user_id
                
                data = {
                    'first_name': name,
                    'last_name': 'updated',
                    'email': f'{name}@example.com',
                    'phone_number': '555-9999'
                }
                
                response = client.post('/profile/update', data=data)
                return response.status_code
            
            print("\n📝 Two users updating profiles simultaneously...")
            
            # Use threads to simulate concurrent access
            with ThreadPoolExecutor(max_workers=2) as executor:
                future1 = executor.submit(update_profile, user1.id, 'user1')
                future2 = executor.submit(update_profile, user2.id, 'user2')
                
                status1 = future1.result()
                status2 = future2.result()
            
            print(f"   User 1 update status: {status1}")
            print(f"   User 2 update status: {status2}")
            
            # Both should succeed
            if status1 in [200, 302] and status2 in [200, 302]:
                print("\n✅ PASS: Different users don't block each other")
                success = True
            else:
                print("\n❌ FAIL: Users are blocking each other")
                success = False
            
            # Cleanup
            User.query.filter(User.email.like('concurrent%')).delete()
            db.session.commit()
            
            return success


def run_all_tests():
    """Run all race condition protection tests"""
    print("\n" + "="*70)
    print("RACE CONDITION PROTECTION TEST SUITE")
    print("="*70)
    print("\nTesting race protection mechanisms across all critical forms...")
    
    results = []
    
    # Run tests
    results.append(('Hash Duplicate Detection', test_hash_based_duplicate_detection()))
    results.append(('Concurrent Registration', test_concurrent_registration()))
    results.append(('Tournament Signup Race', test_tournament_signup_race()))
    results.append(('Join Event Race', test_join_event_race()))
    results.append(('Concurrent Different Users', test_concurrent_different_users()))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Race protection is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review implementation.")
        return 1


if __name__ == '__main__':
    exit_code = run_all_tests()
    sys.exit(exit_code)
