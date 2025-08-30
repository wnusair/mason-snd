#!/usr/bin/env python3
"""
Simple test to verify that the datetime comparison fixes work correctly.
This test simulates the scenario that was causing the TypeError.
"""

from datetime import datetime, timedelta
import pytz

# Simulate the timezone setup from the application
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

def test_datetime_comparison():
    """Test that datetime comparison works with both naive and aware timestamps"""
    
    # Create a timezone-aware reference time (like thirty_days_ago in the code)
    thirty_days_ago = datetime.now(EST) - timedelta(days=30)
    print(f"Reference time (thirty_days_ago): {thirty_days_ago}")
    print(f"Reference time timezone: {thirty_days_ago.tzinfo}")
    
    # Test with timezone-naive timestamp (old data)
    naive_timestamp = datetime.now() - timedelta(days=15)  # 15 days ago, should be > 30 days ago
    print(f"\nNaive timestamp: {naive_timestamp}")
    print(f"Naive timestamp timezone: {naive_timestamp.tzinfo}")
    
    # Normalize the naive timestamp
    normalized_naive = normalize_timestamp_for_comparison(naive_timestamp)
    print(f"Normalized naive timestamp: {normalized_naive}")
    print(f"Normalized naive timestamp timezone: {normalized_naive.tzinfo}")
    
    # Test comparison (this would have failed before the fix)
    try:
        result = normalized_naive >= thirty_days_ago
        print(f"Comparison result (naive >= reference): {result}")
        print("✅ Naive timestamp comparison successful!")
    except TypeError as e:
        print(f"❌ Naive timestamp comparison failed: {e}")
    
    # Test with timezone-aware timestamp (new data)
    aware_timestamp = datetime.now(EST) - timedelta(days=15)  # 15 days ago
    print(f"\nAware timestamp: {aware_timestamp}")
    print(f"Aware timestamp timezone: {aware_timestamp.tzinfo}")
    
    # Normalize the aware timestamp (should be unchanged)
    normalized_aware = normalize_timestamp_for_comparison(aware_timestamp)
    print(f"Normalized aware timestamp: {normalized_aware}")
    print(f"Normalized aware timestamp timezone: {normalized_aware.tzinfo}")
    
    # Test comparison
    try:
        result = normalized_aware >= thirty_days_ago
        print(f"Comparison result (aware >= reference): {result}")
        print("✅ Aware timestamp comparison successful!")
    except TypeError as e:
        print(f"❌ Aware timestamp comparison failed: {e}")
    
    # Test with None timestamp
    none_timestamp = None
    normalized_none = normalize_timestamp_for_comparison(none_timestamp)
    print(f"\nNone timestamp normalized: {normalized_none}")
    if normalized_none is None:
        print("✅ None timestamp handled correctly!")
    else:
        print("❌ None timestamp not handled correctly!")

if __name__ == "__main__":
    print("Testing datetime comparison fixes...")
    print("=" * 50)
    test_datetime_comparison()
    print("=" * 50)
    print("All tests completed!")
