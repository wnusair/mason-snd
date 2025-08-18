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

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        phone_number = request.form.get('phone_number')
        is_parent = request.form.get('is_parent') == 'yes'
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        emergency_first_name = emergency_last_name = emergency_email = emergency_phone = emergency_relationship = None
        child_first_name = child_last_name = None

        if is_parent:
            child_first_name = request.form.get('child_first_name')
            child_last_name = request.form.get('child_last_name')
        else:
            emergency_first_name = request.form.get('emergency_first_name')
            emergency_last_name = request.form.get('emergency_last_name')
            emergency_email = request.form.get('emergency_email')
            emergency_phone = request.form.get('emergency_phone')
            emergency_relationship = request.form.get('emergency_relationship')
        
        print(first_name, last_name, email, phone_number, is_parent, password, confirm_password, emergency_first_name, emergency_last_name, emergency_email, emergency_phone, emergency_relationship, child_first_name, child_last_name)

        if password != confirm_password:
            flash("Passwords do not match", 'error')
            return render_template('auth/register.html')

        if is_parent:
            new_user = User(
                first_name=first_name.lower(),
                last_name=last_name.lower(),
                email=email,
                password=generate_password_hash(password),
                phone_number=phone_number,
                judging_reqs="test",
                is_parent=is_parent,
                child_first_name=child_first_name,
                child_last_name=child_last_name,
                account_claimed=True
            )

            # Check if the child already exists (real or ghost)
            child_user = User.query.filter_by(
                first_name=child_first_name.lower() if child_first_name else None,
                last_name=child_last_name.lower() if child_last_name else None,
                is_parent=False
            ).first()

            existing_user = User.query.filter_by(first_name=first_name.lower(), last_name=last_name.lower()).first()
            print(existing_user)

            if existing_user:
                existing_user.email = email
                existing_user.password = generate_password_hash(password)
                existing_user.judging_reqs = "test"
                existing_user.child_first_name = child_first_name.lower() if child_first_name else None
                existing_user.child_last_name = child_last_name.lower() if child_last_name else None
                existing_user.account_claimed = True
                db.session.commit()
                parent_user = existing_user
                # Only create ghost child if not found
                if not child_user:
                    ghost_user = User(
                        first_name=child_first_name.lower() if child_first_name else None,
                        last_name=child_last_name.lower() if child_last_name else None,
                        is_parent=False,
                        account_claimed=False
                    )
                    db.session.add(ghost_user)
                    db.session.commit()
                    child_user = ghost_user
            else:
                db.session.add(new_user)
                if not child_user:
                    ghost_user = User(
                        first_name=child_first_name.lower() if child_first_name else None,
                        last_name=child_last_name.lower() if child_last_name else None,
                        is_parent=False,
                        account_claimed=False
                    )
                    db.session.add(ghost_user)
                    db.session.commit()
                    child_user = ghost_user
                else:
                    db.session.commit()
                parent_user = new_user
                # If child_user existed, don't create a new one
        elif not is_parent:
            new_user = User(
                first_name=first_name.lower(),
                last_name=last_name.lower(),
                
                email=email,
                password=generate_password_hash(password),
                phone_number=phone_number,

                is_parent=is_parent,
                emergency_contact_first_name=emergency_first_name.lower(),
                emergency_contact_last_name=emergency_last_name.lower(),
                emergency_contact_number=emergency_phone,
                emergency_contact_relationship=emergency_relationship,
                emergency_contact_email=emergency_email,

                account_claimed=True
            )

            ghost_user = User(
                first_name=emergency_first_name.lower(),
                last_name=emergency_last_name.lower(),
                phone_number=emergency_phone,
                email=emergency_email,
                child_first_name=child_first_name,
                child_last_name=child_last_name,
                is_parent=True,
                account_claimed=False
            )

            existing_user = User.query.filter_by(first_name=first_name.lower(),last_name=last_name.lower()).first()
            print(existing_user)

            if existing_user:
                existing_user.email = email
                existing_user.password = generate_password_hash(password)
                existing_user.emergency_contact_first_name = emergency_first_name
                existing_user.emergency_contact_last_name = emergency_last_name
                existing_user.account_claimed = True
                db.session.commit()
            else:
                db.session.add(new_user)
                db.session.add(ghost_user)
                db.session.commit()
        

        if is_parent:
            judge = Judges(
                judge_id=parent_user.id,
                child_id=child_user.id
            )
            db.session.add(judge)
            db.session.commit()
            make_judge_reqs(parent_user)
        else:
            parent_user = User.query.filter_by(first_name=emergency_first_name.lower(), last_name=emergency_last_name.lower()).first()
            child_user = User.query.filter_by(first_name=first_name.lower(), last_name=last_name.lower()).first()
            judge = Judges(
                judge_id=parent_user.id,
                child_id=child_user.id
            )
            db.session.add(judge)
            db.session.commit()
            make_child_reqs(child_user)

        flash("Registration successful!", "success")
        return redirect(url_for("auth.login"))

    return render_template('auth/register.html')
