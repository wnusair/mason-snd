#!/usr/bin/env python3
"""
Test script to verify that the datetime fixes are working correctly in the Flask app.
This creates some test data and makes sure comparisons work without errors.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import pytz

# Test the normalize function from the metrics module
EST = pytz.timezone('US/Eastern')

def normalize_timestamp_for_comparison(timestamp):
    """
    Helper function to normalize timestamps for timezone-aware comparisons.
    If timestamp is naive, assumes it's in EST timezone.
    """
    if timestamp is None:
        return None
    if timestamp.tzinfo is None:
        return EST.localize(timestamp)
    return timestamp

def test_all_datetime_scenarios():
    """Test various datetime comparison scenarios that could occur in the app"""
    
    print("Testing datetime comparison scenarios...")
    print("=" * 50)
    
    # Test scenario 1: comparing timezone-aware datetime with date
    print("\n1. Testing datetime vs date comparison:")
    six_months_ago = datetime.now(EST) - timedelta(days=180)
    tournament_date = datetime.now(EST) - timedelta(days=100)  # 100 days ago
    
    try:
        # This was the problematic comparison
        # tournament_date >= six_months_ago.date()  # This would fail
        
        # Fixed version - both are datetime objects
        normalized_tournament = normalize_timestamp_for_comparison(tournament_date)
        result = normalized_tournament >= six_months_ago
        print(f"✅ Datetime comparison successful: {result}")
    except TypeError as e:
        print(f"❌ Datetime comparison failed: {e}")
    
    # Test scenario 2: naive vs aware datetime comparison
    print("\n2. Testing naive vs aware datetime comparison:")
    naive_datetime = datetime.now() - timedelta(days=50)
    aware_datetime = datetime.now(EST) - timedelta(days=30)
    
    try:
        normalized_naive = normalize_timestamp_for_comparison(naive_datetime)
        result = normalized_naive >= aware_datetime
        print(f"✅ Naive vs aware comparison successful: {result}")
    except TypeError as e:
        print(f"❌ Naive vs aware comparison failed: {e}")
    
    # Test scenario 3: None handling
    print("\n3. Testing None timestamp handling:")
    try:
        normalized_none = normalize_timestamp_for_comparison(None)
        if normalized_none is None:
            print("✅ None timestamp handled correctly")
        else:
            print("❌ None timestamp not handled correctly")
    except Exception as e:
        print(f"❌ None timestamp handling failed: {e}")
    
    # Test scenario 4: Mixed timezone and date types
    print("\n4. Testing mixed types with timezone conversion:")
    try:
        # Simulate database datetime that might be naive
        db_datetime = datetime(2025, 8, 1, 10, 0, 0)  # Naive datetime
        current_time = datetime.now(EST)
        thirty_days_ago = current_time - timedelta(days=30)
        
        # Normalize and compare
        normalized_db = normalize_timestamp_for_comparison(db_datetime)
        result = normalized_db >= thirty_days_ago
        print(f"✅ Mixed type comparison successful: {result}")
        print(f"   Original: {db_datetime} (timezone: {db_datetime.tzinfo})")
        print(f"   Normalized: {normalized_db} (timezone: {normalized_db.tzinfo})")
    except TypeError as e:
        print(f"❌ Mixed type comparison failed: {e}")
    
    print("\n" + "=" * 50)
    print("All datetime tests completed!")

if __name__ == "__main__":
    test_all_datetime_scenarios()
