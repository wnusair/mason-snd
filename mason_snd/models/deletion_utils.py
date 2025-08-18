"""
Utility functions for safely deleting users and tournaments with all their related data.
This handles cascade deletion of foreign key relationships to prevent integrity errors.
"""

from ..extensions import db
from .auth import User, User_Published_Rosters, Roster_Penalty_Entries, Judges
from .tournaments import (Tournament, Form_Fields, Form_Responses, Tournament_Signups, 
                         Tournaments_Attended, Tournament_Performance, Tournament_Judges,
                         Tournament_Partners)
from .events import Event, User_Event, Effort_Score
from .rosters import Roster, Roster_Judge, Roster_Competitors, Roster_Partners
from .admin import User_Requirements, Popups
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import pytz

EST = pytz.timezone('US/Eastern')

class DeletionResult:
    """Class to track deletion results and statistics"""
    def __init__(self):
        self.success = True
        self.errors = []
        self.deleted_counts = {}
        self.failed_items = []
    
    def add_deleted(self, model_name, count):
        self.deleted_counts[model_name] = self.deleted_counts.get(model_name, 0) + count
    
    def add_error(self, error_msg, item_id=None):
        self.success = False
        self.errors.append(error_msg)
        if item_id:
            self.failed_items.append(item_id)
    
    def get_summary(self):
        if self.success:
            total_deleted = sum(self.deleted_counts.values())
            return f"Successfully deleted {total_deleted} records across {len(self.deleted_counts)} tables"
        else:
            return f"Deletion failed with {len(self.errors)} errors"

def delete_user_safely(user_id):
    """
    Safely delete a user and all their related data.
    Returns DeletionResult object with success status and details.
    """
    result = DeletionResult()
    
    try:
        user = User.query.get(user_id)
        if not user:
            result.add_error(f"User with ID {user_id} not found")
            return result
        
        user_name = f"{user.first_name} {user.last_name}"
        
        # Delete in order to respect foreign key constraints
        
        # 1. Delete user's published roster entries
        published_rosters = User_Published_Rosters.query.filter_by(user_id=user_id).all()
        for entry in published_rosters:
            db.session.delete(entry)
        result.add_deleted('User_Published_Rosters', len(published_rosters))
        
        # 2. Delete user's penalty entries
        penalty_entries = Roster_Penalty_Entries.query.filter_by(penalized_user_id=user_id).all()
        for entry in penalty_entries:
            db.session.delete(entry)
        result.add_deleted('Roster_Penalty_Entries', len(penalty_entries))
        
        # 3. Delete judge relationships where user is judge or child
        judge_relationships = Judges.query.filter(
            (Judges.judge_id == user_id) | (Judges.child_id == user_id)
        ).all()
        for judge in judge_relationships:
            db.session.delete(judge)
        result.add_deleted('Judges', len(judge_relationships))
        
        # 4. Delete tournament judges where user is judge or child
        tournament_judges = Tournament_Judges.query.filter(
            (Tournament_Judges.judge_id == user_id) | (Tournament_Judges.child_id == user_id)
        ).all()
        for tj in tournament_judges:
            db.session.delete(tj)
        result.add_deleted('Tournament_Judges', len(tournament_judges))
        
        # 5. Delete tournament partners where user is partner1 or partner2
        tournament_partners = Tournament_Partners.query.filter(
            (Tournament_Partners.partner1_user_id == user_id) | 
            (Tournament_Partners.partner2_user_id == user_id)
        ).all()
        for tp in tournament_partners:
            db.session.delete(tp)
        result.add_deleted('Tournament_Partners', len(tournament_partners))
        
        # 6. Delete roster partners where user is partner1 or partner2
        roster_partners = Roster_Partners.query.filter(
            (Roster_Partners.partner1_user_id == user_id) | 
            (Roster_Partners.partner2_user_id == user_id)
        ).all()
        for rp in roster_partners:
            db.session.delete(rp)
        result.add_deleted('Roster_Partners', len(roster_partners))
        
        # 7. Delete form responses
        form_responses = Form_Responses.query.filter_by(user_id=user_id).all()
        for response in form_responses:
            db.session.delete(response)
        result.add_deleted('Form_Responses', len(form_responses))
        
        # 8. Delete tournament signups (including where user is judge or partner)
        tournament_signups = Tournament_Signups.query.filter(
            (Tournament_Signups.user_id == user_id) | 
            (Tournament_Signups.judge_id == user_id) |
            (Tournament_Signups.partner_id == user_id)
        ).all()
        for signup in tournament_signups:
            db.session.delete(signup)
        result.add_deleted('Tournament_Signups', len(tournament_signups))
        
        # 9. Delete tournaments attended
        tournaments_attended = Tournaments_Attended.query.filter_by(user_id=user_id).all()
        for ta in tournaments_attended:
            db.session.delete(ta)
        result.add_deleted('Tournaments_Attended', len(tournaments_attended))
        
        # 10. Delete tournament performances
        tournament_performances = Tournament_Performance.query.filter_by(user_id=user_id).all()
        for tp in tournament_performances:
            db.session.delete(tp)
        result.add_deleted('Tournament_Performance', len(tournament_performances))
        
        # 11. Delete user events
        user_events = User_Event.query.filter_by(user_id=user_id).all()
        for ue in user_events:
            db.session.delete(ue)
        result.add_deleted('User_Event', len(user_events))
        
        # 12. Delete effort scores (both given to user and given by user)
        effort_scores = Effort_Score.query.filter(
            (Effort_Score.user_id == user_id) | (Effort_Score.given_by_id == user_id)
        ).all()
        for es in effort_scores:
            db.session.delete(es)
        result.add_deleted('Effort_Score', len(effort_scores))
        
        # 13. Delete roster judges where user is judge or child
        roster_judges = Roster_Judge.query.filter(
            (Roster_Judge.user_id == user_id) | (Roster_Judge.child_id == user_id)
        ).all()
        for rj in roster_judges:
            db.session.delete(rj)
        result.add_deleted('Roster_Judge', len(roster_judges))
        
        # 14. Delete roster competitors where user is competitor or judge
        roster_competitors = Roster_Competitors.query.filter(
            (Roster_Competitors.user_id == user_id) | (Roster_Competitors.judge_id == user_id)
        ).all()
        for rc in roster_competitors:
            db.session.delete(rc)
        result.add_deleted('Roster_Competitors', len(roster_competitors))
        
        # 15. Delete user requirements
        user_requirements = User_Requirements.query.filter_by(user_id=user_id).all()
        for ur in user_requirements:
            db.session.delete(ur)
        result.add_deleted('User_Requirements', len(user_requirements))
        
        # 16. Delete popups (both received and sent)
        popups = Popups.query.filter(
            (Popups.user_id == user_id) | (Popups.admin_id == user_id)
        ).all()
        for popup in popups:
            db.session.delete(popup)
        result.add_deleted('Popups', len(popups))
        
        # 17. Handle events owned by user - transfer ownership to admin or delete
        owned_events = Event.query.filter_by(owner_id=user_id).all()
        if owned_events:
            # Find an admin user to transfer ownership to
            admin_user = User.query.filter(User.role >= 2).first()
            if admin_user:
                for event in owned_events:
                    event.owner_id = admin_user.id
                result.add_deleted('Events_Transferred', len(owned_events))
            else:
                # No admin found, delete the events (this will cascade)
                for event in owned_events:
                    db.session.delete(event)
                result.add_deleted('Events_Deleted', len(owned_events))
        
        # 18. Finally delete the user
        db.session.delete(user)
        result.add_deleted('User', 1)
        
        # Commit all changes
        db.session.commit()
        
        return result
        
    except IntegrityError as e:
        db.session.rollback()
        result.add_error(f"Database integrity error when deleting user {user_id}: {str(e)}")
        return result
    except Exception as e:
        db.session.rollback()
        result.add_error(f"Unexpected error when deleting user {user_id}: {str(e)}")
        return result

def delete_tournament_safely(tournament_id):
    """
    Safely delete a tournament and all its related data.
    Returns DeletionResult object with success status and details.
    """
    result = DeletionResult()
    
    try:
        tournament = Tournament.query.get(tournament_id)
        if not tournament:
            result.add_error(f"Tournament with ID {tournament_id} not found")
            return result
        
        tournament_name = tournament.name
        
        # Delete in order to respect foreign key constraints
        
        # 1. Delete published roster entries for this tournament
        published_rosters = User_Published_Rosters.query.filter_by(tournament_id=tournament_id).all()
        for entry in published_rosters:
            db.session.delete(entry)
        result.add_deleted('User_Published_Rosters', len(published_rosters))
        
        # 2. Delete penalty entries for this tournament
        penalty_entries = Roster_Penalty_Entries.query.filter_by(tournament_id=tournament_id).all()
        for entry in penalty_entries:
            db.session.delete(entry)
        result.add_deleted('Roster_Penalty_Entries', len(penalty_entries))
        
        # 3. Delete form responses for this tournament
        form_responses = Form_Responses.query.filter_by(tournament_id=tournament_id).all()
        for response in form_responses:
            db.session.delete(response)
        result.add_deleted('Form_Responses', len(form_responses))
        
        # 4. Delete form fields for this tournament
        form_fields = Form_Fields.query.filter_by(tournament_id=tournament_id).all()
        for field in form_fields:
            db.session.delete(field)
        result.add_deleted('Form_Fields', len(form_fields))
        
        # 5. Delete tournament signups
        tournament_signups = Tournament_Signups.query.filter_by(tournament_id=tournament_id).all()
        for signup in tournament_signups:
            db.session.delete(signup)
        result.add_deleted('Tournament_Signups', len(tournament_signups))
        
        # 6. Delete tournaments attended records
        tournaments_attended = Tournaments_Attended.query.filter_by(tournament_id=tournament_id).all()
        for ta in tournaments_attended:
            db.session.delete(ta)
        result.add_deleted('Tournaments_Attended', len(tournaments_attended))
        
        # 7. Delete tournament performances
        tournament_performances = Tournament_Performance.query.filter_by(tournament_id=tournament_id).all()
        for tp in tournament_performances:
            db.session.delete(tp)
        result.add_deleted('Tournament_Performance', len(tournament_performances))
        
        # 8. Delete tournament judges
        tournament_judges = Tournament_Judges.query.filter_by(tournament_id=tournament_id).all()
        for tj in tournament_judges:
            db.session.delete(tj)
        result.add_deleted('Tournament_Judges', len(tournament_judges))
        
        # 9. Delete tournament partners
        tournament_partners = Tournament_Partners.query.filter_by(tournament_id=tournament_id).all()
        for tp in tournament_partners:
            db.session.delete(tp)
        result.add_deleted('Tournament_Partners', len(tournament_partners))
        
        # 10. Delete rosters associated with this tournament
        rosters = Roster.query.filter_by(tournament_id=tournament_id).all()
        for roster in rosters:
            # Delete roster-related entries first
            roster_judges = Roster_Judge.query.filter_by(roster_id=roster.id).all()
            for rj in roster_judges:
                db.session.delete(rj)
            
            roster_competitors = Roster_Competitors.query.filter_by(roster_id=roster.id).all()
            for rc in roster_competitors:
                db.session.delete(rc)
            
            roster_partners = Roster_Partners.query.filter_by(roster_id=roster.id).all()
            for rp in roster_partners:
                db.session.delete(rp)
            
            # Delete the roster itself
            db.session.delete(roster)
        
        result.add_deleted('Rosters_and_Related', len(rosters))
        
        # 11. Finally delete the tournament
        db.session.delete(tournament)
        result.add_deleted('Tournament', 1)
        
        # Commit all changes
        db.session.commit()
        
        return result
        
    except IntegrityError as e:
        db.session.rollback()
        result.add_error(f"Database integrity error when deleting tournament {tournament_id}: {str(e)}")
        return result
    except Exception as e:
        db.session.rollback()
        result.add_error(f"Unexpected error when deleting tournament {tournament_id}: {str(e)}")
        return result

def delete_multiple_users(user_ids):
    """
    Delete multiple users safely.
    Returns DeletionResult object with aggregated results.
    """
    result = DeletionResult()
    
    for user_id in user_ids:
        individual_result = delete_user_safely(user_id)
        
        if individual_result.success:
            # Aggregate successful deletions
            for model_name, count in individual_result.deleted_counts.items():
                result.add_deleted(model_name, count)
        else:
            # Aggregate errors
            for error in individual_result.errors:
                result.add_error(error, user_id)
    
    return result

def get_user_deletion_preview(user_id):
    """
    Get a preview of what would be deleted when deleting a user.
    Returns a dictionary with counts of related records.
    """
    user = User.query.get(user_id)
    if not user:
        return None
    
    preview = {
        'user_name': f"{user.first_name} {user.last_name}",
        'user_email': user.email,
        'counts': {}
    }
    
    # Count related records
    preview['counts']['Published_Rosters'] = User_Published_Rosters.query.filter_by(user_id=user_id).count()
    preview['counts']['Penalty_Entries'] = Roster_Penalty_Entries.query.filter_by(penalized_user_id=user_id).count()
    preview['counts']['Judge_Relationships'] = Judges.query.filter(
        (Judges.judge_id == user_id) | (Judges.child_id == user_id)
    ).count()
    preview['counts']['Tournament_Judges'] = Tournament_Judges.query.filter(
        (Tournament_Judges.judge_id == user_id) | (Tournament_Judges.child_id == user_id)
    ).count()
    preview['counts']['Tournament_Partners'] = Tournament_Partners.query.filter(
        (Tournament_Partners.partner1_user_id == user_id) | 
        (Tournament_Partners.partner2_user_id == user_id)
    ).count()
    preview['counts']['Roster_Partners'] = Roster_Partners.query.filter(
        (Roster_Partners.partner1_user_id == user_id) | 
        (Roster_Partners.partner2_user_id == user_id)
    ).count()
    preview['counts']['Form_Responses'] = Form_Responses.query.filter_by(user_id=user_id).count()
    preview['counts']['Tournament_Signups'] = Tournament_Signups.query.filter(
        (Tournament_Signups.user_id == user_id) | 
        (Tournament_Signups.judge_id == user_id) |
        (Tournament_Signups.partner_id == user_id)
    ).count()
    preview['counts']['Tournaments_Attended'] = Tournaments_Attended.query.filter_by(user_id=user_id).count()
    preview['counts']['Tournament_Performances'] = Tournament_Performance.query.filter_by(user_id=user_id).count()
    preview['counts']['User_Events'] = User_Event.query.filter_by(user_id=user_id).count()
    preview['counts']['Effort_Scores'] = Effort_Score.query.filter(
        (Effort_Score.user_id == user_id) | (Effort_Score.given_by_id == user_id)
    ).count()
    preview['counts']['Roster_Judges'] = Roster_Judge.query.filter(
        (Roster_Judge.user_id == user_id) | (Roster_Judge.child_id == user_id)
    ).count()
    preview['counts']['Roster_Competitors'] = Roster_Competitors.query.filter(
        (Roster_Competitors.user_id == user_id) | (Roster_Competitors.judge_id == user_id)
    ).count()
    preview['counts']['User_Requirements'] = User_Requirements.query.filter_by(user_id=user_id).count()
    preview['counts']['Popups'] = Popups.query.filter(
        (Popups.user_id == user_id) | (Popups.admin_id == user_id)
    ).count()
    preview['counts']['Owned_Events'] = Event.query.filter_by(owner_id=user_id).count()
    
    # Calculate total related records
    preview['total_related'] = sum(preview['counts'].values())
    
    return preview

def get_tournament_deletion_preview(tournament_id):
    """
    Get a preview of what would be deleted when deleting a tournament.
    Returns a dictionary with counts of related records.
    """
    tournament = Tournament.query.get(tournament_id)
    if not tournament:
        return None
    
    preview = {
        'tournament_name': tournament.name,
        'tournament_date': tournament.date,
        'counts': {}
    }
    
    # Count related records
    preview['counts']['Published_Rosters'] = User_Published_Rosters.query.filter_by(tournament_id=tournament_id).count()
    preview['counts']['Penalty_Entries'] = Roster_Penalty_Entries.query.filter_by(tournament_id=tournament_id).count()
    preview['counts']['Form_Responses'] = Form_Responses.query.filter_by(tournament_id=tournament_id).count()
    preview['counts']['Form_Fields'] = Form_Fields.query.filter_by(tournament_id=tournament_id).count()
    preview['counts']['Tournament_Signups'] = Tournament_Signups.query.filter_by(tournament_id=tournament_id).count()
    preview['counts']['Tournaments_Attended'] = Tournaments_Attended.query.filter_by(tournament_id=tournament_id).count()
    preview['counts']['Tournament_Performances'] = Tournament_Performance.query.filter_by(tournament_id=tournament_id).count()
    preview['counts']['Tournament_Judges'] = Tournament_Judges.query.filter_by(tournament_id=tournament_id).count()
    preview['counts']['Tournament_Partners'] = Tournament_Partners.query.filter_by(tournament_id=tournament_id).count()
    preview['counts']['Rosters'] = Roster.query.filter_by(tournament_id=tournament_id).count()
    
    # Calculate total related records
    preview['total_related'] = sum(preview['counts'].values())
    
    return preview

def delete_event_safely(event_id):
    """
    Safely delete an event and all its related data.
    Returns DeletionResult object with success status and details.
    """
    result = DeletionResult()
    
    try:
        event = Event.query.get(event_id)
        if not event:
            result.add_error(f"Event with ID {event_id} not found")
            return result
        
        event_name = event.event_name
        
        # Delete in order to respect foreign key constraints
        
        # 1. Delete published roster entries for this event
        published_rosters = User_Published_Rosters.query.filter_by(event_id=event_id).all()
        for entry in published_rosters:
            db.session.delete(entry)
        result.add_deleted('User_Published_Rosters', len(published_rosters))
        
        # 2. Delete penalty entries for this event
        penalty_entries = Roster_Penalty_Entries.query.filter_by(event_id=event_id).all()
        for entry in penalty_entries:
            db.session.delete(entry)
        result.add_deleted('Roster_Penalty_Entries', len(penalty_entries))
        
        # 3. Delete tournament signups for this event
        tournament_signups = Tournament_Signups.query.filter_by(event_id=event_id).all()
        for signup in tournament_signups:
            db.session.delete(signup)
        result.add_deleted('Tournament_Signups', len(tournament_signups))
        
        # 4. Delete tournament judges for this event
        tournament_judges = Tournament_Judges.query.filter_by(event_id=event_id).all()
        for tj in tournament_judges:
            db.session.delete(tj)
        result.add_deleted('Tournament_Judges', len(tournament_judges))
        
        # 5. Delete tournament partners for this event
        tournament_partners = Tournament_Partners.query.filter_by(event_id=event_id).all()
        for tp in tournament_partners:
            db.session.delete(tp)
        result.add_deleted('Tournament_Partners', len(tournament_partners))
        
        # 6. Delete roster judges for this event
        roster_judges = Roster_Judge.query.filter_by(event_id=event_id).all()
        for rj in roster_judges:
            db.session.delete(rj)
        result.add_deleted('Roster_Judge', len(roster_judges))
        
        # 7. Delete roster competitors for this event
        roster_competitors = Roster_Competitors.query.filter_by(event_id=event_id).all()
        for rc in roster_competitors:
            db.session.delete(rc)
        result.add_deleted('Roster_Competitors', len(roster_competitors))
        
        # 8. Delete user events (user participation in this event)
        user_events = User_Event.query.filter_by(event_id=event_id).all()
        for ue in user_events:
            db.session.delete(ue)
        result.add_deleted('User_Event', len(user_events))
        
        # 9. Delete effort scores for this event
        effort_scores = Effort_Score.query.filter_by(event_id=event_id).all()
        for es in effort_scores:
            db.session.delete(es)
        result.add_deleted('Effort_Score', len(effort_scores))
        
        # 10. Finally delete the event
        db.session.delete(event)
        result.add_deleted('Event', 1)
        
        # Commit all changes
        db.session.commit()
        
        return result
        
    except IntegrityError as e:
        db.session.rollback()
        result.add_error(f"Database integrity error when deleting event {event_id}: {str(e)}")
        return result
    except Exception as e:
        db.session.rollback()
        result.add_error(f"Unexpected error when deleting event {event_id}: {str(e)}")
        return result

def delete_multiple_events(event_ids):
    """
    Delete multiple events safely.
    Returns DeletionResult object with aggregated results.
    """
    result = DeletionResult()
    
    for event_id in event_ids:
        individual_result = delete_event_safely(event_id)
        
        if individual_result.success:
            # Aggregate successful deletions
            for model_name, count in individual_result.deleted_counts.items():
                result.add_deleted(model_name, count)
        else:
            # Aggregate errors
            for error in individual_result.errors:
                result.add_error(error, event_id)
    
    return result

def get_event_deletion_preview(event_id):
    """
    Get a preview of what would be deleted when deleting an event.
    Returns a dictionary with counts of related records.
    """
    event = Event.query.get(event_id)
    if not event:
        return None
    
    preview = {
        'event_name': event.event_name,
        'event_description': event.event_description,
        'event_type': event.event_type,
        'is_partner_event': event.is_partner_event,
        'owner_name': f"{event.owner.first_name} {event.owner.last_name}" if event.owner else "No owner",
        'counts': {}
    }
    
    # Count related records
    preview['counts']['Published_Rosters'] = User_Published_Rosters.query.filter_by(event_id=event_id).count()
    preview['counts']['Penalty_Entries'] = Roster_Penalty_Entries.query.filter_by(event_id=event_id).count()
    preview['counts']['Tournament_Signups'] = Tournament_Signups.query.filter_by(event_id=event_id).count()
    preview['counts']['Tournament_Judges'] = Tournament_Judges.query.filter_by(event_id=event_id).count()
    preview['counts']['Tournament_Partners'] = Tournament_Partners.query.filter_by(event_id=event_id).count()
    preview['counts']['Roster_Judges'] = Roster_Judge.query.filter_by(event_id=event_id).count()
    preview['counts']['Roster_Competitors'] = Roster_Competitors.query.filter_by(event_id=event_id).count()
    preview['counts']['User_Events'] = User_Event.query.filter_by(event_id=event_id).count()
    preview['counts']['Effort_Scores'] = Effort_Score.query.filter_by(event_id=event_id).count()
    
    # Calculate total related records
    preview['total_related'] = sum(preview['counts'].values())
    
    return preview
