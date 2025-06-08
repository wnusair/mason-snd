from flask import Blueprint, session, redirect, url_for, render_template, request, flash, abort
from werkzeug.security import generate_password_hash
from mason_snd.extensions import db
from mason_snd.models.auth import User, Judges

profile_bp = Blueprint('profile', __name__, template_folder='templates')


def create_ghost(first_name, last_name, email, phone_number, creator):
    ghost = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone_number=phone_number,
        judging_reqs="test",
        child_first_name=creator.first_name,
        child_last_name=creator.last_name
    )

    db.session.add(ghost)
    db.session.commit()

    print("Ghost created")



@profile_bp.route('/user/<int:user_id>')
def index(user_id):
    # Get the current logged-in user's ID from the session
    current_user_id = session.get('user_id')
    if not current_user_id:
        return redirect(url_for('auth.login'))  # Redirect to login if not authenticated

    # Fetch the current logged-in user and the target user being viewed
    current_user = User.query.get(current_user_id)
    target_user = User.query.get(user_id)

    if not target_user:
        return abort(404)  # Return 404 if the target user does not exist

    # Determine if the current user is allowed to view the target user's profile
    allowed = False
    if current_user.id == target_user.id:
        allowed = True  # Same user can view their own profile
    elif current_user.role > 0:
        allowed = True  # Elevated roles can view any profile
    else:
        # Check parent-child relationship between current user and target user
        judge_link = Judges.query.filter_by(judge_id=current_user.id, child_id=target_user.id).first()
        judge_link_reverse = Judges.query.filter_by(judge_id=target_user.id, child_id=current_user.id).first()
        if judge_link or judge_link_reverse:
            allowed = True

    if not allowed:
        return abort(403)  # Forbidden if not allowed

    # Determine the judge_link based on the target user being viewed
    judge_link = None
    if target_user.is_parent:
        # If the target user is a parent, find their child
        child = User.query.filter_by(
            first_name=target_user.child_first_name,
            last_name=target_user.child_last_name
        ).first()
        if child:
            judge_link = child.id
    else:
        # If the target user is a child, find their parent
        parent = User.query.filter_by(
            first_name=target_user.emergency_contact_first_name,
            last_name=target_user.emergency_contact_last_name
        ).first()
        if parent:
            judge_link = parent.id

    # Render the profile page with the correct judge_link
    return render_template(
        'profile/profile.html',
        judge_link=judge_link,
        user=target_user
    )

@profile_bp.route('/update', methods=['GET', 'POST'])
def update():
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
    
    user = User.query.filter_by(id=session.get('user_id')).first()

    if request.method == 'POST':
        user.first_name = request.form.get('first_name').lower()
        user.last_name = request.form.get('last_name').lower()
        user.email = request.form.get('email')
        user.phone_number = request.form.get('phone_number')

        password = request.form.get('password')
        if password:
            user.password = generate_password_hash(password)

        if user.is_parent:
            user.child_first_name = request.form.get('child_first_name').lower()
            user.child_last_name = request.form.get('child_last_name').lower()
        else:
            user.emergency_contact_first_name = request.form.get('emergency_contact_first_name').lower()
            user.emergency_contact_last_name = request.form.get('emergency_contact_last_name').lower()
            user.emergency_contact_number = request.form.get('emergency_contact_phone')
            user.emergency_contact_email = request.form.get('emergency_contact_email')
            user.emergency_contact_relationship = request.form.get('emergency_contact_relationship')

        db.session.commit()
        flash('Profile updated successfully', 'success')
        return redirect(url_for('profile.index'))

    return render_template('profile/update.html', user=user)

@profile_bp.route('/add_judge', methods=['POST', 'GET'])
def add_judge():
    user_id = session.get('user_id')
    
    if not user_id:
        flash('Log in first!')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        user = User.query.filter_by(id=user_id).first()

        """
        
        judge first name
        judge last name
        judge email
        judge phone number

        check if account exists
        if not exists -> make ghost account

        add judge relationship


        
        """

        judge_first_name = request.form.get("judge_first_name")
        judge_last_name = request.form.get("judge_last_name")
        judge_email = request.form.get("judge_email")
        judge_phone = request.form.get("judge_phone")


        judge_account = User.query.filter_by(first_name=judge_first_name, last_name=judge_last_name, phone_number=judge_phone).first()

        if not judge_account:
            create_ghost(judge_first_name, judge_last_name, judge_email, judge_phone, user)
        
        judge_relationship = Judges(
            background_check=False,
            judge_id=judge_account.id,
            child_id=user_id
        )

        db.session.add(judge_relationship)
        db.session.commit()

        return redirect(url_for('profile.index'))
    return render_template('add_judge.html')