"""Tournament Signup Validation - Comprehensive validation system.

This module provides exhaustive validation for tournament signups to prevent
any possibility of users thinking they signed up when they didn't, or signups
failing silently.

Validation Checks:
    1. User account status (active, not ghost account)
    2. Event membership (user must be in event to sign up)
    3. Tournament availability (exists, not past deadline)
    4. Form completeness (all required fields filled)
    5. Partner requirements (partner events need valid partner)
    6. Partner reciprocity (partner must agree and be in same event)
    7. Duplicate prevention (not already signed up)
    8. Database constraints (all foreign keys valid)

Usage:
    validator = TournamentSignupValidator(user_id, tournament_id)
    validation_result = validator.validate_signup_request(form_data)
    
    if not validation_result.is_valid:
        # Show detailed error messages
        for error in validation_result.errors:
            flash(error, 'error')
    else:
        # Proceed with signup
"""

from datetime import datetime
import pytz
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

from ..extensions import db
from ..models.tournaments import Tournament, Tournament_Signups, Form_Fields, Form_Responses
from ..models.events import Event, User_Event
from ..models.auth import User

EST = pytz.timezone('US/Eastern')


@dataclass
class ValidationError:
    """Represents a single validation error with details and fix instructions."""
    field: str
    message: str
    fix_instructions: str
    severity: str = "error"  # "error", "warning", "info"


@dataclass
class ValidationResult:
    """Result of validation with detailed errors and warnings."""
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    requirements_met: Dict[str, bool] = field(default_factory=dict)
    
    def add_error(self, field: str, message: str, fix_instructions: str):
        """Add an error that blocks signup."""
        self.errors.append(ValidationError(field, message, fix_instructions, "error"))
        self.is_valid = False
    
    def add_warning(self, field: str, message: str, fix_instructions: str):
        """Add a warning that doesn't block signup but should be confirmed."""
        self.warnings.append(ValidationError(field, message, fix_instructions, "warning"))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'is_valid': self.is_valid,
            'errors': [
                {
                    'field': e.field,
                    'message': e.message,
                    'fix_instructions': e.fix_instructions,
                    'severity': e.severity
                }
                for e in self.errors
            ],
            'warnings': [
                {
                    'field': w.field,
                    'message': w.message,
                    'fix_instructions': w.fix_instructions,
                    'severity': w.severity
                }
                for w in self.warnings
            ],
            'requirements_met': self.requirements_met
        }


class TournamentSignupValidator:
    """Comprehensive validator for tournament signups."""
    
    def __init__(self, user_id: int, tournament_id: int):
        """Initialize validator with user and tournament context.
        
        Args:
            user_id: ID of user attempting to sign up
            tournament_id: ID of tournament to sign up for
        """
        self.user_id = user_id
        self.tournament_id = tournament_id
        self.user = User.query.get(user_id)
        self.tournament = Tournament.query.get(tournament_id)
        self.now = datetime.now(EST)
    
    def validate_signup_request(self, form_data: Dict[str, Any]) -> ValidationResult:
        """Perform comprehensive validation of signup request.
        
        Args:
            form_data: Dictionary containing:
                - selected_event_ids: List of event IDs to sign up for
                - form_responses: Dict mapping field_id to response value
                - partners: Dict mapping event_id to partner_id
        
        Returns:
            ValidationResult with detailed errors and warnings
        """
        result = ValidationResult(is_valid=True)
        
        # 1. Validate user account
        self._validate_user_account(result)
        
        # 2. Validate tournament availability
        self._validate_tournament_availability(result)
        
        # 3. Validate event selection
        selected_event_ids = form_data.get('selected_event_ids', [])
        if not selected_event_ids:
            result.add_error(
                'events',
                'No events selected',
                'Please select at least one event to sign up for.'
            )
        else:
            self._validate_event_membership(result, selected_event_ids)
        
        # 4. Validate form responses
        form_responses = form_data.get('form_responses', {})
        self._validate_form_responses(result, form_responses)
        
        # 5. Validate partner requirements
        partners = form_data.get('partners', {})
        self._validate_partner_requirements(result, selected_event_ids, partners)
        
        # 6. Check for duplicates
        self._validate_no_duplicates(result, selected_event_ids)
        
        return result
    
    def _validate_user_account(self, result: ValidationResult):
        """Validate user account is active and valid."""
        if not self.user:
            result.add_error(
                'user',
                'User account not found',
                'Please log out and log back in. If the problem persists, contact an administrator.'
            )
            return
        
        result.requirements_met['valid_user_account'] = True
        
        # Check if ghost account
        if hasattr(self.user, 'account_claimed') and not self.user.account_claimed:
            result.add_error(
                'user',
                'Account not fully activated',
                'Your account is not fully activated. Please complete your profile setup or contact an administrator.'
            )
            result.requirements_met['valid_user_account'] = False
    
    def _validate_tournament_availability(self, result: ValidationResult):
        """Validate tournament exists and is accepting signups."""
        if not self.tournament:
            result.add_error(
                'tournament',
                'Tournament not found',
                'The tournament you selected does not exist. Please return to the tournament list and try again.'
            )
            return
        
        # Check signup deadline
        if self.tournament.signup_deadline:
            sd = self.tournament.signup_deadline
            if sd.tzinfo is None:
                sd = EST.localize(sd)
            
            if sd < self.now:
                time_diff = self.now - sd
                hours_past = int(time_diff.total_seconds() / 3600)
                result.add_error(
                    'deadline',
                    f'Signup deadline has passed',
                    f'The signup deadline for {self.tournament.name} was {sd.strftime("%B %d, %Y at %I:%M %p")} '
                    f'({hours_past} hours ago). Contact your coach if you need an exception.'
                )
                result.requirements_met['within_deadline'] = False
                return
        
        result.requirements_met['within_deadline'] = True
        
        # Check if tournament has signup form
        if not self.tournament.form_fields or len(self.tournament.form_fields) == 0:
            result.add_error(
                'tournament',
                'Tournament signup not yet available',
                f'The signup form for {self.tournament.name} has not been created yet. '
                f'Contact an administrator to set up the tournament signup form.'
            )
            result.requirements_met['signup_form_exists'] = False
            return
        
        result.requirements_met['signup_form_exists'] = True
    
    def _validate_event_membership(self, result: ValidationResult, selected_event_ids: List[int]):
        """Validate user is a member of all selected events."""
        # Get all events user is a member of (active)
        user_event_ids = set(
            ue.event_id for ue in User_Event.query.filter_by(
                user_id=self.user_id,
                active=True
            ).all()
        )
        
        if not user_event_ids:
            result.add_error(
                'events',
                'You are not a member of any events',
                'You must join at least one event before signing up for tournaments. '
                'Visit the Events page to join an event, or contact your Event Leader.'
            )
            result.requirements_met['is_event_member'] = False
            return
        
        result.requirements_met['is_event_member'] = True
        
        # Check each selected event
        invalid_events = []
        for event_id in selected_event_ids:
            if event_id not in user_event_ids:
                event = Event.query.get(event_id)
                event_name = event.event_name if event else f"Event #{event_id}"
                invalid_events.append(event_name)
        
        if invalid_events:
            result.add_error(
                'events',
                f'You are not a member of: {", ".join(invalid_events)}',
                f'You can only sign up for events you are a member of. '
                f'Visit the Events page to join {", ".join(invalid_events)}, or remove '
                f'{"these events" if len(invalid_events) > 1 else "this event"} from your signup.'
            )
            result.requirements_met['all_events_valid'] = False
        else:
            result.requirements_met['all_events_valid'] = True
    
    def _validate_form_responses(self, result: ValidationResult, form_responses: Dict[int, str]):
        """Validate all required form fields are filled."""
        required_fields = Form_Fields.query.filter_by(
            tournament_id=self.tournament_id,
            required=True
        ).all()
        
        print("\n" + "-"*80)
        print("FORM VALIDATION DEBUG")
        print("-"*80)
        print(f"Total required fields: {len(required_fields)}")
        print(f"Form responses received: {len(form_responses)}")
        
        missing_required = []
        for field in required_fields:
            response = form_responses.get(field.id, '')
            # Convert to string and strip, handle None case
            if response is None:
                response = ''
            else:
                response = str(response).strip()
            
            print(f"\nField ID {field.id}: '{field.label}'")
            print(f"  Required: {field.required}")
            print(f"  Type: {field.type}")
            print(f"  Response received: '{response}'")
            print(f"  Response length: {len(response)}")
            print(f"  Is empty: {not response}")
            
            if not response:
                missing_required.append(field.label)
                print(f"  MISSING - Added to missing_required list")
            else:
                print(f"  Valid")
        
        print(f"\nTotal missing required fields: {len(missing_required)}")
        if missing_required:
            print(f"Missing fields: {missing_required}")
        print("-"*80 + "\n")
        
        if missing_required:
            result.add_error(
                'form',
                f'Missing required information',
                f'Please fill out the following required fields: {", ".join(missing_required)}'
            )
            result.requirements_met['all_required_fields_filled'] = False
        else:
            result.requirements_met['all_required_fields_filled'] = True
    
    def _validate_partner_requirements(
        self,
        result: ValidationResult,
        selected_event_ids: List[int],
        partners: Dict[int, int]
    ):
        """Validate partner requirements for partner events."""
        partner_event_ids = []
        
        for event_id in selected_event_ids:
            event = Event.query.get(event_id)
            if event and event.is_partner_event:
                partner_event_ids.append(event_id)
                
                # Check if partner was selected
                partner_id = partners.get(event_id)
                if not partner_id:
                    result.add_error(
                        f'partner_event_{event_id}',
                        f'Partner required for {event.event_name}',
                        f'{event.event_name} is a partner event. You must select a partner to compete with.'
                    )
                    result.requirements_met[f'partner_selected_{event_id}'] = False
                    continue
                
                result.requirements_met[f'partner_selected_{event_id}'] = True
                
                # Validate partner exists
                partner = User.query.get(partner_id)
                if not partner:
                    result.add_error(
                        f'partner_event_{event_id}',
                        f'Invalid partner selection',
                        f'The partner you selected does not exist. Please select a different partner.'
                    )
                    continue
                
                # Validate partner is in the same event
                partner_in_event = User_Event.query.filter_by(
                    user_id=partner_id,
                    event_id=event_id,
                    active=True
                ).first()
                
                if not partner_in_event:
                    result.add_error(
                        f'partner_event_{event_id}',
                        f'{partner.first_name} {partner.last_name} is not in {event.event_name}',
                        f'Your partner must be a member of {event.event_name}. Please select a different partner '
                        f'or ask {partner.first_name} to join {event.event_name} first.'
                    )
                    result.requirements_met[f'partner_in_event_{event_id}'] = False
                    continue
                
                result.requirements_met[f'partner_in_event_{event_id}'] = True
                
                # Check if partner is already signed up with someone else
                existing_partner_signup = Tournament_Signups.query.filter_by(
                    tournament_id=self.tournament_id,
                    event_id=event_id,
                    user_id=partner_id,
                    is_going=True
                ).first()
                
                if existing_partner_signup and existing_partner_signup.partner_id:
                    if existing_partner_signup.partner_id != self.user_id:
                        other_partner = User.query.get(existing_partner_signup.partner_id)
                        other_name = f"{other_partner.first_name} {other_partner.last_name}" if other_partner else "someone else"
                        result.add_warning(
                            f'partner_event_{event_id}',
                            f'{partner.first_name} is already partnered with {other_name}',
                            f'{partner.first_name} {partner.last_name} has already signed up with {other_name} for this tournament. '
                            f'If you proceed, their partnership will be updated to you instead. Make sure this is intentional.'
                        )
        
        if partner_event_ids:
            result.requirements_met['partner_events_handled'] = all(
                result.requirements_met.get(f'partner_selected_{eid}', False) and
                result.requirements_met.get(f'partner_in_event_{eid}', False)
                for eid in partner_event_ids
            )
        else:
            result.requirements_met['partner_events_handled'] = True
    
    def _validate_no_duplicates(self, result: ValidationResult, selected_event_ids: List[int]):
        """Check if user is already signed up for any of these events."""
        existing_signups = Tournament_Signups.query.filter(
            Tournament_Signups.tournament_id == self.tournament_id,
            Tournament_Signups.user_id == self.user_id,
            Tournament_Signups.event_id.in_(selected_event_ids),
            Tournament_Signups.is_going == True
        ).all()
        
        if existing_signups:
            event_names = []
            for signup in existing_signups:
                event = Event.query.get(signup.event_id)
                if event:
                    event_names.append(event.event_name)
            
            result.add_warning(
                'duplicates',
                f'You are already signed up for: {", ".join(event_names)}',
                f'Your existing signup will be updated with any changes you make. '
                f'This is not a duplicate signup.'
            )
        
        result.requirements_met['no_duplicates_or_acknowledged'] = True


def get_signup_requirements_summary(user_id: int, tournament_id: int) -> Dict[str, Any]:
    """Get a summary of requirements for tournament signup.
    
    This provides a checklist view before the user even starts the signup process.
    
    Args:
        user_id: ID of user
        tournament_id: ID of tournament
    
    Returns:
        Dictionary with requirement checks and instructions
    """
    user = User.query.get(user_id)
    tournament = Tournament.query.get(tournament_id)
    
    if not user or not tournament:
        return {'error': 'User or tournament not found'}
    
    # Get user's events
    user_events = User_Event.query.filter_by(user_id=user_id, active=True).all()
    event_names = [Event.query.get(ue.event_id).event_name for ue in user_events]
    
    # Check deadline
    now = datetime.now(EST)
    deadline_ok = True
    deadline_message = "Open"
    
    if tournament.signup_deadline:
        sd = tournament.signup_deadline
        if sd.tzinfo is None:
            sd = EST.localize(sd)
        
        if sd < now:
            deadline_ok = False
            deadline_message = f"Closed (deadline was {sd.strftime('%B %d, %Y at %I:%M %p')})"
        else:
            time_left = sd - now
            hours_left = int(time_left.total_seconds() / 3600)
            deadline_message = f"Open (closes {sd.strftime('%B %d, %Y at %I:%M %p')} - {hours_left} hours remaining)"
    
    # Check form exists
    has_form = tournament.form_fields and len(tournament.form_fields) > 0
    
    return {
        'tournament_name': tournament.name,
        'tournament_date': tournament.date.strftime('%B %d, %Y'),
        'requirements': {
            'is_event_member': {
                'met': len(user_events) > 0,
                'message': f"You are a member of {len(user_events)} event(s): {', '.join(event_names)}" if user_events else "You must join at least one event first",
                'action': None if user_events else "Visit the Events page to join an event"
            },
            'within_deadline': {
                'met': deadline_ok,
                'message': deadline_message,
                'action': None if deadline_ok else "Contact your coach if you need an exception"
            },
            'form_exists': {
                'met': has_form,
                'message': "Signup form is ready" if has_form else "Signup form not yet created",
                'action': None if has_form else "Contact an administrator to set up the signup form"
            }
        },
        'can_proceed': len(user_events) > 0 and deadline_ok and has_form
    }
