# Drop Penalty Feature Implementation Summary

## Overview
Implemented a comprehensive drop penalty system that charges users when they drop out of tournaments and penalizes them in future tournament rosters.

## Features Implemented

### 1. Admin Panel Enhancements
- **User Search Page**: 
  - Added "Drops" column to display user's current drop count
  - Added "Add Drop" button for quick penalty application
  - Confirmation dialog to prevent accidental penalties

- **User Detail Page**:
  - Added drop count display in Performance Metrics section (shown in red)
  - Added "Drop Penalty" control in Admin Controls section
  - Confirmation dialog when adding penalty
  - Success message showing new drop count

### 2. Database Changes
- **User Model**: Already had `drops` field (integer, default=0)
- **New Model**: `Roster_Penalty_Entries` to track penalties in published rosters
  - Stores: roster_id, tournament_id, event_id, penalized_user_id, original_rank, drops_applied
  - Used to show "+1" entries in published rosters instead of user names

### 3. Roster System Modifications
- **Penalty Filtering**: New function `filter_drops_and_track_penalties()`
  - Removes users with drops > 0 from tournament rosters
  - Automatically decrements user's drop count by 1 when penalty is applied
  - Tracks penalty information for display purposes
  - Finds replacement users from those without drops

- **View Tournament**: 
  - Shows penalized users in black highlight
  - Displays their replacement underneath
  - Penalty information shown in separate table section

- **Saved Rosters**:
  - Penalty information is saved with roster data
  - When published, penalized entries show as "+1" instead of user names
  - When unpublished, shows actual user names for admin reference

### 4. Backend Routes
- `POST /admin/add_drop/<user_id>`: Quick add drop from search page
- `POST /admin/user_detail/<user_id>` with `action=add_drop`: Add drop from detail page

### 5. UI/UX Features
- **Black highlighting** for penalized users in roster views
- **Confirmation dialogs** to prevent accidental penalty application
- **Clear messaging** about penalty status and drop counts
- **Conditional display**: Shows user names vs "+1" based on publication status

## How It Works

### Adding a Penalty
1. Admin searches for user in admin panel
2. Clicks "Add Drop" button (with confirmation)
3. User's `drops` field increments by 1
4. Success message confirms penalty was added

### Tournament Roster Generation
1. System gets all signups for tournament
2. Ranks users by weighted points
3. **NEW**: Filters out users with drops > 0
4. For each penalized user:
   - Records penalty information (user, rank, drops applied)
   - Decrements their drops count by 1
   - Finds next available replacement
5. Generates roster with filtered users
6. Displays penalty information separately

### Published Rosters
- **For admins**: Shows actual penalized user names
- **For published view**: Shows "+1 (Penalty Applied)" instead of names
- Penalty count increments the roster numbers without revealing identities

## Files Modified

### Backend
- `mason_snd/models/auth.py`: Added `Roster_Penalty_Entries` model
- `mason_snd/blueprints/admin/admin.py`: Added drop penalty routes and logic
- `mason_snd/blueprints/rosters/rosters.py`: Added penalty filtering and tracking

### Frontend Templates
- `mason_snd/templates/admin/search.html`: Added drops column and add drop button
- `mason_snd/templates/admin/user_detail.html`: Added drop display and penalty controls
- `mason_snd/templates/rosters/view_tournament.html`: Added penalty display section
- `mason_snd/templates/rosters/view_roster.html`: Added penalty display with conditional formatting

### Database
- `add_penalty_table.py`: Script to create the new penalty entries table

## Testing
- Created test script to verify drop penalty functionality
- Syntax checks pass for all modified files
- Database table creation successful

## Security Features
- Proper role checking (admin access only)
- CSRF token protection on forms
- Confirmation dialogs for destructive actions
- Session validation

The implementation successfully addresses all requirements:
✅ Admin panel search with drop penalty option
✅ Automatic roster removal when user has drops
✅ Black highlighting for penalized users
✅ Replacement user display
✅ Published roster anonymization ("+1" instead of names)
✅ Proper penalty tracking and application
