"""Tournament Models - Tournament management and participation tracking.

Defines tournaments, custom registration forms, signups, attendance tracking,
performance results, judge commitments, and partner pairings.

Key Models:
    Tournament: Tournament event details and deadlines
    Form_Fields: Custom registration form fields
    Form_Responses: User responses to registration forms
    Tournament_Signups: User registrations for tournaments
    Tournaments_Attended: Attendance tracking
    Tournament_Performance: Competition results and rankings
    Tournament_Judges: Judge commitment tracking
    Tournament_Partners: Partner pairings for partner events

Tournament Lifecycle:
    1. Tournament created with details and deadlines
    2. Custom form fields defined (if needed)
    3. Users sign up (Tournament_Signups, Form_Responses)
    4. Rosters generated from signups
    5. Tournament occurs
    6. Results submitted (Tournament_Performance)
    7. Attendance marked (Tournaments_Attended)

Custom Forms:
    - Dynamic form fields per tournament
    - Various field types (text, select, checkbox, etc.)
    - Required/optional fields
    - User responses tracked separately
"""

from ..extensions import db
from datetime import datetime
import pytz

# Define EST timezone
EST = pytz.timezone('US/Eastern')

class Tournament(db.Model):
    """Tournament event with dates, location, and deadlines.
    
    Represents a speech and debate tournament with signup deadlines,
    performance result submission tracking, and roster generation.
    
    Columns:
        id: Primary key
        name: Tournament name (String, 255 chars)
        date: Tournament date (DateTime)
        address: Tournament location (String, 255 chars)
        signup_deadline: Last day for user signups (DateTime)
        performance_deadline: Last day to submit results (DateTime)
        results_submitted: Whether results have been submitted (Boolean)
        created_at: When tournament created (DateTime, EST)
    
    Deadlines:
        signup_deadline:
            - Users can register until this date
            - After deadline, registrations closed
            - Used by signup form validation
        
        performance_deadline:
            - Admin can submit results until this date
            - After deadline, results finalized
            - Used by results submission form
    
    Results Submission:
        results_submitted field:
            - False: Results not yet submitted (default)
            - True: Results finalized, performance data entered
        
        Purpose:
            - Track completion status
            - Prevent duplicate result entry
            - Enable result submission workflow
    
    Relationships:
        form_fields: Custom registration form fields
        form_responses: User responses to form fields
        tournament_signups: User registrations
        tournaments_attended: Attendance records
        tournament_performances: Competition results
        tournament_judges: Judge commitments
        tournament_partners: Partner pairings
        rosters: Generated rosters for this tournament
        published_roster_entries: Roster publication notifications
        penalty_entries: Roster penalty tracking
    
    Note:
        All timestamps in EST timezone for consistency.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    address = db.Column(db.String(255), nullable=False)
    signup_deadline = db.Column(db.DateTime, nullable=False)
    performance_deadline = db.Column(db.DateTime, nullable=False)
    results_submitted = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(EST), nullable=False)

class Form_Fields(db.Model):
    """Custom registration form fields for tournaments.
    
    Enables dynamic, tournament-specific registration forms with various
    field types (text, select, checkbox, etc.) and required/optional flags.
    
    Purpose:
        - Create custom questions per tournament
        - Collect additional signup information
        - Support various input types
        - Mark fields as required/optional
    
    Field Types:
        Supported types (examples):
            - text: Single-line text input
            - textarea: Multi-line text input
            - select: Dropdown menu (options in options field)
            - checkbox: Boolean yes/no
            - radio: Multiple choice (options in options field)
            - And more...
    
    Options Field:
        For select/radio fields:
            - Stores available choices
            - Format: Likely JSON or delimited string
            - Example: "Option 1|Option 2|Option 3"
        
        For other field types:
            - NULL (not applicable)
    
    Required Fields:
        required flag:
            - True: User must fill out to submit
            - False: Optional field
        
        Validation:
            - Enforced during form submission
            - Prevents incomplete registrations
    
    Columns:
        id: Primary key
        label: Field label/question text (Text)
        type: Field type (text, select, checkbox, etc.) (Text)
        options: Available options for select/radio (Text, nullable)
        required: Whether field is required (Boolean, default False)
        tournament_id: Tournament this field belongs to (foreign key)
    
    Relationships:
        tournament: Tournament object (backref: form_fields)
        responses: User responses to this field (backref via Form_Responses)
    
    Usage:
        Admin creates fields:
            - Define label (question text)
            - Select type (text, select, etc.)
            - Set options (if applicable)
            - Mark required (if mandatory)
        
        User fills form:
            - See all fields for tournament
            - Required fields marked with *
            - Submit responses (Form_Responses)
    
    Common Fields:
        - "Dietary restrictions?" (text, optional)
        - "T-shirt size" (select, required)
        - "Bringing spectators?" (checkbox, optional)
        - "Event preferences" (select, optional)
    
    Note:
        Fields tied to specific tournament (not reusable across tournaments).
        Delete tournament also deletes associated form fields.
    """
    __tablename__ = 'form_fields'
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.Text, nullable=False)
    type = db.Column(db.Text, nullable=False)
    options = db.Column(db.Text, nullable=True)
    required = db.Column(db.Boolean, nullable=False, default=False)
    
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    tournament = db.relationship('Tournament', foreign_keys=[tournament_id], backref='form_fields')

class Form_Responses(db.Model):
    """User responses to tournament registration form fields.
    
    Stores individual user answers to custom form fields defined for
    a tournament. One response record per field per user per tournament.
    
    Purpose:
        - Store user answers to custom form questions
        - Link responses to specific users and fields
        - Track submission timestamp
        - Enable form data retrieval for admins
    
    Response Storage:
        response field:
            - Text field (flexible for all answer types)
            - Stores answer regardless of field type:
                * Text fields: User's text input
                * Select fields: Selected option
                * Checkbox fields: "true"/"false" or similar
                * Etc.
    
    Data Model:
        One record per:
            - User (user_id)
            - Tournament (tournament_id)
            - Form field (field_id)
        
        Example:
            Tournament X has 3 custom fields.
            User Y signs up and fills form.
            Result: 3 Form_Responses records (one per field).
    
    Columns:
        id: Primary key
        response: User's answer to field (Text, nullable)
        submitted_at: When response submitted (DateTime, EST)
        tournament_id: Tournament context (foreign key)
        user_id: User who submitted response (foreign key)
        field_id: Form field being answered (foreign key)
    
    Relationships:
        tournament: Tournament object (backref: form_responses)
        field: Form field object (backref: responses)
        user: User who submitted (backref: form_responses)
    
    Usage:
        User submission:
            - For each form field, create Form_Responses record
            - Store user's answer in response field
            - Timestamp with submitted_at
        
        Admin retrieval:
            - Query responses by tournament_id
            - Group by user_id to see complete submissions
            - Filter by field_id to see all answers to specific question
    
    Queries:
        All responses for user in tournament:
            Form_Responses.query.filter_by(
                tournament_id=X, user_id=Y
            ).all()
        
        All answers to specific question:
            Form_Responses.query.filter_by(
                field_id=Z
            ).all()
    
    Note:
        Nullable response field allows partial form saves (draft mode).
        submitted_at tracks when answer provided (can update later).
    """
    id = db.Column(db.Integer, primary_key=True)
    response = db.Column(db.Text, nullable=True)
    submitted_at = db.Column(db.DateTime, default=lambda: datetime.now(EST), nullable=False)

    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    field_id = db.Column(db.Integer, db.ForeignKey('form_fields.id'), nullable=False)


    tournament = db.relationship('Tournament', foreign_keys=[tournament_id], backref='form_responses')
    field = db.relationship('Form_Fields', foreign_keys=[field_id], backref='responses')
    user = db.relationship('User', foreign_keys=[user_id], backref='form_responses')

class Tournament_Signups(db.Model):
    """User tournament registration with judge and partner assignments.
    
    Tracks user signups for specific events at tournaments, including whether
    they're bringing a judge, which judge, attendance confirmation, and partner
    pairings for partner events.
    
    Purpose:
        - Register user for event at tournament
        - Track judge commitment (bringing_judge, judge_id)
        - Confirm attendance (is_going)
        - Link partners for partner events (partner_id)
        - Enable roster generation from signups
    
    Judge Commitment:
        bringing_judge field:
            - True: User committing to bring a judge
            - False: User not bringing judge
        
        judge_id field:
            - If bringing_judge=True: ID of judge user
            - 0 or NULL: No specific judge assigned
        
        Purpose:
            - Track judge availability for roster generation
            - Ensure sufficient judges for tournament
            - Link children to their judges
    
    Attendance:
        is_going field:
            - True: User confirmed attendance
            - False: User not attending or unsure
        
        Purpose:
            - Filter confirmed attendees for roster generation
            - Track commitment level
            - Enable waitlist management
    
    Partner Events:
        partner_id field:
            - For partner events (PF, etc.): ID of partner user
            - NULL: No partner or not partner event
        
        Purpose:
            - Link debate/speech partners
            - Ensure partners both registered
            - Generate rosters with partner pairings
    
    Columns:
        id: Primary key
        bringing_judge: Boolean indicating judge commitment
        is_going: Boolean indicating confirmed attendance
        created_at: When signup was created (DateTime, EST)
        user_id: User registering (foreign key to User)
        tournament_id: Tournament context (foreign key to Tournament)
        event_id: Event registering for (foreign key to Event)
        judge_id: Judge being brought (foreign key to User, nullable)
        partner_id: Partner for partner events (foreign key to User, nullable)
    
    Relationships:
        user: User registering (backref: tournament_signups)
        tournament: Tournament object (backref: tournament_signups)
        event: Event object (backref: tournament_signups)
        judge: Judge user object (backref: judge_id_tournament_signup)
        partner: Partner user object (backref: partner_tournament_signup)
    
    Roster Generation:
        Query signups:
            - Filter by tournament_id, event_id
            - Filter is_going=True (confirmed attendees)
            - Group by judge availability
            - Pair partners (partner_id)
        
        Judge allocation:
            - Count judges available (bringing_judge=True)
            - Assign competitors to judges
            - Ensure judge coverage
    
    Validation:
        - User can only sign up once per event per tournament (unique constraint)
        - Partner must also be signed up for same event
        - Judge must exist in User table
    
    Note:
        judge_id uses special foreign key name to avoid conflicts.
        Default judge_id=0 indicates no judge (not NULL for SQL compatibility).
    """
    id = db.Column(db.Integer, primary_key=True)

    bringing_judge = db.Column(db.Boolean, default=False)
    is_going = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(EST), nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'))
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    judge_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id', name='fk_tournament_signups_judge_id_user'),
        nullable=True,
        default=0
    )
    partner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    user = db.relationship('User', foreign_keys=[user_id], backref='tournament_signups')
    tournament = db.relationship('Tournament', foreign_keys=[tournament_id], backref='tournament_signups')
    event = db.relationship('Event', foreign_keys=[event_id], backref='tournament_signups')
    judge = db.relationship('User', foreign_keys=[judge_id], backref="judge_id_tournament_signup")
    partner = db.relationship('User', foreign_keys=[partner_id], backref="partner_tournament_signup")

class Tournaments_Attended(db.Model):
    """Attendance tracking for tournaments.
    
    Records which users actually attended tournaments (vs. signed up but didn't attend).
    Used for attendance statistics, commitment tracking, and historical records.
    
    Purpose:
        - Track actual attendance (vs. signups)
        - Build attendance history per user
        - Calculate attendance rates
        - Award attendance-based achievements
        - Identify commitment issues (signup but no-show)
    
    Attendance Workflow:
        1. User signs up (Tournament_Signups created)
        2. Tournament occurs
        3. Admin marks attendance (Tournaments_Attended created)
        4. Attendance counted toward user stats
    
    Columns:
        id: Primary key
        user_id: User who attended (foreign key to User)
        tournament_id: Tournament attended (foreign key to Tournament)
    
    Relationships:
        user: User object (backref: tournaments_attended)
        tournament: Tournament object (backref: tournaments_attended)
    
    Usage:
        Admin marks attendance:
            - After tournament, mark attendees
            - Create Tournaments_Attended for each attendee
            - Compare to Tournament_Signups to find no-shows
        
        User statistics:
            - Count Tournaments_Attended for attendance total
            - Compare to Tournament_Signups for commitment rate
            - Display on user profile or metrics
    
    Queries:
        User's attendance:
            Tournaments_Attended.query.filter_by(user_id=X).count()
        
        Tournament attendees:
            Tournaments_Attended.query.filter_by(tournament_id=Y).all()
        
        No-shows (signed up but didn't attend):
            Signups NOT IN Tournaments_Attended
    
    Note:
        Simple model (just IDs, no timestamps). Consider adding attended_at
        timestamp if needed for detailed tracking.
    """
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'))

    user = db.relationship('User', foreign_keys=[user_id], backref='tournaments_attended')
    tournament = db.relationship('Tournament', foreign_keys=[tournament_id], backref='tournaments_attended')

class Tournament_Performance(db.Model):
    """User competition results and rankings for tournaments.
    
    Stores performance data including points, bids, rankings, and elimination
    round progress. Used for metrics calculation and performance tracking.
    
    Purpose:
        - Record competition results
        - Track points earned (for weighted metrics)
        - Award bids (qualification achievements)
        - Record rankings and elimination progress
        - Enable performance analysis
    
    Points System:
        points field:
            - Numeric points earned at tournament
            - Used in weighted metrics calculation
            - May vary by tournament tier/importance
            - NULL if tournament doesn't use points
    
    Bid System:
        bid field:
            - True: User earned bid at this tournament
            - False/NULL: No bid earned
        
        Purpose:
            - Track qualification achievements
            - Count total bids for user (User.bids)
            - Display achievements on profile
    
    Ranking:
        rank field:
            - Numeric rank/placement (1=first, 2=second, etc.)
            - NULL if rank not tracked or DNF
        
        Purpose:
            - Display placement on profile
            - Calculate points based on rank
            - Award achievements for top placements
    
    Elimination Rounds:
        stage field (0-5 indicating progress):
            - 0: Did not break (prelims only)
            - 1: Double octas (reached but eliminated)
            - 2: Octas (octafinals)
            - 3: Quarters (quarterfinals)
            - 4: Semis (semifinals)
            - 5: Finals (championship round)
        
        Purpose:
            - Track elimination round progress
            - Award achievements for breaking
            - Display on user profile
            - Calculate advanced performance metrics
    
    Columns:
        id: Primary key
        points: Points earned (Integer, nullable)
        bid: Boolean indicating bid earned (nullable)
        rank: Placement/rank (Integer, nullable)
        stage: Elimination round reached (Integer, 0-5)
        user_id: User who competed (foreign key to User)
        tournament_id: Tournament context (foreign key to Tournament)
    
    Relationships:
        user: User object (backref: tournament_performances)
        tournament: Tournament object (backref: tournament_performances)
    
    Metrics Integration:
        User.tournament_points property:
            - Sums points from all Tournament_Performance records
            - Used in weighted metrics calculation
            - Combined with effort_points for total score
    
    Usage:
        Admin submits results:
            - After tournament, enter performance data
            - Create Tournament_Performance for each competitor
            - Set points, bid, rank, stage as applicable
        
        User views results:
            - Display on profile or tournament page
            - Show achievements (bids, top placements)
            - Track progress over time
    
    Note:
        Not all fields required for every tournament. Flexibility allows
        different tournament formats (some use points, some use ranks, etc.).
    
    Point System:
        Points calculated using formula: 1 + 9 * ((n - r)/(n-1))^k
        - n: total_competitors (how many people competed in the event)
        - r: overall_rank (the user's overall placement)
        - k: decay_coefficient (default 2, controls how steeply points drop off)
        
        This provides a fairer, more granular scoring system (1-10 points possible).
        The minimum number of points is 1, and the max is 10.
        
        Legacy Support:
        - Old results may not have total_competitors/overall_rank
        - These display original points value without recalculation
        - Users can edit old results to add competitor count for updated scoring
    """
    id = db.Column(db.Integer, primary_key=True)

    points = db.Column(db.Integer)
    bid = db.Column(db.Boolean)
    rank = db.Column(db.Integer)
    stage = db.Column(db.Integer)
    # 0 = nothing, 1 = double octas, 2 = octas, 3 = quarters, 4 = semis, 5 = finals
    
    # New fields for refined ranking system (added 2025)
    overall_rank = db.Column(db.Integer, nullable=True)  # User's overall placement at tournament
    total_competitors = db.Column(db.Integer, nullable=True)  # Total number of competitors in the event
    decay_coefficient = db.Column(db.Float, default=2.0, nullable=True)  # K value for points formula

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'))

    user = db.relationship('User', foreign_keys=[user_id], backref='tournament_performances')
    tournament = db.relationship('Tournament', foreign_keys=[tournament_id], backref='tournament_performances')

class Tournament_Judges(db.Model):
    """Judge commitments for specific tournaments and events.
    
    Tracks which judges are committed to judge for which children at specific
    tournaments and events. Separate from general Judges relationship (which
    is permanent), this tracks per-tournament commitments.
    
    Purpose:
        - Track judge commitments per tournament
        - Link judges to children for specific events
        - Confirm judge acceptance of commitment
        - Enable roster generation with judge assignments
        - Ensure sufficient judge coverage
    
    Relationship Types:
        Judges table (models/auth.py):
            - Permanent parent-child relationship
            - General judge availability
            - Background check status
        
        Tournament_Judges (this model):
            - Specific tournament commitment
            - Per-event assignment
            - Accepted/pending status
    
    Acceptance Tracking:
        accepted field:
            - False: Judge commitment pending acceptance (default)
            - True: Judge confirmed they will judge
        
        Purpose:
            - Track judge confirmation status
            - Prevent assuming unconfirmed judges
            - Enable reminder system for pending acceptances
    
    Columns:
        id: Primary key
        accepted: Boolean indicating judge confirmed (default False)
        judge_id: Judge user (foreign key to User)
        child_id: Child/competitor user (foreign key to User)
        tournament_id: Tournament context (foreign key to Tournament)
        event_id: Event being judged (foreign key to Event, nullable)
    
    Relationships:
        judge: Judge user object (backref: tournament_judges_judge)
        child: Child user object (backref: tournament_judges_child)
        tournament: Tournament object (backref: tournament_judges)
        event: Event object (backref: tournament_judges)
    
    Workflow:
        Signup:
            1. Child signs up for tournament (Tournament_Signups)
            2. Child selects judge to bring (from Judges relationships)
            3. Tournament_Judges entry created (accepted=False)
            4. Judge notified of commitment
        
        Acceptance:
            5. Judge accepts or declines commitment
            6. If accepted: accepted=True
            7. If declined: Entry deleted or marked differently
        
        Roster generation:
            8. Query accepted judges (accepted=True)
            9. Assign competitors to judges
            10. Generate roster with judge coverage
    
    Usage:
        Admin queries:
            - Find judges for tournament/event
            - Check acceptance status
            - Send reminders to unaccepted judges
        
        Roster generation:
            - Filter accepted=True
            - Count judges per child
            - Ensure minimum judge coverage
    
    Validation:
        - Judge must exist in Judges table (parent-child relationship)
        - Child must be signed up for same tournament/event
        - One judge per child per event (typically)
    
    Note:
        event_id nullable for tournament-wide judge commitments vs.
        event-specific assignments.
    """
    id = db.Column(db.Integer, primary_key=True)

    accepted = db.Column(db.Boolean, default=False)

    judge_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    child_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'))
    event_id = db.Column(db.Integer, db.ForeignKey('event.id', name='fk_tournament_judges_event_id'), nullable=True)

    judge = db.relationship('User', foreign_keys=[judge_id], backref='tournament_judges_judge')
    child = db.relationship('User', foreign_keys=[child_id], backref='tournament_judges_child')
    tournament = db.relationship('Tournament', foreign_keys=[tournament_id], backref='tournament_judges')
    event = db.relationship('Event', foreign_keys=[event_id], backref='tournament_judges')

class Tournament_Partners(db.Model):
    """Partner pairings for partner events at tournaments.
    
    Tracks which users are partnered together for specific partner events
    (e.g., Public Forum debate) at specific tournaments. Created when both
    partners sign up and confirm pairing.
    
    Purpose:
        - Link partners for partner events (PF, Policy, Duo Interp, etc.)
        - Ensure both partners registered for same event
        - Enable roster generation with partner pairings
        - Track partnership history
        - Prevent solo entries in partner events
    
    Partner Event System:
        Event.is_partner_event:
            - True: Event requires partners (PF, Policy, Duo, etc.)
            - False: Individual event (LD, Extemp, etc.)
        
        Partner pairing:
            - Both users must sign up (Tournament_Signups)
            - Partnership confirmed (creates Tournament_Partners)
            - Both partners linked in roster generation
    
    Bidirectional Relationship:
        partner1_user_id and partner2_user_id:
            - Arbitrary assignment (no "primary" partner)
            - Both users equal partners
            - Order doesn't matter for functionality
        
        Queries must check both directions:
            WHERE partner1_user_id=X OR partner2_user_id=X
    
    Columns:
        id: Primary key
        partner1_user_id: First partner (foreign key to User)
        partner2_user_id: Second partner (foreign key to User)
        tournament_id: Tournament context (foreign key to Tournament)
        event_id: Partner event (foreign key to Event)
        created_at: When partnership created (DateTime, EST)
    
    Relationships:
        partner1_user: First partner User object (backref: tournament_partner1)
        partner2_user: Second partner User object (backref: tournament_partner2)
        tournament: Tournament object (backref: tournament_partners)
        event: Event object (backref: tournament_partners)
    
    Workflow:
        Partnership creation:
            1. User A signs up for partner event
            2. User B signs up for same partner event
            3. Users agree to partner (UI workflow)
            4. Tournament_Partners entry created
            5. Both users linked for roster generation
        
        Roster generation:
            6. Query Tournament_Partners for event
            7. Group partners together in roster
            8. Ensure both partners have judges (if needed)
    
    Validation:
        - Both partners must be signed up (Tournament_Signups)
        - Event must be partner event (is_partner_event=True)
        - Both partners must be for same tournament and event
        - Each user can have max one partner per event per tournament
    
    Queries:
        Find user's partner:
            Tournament_Partners.query.filter(
                (Tournament_Partners.partner1_user_id == user_id) |
                (Tournament_Partners.partner2_user_id == user_id),
                Tournament_Partners.tournament_id == tournament_id,
                Tournament_Partners.event_id == event_id
            ).first()
        
        All partnerships for event:
            Tournament_Partners.query.filter_by(
                tournament_id=X, event_id=Y
            ).all()
    
    Note:
        Created_at timestamp tracks when partnership formed (useful for
        resolving conflicts if multiple pairing attempts occur).
    """
    id = db.Column(db.Integer, primary_key=True)

    partner1_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    partner1_user = db.relationship('User', foreign_keys=[partner1_user_id], backref='tournament_partner1')

    partner2_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    partner2_user = db.relationship('User', foreign_keys=[partner2_user_id], backref='tournament_partner2')

    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    tournament = db.relationship('Tournament', foreign_keys=[tournament_id], backref='tournament_partners')

    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    event = db.relationship('Event', foreign_keys=[event_id], backref='tournament_partners')

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(EST), nullable=False)
