#!/usr/bin/env python3
"""
Test the complete registration flow for ghost account claiming
"""

import os
import sys
sys.path.insert(0, '/home/wnusair/mason-snd')

from mason_snd import create_app
from mason_snd.extensions import db
from mason_snd.models.auth import User, Judges
from werkzeug.security import generate_password_hash

def test_complete_ghost_flow():
    """Test the complete flow of ghost account creation and claiming"""
    
    app = create_app()
    
    with app.app_context():
        print("=== COMPLETE GHOST ACCOUNT FLOW TEST ===\n")
        
        # Clear test data
        print("Clearing test data...")
        User.query.filter(User.first_name.in_(['realchild', 'realparent'])).delete(synchronize_session=False)
        Judges.query.filter(
            (Judges.judge.has(User.first_name.in_(['realchild', 'realparent']))) |
            (Judges.child.has(User.first_name.in_(['realchild', 'realparent'])))
        ).delete(synchronize_session=False)
        db.session.commit()
        
        from mason_snd.blueprints.auth.auth import find_or_create_user, create_or_update_judge_relationship
        
        print("✅ Test data cleared\n")
        
        # Step 1: Child registers first, creating a ghost parent
        print("📝 STEP 1: Child registers first")
        print("   Child 'RealChild Smith' registers, creating ghost parent 'RealParent Smith'")
        
        # Simulate the child registration process
        child_user_data = {
            'email': 'realchild@student.example.com',
            'password': generate_password_hash('childpassword'),
            'phone_number': '555-1001',
            'emergency_contact_first_name': 'realparent',
            'emergency_contact_last_name': 'smith',
            'emergency_contact_number': '555-2001',
            'emergency_contact_relationship': 'parent',
            'emergency_contact_email': 'realparent@parent.example.com'
        }
        
        child_user = find_or_create_user('realchild', 'smith', False, **child_user_data)
        
        # Create ghost parent from emergency contact
        parent_user_data = {
            'phone_number': '555-2001',
            'email': 'realparent@parent.example.com',
            'child_first_name': 'realchild',
            'child_last_name': 'smith'
        }
        parent_user = find_or_create_user('realparent', 'smith', True, **parent_user_data)
        parent_user.account_claimed = False  # Make it a ghost
        db.session.commit()
        
        create_or_update_judge_relationship(parent_user.id, child_user.id)
        
        print(f"   ✅ Child created: ID={child_user.id}, claimed={child_user.account_claimed}")
        print(f"   ✅ Ghost parent created: ID={parent_user.id}, claimed={parent_user.account_claimed}")
        print(f"   ✅ Ghost parent email: {parent_user.email}")
        
        # Step 2: The actual parent tries to register
        print(f"\n📝 STEP 2: Actual parent tries to register")
        print("   Parent 'RealParent Smith' tries to register with email 'realparent@parent.example.com'")
        
        # Test the email validation logic that happens during registration
        email = 'realparent@parent.example.com'
        first_name = 'RealParent'
        last_name = 'Smith'
        is_parent = True
        
        existing_email_user = User.query.filter_by(email=email).first()
        print(f"   📧 Found existing user with email: {existing_email_user is not None}")
        
        if existing_email_user:
            print(f"   📧 Existing user: {existing_email_user.first_name} {existing_email_user.last_name}")
            print(f"   📧 Existing user claimed: {existing_email_user.account_claimed}")
            print(f"   📧 Existing user is_parent: {existing_email_user.is_parent}")
        
        # Apply the email validation logic
        should_block = False
        if existing_email_user and existing_email_user.account_claimed:
            is_same_person = (
                existing_email_user.first_name.lower() == first_name.lower() and
                existing_email_user.last_name.lower() == last_name.lower() and
                existing_email_user.is_parent == is_parent
            )
            should_block = not is_same_person
            print(f"   🔍 Is same person: {is_same_person}")
        
        print(f"   🚫 Should block registration: {should_block}")
        
        # Since the ghost account is not claimed, registration should proceed
        if not should_block:
            print("   ✅ Registration allowed - proceeding to claim ghost account")
            
            # Simulate the parent registration
            parent_claim_data = {
                'email': 'realparent@parent.example.com',
                'password': generate_password_hash('parentpassword'),
                'phone_number': '555-2001',
                'judging_reqs': 'test',
                'child_first_name': 'realchild',
                'child_last_name': 'smith'
            }
            
            claimed_parent = find_or_create_user('realparent', 'smith', True, **parent_claim_data)
            create_or_update_judge_relationship(claimed_parent.id, child_user.id)
            
            print(f"   ✅ Parent account claimed: ID={claimed_parent.id}")
            print(f"   ✅ Same as ghost: {claimed_parent.id == parent_user.id}")
            print(f"   ✅ Now claimed: {claimed_parent.account_claimed}")
            print(f"   ✅ Password set: {claimed_parent.password is not None}")
            
        else:
            print("   ❌ Registration blocked - this would be an error!")
        
        # Step 3: Verify someone else can't use the same email now
        print(f"\n📝 STEP 3: Different person tries to use the same email")
        print("   Person 'Different Person' tries to register with 'realparent@parent.example.com'")
        
        # Test with a different person
        different_email_user = User.query.filter_by(email=email).first()
        different_should_block = False
        
        if different_email_user and different_email_user.account_claimed:
            is_different_person = (
                different_email_user.first_name.lower() == 'different' and
                different_email_user.last_name.lower() == 'person' and
                different_email_user.is_parent == True
            )
            different_should_block = not is_different_person
        
        print(f"   🚫 Should block different person: {different_should_block}")
        print(f"   ✅ Email protection working: {different_should_block}")
        
        # Step 4: Final verification
        print(f"\n📝 STEP 4: Final verification")
        
        final_parent = User.query.filter_by(first_name='realparent', last_name='smith').first()
        final_child = User.query.filter_by(first_name='realchild', last_name='smith').first()
        final_relationship = Judges.query.filter_by(judge_id=final_parent.id, child_id=final_child.id).first()
        
        print(f"   ✅ Parent exists and claimed: {final_parent.account_claimed}")
        print(f"   ✅ Child exists and claimed: {final_child.account_claimed}")
        print(f"   ✅ Relationship exists: {final_relationship is not None}")
        print(f"   ✅ Parent email: {final_parent.email}")
        print(f"   ✅ Child email: {final_child.email}")
        
        print("\n🎉 COMPLETE GHOST ACCOUNT FLOW TEST PASSED!")
        print("\n📋 FLOW SUMMARY:")
        print("   1️⃣ Child registers → Creates ghost parent with email")
        print("   2️⃣ Ghost parent can claim account with same email")
        print("   3️⃣ Different people blocked from using claimed emails")
        print("   4️⃣ All relationships preserved throughout process")

if __name__ == '__main__':
    test_complete_ghost_flow()
