from ..extensions import db

from datetime import datetime
import pytz

class Event(db.Model):
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
    id = db.Column(db.Integer, primary_key=True)
    
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    event = db.relationship('Event', back_populates='leaders')
    user = db.relationship('User', foreign_keys=[user_id], backref='event_leaderships')

class User_Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    effort_score = db.Column(db.Integer, nullable=True, default=0)

    active = db.Column(db.Boolean, default=False)

    event_id = db.Column(db.Integer, db.ForeignKey('event.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    event = db.relationship('Event', foreign_keys=[event_id], backref='user_event')
    user = db.relationship('User', foreign_keys=[user_id], backref='user_event')

class Effort_Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    score = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('US/Eastern'))) # datetime eastern time

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', foreign_keys=[user_id], backref='effort_score_user')

    event_id = db.Column(db.Integer, db.ForeignKey('event.id'))
    event = db.relationship('Event', foreign_keys=[event_id], backref='effort_score')

    given_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    given_by = db.relationship('User', foreign_keys=[given_by_id], backref='effort_score_given_by')

