from ..extensions import db

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    event_name = db.Column(db.String)
    event_description = db.Column(db.String)

    event_emoji = db.Column(db.String)
    
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = db.relationship('User', foreign_keys=[owner_id], backref='owner')

class User_Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    effort_score = db.Column(db.Integer, nullable=True, default=0)

    event_id = db.Column(db.Integer, db.ForeignKey('event.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    event = db.relationship('Event', foreign_keys=[event_id], backref='event')
    user = db.relationship('User', foreign_keys=[user_id], backref='user')

class Effort_Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    score = db.Column(db.Integer)
    timestamp = db.Column() # datetime eastern time

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', foreign_keys=[user_id], backref='user')

    event_id = db.Column(db.Integer, db.ForeignKey('event.id'))
    event = db.relationship('Event', foreign_keys=[event_id], backref='event')

    given_by_id = db.Column(db.Integer, db.ForeignKey('given_by.id'))
    given_by = db.relationship('User', foreign_keys=[given_by_id], backref='given_by')

