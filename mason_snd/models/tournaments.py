from ..extensions import db
from datetime import datetime
import pytz

# Define EST timezone
EST = pytz.timezone('US/Eastern')

class Tournament(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    address = db.Column(db.String(255), nullable=False)
    signup_deadline = db.Column(db.DateTime, nullable=False)
    performance_deadline = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(EST), nullable=False)

class Form_Fields(db.Model):
    __tablename__ = 'form_fields'
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.Text, nullable=False)
    type = db.Column(db.Text, nullable=False)
    options = db.Column(db.Text, nullable=True)
    required = db.Column(db.Boolean, nullable=False, default=False)
    
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    tournament = db.relationship('Tournament', foreign_keys=[tournament_id], backref='form_fields')

class Form_Responses(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    response = db.Column(db.Text, nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.now(EST), nullable=False)

    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    field_id = db.Column(db.Integer, db.ForeignKey('form_fields.id'), nullable=False)


    tournament = db.relationship('Tournament', foreign_keys=[tournament_id], backref='form_responses')
    field = db.relationship('Form_Fields', foreign_keys=[field_id], backref='responses')
    user = db.relationship('User', foreign_keys=[user_id], backref='form_responses')

class Tournament_Signups(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    bringing_judge = db.Column(db.Boolean, default=False)
    is_going = db.Column(db.Boolean, default=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'))

    user = db.relationship('User', foreign_keys=[user_id], backref='tournament_signups')
    tournament = db.relationship('Tournament', foreign_keys=[tournament_id], backref='tournament_signups')