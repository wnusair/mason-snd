"""
Authentication Helper Utilities

This module provides helper functions and decorators for authentication
across the application, including login redirects with 'next' parameter support.
"""

from functools import wraps
from flask import session, redirect, url_for, request, flash


def login_required(f):
    """
    Decorator to require login for a route.
    
    If user is not logged in, redirects to login page with 'next' parameter
    set to the current URL so user can be redirected back after login.
    
    Usage:
        @app.route('/protected')
        @login_required
        def protected_route():
            return "This is protected"
    
    Args:
        f: The function to decorate
    
    Returns:
        Decorated function that checks for authentication
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "error")
            # Save the current path (relative URL) to redirect back after login
            next_url = request.full_path if request.query_string else request.path
            return redirect(url_for('auth.login', next=next_url))
        return f(*args, **kwargs)
    return decorated_function


def redirect_to_login(message="Please log in", next_url=None):
    """
    Helper function to redirect to login with optional next parameter.
    
    Args:
        message (str): Flash message to display
        next_url (str, optional): URL to redirect to after successful login.
                                 If None, uses request path (relative URL)
    
    Returns:
        redirect: Redirect response to login page with next parameter
    """
    if message:
        flash(message, "error")
    
    # Use provided next_url or fall back to current request path (relative URL)
    if next_url is None:
        # Use full_path to include query string, or just path if no query string
        next_url = request.full_path if request.query_string else request.path
    
    return redirect(url_for('auth.login', next=next_url))
