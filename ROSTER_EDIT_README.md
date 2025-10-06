# 📊 Roster Edit Feature - README

## 🎯 What This Feature Does

**Download** rosters as Excel → **Edit** them offline → **Upload** to automatically update the roster.

Perfect for:
- Fixing name typos
- Swapping competitor rankings
- Adding/removing participants
- Bulk editing judges

## 🚀 Quick Start (3 Steps)

### 1. Download
```
View Roster → Click "Download" → Save Excel file
```

### 2. Edit
```
Open in Excel → Make changes → Save file
```

### 3. Upload
```
Upload Page → "Update Existing Roster" → Select roster → Upload → Done!
```

## ✨ What You Can Edit

| Editable | Not Editable (Auto-handled) |
|----------|---------------------------|
| ✅ Names (competitors, judges) | ❌ User IDs (used for matching) |
| ✅ Add rows (new people) | ❌ Event IDs (auto-updated) |
| ✅ Delete rows (remove people) | ❌ Weighted Points (from database) |
| ✅ Reorder rows (change ranks) | ❌ Calculated fields |

## 🔑 Key Concept: User ID vs Name

```
User ID Present → System uses that person (name ignored)
User ID Blank   → System searches by name
```

**Example**: To fix a typo, change the name but KEEP the User ID.

## 📋 Excel Sheet Guide

Your downloaded file has these sheets:

- **Judges** - All judge assignments (edit names, add/remove)
- **Rank View** ⭐ - PRIMARY sheet for competitors (edit here!)
- **[Event Names]** - View-only per-event sheets (reference)

## 💡 Common Tasks

### Fix a Name
```
Keep User ID, change name → Upload
```

### Swap Two Rankings
```
Row 1: Change User ID to person from Row 2
Row 2: Change User ID to person from Row 1
Upload
```

### Add Someone
```
Add new row with name (leave User ID blank) → Upload
```

### Remove Someone
```
Delete their row → Upload
```

## ⚠️ Important Rules

1. **Always edit "Rank View" sheet** for competitors
2. **Keep User IDs** unless you want to change the person
3. **Use "Update Existing Roster"** mode when re-uploading
4. **Check warnings** after upload for any issues

## 🎨 Color Code in Excel

- 🔵 Blue: Column headers
- 💙 Light Blue: ID columns (matching keys)
- 🔲 Gray: Read-only fields
- ⬜ White: Editable fields

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [ROSTER_EDIT_QUICK_REFERENCE.md](ROSTER_EDIT_QUICK_REFERENCE.md) | Quick cheat sheet |
| [ROSTER_EDIT_EXAMPLE.md](ROSTER_EDIT_EXAMPLE.md) | Step-by-step walkthrough |
| [ROSTER_EDIT_FEATURE.md](ROSTER_EDIT_FEATURE.md) | Complete documentation |
| [ROSTER_EDIT_SUMMARY.md](ROSTER_EDIT_SUMMARY.md) | Technical implementation |

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| "Could not find user" | Check spelling or add User ID |
| Changes didn't save | Use "Update Existing Roster" mode |
| Wrong person added | Use User ID for exact matching |
| Excel won't open | Check pandas/openpyxl installed |

## 🔧 Installation

```bash
pip install pandas openpyxl
```

## 🧪 Testing

```bash
python test_roster_edit_feature.py
```

## 📊 Example Workflow

```
BEFORE (Excel):
Rank | Name          | User ID
1    | John Smyth    | 41      ← Typo, want rank 2
2    | Sarah Jones   | 38      ← Want rank 1
3    | David Lee     | 52      ← Remove

EDITS:
1. Fix typo: "Smyth" → "Smith"
2. Swap User IDs: 41 ↔ 38
3. Delete row 3

AFTER (Excel):
Rank | Name          | User ID
1    | Sarah Jones   | 38      ← Now rank 1
2    | John Smith    | 41      ← Now rank 2, fixed

RESULT:
✅ Sarah is rank 1
✅ John is rank 2 with corrected name
✅ David removed
```

## 🎓 Pro Tips

1. **Backup first** - Download before major edits
2. **Use User IDs** - Guaranteed exact matching
3. **Sort in Excel** - Organize before uploading
4. **Test with copies** - Try on duplicate roster first
5. **Read warnings** - They tell you what failed

## 🔗 Quick Links

- Upload Page: `/rosters/upload_roster`
- View Roster: `/rosters/view_roster/<id>`
- Download: `/rosters/download_roster/<id>`

## ❓ FAQ

**Q: Can I create new users in the spreadsheet?**
A: No, users must exist in the database first.

**Q: What happens if I upload the same file twice?**
A: Same result - old data replaced with spreadsheet data.

**Q: Can I edit multiple rosters at once?**
A: Not currently - upload each roster separately.

**Q: Do I need to update the Rank column manually?**
A: No, rank is auto-calculated from row order.

## 🚀 Getting Started Now

1. Open any roster in the system
2. Click the green "Download" button
3. Open the Excel file
4. Try editing a name (keep the User ID)
5. Go to Upload Roster page
6. Select "Update Existing Roster"
7. Choose your roster
8. Upload the file
9. See the magic happen! ✨

---

**Need Help?** Check the detailed docs or the quick reference guide!

**Feature Version:** 1.0
**Last Updated:** January 6, 2025
