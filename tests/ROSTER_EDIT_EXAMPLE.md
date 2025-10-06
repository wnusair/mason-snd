# Roster Edit Feature - Complete Example Walkthrough

## Real-World Scenario: Fixing a Tournament Roster

### Background
You've created a roster for the "Princeton Classic" tournament. After publishing, you realize:
1. One competitor's name is misspelled
2. You need to swap two competitors' rankings
3. A judge needs to be added
4. One competitor needs to be removed

Instead of manually recreating the roster, you can **download → edit → upload** in minutes!

---

## Step-by-Step Walkthrough

### STEP 1: Download the Current Roster

1. Navigate to the roster view page:
   ```
   Rosters → View Roster → "Princeton Classic Roster"
   ```

2. Click the **"Download"** button (green button in top right)

3. Excel file downloads: `roster_Princeton_Classic_20250106_143022.xlsx`

### STEP 2: Open and Review the Excel File

The file contains 3+ sheets:

#### **Sheet 1: "Judges"**
```
Judge Name       | Child          | Event              | Category | Number People Bringing | Judge ID | Child ID | Event ID
Mrs. Johnson     | Emily Johnson  | Lincoln Douglas    | LD       | 2                      | 15       | 23       | 3
Mr. Williams     | Alex Williams  | Policy Debate      | PF       | 4                      | 22       | 31       | 5
```

#### **Sheet 2: "Rank View"** ⭐ PRIMARY SHEET FOR COMPETITORS
```
Rank | Competitor Name | Partner | Weighted Points | Event              | Category | Status | User ID | Partner ID | Event ID
1    | John Smyth      |         | 450             | Lincoln Douglas    | LD       | Active | 41      |            | 3
2    | Sarah Martinez  |         | 425             | Lincoln Douglas    | LD       | Active | 38      |            | 3
3    | David Lee       |         | 400             | Lincoln Douglas    | LD       | Active | 52      |            | 3
```

#### **Sheet 3: "Lincoln Douglas"** (Event-specific sheet)
```
Event              | Category | Rank | Competitor    | Partner | Weighted Points | User ID | Event ID
Lincoln Douglas    | LD       | 1    | John Smyth    |         | 450             | 41      | 3
Lincoln Douglas    | LD       | 2    | Sarah Martinez|         | 425             | 38      | 3
```

### STEP 3: Make Your Edits

#### **Fix 1: Correct the Misspelled Name**
In "Rank View" sheet, Row 2:
```diff
- Rank | Competitor Name | User ID
- 1    | John Smyth      | 41      <- Typo in last name

+ 1    | John Smith      | 41      <- Fixed (keep User ID!)
```

**What happens**: Because User ID 41 is still there, the system knows it's the same person. The corrected name is just for display.

#### **Fix 2: Swap Rankings (Make Sarah #1, John #2)**

**Option A: Swap the User IDs** (Recommended)
```diff
In "Rank View" sheet:
- Rank | Competitor Name | User ID
- 1    | John Smith      | 41
- 2    | Sarah Martinez  | 38

+ 1    | Sarah Martinez  | 38      <- Swapped User ID
+ 2    | John Smith      | 41      <- Swapped User ID
```

**Option B: Reorder the rows**
```diff
Cut row 2 (Sarah Martinez) and insert above row 1
Result:
+ Rank | Competitor Name | User ID
+ 1    | Sarah Martinez  | 38      <- Now first
+ 2    | John Smith      | 41      <- Now second
```

#### **Fix 3: Add a New Judge**

In "Judges" sheet, add a new row:
```diff
+ Judge Name       | Child         | Event              | Category | Number People Bringing | Judge ID | Child ID | Event ID
+ Mrs. Thompson    | Mark Thompson | Lincoln Douglas    | LD       | 2                      | 67       | 71       | 3
```

**Tips**: 
- If you know the Judge ID, use it
- If not, just put the name and leave Judge ID blank (system will search by name)
- Same for Child ID

#### **Fix 4: Remove a Competitor**

In "Rank View" sheet:
```diff
- Delete row 3 (David Lee)
```
Just delete the entire row. That person won't be in the roster anymore.

### STEP 4: Save the Excel File

Save the file (keep the same name or rename it):
```
roster_Princeton_Classic_UPDATED.xlsx
```

### STEP 5: Upload the Updated Roster

1. Navigate to Upload Roster page:
   ```
   Rosters → Upload Roster
   ```

2. Select upload mode:
   ```
   ☑️ Update Existing Roster  (NOT "Create New Roster")
   ```

3. Select the roster to update:
   ```
   Dropdown: "Princeton Classic Roster (2025-01-06)"
   ```

4. Upload your file:
   ```
   Click "Choose File" → Select "roster_Princeton_Classic_UPDATED.xlsx"
   ```

5. Click **"Upload Roster"**

### STEP 6: Review the Results

After upload, you'll see:
```
✅ Roster 'Princeton Classic Roster' updated successfully! 
   Added 3 competitors and 3 judges. 0 warnings.
```

Or with warnings:
```
✅ Roster 'Princeton Classic Roster' updated successfully! 
   Added 3 competitors and 3 judges. 1 warnings.

⚠️ Row 15 in Rank View: Could not find user 'Unknown Person'
```

### STEP 7: Verify Changes

Navigate back to the roster view:
```
Rosters → View Roster → "Princeton Classic Roster"
```

Verify:
- ✅ John Smith's name is spelled correctly
- ✅ Sarah Martinez is now ranked #1
- ✅ Mrs. Thompson is added as a judge
- ✅ David Lee is removed

---

## Advanced Techniques

### Technique 1: Bulk Name Updates

**Scenario**: Fix multiple typos at once

In Excel, use Find & Replace:
```
Find: "Smyth"
Replace: "Smith"
Replace All → Fixes all instances
```

### Technique 2: Reordering by Points

**Scenario**: Want to re-rank based on updated points

1. In "Rank View" sheet, sort by "Weighted Points" (highest to lowest)
2. Manually adjust User IDs if needed
3. Upload

### Technique 3: Template Creation

**Scenario**: Creating multiple similar rosters

1. Download an existing roster
2. Clear competitor data (keep structure)
3. Fill in new names
4. Upload as "Create New Roster"

### Technique 4: Cross-Tournament Transfers

**Scenario**: Moving competitors from one roster to another

1. Download Roster A
2. Copy rows from "Rank View" sheet
3. Download Roster B
4. Paste rows into Roster B's "Rank View" sheet
5. Upload to update Roster B

---

## Common Mistakes & Solutions

### ❌ Mistake 1: Editing Event View Instead of Rank View
**Problem**: Changes in event-specific sheets are ignored.
**Solution**: Always edit the "Rank View" sheet for competitor changes.

### ❌ Mistake 2: Deleting User IDs When Just Fixing Names
**Problem**: System can't find the person, treats it as a new entry.
**Solution**: Keep User ID intact when fixing spelling/typos.

### ❌ Mistake 3: Using "Create New Roster" for Updates
**Problem**: Creates a duplicate instead of updating.
**Solution**: Use "Update Existing Roster" mode.

### ❌ Mistake 4: Manually Changing Event IDs
**Problem**: Might mismatch events.
**Solution**: Let the system handle Event IDs automatically.

---

## Tips for Success

### ✅ Do's
- ✅ **Keep User IDs** when you want the same person
- ✅ **Edit Rank View** for competitor changes
- ✅ **Sort/filter in Excel** for easier editing
- ✅ **Save backups** before major changes
- ✅ **Check warnings** after upload

### ❌ Don'ts
- ❌ Don't edit Event View sheets (use Rank View)
- ❌ Don't manually change Weighted Points (read-only)
- ❌ Don't forget to select "Update Existing Roster"
- ❌ Don't upload .csv files (must be .xlsx)
- ❌ Don't delete the sheet names (system needs them)

---

## Keyboard Shortcuts in Excel

Speed up your editing:

| Action | Windows | Mac |
|--------|---------|-----|
| Find & Replace | Ctrl+H | Cmd+H |
| Insert Row | Ctrl+Shift+= | Cmd+Shift+= |
| Delete Row | Ctrl+- | Cmd+- |
| Cut Row | Ctrl+X | Cmd+X |
| Copy Row | Ctrl+C | Cmd+C |
| Paste Row | Ctrl+V | Cmd+V |
| Sort Data | Alt+A+S+S | Cmd+Shift+F |

---

## Troubleshooting Guide

### Issue: "Could not find user 'Jane Doe'"

**Cause**: No user named "Jane Doe" in database.

**Solutions**:
1. Check spelling: "Jane Doe" vs "Jane  Doe" (extra space)
2. Check if user exists in system
3. Use User ID instead of name
4. Create user first, then add to roster

### Issue: Upload seems to work but nothing changed

**Cause**: Uploaded to wrong roster or used "Create New" instead of "Update"

**Solutions**:
1. Verify you selected the correct roster in dropdown
2. Confirm "Update Existing Roster" was selected
3. Check if a new roster was created instead

### Issue: Ranks are all wrong after upload

**Cause**: Rows were reordered but ranks weren't updated

**Solutions**:
- Ranks are auto-calculated from row order
- Ensure rows are in the order you want
- The "Rank" column in spreadsheet is for reference only

### Issue: Partner information is lost

**Cause**: Partner ID was deleted or incorrect

**Solutions**:
- Keep Partner ID column intact
- If adding new partners, include their User ID
- Partners must both be in the same event

---

## Complete Before/After Example

### BEFORE (Downloaded Excel):
```
Rank | Competitor Name  | User ID | Event ID
1    | John Smyth       | 41      | 3       <- Typo + want rank 2
2    | Sarah Martinez   | 38      | 3       <- Want rank 1
3    | David Lee        | 52      | 3       <- Remove
4    | Emily Chen       | 29      | 3       <- Keep rank 3
```

### EDITS MADE:
1. Row 1: Fix "Smyth" → "Smith", change User ID to 38 (Sarah)
2. Row 2: Change User ID to 41 (John)
3. Row 3: DELETE THIS ROW
4. Row 4: Becomes row 3

### AFTER (Edited Excel):
```
Rank | Competitor Name  | User ID | Event ID
1    | Sarah Martinez   | 38      | 3       <- Was rank 2
2    | John Smith       | 41      | 3       <- Was rank 1, fixed name
3    | Emily Chen       | 29      | 3       <- Was rank 4
```

### RESULT IN SYSTEM:
```
Rank 1: Sarah Martinez (ID: 38)
Rank 2: John Smith (ID: 41) - name corrected
Rank 3: Emily Chen (ID: 29)
[David Lee removed]
```

---

## Summary

**The roster edit feature gives you:**
- 📥 **Easy export** of roster data to Excel
- ✏️ **Flexible editing** with familiar spreadsheet tools
- 🤖 **Smart matching** that handles name changes automatically
- 📤 **Simple re-import** to update rosters
- ⚠️ **Clear feedback** on what was changed and any issues

**Remember the golden rule**: 
> User IDs are the source of truth. Keep them to preserve identity, delete them to match by name.

---

**Need help?** Check the warnings after upload or refer to the Quick Reference guide!
