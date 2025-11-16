"""Authentication and User Models - Core user system with relationships.

Defines user accounts, ghost accounts, parent-child relationships (Judges),
published roster notifications, and roster penalty tracking. Central to all
application functionality.

Key Models:
    User: Core user account (members, parents, children, admins)
    Judges: Parent-child relationship tracking
    User_Published_Rosters: Roster publication notifications
    Roster_Penalty_Entries: Penalty tracking for rosters (+1 indicators)

User Types:
    - Members: Regular users (role=0)
    - Event Leaders: Event managers (role=1)
    - Chairs+: Full admins (role=2+)
    - Parents: Users with is_parent=True
    - Children: Users with is_parent=False
    - Ghost Accounts: Unclaimed accounts (account_claimed=False)

Relationship System:
    - Parents linked to children via Judges table
    - Enables profile access across family members
    - Supports judge commitments for tournaments
    - Handles emergency contact information
"""

from ..extensions import db
from datetime import datetime
import pytz

class User(db.Model):
    """Core user account model for all application users.
    
    Represents members, parents, children, event leaders, and administrators.
    Supports both claimed accounts (registered users) and ghost accounts
    (unclaimed placeholders for parent-child relationships).
    
    User Types & Roles:
        is_parent:
            - True: Parent/guardian account
            - False: Child/competitor account
        
        role (authorization level):
            - 0: Regular member (default)
            - 1: Event Leader (can manage specific events)
            - 2+: Chair/Admin (full system access)
    
    Ghost Accounts:
        Purpose:
            Enable parent-child relationships before both parties register.
            Created when user adds parent/child who doesn't exist yet.
        
        Identification:
            - account_claimed = False (unclaimed)
            - account_claimed = True (claimed/registered)
        
        Claiming Process:
            When ghost user registers, account_claimed set to True.
            Existing relationships preserved (Judges table).
    
    Parent-Child Relationships:
        Parent Fields:
            - child_first_name, child_last_name: Link to child account
        
        Child Fields:
            - emergency_contact_*: Link to parent/guardian account
        
        Relationship Table:
            Judges table links parent (judge_id) to child (child_id)
    
    Metrics & Performance:
        points: Deprecated field (use properties instead)
        drops: Number of drops applied (penalty system)
        bids: Number of bids earned (tournament achievements)
        tournaments_attended_number: Count of tournaments attended
        
        Computed Properties:
            - tournament_points: Sum from Tournament_Performance
            - effort_points: Sum from Effort_Score
    
    Contact Information:
        Primary:
            - email, phone_number: User's own contact info
        
        Emergency Contact (for children):
            - emergency_contact_first_name, emergency_contact_last_name
            - emergency_contact_number, emergency_contact_email
            - emergency_contact_relationship (parent, guardian, etc.)
    
    Security:
        - password: Hashed password (werkzeug.security)
        - Nullable for ghost accounts (no password until claimed)
    
    Columns:
        id: Primary key
        first_name, last_name: User's name (required)
        email: User's email (nullable for ghost accounts)
        password: Hashed password (nullable for ghost accounts)
        phone_number: User's phone (nullable)
        is_parent: Boolean indicating parent (True) or child (False)
        role: Authorization level (0=member, 1=EL, 2+=admin)
        judging_reqs: Legacy field for judging requirements
        emergency_contact_*: Emergency contact info (for children)
        child_first_name, child_last_name: Child info (for parents)
        points: Deprecated (use tournament_points + effort_points)
        drops: Number of drops applied
        bids: Number of bids earned
        tournaments_attended_number: Count of tournaments
        account_claimed: False for ghost accounts, True for claimed
    
    Relationships:
        - judge: Judges relationships where user is judge (parent)
        - child: Judges relationships where user is child
        - tournament_signups: Tournament registrations
        - tournament_performances: Tournament results
        - effort_score_user: Effort scores received
        - effort_score_given_by: Effort scores given to others
        - published_rosters: Roster publication notifications
        - penalty_entries: Roster penalties applied
        - And many more via backref...
    
    Properties:
        tournament_points: Sum of points from Tournament_Performance
        effort_points: Sum of scores from Effort_Score
    
    Note:
        Names (first_name, last_name, child_*, emergency_contact_*) stored
        lowercase for case-insensitive matching.
    """
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    
    email = db.Column(db.String(50), nullable=True)
    password = db.Column(db.String(500), nullable=True)
    phone_number = db.Column(db.String(50), nullable=True)

    is_parent = db.Column(db.Boolean, default=False)
    role = db.Column(db.Integer, default=0)
    # 0 = member, 1 = EL, 2 = chair+

    judging_reqs = db.Column(db.String(5000), nullable=True)

    emergency_contact_first_name = db.Column(db.String(50), nullable=True)
    emergency_contact_last_name = db.Column(db.String(50), nullable=True)
    emergency_contact_number = db.Column(db.String(50), nullable=True)
    emergency_contact_relationship = db.Column(db.String(50), nullable=True)
    emergency_contact_email = db.Column(db.String(50), nullable=True)

    child_first_name = db.Column(db.String(50), nullable=True)
    child_last_name = db.Column(db.String(50), nullable=True)

    points = db.Column(db.Integer, default=0)
    drops = db.Column(db.Integer, default=0)
    bids = db.Column(db.Integer, default=0)

    tournaments_attended_number = db.Column(db.Integer, default=0)
    #tournaments_attended_name = db.relationship('tournaments', backref='attendee') MAYBE NEEDED? wissam 5/12/25

    @property
    def tournament_points(self):
        from mason_snd.models.tournaments import Tournament_Performance
        performances = Tournament_Performance.query.filter_by(user_id=self.id).all()
        return sum([p.points or 0 for p in performances])

    @property
    def effort_points(self):
        from mason_snd.models.events import Effort_Score
        scores = Effort_Score.query.filter_by(user_id=self.id).all()
        return sum([s.score or 0 for s in scores])

    @property
    def weighted_points(self):
        """Calculate weighted points with drop penalty applied.
        
        Weighted points = (tournament_points * tournament_weight) + (effort_points * effort_weight) - (drops * 10)
        
        Each drop deducts 10 points from the weighted score, affecting:
        - Roster generation rankings
        - Manage members display
        - User rankings and analytics
        - All systems using weighted_points for sorting/comparison
        
        Returns:
            float: Weighted points with drop penalty applied, rounded to 2 decimals.
        """
        from mason_snd.models.metrics import MetricsSettings
        
        settings = MetricsSettings.query.first()
        if not settings:
            settings = MetricsSettings()
            db.session.add(settings)
            db.session.commit()
        
        tournament_weight = settings.tournament_weight
        effort_weight = settings.effort_weight
        
        base_weighted = (self.tournament_points * tournament_weight) + (self.effort_points * effort_weight)
        drop_penalty = (self.drops or 0) * 10
        
        return round(base_weighted - drop_penalty, 2)

    account_claimed = db.Column(db.Boolean, default=False)

class User_Published_Rosters(db.Model):
    """Tracks roster publication notifications for users.
    
    Created when a roster is published and a user is included. Enables notification
    system on user profile to alert users of new published rosters.
    
    Notification Flow:
        1. Admin publishes roster for tournament/event
        2. User_Published_Rosters entry created for each user on roster
        3. notified=False indicates "new" roster (not yet seen)
        4. When user views own profile, notified set to True
        5. "New" badge removed from roster notification
    
    Purpose:
        - Alert users when they're included in published rosters
        - Track which rosters users have/haven't seen
        - Enable notification system on profile page
        - Prevent repeated "new" badges after viewing
    
    Columns:
        id: Primary key
        user_id: User being notified (foreign key to User)
        roster_id: Published roster (foreign key to Roster)
        tournament_id: Tournament roster belongs to (foreign key to Tournament)
        event_id: Event roster is for (foreign key to Event)
        notified: False = new/unseen, True = seen by user
        created_at: When notification created (EST timezone)
    
    Relationships:
        user: User being notified (backref: published_rosters)
        roster: Roster that was published (backref: published_users)
        tournament: Tournament context (backref: published_roster_entries)
        event: Event context (backref: published_roster_entries)
    
    Usage:
        Display on profile page:
            - Query unnotified entries (notified=False)
            - Show as "new" rosters
            - Mark as seen when user views profile
        
        Admin workflow:
            - Create entries when publishing roster
            - One entry per user on roster
            - Links roster to tournament and event context
    
    Note:
        Notification auto-marked as seen only when user views own profile,
        not when admin views it (preserves "new" status).
    """
    id = db.Column(db.Integer, primary_key=True)
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    roster_id = db.Column(db.Integer, db.ForeignKey('roster.id'), nullable=False)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    notified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('US/Eastern')))
    
    user = db.relationship('User', foreign_keys=[user_id], backref='published_rosters')
    roster = db.relationship('Roster', foreign_keys=[roster_id], backref='published_users')
    tournament = db.relationship('Tournament', foreign_keys=[tournament_id], backref='published_roster_entries')
    event = db.relationship('Event', foreign_keys=[event_id], backref='published_roster_entries')

class Roster_Penalty_Entries(db.Model):
    """Tracks penalty entries in published rosters (displayed as '+1').
    
    When a user has drops applied and moves down in the roster, this creates
    a penalty entry to display '+1' instead of the user's name in the original
    position. Indicates roster penalty applied to user.
    
    Penalty System:
        Purpose:
            - Apply consequences for missed commitments
            - Move penalized users down in roster priority
            - Show '+1' placeholder in original position
        
        Algorithm:
            1. User has drops applied (User.drops > 0)
            2. Roster generation moves user down by N positions
            3. Original position shows '+1' instead of name
            4. Penalty entry created to track this
        
        Display:
            - Original rank shows '+1' instead of user name
            - Indicates penalty applied, not actual roster slot
            - User appears lower in actual roster
    
    Columns:
        id: Primary key
        roster_id: Roster containing penalty (foreign key to Roster)
        tournament_id: Tournament context (foreign key to Tournament)
        event_id: Event context (foreign key to Event)
        penalized_user_id: User who was penalized (foreign key to User)
        original_rank: Position where '+1' displays (user's pre-penalty rank)
        drops_applied: Number of drops that caused penalty
        created_at: When penalty entry created (EST timezone)
    
    Relationships:
        roster: Roster containing penalty (backref: penalty_entries)
        tournament: Tournament context (backref: penalty_entries)
        event: Event context (backref: penalty_entries)
        penalized_user: User penalized (backref: penalty_entries)
    
    Usage:
        Roster generation:
            - Calculate user's pre-penalty rank
            - Apply drops (move user down)
            - Create penalty entry for original position
            - Store drops_applied for audit trail
        
        Roster display:
            - Query penalty entries for roster
            - Show '+1' at original_rank positions
            - Show actual users at their post-penalty positions
    
    Example:
        User normally rank 3, but has 2 drops:
        - User moved to rank 5 in actual roster
        - Penalty entry created: original_rank=3, drops_applied=2
        - Roster displays '+1' at position 3
        - User's name appears at position 5
    
    Note:
        Multiple penalty entries possible in same roster if multiple users
        have drops applied.
    """
    id = db.Column(db.Integer, primary_key=True)
    
    roster_id = db.Column(db.Integer, db.ForeignKey('roster.id'), nullable=False)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    penalized_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    original_rank = db.Column(db.Integer, nullable=False)
    drops_applied = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('US/Eastern')))
    
    roster = db.relationship('Roster', foreign_keys=[roster_id], backref='penalty_entries')
    tournament = db.relationship('Tournament', foreign_keys=[tournament_id], backref='penalty_entries')
    event = db.relationship('Event', foreign_keys=[event_id], backref='penalty_entries')
    penalized_user = db.relationship('User', foreign_keys=[penalized_user_id], backref='penalty_entries')

class Judges(db.Model):
    """Parent-child relationship tracking for judge commitments.
    
    Links parent/guardian accounts (judges) to child/competitor accounts.
    Enables profile access across family members, judge commitments for
    tournaments, and roster generation with judge availability.
    
    Purpose:
        - Establish parent-child relationships
        - Enable profile access (parents view children, children view parents)
        - Track which parents can judge for which children
        - Support roster generation (children need judges)
        - Manage background check status for judges
    
    Relationship Types:
        Parent → Child:
            - Parent adds child account (add_child route)
            - Creates Judges entry (judge_id=parent, child_id=child)
            - Enables parent to view child's profile
        
        Child → Parent:
            - Child adds parent account (add_judge route)
            - Creates Judges entry (judge_id=parent, child_id=child)
            - Enables child to view parent's profile
        
        Ghost Accounts:
            - Relationship created even if parent/child doesn't exist yet
            - Ghost account created as placeholder
            - Relationship preserved when ghost account claimed
    
    Background Checks:
        background_check field:
            - False: Judge not yet background checked (default)
            - True: Judge has cleared background check
        
        Purpose:
            - Some tournaments require background-checked judges
            - Track which judges are cleared
            - Enable filtering in roster generation
    
    Columns:
        id: Primary key
        background_check: Boolean indicating cleared background check
        judge_id: Parent/guardian user (foreign key to User)
        child_id: Child/competitor user (foreign key to User)
    
    Relationships:
        judge: Parent/guardian User object (backref: judge)
        child: Child User object (backref: child)
    
    Access Control:
        Profile viewing:
            - Parent can view child profile via Judges link
            - Child can view parent profile via reverse Judges link
            - Checked in profile.index() route
        
        Query patterns:
            - Find parent for child: Judges.query.filter_by(child_id=X)
            - Find children for parent: Judges.query.filter_by(judge_id=X)
            - Check relationship exists: filter both directions
    
    Usage:
        Tournament signup:
            - Child selects which judge to bring (from Judges relationships)
            - Tournament_Judges entry created for commitment
        
        Roster generation:
            - Query children and their available judges
            - Assign judges to cover competitors
            - Consider background check status if required
    
    Note:
        Multiple Judges entries possible:
        - One child can have multiple parents/guardians
        - One parent can have multiple children
        - Each relationship tracked separately
    """
    id = db.Column(db.Integer, primary_key=True)
    background_check = db.Column(db.Boolean, default=False)

    judge_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    child_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    judge = db.relationship('User', foreign_keys=[judge_id], backref='judge')
    child = db.relationship('User', foreign_keys=[child_id], backref='child')