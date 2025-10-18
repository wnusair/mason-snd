"""Roster Models - Tournament roster generation and management.

Defines rosters, judge assignments, competitor entries, and partner pairings
for tournament attendance. Rosters allocate competitors to judges and track
publication status.

Key Models:
    Roster: Tournament roster with publication tracking
    Roster_Judge: Judge assignments with competitor counts
    Roster_Competitors: Individual competitor entries with judge links
    Roster_Partners: Partner pairings for partner events

Roster System:
    - Generated from tournament signups (Tournament_Signups)
    - Assigns competitors to available judges
    - Tracks publication status and timestamps
    - Supports manual editing before publication
    - Notifies users when published (User_Published_Rosters)

Roster Generation Algorithm:
    1. Query confirmed signups (is_going=True)
    2. Identify available judges (bringing_judge=True)
    3. Calculate judge capacity (people_bringing)
    4. Allocate competitors to judges (priority-based)
    5. Handle penalty entries (drops applied)
    6. Pair partners (for partner events)
    7. Create Roster_Judge and Roster_Competitors entries

Publishing Workflow:
    - Draft rosters: published=False (editable)
    - Published rosters: published=True (locked, notifications sent)
    - Users notified via User_Published_Rosters entries
"""

from ..extensions import db
from datetime import datetime
import pytz

# Define EST timezone
EST = pytz.timezone('US/Eastern')

class Roster(db.Model):
    """Tournament roster with publication tracking.
    
    Represents a generated or manually created roster for a tournament,
    with publication status and timestamps.
    
    Purpose:
        - Store roster metadata (name, tournament, dates)
        - Track publication status (draft vs. published)
        - Enable roster versioning (multiple rosters per tournament)
        - Link to roster components (judges, competitors, partners)
    
    Publication System:
        published field:
            - False: Draft roster (editable, not visible to users)
            - True: Published roster (locked, notifications sent)
        
        published_at field:
            - NULL: Not yet published
            - DateTime: When roster was published (EST)
        
        Workflow:
            1. Generate roster (published=False)
            2. Admin reviews/edits roster
            3. Admin publishes (published=True, published_at=now)
            4. Users notified (User_Published_Rosters created)
            5. Roster locked (no further edits)
    
    Versioning:
        Purpose:
            - Multiple rosters per tournament (drafts, revisions)
            - Track roster evolution over time
            - Compare different roster strategies
        
        Implementation:
            - No unique constraint on tournament_id
            - Multiple Roster records can share same tournament
            - Typically one published, others drafts/archives
    
    Columns:
        id: Primary key
        name: Roster name/identifier (String)
        published: Publication status (Boolean, default False)
        published_at: Publication timestamp (DateTime, nullable)
        tournament_id: Tournament context (foreign key, nullable)
        date_made: Creation timestamp (DateTime, EST)
    
    Relationships:
        tournament: Tournament object (backref: rosters)
        roster_judge_roster: Roster_Judge entries (judges and allocations)
        roster_judge_roster_competitors: Roster_Competitors entries
        published_users: User_Published_Rosters (notification tracking)
        penalty_entries: Roster_Penalty_Entries (penalty tracking)
        roster_partners: Roster_Partners (partner pairings)
    
    Usage:
        Generate roster:
            roster = Roster(
                name="Tournament X - LD Roster",
                tournament_id=tournament_id,
                published=False
            )
            # Create Roster_Judge, Roster_Competitors entries
        
        Publish roster:
            roster.published = True
            roster.published_at = datetime.now(EST)
            # Create User_Published_Rosters notifications
            db.session.commit()
        
        Query published rosters:
            Roster.query.filter_by(
                tournament_id=X,
                published=True
            ).all()
    
    Archiving:
        - Old rosters preserved (not deleted)
        - Query by tournament_id for history
        - Use published=False for archived drafts
        - Use date_made for chronological ordering
    
    Note:
        tournament_id nullable allows event-only rosters (not tournament-specific).
        Consider making required if all rosters tied to tournaments.
    """
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String)
    
    published = db.Column(db.Boolean, default=False)
    published_at = db.Column(db.DateTime, nullable=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=True)
    tournament = db.relationship('Tournament', foreign_keys=[tournament_id], backref='rosters')

    date_made = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('US/Eastern')))

class Roster_Judge(db.Model):
    """Judge assignments in rosters with competitor capacity.
    
    Represents a judge's assignment in a roster, including which child they're
    judging for and how many total people they're bringing (capacity).
    
    Purpose:
        - Assign judges to rosters
        - Link judges to children (who brought them)
        - Track judge capacity (people_bringing)
        - Enable competitor allocation to judges
        - Display judge names on published rosters
    
    Judge Capacity:
        people_bringing field:
            - Number of competitors assigned to this judge
            - Example: Judge brings 3 people = judge + 2 competitors
            - Used for roster balance (distribute competitors evenly)
        
        Calculation:
            - Based on Tournament_Signups.bringing_judge counts
            - May be manually adjusted by admin
            - Includes judge's own child if competing
    
    Parent-Child Link:
        user_id (judge) and child_id:
            - Links judge to specific child who brought them
            - Enables parent-child tracking in roster
            - Supports Judges relationship validation
        
        Note:
            Same judge may appear multiple times if judging for
            multiple children (different child_id values).
    
    Columns:
        id: Primary key
        user_id: Judge user (foreign key to User)
        child_id: Child who brought judge (foreign key to User)
        event_id: Event context (foreign key to Event)
        roster_id: Roster this assignment belongs to (foreign key to Roster)
        people_bringing: Competitor capacity (Integer)
    
    Relationships:
        user: Judge User object (backref: roster_judge_user)
        child: Child User object (backref: roster_judge_child)
        event: Event object (backref: roster_judge_event)
        roster: Roster object (backref: roster_judge_roster)
    
    Usage:
        Roster generation:
            1. Query Tournament_Signups (bringing_judge=True)
            2. Create Roster_Judge for each judge
            3. Set people_bringing from signup counts
            4. Link to child via child_id
        
        Competitor allocation:
            1. Query Roster_Judge for roster
            2. Allocate competitors based on people_bringing
            3. Create Roster_Competitors with judge_id
        
        Display:
            - Show judge names on roster
            - Group competitors by judge
            - Show judge capacity (X people)
    
    Queries:
        Judges for roster:
            Roster_Judge.query.filter_by(roster_id=X).all()
        
        Judge capacity:
            judge = Roster_Judge.query.get(id)
            capacity = judge.people_bringing
        
        Competitors for judge:
            Roster_Competitors.query.filter_by(
                roster_id=X,
                judge_id=judge.user_id
            ).count()
    
    Balance Algorithm:
        - Distribute competitors evenly across judges
        - Consider people_bringing for each judge
        - Prioritize judge's own child first
        - Fill remaining capacity with other competitors
    
    Note:
        people_bringing includes judge if they're also competing.
        Example: Judge brings self + 2 others = 3 people_bringing.
    """
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', foreign_keys=[user_id], backref='roster_judge_user')

    child_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    child = db.relationship('User', foreign_keys=[child_id], backref='roster_judge_child')

    event_id = db.Column(db.Integer, db.ForeignKey('event.id'))
    event = db.relationship('Event', foreign_keys=[event_id], backref='roster_judge_event')

    roster_id = db.Column(db.Integer, db.ForeignKey('roster.id'))
    roster = db.relationship('Roster', foreign_keys=[roster_id], backref='roster_judge_roster')

    people_bringing = db.Column(db.Integer)

class Roster_Competitors(db.Model):
    """Individual competitor entries in rosters with judge assignments.
    
    Represents each competitor on a roster, linked to their assigned judge.
    Enables roster display with competitor-judge pairings.
    
    Purpose:
        - List all competitors on roster
        - Assign competitors to judges
        - Enable roster sorting and display
        - Track who's attending tournament
        - Link competitors to judges for organization
    
    Judge Assignment:
        judge_id field:
            - Judge assigned to this competitor
            - Links to Roster_Judge.user_id
            - Typically competitor's parent, but may be redistributed
        
        Algorithm:
            1. Prioritize judge's own child
            2. Fill remaining judge capacity with other competitors
            3. Balance competitors across available judges
            4. Consider judge preferences/relationships
    
    Competitor Ordering:
        Purpose:
            - Display roster in organized fashion
            - Group by judge
            - Sort by priority/rank within judge
        
        Implementation:
            - Query by roster_id and event_id
            - Order by judge_id, then user priority
            - Display grouped by judge name
    
    Columns:
        id: Primary key
        user_id: Competitor user (foreign key to User)
        event_id: Event context (foreign key to Event)
        judge_id: Assigned judge (foreign key to User)
        roster_id: Roster this entry belongs to (foreign key to Roster)
    
    Relationships:
        user: Competitor User object (backref: roster_judge_user_competitors)
        event: Event object (backref: roster_judge_event_competitors)
        judge: Judge User object (backref: roster_judge_judge_competitors)
        roster: Roster object (backref: roster_judge_roster_competitors)
    
    Usage:
        Add competitor to roster:
            Roster_Competitors(
                user_id=competitor_id,
                event_id=event_id,
                judge_id=assigned_judge_id,
                roster_id=roster_id
            )
        
        Query roster competitors:
            Roster_Competitors.query.filter_by(
                roster_id=X
            ).order_by(
                Roster_Competitors.judge_id,
                Roster_Competitors.user_id
            ).all()
        
        Group by judge:
            competitors = Roster_Competitors.query.filter_by(
                roster_id=X
            ).all()
            by_judge = {}
            for comp in competitors:
                by_judge.setdefault(comp.judge_id, []).append(comp)
    
    Roster Display:
        Typical format:
            Judge: John Doe (3 people)
            - Competitor A
            - Competitor B
            - Competitor C
            
            Judge: Jane Smith (2 people)
            - Competitor D
            - Competitor E
    
    Validation:
        - Competitor must be signed up (Tournament_Signups)
        - Judge must exist in Roster_Judge for same roster
        - Event must match throughout
        - No duplicate competitors in same roster
    
    Note:
        Backref names use "competitors" suffix to distinguish from
        Roster_Judge (which also links users and judges).
    """
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', foreign_keys=[user_id], backref='roster_judge_user_competitors')

    event_id = db.Column(db.Integer, db.ForeignKey('event.id'))
    event = db.relationship('Event', foreign_keys=[event_id], backref='roster_judge_event_competitors')
    
    judge_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    judge = db.relationship('User', foreign_keys=[judge_id], backref='roster_judge_judge_competitors')

    roster_id = db.Column(db.Integer, db.ForeignKey('roster.id'))
    roster = db.relationship('Roster', foreign_keys=[roster_id], backref='roster_judge_roster_competitors')

class Roster_Partners(db.Model):
    """Partner pairings in rosters for partner events.
    
    Tracks which users are partnered together in a specific roster.
    Parallel to Tournament_Partners but roster-specific (allows different
    pairings in different rosters if needed).
    
    Purpose:
        - Record partner pairings in roster
        - Display partners together on roster
        - Ensure both partners included
        - Enable partner-aware roster generation
        - Support roster editing (change partners)
    
    Relationship to Tournament_Partners:
        Tournament_Partners:
            - Declared partnerships for tournament signups
            - User intent (who they want to partner with)
            - Created during signup
        
        Roster_Partners:
            - Actual partnerships in generated roster
            - May differ from Tournament_Partners (admin override)
            - Created during roster generation
            - Editable before publication
    
    Bidirectional Relationship:
        partner1_user_id and partner2_user_id:
            - Arbitrary assignment (no primary partner)
            - Both users equal partners
            - Order doesn't affect functionality
        
        Queries must check both directions:
            WHERE partner1_user_id=X OR partner2_user_id=X
    
    Columns:
        id: Primary key
        partner1_user_id: First partner (foreign key to User)
        partner2_user_id: Second partner (foreign key to User)
        roster_id: Roster this pairing belongs to (foreign key to Roster)
    
    Relationships:
        partner1_user: First partner User object (backref: roster_partner1)
        partner2_user: Second partner User object (backref: roster_partner2)
        roster: Roster object (backref: roster_partners)
    
    Usage:
        Roster generation:
            1. Query Tournament_Partners for signups
            2. Create Roster_Partners mirroring partnerships
            3. Ensure both partners in Roster_Competitors
        
        Manual editing:
            1. Admin can change partners in draft roster
            2. Update Roster_Partners entries
            3. Validate both partners still in roster
        
        Display:
            partners = Roster_Partners.query.filter_by(
                roster_id=X
            ).all()
            for partnership in partners:
                print(f"{partnership.partner1_user.first_name} & "
                      f"{partnership.partner2_user.first_name}")
    
    Validation:
        - Both partners must be in Roster_Competitors for same roster
        - Event must be partner event (is_partner_event=True)
        - Each user can have max one partner per roster
        - Partners must match Tournament_Partners (unless admin override)
    
    Partner Event Roster:
        Typical display:
            Team 1: Alice & Bob (Judge: Parent1)
            Team 2: Charlie & Dana (Judge: Parent2)
            Team 3: Eve & Frank (Judge: Parent3)
    
    Queries:
        Find user's partner in roster:
            Roster_Partners.query.filter(
                (Roster_Partners.partner1_user_id == user_id) |
                (Roster_Partners.partner2_user_id == user_id),
                Roster_Partners.roster_id == roster_id
            ).first()
        
        All partnerships in roster:
            Roster_Partners.query.filter_by(
                roster_id=roster_id
            ).all()
    
    Note:
        Separate from Tournament_Partners to allow roster-specific
        overrides (admin may pair differently than signups).
    """
    id = db.Column(db.Integer, primary_key=True)

    partner1_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    partner1_user = db.relationship('User', foreign_keys=[partner1_user_id], backref='roster_partner1')

    partner2_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    partner2_user = db.relationship('User', foreign_keys=[partner2_user_id], backref='roster_partner2')
    
    roster_id = db.Column(db.Integer, db.ForeignKey('roster.id', ondelete='CASCADE'), nullable=False)
    roster = db.relationship('Roster', foreign_keys=[roster_id], backref=db.backref('roster_partners', cascade='all, delete-orphan'))