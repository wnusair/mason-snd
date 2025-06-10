from ..extensions import db

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    event_name = db.Column(db.String)
    event_description = db.Column(db.String)

    event_emoji = db.Column(db.String)
    
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = db.relationship('User', foreign_keys=[owner_id], backref='ownver')

class User_Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    effort_score = db.Column(db.Integer)

    event_id = db.Column(db.Integer, db.ForeignKey('event.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    event = db.relationship('Event', foreign_keys=[event_id], backref='event')
    user = db.relationship('User', foreign_keys=[user_id], backref='user')