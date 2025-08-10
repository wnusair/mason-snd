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
    from mason_snd.blueprints.tournaments.tournaments import tournaments_bp
    from mason_snd.blueprints.metrics.metrics import metrics_bp
    from mason_snd.blueprints.admin.admin import admin_bp
    from mason_snd.blueprints.rosters.rosters import rosters_bp
    from mason_snd.blueprints.main.main import main_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(profile_bp, url_prefix='/profile')
    app.register_blueprint(events_bp, url_prefix='/events')
    app.register_blueprint(tournaments_bp, url_prefix='/tournaments')
    app.register_blueprint(metrics_bp, url_prefix='/metrics')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(rosters_bp, url_prefix='/rosters')
    app.register_blueprint(main_bp, url_prefix='/')

    with app.app_context():
        db.create_all()

    return app
