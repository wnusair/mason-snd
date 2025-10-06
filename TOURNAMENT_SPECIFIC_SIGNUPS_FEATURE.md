# Tournament-Specific Signup Management Feature

## Overview
This feature provides administrators with the ability to view and download tournament signups for individual tournaments, instead of only being able to download all signups from all tournaments.

## What Was Implemented

### 1. New Admin Routes
**Location**: `/workspaces/mason-snd/mason_snd/blueprints/admin/admin.py`

#### Route: `/admin/view_tournament_signups/<int:tournament_id>`
- **Purpose**: Display a detailed table of all signups for a specific tournament
- **Access**: Admin only (role >= 2)
- **Features**:
  - Comprehensive table showing student details, events, judges, partners
  - Summary statistics (total signups, confirmed attendees, judge counts)
  - Color-coded event categories (Speech, LD, PF)
  - Status indicators for bringing judge and attendance confirmation

#### Route: `/admin/download_tournament_signups/<int:tournament_id>`
- **Purpose**: Download tournament-specific signups as Excel file
- **Access**: Admin only (role >= 2)
- **Features**:
  - Professional Excel formatting with styled headers
  - Tournament name in sheet title and filename
  - Same data structure as the global download but filtered to one tournament
  - Timestamped filenames to prevent overwrites

### 2. Enhanced Tournament Index Page
**Location**: `/workspaces/mason-snd/mason_snd/templates/tournaments/index.html`

Added admin-only buttons to both upcoming and past tournaments tables:
- **"View Signups"** button (purple) - Opens detailed signup view
- **"📥 Download"** button (green) - Downloads Excel file
- Buttons appear alongside existing actions (View Results, Delete, etc.)

### 3. New Template for Tournament Signup View
**Location**: `/workspaces/mason-snd/mason_snd/templates/admin/view_tournament_signups.html`

Features:
- Clean, responsive table layout
- Tournament information header with date and location
- Summary statistics cards showing:
  - Total signups
  - Confirmed attendees
  - Students bringing judges
  - Event type diversity
- Color-coded badges for event categories and status indicators
- Download button for easy Excel export
- Empty state handling when no signups exist

### 4. Updated Admin Dashboard
**Location**: `/workspaces/mason-snd/mason_snd/templates/admin/index.html`

- Clarified existing "Download ALL Signups" button to emphasize it covers all tournaments
- Added informational section directing admins to the tournaments page for individual tournament downloads

## Data Structure

The tournament-specific downloads include the same comprehensive data as the global download:

### Excel Columns (16 total):
1. **Signup ID** - Unique identifier
2. **Tournament Name** - Name of the tournament
3. **Tournament Date** - Date and time of tournament
4. **Student Name** - Full name of student
5. **Student Email** - Contact email
6. **Event Name** - Specific event (e.g., "Impromptu", "Lincoln Douglas")
7. **Event Category** - Type (Speech/LD/PF)
8. **Partner Name** - For partner events
9. **Bringing Judge** - Yes/No indicator
10. **Judge Name** - Name of judge being brought
11. **Is Going** - Attendance confirmation
12. **User ID** - Student's user ID
13. **Tournament ID** - Tournament identifier
14. **Event ID** - Event identifier
15. **Judge ID** - Judge's user ID (if applicable)
16. **Partner ID** - Partner's user ID (if applicable)

## User Experience Improvements

### Before This Feature:
- Admins had to download ALL signups from all tournaments
- No way to view signups for a specific tournament in the web interface
- Had to manually filter Excel data to see tournament-specific information

### After This Feature:
- ✅ View signups for any tournament directly in the web interface
- ✅ Download Excel files for individual tournaments
- ✅ Quick access from the tournaments index page
- ✅ Summary statistics for each tournament
- ✅ Maintain existing "Download ALL" functionality for comprehensive reports

## Access Control

- **Admin Only**: All new routes require role >= 2 (admin level)
- **Authentication Required**: Users must be logged in
- **Graceful Handling**: Non-admins are redirected with appropriate flash messages
- **Error Handling**: Missing tournaments return 404 errors

## File Output

Tournament-specific Excel files are named with the pattern:
```
{TournamentName}_signups_{YYYYMMDD_HHMMSS}.xlsx
```

Examples:
- `MASON_NOVICE_signups_20251006_142030.xlsx`
- `Regional_Qualifier_signups_20251006_143015.xlsx`

## Integration Points

### Existing Features:
- **Download ALL Signups**: Still available from admin dashboard, now clearly labeled
- **Roster Downloads**: Tournament-specific roster downloads remain unchanged
- **Tournament Management**: Integrates seamlessly with existing tournament workflows

### Database Models Used:
- `Tournament` - Tournament information
- `Tournament_Signups` - Signup records
- `User` - Student, judge, and partner information
- `Event` - Event details and categories

## Testing

Comprehensive test script created: `/workspaces/mason-snd/test_tournament_signup_features.py`

Tests verify:
- Route registration
- Database connectivity
- Admin user access
- Data structure integrity
- Error handling

## Quick Start Guide

### For Administrators:

1. **View Tournament Signups**:
   - Navigate to Tournaments page
   - Find desired tournament
   - Click "View Signups" button
   - Browse detailed table and statistics

2. **Download Tournament Signups**:
   - From tournaments page: Click "📥 Download" button
   - From signup view page: Click "📥 Download Excel" button
   - File automatically downloads to your device

3. **Download ALL Signups** (existing feature):
   - Go to Admin Dashboard
   - Click "📥 Download ALL Signups" card
   - Excel file with all tournaments included

## Technical Implementation Notes

### Dependencies:
- `pandas` - DataFrame creation and Excel export
- `openpyxl` - Excel styling and formatting
- Both already installed in the project

### Error Handling:
- Missing pandas/openpyxl: Flash message with redirect
- Tournament not found: 404 error
- No signups: Flash message with redirect to view page
- Authentication failures: Redirect to login
- Authorization failures: Redirect to profile with error message

### Performance Considerations:
- Efficient database queries with foreign key relationships
- Excel generation uses in-memory BytesIO for speed
- Column width auto-adjustment optimized for readability

## Future Enhancement Opportunities

- Date range filtering for signup downloads
- Email export functionality
- Bulk download options (multiple tournaments)
- Scheduled export capabilities
- CSV format options
- Integration with external reporting tools

---

## 🎉 Success Criteria Met

✅ **Tournament-specific VIEW functionality** - Detailed web interface for each tournament  
✅ **Tournament-specific DOWNLOAD functionality** - Excel export per tournament  
✅ **Admin-only access** - Proper security controls  
✅ **Clear UI integration** - Buttons on tournaments page  
✅ **Preserved existing functionality** - "Download ALL" still works  
✅ **Professional formatting** - Styled Excel output  
✅ **Comprehensive data** - All signup information included  
✅ **Error handling** - Graceful failure modes  
✅ **Documentation** - Complete implementation guide  

The feature is ready for production use!