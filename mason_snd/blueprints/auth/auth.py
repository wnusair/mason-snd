from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from mason_snd.extensions import db
from mason_snd.models.auth import User, Judges
from mason_snd.models.admin import User_Requirements, Requirements
from mason_snd.models.events import User_Event
from mason_snd.models.tournaments import Tournament_Judges, Tournaments_Attended, Tournament, Tournament_Performance

from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import pytz

auth_bp = Blueprint('auth', __name__, template_folder='templates')

def make_all_requirements():
    requirements_body = [
        "Submit Final Forms",
        "Pay Membership Fee on PaySchools",
        "Submit Tournament Performance",
        "Join an Event",
        "Sign the Permission slip for GMV tournaments",
        "Pay your Tournament Fees",
        "complete background check",
        "Respond to Judging Request by Child",
        "Complete your judge training"
    ]

    existing_reqs = {req.body for req in Requirements.query.all()}
    for requirement in requirements_body:
        if requirement not in existing_reqs:
            new_req = Requirements(body=requirement)
            db.session.add(new_req)
            db.session.commit()
    print("Requirements checked and created if missing")

def make_user_requirement(user_id, requirement_id, deadline):
    user_requirement = User_Requirements(deadline=deadline, user_id=user_id, requirement_id=requirement_id)

    db.session.add(user_requirement)
    db.session.commit()

def get_requirements(user):
    requirements_body = [
        "Submit Final Forms",
        "Pay Membership Fee on PaySchools",
        "Submit Tournament Performance",
        "Join an Event",
        "Sign the Permission slip for GMV tournaments",
        "Pay your Tournament Fees",
        "complete background check",
        "Respond to Judging Request by Child",
        "Complete your judge training"
    ]
    existing_reqs = {req.body for req in Requirements.query.all()}
    missing_reqs = [req for req in requirements_body if req not in existing_reqs]
    if missing_reqs:
        make_all_requirements()
    
    if user.is_parent:
        make_judge_reqs(user)
    else:
        make_child_reqs(user)

    
def make_child_reqs(user):
    eastern = pytz.timezone('US/Eastern')
    now = datetime.datetime.now(eastern)
    
    # Standard requirements that always apply
    standard_requirement_deadlines = {
        "1": now + datetime.timedelta(days=7),  # Submit Final Forms
        "2": now + datetime.timedelta(days=7),  # Pay Membership Fee on PaySchools
        "5": now + datetime.timedelta(days=7),  # Sign the Permission slip for GMV tournaments
        "6": now + datetime.timedelta(days=7)   # Pay your Tournament Fees
    }
    
    # Add standard requirements
    for requirement_id, deadline in standard_requirement_deadlines.items():
        req = User_Requirements.query.filter_by(user_id=user.id, requirement_id=requirement_id).first()
        if req is None:
            make_user_requirement(user.id, requirement_id, deadline)
    
    # Check if user attended tournaments but hasn't submitted performance
    attended_tournaments = Tournaments_Attended.query.filter_by(user_id=user.id).all()
    needs_performance_submission = False
    
    for tournament_attendance in attended_tournaments:
        performance_submitted = Tournament_Performance.query.filter_by(
            user_id=user.id, 
            tournament_id=tournament_attendance.tournament_id
        ).first()
        if performance_submitted is None:
            needs_performance_submission = True
            break
    
    # Only add tournament performance requirement if they have unsubmitted performances
    if needs_performance_submission:
        req = User_Requirements.query.filter_by(user_id=user.id, requirement_id=3).first()
        if req is None:
            make_user_requirement(user.id, 3, now + datetime.timedelta(days=7))
    
    # Check if user is not in an event
    user_in_event = User_Event.query.filter_by(user_id=user.id).first()
    if user_in_event is None:
        req = User_Requirements.query.filter_by(user_id=user.id, requirement_id=4).first()
        if req is None:
            make_user_requirement(user.id, 4, now + datetime.timedelta(days=7))

def make_judge_reqs(user):
    eastern = pytz.timezone('US/Eastern')
    now = datetime.datetime.now(eastern)
    
    # Standard judge requirements that always apply
    standard_requirement_deadlines = {
        "7": now + datetime.timedelta(days=7),  # complete background check
        "9": now + datetime.timedelta(days=7)   # Complete your judge training
    }
    
    # Add standard requirements
    for requirement_id, deadline in standard_requirement_deadlines.items():
        req = User_Requirements.query.filter_by(user_id=user.id, requirement_id=requirement_id).first()
        if req is None:
            make_user_requirement(user.id, requirement_id, deadline)
    
    # Check if their child has requested them to judge (pending requests)
    tournament_judge_requests = Tournament_Judges.query.filter_by(judge_id=user.id, accepted=False).all()
    
    # Only add the judging request requirement if there are pending requests
    if tournament_judge_requests:
        req = User_Requirements.query.filter_by(user_id=user.id, requirement_id=8).first()
        if req is None:
            make_user_requirement(user.id, 8, now + datetime.timedelta(days=7))

def req_checks(user):

    # child
    if user.is_parent == False:
        # Check if performance submitted for attended tournaments
        attended_tournaments = Tournaments_Attended.query.filter_by(user_id=user.id).all()
        print(f"Attended tournaments: {attended_tournaments}")

        print("Checking if submitted performance")
        has_unsubmitted_performance = False
        
        for tournament_attendance in attended_tournaments:
            performance_submitted = Tournament_Performance.query.filter_by(
                user_id=user.id, 
                tournament_id=tournament_attendance.tournament_id
            ).first()
            
            if performance_submitted is None:
                has_unsubmitted_performance = True
                break

        # Update or remove tournament performance requirement based on status
        performance_req = User_Requirements.query.filter_by(user_id=user.id, requirement_id=3).first()
        if has_unsubmitted_performance:
            if performance_req:
                performance_req.complete = False
                print("Performance needed to be submitted")
            # If requirement doesn't exist, it will be created by make_child_reqs
        else:
            if performance_req:
                # Remove the requirement if all performances are submitted
                db.session.delete(performance_req)
                print("All performances submitted - requirement removed")

        # Check if the user is in an event
        user_in_event = User_Event.query.filter_by(user_id=user.id).first()
        event_req = User_Requirements.query.filter_by(user_id=user.id, requirement_id=4).first()
        
        if user_in_event is not None:
            if event_req:
                # Remove the requirement if user is in an event
                db.session.delete(event_req)
                print("User is in event - requirement removed")
        else:
            if event_req:
                event_req.complete = False
                print("User not in event - requirement remains")
            # If requirement doesn't exist, it will be created by make_child_reqs

    # judge/parent
    if user.is_parent:
        # Check for pending judging requests
        tournament_judge_requests = Tournament_Judges.query.filter_by(judge_id=user.id, accepted=False).all()
        judge_req = User_Requirements.query.filter_by(user_id=user.id, requirement_id=8).first()

        if tournament_judge_requests:
            if judge_req:
                judge_req.complete = False
                print("Pending judging requests - requirement active")
            # If requirement doesn't exist, it will be created by make_judge_reqs
        else:
            if judge_req:
                # Remove the requirement if no pending requests
                db.session.delete(judge_req)
                print("No pending judging requests - requirement removed")

    db.session.commit()
    


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role'] = user.role
            get_requirements(user)
            req_checks(user)
            # Re-check and add requirements after status updates
            if user.is_parent:
                make_judge_reqs(user)
            else:
                make_child_reqs(user)
            flash("Logged in successfully!")
            return redirect(url_for('profile.index', user_id=user.id))
        else:
            flash("Invalid email or password")

    return render_template('auth/login.html')

"""
ghost_account = User(
                first_name=child_first_name,
                last_name=child_last_name,

                is_parent=False,

                account_claimed=False
            )
"""

def find_or_create_user(first_name, last_name, is_parent, **user_data):
    """
    Find existing user or create new one, handling account claiming properly.
    Returns the user object.
    """
    # Look for existing user with same name and parent status
    existing_user = User.query.filter_by(
        first_name=first_name.lower(), 
        last_name=last_name.lower(),
        is_parent=is_parent
    ).first()
    
    if existing_user:
        # If user exists but account not claimed, claim it with new data
        if not existing_user.account_claimed:
            for key, value in user_data.items():
                if value is not None:  # Only update non-None values
                    setattr(existing_user, key, value)
            existing_user.account_claimed = True
            db.session.commit()
            print(f"Claimed existing ghost account for {first_name} {last_name}")
        else:
            # Account is already claimed, but update any missing critical information
            updated_fields = []
            critical_fields = ['email', 'phone_number', 'password']  # Fields that should be updated if missing
            
            for key, value in user_data.items():
                if key in critical_fields and value is not None:
                    current_value = getattr(existing_user, key)
                    if current_value is None or current_value == '':
                        setattr(existing_user, key, value)
                        updated_fields.append(key)
            
            if updated_fields:
                db.session.commit()
                print(f"Updated existing claimed account for {first_name} {last_name} with fields: {updated_fields}")
            else:
                print(f"User {first_name} {last_name} already has a claimed account with complete information")
        return existing_user
    else:
        # Create new user
        new_user = User(
            first_name=first_name.lower(),
            last_name=last_name.lower(),
            is_parent=is_parent,
            account_claimed=True,
            **user_data
        )
        db.session.add(new_user)
        db.session.commit()
        print(f"Created new user for {first_name} {last_name}")
        return new_user

def create_or_update_judge_relationship(judge_id, child_id):
    """
    Create judge relationship if it doesn't exist, avoiding duplicates.
    """
    existing_relationship = Judges.query.filter_by(
        judge_id=judge_id,
        child_id=child_id
    ).first()
    
    if not existing_relationship:
        judge_relationship = Judges(
            judge_id=judge_id,
            child_id=child_id
        )
        db.session.add(judge_relationship)
        db.session.commit()
        print(f"Created judge relationship: judge_id={judge_id}, child_id={child_id}")
    else:
        print(f"Judge relationship already exists: judge_id={judge_id}, child_id={child_id}")

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        phone_number = request.form.get('phone_number')
        is_parent_form_value = request.form.get('is_parent')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Validate basic required fields
        if not all([first_name, last_name, email, phone_number, password, confirm_password]):
            flash("All basic information fields are required.", 'error')
            return render_template('auth/register.html')

        # Validate that is_parent is actually selected
        if is_parent_form_value not in ['yes', 'no']:
            flash("Please select whether you are a parent or not.", 'error')
            return render_template('auth/register.html')

        is_parent = is_parent_form_value == 'yes'

        emergency_first_name = emergency_last_name = emergency_email = emergency_phone = emergency_relationship = None
        child_first_name = child_last_name = None

        if is_parent:
            child_first_name = request.form.get('child_first_name')
            child_last_name = request.form.get('child_last_name')
            
            # Validate required child information
            if not child_first_name or not child_last_name:
                flash("Child's first name and last name are required when registering as a parent.", 'error')
                return render_template('auth/register.html')
        else:
            emergency_first_name = request.form.get('emergency_first_name')
            emergency_last_name = request.form.get('emergency_last_name')
            emergency_email = request.form.get('emergency_email')
            emergency_phone = request.form.get('emergency_phone')
            emergency_relationship = request.form.get('emergency_relationship')
            
            # Validate required emergency contact information
            if not all([emergency_first_name, emergency_last_name, emergency_email, emergency_phone, emergency_relationship]):
                flash("All emergency contact information is required when registering as a student.", 'error')
                return render_template('auth/register.html')
        
        print(first_name, last_name, email, phone_number, is_parent, password, confirm_password, emergency_first_name, emergency_last_name, emergency_email, emergency_phone, emergency_relationship, child_first_name, child_last_name)

        if password != confirm_password:
            flash("Passwords do not match", 'error')
            return render_template('auth/register.html')

        # Check if someone is trying to register with an email that already exists
        # But allow claiming of ghost accounts (unclaimed accounts with same name)
        existing_email_user = User.query.filter_by(email=email).first()
        if existing_email_user and existing_email_user.account_claimed:
            # Check if this is the same person trying to claim their ghost account
            is_same_person = (
                existing_email_user.first_name.lower() == first_name.lower() and
                existing_email_user.last_name.lower() == last_name.lower() and
                existing_email_user.is_parent == is_parent
            )
            
            if not is_same_person:
                flash("An account with this email address already exists. Please use a different email or try logging in.", 'error')
                return render_template('auth/register.html')

        if is_parent:
            # Handle parent registration
            parent_user_data = {
                'email': email,
                'password': generate_password_hash(password),
                'phone_number': phone_number,
                'judging_reqs': "test",
                'child_first_name': child_first_name.lower() if child_first_name else None,
                'child_last_name': child_last_name.lower() if child_last_name else None
            }
            
            # Find or create parent user
            parent_user = find_or_create_user(first_name, last_name, True, **parent_user_data)
            
            # Find or create child user (as ghost account if not exists)
            child_user_data = {}  # Child gets minimal data initially
            child_user = find_or_create_user(child_first_name, child_last_name, False, **child_user_data)
            
            # Create or update judge relationship
            create_or_update_judge_relationship(parent_user.id, child_user.id)
            make_judge_reqs(parent_user)
            
        else:
            # Handle child registration
            child_user_data = {
                'email': email,
                'password': generate_password_hash(password),
                'phone_number': phone_number,
                'emergency_contact_first_name': emergency_first_name.lower(),
                'emergency_contact_last_name': emergency_last_name.lower(),
                'emergency_contact_number': emergency_phone,
                'emergency_contact_relationship': emergency_relationship,
                'emergency_contact_email': emergency_email
            }
            
            # Find or create child user
            child_user = find_or_create_user(first_name, last_name, False, **child_user_data)
            
            # Find or create parent user (as ghost account if not exists)
            parent_user_data = {
                'phone_number': emergency_phone,
                'email': emergency_email,
                'child_first_name': first_name.lower(),
                'child_last_name': last_name.lower()
            }
            parent_user = find_or_create_user(emergency_first_name, emergency_last_name, True, **parent_user_data)
            
            # Create or update judge relationship
            create_or_update_judge_relationship(parent_user.id, child_user.id)
            make_child_reqs(child_user)

        flash("Registration successful!", "success")
        return redirect(url_for("auth.login"))

    return render_template('auth/register.html')
