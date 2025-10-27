"""Profile Blueprint - User profile management with ghost account system.

Handles user profile viewing, editing, parent-child relationship management, and
ghost account creation for unclaimed parent/child accounts. Includes notification
system for published rosters and popup messages.

Ghost Account System:
    Purpose:
        - Enable parent-child relationships before both parties have accounts
        - Create placeholder accounts for judges/children not yet registered
        - Maintain judge commitments and roster assignments
    
    Ghost Account Creation:
        - Created when user adds parent/child who doesn't exist
        - Fields: first_name, last_name, email, phone_number
        - Flags: is_parent (True/False), account_claimed (False)
        - Link: child_first_name/child_last_name point to creator
    
    Ghost Account Claiming:
        - When ghost user registers, account_claimed set to True
        - Existing relationships preserved (Judges table)
        - Profile data merged/updated

Parent-Child Relationships:
    Judges Table:
        - Links parent (judge_id) to child (child_id)
        - Enables profile access across family members
        - Tracks background_check status
    
    Access Control:
        - Users can view their own profile
        - Elevated roles (role > 0) can view any profile
        - Parents can view child profiles (via Judges link)
        - Children can view parent profiles (reverse link)
    
    Relationship Management:
        - add_judge(): Child adds parent relationship
        - add_child(): Parent adds child relationship
        - update(): Updates relationships when emergency contact/child changes

Notification System:
    Published Rosters:
        - User_Published_Rosters entries created when roster published
        - notified flag tracks if user has seen notification
        - New notifications displayed on profile page
        - Auto-marked as seen when user views own profile
    
    Popup Messages:
        - Admin-created messages (Popups table)
        - Displayed until dismissed or expired
        - Expiration: expires_at timestamp or NULL (never expires)
        - Dismissal: Sets completed=True

Route Organization:
    Profile Viewing:
        - index(user_id): View user profile with access control
    
    Profile Management:
        - update(): Edit profile, password, emergency contact/child info
    
    Relationship Management:
        - add_judge(): Child adds parent/guardian
        - add_child(): Parent adds child
    
    Notifications:
        - dismiss_popup(popup_id): Dismiss admin popup message

Key Features:
    - Dynamic relationship updates with ghost creation
    - Parent-child access control
    - Published roster notifications
    - Popup message system
    - Race condition protection on updates
"""

from flask import Blueprint, session, redirect, url_for, render_template, request, flash, abort
from werkzeug.security import generate_password_hash
from mason_snd.extensions import db
from mason_snd.models.auth import User, Judges, User_Published_Rosters
from mason_snd.models.admin import User_Requirements, Requirements, Popups
from mason_snd.models.rosters import Roster
from mason_snd.models.tournaments import Tournament
from mason_snd.models.events import Event
from mason_snd.utils.race_protection import prevent_race_condition
from mason_snd.utils.auth_helpers import redirect_to_login
from datetime import datetime
import pytz

profile_bp = Blueprint('profile', __name__, template_folder='templates')


def create_ghost(first_name, last_name, email, phone_number, creator):
    """Create ghost (unclaimed) account for parent or child not yet registered.
    
    Ghost accounts are placeholder user records created when a user adds a parent/child
    relationship to someone who doesn't have an account yet. This enables judge commitments
    and roster assignments before both parties are registered.
    
    Args:
        first_name (str): Ghost user's first name.
        last_name (str): Ghost user's last name.
        email (str): Ghost user's email (may be empty string).
        phone_number (str): Ghost user's phone number (may be empty string).
        creator (User): User object of person creating the ghost (establishes link).
    
    Ghost Account Fields:
        - first_name, last_name: Identity
        - email, phone_number: Contact info (may be incomplete)
        - judging_reqs: Set to "test" (placeholder)
        - child_first_name, child_last_name: Link to creator (establishes relationship)
        - is_parent: False (ghosts created by children are parents, but this field is legacy)
        - account_claimed: False (marks as unclaimed ghost)
    
    Side Effects:
        - Creates User record in database
        - Commits transaction
        - Prints "Ghost created" to console
    
    Note:
        After creation, caller should query for the new ghost user and create
        Judges relationship entry. Ghost users can later claim their account
        during registration by matching name/phone.
    
    Example Flow:
        1. Child adds parent who doesn't exist
        2. create_ghost() creates parent placeholder
        3. Judges relationship created (judge_id=ghost, child_id=child)
        4. Parent later registers and claims account
        5. account_claimed set to True, relationships preserved
    """
    ghost = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone_number=phone_number,
        judging_reqs="test",
        child_first_name=creator.first_name,
        child_last_name=creator.last_name,
        is_parent=False,
        account_claimed=False
    )

    db.session.add(ghost)
    db.session.commit()

    print("Ghost created")


    


@profile_bp.route('/user/<int:user_id>')
def index(user_id):
    """View user profile with access control and notifications.
    
    Displays user profile with incomplete requirements, active popups, published rosters,
    and parent-child relationship links. Implements sophisticated access control based on
    role, self-viewing, and parent-child relationships.
    
    URL Parameters:
        user_id (int): User primary key to view.
    
    Access Control:
        Allowed if:
        - User viewing their own profile (current_user.id == user_id)
        - Current user has elevated role (role > 0)
        - Parent-child relationship exists (either direction via Judges table)
        
        Denied:
        - Returns 403 Forbidden if none of above conditions met
        - Returns 404 if target user not found
        - Redirects to login if not authenticated
    
    Parent-Child Link Detection:
        If target user is parent (is_parent=True):
            - Searches for child by child_first_name/child_last_name
            - Sets judge_link to child's user_id
        
        If target user is child (is_parent=False):
            - Searches for parent by emergency_contact_first_name/emergency_contact_last_name
            - Sets judge_link to parent's user_id
        
        Purpose: Enables navigation between parent and child profiles
    
    Data Displayed:
        - User basic info (name, email, phone, role)
        - Incomplete requirements (User_Requirements where complete=False)
        - Active popups (Popups not completed, not expired)
        - Published rosters (User_Published_Rosters with roster/tournament/event details)
        - New roster notifications (unnotified published rosters)
    
    Notifications:
        - Published rosters with notified=False shown as "new"
        - Auto-marked as seen (notified=True) when viewing own profile
        - Prevents repeated "new" badges on subsequent visits
    
    Popup Filtering:
        - Active if completed=False
        - AND (expires_at is NULL OR expires_at > current time EST)
        - Sorted by creation/priority
    
    Template Variables:
        - judge_link: User ID of related parent/child (or None)
        - user: Target user being viewed
        - user_requirements: List of incomplete requirements
        - requirements: Dict of all Requirements by ID
        - current_user: Target user (alias for template compatibility)
        - active_popups: List of active Popup objects
        - published_rosters: List of (User_Published_Rosters, Roster, Tournament, Event) tuples
        - new_roster_notifications: List of unnotified rosters (only if viewing own profile)
    
    Returns:
        profile/profile.html with comprehensive profile data.
    
    Note:
        Judge_link enables quick navigation in template between parent and child.
        Notification auto-marking happens only for own profile to preserve "new" status
        when others (admins) view the profile.
    """
    # Get the current logged-in user's ID from the session
    current_user_id = session.get('user_id')
    if not current_user_id:
        return redirect_to_login()  # Redirect to login if not authenticated

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

    user_requirements = User_Requirements.query.filter_by(user_id=user_id, complete=False).all()

    # Get active popups for the user
    EST = pytz.timezone('US/Eastern')
    now = datetime.now(EST)
    
    active_popups = Popups.query.filter_by(
        user_id=user_id, 
        completed=False
    ).filter(
        (Popups.expires_at.is_(None)) | (Popups.expires_at > now)
    ).all()

    # Get published rosters for this user
    published_rosters = db.session.query(
        User_Published_Rosters, Roster, Tournament, Event
    ).join(
        Roster, User_Published_Rosters.roster_id == Roster.id
    ).join(
        Tournament, User_Published_Rosters.tournament_id == Tournament.id
    ).join(
        Event, User_Published_Rosters.event_id == Event.id
    ).filter(
        User_Published_Rosters.user_id == user_id
    ).order_by(
        Roster.published_at.desc()
    ).all()

    # Check for new notifications (unnotified published rosters)
    new_roster_notifications = User_Published_Rosters.query.filter_by(
        user_id=user_id, 
        notified=False
    ).all()

    # Mark notifications as seen if we're viewing our own profile
    if current_user.id == target_user.id and new_roster_notifications:
        for notification in new_roster_notifications:
            notification.notified = True
        db.session.commit()

    # Render the profile page with the correct judge_link
    return render_template(
        'profile/profile.html',
        judge_link=judge_link,
        user=target_user,
        user_requirements=user_requirements,
        requirements={r.id: r for r in Requirements.query.all()},
        current_user=target_user,
        active_popups=active_popups,
        published_rosters=published_rosters,
        new_roster_notifications=new_roster_notifications if current_user.id == target_user.id else []
    )

@profile_bp.route('/update', methods=['GET', 'POST'])
@prevent_race_condition('update_profile', min_interval=1.0, redirect_on_duplicate=lambda uid, form: redirect(url_for('profile.index', user_id=uid.replace('ip_', '') if not uid.startswith('ip_') else session.get('user_id'))))
def update():
    """Update user profile with dynamic parent-child relationship management.
    
    Methods:
        GET: Display profile update form with current user data.
        POST: Process profile updates, create ghosts if needed, update relationships.
    
    Form Fields (POST):
        All Users:
            - first_name, last_name: User's name (lowercased)
            - email: User's email address
            - phone_number: User's phone number
            - password: Optional password change (hashed if provided)
        
        Parent Users (is_parent=True):
            - child_first_name, child_last_name: Child's name (lowercased)
        
        Child Users (is_parent=False):
            - emergency_first_name, emergency_last_name: Emergency contact name (lowercased)
            - emergency_contact_phone: Emergency contact phone
            - emergency_contact_email: Emergency contact email
            - emergency_contact_relationship: Relationship (parent, guardian, etc.)
    
    Parent User Update Logic:
        1. Compare old vs new child_first_name/child_last_name
        2. If changed:
            a. Search for existing user with new child name (is_parent=False)
            b. If not found: Create ghost account for child
            c. Remove old Judges relationship (if child changed)
            d. Create new Judges relationship (judge_id=parent, child_id=child)
    
    Child User Update Logic:
        1. Compare old vs new emergency_contact info
        2. If changed (name OR phone):
            a. Search for existing user with new emergency contact (is_parent=True, matching phone)
            b. If not found: Create ghost parent account
            c. Remove old Judges relationship (if parent changed)
            d. Create new Judges relationship (judge_id=parent, child_id=child)
    
    Ghost Account Creation:
        Parent Ghost (created by child):
            - first_name, last_name from emergency contact
            - phone_number, email from emergency contact
            - child_first_name, child_last_name: Link to child creator
            - is_parent=True, account_claimed=False
        
        Child Ghost (created by parent):
            - first_name, last_name from child fields
            - email, phone_number: Empty strings (not provided)
            - child_first_name, child_last_name: Link to parent creator
            - is_parent=False, account_claimed=False
    
    Judges Relationship Management:
        - Always checks for existing relationship before creating (avoids duplicates)
        - Deletes old relationship when parent/child changes
        - Creates new relationship with background_check=False
        - Preserves relationships across ghost account claiming
    
    Password Update:
        - Only updated if password field provided (not empty)
        - Hashed using generate_password_hash (werkzeug.security)
        - Old password NOT required (admin feature)
    
    Race Condition Protection:
        @prevent_race_condition decorator (1 second interval) prevents duplicate submissions.
    
    Access Control:
        Requires login. Redirects to auth.login if not authenticated.
    
    Returns:
        GET: profile/update.html with current user data.
        POST: Redirects to profile.index with success message.
    
    Side Effects:
        - Updates User record fields
        - May create ghost User accounts
        - May create/delete Judges relationships
        - Commits all changes to database
    
    Note:
        Relationship updates happen ONLY when names change (not email/phone alone for children).
        For children, phone change triggers relationship update because phone is used for
        parent matching (emergency contact phone = parent phone).
    """
    if not session.get('user_id'):
        return redirect_to_login()
    
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
            old_child_first = user.child_first_name
            old_child_last = user.child_last_name
            new_child_first = request.form.get('child_first_name').lower()
            new_child_last = request.form.get('child_last_name').lower()
            
            user.child_first_name = new_child_first
            user.child_last_name = new_child_last
            
            # Check if child information has changed and create ghost if needed
            if (old_child_first != new_child_first or old_child_last != new_child_last):
                # Check if the new child already exists
                existing_child = User.query.filter_by(
                    first_name=new_child_first,
                    last_name=new_child_last,
                    is_parent=False
                ).first()
                
                if not existing_child:
                    # Create ghost account for the new child
                    create_ghost(new_child_first, new_child_last, "", "", user)
                    existing_child = User.query.filter_by(
                        first_name=new_child_first,
                        last_name=new_child_last,
                        is_parent=False
                    ).first()
                
                # Update judge relationship if child changed
                if existing_child:
                    # Remove old relationship if it exists
                    if old_child_first and old_child_last:
                        old_child = User.query.filter_by(
                            first_name=old_child_first,
                            last_name=old_child_last,
                            is_parent=False
                        ).first()
                        if old_child:
                            old_relationship = Judges.query.filter_by(
                                judge_id=user.id, 
                                child_id=old_child.id
                            ).first()
                            if old_relationship:
                                db.session.delete(old_relationship)
                    
                    # Add new relationship
                    new_relationship = Judges.query.filter_by(
                        judge_id=user.id, 
                        child_id=existing_child.id
                    ).first()
                    if not new_relationship:
                        new_relationship = Judges(
                            background_check=False,
                            judge_id=user.id,
                            child_id=existing_child.id
                        )
                        db.session.add(new_relationship)
        else:
            old_emergency_first = user.emergency_contact_first_name
            old_emergency_last = user.emergency_contact_last_name
            old_emergency_phone = user.emergency_contact_number
            old_emergency_email = user.emergency_contact_email
            
            new_emergency_first = request.form.get('emergency_first_name').lower()
            new_emergency_last = request.form.get('emergency_last_name').lower()
            new_emergency_phone = request.form.get('emergency_contact_phone')
            new_emergency_email = request.form.get('emergency_contact_email')
            
            user.emergency_contact_first_name = new_emergency_first
            user.emergency_contact_last_name = new_emergency_last
            user.emergency_contact_number = new_emergency_phone
            user.emergency_contact_email = new_emergency_email
            user.emergency_contact_relationship = request.form.get('emergency_contact_relationship')
            
            # Check if emergency contact information has changed and create ghost if needed
            if (old_emergency_first != new_emergency_first or 
                old_emergency_last != new_emergency_last or
                old_emergency_phone != new_emergency_phone):
                
                # Check if the new emergency contact already exists
                existing_parent = User.query.filter_by(
                    first_name=new_emergency_first,
                    last_name=new_emergency_last,
                    phone_number=new_emergency_phone,
                    is_parent=True
                ).first()
                
                if not existing_parent:
                    # Create ghost account for the new emergency contact
                    ghost_parent = User(
                        first_name=new_emergency_first,
                        last_name=new_emergency_last,
                        phone_number=new_emergency_phone,
                        email=new_emergency_email,
                        child_first_name=user.first_name,
                        child_last_name=user.last_name,
                        is_parent=True,
                        account_claimed=False
                    )
                    db.session.add(ghost_parent)
                    db.session.commit()
                    existing_parent = ghost_parent
                
                # Update judge relationship if emergency contact changed
                if existing_parent:
                    # Remove old relationship if it exists
                    if old_emergency_first and old_emergency_last:
                        old_parent = User.query.filter_by(
                            first_name=old_emergency_first,
                            last_name=old_emergency_last,
                            is_parent=True
                        ).first()
                        if old_parent:
                            old_relationship = Judges.query.filter_by(
                                judge_id=old_parent.id, 
                                child_id=user.id
                            ).first()
                            if old_relationship:
                                db.session.delete(old_relationship)
                    
                    # Add new relationship
                    new_relationship = Judges.query.filter_by(
                        judge_id=existing_parent.id, 
                        child_id=user.id
                    ).first()
                    if not new_relationship:
                        new_relationship = Judges(
                            background_check=False,
                            judge_id=existing_parent.id,
                            child_id=user.id
                        )
                        db.session.add(new_relationship)

        db.session.commit()
        flash('Profile updated successfully', 'success')
        return redirect(url_for('profile.index', user_id=user.id))

    return render_template('profile/update.html', user=user, current_user=user)

@profile_bp.route('/add_judge', methods=['POST', 'GET'])
@prevent_race_condition('add_judge', min_interval=1.0, redirect_on_duplicate=lambda uid, form: redirect(url_for('profile.index', user_id=session.get('user_id'))))
def add_judge():
    """Child adds parent/guardian relationship with ghost creation.
    
    Enables children to add parent/guardian relationships. Creates ghost account
    for judge if they don't exist yet, then creates Judges relationship.
    
    Methods:
        GET: Display add judge form.
        POST: Create judge account (if needed) and relationship.
    
    Form Fields (POST):
        - judge_first_name: Judge's first name (lowercased)
        - judge_last_name: Judge's last name (lowercased)
        - judge_email: Judge's email (lowercased)
        - judge_phone: Judge's phone number (lowercased)
    
    Algorithm:
        1. Search for existing user: first_name, last_name, phone_number match
        2. If not found:
            a. Create ghost account using create_ghost()
            b. Query for newly created ghost
        3. Check for existing Judges relationship (judge_id, child_id)
        4. If no relationship exists:
            a. Create Judges entry (background_check=False)
            b. Commit to database
        5. Redirect to profile
    
    Ghost Account Creation:
        Uses create_ghost() helper:
        - first_name, last_name, email, phone_number from form
        - creator: current user (child)
        - Results in unclaimed parent ghost account
    
    Judges Relationship:
        Fields:
        - judge_id: Judge/parent user ID
        - child_id: Current user (child) ID
        - background_check: False (not yet completed)
    
    Access Control:
        - Requires login (redirects to auth.login)
        - Child only: is_parent must be False
        - Parents redirected to profile with error message
    
    Race Condition Protection:
        @prevent_race_condition decorator (1 second interval).
    
    Returns:
        GET: profile/add_judge.html with current_user.
        POST: Redirects to profile.index.
    
    Use Cases:
        - Child self-registering needs to add parent
        - Child updating to new guardian
        - Enabling parent to judge at tournaments
    
    Note:
        Matching uses first_name + last_name + phone_number for uniqueness.
        Email is stored but not used for matching (may change, phone more stable).
        Ghost accounts can later be claimed when parent registers.
    """
    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()

    if not user_id:
        flash('Log in first!')
        return redirect_to_login()
    
    if user.is_parent:
        flash('You are not a child')
        return redirect(url_for('profile.index', user_id=user_id))

    
    if request.method == 'POST':
        """
        
        judge first name
        judge last name
        judge email
        judge phone number

        check if account exists
        if not exists -> make ghost account

        add judge relationship


        
        """

        judge_first_name = request.form.get("judge_first_name").lower()
        judge_last_name = request.form.get("judge_last_name").lower()
        judge_email = request.form.get("judge_email").lower()
        judge_phone = request.form.get("judge_phone").lower()


        judge_account = User.query.filter_by(first_name=judge_first_name, last_name=judge_last_name, phone_number=judge_phone).first()

        if not judge_account:
            create_ghost(judge_first_name, judge_last_name, judge_email, judge_phone, user)
            judge_account = User.query.filter_by(first_name=judge_first_name, last_name=judge_last_name, phone_number=judge_phone).first()

        existing_relationship = Judges.query.filter_by(judge_id=judge_account.id, child_id=user_id).first()
        if not existing_relationship:
            judge_relationship = Judges(
            background_check=False,
            judge_id=judge_account.id,
            child_id=user_id
            )

            db.session.add(judge_relationship)
            db.session.commit()

        return redirect(url_for('profile.index', user_id=user_id))
    return render_template('profile/add_judge.html', current_user=user)


@profile_bp.route('/add_child', methods=['POST', 'GET'])
@prevent_race_condition('add_child', min_interval=1.0, redirect_on_duplicate=lambda uid, form: redirect(url_for('profile.index', user_id=session.get('user_id'))))
def add_child():
    """Parent adds child relationship with ghost creation.
    
    Enables parents to add child relationships. Creates ghost account for child
    if they don't exist yet, then creates Judges relationship.
    
    Methods:
        GET: Display add child form.
        POST: Create child account (if needed) and relationship.
    
    Form Fields (POST):
        - child_first_name: Child's first name (lowercased)
        - child_last_name: Child's last name (lowercased)
        - child_email: Child's email (lowercased)
        - child_phone: Child's phone number (lowercased)
    
    Algorithm:
        1. Search for existing user: first_name, last_name, phone_number match
        2. If not found:
            a. Create ghost account using create_ghost()
            b. Query for newly created ghost
        3. Check for existing Judges relationship (judge_id=parent, child_id=child)
        4. If no relationship exists:
            a. Create Judges entry (background_check=False)
            b. Commit to database
        5. Redirect to profile
    
    Ghost Account Creation:
        Uses create_ghost() helper:
        - first_name, last_name, email, phone_number from form
        - creator: current user (parent)
        - Results in unclaimed child ghost account
    
    Judges Relationship:
        Fields:
        - judge_id: Current user (parent) ID
        - child_id: Child user ID
        - background_check: False (not yet completed)
    
    Access Control:
        - Requires login (redirects to auth.login)
        - Parent only: is_parent must be True
        - Children redirected to profile with error message
    
    Race Condition Protection:
        @prevent_race_condition decorator (1 second interval).
    
    Returns:
        GET: profile/add_child.html with current_user.
        POST: Redirects to profile.index.
    
    Use Cases:
        - Parent wants to register child for tournaments
        - Parent adding additional children
        - Establishing judge commitment for tournaments
    
    Note:
        Matching uses first_name + last_name + phone_number for uniqueness.
        Child ghost accounts often have empty email/phone (parent may not know).
        Ghost accounts can later be claimed when child registers.
    """
    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()

    if not user_id:
        flash('Log in first!')
        return redirect_to_login()
    
    if not user.is_parent:
        flash('You are not a parent')
        return redirect(url_for('profile.index', user_id=user_id))

    
    if request.method == 'POST':

        """
        
        child first name
        child last name
        child email
        child phone number

        check if account exists
        if not exists -> make ghost account

        add child relationship


        
        """

        child_first_name = request.form.get("child_first_name").lower()
        child_last_name = request.form.get("child_last_name").lower()
        child_email = request.form.get("child_email").lower()
        child_phone = request.form.get("child_phone").lower()


        child_account = User.query.filter_by(first_name=child_first_name, last_name=child_last_name, phone_number=child_phone).first()

        if not child_account:
            create_ghost(child_first_name, child_last_name, child_email, child_phone, user)
            child_account = User.query.filter_by(first_name=child_first_name, last_name=child_last_name, phone_number=child_phone).first()

        existing_relationship = Judges.query.filter_by(judge_id=user_id, child_id=child_account.id).first()
        if not existing_relationship:
            child_relationship = Judges(
            background_check=False,
            judge_id=user_id,
            child_id=child_account.id
            )

            db.session.add(child_relationship)
            db.session.commit()

        return redirect(url_for('profile.index', user_id=user_id))
    return render_template('profile/add_child.html', current_user=user)

@profile_bp.route('/dismiss_popup/<int:popup_id>', methods=['POST'])
def dismiss_popup(popup_id):
    """Dismiss admin popup message to remove from profile display.
    
    Marks popup as completed so it no longer appears on user's profile page.
    Validates user owns the popup before dismissing (security).
    
    URL Parameters:
        popup_id (int): Popup primary key to dismiss.
    
    Methods:
        POST: Mark popup as completed (completed=True).
    
    Validation:
        - Verifies popup belongs to current user (user_id match)
        - Only matching popups can be dismissed (prevents cross-user dismissal)
        - If popup not found or user mismatch: No action, silent fail
    
    Database Changes:
        - Popup.completed: False → True
        - Popup remains in database but filtered from active queries
    
    Access Control:
        Requires login. Redirects to auth.login if not authenticated.
    
    Returns:
        Redirects to profile.index with success message.
    
    Use Cases:
        - User acknowledges admin announcement
        - User dismisses requirement notification
        - User clears completed action reminder
    
    Note:
        Dismissal is permanent (cannot be undone by user).
        Admin can delete popup record to fully remove.
        Expired popups (expires_at < now) still appear until dismissed.
    """
    if not session.get('user_id'):
        return redirect_to_login()
    
    user_id = session.get('user_id')
    popup = Popups.query.filter_by(id=popup_id, user_id=user_id).first()
    
    if popup:
        popup.completed = True
        db.session.commit()
        flash('Message dismissed.', 'success')
    
    return redirect(url_for('profile.index', user_id=user_id))