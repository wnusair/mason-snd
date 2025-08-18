#!/usr/bin/env python3
"""
Test Data Management Script for Mason SND

This script demonstrates how to create and manage test data programmatically.
You can also use the web interface at /admin/test_data
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mason_snd import create_app
from mason_snd.extensions import db
from mason_snd.models.auth import User, Judges
from mason_snd.models.events import Event, User_Event
from mason_snd.models.tournaments import Tournament, Tournament_Signups, Tournament_Judges
from werkzeug.security import generate_password_hash
import random

def create_test_users(password="testpass123"):
    """Create 15 test students and their parents"""
    app = create_app()
    
    with app.app_context():
        print(f"Creating 15 test students and parents with password: {password}")
        
        for i in range(1, 16):
            # Check if student already exists
            existing_student = User.query.filter_by(
                first_name=f'Student{i}',
                last_name='Test'
            ).first()
            
            if existing_student:
                print(f"Student{i} already exists, skipping...")
                continue
            
            # Create student
            student = User(
                first_name=f'Student{i}',
                last_name='Test',
                email=f'student{i}@gmail.com',
                password=generate_password_hash(password),
                phone_number=f'555-000-{1000+i}',
                is_parent=False,
                role=0,
                emergency_contact_first_name=f'Parent{i}',
                emergency_contact_last_name='Test',
                emergency_contact_number=f'555-100-{1000+i}',
                emergency_contact_relationship='Parent',
                emergency_contact_email=f'parent{i}@gmail.com',
                account_claimed=True
            )
            db.session.add(student)
            db.session.flush()
            
            # Create parent
            parent = User(
                first_name=f'Parent{i}',
                last_name='Test',
                email=f'parent{i}@gmail.com',
                password=generate_password_hash(password),
                phone_number=f'555-100-{1000+i}',
                is_parent=True,
                role=0,
                child_first_name=f'Student{i}',
                child_last_name='Test',
                account_claimed=True
            )
            db.session.add(parent)
            db.session.flush()
            
            # Create judge relationship
            judge_rel = Judges(
                judge_id=parent.id,
                child_id=student.id,
                background_check=True
            )
            db.session.add(judge_rel)
            
            print(f"Created Student{i} and Parent{i}")
        
        db.session.commit()
        print("✅ All test users created successfully!")

def enroll_in_events():
    """Enroll test students in random events"""
    app = create_app()
    
    with app.app_context():
        students = User.query.filter(
            User.first_name.like('Student%'),
            User.last_name == 'Test'
        ).all()
        
        events = Event.query.all()
        
        if not events:
            print("❌ No events found. Create some events first.")
            return
        
        print(f"Enrolling {len(students)} students in random events...")
        
        for student in students:
            # Join 1-3 random events
            num_events = random.randint(1, min(3, len(events)))
            selected_events = random.sample(events, num_events)
            
            for event in selected_events:
                existing = User_Event.query.filter_by(
                    user_id=student.id,
                    event_id=event.id
                ).first()
                
                if not existing:
                    user_event = User_Event(
                        user_id=student.id,
                        event_id=event.id,
                        active=True
                    )
                    db.session.add(user_event)
                    print(f"  {student.first_name} enrolled in {event.event_name}")
        
        db.session.commit()
        print("✅ All students enrolled in events!")

def signup_for_tournaments():
    """Sign up test students for random tournaments"""
    app = create_app()
    
    with app.app_context():
        students = User.query.filter(
            User.first_name.like('Student%'),
            User.last_name == 'Test'
        ).all()
        
        tournaments = Tournament.query.all()
        
        if not tournaments:
            print("❌ No tournaments found. Create some tournaments first.")
            return
        
        print(f"Signing up {len(students)} students for random tournaments...")
        
        for student in students:
            # Get student's events
            student_events = User_Event.query.filter_by(user_id=student.id, active=True).all()
            
            if not student_events:
                print(f"  {student.first_name} has no events, skipping...")
                continue
            
            # Sign up for 1-2 random tournaments
            num_tournaments = random.randint(1, min(2, len(tournaments)))
            selected_tournaments = random.sample(tournaments, num_tournaments)
            
            # Get parent
            parent = User.query.filter(
                User.child_first_name == student.first_name,
                User.child_last_name == student.last_name,
                User.is_parent == True
            ).first()
            
            for tournament in selected_tournaments:
                # Pick random event
                event = random.choice(student_events).event
                
                existing = Tournament_Signups.query.filter_by(
                    user_id=student.id,
                    tournament_id=tournament.id,
                    event_id=event.id
                ).first()
                
                if not existing:
                    # Randomly decide if bringing a judge (70% chance if parent exists)
                    bringing_judge = bool(parent and random.random() < 0.7)
                    
                    signup = Tournament_Signups(
                        user_id=student.id,
                        tournament_id=tournament.id,
                        event_id=event.id,
                        bringing_judge=bringing_judge,
                        judge_id=parent.id if bringing_judge else None,
                        is_going=True
                    )
                    db.session.add(signup)
                    
                    # Create Tournament_Judges entry if bringing a judge
                    if bringing_judge and parent:
                        # Check if Tournament_Judges entry already exists
                        existing_judge = Tournament_Judges.query.filter_by(
                            tournament_id=tournament.id,
                            child_id=student.id,
                            event_id=event.id
                        ).first()
                        
                        if not existing_judge:
                            # Random approval chance (80% chance parent approves)
                            accepted = random.random() < 0.8
                            
                            judge_entry = Tournament_Judges(
                                accepted=accepted,
                                judge_id=parent.id,
                                child_id=student.id,
                                tournament_id=tournament.id,
                                event_id=event.id
                            )
                            db.session.add(judge_entry)
                            print(f"  {student.first_name} signed up for {tournament.name} in {event.event_name} (bringing judge: {accepted})")
                        else:
                            print(f"  {student.first_name} already has judge entry for {tournament.name}")
                    else:
                        print(f"  {student.first_name} signed up for {tournament.name} in {event.event_name} (no judge)")
        
        db.session.commit()
        print("✅ All students signed up for tournaments!")

def approve_judge_requests():
    """Approve or deny judge requests for test parents"""
    app = create_app()
    
    with app.app_context():
        parents = User.query.filter(
            User.first_name.like('Parent%'),
            User.last_name == 'Test',
            User.is_parent == True
        ).all()
        
        print(f"Processing judge requests for {len(parents)} test parents...")
        
        for parent in parents:
            # Get all judge requests for this parent
            judge_requests = Tournament_Judges.query.filter_by(judge_id=parent.id).all()
            
            for request in judge_requests:
                # 80% chance to approve
                if random.random() < 0.8:
                    request.accepted = True
                    print(f"  Approved judge request for {parent.first_name}")
                else:
                    request.accepted = False
                    print(f"  Denied judge request for {parent.first_name}")
        
        db.session.commit()
        print("✅ All judge requests processed!")

def cleanup_test_data():
    """Remove all test data"""
    app = create_app()
    
    with app.app_context():
        print("Cleaning up test data...")
        
        students = User.query.filter(
            User.first_name.like('Student%'),
            User.last_name == 'Test'
        ).all()
        
        parents = User.query.filter(
            User.first_name.like('Parent%'),
            User.last_name == 'Test'
        ).all()
        
        # Delete related records first
        for student in students:
            User_Event.query.filter_by(user_id=student.id).delete()
            Tournament_Signups.query.filter_by(user_id=student.id).delete()
            Tournament_Judges.query.filter_by(child_id=student.id).delete()
            Judges.query.filter_by(child_id=student.id).delete()
        
        for parent in parents:
            Tournament_Signups.query.filter_by(judge_id=parent.id).delete()
            Tournament_Judges.query.filter_by(judge_id=parent.id).delete()
            Judges.query.filter_by(judge_id=parent.id).delete()
        
        # Delete users
        for student in students:
            db.session.delete(student)
            print(f"Deleted {student.first_name}")
        for parent in parents:
            db.session.delete(parent)
            print(f"Deleted {parent.first_name}")
        
        db.session.commit()
        print("✅ All test data cleaned up!")

def show_stats():
    """Show current test data statistics"""
    app = create_app()
    
    with app.app_context():
        students = User.query.filter(
            User.first_name.like('Student%'),
            User.last_name == 'Test'
        ).all()
        
        parents = User.query.filter(
            User.first_name.like('Parent%'),
            User.last_name == 'Test'
        ).all()
        
        event_enrollments = 0
        tournament_signups = 0
        judge_entries = 0
        approved_judges = 0
        for student in students:
            event_enrollments += User_Event.query.filter_by(user_id=student.id).count()
            tournament_signups += Tournament_Signups.query.filter_by(user_id=student.id).count()
            judge_entries += Tournament_Judges.query.filter_by(child_id=student.id).count()
            approved_judges += Tournament_Judges.query.filter_by(child_id=student.id, accepted=True).count()
        
        print(f"""
📊 Current Test Data Stats:
  • Students: {len(students)}
  • Parents: {len(parents)}
  • Event Enrollments: {event_enrollments}
  • Tournament Signups: {tournament_signups}
  • Judge Entries: {judge_entries}
  • Approved Judges: {approved_judges}
        """)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage test data for Mason SND")
    parser.add_argument('action', choices=['create', 'enroll', 'signup', 'approve', 'cleanup', 'stats'], 
                       help='Action to perform')
    parser.add_argument('--password', default='testpass123', 
                       help='Password for test users (default: testpass123)')
    
    args = parser.parse_args()
    
    if args.action == 'create':
        create_test_users(args.password)
    elif args.action == 'enroll':
        enroll_in_events()
    elif args.action == 'signup':
        signup_for_tournaments()
    elif args.action == 'approve':
        approve_judge_requests()
    elif args.action == 'cleanup':
        cleanup_test_data()
    elif args.action == 'stats':
        show_stats()
