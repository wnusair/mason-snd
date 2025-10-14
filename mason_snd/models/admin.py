"""Administrative Models - Requirements and popup message system.

Defines requirement templates, user-specific requirement assignments with deadlines,
and admin popup messaging system for user notifications.

Key Models:
    Requirements: Requirement templates (e.g., waiver, payment, forms)
    User_Requirements: User-specific requirement assignments with completion tracking
    Popups: Admin messages displayed on user profiles

Requirement System:
    - Admins create requirement templates (Requirements)
    - Requirements assigned to users (User_Requirements)
    - Deadlines set per-user (flexible scheduling)
    - Completion tracked (complete=True/False)
    - Active requirements shown on profile until completed

Popup System:
    - Admins send messages to specific users
    - Messages displayed on user profile
    - Optional expiration (expires_at timestamp)
    - User dismissal (completed=True)
    - Track who sent message (admin_id)
"""

from ..extensions import db

from datetime import datetime
import pytz

# Define EST timezone
EST = pytz.timezone('US/Eastern')


class User_Requirements(db.Model):
    """User-specific requirement assignments with completion tracking.
    
    Links users to requirement templates (Requirements) with per-user deadlines
    and completion status. Displayed on user profile until marked complete.
    
    Purpose:
        - Assign requirements to specific users
        - Set individual deadlines (not template-wide)
        - Track completion status
        - Display incomplete requirements on profile
        - Notify users of pending requirements
    
    Workflow:
        1. Admin creates requirement template (Requirements)
        2. Admin assigns requirement to user(s) (creates User_Requirements)
        3. Admin sets deadline for each user
        4. User sees requirement on profile (complete=False)
        5. User completes requirement (admin marks complete=True)
        6. Requirement removed from profile display
    
    Deadline System:
        - Per-user deadlines (not one-size-fits-all)
        - Default: Created with current timestamp (needs updating)
        - Flexible: Admin can set different deadlines per user
        - Display: Sorted by deadline on profile
    
    Completion Tracking:
        complete field:
            - False: Requirement not yet completed (default)
            - True: Requirement completed (hidden from profile)
        
        Completion process:
            - Admin manually marks as complete (no self-service)
            - May require verification (payment received, waiver signed, etc.)
            - Permanent (no uncomplete functionality)
    
    Columns:
        id: Primary key
        complete: Boolean indicating completion status (False=pending)
        deadline: DateTime for requirement completion (EST timezone)
        user_id: User assigned requirement (foreign key to User)
        requirement_id: Requirement template (foreign key to Requirements)
    
    Relationships:
        requirement: Requirement template object (backref: requirement)
        user: User assigned requirement (backref: user)
    
    Display:
        Profile page:
            - Query incomplete requirements (complete=False)
            - Show requirement body text
            - Show deadline
            - Highlight overdue (deadline < now)
        
        Admin interface:
            - View all user requirements
            - Mark as complete
            - Update deadlines
            - Bulk assignment
    
    Common Requirements:
        - Waiver signing
        - Payment submission
        - Registration forms
        - Parent permission slips
        - Background checks (for judges)
        - Code of conduct acknowledgment
    
    Note:
        Default deadline (datetime.now) should be updated to actual deadline
        when creating assignment. Not intended as actual deadline value.
    """
    id = db.Column(db.Integer, primary_key=True)

    complete = db.Column(db.Boolean, default=False)
    deadline = db.Column(db.DateTime, default=datetime.now(EST), nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    requirement_id = db.Column(db.Integer, db.ForeignKey('requirements.id'))
    
    requirement = db.relationship('Requirements', foreign_keys=[requirement_id], backref='requirement')
    user = db.relationship('User', foreign_keys=[user_id], backref='user')

class Requirements(db.Model):
    """Requirement templates for user assignments.
    
    Defines reusable requirement templates that can be assigned to multiple users.
    Templates include requirement text and active status for enabling/disabling.
    
    Purpose:
        - Create reusable requirement templates
        - Define requirement text/description
        - Enable/disable requirements globally
        - Avoid duplicating requirement text for each user
    
    Template System:
        - Create once, assign to many users
        - Consistent requirement text across assignments
        - Update template text (affects future assignments)
        - Active/inactive toggle for seasonal requirements
    
    Active Status:
        active field:
            - True: Requirement available for assignment (default)
            - False: Requirement hidden/disabled
        
        Purpose:
            - Disable seasonal requirements (off-season)
            - Archive old requirements without deleting
            - Prevent accidental assignment of inactive requirements
            - Maintain historical record (don't delete)
    
    Columns:
        id: Primary key
        body: Requirement text/description (String, no length limit)
        active: Boolean indicating availability (True=active, False=disabled)
    
    Relationships:
        requirement: User_Requirements backref (assignments using this template)
    
    Usage:
        Admin workflow:
            1. Create requirement template with descriptive body text
            2. Set active=True to enable for assignment
            3. Assign to users (creates User_Requirements entries)
            4. Set active=False when requirement no longer needed
        
        Assignment:
            - Query active requirements (active=True)
            - Display in admin assignment interface
            - Create User_Requirements with requirement_id
    
    Common Templates:
        - "Sign and submit team waiver by [date]"
        - "Pay team dues ($X) via [payment method]"
        - "Complete registration form at [URL]"
        - "Submit parent permission slip (under 18)"
        - "Complete background check (judges only)"
    
    Deletion:
        - Deleting requirement also deletes all User_Requirements
        - Use active=False instead of deletion (preserves history)
        - If deleted, use deletion_utils.delete_requirement_safely()
    
    Note:
        Body field has no explicit length limit (use db.String not db.String(N)).
        Can contain detailed instructions, links, formatting.
    """
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String)
    active = db.Column(db.Boolean, default=True, nullable=False)

class Popups(db.Model):
    """Admin popup messages displayed on user profiles.
    
    Enables admins to send direct messages to users that appear on their profile
    page until dismissed or expired. Used for announcements, reminders, and
    important notifications.
    
    Purpose:
        - Send targeted messages to specific users
        - Display prominent notifications on profile
        - Track message creation and expiration
        - Enable user dismissal when acknowledged
        - Audit who sent which messages (admin accountability)
    
    Message Lifecycle:
        1. Admin creates popup for user (admin_id, user_id, message)
        2. Popup displayed on user's profile (completed=False)
        3. User sees message prominently on profile page
        4. User dismisses message (sets completed=True)
        5. Message no longer displayed
    
    Expiration System:
        expires_at field:
            - NULL: Never expires (permanent until dismissed)
            - DateTime: Auto-hides after expiration time
        
        Display logic:
            - Show if: completed=False AND (expires_at is NULL OR expires_at > now)
            - Hide if: completed=True OR (expires_at <= now)
        
        Purpose:
            - Time-sensitive announcements (tournament reminders)
            - Auto-cleanup of old messages
            - Reduce clutter on profile
    
    Dismissal:
        completed field:
            - False: Message active/visible (default)
            - True: Message dismissed by user (hidden)
        
        Dismissal process:
            - User clicks dismiss button (profile.dismiss_popup route)
            - Sets completed=True
            - Permanent (cannot be undismissed)
    
    Columns:
        id: Primary key
        message: Popup text content (Text field, no length limit)
        created_at: When popup created (EST timezone)
        expires_at: When popup expires (DateTime, nullable)
        completed: Boolean indicating dismissal (False=active, True=dismissed)
        user_id: User receiving message (foreign key to User)
        admin_id: Admin who sent message (foreign key to User)
    
    Relationships:
        user: User receiving message (backref: popups_received)
        admin: Admin who sent message (backref: popups_sent)
    
    Display:
        Profile page:
            - Query active popups (completed=False, not expired)
            - Show prominently (likely at top of profile)
            - Include dismiss button
            - Show creation date/expiration
        
        Admin interface:
            - Create new popups
            - Target specific users
            - Set expiration (optional)
            - View sent popups (admin_id)
    
    Use Cases:
        - Tournament reminders ("Tournament X tomorrow!")
        - Payment reminders ("Dues payment overdue")
        - Important announcements ("Practice cancelled this week")
        - Requirement notifications ("Please complete waiver")
        - Congratulations ("Great job at [tournament]!")
    
    Audit Trail:
        - admin_id tracks who sent message (accountability)
        - created_at tracks when sent (timeline)
        - Cannot be edited once created (integrity)
    
    Note:
        Expired messages (expires_at < now) still appear until dismissed if
        user hasn't viewed profile since expiration. User dismissal required
        for permanent removal.
    """
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(EST), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)
    completed = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    user = db.relationship('User', foreign_keys=[user_id], backref='popups_received')
    admin = db.relationship('User', foreign_keys=[admin_id], backref='popups_sent')


