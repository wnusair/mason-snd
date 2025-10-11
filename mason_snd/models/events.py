"""Event Models - Competition events and effort scoring system.

Defines speech and debate events (LD, PF, Extemp, etc.), event leadership,
user participation tracking, and effort scoring for practice/preparation.

Key Models:
    Event: Competition event definitions (LD, PF, Impromptu, etc.)
    Event_Leader: Event leadership assignments (ELs)
    User_Event: User participation in events (active membership)
    Effort_Score: Practice/preparation effort scoring by event leaders

Event System:
    - Events represent competition categories (LD, PF, Extemp, Oratory, etc.)
    - Users join events (User_Event) to participate
    - Event Leaders (ELs) manage events and score effort
    - Effort scores track practice/preparation (not competition results)

Event Types:
    - Speech events (event_type=0): Oratory, Impromptu, Extemp, etc.
    - LD debate (event_type=1): Lincoln-Douglas debate
    - PF debate (event_type=2): Public Forum debate
    - Partner events (is_partner_event=True): PF, Policy, Duo Interp

Effort Scoring:
    - Event leaders score member effort/preparation
    - Scores contribute to weighted metrics
    - Separate from tournament performance results
    - Encourages practice and team participation
"""

from ..extensions import db

from datetime import datetime
import pytz

class Event(db.Model):
    """Competition event definition (LD, PF, Extemp, Oratory, etc.).
    
    Represents a speech or debate event category with leadership, type
    classification, and partner event designation.
    
    Purpose:
        - Define competition event categories
        - Assign event leaders (ELs) for management
        - Classify event types (speech, LD, PF)
        - Designate partner events vs. individual
        - Enable event-specific signups and rosters
    
    Event Types:
        event_type field:
            - 0: Speech events (Oratory, Impromptu, Extemp, Interp, etc.)
            - 1: LD debate (Lincoln-Douglas, individual)
            - 2: PF debate (Public Forum, partner event)
        
        Purpose:
            - Group similar events for organization
            - Apply type-specific rules/workflows
            - Filter events by category
    
    Partner Events:
        is_partner_event field:
            - True: Requires partner pairing (PF, Policy, Duo Interp)
            - False: Individual competition (LD, Extemp, Oratory)
        
        Purpose:
            - Enable partner pairing workflows
            - Require two users per roster entry
            - Validate tournament signups
            - Generate partner-aware rosters
    
    Event Leadership:
        owner_id:
            - Legacy field for primary event leader
            - Deprecated in favor of leaders relationship
        
        leaders relationship (Event_Leader):
            - Multiple event leaders per event
            - One-to-many relationship
            - Preferred method for leadership tracking
        
        leader_users property:
            - Convenience property
            - Returns list of User objects who are leaders
            - Queries through Event_Leader relationship
    
    Columns:
        id: Primary key
        event_name: Event name (String, e.g., "Lincoln-Douglas")
        event_description: Event description (String, optional)
        event_emoji: Emoji icon for display (String, e.g., "🎤")
        owner_id: Legacy primary leader (foreign key to User, deprecated)
        event_type: Event category (Integer, 0=speech, 1=LD, 2=PF)
        is_partner_event: Requires partners (Boolean, default False)
    
    Relationships:
        owner: Legacy primary leader User (backref: event)
        leaders: Event_Leader entries (back_populates: event)
        user_event: User participation records
        effort_score: Effort scores for this event
        tournament_signups: Tournament registrations
        tournament_judges: Judge commitments
        tournament_partners: Partner pairings
        roster_judge_event: Roster judge assignments
        roster_judge_event_competitors: Roster competitor entries
        published_roster_entries: Roster publication notifications
        penalty_entries: Roster penalty tracking
    
    Properties:
        leader_users:
            Returns list of User objects who are event leaders.
            Queries Event_Leader.user for all leaders of this event.
    
    Common Events:
        Individual:
            - Lincoln-Douglas Debate (LD, type=1)
            - Extemporaneous Speaking (Extemp, type=0)
            - Oratory (type=0)
            - Impromptu Speaking (type=0)
            - Dramatic/Humorous Interpretation (type=0)
        
        Partner:
            - Public Forum Debate (PF, type=2, is_partner_event=True)
            - Policy Debate (type=2, is_partner_event=True)
            - Duo Interpretation (type=0, is_partner_event=True)
    
    Note:
        Use leaders relationship (not owner_id) for event leadership.
        Multiple leaders supported for shared event management.
    """
    id = db.Column(db.Integer, primary_key=True)

    event_name = db.Column(db.String)
    event_description = db.Column(db.String)

    event_emoji = db.Column(db.String)
    
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = db.relationship('User', foreign_keys=[owner_id], backref='event')

    event_type = db.Column(db.Integer) # 0 = speech, 1 = LD, 2 = PF
    is_partner_event = db.Column(db.Boolean, default=False) # True if event requires partners

    # Relationship to multiple leaders
    leaders = db.relationship('Event_Leader', back_populates='event')

    @property
    def leader_users(self):
        """Get all leader users for this event"""
        return [leader.user for leader in self.leaders]

class Event_Leader(db.Model):
    """Event leadership assignments (Event Leaders / ELs).
    
    Links users to events they lead/manage. Event Leaders have elevated
    permissions for their events (scoring effort, managing members, etc.).
    
    Purpose:
        - Assign event leaders to events
        - Enable multiple leaders per event (shared management)
        - Grant event-specific permissions (not full admin)
        - Track leadership history
    
    Event Leader Permissions:
        - Score member effort for their events
        - Manage event membership (activate/deactivate users)
        - View event-specific analytics
        - Cannot manage other events or system-wide settings
    
    User Roles:
        System roles (User.role):
            - 0: Regular member (no leadership)
            - 1: Event Leader (can lead one or more events)
            - 2+: Chair/Admin (full system access)
        
        Event_Leader assignment:
            - Additional to role=1 (which events they lead)
            - Can have multiple Event_Leader entries (multiple events)
            - Role=1 users typically have Event_Leader entries
    
    Columns:
        id: Primary key
        event_id: Event being led (foreign key to Event)
        user_id: User who is event leader (foreign key to User)
    
    Relationships:
        event: Event object (back_populates: leaders)
        user: User object (backref: event_leaderships)
    
    Usage:
        Admin assigns leader:
            1. Set user.role = 1 (Event Leader role)
            2. Create Event_Leader entry (event_id, user_id)
            3. User now has permissions for that event
        
        Permission check:
            Event_Leader.query.filter_by(
                event_id=event_id,
                user_id=user_id
            ).first() is not None
        
        List user's events:
            Event_Leader.query.filter_by(user_id=user_id).all()
    
    Multiple Leaders:
        Purpose:
            - Share event management workload
            - Co-leaders for large events
            - Succession planning (new + experienced leaders)
        
        Example:
            Event "Lincoln-Douglas" has 3 Event_Leader entries:
            - Senior leader (graduating)
            - Junior leader (learning)
            - Third leader (backup)
    
    Note:
        Event_Leader entries typically exist only for users with role=1.
        Role=2+ (admins) have access to all events without Event_Leader entries.
    """
    id = db.Column(db.Integer, primary_key=True)
    
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    event = db.relationship('Event', back_populates='leaders')
    user = db.relationship('User', foreign_keys=[user_id], backref='event_leaderships')

class User_Event(db.Model):
    """User participation in events (active membership).
    
    Tracks which users participate in which events, with active status and
    deprecated effort score field. Determines which events users can sign up
    for at tournaments.
    
    Purpose:
        - Link users to events they participate in
        - Track active vs. inactive participation
        - Enable event-specific rosters
        - Filter tournament signup options
        - (Deprecated: track effort score per event)
    
    Active Status:
        active field:
            - True: User actively participating in event
            - False: User inactive or removed from event
        
        Purpose:
            - Filter active participants for rosters
            - Hide inactive users from event lists
            - Preserve historical participation data
            - Soft delete (not hard delete)
        
        Workflow:
            - User joins event: active=True
            - User leaves/drops event: active=False
            - Event leader can reactivate: active=True again
    
    Effort Score (Deprecated):
        effort_score field:
            - Deprecated: Use Effort_Score model instead
            - Was intended for cumulative effort per event
            - Now tracked separately with timestamps
        
        Note:
            Don't use this field. Query Effort_Score model for
            effort scores by event.
    
    Columns:
        id: Primary key
        effort_score: Deprecated (Integer, use Effort_Score model)
        active: Participation status (Boolean, default False)
        event_id: Event being participated in (foreign key to Event)
        user_id: Participating user (foreign key to User)
    
    Relationships:
        event: Event object (backref: user_event)
        user: User object (backref: user_event)
    
    Usage:
        Join event:
            User_Event.create(user_id=X, event_id=Y, active=True)
        
        Leave event:
            user_event.active = False
        
        List active participants:
            User_Event.query.filter_by(
                event_id=event_id,
                active=True
            ).all()
        
        Check user participation:
            User_Event.query.filter_by(
                user_id=user_id,
                event_id=event_id,
                active=True
            ).first() is not None
    
    Tournament Integration:
        Signup filtering:
            - Only show events where User_Event.active=True
            - Prevents signup for events user doesn't participate in
            - Ensures roster eligibility
    
    Note:
        Default active=False requires explicit activation when creating.
        Consider changing default to True for better UX.
    """
    id = db.Column(db.Integer, primary_key=True)

    effort_score = db.Column(db.Integer, nullable=True, default=0)

    active = db.Column(db.Boolean, default=False)

    event_id = db.Column(db.Integer, db.ForeignKey('event.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    event = db.relationship('Event', foreign_keys=[event_id], backref='user_event')
    user = db.relationship('User', foreign_keys=[user_id], backref='user_event')

class Effort_Score(db.Model):
    """Practice and preparation effort scoring by event leaders.
    
    Event leaders score member effort/preparation for their events. Scores
    contribute to weighted metrics alongside tournament performance results.
    
    Purpose:
        - Reward practice and preparation (not just competition results)
        - Enable event leader feedback and evaluation
        - Contribute to overall user metrics (weighted with tournament points)
        - Track effort over time (timestamps)
        - Encourage consistent team participation
    
    Effort vs. Performance:
        Effort_Score:
            - Practice attendance and quality
            - Preparation and improvement
            - Team participation and attitude
            - Scored by event leaders (subjective)
            - Contributes to weighted metrics
        
        Tournament_Performance:
            - Competition results (ranks, points)
            - Objective tournament outcomes
            - Contributes to weighted metrics
    
    Scoring System:
        score field:
            - Numeric score value (Integer)
            - Scale determined by event leader practice
            - Example: 1-10 scale per practice
            - Cumulative: Multiple scores tracked over time
        
        User.effort_points property:
            - Sums all Effort_Score records for user
            - Combined with tournament_points in metrics
            - Weighted by MetricsSettings (default 30% effort, 70% tournament)
    
    Attribution:
        given_by_id field:
            - Event leader who assigned score
            - Accountability and audit trail
            - Query scores by who gave them
        
        Purpose:
            - Track which leaders scored which users
            - Enable leader-specific score analysis
            - Audit trail for disputes
    
    Columns:
        id: Primary key
        score: Effort score value (Integer)
        timestamp: When score assigned (DateTime, EST)
        user_id: User being scored (foreign key to User)
        event_id: Event context (foreign key to Event)
        given_by_id: Event leader who scored (foreign key to User)
    
    Relationships:
        user: User being scored (backref: effort_score_user)
        event: Event context (backref: effort_score)
        given_by: Event leader who scored (backref: effort_score_given_by)
    
    Usage:
        Event leader scores user:
            1. After practice or preparation period
            2. Event leader creates Effort_Score record
            3. Sets score value (e.g., 8/10)
            4. Sets given_by_id to own user_id
            5. Timestamp auto-set to current time
        
        Calculate user effort:
            scores = Effort_Score.query.filter_by(user_id=X).all()
            total = sum([s.score for s in scores])
        
        Calculate user effort by event:
            scores = Effort_Score.query.filter_by(
                user_id=X,
                event_id=Y
            ).all()
    
    Metrics Integration:
        Weighted calculation:
            - effort_points = sum of all Effort_Score.score
            - tournament_points = sum of all Tournament_Performance.points
            - total_score = (effort_points * effort_weight) + 
                           (tournament_points * tournament_weight)
            - Default: 30% effort, 70% tournament (MetricsSettings)
    
    Timestamp Tracking:
        Purpose:
            - Analyze effort trends over time
            - Calculate recent effort vs. historical
            - Generate time-based effort reports
            - Track improvement trajectories
    
    Note:
        Multiple scores per user per event (cumulative over time).
        Event leaders can only score users in events they lead (enforced in routes).
    """
    id = db.Column(db.Integer, primary_key=True)

    score = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('US/Eastern'))) # datetime eastern time

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', foreign_keys=[user_id], backref='effort_score_user')

    event_id = db.Column(db.Integer, db.ForeignKey('event.id'))
    event = db.relationship('Event', foreign_keys=[event_id], backref='effort_score')

    given_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    given_by = db.relationship('User', foreign_keys=[given_by_id], backref='effort_score_given_by')

