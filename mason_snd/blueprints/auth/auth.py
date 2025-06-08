from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from mason_snd.extensions import db
from mason_snd.models.auth import User, Judges

from werkzeug.security import generate_password_hash, check_password_hash

auth_bp = Blueprint('auth', __name__, template_folder='templates')

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

        flash("Registration successful!", "success")
        return redirect(url_for("auth.login"))

    return render_template('auth/register.html')
