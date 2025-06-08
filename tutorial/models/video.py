from ..extensions import db

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(80), nullable=False)

    def __init__(self, url):
        self.url = url