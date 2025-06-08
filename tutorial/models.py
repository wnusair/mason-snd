from .extensions import db

class User:
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))