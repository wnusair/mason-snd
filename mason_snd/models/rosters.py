from ..extensions import db
from datetime import datetime
import pytz

# Define EST timezone
EST = pytz.timezone('US/Eastern')

class Roster(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String)
    
    published = db.Column(db.Boolean, default=False)
    published_at = db.Column(db.DateTime, nullable=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=True)
    tournament = db.relationship('Tournament', foreign_keys=[tournament_id], backref='rosters')

    date_made = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('US/Eastern')))

class Roster_Judge(db.Model):
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
    id = db.Column(db.Integer, primary_key=True)

    partner1_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    partner1_user = db.relationship('User', foreign_keys=[partner1_user_id], backref='roster_partner1')

    partner2_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    partner2_user = db.relationship('User', foreign_keys=[partner2_user_id], backref='roster_partner2')
    
    roster_id = db.Column(db.Integer, db.ForeignKey('roster.id'), nullable=False)
    roster = db.relationship('Roster', foreign_keys=[roster_id], backref='roster_partners')