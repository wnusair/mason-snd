from flask import Flask
from flask_migrate import Migrate

from .extensions import db
from .models.auth import User, Judges

def create_app():
    app = Flask(__name__)

    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    app.config['SECRET_KEY'] = 'GYATTTTTTsigmasigmasigma'

    db.init_app(app)
    Migrate(app, db)

    from mason_snd.blueprints.auth.auth import auth_bp
    from mason_snd.blueprints.profile.profile import profile_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(profile_bp, url_prefix='/profile')

    with app.app_context():
        db.create_all()

    return app