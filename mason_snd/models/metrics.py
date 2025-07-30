from ..extensions import db

class MetricsSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    effort_weight = db.Column(db.Float, default=0.3)
    tournament_weight = db.Column(db.Float, default=0.7)
