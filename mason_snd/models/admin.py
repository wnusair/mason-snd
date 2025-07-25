from ..extensions import db

from datetime import datetime
import pytz

# Define EST timezone
EST = pytz.timezone('US/Eastern')


class User_Requirements(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    complete = db.Column(db.Boolean, default=False)
    deadline = db.Column(db.DateTime, default=datetime.now(EST), nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    requirement_id = db.Column(db.Integer, db.ForeignKey('requirement.id'))
    
    requirement = db.relationship('Requirements', foreign_keys=[requirement_id], backref='requirement')
    user = db.relationship('User', foreign_keys=[user_id], backref='user')

class Requirements(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    body = db.Column(db.String)


