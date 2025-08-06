from flask import Blueprint, render_template, request, redirect, url_for, flash, session, Response
import csv
from io import StringIO

from mason_snd.extensions import db
from mason_snd.models.events import Event, User_Event, Effort_Score
from mason_snd.models.auth import User
from mason_snd.models.metrics import MetricsSettings

from werkzeug.security import generate_password_hash, check_password_hash

main_bp = Blueprint('main', __name__, template_folder='templates')

@main_bp.route('/')
def index():
    user_id = session.get('user_id')

    return render_template('main/index.html', user_id=user_id)
