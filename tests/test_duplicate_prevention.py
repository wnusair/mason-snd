#!/usr/bin/env python3
"""
Test script to verify that the new registration logic prevents duplicate accounts
and properly handles the judges relationship table.
"""

import os
import sys
sys.path.insert(0, '/home/wnusair/mason-snd')

from mason_snd import create_app
from mason_snd.extensions import db
from mason_snd.models.auth import User, Judges
from werkzeug.security import generate_password_hash

def test_duplicate_prevention():
    """Test scenarios for duplicate account prevention"""
    
    app = create_app()
    
    with app.app_context():
        # Clear existing test data
        print("Clearing existing test data...")
        Judges.query.filter(
            (Judges.judge.has(first_name='john')) |
            (Judges.judge.has(first_name='jane')) |
            (Judges.child.has(first_name='alice')) |
            (Judges.child.has(first_name='bob'))
        ).delete(synchronize_session=False)
        
        User.query.filter(
            User.first_name.in_(['john', 'jane', 'alice', 'bob'])
        ).delete(synchronize_session=False)
        
        db.session.commit()
        
        print("\n=== Test Scenario 1: Parent registers first ===")
        # Simulate parent John registering for child Alice
        from mason_snd.blueprints.auth.auth import find_or_create_user, create_or_update_judge_relationship
        
        # Parent John registers for child Alice
        parent_data = {
            'email': 'john.doe@example.com',
            'password': generate_password_hash('password123'),
            'phone_number': '555-1234',
            'judging_reqs': 'test',
            'child_first_name': 'alice',
            'child_last_name': 'doe'
        }
        
        john = find_or_create_user('john', 'doe', True, **parent_data)
        alice = find_or_create_user('alice', 'doe', False)
        create_or_update_judge_relationship(john.id, alice.id)
        
        print(f"Created John (ID: {john.id}, claimed: {john.account_claimed})")
        print(f"Created Alice (ID: {alice.id}, claimed: {alice.account_claimed})")
        
        # Check judge relationship
        judge_rel = Judges.query.filter_by(judge_id=john.id, child_id=alice.id).first()
        print(f"Judge relationship created: {judge_rel is not None}")
        
        print("\n=== Test Scenario 2: Another parent registers for the same child ===")
        # Simulate parent Jane registering for the same child Alice
        parent_data2 = {
            'email': 'jane.smith@example.com',
            'password': generate_password_hash('password456'),
            'phone_number': '555-5678',
            'judging_reqs': 'test',
            'child_first_name': 'alice',
            'child_last_name': 'doe'
        }
        
        jane = find_or_create_user('jane', 'smith', True, **parent_data2)
        alice_existing = find_or_create_user('alice', 'doe', False)
        create_or_update_judge_relationship(jane.id, alice_existing.id)
        
        print(f"Created Jane (ID: {jane.id}, claimed: {jane.account_claimed})")
        print(f"Alice reused (ID: {alice_existing.id}, same as before: {alice_existing.id == alice.id})")
        
        # Check both judge relationships exist
        john_alice_rel = Judges.query.filter_by(judge_id=john.id, child_id=alice.id).first()
        jane_alice_rel = Judges.query.filter_by(judge_id=jane.id, child_id=alice.id).first()
        print(f"John-Alice relationship exists: {john_alice_rel is not None}")
        print(f"Jane-Alice relationship exists: {jane_alice_rel is not None}")
        
        print("\n=== Test Scenario 3: Child registers and claims their account ===")
        # Alice registers herself and claims her account
        child_data = {
            'email': 'alice.doe@student.example.com',
            'password': generate_password_hash('studentpass'),
            'phone_number': '555-9999',
            'emergency_contact_first_name': 'john',
            'emergency_contact_last_name': 'doe',
            'emergency_contact_number': '555-1234',
            'emergency_contact_relationship': 'father',
            'emergency_contact_email': 'john.doe@example.com'
        }
        
        alice_claimed = find_or_create_user('alice', 'doe', False, **child_data)
        john_existing = find_or_create_user('john', 'doe', True)
        create_or_update_judge_relationship(john_existing.id, alice_claimed.id)
        
        print(f"Alice claimed her account (ID: {alice_claimed.id}, same as before: {alice_claimed.id == alice.id})")
        print(f"Alice now claimed: {alice_claimed.account_claimed}")
        print(f"Alice email: {alice_claimed.email}")
        print(f"John reused (ID: {john_existing.id}, same as before: {john_existing.id == john.id})")
        
        print("\n=== Test Scenario 4: Parent registers for multiple children ===")
        # John registers for another child Bob
        bob = find_or_create_user('bob', 'doe', False)
        create_or_update_judge_relationship(john.id, bob.id)
        
        print(f"Created Bob (ID: {bob.id}, claimed: {bob.account_claimed})")
        
        # Check all relationships
        john_relationships = Judges.query.filter_by(judge_id=john.id).all()
        print(f"John has {len(john_relationships)} children: {[rel.child_id for rel in john_relationships]}")
        
        print("\n=== Final Database State ===")
        all_users = User.query.filter(User.first_name.in_(['john', 'jane', 'alice', 'bob'])).all()
        for user in all_users:
            print(f"User: {user.first_name} {user.last_name} (ID: {user.id}, parent: {user.is_parent}, claimed: {user.account_claimed})")
        
        all_judges = Judges.query.join(User, Judges.judge_id == User.id).filter(
            User.first_name.in_(['john', 'jane'])
        ).all()
        for judge_rel in all_judges:
            print(f"Judge relationship: {judge_rel.judge.first_name} {judge_rel.judge.last_name} -> {judge_rel.child.first_name} {judge_rel.child.last_name}")
        
        print("\n=== Test Scenario 5: Duplicate relationship prevention ===")
        # Try to create the same relationship again
        initial_count = Judges.query.filter_by(judge_id=john.id, child_id=alice.id).count()
        create_or_update_judge_relationship(john.id, alice.id)
        final_count = Judges.query.filter_by(judge_id=john.id, child_id=alice.id).count()
        print(f"Duplicate relationship prevention: {initial_count} -> {final_count} (should stay 1)")

if __name__ == '__main__':
    test_duplicate_prevention()
