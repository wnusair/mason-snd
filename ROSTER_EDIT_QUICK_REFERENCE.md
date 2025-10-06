# Roster Edit Feature - Quick Reference

## 🚀 Quick Start

### Download → Edit → Upload
1. Open roster → Click "Download" → Get Excel file
2. Edit names in Excel (keep User IDs for matching)
3. Upload page → Select "Update Existing Roster" → Choose roster → Upload file

## 📋 What You Can Edit

| Editable | Column Name | Notes |
|----------|-------------|-------|
| ✅ Yes | Competitor Name | Changes displayed name |
| ✅ Yes | Judge Name | Changes displayed name |
| ✅ Yes | Child | Changes child name |
| ✅ Yes | Partner | Changes partner name |
| ✅ Yes | Add/Delete Rows | Adds/removes from roster |
| ❌ No | User ID | Used for matching only |
| ❌ No | Event ID | Used for matching only |
| ❌ No | Weighted Points | Read-only from database |
| ❌ No | Rank | Auto-calculated |

## 🎯 Common Tasks

### Replace Person at Rank #1 with Person at Rank #99
```
In Rank View sheet:
Row with Rank 1: Change User ID from 15 to 42 (person at rank 99)
Row with Rank 99: Change User ID from 42 to 15 (person at rank 1)
```
Upload → Done! The algorithm handles everything else.

### Fix Misspelled Name
```
Row with typo: Fix the name, KEEP the User ID
```
Upload → The User ID ensures it's the same person.

### Add New Competitor
```
Add new row at bottom:
- Competitor Name: "Alex Johnson"
- User ID: (leave blank)
- Event ID: (same as other competitors in that event)
```
Upload → System finds "Alex Johnson" and adds them.

### Remove Someone
```
Delete their row in the Rank View sheet
```
Upload → They're removed from roster.

## ⚠️ Important Rules

1. **User ID beats Name**: If User ID is filled, that person is used (name is ignored)
2. **Rank View is Primary**: Make competitor changes in "Rank View" sheet
3. **Names Must Exist**: Can't create new users, only assign existing ones
4. **Update Mode for Re-uploads**: Always use "Update Existing Roster" when re-uploading

## 🔍 Matching Logic

```
User ID Present? 
  ├─ YES → Use that user (ignore name)
  └─ NO → Search by name
      ├─ Exact match found? → Use that user
      ├─ Case-insensitive match? → Use that user
      └─ No match → ⚠️ Warning
```

## 🎨 Color Guide in Excel

- 🔵 **Blue Headers**: All column headers
- 💙 **Light Blue**: ID columns (User ID, Event ID) - matching keys
- ⚪ **Light Gray**: Calculated fields (Rank, Points) - read-only
- ⬜ **White**: Editable fields (Names)

## ✅ Success Messages

After upload, you'll see:
- `✅ "Added X competitors and Y judges"` - Success count
- `⚠️ "Z warnings"` - Issues (names not found, etc.)
- Individual warnings shown (first 5)

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| "Could not find user" | Check spelling or add User ID |
| Changes didn't save | Check warnings for specific rows |
| Wrong person added | Use User ID to be specific |
| Upload failed | Check file format (.xlsx only) |

## 📊 Excel Sheets Explained

| Sheet Name | Purpose | Primary Use |
|-----------|---------|-------------|
| Judges | All judge assignments | Edit judge names, events |
| Rank View | **Primary competitor list** | Edit competitors, reorder |
| [Event Name] | Competitors in specific event | View-only (use Rank View) |

## 💡 Pro Tips

1. **Keep a backup**: Download before making major changes
2. **Test first**: Use a duplicate roster for major edits
3. **User IDs are your friend**: They guarantee exact matching
4. **Sort by rank**: Keep rows in rank order for clarity
5. **Check event IDs**: Ensure they match between rows in same event

## 🔗 Related Features

- **Publish Roster**: Share with competitors (view_roster page)
- **Rename Roster**: Change roster name (view_roster page)
- **Download for Tournament**: Get roster from tournament view

---
**Pro Tip**: The "User ID" column is like a database key - it always wins over names!
