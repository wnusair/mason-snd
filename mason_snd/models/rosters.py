from ..extensions import db
from datetime import datetime
import pytz

# Define EST timezone
EST = pytz.timezone('US/Eastern')

class Roster_Tournament(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    """
    
    tournmanet id
    user id
    

    """
    