# Test Data Management for Mason SND

This document explains how to create and manage test users for development and testing purposes, including the complete tournament signup and judging approval workflow.

## 🎯 Overview

The test data system creates 15 fake students and 15 fake parents with realistic data for testing tournaments, events, rosters, and the complete judging approval workflow. All test users share the same password that you specify.

### 🔄 Complete Tournament Workflow

The system now properly supports the full tournament lifecycle:
1. **Student Signup** → Students sign up for tournaments and select events
2. **Judge Assignment** → Students can specify if parents are bringing judges
3. **Parent Approval** → Parents approve/deny judging requests through `/tournaments/judge_requests`
4. **Roster Generation** → Only approved judges and confirmed students appear in final rosters
5. **Capacity Management** → Roster spots calculated based on approved judges (6 for Speech, 2 for LD, 4 for PF)

## 🌐 Web Interface (Recommended)


The easiest way to manage test data is through the admin web interface:

1. **Access Admin Panel**: Go to `/admin` (requires admin role)
2. **Click "🧪 Test Data"** from the dashboard
3. **Follow the step-by-step process**:
   - Set a password for all test users
   - Create 15 students + 15 parents
   - Enroll students in random events
   - Sign up students for random tournaments
   - Clean up when done testing

## 📋 Test User Details

### Students
- **Names**: Student1 Test, Student2 Test, ..., Student15 Test
- **Emails**: student1@gmail.com, student2@gmail.com, ..., student15@gmail.com
- **Phone**: 555-000-1001, 555-000-1002, ..., 555-000-1015
- **Role**: Regular students (role=0)

### Parents
- **Names**: Parent1 Test, Parent2 Test, ..., Parent15 Test
- **Emails**: parent1@gmail.com, parent2@gmail.com, ..., parent15@gmail.com
- **Phone**: 555-100-1001, 555-100-1002, ..., 555-100-1015
- **Role**: Parents with judge capabilities
- **Linked**: Each parent is linked to their corresponding student

## 💻 Command Line Interface

You can also use the command line script for programmatic access:

```bash
# Show current stats (includes judge approval statistics)
python test_data_manager.py stats

# Create test users with custom password
python test_data_manager.py create --password mypassword123

# Enroll students in random events
python test_data_manager.py enroll

# Sign up students for random tournaments (creates judge requests)
python test_data_manager.py signup

# Simulate parent approvals/denials of judge requests (80% approval rate)
python test_data_manager.py approve

# Clean up all test data (including Tournament_Judges entries)
python test_data_manager.py cleanup
```

### 📊 Statistics Output
The `stats` command now shows:
- Students and Parents created
- Event Enrollments 
- Tournament Signups
- **Judge Entries** (Tournament_Judges records)
- **Approved Judges** (parents who agreed to judge)

## 🧪 Testing Workflow

### 1. Setup Phase
```bash
# Create test users
python test_data_manager.py create --password testpass123

# OR use web interface at /admin/test_data
```

### 2. Event Testing
```bash
# Make sure you have events created first
# Then enroll test students
python test_data_manager.py enroll
```

### 3. Tournament Testing
```bash
# Make sure you have tournaments created first
# Then sign up test students (creates Tournament_Judges entries)
python test_data_manager.py signup

# Simulate parent approval process (80% approval rate)
python test_data_manager.py approve
```

### 4. Complete Tournament Workflow Testing

#### 4a. Student Experience
- Login as test student: `student1@gmail.com` / `testpass123`
- Navigate to `/tournaments/signup`
- Select tournament and events
- Choose "Yes" for bringing a judge
- Select parent from dropdown
- Submit signup

#### 4b. Parent Experience  
- Login as test parent: `parent1@gmail.com` / `testpass123`
- Navigate to `/tournaments/judge_requests`
- See requests from their child
- Approve or deny each request
- Submit decisions

#### 4c. Admin Experience
- Login as admin with role ≥ 2
- Navigate to `/rosters/view_tournament/{id}`
- See only approved judges in roster
- See students ranked by weighted points
- Download Excel roster with multiple sheets

### 5. Login Testing
- Students: `student1@gmail.com` through `student15@gmail.com`
- Parents: `parent1@gmail.com` through `parent15@gmail.com`
- Password: Whatever you set (default: `testpass123`)

### 6. Roster Testing
- View rosters at `/rosters/view_tournament/{tournament_id}`
- Only students with approved judges appear
- Capacity calculated: Speech (6 per judge), LD (2 per judge), PF (4 per judge)
- Download Excel files with judge and competitor sheets

### 7. Cleanup
```bash
# Remove all test data when done
python test_data_manager.py cleanup
```

## ⚠️ Important Notes

### System Requirements
- **Role-Based Access**: Roster viewing requires admin role (≥2)
- **Judge Relationship**: Parents must be linked via `Judges` table
- **Tournament Forms**: Tournaments need form fields with "Are you bringing a judge?" question
- **Event Types**: Events must have proper event_type (0=Speech, 1=LD, 2=PF) for capacity calculation

### Test Data Behavior
- **Test Data Only**: All test users have "Test" as their last name for easy identification
- **Same Password**: All test users use the same password you specify
- **Realistic Relationships**: Parents are properly linked to their children with judge capabilities
- **Random Behavior**: Event enrollments and tournament signups are randomized for realistic testing
- **Judge Approval Simulation**: The `approve` command uses 80% approval rate to simulate realistic parent responses
- **Safe Cleanup**: Cleanup only removes users with "Test" last names and related Tournament_Judges entries

### Database Considerations
- **Tournament_Signups**: Only entries with `is_going=True` appear in rosters
- **Tournament_Judges**: Only entries with `accepted=True` provide judge capacity
- **Capacity Logic**: Speech events get 6 spots per judge, LD gets 2, PF gets 4
- **Ranking System**: Students ranked by weighted_points (falls back to points) for roster selection

## 🔧 Features Tested

With this test data, you can test:

### Core User Management
- ✅ User authentication and profiles
- ✅ Parent-child relationships and judge linking
- ✅ Admin user management functions

### Event & Tournament Management  
- ✅ Event enrollment and management
- ✅ Tournament creation and form configuration
- ✅ Tournament signup workflows with judge selection

### Judging Approval System
- ✅ **Tournament_Judges entry creation** during signup
- ✅ **Parent judge request approval/denial** via `/tournaments/judge_requests`
- ✅ **Judge assignment to specific events** (Speech, LD, PF)
- ✅ **Capacity calculation** based on approved judges

### Roster Generation & Management
- ✅ **Roster generation** with approved judges only (`accepted=True`)
- ✅ **Capacity-based competitor selection** (6 Speech, 2 LD, 4 PF per judge)
- ✅ **Weighted points ranking** for competitor selection
- ✅ **Excel export** with judges and competitors sheets
- ✅ Roster publishing and confetti notifications

### Database Integrity
- ✅ **Tournament_Signups** filtering by `is_going=True`
- ✅ **Duplicate prevention** for Tournament_Judges entries
- ✅ **Proper cleanup** of all related records

## 🚨 Security Considerations

- Only use in development/testing environments
- Never use on production systems
- Test users have simple, predictable emails and data
- All test users share the same password for convenience
- Regular cleanup prevents database bloat

## 🔧 Troubleshooting & Recent Fixes

### Issue: Students Not Appearing in Tournament Rosters
**Problem**: Students would sign up for tournaments but not appear in the roster view.

**Root Cause**: Missing Tournament_Judges entries and no parent approval mechanism.

**Solution**: Enhanced test data manager to:
- Create Tournament_Judges entries during signup
- Simulate parent approval process with `approve` command
- Filter rosters to only show approved judges

### Issue: Judge Capacity Not Calculated Correctly  
**Problem**: Roster generation didn't respect judge capacity limits.

**Root Cause**: View logic only counted accepted judges but didn't apply capacity filtering.

**Solution**: Fixed roster generation to:
- Only include signups with `is_going=True`
- Only count judges with `accepted=True` 
- Apply proper capacity per event type (6/2/4 for Speech/LD/PF)

### Issue: Duplicate Tournament_Judges Entries
**Problem**: Re-running signup process created duplicate judge entries.

**Solution**: Added duplicate prevention checks in both:
- Tournament signup route (`tournaments.py`)
- Test data manager (`test_data_manager.py`)

### Current Status: ✅ All Fixed
- Tournament signups → Tournament_Judges creation ✅
- Parent approval workflow ✅  
- Capacity-based roster generation ✅
- Proper filtering and ranking ✅

### Verification Commands
```bash
# Check current state
python test_data_manager.py stats

# Expected output for working system:
# • Students: 15
# • Tournament Signups: 15  
# • Judge Entries: 10 (students bringing judges)
# • Approved Judges: 7-9 (80% approval rate)
```

## 🎉 Example Use Cases

### Testing Complete Tournament Lifecycle
1. **Setup**: Create test users and enroll in events
2. **Tournament Creation**: Create tournament with form fields including "Are you bringing a judge?"
3. **Student Signups**: Students sign up, select events, choose to bring judges
4. **Judge Assignment**: Students select their parent as judge
5. **Parent Approval**: Parents review and approve/deny judge requests
6. **Roster Generation**: Admin views final roster with only approved judges
7. **Capacity Verification**: Confirm roster respects judge capacity limits

Example scenario:
```bash
# Full workflow test
python test_data_manager.py create
python test_data_manager.py enroll  
python test_data_manager.py signup  # Creates judge requests
python test_data_manager.py approve # Simulates parent approvals
python test_data_manager.py stats   # Shows: 15 signups, 10 judge entries, 8 approved

# Result: Tournament roster shows 8 approved judges bringing 16 LD competitors
# 15 students signed up, all can participate since 16 > 15
```

### Testing Judge Approval Edge Cases
1. **No Approved Judges**: All parents deny requests → roster shows 0 capacity
2. **Partial Approval**: Some parents approve → limited roster capacity  
3. **Over-Capacity**: More signups than judge capacity → ranking determines selection
4. **Multiple Events**: Test Speech (6/judge), LD (2/judge), PF (4/judge) ratios

### Testing Roster Publishing
1. Create test users and complete tournament workflow
2. Generate rosters from tournament signups with approved judges
3. Publish rosters and test confetti notifications  
4. Check user profiles for tournament listings
5. Download Excel files with comprehensive data

### Load Testing Tournament System
1. Create multiple batches of test users
2. Simulate various approval rates (approve command uses 80% rate)
3. Test system performance with realistic judge approval ratios
4. Verify database constraints and relationship integrity
