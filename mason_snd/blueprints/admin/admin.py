
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from difflib import get_close_matches
from datetime import datetime
import random
import pytz

EST = pytz.timezone('US/Eastern')

from mason_snd.extensions import db
from mason_snd.models.auth import User, Judges
from mason_snd.models.admin import User_Requirements, Requirements, Popups
from mason_snd.models.events import User_Event, Event
from mason_snd.models.tournaments import Tournament_Performance, Tournament, Tournament_Signups
from mason_snd.models.metrics import MetricsSettings
from mason_snd.models.deletion_utils import (
    delete_user_safely, delete_tournament_safely, delete_multiple_users,
    get_user_deletion_preview, get_tournament_deletion_preview,
    delete_event_safely, delete_multiple_events, get_event_deletion_preview,
    delete_requirement_safely, delete_multiple_requirements, get_requirement_deletion_preview
)

from werkzeug.security import generate_password_hash, check_password_hash

admin_bp = Blueprint('admin', __name__, template_folder='templates')

# Import testing system components
try:
    from UNIT_TEST.master_controller import MasterTestController
    from UNIT_TEST.final_verification import run_final_verification
    from UNIT_TEST.production_safety import get_safety_guard
    TESTING_AVAILABLE = True
except ImportError:
    TESTING_AVAILABLE = False

@admin_bp.route('/')
def index():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('auth.login'))
        
    user = User.query.filter_by(id=user_id).first()
    if not user or user.role <= 1:
        flash('Restricted Access!!!!!')
        return redirect(url_for('profile.index', user_id=user_id))
    return render_template('admin/index.html')


# Requirements management page
@admin_bp.route('/requirements', methods=['GET', 'POST'])
def requirements():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('auth.login'))
        
    user = User.query.filter_by(id=user_id).first()
    if not user or user.role <= 1:
        flash('Restricted Access!!!!!')
        return redirect(url_for('profile.index', user_id=user_id))

    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'create_requirement':
            # Create new requirement
            requirement_body = request.form.get('requirement_body', '').strip()
            if requirement_body:
                new_requirement = Requirements(
                    body=requirement_body,
                    active=True
                )
                db.session.add(new_requirement)
                db.session.commit()
                flash(f'Requirement "{requirement_body}" created successfully.', 'success')
            else:
                flash('Please enter a requirement description.', 'error')
                
        elif action == 'assign_requirement':
            # Assign requirement to selected users
            requirement_id = request.form.get('requirement_id')
            selected_users = request.form.getlist('selected_users')
            deadline_str = request.form.get('deadline')
            
            if requirement_id and selected_users:
                deadline = None
                if deadline_str:
                    try:
                        deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
                        deadline = EST.localize(deadline)
                    except ValueError:
                        flash('Invalid deadline format.', 'error')
                        return redirect(url_for('admin.requirements'))
                
                requirement = Requirements.query.get(requirement_id)
                assigned_count = 0
                
                for user_id_str in selected_users:
                    # Check if user already has this requirement
                    existing = User_Requirements.query.filter_by(
                        user_id=int(user_id_str),
                        requirement_id=int(requirement_id)
                    ).first()
                    
                    if not existing:
                        user_req = User_Requirements(
                            user_id=int(user_id_str),
                            requirement_id=int(requirement_id),
                            deadline=deadline
                        )
                        db.session.add(user_req)
                        assigned_count += 1
                
                db.session.commit()
                flash(f'Assigned requirement to {assigned_count} users.', 'success')
            else:
                flash('Please select a requirement and at least one user.', 'error')
                
        elif action == 'assign_to_group':
            # Assign requirement to all users in a group (children or judges)
            requirement_id = request.form.get('requirement_id')
            group_type = request.form.get('group_type')
            deadline_str = request.form.get('deadline')
            
            if requirement_id and group_type:
                deadline = None
                if deadline_str:
                    try:
                        deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
                        deadline = EST.localize(deadline)
                    except ValueError:
                        flash('Invalid deadline format.', 'error')
                        return redirect(url_for('admin.requirements'))
                
                requirement = Requirements.query.get(requirement_id)
                assigned_count = 0
                
                if group_type == 'children':
                    # Get all users who are children (have is_parent=False and have a judge relationship)
                    children = User.query.filter_by(is_parent=False).join(
                        Judges, Judges.child_id == User.id
                    ).all()
                elif group_type == 'judges':
                    # Get all users who are judges (have is_parent=True)
                    children = User.query.filter_by(is_parent=True).all()
                else:
                    flash('Invalid group type.', 'error')
                    return redirect(url_for('admin.requirements'))
                
                for user in children:
                    # Check if user already has this requirement
                    existing = User_Requirements.query.filter_by(
                        user_id=user.id,
                        requirement_id=int(requirement_id)
                    ).first()
                    
                    if not existing:
                        user_req = User_Requirements(
                            user_id=user.id,
                            requirement_id=int(requirement_id),
                            deadline=deadline
                        )
                        db.session.add(user_req)
                        assigned_count += 1
                
                db.session.commit()
                flash(f'Assigned requirement to {assigned_count} {group_type}.', 'success')
            else:
                flash('Please select a requirement and group type.', 'error')
                
        else:
            # Original toggle functionality
            requirements = Requirements.query.all()
            for req in requirements:
                active = request.form.get(f'active_{req.id}') == 'on'
                req.active = active
            db.session.commit()
            flash('Requirements updated.', 'success')
            
        return redirect(url_for('admin.requirements'))
    
    # GET request
    requirements = Requirements.query.all()
    
    # Get all users for assignment
    all_users = User.query.order_by(User.last_name, User.first_name).all()
    
    # Get children and judges counts for group assignment
    children_count = User.query.filter_by(is_parent=False).join(
        Judges, Judges.child_id == User.id
    ).count()
    judges_count = User.query.filter_by(is_parent=True).count()
    
    return render_template('admin/requirements.html', 
                         requirements=requirements,
                         all_users=all_users,
                         children_count=children_count,
                         judges_count=judges_count)


# Enhanced popup sending: select users, set expiration
@admin_bp.route('/add_popup', methods=['POST', 'GET'])
def add_popup():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('auth.login'))
        
    user = User.query.filter_by(id=user_id).first()
    if not user or user.role <= 1:
        flash('Restricted Access!!!!!')
        return redirect(url_for('profile.index', user_id=user_id))

    users = User.query.all()
    if request.method == 'POST':
        selected_user_ids = request.form.getlist('recipient_ids')
        message = request.form.get('message')
        expires_at_str = request.form.get('expires_at')
        expires_at = None
        if expires_at_str:
            try:
                expires_at = datetime.strptime(expires_at_str, "%Y-%m-%dT%H:%M")
            except Exception:
                expires_at = None
        if not selected_user_ids or not message:
            flash("Please select at least one user and enter a message.", "error")
            return redirect(url_for('admin.add_popup'))
        for uid in selected_user_ids:
            popup = Popups(
                message=message,
                user_id=uid,
                admin_id=user_id,
                expires_at=expires_at
            )
            db.session.add(popup)
        db.session.commit()
        flash("Popup(s) sent!", "success")
        return redirect(url_for('admin.add_popup'))
    return render_template('admin/add_popup.html', users=users)


# Admin view of user details
@admin_bp.route('/user/<int:user_id>', methods=['GET', 'POST'])
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    user_events = User_Event.query.filter_by(user_id=user_id).all()
    events = [Event.query.get(ue.event_id) for ue in user_events]
    tournament_points = user.tournament_points or 0
    effort_points = user.effort_points or 0
    total_points = tournament_points + effort_points
    settings = MetricsSettings.query.first()
    if not settings:
        tournament_weight, effort_weight = 0.7, 0.3
    else:
        tournament_weight, effort_weight = settings.tournament_weight, settings.effort_weight
    weighted_points = round(tournament_points * tournament_weight + effort_points * effort_weight, 2)

    # Emergency/child info
    if user.is_parent:
        child_info = {
            'first_name': user.child_first_name,
            'last_name': user.child_last_name
        }
    else:
        child_info = None
    emergency_contact = {
        'first_name': user.emergency_contact_first_name,
        'last_name': user.emergency_contact_last_name,
        'number': user.emergency_contact_number,
        'relationship': user.emergency_contact_relationship,
        'email': user.emergency_contact_email
    }

    requirements = User_Requirements.query.filter_by(user_id=user_id).all()
    all_requirements = Requirements.query.filter_by(active=True).all()

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'reset_password':
            new_password = request.form.get('new_password')
            if new_password:
                user.password = generate_password_hash(new_password)
                db.session.commit()
                flash('Password reset successfully.', 'success')
        elif action == 'assign_role':
            new_role = int(request.form.get('role', 0))
            user.role = new_role
            db.session.commit()
            flash('Role updated.', 'success')
        elif action == 'assign_requirement':
            req_id = request.form.get('assign_requirement_id')
            if req_id:
                # Only assign if not already assigned
                exists = User_Requirements.query.filter_by(user_id=user_id, requirement_id=req_id).first()
                if not exists:
                    new_ur = User_Requirements(user_id=user_id, requirement_id=req_id)
                    db.session.add(new_ur)
                    db.session.commit()
                    flash('Requirement assigned.', 'success')
                else:
                    flash('Requirement already assigned.', 'info')
        elif action == 'toggle_requirements':
            # Toggle requirements for this user
            for req in requirements:
                checked = request.form.get(f'requirement_{req.id}') == 'on'
                req.complete = checked
            db.session.commit()
            flash('Requirements updated.', 'success')
        elif action == 'add_drop':
            # Add a drop penalty to the user
            user.drops += 1
            db.session.commit()
            flash(f'Drop penalty added. User now has {user.drops} drops.', 'warning')
        return redirect(url_for('admin.user_detail', user_id=user_id))

    return render_template(
        'admin/user_detail.html',
        user=user,
        events=events,
        tournament_points=tournament_points,
        effort_points=effort_points,
        total_points=total_points,
        weighted_points=weighted_points,
        emergency_contact=emergency_contact,
        child_info=child_info,
        requirements=requirements,
        all_requirements=all_requirements
    )

# Fuzzy search for users by name
@admin_bp.route('/search', methods=['GET', 'POST'])
def search():
    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()
    print(user)

    results = []
    query = ''
    if request.method == 'POST':
        query = request.form.get('name', '').strip().lower()
        if query:
            # Get all users and their full names
            users = User.query.all()
            
            # Add judge/child relationship information to each user
            for u in users:
                # Check if user is a child (has entries in Judges table as child_id)
                child_entries = Judges.query.filter_by(child_id=u.id).all()
                u.child_entries = child_entries
                
            user_map = {f"{u.first_name.lower()} {u.last_name.lower()}": u for u in users}
            names = list(user_map.keys())
            # Use difflib to get close matches
            close = get_close_matches(query, names, n=10, cutoff=0.0)  # cutoff=0.0 for all, sorted by similarity
            # If no close matches, show all users
            if not close:
                close = names
            results = [(user_map[name], name) for name in close]
    return render_template('admin/search.html', results=results, query=query)


# Quick add drop penalty from search page
@admin_bp.route('/add_drop/<int:user_id>', methods=['POST'])
def add_drop(user_id):
    admin_user_id = session.get('user_id')
    if not admin_user_id:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('auth.login'))
        
    admin_user = User.query.filter_by(id=admin_user_id).first()
    if not admin_user or admin_user.role <= 1:
        flash('Restricted Access!!!!!')
        return redirect(url_for('profile.index', user_id=admin_user_id))

    user = User.query.get_or_404(user_id)
    user.drops += 1
    db.session.commit()
    flash(f'Drop penalty added to {user.first_name} {user.last_name}. They now have {user.drops} drops.', 'warning')
    return redirect(url_for('admin.search'))


# Events management
@admin_bp.route('/events_management')
def events_management():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('auth.login'))
        
    user = User.query.filter_by(id=user_id).first()
    if not user or user.role <= 1:
        flash('Restricted Access!!!!!')
        return redirect(url_for('profile.index', user_id=user_id))

    events = Event.query.all()
    
    # Get participant counts for each event
    event_stats = {}
    for event in events:
        participant_count = User_Event.query.filter_by(event_id=event.id).count()
        active_participants = User_Event.query.filter_by(event_id=event.id, active=True).count()
        event_stats[event.id] = {
            'total_participants': participant_count,
            'active_participants': active_participants
        }
    
    return render_template('admin/events_management.html', events=events, event_stats=event_stats)


# Change event leader
@admin_bp.route('/change_event_leader/<int:event_id>', methods=['GET', 'POST'])
def change_event_leader(event_id):
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('auth.login'))
        
    user = User.query.filter_by(id=user_id).first()
    if not user or user.role <= 1:
        flash('Restricted Access!!!!!')
        return redirect(url_for('profile.index', user_id=user_id))

    event = Event.query.get_or_404(event_id)
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'search_leader':
            # Search for new leader
            search_query = request.form.get('search_query', '').strip().lower()
            search_results = []
            
            if search_query:
                # Get all users and their full names
                users = User.query.all()
                
                # Add judge/child relationship information to each user
                for u in users:
                    # Check if user is a child (has entries in Judges table as child_id)
                    child_entries = Judges.query.filter_by(child_id=u.id).all()
                    u.child_entries = child_entries
                    
                user_map = {f"{u.first_name.lower()} {u.last_name.lower()}": u for u in users}
                names = list(user_map.keys())
                # Use difflib to get close matches
                close = get_close_matches(search_query, names, n=10, cutoff=0.0)
                search_results = [(user_map[name], name) for name in close]
            
            return render_template('admin/change_event_leader.html', 
                                 event=event, 
                                 search_query=search_query,
                                 search_results=search_results)
        
        elif action == 'assign_leader':
            # Assign new leader
            new_leader_id = request.form.get('new_leader_id')
            if new_leader_id:
                old_leader = User.query.get(event.owner_id) if event.owner_id else None
                new_leader = User.query.get(new_leader_id)
                
                if new_leader:
                    event.owner_id = new_leader_id
                    db.session.commit()
                    
                    old_leader_name = f"{old_leader.first_name} {old_leader.last_name}" if old_leader else "None"
                    new_leader_name = f"{new_leader.first_name} {new_leader.last_name}"
                    
                    flash(f'Event leader changed from {old_leader_name} to {new_leader_name}', 'success')
                    return redirect(url_for('admin.events_management'))
                else:
                    flash('Selected user not found', 'error')
            else:
                flash('Please select a new leader', 'error')
        
        elif action == 'remove_leader':
            # Remove current leader
            old_leader = User.query.get(event.owner_id) if event.owner_id else None
            event.owner_id = None
            db.session.commit()
            
            old_leader_name = f"{old_leader.first_name} {old_leader.last_name}" if old_leader else "None"
            flash(f'Removed {old_leader_name} as event leader', 'success')
            return redirect(url_for('admin.events_management'))
    
    return render_template('admin/change_event_leader.html', event=event)


@admin_bp.route('/test_data', methods=['GET', 'POST'])
def test_data():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('auth.login'))
        
    user = User.query.filter_by(id=user_id).first()
    if not user or user.role <= 1:
        flash('Restricted Access!!!!!')
        return redirect(url_for('profile.index', user_id=user_id))

    if request.method == 'POST':
        action = request.form.get('action')
        password = request.form.get('password', 'testpass123')
        
        if action == 'create_users':
            created_students = []
            created_parents = []
            
            try:
                # Create 15 test students and their parents
                for i in range(1, 16):
                    # Create student
                    student = User(
                        first_name=f'Student{i}',
                        last_name='Test',
                        email=f'student{i}@gmail.com',
                        password=generate_password_hash(password),
                        phone_number=f'555-000-{1000+i}',
                        is_parent=False,
                        role=0,
                        emergency_contact_first_name=f'Parent{i}',
                        emergency_contact_last_name='Test',
                        emergency_contact_number=f'555-100-{1000+i}',
                        emergency_contact_relationship='Parent',
                        emergency_contact_email=f'parent{i}@gmail.com',
                        account_claimed=True
                    )
                    db.session.add(student)
                    db.session.flush()  # Get the ID
                    
                    # Create parent
                    parent = User(
                        first_name=f'Parent{i}',
                        last_name='Test',
                        email=f'parent{i}@gmail.com',
                        password=generate_password_hash(password),
                        phone_number=f'555-100-{1000+i}',
                        is_parent=True,
                        role=0,
                        child_first_name=f'Student{i}',
                        child_last_name='Test',
                        account_claimed=True
                    )
                    db.session.add(parent)
                    db.session.flush()  # Get the ID
                    
                    # Create judge relationship
                    judge_rel = Judges(
                        judge_id=parent.id,
                        child_id=student.id,
                        background_check=True
                    )
                    db.session.add(judge_rel)
                    
                    created_students.append(student.id)
                    created_parents.append(parent.id)
                
                db.session.commit()
                flash(f'Successfully created 15 test students and 15 test parents with password: {password}', 'success')
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error creating test users: {str(e)}', 'error')
        
        elif action == 'join_events':
            # Get all test students
            test_students = User.query.filter(
                User.first_name.like('Student%'),
                User.last_name == 'Test'
            ).all()
            
            # Get all events
            events = Event.query.all()
            
            if not events:
                flash('No events found to join', 'error')
                return redirect(url_for('admin.test_data'))
            
            try:
                for student in test_students:
                    # Join 1-3 random events
                    num_events = random.randint(1, min(3, len(events)))
                    selected_events = random.sample(events, num_events)
                    
                    for event in selected_events:
                        # Check if already joined
                        existing = User_Event.query.filter_by(
                            user_id=student.id,
                            event_id=event.id
                        ).first()
                        
                        if not existing:
                            user_event = User_Event(
                                user_id=student.id,
                                event_id=event.id,
                                active=True
                            )
                            db.session.add(user_event)
                
                db.session.commit()
                flash(f'Successfully enrolled {len(test_students)} test students in random events', 'success')
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error enrolling students in events: {str(e)}', 'error')
        
        elif action == 'signup_tournaments':
            # Get all test students
            test_students = User.query.filter(
                User.first_name.like('Student%'),
                User.last_name == 'Test'
            ).all()
            
            # Get all tournaments
            tournaments = Tournament.query.all()
            
            if not tournaments:
                flash('No tournaments found to sign up for', 'error')
                return redirect(url_for('admin.test_data'))
            
            try:
                for student in test_students:
                    # Get student's events
                    student_events = User_Event.query.filter_by(user_id=student.id, active=True).all()
                    
                    if not student_events:
                        continue
                    
                    # Sign up for 1-2 random tournaments
                    num_tournaments = random.randint(1, min(2, len(tournaments)))
                    selected_tournaments = random.sample(tournaments, num_tournaments)
                    
                    # Get parent for judge
                    parent = User.query.filter(
                        User.child_first_name == student.first_name,
                        User.child_last_name == student.last_name,
                        User.is_parent == True
                    ).first()
                    
                    for tournament in selected_tournaments:
                        # Pick a random event from student's events
                        event = random.choice(student_events).event
                        
                        # Check if already signed up
                        existing = Tournament_Signups.query.filter_by(
                            user_id=student.id,
                            tournament_id=tournament.id,
                            event_id=event.id
                        ).first()
                        
                        if not existing:
                            signup = Tournament_Signups(
                                user_id=student.id,
                                tournament_id=tournament.id,
                                event_id=event.id,
                                bringing_judge=True if parent else False,
                                judge_id=parent.id if parent else None,
                                is_going=True
                            )
                            db.session.add(signup)
                
                db.session.commit()
                flash(f'Successfully signed up {len(test_students)} test students for random tournaments', 'success')
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error signing up students for tournaments: {str(e)}', 'error')
        
        elif action == 'cleanup':
            try:
                # Delete all test data
                test_students = User.query.filter(
                    User.first_name.like('Student%'),
                    User.last_name == 'Test'
                ).all()
                
                test_parents = User.query.filter(
                    User.first_name.like('Parent%'),
                    User.last_name == 'Test'
                ).all()
                
                # Delete related records first
                for student in test_students:
                    User_Event.query.filter_by(user_id=student.id).delete()
                    Tournament_Signups.query.filter_by(user_id=student.id).delete()
                    User_Requirements.query.filter_by(user_id=student.id).delete()
                    Judges.query.filter_by(child_id=student.id).delete()
                
                for parent in test_parents:
                    Tournament_Signups.query.filter_by(judge_id=parent.id).delete()
                    User_Requirements.query.filter_by(user_id=parent.id).delete()
                    Judges.query.filter_by(judge_id=parent.id).delete()
                
                # Delete users
                for student in test_students:
                    db.session.delete(student)
                for parent in test_parents:
                    db.session.delete(parent)
                
                db.session.commit()
                flash('Successfully cleaned up all test data', 'success')
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error cleaning up test data: {str(e)}', 'error')
    
    # Get current test data stats
    test_students = User.query.filter(
        User.first_name.like('Student%'),
        User.last_name == 'Test'
    ).all()
    
    test_parents = User.query.filter(
        User.first_name.like('Parent%'),
        User.last_name == 'Test'
    ).all()
    
    # Count event enrollments
    event_enrollments = 0
    tournament_signups = 0
    for student in test_students:
        event_enrollments += User_Event.query.filter_by(user_id=student.id).count()
        tournament_signups += Tournament_Signups.query.filter_by(user_id=student.id).count()
    
    stats = {
        'students': len(test_students),
        'parents': len(test_parents),
        'event_enrollments': event_enrollments,
        'tournament_signups': tournament_signups
    }
    
    return render_template('admin/test_data.html', stats=stats)


# User and Tournament Deletion Routes

@admin_bp.route('/delete_management')
def delete_management():
    """Main page for deletion management"""
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('auth.login'))
        
    user = User.query.filter_by(id=user_id).first()
    if not user or user.role <= 1:
        flash('Restricted Access!!!!!')
        return redirect(url_for('profile.index', user_id=user_id))
    
    return render_template('admin/delete_management.html')

@admin_bp.route('/delete_users', methods=['GET', 'POST'])
def delete_users():
    """User deletion interface with search and bulk selection"""
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('auth.login'))
        
    user = User.query.filter_by(id=user_id).first()
    if not user or user.role <= 1:
        flash('Restricted Access!!!!!')
        return redirect(url_for('profile.index', user_id=user_id))
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'preview':
            # Get preview for selected users
            selected_user_ids = request.form.getlist('selected_users')
            if not selected_user_ids:
                flash('Please select at least one user.', 'error')
                return redirect(url_for('admin.delete_users'))
            
            # Convert to integers for easier comparison
            user_ids = [int(uid) for uid in selected_user_ids]
            
            # Don't allow deleting yourself - check if current user is in the list
            current_user_id = session.get('user_id')
            if current_user_id in user_ids:
                flash('You cannot delete your own account. Please remove yourself from the selection.', 'error')
                return redirect(url_for('admin.delete_users'))
            
            previews = []
            for uid in user_ids:
                preview = get_user_deletion_preview(uid)
                if preview:
                    previews.append(preview)
            
            return render_template('admin/delete_users_preview.html', 
                                 previews=previews, 
                                 selected_user_ids=selected_user_ids)
        
        elif action == 'confirm_delete':
            # Perform actual deletion
            selected_user_ids = request.form.getlist('confirmed_user_ids')
            if not selected_user_ids:
                flash('No users selected for deletion.', 'error')
                return redirect(url_for('admin.delete_users'))
            
            # Convert to integers
            user_ids = [int(uid) for uid in selected_user_ids]
            
            # Don't allow deleting yourself - check if current user is in the list
            current_user_id = session.get('user_id')
            if current_user_id in user_ids:
                flash('You cannot delete your own account. Please remove yourself from the selection.', 'error')
                return redirect(url_for('admin.delete_users'))
            
            # Perform deletion
            result = delete_multiple_users(user_ids)
            
            if result.success:
                flash(f'Successfully deleted {len(user_ids)} users and all related data. {result.get_summary()}', 'success')
            else:
                flash(f'Deletion completed with errors: {"; ".join(result.errors)}', 'error')
            
            return redirect(url_for('admin.delete_users'))
    
    # GET request - show user search/selection interface
    search_query = request.args.get('search', '')
    users = []
    
    if search_query:
        users = User.query.filter(
            db.or_(
                User.first_name.contains(search_query),
                User.last_name.contains(search_query),
                User.email.contains(search_query)
            )
        ).limit(50).all()
        
        # Add judge/child relationship information to each user
        for u in users:
            # Check if user is a child (has entries in Judges table as child_id)
            child_entries = Judges.query.filter_by(child_id=u.id).all()
            u.child_entries = child_entries
    
    return render_template('admin/delete_users.html', 
                         users=users, 
                         search_query=search_query,
                         current_user_id=session.get('user_id'))

@admin_bp.route('/delete_tournaments', methods=['GET', 'POST'])
def delete_tournaments():
    """Tournament deletion interface"""
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('auth.login'))
        
    user = User.query.filter_by(id=user_id).first()
    if not user or user.role <= 1:
        flash('Restricted Access!!!!!')
        return redirect(url_for('profile.index', user_id=user_id))
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'preview':
            # Get preview for selected tournament
            tournament_id = request.form.get('tournament_id')
            if not tournament_id:
                flash('Please select a tournament.', 'error')
                return redirect(url_for('admin.delete_tournaments'))
            
            preview = get_tournament_deletion_preview(int(tournament_id))
            if not preview:
                flash('Tournament not found.', 'error')
                return redirect(url_for('admin.delete_tournaments'))
            
            return render_template('admin/delete_tournament_preview.html', 
                                 preview=preview, 
                                 tournament_id=tournament_id)
        
        elif action == 'confirm_delete':
            # Perform actual deletion
            tournament_id = request.form.get('confirmed_tournament_id')
            if not tournament_id:
                flash('No tournament selected for deletion.', 'error')
                return redirect(url_for('admin.delete_tournaments'))
            
            # Perform deletion
            result = delete_tournament_safely(int(tournament_id))
            
            if result.success:
                flash(f'Successfully deleted tournament and all related data. {result.get_summary()}', 'success')
            else:
                flash(f'Deletion failed: {"; ".join(result.errors)}', 'error')
            
            return redirect(url_for('admin.delete_tournaments'))
    
    # GET request - show tournament selection interface
    tournaments = Tournament.query.order_by(Tournament.date.desc()).all()
    return render_template('admin/delete_tournaments.html', tournaments=tournaments)

@admin_bp.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_single_user(user_id):
    """Quick delete for a single user (from user detail page)"""
    current_user_id = session.get('user_id')
    if not current_user_id:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('auth.login'))
        
    current_user = User.query.filter_by(id=current_user_id).first()
    if not current_user or current_user.role <= 1:
        flash('Restricted Access!!!!!')
        return redirect(url_for('profile.index', user_id=current_user_id))
    
    # Don't allow deleting yourself
    if user_id == current_user_id:
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('admin.user_detail', user_id=user_id))
    
    result = delete_user_safely(user_id)
    
    if result.success:
        flash(f'User successfully deleted. {result.get_summary()}', 'success')
        return redirect(url_for('admin.delete_users'))
    else:
        flash(f'Failed to delete user: {"; ".join(result.errors)}', 'error')
        return redirect(url_for('admin.user_detail', user_id=user_id))

@admin_bp.route('/delete_events', methods=['GET', 'POST'])
def delete_events():
    """Event deletion interface"""
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('auth.login'))
        
    user = User.query.filter_by(id=user_id).first()
    if not user or user.role <= 1:
        flash('Restricted Access!!!!!')
        return redirect(url_for('profile.index', user_id=user_id))
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'preview':
            # Get preview for selected events
            selected_event_ids = request.form.getlist('selected_events')
            if not selected_event_ids:
                flash('Please select at least one event.', 'error')
                return redirect(url_for('admin.delete_events'))
            
            previews = []
            for eid in selected_event_ids:
                preview = get_event_deletion_preview(int(eid))
                if preview:
                    previews.append(preview)
            
            return render_template('admin/delete_events_preview.html', 
                                 previews=previews, 
                                 selected_event_ids=selected_event_ids)
        
        elif action == 'confirm_delete':
            # Perform actual deletion
            selected_event_ids = request.form.getlist('confirmed_event_ids')
            if not selected_event_ids:
                flash('No events selected for deletion.', 'error')
                return redirect(url_for('admin.delete_events'))
            
            # Convert to integers
            event_ids = [int(eid) for eid in selected_event_ids]
            
            # Perform deletion
            result = delete_multiple_events(event_ids)
            
            if result.success:
                flash(f'Successfully deleted {len(event_ids)} events and all related data. {result.get_summary()}', 'success')
            else:
                flash(f'Deletion completed with errors: {"; ".join(result.errors)}', 'error')
            
            return redirect(url_for('admin.delete_events'))
    
    # GET request - show event selection interface
    events = Event.query.order_by(Event.event_name).all()
    return render_template('admin/delete_events.html', events=events)

@admin_bp.route('/delete_requirements', methods=['GET', 'POST'])
def delete_requirements():
    """Requirements deletion interface"""
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('auth.login'))
        
    user = User.query.filter_by(id=user_id).first()
    if not user or user.role <= 1:
        flash('Restricted Access!!!!!')
        return redirect(url_for('profile.index', user_id=user_id))
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'preview':
            requirement_ids = request.form.getlist('requirement_ids')
            if not requirement_ids:
                flash('Please select at least one requirement to delete.', 'error')
                return redirect(url_for('admin.delete_requirements'))
            
            # Get preview data for all selected requirements
            previews = []
            for req_id in requirement_ids:
                preview = get_requirement_deletion_preview(int(req_id))
                if preview:
                    previews.append(preview)
            
            return render_template('admin/delete_requirements_preview.html', 
                                 previews=previews, 
                                 requirement_ids=requirement_ids)
        
        elif action == 'confirm_delete':
            requirement_ids = request.form.getlist('requirement_ids')
            result = delete_multiple_requirements([int(req_id) for req_id in requirement_ids])
            
            if result.success:
                flash(f'Successfully deleted {len(requirement_ids)} requirements. {result.get_summary()}', 'success')
            else:
                flash(f'Deletion failed: {"; ".join(result.errors)}', 'error')
            
            return redirect(url_for('admin.delete_requirements'))
    
    # GET request - show requirement selection interface
    requirements = Requirements.query.order_by(Requirements.body).all()
    return render_template('admin/delete_requirements.html', requirements=requirements)

@admin_bp.route('/view_requirement_assignments/<int:requirement_id>')
def view_requirement_assignments(requirement_id):
    """View all users assigned to a specific requirement"""
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('auth.login'))
        
    user = User.query.filter_by(id=user_id).first()
    if not user or user.role <= 1:
        flash('Restricted Access!!!!!')
        return redirect(url_for('profile.index', user_id=user_id))
    
    requirement = Requirements.query.get_or_404(requirement_id)
    
    # Get all user requirements for this requirement
    user_requirements = User_Requirements.query.filter_by(requirement_id=requirement_id).all()
    
    # Get assignment statistics
    total_assigned = len(user_requirements)
    completed_count = sum(1 for ur in user_requirements if ur.complete)
    overdue_count = sum(1 for ur in user_requirements 
                       if ur.deadline and ur.deadline < datetime.now(EST) and not ur.complete)
    
    return render_template('admin/view_requirement_assignments.html',
                         requirement=requirement,
                         user_requirements=user_requirements,
                         total_assigned=total_assigned,
                         completed_count=completed_count,
                         overdue_count=overdue_count,
                         now=datetime.now(EST))


# Testing System Integration Routes

@admin_bp.route('/testing_suite')
def testing_suite():
    """Main testing suite dashboard for admins"""
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('auth.login'))
        
    user = User.query.filter_by(id=user_id).first()
    if not user or user.role <= 1:
        flash('Restricted Access!!!!!')
        return redirect(url_for('profile.index', user_id=user_id))
    
    if not TESTING_AVAILABLE:
        flash('Testing system is not available. Please check installation.', 'error')
        return redirect(url_for('admin.index'))
    
    # Get testing system status
    try:
        safety_guard = get_safety_guard()
        safety_report = safety_guard.generate_safety_report()
        
        test_status = {
            'safety_status': safety_report['safety_status'],
            'production_protected': safety_report['production_database']['integrity_check']['safe'],
            'test_resources': safety_report['test_resources']['total_test_resources']
        }
    except Exception as e:
        test_status = {
            'safety_status': 'ERROR',
            'production_protected': False,
            'test_resources': 0,
            'error': str(e)
        }
    
    return render_template('admin/testing_suite.html', 
                         test_status=test_status,
                         testing_available=TESTING_AVAILABLE)

@admin_bp.route('/testing_suite/run_quick_test', methods=['POST'])
def run_quick_test():
    """Run quick test suite"""
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('auth.login'))
        
    user = User.query.filter_by(id=user_id).first()
    if not user or user.role <= 1:
        flash('Restricted Access!!!!!')
        return redirect(url_for('profile.index', user_id=user_id))
    
    if not TESTING_AVAILABLE:
        flash('Testing system is not available.', 'error')
        return redirect(url_for('admin.testing_suite'))
    
    try:
        # Run quick test
        controller = MasterTestController()
        
        quick_config = {
            'num_users': 5,
            'num_events': 2,
            'num_tournaments': 1,
            'run_unit_tests': True,
            'run_simulation': True,
            'run_roster_tests': True,
            'run_metrics_tests': True,
            'cleanup_after': True
        }
        
        results = controller.run_comprehensive_test_suite(quick_config)
        
        if results.get('overall_success', False):
            flash('✅ Quick test completed successfully! All systems operational.', 'success')
        else:
            flash('⚠️ Quick test completed with issues. Check test results for details.', 'warning')
        
        # Store results in session for display
        session['last_test_results'] = {
            'timestamp': datetime.now().isoformat(),
            'overall_success': results.get('overall_success', False),
            'duration': results.get('duration', 0),
            'test_summary': results.get('test_results', {}).get('report', {}).get('summary', {})
        }
        
    except Exception as e:
        flash(f'❌ Test execution failed: {str(e)}', 'error')
    
    return redirect(url_for('admin.testing_suite'))

@admin_bp.route('/testing_suite/run_full_test', methods=['POST'])
def run_full_test():
    """Run full test suite"""
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('auth.login'))
        
    user = User.query.filter_by(id=user_id).first()
    if not user or user.role <= 1:
        flash('Restricted Access!!!!!')
        return redirect(url_for('profile.index', user_id=user_id))
    
    if not TESTING_AVAILABLE:
        flash('Testing system is not available.', 'error')
        return redirect(url_for('admin.testing_suite'))
    
    try:
        # Run full test suite
        controller = MasterTestController()
        
        full_config = {
            'num_users': 30,
            'num_events': 5,
            'num_tournaments': 3,
            'run_unit_tests': True,
            'run_simulation': True,
            'run_roster_tests': True,
            'run_metrics_tests': True,
            'cleanup_after': True
        }
        
        results = controller.run_comprehensive_test_suite(full_config)
        
        if results.get('overall_success', False):
            flash('✅ Full test suite completed successfully! System is production-ready.', 'success')
        else:
            flash('⚠️ Full test suite completed with issues. Review detailed results.', 'warning')
        
        # Store results in session for display
        session['last_test_results'] = {
            'timestamp': datetime.now().isoformat(),
            'overall_success': results.get('overall_success', False),
            'duration': results.get('duration', 0),
            'test_summary': results.get('test_results', {}).get('report', {}).get('summary', {}),
            'detailed_results': results.get('test_results', {})
        }
        
    except Exception as e:
        flash(f'❌ Full test execution failed: {str(e)}', 'error')
    
    return redirect(url_for('admin.testing_suite'))

@admin_bp.route('/testing_suite/verify_system', methods=['POST'])
def verify_system():
    """Run system verification"""
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('auth.login'))
        
    user = User.query.filter_by(id=user_id).first()
    if not user or user.role <= 1:
        flash('Restricted Access!!!!!')
        return redirect(url_for('profile.index', user_id=user_id))
    
    if not TESTING_AVAILABLE:
        flash('Testing system is not available.', 'error')
        return redirect(url_for('admin.testing_suite'))
    
    try:
        # Run system verification
        verification_results = run_final_verification()
        
        success_rate = 0
        if verification_results.get('tests'):
            total_tests = len(verification_results['tests'])
            successful_tests = sum(1 for test in verification_results['tests'].values() 
                                 if test.get('success', False))
            success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
        
        if success_rate >= 90:
            flash(f'✅ System verification passed! Success rate: {success_rate:.1f}%', 'success')
        elif success_rate >= 70:
            flash(f'⚠️ System verification completed with warnings. Success rate: {success_rate:.1f}%', 'warning')
        else:
            flash(f'❌ System verification failed. Success rate: {success_rate:.1f}%', 'error')
        
        # Store verification results
        session['last_verification_results'] = {
            'timestamp': datetime.now().isoformat(),
            'success_rate': success_rate,
            'overall_success': verification_results.get('overall_success', False),
            'tests': verification_results.get('tests', {}),
            'recommendations': verification_results.get('recommendations', [])
        }
        
    except Exception as e:
        flash(f'❌ System verification failed: {str(e)}', 'error')
    
    return redirect(url_for('admin.testing_suite'))

@admin_bp.route('/testing_suite/cleanup', methods=['POST'])
def cleanup_test_data():
    """Emergency cleanup of all test data"""
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('auth.login'))
        
    user = User.query.filter_by(id=user_id).first()
    if not user or user.role <= 1:
        flash('Restricted Access!!!!!')
        return redirect(url_for('profile.index', user_id=user_id))
    
    if not TESTING_AVAILABLE:
        flash('Testing system is not available.', 'error')
        return redirect(url_for('admin.testing_suite'))
    
    try:
        # Perform emergency cleanup
        safety_guard = get_safety_guard()
        cleanup_results = safety_guard.emergency_cleanup()
        
        total_cleaned = cleanup_results.get('test_databases_removed', 0) + cleanup_results.get('temp_directories_removed', 0)
        
        if cleanup_results.get('errors'):
            flash(f'⚠️ Cleanup completed with {len(cleanup_results["errors"])} errors. {total_cleaned} items cleaned.', 'warning')
        else:
            flash(f'✅ Emergency cleanup completed successfully. {total_cleaned} test resources removed.', 'success')
        
        # Store cleanup results
        session['last_cleanup_results'] = {
            'timestamp': datetime.now().isoformat(),
            'items_cleaned': total_cleaned,
            'errors': cleanup_results.get('errors', [])
        }
        
    except Exception as e:
        flash(f'❌ Emergency cleanup failed: {str(e)}', 'error')
    
    return redirect(url_for('admin.testing_suite'))

@admin_bp.route('/testing_suite/results')
def test_results():
    """View detailed test results"""
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('auth.login'))
        
    user = User.query.filter_by(id=user_id).first()
    if not user or user.role <= 1:
        flash('Restricted Access!!!!!')
        return redirect(url_for('profile.index', user_id=user_id))
    
    # Get results from session
    test_results = session.get('last_test_results')
    verification_results = session.get('last_verification_results')
    cleanup_results = session.get('last_cleanup_results')
    
    return render_template('admin/test_results.html',
                         test_results=test_results,
                         verification_results=verification_results,
                         cleanup_results=cleanup_results)
