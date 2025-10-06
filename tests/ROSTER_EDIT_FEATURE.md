# Roster Download/Edit/Upload Feature

## Overview
This feature allows administrators to download rosters as Excel spreadsheets, edit them offline, and re-upload them with automatic data reconciliation. The system intelligently matches users and updates roster information based on the changes made in the spreadsheet.

## Key Features

### 📥 Download Rosters
- Download any roster as a comprehensive Excel file (`.xlsx`)
- Multiple sheets included:
  - **Judges Sheet**: All judge assignments with event and child information
  - **Rank View Sheet**: Primary competitor list with ranking and points
  - **Event View Sheets**: One sheet per event showing competitors in that event

### ✏️ Edit Spreadsheets
You can edit the following in the downloaded spreadsheet:

#### **Names (Primary Edit Feature)**
- Change competitor names (First Last format)
- Change judge names
- The system will automatically find users by ID or match by name

#### **Add/Remove Entries**
- Add new rows to add competitors or judges
- Delete rows to remove them from the roster
- Reorder rows to change ranking

#### **What You DON'T Need to Change**
- **Event IDs** - Automatically updated when you change events
- **User IDs** - Used for matching, but name takes precedence
- **Ranks** - Automatically recalculated based on order
- **Points** - Read-only, pulled from database

### 📤 Upload Edited Rosters

#### **Two Upload Modes**

1. **Create New Roster**
   - Upload a spreadsheet to create a brand new roster
   - Assign a unique name
   - All data is imported fresh

2. **Update Existing Roster**
   - Select which roster to update from dropdown
   - Upload the modified spreadsheet
   - Existing data is replaced with new data
   - Roster name can optionally be changed

## How It Works

### Smart User Matching Algorithm

The system uses a three-tier approach to match users:

1. **User ID Match (Highest Priority)**
   - If the User ID column has a value, that user is selected
   - Names are ignored when User ID is present
   - **Use Case**: You want to change how a name appears but keep the same person

2. **Exact Name Match**
   - Matches "FirstName LastName" format exactly
   - Case-insensitive matching
   - **Use Case**: You deleted the User ID and want to match by name

3. **Fuzzy Name Match**
   - Case-insensitive partial matching
   - **Use Case**: Minor spelling variations

### Example Scenarios

#### Scenario 1: Replacing Someone in a Rank
**Goal**: Replace the person ranked #1 with someone ranked #99

**In the Spreadsheet (Rank View sheet)**:
```
Before:
Rank | Competitor Name | User ID | Event ID
1    | John Smith      | 15      | 3
...
99   | Sarah Jones     | 42      | 3

After (swap User IDs):
Rank | Competitor Name | User ID | Event ID  
1    | Sarah Jones     | 42      | 3    <- Changed User ID to 42
...
99   | John Smith      | 15      | 3    <- Changed User ID to 15
```

**What Happens**: The system sees User ID 42 is now rank 1, so Sarah Jones becomes rank 1. All event info, parent info, etc. is automatically pulled from Sarah's profile.

#### Scenario 2: Fixing a Misspelled Name
**Goal**: Fix a typo in someone's name

**In the Spreadsheet**:
```
Before:
Rank | Competitor Name | User ID | Event ID
1    | Jhon Smith      | 15      | 3    <- Typo in first name

After:
Rank | Competitor Name | User ID | Event ID
1    | John Smith      | 15      | 3    <- Fixed spelling, kept User ID
```

**What Happens**: Because User ID 15 is still there, the system uses that person regardless of the name change. The corrected name is just for display in the spreadsheet.

#### Scenario 3: Adding a New Competitor
**Goal**: Add someone new to the roster

**In the Spreadsheet (add new row)**:
```
Rank | Competitor Name | User ID | Event ID
...
25   | Alex Johnson    |         | 3      <- Leave User ID blank
```

**What Happens**: System searches for a user named "Alex Johnson" in the database and adds them to the roster.

## Workflow Guide

### Step-by-Step: Download → Edit → Upload

1. **Download the Roster**
   ```
   Navigate to roster view → Click "Download" button → Save .xlsx file
   ```

2. **Edit in Excel/Spreadsheet App**
   ```
   Open the file in Excel, Google Sheets, or similar
   Make your changes to names, add/remove rows, reorder
   Save the file
   ```

3. **Upload the Modified File**
   ```
   Navigate to Upload Roster page → Select "Update Existing Roster"
   Choose the roster from dropdown → Upload your file → Submit
   ```

4. **Review Changes**
   ```
   System shows summary: "Added X competitors, Y judges, Z warnings"
   View the updated roster to verify changes
   ```

## Visual Indicators in Excel

The downloaded spreadsheet uses color coding:

- **Blue Headers**: Column headers (all sheets)
- **Light Blue Background**: ID columns (User ID, Event ID, etc.) - used for matching
- **Light Gray Background**: Calculated/informational fields (Rank, Points, Status)
- **White Background**: Editable fields (Names, etc.)

## Important Notes

### ⚠️ Critical Information

1. **Primary Sheet for Competitors**: The "Rank View" sheet is the primary source for competitor data. Always edit this sheet for competitor changes.

2. **User ID vs Name**: 
   - If User ID is present → User is matched by ID (name is ignored)
   - If User ID is blank → User is matched by name

3. **Events Cannot Be Changed**: While you can see Event ID columns, changing events requires re-adding the competitor

4. **Backup Before Upload**: When updating an existing roster, the old data is completely replaced

### ✅ Best Practices

1. **Always use "Update Existing Roster"** when modifying a downloaded roster
2. **Keep User IDs** unless you specifically want to change the person
3. **Test with a duplicate roster first** if making major changes
4. **Check warnings** after upload - they indicate issues with matching

## Error Handling

### Common Warnings

- **"Could not find user 'Name'"**: The name doesn't match any user in the database
  - Solution: Check spelling, ensure user exists, or add User ID

- **"Could not find event 'Event Name'"**: Event doesn't exist
  - Solution: Verify event name matches exactly, or use Event ID

### Upload Validation

The system provides detailed feedback:
- ✅ Success count (competitors and judges added)
- ⚠️ Warning count (rows that couldn't be processed)
- 📝 First 5 warnings are displayed with row numbers

## Advanced Use Cases

### Mass Updates
Download roster → Use Excel formulas to bulk update → Re-upload

### Template Creation
Download a well-formed roster → Clear data → Use as template for future rosters

### Data Migration
Export from one tournament → Modify for another → Import to new roster

## API Endpoints

### Download
```
GET /rosters/download_roster/<roster_id>
Returns: Excel file (.xlsx)
```

### Upload
```
POST /rosters/upload_roster
Form Data:
  - file: Excel file
  - roster_name: Name for new roster (optional for updates)
  - roster_id: ID of roster to update (optional)
  - upload_mode: 'new' or 'update'
```

## Technical Implementation

### Smart Matching Function
```python
def find_user_smart(user_id_val, name_val):
    # 1. Try User ID first (most reliable)
    if user_id is valid:
        return User.query.get(user_id)
    
    # 2. Try exact name match
    if name exists:
        return User.query.filter_by(first_name, last_name)
    
    # 3. Try fuzzy name match (case-insensitive)
    return User.query.filter(lower(first_name), lower(last_name))
    
    return None  # No match found
```

### Data Flow
1. Excel file uploaded → pandas reads sheets
2. Each row processed through smart matcher
3. Roster_Competitors and Roster_Judge entries created/updated
4. Transaction committed with change logging
5. User redirected to view updated roster

## Support and Troubleshooting

### FAQ

**Q: What happens if I upload the same file twice?**
A: If updating an existing roster, old data is deleted first, so you'll get the same result.

**Q: Can I change someone's points in the spreadsheet?**
A: No, points are read-only and pulled from the database. Changes in the spreadsheet are ignored.

**Q: Why didn't my changes save?**
A: Check the warnings after upload. Most likely the names or IDs didn't match any users in the database.

**Q: Can I add new users through the spreadsheet?**
A: No, users must already exist in the database. The spreadsheet only assigns existing users to rosters.

**Q: What if two people have the same name?**
A: Use the User ID column to specify exactly which person you want. Names alone may match the wrong person.

### Getting Help

If you encounter issues:
1. Check the flash messages after upload for specific error details
2. Review the warnings (row numbers help identify problems)
3. Verify User IDs and Event IDs in your spreadsheet match the database
4. Contact your system administrator with the error message and the file you tried to upload

---

**Last Updated**: 2025-01-06
**Feature Version**: 1.0
