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
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(EST), nullable=False)

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
    submitted_at = db.Column(db.DateTime, default=lambda: datetime.now(EST), nullable=False)

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
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'))

    user = db.relationship('User', foreign_keys=[user_id], backref='tournaments_attended')
    tournament = db.relationship('Tournament', foreign_keys=[tournament_id], backref='tournaments_attended')

class Tournament_Performance(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    points = db.Column(db.Integer)
    bid = db.Column(db.Boolean)
    rank = db.Column(db.Integer)
    stage = db.Column(db.Integer)
    # 0 = nothing, 1 = double octas, 2 = octas, 3 = quarters, 4 = semis, 5 = finals

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'))

    user = db.relationship('User', foreign_keys=[user_id], backref='tournament_performances')
    tournament = db.relationship('Tournament', foreign_keys=[tournament_id], backref='tournament_performances')

class Tournament_Judges(db.Model):
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
