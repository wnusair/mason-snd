from ..extensions import db

from datetime import datetime

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    orders = db.relationship('order', backref='customer')

    def __init__(self, name):
        self.name = name

order_product = db.Table('order_product',
    db.Column('order_id', db.Integer, db.ForeignKey('order.id'), primary_key=True),
    db.Column('product_id', db.Integer, db.ForeignKey('product.id'), primary_key=True)
)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_date = db.Column(db.DateTime, nullable=False, default=datetime.now())
    shiped_date = db.Column(db.DateTime)
    delivered_date = db.Column(db.DateTime)
    cupon_code = db.Column(db.String(50))
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    products = db.relationship('Product', secondary=order_product)

    def __init__(self, order_date, shiped_date, delivered_date, cupon_code, customer_id):
        self.order_date = order_date
        self.shiped_date = shiped_date
        self.delivered_date = delivered_date
        self.cupon_code = cupon_code
        self.customer_id = customer_id

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    price = db.Column(db.Float, nullable=False)

    def __init__(self, name, price):
        self.name = name
        self.price = price