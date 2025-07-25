from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from mason_snd.extensions import db
from mason_snd.models.auth import User, Judges
from mason_snd.models.admin import User_Requirements, Requirements

from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import pytz

auth_bp = Blueprint('auth', __name__, template_folder='templates')

def make_all_requirements():
    requirements_body = [
        "Final Forms Signed",
        "Membership Fee paid",
        "Tournament Performance Submitted",
        "Event joined",
        "Permission slip for GMV tournaments has been signed",
        "Tournament Fee paid",
        "Has completed background check",
        "Has accepted or denied judging request from their child",
        "Has completed judge training",
        "Has filled out the judging form for their tournament"
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
        "Final Forms Signed",
        "Membership Fee paid",
        "Tournament Performance Submitted",
        "Event joined",
        "Permission slip for GMV tournaments has been signed",
        "Tournament Fee paid",
        "Has completed background check",
        "Has accepted or denied judging request from their child",
        "Has completed judge training",
        "Has filled out the judging form for their tournament"
    ]
    existing_reqs = {req.body for req in Requirements.query.all()}
    missing_reqs = [req for req in requirements_body if req not in existing_reqs]
    if missing_reqs:
        make_all_requirements()
    # Return all requirements for the user (customize as needed)
    
def make_child_reqs(user):
    eastern = pytz.timezone('US/Eastern')
    now = datetime.datetime.now(eastern)
    # Example: set deadlines 7 days from now for each requirement
    requirement_deadlines = {
        "1": now + datetime.timedelta(days=7),
        "2": now + datetime.timedelta(days=7),
        "3": now + datetime.timedelta(days=7),
        "4": now + datetime.timedelta(days=7),
        "5": now + datetime.timedelta(days=7),
        "6": now + datetime.timedelta(days=7)
        #"7": now + datetime.timedelta(days=7),
        #"8": now + datetime.timedelta(days=7),
        #"9": now + datetime.timedelta(days=7),
        #"10": now + datetime.timedelta(days=7)
    }
    for requirement_id, deadline in requirement_deadlines.items():
        make_user_requirement(user, requirement_id, deadline)

def make_judge_reqs(user):
    eastern = pytz.timezone('US/Eastern')
    now = datetime.datetime.now(eastern)
    # Example: set deadlines 7 days from now for each requirement
    requirement_deadlines = {
        #"1": now + datetime.timedelta(days=7),
        #"2": now + datetime.timedelta(days=7),
        #"3": now + datetime.timedelta(days=7),
        #"4": now + datetime.timedelta(days=7),
        #"5": now + datetime.timedelta(days=7),
        #"6": now + datetime.timedelta(days=7)
        "7": now + datetime.timedelta(days=7),
        "8": now + datetime.timedelta(days=7),
        "9": now + datetime.timedelta(days=7),
        "10": now + datetime.timedelta(days=7)
    }
    for requirement_id, deadline in requirement_deadlines.items():
        make_user_requirement(user, requirement_id, deadline)


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
            get_requirements(user)
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

            ghost_user = User(
                first_name=child_first_name,
                last_name=child_last_name,
                is_parent=False,
                account_claimed=False
            )


            existing_user = User.query.filter_by(first_name=first_name.lower(), last_name=last_name.lower()).first()
            print(existing_user)

            if existing_user:
                existing_user.email = email
                existing_user.password = password
                existing_user.judging_reqs="test"
                existing_user.child_first_name = child_first_name
                existing_user.child_last_name = child_last_name
                existing_user.account_claimed = True
                db.session.commit()
            else:
                db.session.add(new_user)
                db.session.add(ghost_user)
                db.session.commit()
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
            parent_user = User.query.filter_by(first_name=first_name.lower(),last_name=last_name.lower()).first()
            child_user = User.query.filter_by(first_name=child_first_name,last_name=child_last_name).first()

            judge = Judges(
                judge_id = parent_user.id,
                child_id = child_user.id
            )

            db.session.add(judge)
            db.session.commit()
        else:
            parent_user = User.query.filter_by(first_name=emergency_first_name.lower(),last_name=emergency_last_name.lower()).first()
            child_user = User.query.filter_by(first_name=first_name.lower(),last_name=last_name.lower()).first()

            judge = Judges(
                judge_id = parent_user.id,
                child_id = child_user.id
            )

            db.session.add(judge)
            db.session.commit()
        
        if is_parent:
            make_judge_reqs(parent_user)
        else:
            make_child_reqs(child_user)

        flash("Registration successful!", "success")
        return redirect(url_for("auth.login"))

    return render_template('auth/register.html')
