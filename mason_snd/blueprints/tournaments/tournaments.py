from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from mason_snd.extensions import db
from mason_snd.models.auth import User, Judges
from mason_snd.models.tournaments import Tournament, Tournament_Performance, Tournaments_Attended, Form_Responses, Form_Fields, Tournament_Signups, Tournament_Judges
from mason_snd.models.events import User_Event, Event

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
    
    user = User.query.filter_by(id=user_id).first()
    if not user or user.role < 2:
        flash("You are not authorized to access this page", "error")
        return redirect(url_for('tournaments.index'))
    
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
        events = Event.query.all()
        for user in users:
            for event in events:
                tournament_signup = Tournament_Signups(
                    user_id = user.id,
                    tournament_id = current_tournament.id,
                    event_id = event.id
                )
                db.session.add(tournament_signup)
        db.session.commit()


    return render_template("tournaments/add_tournament.html")

@tournaments_bp.route('/add_form', methods=['GET', 'POST'])
def add_form():
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in", "error")
        return redirect(url_for('auth.login'))
        
    user = User.query.filter_by(id=user_id).first()
    if not user or user.role < 2:
        flash("You are not authorized to access this page", "error")
        return redirect(url_for('tournaments.index'))

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

    # Get all events the user is signed up for
    user_events = Event.query.join(User_Event, Event.id == User_Event.event_id).filter(User_Event.user_id == user_id).all()

    if request.method == 'POST':
        tournament_id = request.form.get('tournament_id')
        tournament = Tournament.query.get(tournament_id)
        if not tournament:
            flash("Tournament not found.", "error")
            return redirect(url_for('tournaments.signup'))

        # Prevent signup if there are no form fields (no signup form)
        if not tournament.form_fields or len(tournament.form_fields) == 0:
            flash("Signup is not available for this tournament.", "error")
            return redirect(url_for('tournaments.signup'))

        print("Tournament found")

        bringing_judge = False

        # Get selected events from form
        selected_event_ids = request.form.getlist('user_event')

        # Create or update Tournament_Signups for each selected event
        for event_id in selected_event_ids:
            signup = Tournament_Signups.query.filter_by(user_id=user_id, tournament_id=tournament_id, event_id=event_id).first()
            
            # Get partner ID for this event if it's a partner event
            partner_id = request.form.get(f'partner_{event_id}')
            if partner_id:
                try:
                    partner_id = int(partner_id)
                except (ValueError, TypeError):
                    partner_id = None
            else:
                partner_id = None
            
            if not signup:
                signup = Tournament_Signups(
                    user_id=user_id,
                    tournament_id=tournament_id,
                    event_id=event_id,
                    is_going=True,
                    partner_id=partner_id
                )
                db.session.add(signup)
            else:
                signup.is_going = True
                signup.partner_id = partner_id
            
            # If this is a partner event and a partner was selected, create/update the partner's signup too
            if partner_id:
                partner_signup = Tournament_Signups.query.filter_by(user_id=partner_id, tournament_id=tournament_id, event_id=event_id).first()
                if not partner_signup:
                    partner_signup = Tournament_Signups(
                        user_id=partner_id,
                        tournament_id=tournament_id,
                        event_id=event_id,
                        is_going=True,
                        partner_id=user_id
                    )
                    db.session.add(partner_signup)
                else:
                    partner_signup.partner_id = user_id
                    if not partner_signup.is_going:
                        partner_signup.is_going = True

        # For each field in the selected tournament, capture the user's response
        for field in tournament.form_fields:
            field_name = f'field_{field.id}'
            response_value = request.form.get(field_name)
            # Check for the "Are you bringing a judge?" question
            if field.label.strip().lower() == "are you bringing a judge?":
                if response_value and response_value.lower() in ["yes", "true", "on", "1"]:
                    print("bringing judge")
                    bringing_judge = True
            new_response = Form_Responses(
                tournament_id=tournament.id,
                user_id=user_id,
                field_id=field.id,
                response=response_value,
                submitted_at=datetime.now(EST)
            )
            db.session.add(new_response)

        # Add Tournament_Judges rows for selected events only
        for event_id in selected_event_ids:
            # Check if Tournament_Judges entry already exists for this child/tournament/event combination
            existing_judge = Tournament_Judges.query.filter_by(
                child_id=user_id,
                tournament_id=tournament_id,
                event_id=event_id
            ).first()
            
            if not existing_judge:
                judge_acceptance = Tournament_Judges(
                    accepted=False,
                    judge_id=None,
                    child_id=user_id,
                    tournament_id=tournament_id,
                    event_id=event_id
                )
                db.session.add(judge_acceptance)

        # Commit all changes (Tournament_Signups, Form_Responses, Tournament_Judges)
        db.session.commit()

        # Handle judge selection if needed
        if bringing_judge:
            return redirect(url_for('tournaments.bringing_judge', tournament_id=tournament_id))
        
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
            now=now,  # Pass the current time to the template
            user_events=user_events
        )

@tournaments_bp.route('/bringing_judge/<int:tournament_id>', methods=['POST', 'GET'])
def bringing_judge(tournament_id):
    user_id = session.get('user_id')

    if not user_id:
        flash("Log in first")
        return redirect(url_for('auth.login'))

    # Get all Judges entries where the current user is the child
    judges = Judges.query.filter_by(child_id=user_id).all()

    # Build a list of tuples: (judge_id, judge_name)
    judge_options = []
    for judge in judges:
        judge_user = User.query.filter_by(id=judge.judge_id).first()
        if judge_user:
            judge_options.append((judge.judge_id, f"{judge_user.first_name} {judge_user.last_name}"))

    selected_judge_id = None


    if request.method == "POST":
        selected_judge_id = request.form.get("judge_id")

        user_tournament_signup = Tournament_Signups.query.filter_by(user_id=user_id, tournament_id=tournament_id).first()

        if user_tournament_signup:
            user_tournament_signup.bringing_judge = True
            user_tournament_signup.judge_id = selected_judge_id

            # Only add Tournament_Judges rows for events the user actually signed up for in this tournament
            # Find events from Tournament_Judges where child_id=user_id and tournament_id=tournament_id and judge_id is None
            judge_rows = Tournament_Judges.query.filter_by(child_id=user_id, tournament_id=tournament_id, judge_id=None).all()
            for judge_row in judge_rows:
                judge_row.judge_id = selected_judge_id
            db.session.commit()

            flash("Judge selection saved.", "success")
            return redirect(url_for('tournaments.index'))

    return render_template(
        'tournaments/bringing_judge.html',
        judge_options=judge_options,
        selected_judge_id=selected_judge_id
    )

@tournaments_bp.route('/delete_tournament/<int:tournament_id>', methods=['POST'])
def delete_tournament(tournament_id):
    user_id = session.get('user_id')
    if not user_id:
        flash("Please Log in", "error")
        return redirect(url_for('auth.login'))
        
    user = User.query.filter_by(id=user_id).first()
    if not user or user.role < 2:
        flash("You are not authorized to access this page", "error")
        return redirect(url_for('tournaments.index'))

    tournament = Tournament.query.filter_by(id=tournament_id).first()

    db.session.delete(tournament)
    db.session.commit()

    return redirect(url_for('tournaments.index'))

@tournaments_bp.route('/judge_requests', methods=['POST', 'GET'])
def judge_requests():
    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()

    if not user_id:
        flash("Must Be Logged In")
        return redirect(url_for('auth.login'))

    if not user.is_parent:
        flash("Must be a parent")
        return redirect(url_for('main.index'))

    judge_requests = Tournament_Judges.query.filter_by(judge_id=user_id).all()

    # Prepare data for template
    judge_requests_data = []
    for req in judge_requests:
        tournament = Tournament.query.get(req.tournament_id)
        child = User.query.get(req.child_id)
        judge_requests_data.append({
            'id': req.id,
            'tournament_name': tournament.name if tournament else '',
            'address': tournament.address if tournament else '',
            'date': tournament.date if tournament else None,
            'child_name': f"{child.first_name} {child.last_name}" if child else '',
            'accepted': req.accepted,
        })

    if request.method == 'POST':
        for req in judge_requests:
            decision = request.form.get(f"decision_{req.id}")
            req.accepted = True if decision == 'yes' else False
        db.session.commit()
        flash("Decisions updated.", "success")
        return redirect(url_for('tournaments.judge_requests'))

    return render_template('tournaments/judge_requests.html', user=user, judge_requests=judge_requests_data)


@tournaments_bp.route('/my_tournaments')
def my_tournaments():
    user_id = session.get('user_id')

    if not user_id:
        flash("Must Be Logged In")
        return redirect(url_for('auth.login'))

    tournaments = Tournament.query.all()

    # Localize performance_deadline for all tournaments
    for tournament in tournaments:
        if tournament.performance_deadline and tournament.performance_deadline.tzinfo is None:
            tournament.performance_deadline = EST.localize(tournament.performance_deadline)

    now = datetime.now(EST)

    return render_template('tournaments/my_tournaments.html', tournaments=tournaments, now=now)

@tournaments_bp.route('/tournament_results/<int:tournament_id>', methods=['GET', 'POST'])
def tournament_results(tournament_id):
    user_id = session.get('user_id')
    if not user_id:
        flash("Must Be Logged In")
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        # Check if results already submitted
        existing_results = Tournament_Performance.query.filter_by(
            user_id=user_id,
            tournament_id=tournament_id
        ).first()

        if existing_results:
            flash("You have already submitted results for this tournament")
            return redirect(url_for('tournaments.my_tournaments'))

        # Get form data
        bid_str = request.form.get('bid')  # 'yes' or 'no'
        rank_str = request.form.get('rank')
        stage_str = request.form.get('stage')

        # Convert bid to boolean
        bid = True if bid_str == 'yes' else False

        # Convert rank to int safely
        try:
            rank = int(rank_str)
        except (ValueError, TypeError):
            flash("Invalid rank submitted")
            return redirect(request.url)

        # Convert stage to numeric value
        stage_map = {
            "None": 0,
            "Double Octafinals": 1,
            "Octafinals": 2,
            "Quarter Finals": 3,
            "Semifinals": 4,
            "Finals": 5
        }
        stage = stage_map.get(stage_str, 0)

        # Calculate points
        points = 0
        user = User.query.filter_by(id=user_id).first()

        user_bids = user.bids if user.bids is not None else 0

        if user_bids == 0 and bid:
            points += 15
        elif user_bids > 0 and bid:
            points += 5
        if stage != 0:
            points += (stage + 1)

        if rank in [10, 9, 8, 7]:
            points += 1
        elif rank in [6, 5, 4]:
            points += 2
        elif rank in [3, 2, 1]:
            points += 3

        points += 1  # General participation or submission point?

        # Save to DB
        tournament_performance = Tournament_Performance(
            points=points,
            bid=bid,
            rank=rank,
            stage=stage,
            user_id=user_id,
            tournament_id=tournament_id
        )

        user.points += points
        
        db.session.add(tournament_performance)
        db.session.commit()


        return redirect(url_for('profile.index', user_id=user_id))

    return render_template("tournaments/tournament_results.html")

@tournaments_bp.route('/search_partners')
def search_partners():
    from flask import jsonify
    
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    query = request.args.get('q', '').strip()
    event_id = request.args.get('event_id')
    
    if not query or len(query) < 2:
        return jsonify({'users': []})
    
    # Search for users by name, excluding current user
    users = User.query.filter(
        db.or_(
            User.first_name.ilike(f'%{query}%'),
            User.last_name.ilike(f'%{query}%'),
            db.func.concat(User.first_name, ' ', User.last_name).ilike(f'%{query}%')
        ),
        User.id != user_id  # Exclude current user
    ).limit(10).all()
    
    # Filter users who are signed up for the same event
    if event_id:
        from mason_snd.models.events import User_Event
        event_users = User_Event.query.filter_by(event_id=event_id, active=True).all()
        event_user_ids = [eu.user_id for eu in event_users]
        users = [user for user in users if user.id in event_user_ids]
    
    return jsonify({
        'users': [
            {
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name
            }
            for user in users
        ]
    })
