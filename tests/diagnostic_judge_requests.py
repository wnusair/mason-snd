#!/usr/bin/env python3
"""
Diagnostic script to help troubleshoot parent judge request issues
"""

from mason_snd import create_app
from mason_snd.extensions import db
from mason_snd.models.auth import User, Judges
from mason_snd.models.tournaments import Tournament_Judges, Tournament_Signups

app = create_app()

def diagnose_parent_account(parent_email_or_name):
    """Diagnose issues with a parent account"""
    with app.app_context():
        print(f"=== DIAGNOSING PARENT ACCOUNT: {parent_email_or_name} ===\n")
        
        # Try to find parent by email or name
        parent = None
        if '@' in parent_email_or_name:
            parent = User.query.filter_by(email=parent_email_or_name).first()
        else:
            # Try to find by first name
            parent = User.query.filter(User.first_name.ilike(f'%{parent_email_or_name}%')).first()
        
        if not parent:
            print(f"❌ Parent account not found for: {parent_email_or_name}")
            print("🔍 Available parent accounts:")
            parents = User.query.filter_by(is_parent=True).all()
            for p in parents[:10]:  # Show first 10
                print(f"  - {p.first_name} {p.last_name} ({p.email})")
            return
        
        print(f"✅ Parent account found: {parent.first_name} {parent.last_name}")
        print(f"   Email: {parent.email}")
        print(f"   is_parent: {parent.is_parent}")
        print(f"   Account claimed: {parent.account_claimed}")
        
        # Check child relationships
        print(f"\n--- CHILD RELATIONSHIPS ---")
        judge_relationships = Judges.query.filter_by(judge_id=parent.id).all()
        print(f"Judge relationships: {len(judge_relationships)}")
        
        children = []
        for rel in judge_relationships:
            child = User.query.get(rel.child_id)
            if child:
                children.append(child)
                print(f"  - Child: {child.first_name} {child.last_name} ({child.email})")
                print(f"    Background check: {rel.background_check}")
        
        if not children:
            print("❌ No children linked to this parent account")
            return
        
        # Check tournament signups for children
        print(f"\n--- TOURNAMENT SIGNUPS ---")
        for child in children:
            signups = Tournament_Signups.query.filter_by(user_id=child.id, is_going=True).all()
            print(f"Signups for {child.first_name}: {len(signups)}")
            
            for signup in signups:
                tournament = Tournament.query.get(signup.tournament_id)
                event = Event.query.get(signup.event_id)
                print(f"  - Tournament: {tournament.name if tournament else 'Unknown'}")
                print(f"    Event: {event.event_name if event else 'Unknown'}")
                print(f"    Bringing judge: {signup.bringing_judge}")
                print(f"    Judge ID: {signup.judge_id}")
        
        # Check judge requests
        print(f"\n--- JUDGE REQUESTS ---")
        judge_requests = Tournament_Judges.query.filter_by(judge_id=parent.id).all()
        print(f"Judge requests for {parent.first_name}: {len(judge_requests)}")
        
        if judge_requests:
            for req in judge_requests:
                child = User.query.get(req.child_id)
                tournament = Tournament.query.get(req.tournament_id)
                event = Event.query.get(req.event_id)
                print(f"  - Request from: {child.first_name if child else 'Unknown'}")
                print(f"    Tournament: {tournament.name if tournament else 'Unknown'}")
                print(f"    Event: {event.event_name if event else 'Unknown'}")
                print(f"    Accepted: {req.accepted}")
        else:
            print("❌ No judge requests found")
            
            # Check if there are any Tournament_Judges entries with judge_id=None for their children
            print(f"\n🔍 Checking for incomplete judge assignments...")
            for child in children:
                incomplete = Tournament_Judges.query.filter_by(child_id=child.id, judge_id=None).all()
                if incomplete:
                    print(f"  ⚠️  Found {len(incomplete)} incomplete judge assignments for {child.first_name}")
                    for inc in incomplete:
                        tournament = Tournament.query.get(inc.tournament_id)
                        event = Event.query.get(inc.event_id)
                        print(f"    - Tournament: {tournament.name if tournament else 'Unknown'}")
                        print(f"      Event: {event.event_name if event else 'Unknown'}")
        
        print(f"\n--- RECOMMENDATIONS ---")
        if not parent.is_parent:
            print("❌ Set is_parent=True for this account")
        if not judge_relationships:
            print("❌ Create Judge relationship linking parent to child")
        if not judge_requests:
            print("❌ Child needs to complete tournament signup and select this parent as judge")

def list_common_issues():
    """List common issues and their solutions"""
    print("=== COMMON ISSUES AND SOLUTIONS ===\n")
    
    print("1. PARENT ACCOUNT NOT MARKED AS PARENT")
    print("   - Check if user.is_parent = True")
    print("   - Solution: Update the User record")
    
    print("\n2. MISSING JUDGE RELATIONSHIP")
    print("   - Check if Judges table has entry linking parent and child")
    print("   - Solution: Create Judges record with judge_id=parent.id, child_id=child.id")
    
    print("\n3. INCOMPLETE TOURNAMENT SIGNUP")
    print("   - Child signed up but didn't complete judge selection")
    print("   - Look for Tournament_Judges entries with judge_id=None")
    print("   - Solution: Child needs to go to bringing_judge page and select parent")
    
    print("\n4. CHILD DIDN'T INDICATE BRINGING JUDGE")
    print("   - Child signed up but answered 'no' to bringing judge question")
    print("   - No Tournament_Judges entry will be created")
    print("   - Solution: Child needs to sign up again and select 'yes'")

if __name__ == "__main__":
    import sys
    
    # Import missing models
    from mason_snd.models.tournaments import Tournament
    from mason_snd.models.events import Event
    
    if len(sys.argv) > 1:
        parent_identifier = sys.argv[1]
        diagnose_parent_account(parent_identifier)
    else:
        print("Usage: python diagnostic_script.py <parent_email_or_name>")
        print("Example: python diagnostic_script.py parent@gmail.com")
        print("Example: python diagnostic_script.py 'Parent1'")
        print()
        list_common_issues()
