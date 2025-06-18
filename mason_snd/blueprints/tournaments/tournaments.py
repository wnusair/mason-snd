from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from mason_snd.extensions import db
from mason_snd.models.auth import User, Judges
from mason_snd.models.tournaments import Tournament, Form_Responses, Form_Fields, Tournament_Signups

from werkzeug.security import generate_password_hash, check_password_hash

from datetime import datetime
import pytz

EST = pytz.timezone('US/Eastern')

tournaments_bp = Blueprint('tournaments', __name__, template_folder='templates')

@tournaments_bp.route('/')
def index():
    tournaments = Tournament.query.all()

    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()

    if not user_id:
        flash("Please Log in", "error")
        return redirect(url_for('auth.login'))

    for tournament in tournaments:
        print(tournament.name,tournament.date,tournament.address,tournament.signup_deadline,tournament.performance_deadline)

    return render_template('tournaments/index.html', tournaments=tournaments, user=user)

from datetime import datetime

@tournaments_bp.route('/add_tournament', methods=['POST', 'GET'])
def add_tournament():
    user_id = session.get('user_id')

    if not user_id:
        flash("Please Log in", "error")
        return redirect(url_for('auth.login'))
    
    if request.method == "POST":
        name = request.form.get("name")
        address = request.form.get("address")
        date_str = request.form.get("date")  # "YYYY-MM-DDTHH:MM"
        signup_deadline_str = request.form.get("signup_deadline")  # "YYYY-MM-DDTHH:MM"
        performance_deadline_str = request.form.get("performance_deadline")  # "YYYY-MM-DDTHH:MM"
        created_at = datetime.now(EST)

        try:
            # Convert string inputs to datetime objects
            date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M")  # Now parses datetime
            signup_deadline = datetime.strptime(signup_deadline_str, "%Y-%m-%dT%H:%M")
            performance_deadline = datetime.strptime(performance_deadline_str, "%Y-%m-%dT%H:%M")
        except ValueError:
            flash("Invalid date format. Please use the date pickers.", "error")
            return render_template("tournaments/add_tournament.html")

        new_tournament = Tournament(
            name=name,
            date=date,
            address=address,
            signup_deadline=signup_deadline,
            performance_deadline=performance_deadline,
            created_at=created_at
        )

        db.session.add(new_tournament)
        db.session.commit()

        users = User.query.all()
        current_tournament = Tournament.query.filter_by(name=name).first()

        for user in users:
            tournament_signup = Tournament_Signups(
                user_id = user.id,
                tournament_id = current_tournament.id
            )

            db.session.add(tournament_signup)
            db.session.commit()


    return render_template("tournaments/add_tournament.html")

@tournaments_bp.route('/add_form', methods=['GET', 'POST'])
def add_form():
    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()
    if not user_id:
        flash("Please log in", "error")
        return redirect(url_for('auth.login'))

    tournaments = Tournament.query.all()

    if request.method == 'POST':
        tournament_id = request.form.get('tournament_id')

        # Get multiple field inputs
        labels = request.form.getlist('label')
        types = request.form.getlist('type')
        options_list = request.form.getlist('options')
        # Note: for checkboxes, if not checked the value is not submitted.
        required_vals = request.form.getlist('required')

        # Create a field entry for each input group
        for i in range(len(labels)):
            label = labels[i]
            field_type = types[i]
            options = options_list[i] if options_list[i] != "" else None
            # Each field row has its own checkbox input. If checkbox exists, its value (e.g. "on") appears
            required = (str(required_vals[i]).lower() in ["on", "true", "1"]) if i < len(required_vals) else False

            new_field = Form_Fields(
                label=label,
                type=field_type,
                options=options,
                required=required,
                tournament_id=tournament_id
            )
            db.session.add(new_field)
        db.session.commit()
        flash("Form fields added successfully.", "success")
        return redirect(url_for('tournaments.index'))

    return render_template("tournaments/add_form.html", tournaments=tournaments)

@tournaments_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    tournaments = Tournament.query.all()

    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()

    now = datetime.now(EST)  # Get the current time in EST

    if not user_id:
        flash("Please Log in", "error")
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        tournament_id = request.form.get('tournament_id')
        tournament = Tournament.query.get(tournament_id)
        if not tournament:
            flash("Tournament not found.", "error")
            return redirect(url_for('tournaments.signup'))
        
        print("Tournament found")

        my_tournament_signup = Tournament_Signups.query.filter_by(user_id=user_id, tournament_id=tournament_id).first()
        bringing_judge = request.form.get('bringing_judge_yes')

        if bringing_judge:
            my_tournament_signup.bringing_judge = True
        
        my_tournament_signup.is_going = True

        # For each field in the selected tournament, capture the user's response
        for field in tournament.form_fields:
            field_name = f'field_{field.id}'
            response_value = request.form.get(field_name)
            new_response = Form_Responses(
                tournament_id=tournament.id,
                user_id=session.get('user_id'),
                field_id=field.id,
                response=response_value,
                submitted_at=datetime.now(EST)
            )
            db.session.add(new_response)
        db.session.commit()
        flash("Your responses have been submitted.", "success")
        return redirect(url_for('tournaments.index'))
    else:
        # if a tournament is selected via query string, show its form fields
        tournament_id = request.args.get('tournament_id')
        selected_tournament = Tournament.query.get(tournament_id) if tournament_id else None

        # Localize signup_deadline for all tournaments
        for tournament in tournaments:
            if tournament.signup_deadline:
                tournament.signup_deadline = EST.localize(tournament.signup_deadline)

        fields = selected_tournament.form_fields if selected_tournament else []


        return render_template(
            "tournaments/signup.html",
            tournaments=tournaments,
            selected_tournament=selected_tournament,
            fields=fields,
            now=now  # Pass the current time to the template
        )

@tournaments_bp.route('/delete_tournament/<int:tournament_id>', methods=['POST'])
def delete_tournament(tournament_id):
    tournaments = Tournament.query.all()

    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()

    now = datetime.now(EST)

    if not user_id:
        flash("Please Log in", "error")
        return redirect(url_for('auth.login'))

    tournament = Tournament.query.filter_by(id=tournament_id).first()

    db.session.delete(tournament)
    db.session.commit()

    return redirect(url_for('tournaments.index'))