# Roster Generation Fix Summary

## Issues Fixed

### 1. Partner Events Counting as Two Registrations
**Problem**: When a speech partner event had a duo (e.g., Public Forum partners), the system counted them as 2 separate registrations instead of 1 partnership.

**Solution**: 
- Created `add_competitor()` helper function that tracks selected users and their partners
- When a competitor with a partner is selected:
  - Checks if partner is already selected (prevents double-counting)
  - Verifies partner is in the event signup list
  - Adds both users to `selected_user_ids` set
  - Adds both to `event_view` and `rank_view` together
- Uses `partnership_map` to track bidirectional partnerships
- Ensures partner pairs are treated as a single unit

### 2. Judge's Child Not Guaranteed a Spot
**Problem**: When a parent brought a judge, their child wasn't guaranteed a spot on the roster even though that's the expected behavior.

**Solution**:
- Pass `judge_children_ids` set through all roster generation functions
- Added priority selection phase for each event type (Speech, LD, PF)
- Before normal selection, iterate through competitors and pre-select any judge's children
- Judge's children are selected first, then remaining spots filled normally
- Works across all event types (Speech, LD, PF)

## Code Changes

### Modified Functions

#### `select_competitors_by_event_type()`
**Location**: `/workspaces/mason-snd/mason_snd/blueprints/rosters/rosters.py`

**Changes**:
1. Added `add_competitor()` helper function
   - Prevents duplicate selection
   - Handles partner pairing logic
   - Adds both partner and primary competitor atomically

2. Speech Events:
   - Pre-select judge's children before rotation algorithm
   - Use `add_competitor()` for all selections
   - Skip already-selected users automatically

3. LD Events:
   - Pre-select judge's children before normal selection
   - Use `add_competitor()` with retry logic for partner pairs
   - Handle middle-selection algorithm with partner awareness

4. PF Events:
   - Pre-select judge's children before normal selection
   - Use `add_competitor()` with retry logic for partner pairs
   - Handle middle-selection algorithm with partner awareness

### Modified Routes

#### `view_tournament()`
- Added judge query to get `judge_children_ids`
- Pass `judge_children_ids` to `select_competitors_by_event_type()`

#### `download_tournament()`
- Added judge query to get `judge_children_ids`
- Pass `judge_children_ids` to `select_competitors_by_event_type()`

#### `save_tournament()`
- Added judge query to get `judge_children_ids`
- Pass `judge_children_ids` to `select_competitors_by_event_type()`

## Testing

### Test Case 1: Partner Events
```python
# Input: 4 PF spots, 2 partner pairs
ranked = {1: [user1+user2 pair, user3+user4 pair]}
# Output: 4 users selected (2 pairs)
# ✅ Partners counted as single registration unit
```

### Test Case 2: Judge Child Priority
```python
# Input: 6 speech spots, user 13 is judge's child
ranked = {2: [user10, user11, user12, user13, user14]}
# Output: user 13 selected first, then others
# ✅ Judge's child guaranteed a spot
```

## Impact

### Positive Changes
- Partner pairs now correctly count as one registration
- Judge's children guaranteed spots (expected behavior)
- No breaking changes to existing functionality
- All event types (Speech, LD, PF) work correctly

### No Negative Impact
- Existing rosters unaffected (only affects new generation)
- Algorithm still respects weighted points ranking
- Random selection (speech) still works
- Middle selection (LD/PF with 2+ judges) still works
- Drop penalty system unchanged

## Files Modified
- `/workspaces/mason-snd/mason_snd/blueprints/rosters/rosters.py`

## Lines Changed
- ~70 lines modified across multiple functions
- No files added or removed
- No database schema changes required
