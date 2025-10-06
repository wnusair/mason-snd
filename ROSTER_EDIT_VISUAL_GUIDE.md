# 🎨 Roster Edit Feature - Visual Guide

## 📸 Feature Overview (Visual)

```
┌─────────────────────────────────────────────────────────────┐
│                    ROSTER EDIT WORKFLOW                     │
│                                                             │
│  1️⃣  DOWNLOAD       2️⃣  EDIT         3️⃣  UPLOAD           │
│                                                             │
│  [Roster View]     [Excel App]     [Upload Page]          │
│       │                 │                 │                │
│       ├─► 📥           ├─► ✏️            ├─► 📤           │
│       │                 │                 │                │
│   Click             Change           Select              │
│  "Download"          Names           "Update"            │
│    Button           & Rows           & Upload            │
│       │                 │                 │                │
│       ▼                 ▼                 ▼                │
│   .xlsx file        Modified         Updated              │
│   Downloaded         .xlsx          Roster!               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 📊 Excel File Structure

```
┌─────────────────────────────────────────────────────────────┐
│                    DOWNLOADED EXCEL FILE                     │
└─────────────────────────────────────────────────────────────┘

📁 roster_Princeton_Classic_20250106.xlsx
│
├─── 📄 Sheet 1: "Judges"
│    ┌──────────────────────────────────────────────────┐
│    │ Judge Name   │ Child  │ Event │ Judge ID │ ...  │
│    ├──────────────┼────────┼───────┼──────────┼──────┤
│    │ Mrs. Smith   │ Emma   │ LD    │ 15       │ ...  │
│    │ Mr. Jones    │ Alex   │ PF    │ 22       │ ...  │
│    └──────────────────────────────────────────────────┘
│
├─── 📄 Sheet 2: "Rank View" ⭐ PRIMARY SHEET
│    ┌────────────────────────────────────────────────────────────┐
│    │ Rank│ Name         │ Points │ Event│ User ID│ Event ID│   │
│    ├─────┼──────────────┼────────┼──────┼────────┼─────────┼───┤
│    │  1  │ John Smith   │  450   │ LD   │  41    │    3    │   │
│    │  2  │ Sarah Jones  │  425   │ LD   │  38    │    3    │   │
│    │  3  │ David Lee    │  400   │ LD   │  52    │    3    │   │
│    └────────────────────────────────────────────────────────────┘
│
└─── 📄 Sheet 3+: Event Sheets (e.g., "Lincoln Douglas")
     ┌──────────────────────────────────────────────────┐
     │ Event  │ Rank │ Competitor    │ User ID │ ...   │
     ├────────┼──────┼───────────────┼─────────┼───────┤
     │ LD     │  1   │ John Smith    │  41     │ ...   │
     │ LD     │  2   │ Sarah Jones   │  38     │ ...   │
     └──────────────────────────────────────────────────┘
```

## 🎨 Color Coding in Excel

```
╔═══════════════════════════════════════════════════════════╗
║              EXCEL CELL COLOR MEANINGS                    ║
╚═══════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────┐
│ 🔵 DARK BLUE - Column Headers                        │
│    ┌──────────────────────────────────────────┐    │
│    │ Rank │ Competitor Name │ User ID │ ...   │    │
│    └──────────────────────────────────────────┘    │
│    All column titles are blue with white text      │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ 💙 LIGHT BLUE - ID Columns (Matching Keys)          │
│    ┌────────┬──────────┬──────────┬─────────┐      │
│    │ User ID│ Child ID │ Event ID │Partner ID│      │
│    ├────────┼──────────┼──────────┼─────────┤      │
│    │   41   │    23    │     3    │    38    │      │
│    └────────┴──────────┴──────────┴─────────┘      │
│    These are used for matching - keep them!         │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ 🔲 LIGHT GRAY - Read-Only/Calculated Fields         │
│    ┌──────┬────────────┬──────────┬────────┐       │
│    │ Rank │ Points     │ Status   │Category│       │
│    ├──────┼────────────┼──────────┼────────┤       │
│    │   1  │    450     │  Active  │  LD    │       │
│    └──────┴────────────┴──────────┴────────┘       │
│    System calculates these - edits ignored          │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ ⬜ WHITE - Editable Fields                          │
│    ┌─────────────────┬─────────────────┐           │
│    │ Competitor Name │ Judge Name      │           │
│    ├─────────────────┼─────────────────┤           │
│    │  John Smith     │  Mrs. Johnson   │           │
│    └─────────────────┴─────────────────┘           │
│    Edit these freely!                               │
└─────────────────────────────────────────────────────┘
```

## 🔍 Matching Algorithm (Visual)

```
┌─────────────────────────────────────────────────────┐
│         HOW THE SYSTEM FINDS THE RIGHT USER         │
└─────────────────────────────────────────────────────┘

Upload Row:
┌────────────────────────────────────────────┐
│ Competitor Name: "John Smith"              │
│ User ID:         41                        │
└────────────────────────────────────────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │ Is User ID present?   │
        └───────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
       YES                     NO
        │                       │
        ▼                       ▼
   ┌─────────┐          ┌──────────────┐
   │ Use ID  │          │ Search by    │
   │ #41     │          │ Name         │
   └─────────┘          └──────────────┘
        │                       │
        │               ┌───────┴────────┐
        │               │                │
        │         Exact Match      Case-Insensitive
        │               │                │
        ▼               ▼                ▼
   ✅ Found!       ✅ Found!         ✅ Found!
                                         │
                                   (No match?)
                                         │
                                         ▼
                                    ⚠️ Warning!

Result: User with matching ID/name added to roster
```

## 📝 Common Edit Scenarios (Visual)

### Scenario 1: Fix a Typo

```
BEFORE:
┌─────┬─────────────────┬──────────┐
│Rank │ Competitor Name │ User ID  │
├─────┼─────────────────┼──────────┤
│  1  │ John Smyth ❌    │   41     │
└─────┴─────────────────┴──────────┘

EDIT:
┌─────┬─────────────────┬──────────┐
│Rank │ Competitor Name │ User ID  │
├─────┼─────────────────┼──────────┤
│  1  │ John Smith ✅    │   41  ⭐ │ ← Keep User ID!
└─────┴─────────────────┴──────────┘

RESULT: ✅ Same person, corrected name
```

### Scenario 2: Swap Rankings

```
BEFORE:
┌─────┬─────────────────┬──────────┐
│Rank │ Competitor Name │ User ID  │
├─────┼─────────────────┼──────────┤
│  1  │ John Smith      │   41     │
│  2  │ Sarah Jones     │   38     │
└─────┴─────────────────┴──────────┘

SWAP USER IDs:
┌─────┬─────────────────┬──────────┐
│Rank │ Competitor Name │ User ID  │
├─────┼─────────────────┼──────────┤
│  1  │ Sarah Jones     │   38  ⭐ │ ← Swapped
│  2  │ John Smith      │   41  ⭐ │ ← Swapped
└─────┴─────────────────┴──────────┘

RESULT: ✅ Rankings reversed!
```

### Scenario 3: Add Someone

```
BEFORE:
┌─────┬─────────────────┬──────────┐
│Rank │ Competitor Name │ User ID  │
├─────┼─────────────────┼──────────┤
│  1  │ John Smith      │   41     │
│  2  │ Sarah Jones     │   38     │
└─────┴─────────────────┴──────────┘

ADD ROW:
┌─────┬─────────────────┬──────────┐
│Rank │ Competitor Name │ User ID  │
├─────┼─────────────────┼──────────┤
│  1  │ John Smith      │   41     │
│  2  │ Sarah Jones     │   38     │
│  3  │ Alex Johnson    │  (blank) │ ← New!
└─────┴─────────────────┴──────────┘

RESULT: ✅ Alex Johnson added (system finds by name)
```

### Scenario 4: Remove Someone

```
BEFORE:
┌─────┬─────────────────┬──────────┐
│Rank │ Competitor Name │ User ID  │
├─────┼─────────────────┼──────────┤
│  1  │ John Smith      │   41     │
│  2  │ Sarah Jones     │   38     │
│  3  │ David Lee       │   52     │
└─────┴─────────────────┴──────────┘

DELETE ROW 3:
┌─────┬─────────────────┬──────────┐
│Rank │ Competitor Name │ User ID  │
├─────┼─────────────────┼──────────┤
│  1  │ John Smith      │   41     │
│  2  │ Sarah Jones     │   38     │
└─────┴─────────────────┴──────────┘

RESULT: ✅ David Lee removed from roster
```

## 🖥️ Upload Page Interface

```
┌────────────────────────────────────────────────────┐
│                  UPLOAD ROSTER                     │
│                                                    │
│  ℹ️ Instructions Panel                             │
│  ┌──────────────────────────────────────────────┐ │
│  │ 1. Download roster as Excel                  │ │
│  │ 2. Edit names, add/remove rows               │ │
│  │ 3. Upload modified file                      │ │
│  │ 4. Changes auto-applied!                     │ │
│  └──────────────────────────────────────────────┘ │
│                                                    │
│  Upload Mode:                                      │
│  ○ Create New Roster                              │
│  ⦿ Update Existing Roster ✓                       │
│                                                    │
│  Select Roster: [Princeton Classic ▼]             │
│                                                    │
│  Choose File: [📁 roster_file.xlsx]               │
│                                                    │
│  [        📤 Upload Roster        ]               │
│                                                    │
└────────────────────────────────────────────────────┘
```

## ✅ Success Feedback

```
After Upload:

┌────────────────────────────────────────────────────┐
│ ✅ Success!                                         │
│                                                    │
│ Roster 'Princeton Classic' updated successfully!  │
│ Added 15 competitors and 5 judges.                │
│                                                    │
│ 0 warnings                                        │
└────────────────────────────────────────────────────┘

OR with warnings:

┌────────────────────────────────────────────────────┐
│ ✅ Success!                                         │
│                                                    │
│ Roster 'Princeton Classic' updated successfully!  │
│ Added 14 competitors and 5 judges.                │
│                                                    │
│ ⚠️ 1 warning:                                      │
│ • Row 15: Could not find user 'Unknown Person'   │
└────────────────────────────────────────────────────┘
```

## 🎯 Key Takeaways (Visual)

```
╔═══════════════════════════════════════════════════════╗
║           REMEMBER THESE KEY POINTS!                  ║
╚═══════════════════════════════════════════════════════╝

1. USER ID = SOURCE OF TRUTH
   ┌─────────────────────────────────────┐
   │ User ID Present → That person used  │
   │ User ID Blank   → Search by name    │
   └─────────────────────────────────────┘

2. EDIT THE RIGHT SHEET
   ┌─────────────────────────────────────┐
   │ ✅ Rank View    → Competitors       │
   │ ✅ Judges       → Judges            │
   │ ❌ Event Sheets → Reference only    │
   └─────────────────────────────────────┘

3. USE UPDATE MODE
   ┌─────────────────────────────────────┐
   │ Re-uploading? → "Update Existing"   │
   │ First upload? → "Create New"        │
   └─────────────────────────────────────┘

4. COLORS GUIDE YOU
   ┌─────────────────────────────────────┐
   │ 🔵 Blue    → Headers                │
   │ 💙 Lt Blue → Matching IDs           │
   │ 🔲 Gray    → Read-only              │
   │ ⬜ White   → Editable               │
   └─────────────────────────────────────┘
```

## 🚦 Decision Tree

```
                 Want to edit a roster?
                          │
                          ▼
                 ┌────────────────┐
                 │  Download it   │
                 └────────────────┘
                          │
                          ▼
                 What do you need?
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
   Fix a name        Add/Remove         Swap ranks
        │                 │                 │
        ▼                 ▼                 ▼
  Keep User ID      Add/Delete row    Swap User IDs
  Change name       (blank User ID    (keep names)
        │              for new)             │
        │                 │                 │
        └─────────────────┼─────────────────┘
                          │
                          ▼
                 ┌────────────────┐
                 │   Save file    │
                 └────────────────┘
                          │
                          ▼
                 ┌────────────────┐
                 │  Upload page   │
                 └────────────────┘
                          │
                          ▼
                "Update Existing Roster"
                          │
                          ▼
                Select roster → Upload
                          │
                          ▼
                    ✅ Done!
```

## 📱 Quick Reference Card

```
╔═══════════════════════════════════════════════════════╗
║        ROSTER EDIT - QUICK REFERENCE CARD             ║
╠═══════════════════════════════════════════════════════╣
║                                                       ║
║  📥 DOWNLOAD                                          ║
║  └─► View Roster → Green "Download" button           ║
║                                                       ║
║  ✏️ EDIT                                              ║
║  ├─► Fix names: Keep User ID, change name            ║
║  ├─► Add person: New row, blank User ID              ║
║  ├─► Remove: Delete row                              ║
║  └─► Swap ranks: Swap User IDs                       ║
║                                                       ║
║  📤 UPLOAD                                            ║
║  ├─► Mode: "Update Existing Roster"                  ║
║  ├─► Select: Choose roster from dropdown             ║
║  └─► Upload: Click upload button                     ║
║                                                       ║
║  💡 TIPS                                              ║
║  ├─► User ID = guaranteed match                      ║
║  ├─► Edit "Rank View" for competitors                ║
║  ├─► Check warnings after upload                     ║
║  └─► Backup before major changes                     ║
║                                                       ║
╚═══════════════════════════════════════════════════════╝
```

---

**Remember**: The visual cues in the Excel file are designed to guide you. Blue = headers, Light Blue = IDs (keep them!), White = edit freely!

**Need more help?** Check out:
- 📖 [ROSTER_EDIT_README.md](ROSTER_EDIT_README.md)
- 📋 [ROSTER_EDIT_QUICK_REFERENCE.md](ROSTER_EDIT_QUICK_REFERENCE.md)
- 📝 [ROSTER_EDIT_EXAMPLE.md](ROSTER_EDIT_EXAMPLE.md)
