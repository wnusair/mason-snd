import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase
import logging


class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

# create the app
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get('DATABASE_URL')  # Use the Postgres database URL
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))

# initialize the app with the extensions
db.init_app(app)
login_manager.init_app(app)

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

with app.app_context():
    try:
        db.create_all()
        logger.info("Database tables created successfully.")
    except Exception as e:
        logger.error(f"An error occurred while creating database tables: {str(e)}")
        raise

# Log the database URL for debugging (without exposing sensitive information)
logger.info(f"Using database: {app.config['SQLALCHEMY_DATABASE_URI']}")