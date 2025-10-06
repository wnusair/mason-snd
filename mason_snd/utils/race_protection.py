"""
Race condition protection utilities for form submissions.

This module provides mechanisms to prevent race conditions during critical database operations,
particularly during form submissions like registration, tournament signup, and other user actions.
"""

from functools import wraps
from flask import request, flash, redirect, url_for, session
from sqlalchemy import exc
from sqlalchemy.orm import Session
import hashlib
import time
from threading import Lock
from collections import defaultdict
from datetime import datetime, timedelta

# In-memory lock store for form submission tracking
# Format: {user_id: {form_type: {'lock': Lock(), 'last_submit': timestamp}}}
_submission_locks = defaultdict(lambda: defaultdict(lambda: {'lock': Lock(), 'last_submit': 0}))

# Cleanup old locks periodically (locks older than 1 hour)
_lock_cleanup_interval = 3600  # 1 hour
_last_cleanup = time.time()


def _cleanup_old_locks():
    """Remove locks that haven't been used in over an hour."""
    global _last_cleanup
    current_time = time.time()
    
    if current_time - _last_cleanup < _lock_cleanup_interval:
        return
    
    # Find and remove old locks
    cutoff_time = current_time - _lock_cleanup_interval
    user_ids_to_remove = []
    
    for user_id, form_locks in _submission_locks.items():
        form_types_to_remove = []
        for form_type, lock_info in form_locks.items():
            if lock_info['last_submit'] < cutoff_time:
                form_types_to_remove.append(form_type)
        
        for form_type in form_types_to_remove:
            del form_locks[form_type]
        
        if not form_locks:
            user_ids_to_remove.append(user_id)
    
    for user_id in user_ids_to_remove:
        del _submission_locks[user_id]
    
    _last_cleanup = current_time


def _generate_form_hash(form_data, exclude_fields=None):
    """
    Generate a hash of form data to detect duplicate submissions.
    
    Args:
        form_data: The form data dictionary
        exclude_fields: List of fields to exclude from hash (e.g., timestamps, CSRF tokens)
    
    Returns:
        str: SHA256 hash of the form data
    """
    exclude_fields = exclude_fields or ['csrf_token', 'submit', '_']
    
    # Create a sorted string representation of form data
    form_items = []
    for key, value in sorted(form_data.items()):
        if key not in exclude_fields:
            if isinstance(value, list):
                form_items.append(f"{key}={'|'.join(sorted(str(v) for v in value))}")
            else:
                form_items.append(f"{key}={value}")
    
    form_string = '&'.join(form_items)
    return hashlib.sha256(form_string.encode()).hexdigest()


def prevent_race_condition(form_type, min_interval=1.0, use_form_hash=True, redirect_on_duplicate=None):
    """
    Decorator to prevent race conditions on form submissions.
    
    Args:
        form_type (str): Identifier for the form type (e.g., 'registration', 'tournament_signup')
        min_interval (float): Minimum seconds between submissions for same user/form
        use_form_hash (bool): Whether to check for exact duplicate form data
        redirect_on_duplicate (function): Optional function that returns a redirect response
                                         Signature: (user_id, form_data) -> Response
    
    Usage:
        @prevent_race_condition('registration', min_interval=2.0)
        @auth_bp.route('/register', methods=['POST'])
        def register():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Only protect POST requests
            if request.method != 'POST':
                return func(*args, **kwargs)
            
            # Clean up old locks periodically
            _cleanup_old_locks()
            
            # Get user ID from session
            user_id = session.get('user_id')
            if not user_id:
                # For routes like registration where user isn't logged in,
                # use IP address as identifier
                user_id = f"ip_{request.remote_addr}"
            
            # Get the lock for this user/form combination
            lock_info = _submission_locks[user_id][form_type]
            lock = lock_info['lock']
            
            # Try to acquire the lock (non-blocking)
            if not lock.acquire(blocking=False):
                flash(f"Please wait - your previous {form_type.replace('_', ' ')} is still being processed.", "warning")
                if redirect_on_duplicate:
                    return redirect_on_duplicate(user_id, request.form)
                return redirect(request.referrer or url_for('main.index'))
            
            try:
                current_time = time.time()
                last_submit = lock_info['last_submit']
                
                # Check minimum interval between submissions
                if current_time - last_submit < min_interval:
                    time_left = min_interval - (current_time - last_submit)
                    flash(f"Please wait {time_left:.1f} more seconds before submitting again.", "warning")
                    if redirect_on_duplicate:
                        return redirect_on_duplicate(user_id, request.form)
                    return redirect(request.referrer or url_for('main.index'))
                
                # Check for exact duplicate form data if enabled
                if use_form_hash and hasattr(lock_info, 'last_hash'):
                    current_hash = _generate_form_hash(request.form.to_dict(flat=False))
                    if lock_info.get('last_hash') == current_hash and current_time - last_submit < 60:
                        flash(f"This {form_type.replace('_', ' ')} was already submitted. Please wait before resubmitting.", "warning")
                        if redirect_on_duplicate:
                            return redirect_on_duplicate(user_id, request.form)
                        return redirect(request.referrer or url_for('main.index'))
                    lock_info['last_hash'] = current_hash
                
                # Update last submission time
                lock_info['last_submit'] = current_time
                
                # Execute the actual route function
                try:
                    result = func(*args, **kwargs)
                    return result
                except exc.IntegrityError as e:
                    # Handle database integrity errors (duplicate keys, etc.)
                    from mason_snd.extensions import db
                    db.session.rollback()
                    
                    # Check if it's a duplicate entry error
                    error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
                    if 'UNIQUE constraint failed' in error_msg or 'duplicate key' in error_msg.lower():
                        flash(f"This {form_type.replace('_', ' ')} already exists. Please check your data.", "error")
                    else:
                        flash(f"A database error occurred. Please try again.", "error")
                    
                    if redirect_on_duplicate:
                        return redirect_on_duplicate(user_id, request.form)
                    return redirect(request.referrer or url_for('main.index'))
                
            finally:
                # Always release the lock
                lock.release()
        
        return wrapper
    return decorator


def with_optimistic_locking(model_class, record_id_param='id'):
    """
    Decorator for routes that implement optimistic locking using a version field.
    
    This requires the model to have a 'version' column that gets incremented on each update.
    
    Args:
        model_class: The SQLAlchemy model class
        record_id_param: The request parameter name for the record ID
    
    Usage:
        @with_optimistic_locking(Tournament, 'tournament_id')
        @tournaments_bp.route('/edit/<int:tournament_id>', methods=['POST'])
        def edit_tournament(tournament_id):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if request.method != 'POST':
                return func(*args, **kwargs)
            
            # Get the record ID
            record_id = kwargs.get(record_id_param) or request.form.get(record_id_param)
            if not record_id:
                flash("Invalid request - missing record ID", "error")
                return redirect(request.referrer or url_for('main.index'))
            
            # Get the version from form
            expected_version = request.form.get('version')
            if expected_version:
                expected_version = int(expected_version)
                
                # Check current version in database
                record = model_class.query.get(record_id)
                if record and hasattr(record, 'version'):
                    if record.version != expected_version:
                        flash("This record was modified by another user. Please refresh and try again.", "warning")
                        return redirect(request.referrer or url_for('main.index'))
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_unique_constraint(check_func, error_message=None):
    """
    Decorator to check for uniqueness before processing a form.
    
    Args:
        check_func: Function that takes request.form and returns True if constraint is violated
        error_message: Custom error message to display
    
    Usage:
        def check_duplicate_signup(form_data):
            user_id = session.get('user_id')
            tournament_id = form_data.get('tournament_id')
            event_id = form_data.get('event_id')
            return Tournament_Signups.query.filter_by(
                user_id=user_id, tournament_id=tournament_id, event_id=event_id
            ).first() is not None
        
        @require_unique_constraint(check_duplicate_signup, "You are already signed up for this event")
        @tournaments_bp.route('/signup', methods=['POST'])
        def signup():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if request.method != 'POST':
                return func(*args, **kwargs)
            
            if check_func(request.form):
                msg = error_message or "This action has already been completed."
                flash(msg, "warning")
                return redirect(request.referrer or url_for('main.index'))
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


# Database transaction helpers

def safe_commit(db_session, on_error=None):
    """
    Safely commit a database transaction with rollback on error.
    
    Args:
        db_session: The SQLAlchemy session
        on_error: Optional callback function to execute on error
    
    Returns:
        bool: True if commit succeeded, False otherwise
    """
    try:
        db_session.commit()
        return True
    except exc.IntegrityError as e:
        db_session.rollback()
        if on_error:
            on_error(e)
        return False
    except Exception as e:
        db_session.rollback()
        if on_error:
            on_error(e)
        return False


def atomic_operation(func):
    """
    Decorator to ensure database operations are atomic with proper rollback.
    
    Usage:
        @atomic_operation
        def create_user_with_relationships(user_data):
            user = User(**user_data)
            db.session.add(user)
            # ... more operations
            return user
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        from mason_snd.extensions import db
        
        try:
            result = func(*args, **kwargs)
            db.session.commit()
            return result
        except Exception as e:
            db.session.rollback()
            raise e
    
    return wrapper
