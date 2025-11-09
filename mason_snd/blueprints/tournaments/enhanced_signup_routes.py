"""Enhanced Tournament Signup Routes with Comprehensive Validation.

This module adds bulletproof signup validation and multi-step confirmation
to prevent any scenario where a user thinks they signed up but didn't.

New Routes:
    - /signup/requirements/<int:tournament_id> - Pre-signup requirements check
    - /signup - Enhanced signup form with inline validation
    - /signup/confirm - First confirmation screen (review and initial confirmations)
    - /signup/final_confirm - Second confirmation screen (final warnings and submit)
    - /signup/submit - Actually processes the signup with transaction safety
    
Flow:
    1. User clicks signup -> Requirements Check Screen
    2. User fills form -> Enhanced Signup Form (with live validation)
    3. User submits -> First Confirmation Screen (review info + 3 checkboxes)
    4. User confirms -> Second Confirmation Screen (final warning + 3 more checkboxes)
    5. User final submit -> Database transaction + Success Screen with proof
    
Safety Features:
    - Pre-validation before form is even shown
    - Client-side AND server-side validation at every step
    - Partner reciprocity checking
    - Event membership verification
    - Required field enforcement
    - Two separate "Are you sure?" screens
    - Transaction-safe database commits with rollback on error
    - Confirmation ID generation for proof
    - Success screen with all signup IDs for verification
"""

from flask import render_template, request, redirect, url_for, flash, session, jsonify
from mason_snd.extensions import db
from mason_snd.models.auth import User
from mason_snd.models.tournaments import Tournament, Tournament_Signups, Form_Responses, Tournament_Judges
from mason_snd.models.events import Event, User_Event
from mason_snd.utils.tournament_signup_validator import (
    TournamentSignupValidator,
    get_signup_requirements_summary,
    ValidationResult
)
from mason_snd.utils.auth_helpers import redirect_to_login
from datetime import datetime
import pytz
import json
import hashlib

EST = pytz.timezone('US/Eastern')


def register_enhanced_signup_routes(tournaments_bp):
    """Register enhanced signup routes with the tournaments blueprint."""
    
    @tournaments_bp.route('/signup/requirements/<int:tournament_id>')
    def signup_requirements(tournament_id):
        """Pre-signup requirements check screen.
        
        Shows user a checklist of requirements they must meet before
        they can proceed to the signup form. Prevents frustration of
        filling out form only to find they can't submit.
        
        Args:
            tournament_id: Tournament to check requirements for
        
        Returns:
            Requirements checklist page with ability to proceed or not
        """
        user_id = session.get('user_id')
        if not user_id:
            return redirect_to_login("Please log in to sign up for tournaments")
        
        requirements = get_signup_requirements_summary(user_id, tournament_id)
        
        if 'error' in requirements:
            flash(requirements['error'], 'error')
            return redirect(url_for('tournaments.index'))
        
        return render_template(
            'tournaments/signup_requirements.html',
            requirements=requirements,
            tournament_id=tournament_id
        )
    
    @tournaments_bp.route('/signup/confirm', methods=['POST'])
    def signup_confirmation():
        """First confirmation screen - review all info and initial confirmations.
        
        After user submits signup form, show them exactly what they're
        signing up for and require initial confirmations.
        
        POST data should include all form fields from signup.
        
        Returns:
            Confirmation page with review of all data and confirmation checkboxes
        """
        user_id = session.get('user_id')
        if not user_id:
            return redirect_to_login("Please log in")
        
        tournament_id = request.form.get('tournament_id')
        if not tournament_id:
            flash("No tournament selected", "error")
            return redirect(url_for('tournaments.index'))
        
        tournament = Tournament.query.get(tournament_id)
        if not tournament:
            flash("Tournament not found", "error")
            return redirect(url_for('tournaments.index'))
        
        # Gather all form data
        selected_event_ids = [int(eid) for eid in request.form.getlist('user_event')]
        
        # Build partners dict
        partners = {}
        for event_id in selected_event_ids:
            partner_id = request.form.get(f'partner_{event_id}')
            if partner_id:
                try:
                    partners[event_id] = int(partner_id)
                except (ValueError, TypeError):
                    pass
        
        # Build form responses dict
        form_responses = {}
        for field in tournament.form_fields:
            response = request.form.get(f'field_{field.id}')
            form_responses[field.id] = response
        
        # Check for bringing judge
        bringing_judge = False
        for field in tournament.form_fields:
            if field.label.strip().lower() == "are you bringing a judge?":
                response = request.form.get(f'field_{field.id}')
                if response and response.lower() in ["yes", "true", "on", "1"]:
                    bringing_judge = True
                    break
        
        # Validate the signup data
        validator = TournamentSignupValidator(user_id, tournament_id)
        validation_result = validator.validate_signup_request({
            'selected_event_ids': selected_event_ids,
            'form_responses': form_responses,
            'partners': partners,
            'bringing_judge': bringing_judge,
            'judge_id': None  # Will be selected later if needed
        })
        
        if not validation_result.is_valid:
            # Show error page with detailed issues
            return render_template(
                'tournaments/signup_error.html',
                validation_result=validation_result,
                tournament_id=tournament_id
            )
        
        # Build event info for display
        events_info = []
        for event_id in selected_event_ids:
            event = Event.query.get(event_id)
            if event:
                event_info = {
                    'id': event_id,
                    'name': event.event_name,
                    'emoji': event.event_emoji,
                    'partner': None
                }
                
                if event_id in partners:
                    partner = User.query.get(partners[event_id])
                    if partner:
                        event_info['partner'] = partner
                
                events_info.append(event_info)
        
        # Build signup data structure
        signup_data = {
            'tournament_id': tournament_id,
            'events': events_info,
            'form_responses': form_responses,
            'bringing_judge': bringing_judge
        }
        
        # Serialize signup data for next step
        signup_data_json = json.dumps(signup_data)
        
        # Build form_fields dict for template
        form_fields = {field.id: field for field in tournament.form_fields}
        
        return render_template(
            'tournaments/signup_confirmation.html',
            tournament=tournament,
            signup_data=signup_data,
            signup_data_json=signup_data_json,
            form_fields=form_fields,
            validation_result=validation_result
        )
    
    @tournaments_bp.route('/signup/final_confirm', methods=['POST'])
    def signup_final_confirm():
        """Second confirmation screen - final warnings before submit.
        
        After user confirms on first screen, show them one more
        very clear warning screen with additional confirmations.
        This is the "are you REALLY sure?" screen.
        
        Returns:
            Final confirmation page with big warnings and final checkboxes
        """
        user_id = session.get('user_id')
        if not user_id:
            return redirect_to_login("Please log in")
        
        # Get signup data from previous step
        signup_data_json = request.form.get('signup_data_json')
        if not signup_data_json:
            flash("Session expired. Please start signup again.", "error")
            return redirect(url_for('tournaments.index'))
        
        try:
            signup_data = json.loads(signup_data_json)
        except json.JSONDecodeError:
            flash("Invalid signup data. Please start again.", "error")
            return redirect(url_for('tournaments.index'))
        
        tournament_id = signup_data.get('tournament_id')
        tournament = Tournament.query.get(tournament_id)
        
        if not tournament:
            flash("Tournament not found", "error")
            return redirect(url_for('tournaments.index'))
        
        # Verify all confirmations from first screen were checked
        required_confirmations = ['confirm_info_accurate', 'confirm_commitment']
        for conf in required_confirmations:
            if not request.form.get(conf):
                flash("You must check all confirmation boxes to proceed", "error")
                return redirect(url_for('tournaments.signup', tournament_id=tournament_id))
        
        return render_template(
            'tournaments/signup_final_confirmation.html',
            tournament=tournament,
            signup_data=signup_data,
            signup_data_json=signup_data_json
        )
    
    @tournaments_bp.route('/signup/submit', methods=['POST'])
    def signup_submit():
        """Actually process and save the signup to database.
        
        This is the final step that actually creates database records.
        Uses transaction safety to ensure either all records are created
        or none are (atomic operation).
        
        Returns:
            Success page with confirmation ID and all signup details
        """
        user_id = session.get('user_id')
        if not user_id:
            return redirect_to_login("Please log in")
        
        # Get signup data
        signup_data_json = request.form.get('signup_data_json')
        if not signup_data_json:
            flash("Session expired. Please start signup again.", "error")
            return redirect(url_for('tournaments.index'))
        
        try:
            signup_data = json.loads(signup_data_json)
        except json.JSONDecodeError:
            flash("Invalid signup data. Please start again.", "error")
            return redirect(url_for('tournaments.index'))
        
        # Verify all final confirmations
        required_final_confirmations = [
            'final_confirm_reviewed',
            'final_confirm_no_mistakes',
            'final_confirm_understand_consequences'
        ]
        for conf in required_final_confirmations:
            if not request.form.get(conf):
                flash("You must check all confirmation boxes to submit", "error")
                tournament_id = signup_data.get('tournament_id')
                return redirect(url_for('tournaments.signup', tournament_id=tournament_id))
        
        tournament_id = signup_data.get('tournament_id')
        tournament = Tournament.query.get(tournament_id)
        
        if not tournament:
            flash("Tournament not found", "error")
            return redirect(url_for('tournaments.index'))
        
        # Re-validate one more time (safety check)
        selected_event_ids = [event['id'] for event in signup_data.get('events', [])]
        partners = {}
        for event in signup_data.get('events', []):
            if event.get('partner'):
                partners[event['id']] = event['partner']['id']
        
        validator = TournamentSignupValidator(user_id, tournament_id)
        validation_result = validator.validate_signup_request({
            'selected_event_ids': selected_event_ids,
            'form_responses': signup_data.get('form_responses', {}),
            'partners': partners,
            'bringing_judge': signup_data.get('bringing_judge', False),
            'judge_id': None
        })
        
        if not validation_result.is_valid:
            flash("Validation failed. Your signup data may have become invalid. Please try again.", "error")
            return render_template(
                'tournaments/signup_error.html',
                validation_result=validation_result,
                tournament_id=tournament_id
            )
        
        # Begin database transaction
        now = datetime.now(EST)
        created_signups = []
        
        try:
            # Create Tournament_Signups for each event
            for event_data in signup_data.get('events', []):
                event_id = event_data['id']
                partner_id = event_data.get('partner', {}).get('id') if event_data.get('partner') else None
                
                # Check if signup already exists (update instead of create)
                signup = Tournament_Signups.query.filter_by(
                    user_id=user_id,
                    tournament_id=tournament_id,
                    event_id=event_id
                ).first()
                
                if not signup:
                    signup = Tournament_Signups(
                        user_id=user_id,
                        tournament_id=tournament_id,
                        event_id=event_id,
                        is_going=True,
                        partner_id=partner_id,
                        bringing_judge=signup_data.get('bringing_judge', False),
                        created_at=now
                    )
                    db.session.add(signup)
                else:
                    signup.is_going = True
                    signup.partner_id = partner_id
                    signup.bringing_judge = signup_data.get('bringing_judge', False)
                    signup.created_at = now
                
                db.session.flush()  # Get signup ID
                created_signups.append({
                    'event_id': event_id,
                    'event_name': event_data['name'],
                    'event_emoji': event_data.get('emoji', ''),
                    'signup_id': signup.id,
                    'partner': event_data.get('partner')
                })
                
                # If partner event, create/update partner's signup too
                if partner_id:
                    partner_signup = Tournament_Signups.query.filter_by(
                        user_id=partner_id,
                        tournament_id=tournament_id,
                        event_id=event_id
                    ).first()
                    
                    if not partner_signup:
                        partner_signup = Tournament_Signups(
                            user_id=partner_id,
                            tournament_id=tournament_id,
                            event_id=event_id,
                            is_going=True,
                            partner_id=user_id,
                            created_at=now
                        )
                        db.session.add(partner_signup)
                    else:
                        partner_signup.partner_id = user_id
                        if not partner_signup.is_going:
                            partner_signup.is_going = True
                            partner_signup.created_at = now
                
                # Create Tournament_Judges entry
                existing_judge = Tournament_Judges.query.filter_by(
                    child_id=user_id,
                    tournament_id=tournament_id,
                    event_id=event_id
                ).first()
                
                if not existing_judge:
                    judge_entry = Tournament_Judges(
                        accepted=False,
                        judge_id=None,
                        child_id=user_id,
                        tournament_id=tournament_id,
                        event_id=event_id
                    )
                    db.session.add(judge_entry)
            
            # Create Form_Responses
            for field_id, response in signup_data.get('form_responses', {}).items():
                # Delete old response if exists
                old_response = Form_Responses.query.filter_by(
                    tournament_id=tournament_id,
                    user_id=user_id,
                    field_id=field_id
                ).first()
                
                if old_response:
                    db.session.delete(old_response)
                
                # Create new response
                new_response = Form_Responses(
                    tournament_id=tournament_id,
                    user_id=user_id,
                    field_id=int(field_id),
                    response=response,
                    submitted_at=now
                )
                db.session.add(new_response)
            
            # Commit all changes atomically
            db.session.commit()
            
            # Generate confirmation ID (hash of user_id + tournament_id + timestamp)
            confirmation_string = f"{user_id}-{tournament_id}-{now.isoformat()}"
            confirmation_id = hashlib.sha256(confirmation_string.encode()).hexdigest()[:16].upper()
            
            # Generate transaction ID for logging
            transaction_id = hashlib.sha256(f"{confirmation_string}-{len(created_signups)}".encode()).hexdigest()[:24].upper()
            
            return render_template(
                'tournaments/signup_success.html',
                tournament=tournament,
                events_registered=created_signups,
                bringing_judge=signup_data.get('bringing_judge', False),
                confirmation_id=confirmation_id,
                transaction_id=transaction_id,
                submitted_at=now,
                signup_count=len(created_signups)
            )
            
        except Exception as e:
            # Rollback on any error
            db.session.rollback()
            
            # Log the error (in production, use proper logging)
            print(f"ERROR during signup submission: {str(e)}")
            
            flash(
                f"An error occurred while saving your signup: {str(e)}. "
                "Please try again. If the problem persists, contact an administrator.",
                "error"
            )
            return redirect(url_for('tournaments.signup', tournament_id=tournament_id))
    
    @tournaments_bp.route('/search_partners')
    def search_partners():
        """AJAX endpoint to search for potential partners.
        
        Used by the signup form to find partners for partner events.
        Only returns users who are in the specified event.
        
        Query params:
            q: Search query (name)
            event_id: Event ID to filter by
        
        Returns:
            JSON list of matching users
        """
        query = request.args.get('q', '').strip()
        event_id = request.args.get('event_id')
        
        if not query or len(query) < 2:
            return jsonify({'users': []})
        
        if not event_id:
            return jsonify({'users': []})
        
        # Find users in this event whose name matches query
        user_ids_in_event = [
            ue.user_id for ue in User_Event.query.filter_by(
                event_id=int(event_id),
                active=True
            ).all()
        ]
        
        # Search for users by name
        users = User.query.filter(
            User.id.in_(user_ids_in_event),
            db.or_(
                User.first_name.ilike(f'%{query}%'),
                User.last_name.ilike(f'%{query}%')
            )
        ).limit(10).all()
        
        return jsonify({
            'users': [
                {
                    'id': user.id,
                    'first_name': user.first_name,
                    'last_name': user.last_name
                }
                for user in users
            ]
        })
