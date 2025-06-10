from ..extensions import db

class Popup(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    message = db.Column(db.String, nullable=False)

    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    admin = db.relationship('User', foreign_keys=[admin_id], backref='admin')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='recipient')