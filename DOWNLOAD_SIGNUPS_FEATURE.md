# Download All Signups Feature

## Overview
This feature allows administrators to download all tournament signups as an Excel (.xlsx) file with comprehensive headers and formatting.

## Location
- **Route**: `/admin/download_all_signups`
- **Access Level**: Admin only (role >= 2)
- **Blueprint**: `admin_bp`

## Features

### 1. Comprehensive Data Export
The Excel file includes the following columns with headers:

| Column | Description |
|--------|-------------|
| Signup ID | Unique identifier for the signup |
| Tournament Name | Name of the tournament |
| Tournament Date | Date and time of the tournament |
| Student Name | Full name of the student |
| Student Email | Email address of the student |
| Event Name | Name of the event |
| Event Category | Type of event (Speech/LD/PF) |
| Partner Name | Partner's name (for partner events) |
| Bringing Judge | Whether student is bringing a judge (Yes/No) |
| Judge Name | Name of the judge being brought |
| Is Going | Confirmation status (Yes/No) |
| User ID | Internal user identifier |
| Tournament ID | Internal tournament identifier |
| Event ID | Internal event identifier |
| Judge ID | Internal judge identifier |
| Partner ID | Internal partner identifier |

### 2. Excel Formatting
- **Styled Headers**: Blue background (#4472C4) with white bold text
- **Auto-adjusted Column Widths**: Columns automatically resize for readability (max 50 chars)
- **Professional Layout**: Center-aligned headers with proper spacing

### 3. File Naming
Files are automatically named with a timestamp:
```
all_signups_YYYYMMDD_HHMMSS.xlsx
```
Example: `all_signups_20251006_143022.xlsx`

## Usage

### Via Web Interface
1. Log in as an admin user (role >= 2)
2. Navigate to the Admin Dashboard (`/admin`)
3. Click on **"📥 Download All Signups"** card
4. The Excel file will download automatically

### Programmatic Access
```python
from flask import url_for

# Generate download URL
download_url = url_for('admin.download_all_signups')
```

## Technical Implementation

### Dependencies
- **pandas**: For DataFrame creation and Excel writing
- **openpyxl**: For Excel file formatting and styling
- **Flask**: For request handling and file serving

### Code Flow
1. Verify user authentication and admin role
2. Check if pandas and openpyxl are available
3. Query all `Tournament_Signups` records
4. Join with related tables (User, Tournament, Event)
5. Build data dictionary with all required fields
6. Create pandas DataFrame
7. Export to Excel with styling
8. Return file as download

### Error Handling
- Redirects to login if not authenticated
- Shows error message if not admin
- Displays flash message if Excel libraries not installed
- Handles missing data gracefully (shows 'Unknown' for missing records)

## Installation Requirements

Add to `requirements.txt`:
```
pandas
openpyxl
```

Install with:
```bash
pip install pandas openpyxl
```

## Security Considerations
- ✅ Admin-only access (role check)
- ✅ Session-based authentication
- ✅ No SQL injection (uses ORM)
- ✅ Safe file generation (BytesIO in memory)

## Testing

### Test Script
Run the included test script:
```bash
python test_download_signups.py
```

This will:
- Check database connectivity
- Count available signups
- Display sample data structure
- Show all Excel columns
- Provide usage instructions

### Manual Testing
1. Create test signups using existing test data scripts
2. Log in as admin
3. Navigate to `/admin/download_all_signups`
4. Verify file downloads
5. Open Excel file and check:
   - All columns are present
   - Headers are styled (blue background, white text)
   - Data is complete and accurate
   - Column widths are appropriate

## Integration with Existing Features

### Comparison with Roster Download
- **Roster Download**: Specific to saved rosters with judge assignments
- **Signup Download**: All signups regardless of tournament or roster status

### Use Cases
1. **Event Planning**: See all signups across tournaments
2. **Capacity Planning**: Analyze signup patterns
3. **Communication**: Export email lists for specific tournaments
4. **Reporting**: Generate comprehensive signup reports
5. **Backup**: Create snapshots of signup data

## Admin Dashboard Integration
The feature is prominently displayed on the admin dashboard with:
- Indigo-themed card styling
- Download icon (📥)
- Clear description: "Export all tournament signups as Excel file"

## Future Enhancements (Optional)
- [ ] Filter by tournament
- [ ] Filter by date range
- [ ] Include additional statistics sheet
- [ ] Add CSV export option
- [ ] Batch export with multiple sheets per tournament
- [ ] Email export option

## Troubleshooting

### "Excel functionality not available"
**Solution**: Install pandas and openpyxl
```bash
pip install pandas openpyxl
```

### "No signups found"
**Solution**: Create test signups first
```bash
python -m tests.create_sample_data
```

### File won't download
**Checks**:
1. Verify you're logged in as admin
2. Check browser download settings
3. Verify sufficient disk space
4. Check Flask logs for errors

## Related Files
- `/workspaces/mason-snd/mason_snd/blueprints/admin/admin.py` - Route implementation
- `/workspaces/mason-snd/mason_snd/templates/admin/index.html` - Dashboard UI
- `/workspaces/mason-snd/test_download_signups.py` - Test script
- `/workspaces/mason-snd/requirements.txt` - Dependencies

## Support
For issues or questions, check:
1. Flask application logs
2. Browser console for client-side errors
3. Test script output for data verification
