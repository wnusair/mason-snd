from ..extensions import db
from datetime import datetime
import pytz

# Define EST timezone
EST = pytz.timezone('US/Eastern')

class Tournament(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    date = db.Column(db.Date, nullable=False)
    address = db.Column(db.String(255), nullable=False)
    signup_deadline = db.Column(db.DateTime, nullable=False)
    performance_deadline = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(EST), nullable=False)

