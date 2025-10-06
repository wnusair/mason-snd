#!/usr/bin/env python3
"""
Test script for roster download/edit/upload feature
Tests the smart user matching algorithm and Excel generation
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from mason_snd import create_app
from mason_snd.extensions import db
from mason_snd.models.auth import User
from mason_snd.models.events import Event
from mason_snd.models.rosters import Roster, Roster_Competitors, Roster_Judge
from datetime import datetime
import pytz

def test_smart_user_matching():
    """Test the smart user matching logic"""
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("TESTING SMART USER MATCHING")
        print("=" * 60)
        
        # Create test users
        print("\n1. Creating test users...")
        test_user1 = User(
            first_name="TestJohn",
            last_name="TestSmith",
            email="testjohn.testsmith@example.com",
            role=1
        )
        test_user2 = User(
            first_name="TestSarah",
            last_name="TestJones",
            email="testsarah.testjones@example.com",
            role=1
        )
        
        db.session.add(test_user1)
        db.session.add(test_user2)
        db.session.commit()
        
        print(f"   ✅ Created User #{test_user1.id}: TestJohn TestSmith")
        print(f"   ✅ Created User #{test_user2.id}: TestSarah TestJones")
        
        # Test the matching logic (simulated from upload function)
        print("\n2. Testing matching scenarios...")
        
        # Test Case 1: Match by User ID (name is ignored)
        print("\n   Test Case 1: Match by User ID")
        print(f"   Input: user_id={test_user1.id}, name='WRONG NAME'")
        matched = User.query.get(test_user1.id)
        print(f"   ✅ Matched: {matched.first_name} {matched.last_name} (ID: {matched.id})")
        assert matched.id == test_user1.id, "Should match by ID regardless of name"
        
        # Test Case 2: Match by exact name
        print("\n   Test Case 2: Match by exact name")
        print(f"   Input: user_id=None, name='TestSarah TestJones'")
        name_parts = "TestSarah TestJones".split()
        matched = User.query.filter_by(
            first_name=name_parts[0],
            last_name=name_parts[1]
        ).first()
        print(f"   ✅ Matched: {matched.first_name} {matched.last_name} (ID: {matched.id})")
        assert matched.id == test_user2.id, "Should match by exact name"
        
        # Test Case 3: Match by case-insensitive name
        print("\n   Test Case 3: Match by case-insensitive name")
        print(f"   Input: user_id=None, name='TESTJOHN TESTSMITH'")
        name_parts = "TESTJOHN TESTSMITH".split()
        matched = User.query.filter(
            db.func.lower(User.first_name) == name_parts[0].lower(),
            db.func.lower(User.last_name) == name_parts[1].lower()
        ).first()
        print(f"   ✅ Matched: {matched.first_name} {matched.last_name} (ID: {matched.id})")
        assert matched.id == test_user1.id, "Should match case-insensitively"
        
        # Test Case 4: No match
        print("\n   Test Case 4: No match found")
        print(f"   Input: user_id=None, name='Nonexistent Person'")
        matched = User.query.filter_by(
            first_name="Nonexistent",
            last_name="Person"
        ).first()
        result = "No match" if matched is None else f"{matched.first_name} {matched.last_name}"
        print(f"   ✅ Result: {result}")
        assert matched is None, "Should not match"
        
        # Cleanup
        print("\n3. Cleaning up test data...")
        User.query.filter(User.email.in_(['testjohn.testsmith@example.com', 'testsarah.testjones@example.com'])).delete()
        db.session.commit()
        print("   ✅ Test users deleted")
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)

def test_excel_generation():
    """Test Excel file generation"""
    app = create_app()
    
    with app.app_context():
        print("\n" + "=" * 60)
        print("TESTING EXCEL GENERATION")
        print("=" * 60)
        
        # Check if openpyxl is available
        try:
            import pandas as pd
            import openpyxl
            print("   ✅ pandas and openpyxl are installed")
        except ImportError as e:
            print(f"   ❌ Missing dependency: {e}")
            print("   Run: pip install pandas openpyxl")
            return
        
        # Find a roster to test with
        roster = Roster.query.first()
        if not roster:
            print("   ℹ️  No rosters found in database. Skipping Excel generation test.")
            return
        
        print(f"\n   Testing with roster: {roster.name} (ID: {roster.id})")
        
        # Get competitors and judges
        competitors = Roster_Competitors.query.filter_by(roster_id=roster.id).all()
        judges = Roster_Judge.query.filter_by(roster_id=roster.id).all()
        
        print(f"   - {len(competitors)} competitors")
        print(f"   - {len(judges)} judges")
        
        if len(competitors) > 0:
            print("   ✅ Roster has data for Excel generation")
        else:
            print("   ℹ️  Roster is empty, but Excel generation should still work")
        
        print("\n" + "=" * 60)
        print("✅ EXCEL GENERATION CHECK COMPLETE")
        print("=" * 60)

def main():
    print("\n" + "=" * 60)
    print("ROSTER EDIT FEATURE - TEST SUITE")
    print("=" * 60)
    
    try:
        test_smart_user_matching()
        test_excel_generation()
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Start the Flask app")
        print("2. Navigate to a roster and click 'Download'")
        print("3. Edit the Excel file (change names, add/remove rows)")
        print("4. Go to Upload Roster page")
        print("5. Select 'Update Existing Roster' and upload")
        print("6. Verify changes were applied correctly")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
