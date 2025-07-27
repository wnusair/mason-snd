from ..extensions import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    
    email = db.Column(db.String(50), nullable=True)
    password = db.Column(db.String(500), nullable=True)
    phone_number = db.Column(db.String(50), nullable=True)

    is_parent = db.Column(db.Boolean, default=False)
    role = db.Column(db.Integer, default=0)
    # 0 = member, 1 = EL, 2 = chair+

    judging_reqs = db.Column(db.String(5000), nullable=True)

    emergency_contact_first_name = db.Column(db.String(50), nullable=True)
    emergency_contact_last_name = db.Column(db.String(50), nullable=True)
    emergency_contact_number = db.Column(db.String(50), nullable=True)
    emergency_contact_relationship = db.Column(db.String(50), nullable=True)
    emergency_contact_email = db.Column(db.String(50), nullable=True)

    child_first_name = db.Column(db.String(50), nullable=True)
    child_last_name = db.Column(db.String(50), nullable=True)

    points = db.Column(db.Integer, default=0)
    drops = db.Column(db.Integer, default=0)
    bids = db.Column(db.Integer, default=0)

    tournaments_attended_number = db.Column(db.Integer, default=0)
    #tournaments_attended_name = db.relationship('tournaments', backref='attendee')

    @property
    def tournament_points(self):
        from mason_snd.models.tournaments import Tournament_Performance
        performances = Tournament_Performance.query.filter_by(user_id=self.id).all()
        return sum([p.points or 0 for p in performances])

    @property
    def effort_points(self):
        from mason_snd.models.events import Effort_Score
        scores = Effort_Score.query.filter_by(user_id=self.id).all()
        return sum([s.score or 0 for s in scores])

    account_claimed = db.Column(db.Boolean, default=False)

class Judges(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    background_check = db.Column(db.Boolean, default=False)

    judge_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    child_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    judge = db.relationship('User', foreign_keys=[judge_id], backref='judge')
    child = db.relationship('User', foreign_keys=[child_id], backref='child')