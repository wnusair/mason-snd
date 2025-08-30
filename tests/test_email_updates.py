#!/usr/bin/env python3
"""
Test script to verify email duplicate prevention and account updates
"""

import os
import sys
sys.path.insert(0, '/home/wnusair/mason-snd')

from mason_snd import create_app
from mason_snd.extensions import db
from mason_snd.models.auth import User, Judges
from werkzeug.security import generate_password_hash

def test_email_and_account_updates():
    """Test email duplicate prevention and account updates"""
    
    app = create_app()
    
    with app.app_context():
        # Clear existing test data
        print("Clearing existing test data...")
        Judges.query.filter(
            (Judges.judge.has(first_name='test')) |
            (Judges.child.has(first_name='test'))
        ).delete(synchronize_session=False)
        
        User.query.filter(
            User.first_name.like('test%')
        ).delete(synchronize_session=False)
        
        db.session.commit()
        
        from mason_snd.blueprints.auth.auth import find_or_create_user, create_or_update_judge_relationship
        
        print("\n=== Test 1: Create parent without email, then child adds email ===")
        
        # First, create a ghost parent account (no email)
        parent_data_minimal = {
            'phone_number': '555-1234',
            'child_first_name': 'testchild',
            'child_last_name': 'smith'
        }
        parent = find_or_create_user('testparent', 'smith', True, **parent_data_minimal)
        parent.account_claimed = False  # Make it a ghost account
        db.session.commit()
        
        print(f"Created ghost parent (ID: {parent.id}, email: {parent.email}, claimed: {parent.account_claimed})")
        
        # Now child registers and provides parent's email
        child_data = {
            'email': 'testchild@example.com',
            'password': generate_password_hash('password'),
            'phone_number': '555-5678',
            'emergency_contact_first_name': 'testparent',
            'emergency_contact_last_name': 'smith',
            'emergency_contact_number': '555-1234',
            'emergency_contact_relationship': 'parent',
            'emergency_contact_email': 'testparent@example.com'
        }
        
        child = find_or_create_user('testchild', 'smith', False, **child_data)
        
        # Update parent with email from child's emergency contact
        parent_update_data = {
            'email': 'testparent@example.com'
        }
        parent_updated = find_or_create_user('testparent', 'smith', True, **parent_update_data)
        
        print(f"Child created (ID: {child.id}, email: {child.email})")
        print(f"Parent updated (ID: {parent_updated.id}, email: {parent_updated.email}, same ID: {parent_updated.id == parent.id})")
        
        create_or_update_judge_relationship(parent_updated.id, child.id)
        
        print("\n=== Test 2: Check email uniqueness ===")
        
        # Check that email was properly added
        parent_fresh = User.query.get(parent.id)
        print(f"Parent fresh fetch - email: {parent_fresh.email}")
        
        # Try to create another user with same email (should be prevented at registration level)
        existing_email_user = User.query.filter_by(email='testparent@example.com').first()
        print(f"User with testparent@example.com exists: {existing_email_user is not None}")
        print(f"That user is: {existing_email_user.first_name} {existing_email_user.last_name} (claimed: {existing_email_user.account_claimed})")
        
        print("\n=== Test 3: Account claiming scenario ===")
        
        # Create another ghost account
        ghost_data = {}
        ghost = find_or_create_user('testghost', 'jones', False, **ghost_data)
        ghost.account_claimed = False
        db.session.commit()
        
        print(f"Created ghost (ID: {ghost.id}, email: {ghost.email}, claimed: {ghost.account_claimed})")
        
        # Now "claim" the account
        claim_data = {
            'email': 'testghost@example.com',
            'password': generate_password_hash('ghostpass'),
            'phone_number': '555-9999'
        }
        
        claimed_ghost = find_or_create_user('testghost', 'jones', False, **claim_data)
        
        print(f"Claimed ghost (ID: {claimed_ghost.id}, email: {claimed_ghost.email}, claimed: {claimed_ghost.account_claimed})")
        print(f"Same user: {claimed_ghost.id == ghost.id}")

if __name__ == '__main__':
    test_email_and_account_updates()
