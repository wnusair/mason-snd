from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    is_participant = db.Column(db.Boolean, default=False)
    events = db.relationship('Event', secondary='event_participants', back_populates='participants')
    tournaments = db.relationship('Tournament', secondary='tournament_participants', back_populates='participants')
    statistics = db.relationship('Statistics', back_populates='user')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        return True

    def get_id(self):
        return str(self.id)

    @property
    def is_authenticated(self):
        return True

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    participants = db.relationship('User', secondary='event_participants', back_populates='events')
    statistics = db.relationship('Statistics', back_populates='event')

class Tournament(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    location = db.Column(db.String(100))
    status = db.Column(db.String(20), default='ongoing')
    participants = db.relationship('User', secondary='tournament_participants', back_populates='tournaments')
    statistics = db.relationship('Statistics', back_populates='tournament')

class Statistics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=True)
    score = db.Column(db.Float, nullable=False)
    notes = db.Column(db.Text)
    date = db.Column(db.DateTime, default=db.func.current_timestamp())
    rank = db.Column(db.Integer)
    group = db.Column(db.String(20))

    user = db.relationship('User', back_populates='statistics')
    event = db.relationship('Event', back_populates='statistics')
    tournament = db.relationship('Tournament', back_populates='statistics')

event_participants = db.Table('event_participants',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('event_id', db.Integer, db.ForeignKey('event.id'), primary_key=True)
)

tournament_participants = db.Table('tournament_participants',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('tournament_id', db.Integer, db.ForeignKey('tournament.id'), primary_key=True)
)
