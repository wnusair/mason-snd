from ..extensions import db
from datetime import datetime
import pytz

# Define EST timezone
EST = pytz.timezone('US/Eastern')

class Roster_Tournament(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Roster_Partner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    first_competitor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    second_competitor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Roster_Drops(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
