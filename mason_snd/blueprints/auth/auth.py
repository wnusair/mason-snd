"""
Authentication Blueprint

This module handles user authentication, registration, and requirement management.
It provides routes for login, logout, and registration, along with utilities for
managing user requirements based on their role (student vs parent/judge).

Key Features:
    - User login and logout
    - Student and parent/judge registration
    - Ghost account creation and claiming
    - Automated requirement assignment
    - Parent-child relationship management
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from mason_snd.extensions import db
from mason_snd.models.auth import User, Judges
from mason_snd.models.admin import User_Requirements, Requirements
from mason_snd.models.events import User_Event
from mason_snd.models.tournaments import Tournament_Judges, Tournaments_Attended, Tournament, Tournament_Performance
from mason_snd.utils.race_protection import prevent_race_condition

from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import pytz

# Blueprint configuration
auth_bp = Blueprint('auth', __name__, template_folder='templates')

# Timezone constant
EASTERN_TIMEZONE = pytz.timezone('US/Eastern')

# Standard requirement IDs (matches Requirements table)
REQ_SUBMIT_FINAL_FORMS = "1"
REQ_PAY_MEMBERSHIP_FEE = "2"
REQ_SUBMIT_TOURNAMENT_PERFORMANCE = "3"
REQ_JOIN_EVENT = "4"
REQ_SIGN_PERMISSION_SLIP = "5"
REQ_PAY_TOURNAMENT_FEES = "6"
REQ_BACKGROUND_CHECK = "7"
REQ_RESPOND_TO_JUDGE_REQUEST = "8"
REQ_COMPLETE_JUDGE_TRAINING = "9"


def make_all_requirements():
    """
    Create all standard requirements in the database if they don't exist.
    
    This function ensures that all required system requirements are present
    in the Requirements table. It's idempotent and safe to call multiple times.
    
    Standard Requirements:
        1. Submit Final Forms
        2. Pay Membership Fee on PaySchools
        3. Submit Tournament Performance
        4. Join an Event
        5. Sign the Permission slip for GMV tournaments
        6. Pay your Tournament Fees
        7. Complete background check (for judges)
        8. Respond to Judging Request by Child (for judges)
        9. Complete your judge training (for judges)
    
    Returns:
        None
    """
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
    """
    Create a user-specific requirement assignment.
    
    Args:
        user_id (int): The ID of the user to assign the requirement to
        requirement_id (str): The ID of the requirement template
        deadline (datetime): The deadline for completing this requirement
    
    Returns:
        None
    """
    user_requirement = User_Requirements(
        deadline=deadline,
        user_id=user_id,
        requirement_id=requirement_id
    )
    db.session.add(user_requirement)
    db.session.commit()

def get_requirements(user):
    """
    Ensure all requirements exist and assign appropriate requirements to user.
    
    This function first checks that all standard requirements exist in the database,
    creating them if necessary. Then it assigns role-specific requirements to the user
    based on whether they are a parent/judge or student.
    
    Args:
        user (User): The user object to assign requirements to
    
    Returns:
        None
    """
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
    
    # Create any missing requirements
    if missing_reqs:
        make_all_requirements()
    
    # Assign role-specific requirements
    if user.is_parent:
        make_judge_reqs(user)
    else:
        make_child_reqs(user)

    
def make_child_reqs(user):
    """
    Assign student-specific requirements to a user.
    
    This function assigns all requirements applicable to students, including:
    - Standard requirements (forms, fees, permissions)
    - Conditional requirements based on user status:
        * Tournament performance submission (if attended but not submitted)
        * Join event (if not in any event)
    
    Args:
        user (User): The student user object to assign requirements to
    
    Returns:
        None
    """
    now = datetime.datetime.now(EASTERN_TIMEZONE)
    default_deadline_days = 7
    
    # Standard requirements that always apply to students
    standard_requirement_deadlines = {
        REQ_SUBMIT_FINAL_FORMS: now + datetime.timedelta(days=default_deadline_days),
        REQ_PAY_MEMBERSHIP_FEE: now + datetime.timedelta(days=default_deadline_days),
        REQ_SIGN_PERMISSION_SLIP: now + datetime.timedelta(days=default_deadline_days),
        REQ_PAY_TOURNAMENT_FEES: now + datetime.timedelta(days=default_deadline_days)
    }
    
    # Add standard requirements if they don't already exist
    for requirement_id, deadline in standard_requirement_deadlines.items():
        existing_req = User_Requirements.query.filter_by(
            user_id=user.id,
            requirement_id=requirement_id
        ).first()
        if existing_req is None:
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
        existing_req = User_Requirements.query.filter_by(
            user_id=user.id,
            requirement_id=REQ_SUBMIT_TOURNAMENT_PERFORMANCE
        ).first()
        if existing_req is None:
            make_user_requirement(
                user.id,
                REQ_SUBMIT_TOURNAMENT_PERFORMANCE,
                now + datetime.timedelta(days=default_deadline_days)
            )
    
    # Check if user is not in an event and add requirement if needed
    user_in_event = User_Event.query.filter_by(user_id=user.id).first()
    if user_in_event is None:
        existing_req = User_Requirements.query.filter_by(
            user_id=user.id,
            requirement_id=REQ_JOIN_EVENT
        ).first()
        if existing_req is None:
            make_user_requirement(
                user.id,
                REQ_JOIN_EVENT,
                now + datetime.timedelta(days=default_deadline_days)
            )

def make_judge_reqs(user):
    """
    Assign judge/parent-specific requirements to a user.
    
    This function assigns all requirements applicable to judges/parents, including:
    - Standard requirements (background check, judge training)
    - Conditional requirements based on user status:
        * Respond to judge request (if child has pending judge requests)
    
    Args:
        user (User): The parent/judge user object to assign requirements to
    
    Returns:
        None
    """
    now = datetime.datetime.now(EASTERN_TIMEZONE)
    default_deadline_days = 7
    
    # Standard judge requirements that always apply
    standard_requirement_deadlines = {
        REQ_BACKGROUND_CHECK: now + datetime.timedelta(days=default_deadline_days),
        REQ_COMPLETE_JUDGE_TRAINING: now + datetime.timedelta(days=default_deadline_days)
    }
    
    # Add standard requirements if they don't already exist
    for requirement_id, deadline in standard_requirement_deadlines.items():
        existing_req = User_Requirements.query.filter_by(
            user_id=user.id,
            requirement_id=requirement_id
        ).first()
        if existing_req is None:
            make_user_requirement(user.id, requirement_id, deadline)
    
    # Check if their child has requested them to judge (pending requests)
    tournament_judge_requests = Tournament_Judges.query.filter_by(
        judge_id=user.id,
        accepted=False
    ).all()
    
    # Only add the judging request requirement if there are pending requests
    if tournament_judge_requests:
        existing_req = User_Requirements.query.filter_by(
            user_id=user.id,
            requirement_id=REQ_RESPOND_TO_JUDGE_REQUEST
        ).first()
        if existing_req is None:
            make_user_requirement(
                user.id,
                REQ_RESPOND_TO_JUDGE_REQUEST,
                now + datetime.timedelta(days=default_deadline_days)
            )

def req_checks(user):
    """
    Update requirement completion status based on current user state.
    
    This function checks the user's current status and updates or removes requirements
    accordingly. It's called during login to ensure requirements reflect reality.
    
    For Students:
        - Removes tournament performance requirement if all attended tournaments have results
        - Removes join event requirement if user is in an event
    
    For Judges/Parents:
        - Removes judge request requirement if no pending requests
    
    Args:
        user (User): The user object to check requirements for
    
    Returns:
        None
    """
    # Handle student requirements
    if not user.is_parent:
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
        performance_req = User_Requirements.query.filter_by(
            user_id=user.id,
            requirement_id=REQ_SUBMIT_TOURNAMENT_PERFORMANCE
        ).first()
        
        if has_unsubmitted_performance:
            if performance_req:
                performance_req.complete = False
                print("Performance needed to be submitted")
        else:
            if performance_req:
                # Remove the requirement if all performances are submitted
                db.session.delete(performance_req)
                print("All performances submitted - requirement removed")

        # Check if the user is in an event
        user_in_event = User_Event.query.filter_by(user_id=user.id).first()
        event_req = User_Requirements.query.filter_by(
            user_id=user.id,
            requirement_id=REQ_JOIN_EVENT
        ).first()
        
        if user_in_event is not None:
            if event_req:
                # Remove the requirement if user is in an event
                db.session.delete(event_req)
                print("User is in event - requirement removed")
        else:
            if event_req:
                event_req.complete = False
                print("User not in event - requirement remains")

    # Handle judge/parent requirements
    if user.is_parent:
        # Check for pending judging requests
        tournament_judge_requests = Tournament_Judges.query.filter_by(
            judge_id=user.id,
            accepted=False
        ).all()
        judge_req = User_Requirements.query.filter_by(
            user_id=user.id,
            requirement_id=REQ_RESPOND_TO_JUDGE_REQUEST
        ).first()

        if tournament_judge_requests:
            if judge_req:
                judge_req.complete = False
                print("Pending judging requests - requirement active")
        else:
            if judge_req:
                # Remove the requirement if no pending requests
                db.session.delete(judge_req)
                print("No pending judging requests - requirement removed")

    db.session.commit()

@auth_bp.route('/logout')
def logout():
    """
    Log out the current user.
    
    Clears the user session and redirects to the login page.
    
    Returns:
        redirect: Redirect response to login page
    """
    session.clear()
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handle user login.
    
    GET: Display login form
    POST: Authenticate user credentials and create session
    
    On successful login:
        - Creates user session with user_id and role
        - Ensures all requirements exist and are assigned
        - Updates requirement status based on current user state
        - Redirects to user profile
    
    Returns:
        GET: Rendered login template
        POST: Redirect to profile on success, or login page with error on failure
    """
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            # Create user session
            session['user_id'] = user.id
            session['role'] = user.role
            
            # Ensure requirements are up to date
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



def find_or_create_user(first_name, last_name, is_parent, **user_data):
    """
    Find existing user or create new one, handling ghost account claiming.
    
    This function implements the ghost account system, which allows creating
    placeholder accounts for users who haven't registered yet (e.g., when a
    student registers and provides their parent's info).
    
    Behavior:
        - If user exists and unclaimed: Claims account with provided data
        - If user exists and claimed: Updates missing critical fields only
        - If user doesn't exist: Creates new claimed account
    
    Args:
        first_name (str): User's first name (will be stored lowercase)
        last_name (str): User's last name (will be stored lowercase)
        is_parent (bool): True if parent/judge, False if student
        **user_data: Additional user fields (email, password, phone_number, etc.)
    
    Returns:
        User: The found or created user object
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
            critical_fields = ['email', 'phone_number', 'password']
            
            for key, value in user_data.items():
                if key in critical_fields and value is not None:
                    current_value = getattr(existing_user, key)
                    if current_value is None or current_value == '':
                        setattr(existing_user, key, value)
                        updated_fields.append(key)
            
            if updated_fields:
                db.session.commit()
                print(f"Updated existing claimed account for {first_name} {last_name} "
                      f"with fields: {updated_fields}")
            else:
                print(f"User {first_name} {last_name} already has a claimed account "
                      f"with complete information")
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
    Create judge-child relationship if it doesn't exist.
    
    This function links a parent/judge to their child, avoiding duplicates.
    The relationship is stored in the Judges table.
    
    Args:
        judge_id (int): The user ID of the parent/judge
        child_id (int): The user ID of the child/student
    
    Returns:
        None
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
@prevent_race_condition(
    'registration',
    min_interval=2.0,
    redirect_on_duplicate=lambda uid, form: redirect(url_for('auth.login'))
)
def register():
    """
    Handle user registration for both students and parents/judges.
    
    GET: Display registration form
    POST: Process registration, create user account, and set up relationships
    
    Registration Process:
        1. Validate required fields based on role (student vs parent)
        2. Check for existing accounts with same email
        3. Create or claim user account using ghost account system
        4. For parents: Create/find child account and link via Judges table
        5. For students: Create/find parent account and link via Judges table
        6. Assign initial requirements based on role
    
    Form Fields (Common):
        - first_name, last_name, email, phone_number
        - password, confirm_password
        - is_parent: 'yes' or 'no'
    
    Form Fields (Parent-specific):
        - child_first_name, child_last_name
    
    Form Fields (Student-specific):
        - emergency_first_name, emergency_last_name
        - emergency_email, emergency_phone
        - emergency_relationship
    
    Returns:
        GET: Rendered registration template
        POST: Redirect to login on success, or registration page with errors
    """
    if request.method == 'POST':
        # Extract common fields
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

        # Initialize role-specific fields
        emergency_first_name = emergency_last_name = None
        emergency_email = emergency_phone = emergency_relationship = None
        child_first_name = child_last_name = None

        # Validate and extract role-specific fields
        if is_parent:
            child_first_name = request.form.get('child_first_name')
            child_last_name = request.form.get('child_last_name')
            
            if not child_first_name or not child_last_name:
                flash("Child's first name and last name are required when "
                      "registering as a parent.", 'error')
                return render_template('auth/register.html')
        else:
            emergency_first_name = request.form.get('emergency_first_name')
            emergency_last_name = request.form.get('emergency_last_name')
            emergency_email = request.form.get('emergency_email')
            emergency_phone = request.form.get('emergency_phone')
            emergency_relationship = request.form.get('emergency_relationship')
            
            if not all([emergency_first_name, emergency_last_name, emergency_email,
                       emergency_phone, emergency_relationship]):
                flash("All emergency contact information is required when "
                      "registering as a student.", 'error')
                return render_template('auth/register.html')
        
        # Debug logging
        print(first_name, last_name, email, phone_number, is_parent, password,
              confirm_password, emergency_first_name, emergency_last_name,
              emergency_email, emergency_phone, emergency_relationship,
              child_first_name, child_last_name)

        # Validate password match
        if password != confirm_password:
            flash("Passwords do not match", 'error')
            return render_template('auth/register.html')

        # Check for existing email (but allow ghost account claiming)
        existing_email_user = User.query.filter_by(email=email).first()
        if existing_email_user and existing_email_user.account_claimed:
            # Check if this is the same person trying to claim their ghost account
            is_same_person = (
                existing_email_user.first_name.lower() == first_name.lower() and
                existing_email_user.last_name.lower() == last_name.lower() and
                existing_email_user.is_parent == is_parent
            )
            
            if not is_same_person:
                flash("An account with this email address already exists. "
                      "Please use a different email or try logging in.", 'error')
                return render_template('auth/register.html')

        # Handle parent registration
        if is_parent:
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
            child_user = find_or_create_user(
                child_first_name,
                child_last_name,
                False,
                **child_user_data
            )
            
            # Create or update judge relationship
            create_or_update_judge_relationship(parent_user.id, child_user.id)
            make_judge_reqs(parent_user)
            
        # Handle student registration
        else:
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
            parent_user = find_or_create_user(
                emergency_first_name,
                emergency_last_name,
                True,
                **parent_user_data
            )
            
            # Create or update judge relationship
            create_or_update_judge_relationship(parent_user.id, child_user.id)
            make_child_reqs(child_user)

        flash("Registration successful!", "success")
        return redirect(url_for("auth.login"))

    return render_template('auth/register.html')
