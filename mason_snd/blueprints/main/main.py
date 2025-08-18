from flask import Blueprint, render_template, request, redirect, url_for, flash, session, Response, send_from_directory
import csv
from io import StringIO
import os

from mason_snd.extensions import db
from mason_snd.models.events import Event, User_Event, Effort_Score
from mason_snd.models.auth import User
from mason_snd.models.metrics import MetricsSettings

from werkzeug.security import generate_password_hash, check_password_hash

main_bp = Blueprint('main', __name__, template_folder='templates')

@main_bp.route('/')
def index():
    user_id = session.get('user_id')

    if user_id is not None:
        return redirect(url_for('profile.index', user_id=user_id))

    return render_template('main/index.html', user_id=user_id)

@main_bp.route('life')
def life():
    return render_template('main/life.html')

@main_bp.route('/favicon.ico')
def favicon():
    """Serve the favicon from the images directory."""
    images_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'images')
    return send_from_directory(images_dir, 'icon.png', mimetype='image/png')