# Deletion Management System

## Overview

The Deletion Management System provid3. **Delete Tournaments**
   - Click "Manage Tournament Deletion"
   - Select a tournament from the list
   - Click "Preview Deletion"
   - Review impact summary
   - Type "DELETE" to confirm
   - Click final confirmation

4. **Delete Events**
   - Click "Manage Event Deletion"
   - Select events with checkboxes
   - Click "Preview Deletion Impact"
   - Review what will be deleted
   - Type "DELETE" to confirm
   - Click final confirmation

5. **Quick User Deletion** and comprehensive way to delete users and tournaments from the database while maintaining referential integrity. The system automatically handles all foreign key relationships and provides detailed previews before performing any deletions.

## Recent Fixes (v2.0)

✅ **Fixed Route Naming Convention**: Changed from hyphens to underscores to match Flask app conventions
- `/delete-management` → `/delete_management`
- `/delete-users` → `/delete_users` 
- `/delete-tournaments` → `/delete_tournaments`

✅ **Added CSRF Protection**: All forms now include proper CSRF tokens to prevent security vulnerabilities

✅ **Template Updates**: All templates updated with correct route names and security tokens

## Features

### ✅ Safe Deletion
- **Cascade Deletion**: Automatically removes all related records to prevent foreign key violations
- **Transaction Safety**: All deletions are wrapped in database transactions
- **Rollback Protection**: Automatic rollback on any errors

### ✅ User Deletion
- Search users by name or email
- Bulk selection with checkboxes
- Preview impact before deletion
- Handles all related data:
  - Tournament signups and performances
  - Judge relationships and assignments
  - Partnership records (both tournament and roster)
  - Roster entries and penalties
  - Form responses and effort scores
  - User requirements and popups
  - Event ownership (transfers to admin or deletes)

### ✅ Tournament Deletion
- Select tournaments from a list
- Preview all related data
- Comprehensive deletion of:
  - User signups and performances
  - Form fields and responses
  - Tournament-specific rosters
  - Judge assignments and partnerships
  - Published roster entries and penalties

### ✅ Event Deletion
- Select events from a comprehensive list
- Bulk selection with checkboxes  
- Preview impact before deletion
- Handles all related data:
  - User event participation records
  - Effort scores and evaluations
  - Tournament signups for specific events
  - Roster entries and judge assignments
  - Partnership records for partner events
  - Published roster entries and penalties

### ✅ Safety Features
- **Multi-step confirmation**: Preview → Type confirmation → Final warning
- **Admin-only access**: Restricted to users with role >= 2
- **Self-protection**: Cannot delete your own account
- **Detailed logging**: Shows exactly what will be deleted
- **Error handling**: Graceful failure with detailed error messages

## How to Use

### Web Interface

1. **Access the System**
   - Log in as an admin (role >= 2)
   - Go to Admin Dashboard
   - Click "🗑️ Deletion Management"

2. **Delete Users**
   - Click "Manage User Deletion"
   - Search for users by name or email
   - Select users with checkboxes
   - Click "Preview Deletion Impact"
   - Review what will be deleted
   - Type "DELETE" to confirm
   - Click final confirmation

3. **Delete Events**
   - Click "Manage Event Deletion"
   - Select events with checkboxes
   - Click "Preview Deletion Impact"
   - Review what will be deleted
   - Type "DELETE" to confirm
   - Click final confirmation

4. **Quick User Deletion**
   - From any user detail page
   - Look for "⚠️ Danger Zone" section
   - Click "🗑️ Delete User & All Data"
   - Confirm with user's full name

### Programmatic Usage

```python
from mason_snd.models.deletion_utils import (
    delete_user_safely,
    delete_tournament_safely,
    delete_event_safely,
    delete_multiple_users,
    delete_multiple_events,
    get_user_deletion_preview,
    get_tournament_deletion_preview,
    get_event_deletion_preview
)

# Preview what would be deleted
user_preview = get_user_deletion_preview(user_id)
print(f"Would delete {user_preview['total_related']} related records")

event_preview = get_event_deletion_preview(event_id)
print(f"Event: {event_preview['event_name']} - {event_preview['total_related']} related records")

# Delete a single user
result = delete_user_safely(user_id)
if result.success:
    print(f"Success: {result.get_summary()}")
else:
    print(f"Errors: {result.errors}")

# Delete multiple events
result = delete_multiple_events([event_id1, event_id2, event_id3])

# Delete a tournament
result = delete_tournament_safely(tournament_id)
```

## Database Tables Handled

### User Deletion
| Table | Relationship | Action |
|-------|-------------|---------|
| `User_Published_Rosters` | user_id | DELETE |
| `Roster_Penalty_Entries` | penalized_user_id | DELETE |
| `Judges` | judge_id, child_id | DELETE |
| `Tournament_Judges` | judge_id, child_id | DELETE |
| `Tournament_Partners` | partner1_user_id, partner2_user_id | DELETE |
| `Roster_Partners` | partner1_user_id, partner2_user_id | DELETE |
| `Form_Responses` | user_id | DELETE |
| `Tournament_Signups` | user_id, judge_id, partner_id | DELETE |
| `Tournaments_Attended` | user_id | DELETE |
| `Tournament_Performance` | user_id | DELETE |
| `User_Event` | user_id | DELETE |
| `Effort_Score` | user_id, given_by_id | DELETE |
| `Roster_Judge` | user_id, child_id | DELETE |
| `Roster_Competitors` | user_id, judge_id | DELETE |
| `User_Requirements` | user_id | DELETE |
| `Popups` | user_id, admin_id | DELETE |
| `Event` | owner_id | TRANSFER or DELETE |
| `User` | id | DELETE |

### Tournament Deletion
| Table | Relationship | Action |
|-------|-------------|---------|
| `User_Published_Rosters` | tournament_id | DELETE |
| `Roster_Penalty_Entries` | tournament_id | DELETE |
| `Form_Responses` | tournament_id | DELETE |
| `Form_Fields` | tournament_id | DELETE |
| `Tournament_Signups` | tournament_id | DELETE |
| `Tournaments_Attended` | tournament_id | DELETE |
| `Tournament_Performance` | tournament_id | DELETE |
| `Tournament_Judges` | tournament_id | DELETE |
| `Tournament_Partners` | tournament_id | DELETE |
| `Roster` | tournament_id | DELETE (with all related) |
| `Tournament` | id | DELETE |

### Event Deletion
| Table | Relationship | Action |
|-------|-------------|---------|
| `User_Published_Rosters` | event_id | DELETE |
| `Roster_Penalty_Entries` | event_id | DELETE |
| `Tournament_Signups` | event_id | DELETE |
| `Tournament_Judges` | event_id | DELETE |
| `Tournament_Partners` | event_id | DELETE |
| `Roster_Judge` | event_id | DELETE |
| `Roster_Competitors` | event_id | DELETE |
| `User_Event` | event_id | DELETE |
| `Effort_Score` | event_id | DELETE |
| `Event` | id | DELETE |

## Safety Measures

### 🔒 Access Control
- Only admin users (role >= 2) can access deletion functions
- Self-deletion prevention (cannot delete your own account)
- Session-based authentication required

### 🛡️ Data Protection
- **Atomic Transactions**: All deletions in a single transaction
- **Rollback on Error**: Automatic rollback if any step fails
- **Foreign Key Integrity**: Proper deletion order to prevent violations
- **Orphan Prevention**: Ensures no orphaned records remain

### ⚠️ User Confirmation
- **Search Required**: Must search to find users before deletion
- **Preview Step**: Shows exactly what will be deleted
- **Type Confirmation**: Must type "DELETE" to proceed
- **Final Warning**: JavaScript confirmation with full details
- **Detailed Feedback**: Shows success/failure with counts

### 📝 Audit Trail
- **Detailed Results**: Shows what was actually deleted
- **Error Logging**: Captures and reports any issues
- **Count Summary**: Provides totals for verification

## Error Handling

The system handles various error scenarios:

- **Database Constraints**: Catches foreign key violations
- **Missing Records**: Handles deleted/invalid IDs gracefully  
- **Transaction Failures**: Automatic rollback on any error
- **Permission Errors**: Validates admin access at each step
- **Malformed Requests**: Validates all input parameters

## Installation/Setup

The deletion system is automatically available once you:

1. Have the deletion utilities: `mason_snd/models/deletion_utils.py`
2. Have the updated admin blueprint: `mason_snd/blueprints/admin/admin.py`
3. Have the deletion templates in: `mason_snd/templates/admin/`
4. Access through the admin dashboard

No additional configuration required - it uses your existing database and Flask app setup.

## Testing

Use the provided test script to verify functionality:

```bash
python test_deletion_system.py
```

This will show previews for existing users and tournaments without actually deleting anything.

## Support

For issues or questions:
1. Check the error messages in the web interface
2. Review the database logs for constraint violations
3. Test with the preview function first
4. Ensure proper admin access (role >= 2)

**Remember**: All deletions are permanent and cannot be undone. Always use the preview function first!
