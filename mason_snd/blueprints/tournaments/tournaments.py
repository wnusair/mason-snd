from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from mason_snd.extensions import db
from mason_snd.models.auth import User, Judges
from mason_snd.models.tournaments import Tournament

from werkzeug.security import generate_password_hash, check_password_hash

from datetime import datetime
import pytz

EST = pytz.timezone('US/Eastern')

tournaments_bp = Blueprint('tournaments', __name__, template_folder='templates')

@tournaments_bp.route('/')
def index():
    return render_template('tournaments/index.html')

@tournaments_bp.route('/add_tournament', methods=['POST', 'GET'])
def add_tournament():
    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()

    if not user_id:
        flash("Please Log in", "error")
        return redirect(url_for('auth.login'))
    
    if request.method == "POST":
        name = request.form.get("name")
        address = request.form.get("address")
        date = request.form.get("date")
        signup_deadline = request.form.get("signup_deadline")
        performance_deadline = request.form.get("performance_deadline")
        created_at = datetime.now(EST)

        new_tournament = Tournament(
            name = name,
            date = date,
            address = address,
            signup_deadline = signup_deadline,
            performance_deadline = performance_deadline,
            created_at = created_at
        )

        db.session.add(new_tournament)
        db.session.commit()

    return render_template("tournaments/add_tournament.html")