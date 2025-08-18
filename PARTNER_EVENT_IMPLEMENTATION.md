# Partner Event Implementation

This document outlines the implementation of partner events in the Mason Speech and Debate system.

## Overview

Partner events allow participants to search for and select partners when signing up for tournaments. This feature includes:

1. **Event Creation**: When creating an event, you can mark it as a "partner event"
2. **Tournament Signup**: For partner events, users can search for and select partners during signup
3. **Roster Generation**: The roster system automatically tracks partnerships
4. **Download/Upload**: Partner information is included in roster downloads

## Database Changes

### New Fields Added

1. **Event Model** (`events.py`):
   - Added `is_partner_event` boolean field to mark events that require partners

2. **Tournament_Signups Model** (`tournaments.py`):
   - Added `partner_id` foreign key field to link to selected partner
   - Added `partner` relationship to User model

3. **New Tournament_Partners Model** (`tournaments.py`):
   - Tracks partnership relationships for tournaments
   - Links partner1_user_id, partner2_user_id, tournament_id, event_id

### Database Migrations

- Migration `a0300480cf19_add_partner_event_support.py`: Adds partner_id to tournament_signups
- Migration `8453e55c1962_add_tournament_partners_model.py`: Creates tournament_partners table

## Frontend Changes

### Event Creation/Editing

1. **Add Event Form** (`templates/events/add_event.html`):
   - Added checkbox for "This is a partner event"
   - Added description explaining the feature

2. **Edit Event Form** (`templates/events/edit_event.html`):
   - Added checkbox for "This is a partner event" with current value
   - Added description explaining the feature

### Tournament Signup

1. **Signup Form** (`templates/tournaments/signup.html`):
   - Added partner selection interface for partner events
   - Includes search functionality with autocomplete
   - Shows "Partner Event" badge for partner events
   - JavaScript functions for partner search and selection

## Backend Changes

### Event Management

1. **Events Blueprint** (`blueprints/events/events.py`):
   - Updated `add_event` route to handle `is_partner_event` checkbox
   - Updated `edit_event` route to handle `is_partner_event` checkbox

### Tournament Management

1. **Tournaments Blueprint** (`blueprints/tournaments/tournaments.py`):
   - Updated signup process to handle partner selection
   - Added partner search endpoint `/search_partners`
   - Automatically creates mutual partnership when one partner selects another

2. **Partner Search Endpoint**:
   - Searches users by name with query parameter
   - Filters to users signed up for the same event
   - Returns JSON response with user information

### Roster Management

1. **Rosters Blueprint** (`blueprints/rosters/rosters.py`):
   - Updated roster creation to save partnership information
   - Added partner information to roster downloads
   - Uses `Roster_Partners` model to track partnerships in rosters

2. **Download Functionality**:
   - Updated Excel downloads to include "Partner" column
   - Shows partner names for competitors in partner events

## How It Works

### Creating a Partner Event

1. Admin goes to "Add Event" page
2. Fills out normal event information
3. Checks "This is a partner event" checkbox
4. Event is created with `is_partner_event = True`

### Signing Up for a Tournament with Partner Event

1. User goes to tournament signup page
2. Selects tournament and fills out form fields
3. For partner events, additional partner selection interface appears
4. User can search for partners by typing names
5. System shows autocomplete results of users in the same event
6. User selects partner and submits signup
7. Both users are automatically signed up with mutual partnership

### Roster Generation

1. When creating a roster, the system identifies partner events
2. For competitors in partner events, it checks for partnership information
3. If both partners are selected for the roster, a `Roster_Partners` entry is created
4. Partnership information is included in roster downloads

### Partner Search

The partner search functionality:
- Searches users by first name, last name, or full name
- Only shows users who are signed up for the same event
- Excludes the current user from results
- Returns JSON for frontend autocomplete

## Files Modified

### Models
- `mason_snd/models/events.py` - Added `is_partner_event` field
- `mason_snd/models/tournaments.py` - Added `partner_id` field and `Tournament_Partners` model

### Templates
- `mason_snd/templates/events/add_event.html` - Added partner event checkbox
- `mason_snd/templates/events/edit_event.html` - Added partner event checkbox
- `mason_snd/templates/tournaments/signup.html` - Added partner selection interface

### Blueprints
- `mason_snd/blueprints/events/events.py` - Handle partner event flag
- `mason_snd/blueprints/tournaments/tournaments.py` - Partner signup logic and search
- `mason_snd/blueprints/rosters/rosters.py` - Partner information in rosters

### Migrations
- `migrations/versions/a0300480cf19_add_partner_event_support.py`
- `migrations/versions/8453e55c1962_add_tournament_partners_model.py`

## Usage Examples

### Example 1: Creating a Public Forum Event (Partner Event)
1. Admin creates event "Public Forum Debate"
2. Checks "This is a partner event" 
3. Event is saved with partner functionality enabled

### Example 2: Student Signing Up for Tournament
1. Student goes to tournament signup
2. Sees "Public Forum Debate" with "Partner Event" badge
3. Checks the event box - partner selection interface appears
4. Types "John" in partner search - sees "John Smith" in results
5. Selects "John Smith" as partner
6. Submits signup - both student and John are signed up together

### Example 3: Roster Download
1. Admin generates roster for tournament
2. Downloads Excel file
3. Roster shows:
   - Jane Doe | John Smith | 85 points | Public Forum Debate
   - John Smith | Jane Doe | 82 points | Public Forum Debate

This indicates Jane and John are partners in the Public Forum event.

## Benefits

1. **Streamlined Partnership**: No manual coordination needed for partner events
2. **Automatic Mutual Signup**: When one partner selects another, both are signed up
3. **Clear Documentation**: Partners are clearly identified in rosters and downloads
4. **Flexible System**: Works alongside existing individual events
5. **Easy Management**: Admin can easily identify which events require partners
