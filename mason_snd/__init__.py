import os
from flask import Flask
from flask_migrate import Migrate
from dotenv import load_dotenv

from .extensions import db
from .models.auth import User, Judges

load_dotenv()  # This will load variables from .env into the environment

def create_app():
    app = Flask(__name__)

    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///db.sqlite3')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'default-secret')

    db.init_app(app)
    Migrate(app, db)

    from mason_snd.blueprints.auth.auth import auth_bp
    from mason_snd.blueprints.profile.profile import profile_bp
    from mason_snd.blueprints.events.events import events_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(profile_bp, url_prefix='/profile')
    app.register_blueprint(events_bp, url_prefix='/events')

    with app.app_context():
        db.create_all()

    return app
