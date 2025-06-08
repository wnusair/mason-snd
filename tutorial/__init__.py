from flask import Flask
from flask_migrate import Migrate

from .extensions import db

def create_app():
    app = Flask(__name__)

    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    Migrate(app, db)

    from tutorial.blueprints.helloworld.helloworld import helloworld_bp
    from tutorial.blueprints.calculator.calculator import calculator_bp

    app.register_blueprint(helloworld_bp)
    app.register_blueprint(calculator_bp, url_prefix='/calculator')

    return app