from ..extensions import db
from datetime import datetime
import pytz

class User(db.Model):
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
    #tournaments_attended_name = db.relationship('tournaments', backref='attendee')

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

    account_claimed = db.Column(db.Boolean, default=False)

class User_Published_Rosters(db.Model):
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
    """Tracks penalty entries that should show in published rosters as '+1' instead of user names"""
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
    id = db.Column(db.Integer, primary_key=True)
    background_check = db.Column(db.Boolean, default=False)

    judge_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    child_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    judge = db.relationship('User', foreign_keys=[judge_id], backref='judge')
    child = db.relationship('User', foreign_keys=[child_id], backref='child')