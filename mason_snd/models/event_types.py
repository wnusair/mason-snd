from ..extensions import db

class Event_Type(db.Model):
    __tablename__ = 'event_type'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    judge_ratio = db.Column(db.Integer, nullable=False, default=1)
    color_class = db.Column(db.String(50), default='bg-gray-100 text-gray-800')
    created_at = db.Column(db.DateTime, default=db.func.now())
    
    def __repr__(self):
        return f'<Event_Type {self.name} (1:{self.judge_ratio})>'
