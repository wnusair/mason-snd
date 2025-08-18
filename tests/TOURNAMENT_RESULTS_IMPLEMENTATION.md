## Tournament Results Feature Implementation

I have successfully implemented the tournament results submission feature for your Flask application. Here's what was added:

### Database Changes

1. **New Field in Tournament Model**: Added `results_submitted` boolean field to track whether results have been submitted for a tournament.

2. **Migration**: Created a database migration to add the new field with a default value of `False`.

### New Routes Added

1. **Submit Results Route** (`/submit_results/<tournament_id>`):
   - Only accessible to admins (role >= 2)
   - Only available for past tournaments
   - Prevents submission if results already submitted
   - Shows tournament and participant information
   - Marks tournament as having results submitted

2. **View Results Route** (`/view_results/<tournament_id>`):
   - Shows submitted tournament results
   - Displays participant performance data
   - Available to all logged-in users

### Updated Tournament Index Page

The main tournaments page now shows two sections:

1. **Upcoming Tournaments**: Shows tournaments that haven't happened yet
2. **Past Tournaments**: Shows completed tournaments with status badges and action buttons

For past tournaments, the interface shows:
- **Status Badges**: 
  - "Pending Results" (yellow) - Results not yet submitted
  - "Results Submitted" (green) - Results already submitted
- **Action Buttons**:
  - "Submit Results" (for admins, only when results not submitted)
  - "View Results" (when results have been submitted)
  - "Delete" (for admins)

### New Templates

1. **submit_results.html**: Form for admins to confirm and submit tournament results
2. **view_results.html**: Display page for tournament results showing participant performances

### Key Features

- **Access Control**: Only admins can submit results
- **Time Validation**: Results can only be submitted for past tournaments
- **One-Time Submission**: Once results are submitted, they cannot be submitted again
- **User Experience**: Clear visual indicators of tournament status
- **Data Integrity**: Proper validation and error handling

### How to Use

1. When a tournament date passes, admins will see a "Submit Results" button next to past tournaments
2. Clicking the button shows a confirmation page with tournament details and participant list
3. After submitting, the tournament is marked as having results submitted
4. All users can then view the results via the "View Results" button
5. Future attempts to submit results for the same tournament are blocked

The feature integrates seamlessly with your existing tournament system and maintains the same design patterns and security considerations used throughout the application.
