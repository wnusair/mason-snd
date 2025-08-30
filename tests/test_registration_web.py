#!/usr/bin/env python3
"""
Web test simulation for registration scenarios
"""

import os
import sys
sys.path.insert(0, '/home/wnusair/mason-snd')

from mason_snd import create_app
from mason_snd.extensions import db
from mason_snd.models.auth import User, Judges

def simulate_registration_scenarios():
    """Simulate actual registration form submissions"""
    
    app = create_app()
    
    with app.test_client() as client:
        with app.app_context():
            # Clear test data
            print("Clearing test data...")
            Judges.query.filter(
                (Judges.judge.has(first_name='demo')) |
                (Judges.child.has(first_name='demo'))
            ).delete(synchronize_session=False)
            
            User.query.filter(
                User.first_name.like('demo%')
            ).delete(synchronize_session=False)
            
            db.session.commit()
            
            print("\n=== Scenario 1: Parent registers for child ===")
            
            # Parent registration
            parent_form_data = {
                'first_name': 'DemoParent',
                'last_name': 'Johnson',
                'email': 'demoparent@example.com',
                'phone_number': '555-1111',
                'is_parent': 'yes',
                'child_first_name': 'DemoChild',
                'child_last_name': 'Johnson',
                'password': 'password123',
                'confirm_password': 'password123'
            }
            
            response = client.post('/auth/register', data=parent_form_data, follow_redirects=True)
            print(f"Parent registration status: {response.status_code}")
            
            # Check database state
            parent = User.query.filter_by(first_name='demoparent', last_name='johnson', is_parent=True).first()
            child = User.query.filter_by(first_name='demochild', last_name='johnson', is_parent=False).first()
            
            print(f"Parent created: ID={parent.id if parent else 'None'}, claimed={parent.account_claimed if parent else 'None'}")
            print(f"Child created: ID={child.id if child else 'None'}, claimed={child.account_claimed if child else 'None'}")
            
            if parent and child:
                judge_rel = Judges.query.filter_by(judge_id=parent.id, child_id=child.id).first()
                print(f"Judge relationship created: {judge_rel is not None}")
            
            print("\n=== Scenario 2: Another parent registers for same child ===")
            
            # Second parent registration for same child
            parent2_form_data = {
                'first_name': 'DemoParent2',
                'last_name': 'Smith',
                'email': 'demoparent2@example.com',
                'phone_number': '555-2222',
                'is_parent': 'yes',
                'child_first_name': 'DemoChild',
                'child_last_name': 'Johnson',
                'password': 'password456',
                'confirm_password': 'password456'
            }
            
            response = client.post('/auth/register', data=parent2_form_data, follow_redirects=True)
            print(f"Second parent registration status: {response.status_code}")
            
            # Check database state
            parent2 = User.query.filter_by(first_name='demoparent2', last_name='smith', is_parent=True).first()
            child_same = User.query.filter_by(first_name='demochild', last_name='johnson', is_parent=False).first()
            
            print(f"Second parent created: ID={parent2.id if parent2 else 'None'}")
            print(f"Child reused: ID={child_same.id if child_same else 'None'}, same as before={child_same.id == child.id if child_same and child else 'N/A'}")
            
            if parent2 and child_same:
                judge_rel2 = Judges.query.filter_by(judge_id=parent2.id, child_id=child_same.id).first()
                print(f"Second judge relationship created: {judge_rel2 is not None}")
            
            # Count total relationships for the child
            total_relationships = Judges.query.filter_by(child_id=child.id).count() if child else 0
            print(f"Total judge relationships for child: {total_relationships}")
            
            print("\n=== Scenario 3: Child registers and claims account ===")
            
            # Child registration
            child_form_data = {
                'first_name': 'DemoChild',
                'last_name': 'Johnson',
                'email': 'demochild@student.example.com',
                'phone_number': '555-3333',
                'is_parent': 'no',
                'emergency_first_name': 'DemoParent',
                'emergency_last_name': 'Johnson',
                'emergency_email': 'demoparent@example.com',
                'emergency_phone': '555-1111',
                'emergency_relationship': 'parent',
                'password': 'studentpass',
                'confirm_password': 'studentpass'
            }
            
            response = client.post('/auth/register', data=child_form_data, follow_redirects=True)
            print(f"Child registration status: {response.status_code}")
            
            # Check if child account was updated
            child_updated = User.query.filter_by(first_name='demochild', last_name='johnson', is_parent=False).first()
            print(f"Child account updated: email={child_updated.email if child_updated else 'None'}")
            print(f"Child claimed status: {child_updated.account_claimed if child_updated else 'None'}")
            
            print("\n=== Scenario 4: Try duplicate email registration ===")
            
            # Try to register with existing email
            duplicate_email_data = {
                'first_name': 'Different',
                'last_name': 'Person',
                'email': 'demoparent@example.com',  # Same email as first parent
                'phone_number': '555-4444',
                'is_parent': 'yes',
                'child_first_name': 'SomeOther',
                'child_last_name': 'Child',
                'password': 'password789',
                'confirm_password': 'password789'
            }
            
            response = client.post('/auth/register', data=duplicate_email_data, follow_redirects=False)
            print(f"Duplicate email registration status: {response.status_code}")
            
            # Check if new user was NOT created
            duplicate_user = User.query.filter_by(first_name='different', last_name='person').first()
            print(f"Duplicate user created: {duplicate_user is not None}")
            
            print("\n=== Final database summary ===")
            all_users = User.query.filter(User.first_name.like('demo%')).all()
            for user in all_users:
                print(f"User: {user.first_name} {user.last_name} (ID: {user.id}, parent: {user.is_parent}, claimed: {user.account_claimed}, email: {user.email})")
            
            all_relationships = Judges.query.join(User, Judges.judge_id == User.id).filter(User.first_name.like('demo%')).all()
            for rel in all_relationships:
                print(f"Relationship: {rel.judge.first_name} {rel.judge.last_name} -> {rel.child.first_name} {rel.child.last_name}")

if __name__ == '__main__':
    simulate_registration_scenarios()
