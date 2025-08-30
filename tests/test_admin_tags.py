#!/usr/bin/env python3
"""
Test script to verify admin search shows judge/child tags correctly
"""

from mason_snd import create_app
from mason_snd.extensions import db
from mason_snd.models.auth import User, Judges

def test_admin_tags():
    """Test that admin search includes judge/child tags"""
    app = create_app()
    
    with app.app_context():
        print("=== TESTING ADMIN SEARCH TAGS ===\n")
        
        # Get some sample users
        users = User.query.limit(10).all()
        print(f"Testing with {len(users)} users")
        
        for user in users:
            print(f"\nUser: {user.first_name} {user.last_name}")
            print(f"  is_parent: {user.is_parent}")
            
            # Check if user is a child (has entries in Judges table as child_id)
            child_entries = Judges.query.filter_by(child_id=user.id).all()
            print(f"  child_entries: {len(child_entries)}")
            
            # Determine tags
            tags = []
            if user.is_parent:
                tags.append("Judge")
            if child_entries:
                tags.append("Child")
            if not user.is_parent and not child_entries:
                tags.append("Student")
                
            print(f"  Tags: {', '.join(tags)}")
            
            # Show any judge relationships
            if child_entries:
                for entry in child_entries:
                    judge = User.query.get(entry.judge_id)
                    if judge:
                        print(f"    Judge: {judge.first_name} {judge.last_name}")
        
        print(f"\n=== SUMMARY ===")
        total_parents = User.query.filter_by(is_parent=True).count()
        total_children = Judges.query.distinct(Judges.child_id).count()
        total_users = User.query.count()
        
        print(f"Total users: {total_users}")
        print(f"Total judges (is_parent=True): {total_parents}")
        print(f"Total children (in Judges table): {total_children}")
        print(f"Total students (neither): {total_users - total_parents - total_children}")

if __name__ == "__main__":
    test_admin_tags()
