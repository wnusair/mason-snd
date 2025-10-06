# Quick Start: Download All Signups

## Installation (One-Time Setup)

```bash
# Install required libraries
pip install pandas openpyxl
```

Or update from requirements.txt:
```bash
pip install -r requirements.txt
```

## Usage

### Step 1: Start the Application
```bash
python run.py
# or
flask run
```

### Step 2: Access as Admin
1. Open your browser
2. Navigate to your application URL (e.g., `http://localhost:5000`)
3. Log in with an admin account (role >= 2)

### Step 3: Download Signups
1. Go to the Admin Dashboard (`/admin`)
2. Click the **"📥 Download All Signups"** card
3. Your browser will automatically download the Excel file

### Step 4: Open the File
The file will be named: `all_signups_YYYYMMDD_HHMMSS.xlsx`

Example: `all_signups_20251006_143530.xlsx`

## What You'll Get

An Excel file with the following columns:

**Signup Information:**
- Signup ID
- Tournament Name
- Tournament Date
- Student Name
- Student Email
- Event Name
- Event Category (Speech/LD/PF)
- Partner Name (if applicable)
- Bringing Judge (Yes/No)
- Judge Name (if applicable)
- Is Going (Yes/No)

**Reference IDs:**
- User ID
- Tournament ID
- Event ID
- Judge ID
- Partner ID

## Features

✅ **Styled Headers**: Professional blue background with white text  
✅ **Auto-Width Columns**: Optimized for readability  
✅ **All Signups**: Every signup in the system, all tournaments  
✅ **Complete Data**: Student, event, tournament, judge, and partner info  
✅ **Timestamped**: Never overwrite previous exports  

## Troubleshooting

### "Excel functionality not available"
**Solution**: Install pandas and openpyxl
```bash
pip install pandas openpyxl
```

### "No signups found"
**Solution**: The database has no signup records. To create test data:
```bash
python -m tests.create_sample_data
```

### "You are not authorized"
**Solution**: Log in with an admin account (role >= 2)

### File won't open in Excel
**Check**: 
- File extension is `.xlsx`
- Excel or compatible software is installed
- File isn't corrupted (try re-downloading)

## Testing

Verify the feature works:
```bash
python test_download_signups.py
```

This will show:
- Current signup count
- Sample data structure
- All available columns
- Usage instructions

## Common Use Cases

### 1. Export Email List
Open the Excel file and copy the "Student Email" column for bulk emails.

### 2. Analyze Tournament Participation
Filter by "Tournament Name" to see who's attending specific tournaments.

### 3. Judge Coordination
Filter by "Bringing Judge" = "Yes" to see which students are bringing judges.

### 4. Event Planning
Sort by "Event Category" to group signups by event type (Speech/LD/PF).

### 5. Partner Verification
Check the "Partner Name" column to verify partner event registrations.

## Tips

💡 **Regular Backups**: Download periodically to backup signup data  
💡 **Version Control**: Timestamps prevent overwriting previous exports  
💡 **Data Analysis**: Import into Google Sheets or other tools for analysis  
💡 **Reporting**: Share with coaches, event coordinators, or administrators  

## Direct URL

Once logged in as admin, you can also access directly:
```
http://localhost:5000/admin/download_all_signups
```

## Security Note

🔒 This feature is **admin-only** for data security. Regular users cannot access it.

## Support

Need help? Check:
1. `DOWNLOAD_SIGNUPS_FEATURE.md` - Full documentation
2. `DOWNLOAD_SIGNUPS_SUMMARY.md` - Implementation details
3. Flask application logs for error messages
