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
    requirement_id = db.Column(db.Integer, db.ForeignKey('requirements.id'))
    
    requirement = db.relationship('Requirements', foreign_keys=[requirement_id], backref='requirement')
    user = db.relationship('User', foreign_keys=[user_id], backref='user')

class Requirements(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String)
    active = db.Column(db.Boolean, default=True, nullable=False)

class Popups(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(EST), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)
    completed = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    user = db.relationship('User', foreign_keys=[user_id], backref='popups_received')
    admin = db.relationship('User', foreign_keys=[admin_id], backref='popups_sent')


