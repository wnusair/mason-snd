from flask import session, redirect, url_for, request, flash
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.model import typefmt
from flask_admin.form import Select2Widget
from datetime import datetime
from wtforms import TextAreaField, SelectField, BooleanField
from wtforms.widgets import TextArea
from wtforms_sqlalchemy.fields import QuerySelectField

def init_admin(app):
    """Initialize Flask-Admin with all model views"""
    
    # Import models here to avoid circular imports
    from .extensions import db
    from .models.auth import User, Judges, User_Published_Rosters, Roster_Penalty_Entries
    from .models.admin import User_Requirements, Requirements, Popups
    from .models.events import Event, User_Event, Effort_Score
    from .models.tournaments import Tournament, Tournament_Performance, Tournament_Signups, Form_Fields, Form_Responses, Tournament_Partners
    from .models.rosters import Roster, Roster_Judge, Roster_Competitors, Roster_Partners
    from .models.metrics import MetricsSettings

    class SecureAdminIndexView(AdminIndexView):
        """Custom admin index view with authentication"""
        
        @expose('/')
        def index(self):
            # Check if user is logged in and has admin privileges
            user_id = session.get('user_id')
            if not user_id:
                flash('Please log in to access the admin panel.', 'error')
                return redirect(url_for('auth.login'))
            
            user = User.query.get(user_id)
            if not user or user.role <= 1:
                flash('Admin access required.', 'error')
                return redirect(url_for('profile.index', user_id=user_id))
            
            return super(SecureAdminIndexView, self).index()

    class SecureModelView(ModelView):
        """Base model view with authentication and enhanced functionality"""
        
        def is_accessible(self):
            user_id = session.get('user_id')
            if not user_id:
                return False
            
            user = User.query.get(user_id)
            return user and user.role >= 2
        
        def inaccessible_callback(self, name, **kwargs):
            flash('Admin access required.', 'error')
            return redirect(url_for('auth.login'))
        
        # Enhanced display options
        can_create = True
        can_edit = True
        can_delete = True
        can_view_details = True
        can_export = True
        
        # Pagination
        page_size = 50
        can_set_page_size = True

    class UserModelView(SecureModelView):
        """Enhanced user management with role-based editing"""
        
        column_list = ['id', 'first_name', 'last_name', 'email', 'role', 'points', 'drops', 'bids', 'is_parent', 'account_claimed']
        column_searchable_list = ['first_name', 'last_name', 'email', 'child_first_name', 'child_last_name']
        column_filters = ['role', 'is_parent', 'account_claimed', 'drops', 'bids']
        # Remove role from inline editable to avoid choices error
        column_editable_list = ['drops', 'bids', 'points']
        column_sortable_list = ['id', 'first_name', 'last_name', 'email', 'role', 'points', 'drops', 'bids']
        
        # Custom column labels
        column_labels = {
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'is_parent': 'Parent',
            'account_claimed': 'Claimed',
            'judging_reqs': 'Judging Requirements',
            'emergency_contact_first_name': 'Emergency Contact First Name',
            'emergency_contact_last_name': 'Emergency Contact Last Name',
            'emergency_contact_number': 'Emergency Contact Number',
            'emergency_contact_relationship': 'Emergency Contact Relationship',
            'emergency_contact_email': 'Emergency Contact Email',
            'child_first_name': 'Child First Name',
            'child_last_name': 'Child Last Name'
        }
        
        # Form configuration
        form_excluded_columns = ['user_event', 'judge', 'child', 'published_rosters', 'penalty_entries', 
                               'roster_judge_user', 'roster_judge_child', 'form_responses', 
                               'roster_partner1', 'roster_partner2', 'roster_competitor']
        
        form_widget_args = {
            'judging_reqs': {
                'class': 'form-control',
                'rows': 5
            }
        }
        
        # Custom form fields
        form_overrides = {
            'judging_reqs': TextAreaField,
            'role': SelectField
        }
        
        form_args = {
            'role': {
                'choices': [(0, 'Member'), (1, 'Event Leader'), (2, 'Chair+')],
                'coerce': int
            }
        }
        
        # Custom column formatters
        def _role_formatter(view, context, model, name):
            role_map = {0: 'Member', 1: 'Event Leader', 2: 'Chair+'}
            return role_map.get(model.role, 'Unknown')
        
        column_formatters = {
            'role': _role_formatter
        }
        
        def create_model(self, form):
            try:
                model = self.model()
                form.populate_obj(model)
                # Set default password if creating new user
                if not model.password:
                    model.password = 'default_password'
                self.session.add(model)
                self._on_model_change(form, model, True)
                self.session.commit()
            except Exception as ex:
                if not self.handle_view_exception(ex):
                    flash(f'Failed to create record. {str(ex)}', 'error')
                self.session.rollback()
                return False
            else:
                self.after_model_change(form, model, True)
            return model

    class EventModelView(SecureModelView):
        """Event management with relationship handling"""
        
        column_list = ['id', 'event_name', 'event_description', 'event_emoji', 'owner', 'event_type', 'is_partner_event']
        column_searchable_list = ['event_name', 'event_description']
        column_filters = ['event_type', 'is_partner_event', 'owner']
        # Remove event_type from inline editing to avoid choices issues
        column_editable_list = ['event_name', 'event_emoji', 'is_partner_event']
        
        column_labels = {
            'event_name': 'Event Name',
            'event_description': 'Description',
            'event_emoji': 'Emoji',
            'event_type': 'Type',
            'is_partner_event': 'Partner Event'
        }
        
        form_overrides = {
            'event_type': SelectField,
            'event_description': TextAreaField,
            'owner': QuerySelectField
        }
        
        form_args = {
            'event_type': {
                'choices': [(0, 'Speech'), (1, 'LD'), (2, 'PF')],
                'coerce': int
            },
            'owner': {
                'query_factory': lambda: User.query.all(),
                'get_label': lambda u: f"{u.first_name} {u.last_name}"
            }
        }
        
        # Handle relationship display
        def _owner_formatter(view, context, model, name):
            if model.owner:
                return f"{model.owner.first_name} {model.owner.last_name}"
            return ""
        
        def _event_type_formatter(view, context, model, name):
            type_map = {0: 'Speech', 1: 'LD', 2: 'PF'}
            return type_map.get(model.event_type, 'Unknown')
        
        column_formatters = {
            'owner': _owner_formatter,
            'event_type': _event_type_formatter
        }

    class TournamentModelView(SecureModelView):
        """Tournament management with deadline tracking"""
        
        column_list = ['id', 'name', 'date', 'address', 'signup_deadline', 'performance_deadline', 'results_submitted']
        column_searchable_list = ['name', 'address']
        column_filters = ['results_submitted', 'date', 'signup_deadline', 'performance_deadline']
        column_editable_list = ['results_submitted']
        column_sortable_list = ['id', 'name', 'date', 'signup_deadline', 'performance_deadline']
        
        form_widget_args = {
            'address': {
                'class': 'form-control',
                'rows': 3
            }
        }
        
        form_overrides = {
            'address': TextAreaField
        }

    class PopupsModelView(SecureModelView):
        """Popup management with user relationships"""
        
        column_list = ['id', 'message', 'user', 'admin', 'created_at', 'expires_at', 'completed']
        column_searchable_list = ['message']
        column_filters = ['completed', 'created_at', 'expires_at']
        column_editable_list = ['completed']
        column_sortable_list = ['id', 'created_at', 'expires_at']
        
        form_overrides = {
            'message': TextAreaField,
            'user': QuerySelectField,
            'admin': QuerySelectField
        }
        
        form_widget_args = {
            'message': {
                'class': 'form-control',
                'rows': 4
            }
        }
        
        form_args = {
            'user': {
                'query_factory': lambda: User.query.all(),
                'get_label': lambda u: f"{u.first_name} {u.last_name}"
            },
            'admin': {
                'query_factory': lambda: User.query.filter(User.role >= 2).all(),
                'get_label': lambda u: f"{u.first_name} {u.last_name}"
            }
        }
        
        def _user_formatter(view, context, model, name):
            user = getattr(model, name)
            if user:
                return f"{user.first_name} {user.last_name}"
            return ""
        
        column_formatters = {
            'user': _user_formatter,
            'admin': _user_formatter
        }

    class RequirementsModelView(SecureModelView):
        """Requirements management"""
        
        column_list = ['id', 'body', 'active']
        column_searchable_list = ['body']
        column_filters = ['active']
        column_editable_list = ['active']
        
        form_overrides = {
            'body': TextAreaField
        }
        
        form_widget_args = {
            'body': {
                'class': 'form-control',
                'rows': 4
            }
        }

    class UserEventModelView(SecureModelView):
        """User-Event relationship management"""
        
        column_list = ['id', 'user', 'event', 'effort_score', 'active']
        column_filters = ['active', 'effort_score']
        column_editable_list = ['effort_score', 'active']
        column_sortable_list = ['id', 'effort_score']
        
        form_overrides = {
            'user': QuerySelectField,
            'event': QuerySelectField
        }
        
        form_args = {
            'user': {
                'query_factory': lambda: User.query.all(),
                'get_label': lambda u: f"{u.first_name} {u.last_name}"
            },
            'event': {
                'query_factory': lambda: Event.query.all(),
                'get_label': lambda e: e.event_name
            }
        }
        
        def _user_formatter(view, context, model, name):
            obj = getattr(model, name)
            if obj:
                if name == 'user':
                    return f"{obj.first_name} {obj.last_name}"
                elif name == 'event':
                    return obj.event_name
            return ""
        
        column_formatters = {
            'user': _user_formatter,
            'event': _user_formatter
        }

    class RosterModelView(SecureModelView):
        """Roster management with publication tracking"""
        
        column_list = ['id', 'name', 'tournament', 'published', 'published_at', 'date_made']
        column_searchable_list = ['name']
        column_filters = ['published', 'published_at', 'date_made']
        column_editable_list = ['published']
        column_sortable_list = ['id', 'name', 'date_made', 'published_at']
        
        form_overrides = {
            'tournament': QuerySelectField
        }
        
        form_args = {
            'tournament': {
                'query_factory': lambda: Tournament.query.all(),
                'get_label': lambda t: t.name
            }
        }
        
        def _tournament_formatter(view, context, model, name):
            if model.tournament:
                return model.tournament.name
            return ""
        
        column_formatters = {
            'tournament': _tournament_formatter
        }
    
    admin = Admin(
        app, 
        name='Mason SND Admin',
        template_mode='bootstrap4',
        index_view=SecureAdminIndexView(),
        base_template='admin/custom_base.html'
    )
    
    # Core models
    admin.add_view(UserModelView(User, db.session, name='Users', category='User Management'))
    
    # Enhanced Judges view with relationship display
    class JudgesModelView(SecureModelView):
        column_list = ['id', 'judge', 'child', 'background_check']
        column_filters = ['background_check']
        column_editable_list = ['background_check']
        
        form_overrides = {
            'judge': QuerySelectField,
            'child': QuerySelectField
        }
        
        form_args = {
            'judge': {
                'query_factory': lambda: User.query.all(),
                'get_label': lambda u: f"{u.first_name} {u.last_name}"
            },
            'child': {
                'query_factory': lambda: User.query.all(),
                'get_label': lambda u: f"{u.first_name} {u.last_name}"
            }
        }
        
        def _user_formatter(view, context, model, name):
            user = getattr(model, name)
            if user:
                return f"{user.first_name} {user.last_name}"
            return ""
        
        column_formatters = {
            'judge': _user_formatter,
            'child': _user_formatter
        }
    
    admin.add_view(JudgesModelView(Judges, db.session, name='Judge Relationships', category='User Management'))
    
    # Enhanced User Requirements view with relationship display
    class UserRequirementsModelView(SecureModelView):
        column_list = ['id', 'user', 'requirement', 'complete', 'deadline']
        column_filters = ['complete', 'deadline']
        column_editable_list = ['complete']
        column_sortable_list = ['id', 'deadline']
        
        form_overrides = {
            'user': QuerySelectField,
            'requirement': QuerySelectField
        }
        
        form_args = {
            'user': {
                'query_factory': lambda: User.query.all(),
                'get_label': lambda u: f"{u.first_name} {u.last_name}"
            },
            'requirement': {
                'query_factory': lambda: Requirements.query.all(),
                'get_label': lambda r: r.body[:50] + "..." if len(r.body) > 50 else r.body
            }
        }
        
        def _user_formatter(view, context, model, name):
            if name == 'user' and model.user:
                return f"{model.user.first_name} {model.user.last_name}"
            elif name == 'requirement' and model.requirement:
                return model.requirement.body[:50] + "..." if len(model.requirement.body) > 50 else model.requirement.body
            return ""
        
        column_formatters = {
            'user': _user_formatter,
            'requirement': _user_formatter
        }
    
    admin.add_view(UserRequirementsModelView(User_Requirements, db.session, name='User Requirements', category='User Management'))
    
    # Events & Tournaments
    admin.add_view(EventModelView(Event, db.session, name='Events', category='Events & Tournaments'))
    admin.add_view(UserEventModelView(User_Event, db.session, name='User-Event Relationships', category='Events & Tournaments'))
    admin.add_view(SecureModelView(Effort_Score, db.session, name='Effort Scores', category='Events & Tournaments'))
    admin.add_view(TournamentModelView(Tournament, db.session, name='Tournaments', category='Events & Tournaments'))
    
    # Enhanced Tournament Performance view
    class TournamentPerformanceModelView(SecureModelView):
        column_list = ['id', 'user', 'tournament', 'points', 'rank', 'stage', 'bid']
        column_filters = ['points', 'rank', 'stage', 'bid']
        column_editable_list = ['points', 'rank', 'stage', 'bid']
        column_sortable_list = ['id', 'points', 'rank', 'stage']
        
        form_overrides = {
            'user': QuerySelectField,
            'tournament': QuerySelectField
        }
        
        form_args = {
            'user': {
                'query_factory': lambda: User.query.all(),
                'get_label': lambda u: f"{u.first_name} {u.last_name}"
            },
            'tournament': {
                'query_factory': lambda: Tournament.query.all(),
                'get_label': lambda t: t.name
            }
        }
        
        def _relationship_formatter(view, context, model, name):
            obj = getattr(model, name)
            if obj:
                if name == 'user':
                    return f"{obj.first_name} {obj.last_name}"
                elif name == 'tournament':
                    return obj.name
            return ""
        
        column_formatters = {
            'user': _relationship_formatter,
            'tournament': _relationship_formatter
        }
    
    admin.add_view(TournamentPerformanceModelView(Tournament_Performance, db.session, name='Tournament Performance', category='Events & Tournaments'))
    
    # Enhanced Tournament Signups view
    class TournamentSignupsModelView(SecureModelView):
        column_list = ['id', 'user', 'tournament', 'event', 'partner', 'bringing_judge', 'is_going']
        column_filters = ['bringing_judge', 'is_going']
        column_editable_list = ['bringing_judge', 'is_going']
        column_sortable_list = ['id']
        
        form_overrides = {
            'user': QuerySelectField,
            'tournament': QuerySelectField,
            'event': QuerySelectField,
            'partner': QuerySelectField,
            'judge': QuerySelectField
        }
        
        form_args = {
            'user': {
                'query_factory': lambda: User.query.all(),
                'get_label': lambda u: f"{u.first_name} {u.last_name}"
            },
            'tournament': {
                'query_factory': lambda: Tournament.query.all(),
                'get_label': lambda t: t.name
            },
            'event': {
                'query_factory': lambda: Event.query.all(),
                'get_label': lambda e: e.event_name
            },
            'partner': {
                'query_factory': lambda: User.query.all(),
                'get_label': lambda u: f"{u.first_name} {u.last_name}"
            },
            'judge': {
                'query_factory': lambda: User.query.all(),
                'get_label': lambda u: f"{u.first_name} {u.last_name}"
            }
        }
        
        def _signup_formatter(view, context, model, name):
            obj = getattr(model, name)
            if obj:
                if name in ['user', 'partner', 'judge']:
                    return f"{obj.first_name} {obj.last_name}"
                elif name == 'tournament':
                    return obj.name
                elif name == 'event':
                    return obj.event_name
            return ""
        
        column_formatters = {
            'user': _signup_formatter,
            'tournament': _signup_formatter,
            'event': _signup_formatter,
            'partner': _signup_formatter
        }
    
    admin.add_view(TournamentSignupsModelView(Tournament_Signups, db.session, name='Tournament Signups', category='Events & Tournaments'))
    
    # Enhanced Tournament Partners view
    class TournamentPartnersModelView(SecureModelView):
        column_list = ['id', 'partner1_user', 'partner2_user', 'tournament', 'event']
        
        form_overrides = {
            'partner1_user': QuerySelectField,
            'partner2_user': QuerySelectField,
            'tournament': QuerySelectField,
            'event': QuerySelectField
        }
        
        form_args = {
            'partner1_user': {
                'query_factory': lambda: User.query.all(),
                'get_label': lambda u: f"{u.first_name} {u.last_name}"
            },
            'partner2_user': {
                'query_factory': lambda: User.query.all(),
                'get_label': lambda u: f"{u.first_name} {u.last_name}"
            },
            'tournament': {
                'query_factory': lambda: Tournament.query.all(),
                'get_label': lambda t: t.name
            },
            'event': {
                'query_factory': lambda: Event.query.all(),
                'get_label': lambda e: e.event_name
            }
        }
        
        def _partners_formatter(view, context, model, name):
            obj = getattr(model, name)
            if obj:
                if name in ['partner1_user', 'partner2_user']:
                    return f"{obj.first_name} {obj.last_name}"
                elif name == 'tournament':
                    return obj.name
                elif name == 'event':
                    return obj.event_name
            return ""
        
        column_formatters = {
            'partner1_user': _partners_formatter,
            'partner2_user': _partners_formatter,
            'tournament': _partners_formatter,
            'event': _partners_formatter
        }
    
    admin.add_view(TournamentPartnersModelView(Tournament_Partners, db.session, name='Tournament Partners', category='Events & Tournaments'))
    
    # Enhanced Form Fields view
    class FormFieldsModelView(SecureModelView):
        column_list = ['id', 'label', 'type', 'required', 'tournament']
        column_filters = ['type', 'required']
        column_editable_list = ['required']
        
        form_overrides = {
            'tournament': QuerySelectField
        }
        
        form_args = {
            'tournament': {
                'query_factory': lambda: Tournament.query.all(),
                'get_label': lambda t: t.name
            }
        }
        
        def _tournament_formatter(view, context, model, name):
            if model.tournament:
                return model.tournament.name
            return ""
        
        column_formatters = {
            'tournament': _tournament_formatter
        }
    
    admin.add_view(FormFieldsModelView(Form_Fields, db.session, name='Form Fields', category='Events & Tournaments'))
    
    # Enhanced Form Responses view
    class FormResponsesModelView(SecureModelView):
        column_list = ['id', 'user', 'tournament', 'field', 'response', 'submitted_at']
        column_filters = ['submitted_at']
        column_sortable_list = ['id', 'submitted_at']
        
        form_overrides = {
            'user': QuerySelectField,
            'tournament': QuerySelectField,
            'field': QuerySelectField
        }
        
        form_args = {
            'user': {
                'query_factory': lambda: User.query.all(),
                'get_label': lambda u: f"{u.first_name} {u.last_name}"
            },
            'tournament': {
                'query_factory': lambda: Tournament.query.all(),
                'get_label': lambda t: t.name
            },
            'field': {
                'query_factory': lambda: Form_Fields.query.all(),
                'get_label': lambda f: f.label
            }
        }
        
        def _response_formatter(view, context, model, name):
            obj = getattr(model, name)
            if obj:
                if name == 'user':
                    return f"{obj.first_name} {obj.last_name}"
                elif name == 'tournament':
                    return obj.name
                elif name == 'field':
                    return obj.label
            return ""
        
        column_formatters = {
            'user': _response_formatter,
            'tournament': _response_formatter,
            'field': _response_formatter
        }
    
    admin.add_view(FormResponsesModelView(Form_Responses, db.session, name='Form Responses', category='Events & Tournaments'))
    
    # Rosters
    admin.add_view(RosterModelView(Roster, db.session, name='Rosters', category='Rosters'))
    
    # Enhanced Roster Judges view
    class RosterJudgeModelView(SecureModelView):
        column_list = ['id', 'user', 'child', 'event', 'roster', 'people_bringing']
        column_editable_list = ['people_bringing']
        
        form_overrides = {
            'user': QuerySelectField,
            'child': QuerySelectField,
            'event': QuerySelectField,
            'roster': QuerySelectField
        }
        
        form_args = {
            'user': {
                'query_factory': lambda: User.query.all(),
                'get_label': lambda u: f"{u.first_name} {u.last_name}"
            },
            'child': {
                'query_factory': lambda: User.query.all(),
                'get_label': lambda u: f"{u.first_name} {u.last_name}"
            },
            'event': {
                'query_factory': lambda: Event.query.all(),
                'get_label': lambda e: e.event_name
            },
            'roster': {
                'query_factory': lambda: Roster.query.all(),
                'get_label': lambda r: r.name
            }
        }
        
        def _roster_judge_formatter(view, context, model, name):
            obj = getattr(model, name)
            if obj:
                if name in ['user', 'child']:
                    return f"{obj.first_name} {obj.last_name}"
                elif name == 'event':
                    return obj.event_name
                elif name == 'roster':
                    return obj.name
            return ""
        
        column_formatters = {
            'user': _roster_judge_formatter,
            'child': _roster_judge_formatter,
            'event': _roster_judge_formatter,
            'roster': _roster_judge_formatter
        }
    
    admin.add_view(RosterJudgeModelView(Roster_Judge, db.session, name='Roster Judges', category='Rosters'))
    
    # Enhanced Roster Competitors view
    class RosterCompetitorsModelView(SecureModelView):
        column_list = ['id', 'user', 'event', 'judge', 'roster']
        
        form_overrides = {
            'user': QuerySelectField,
            'event': QuerySelectField,
            'judge': QuerySelectField,
            'roster': QuerySelectField
        }
        
        form_args = {
            'user': {
                'query_factory': lambda: User.query.all(),
                'get_label': lambda u: f"{u.first_name} {u.last_name}"
            },
            'event': {
                'query_factory': lambda: Event.query.all(),
                'get_label': lambda e: e.event_name
            },
            'judge': {
                'query_factory': lambda: User.query.all(),
                'get_label': lambda u: f"{u.first_name} {u.last_name}"
            },
            'roster': {
                'query_factory': lambda: Roster.query.all(),
                'get_label': lambda r: r.name
            }
        }
        
        def _competitor_formatter(view, context, model, name):
            obj = getattr(model, name)
            if obj:
                if name in ['user', 'judge']:
                    return f"{obj.first_name} {obj.last_name}"
                elif name == 'event':
                    return obj.event_name
                elif name == 'roster':
                    return obj.name
            return ""
        
        column_formatters = {
            'user': _competitor_formatter,
            'event': _competitor_formatter,
            'judge': _competitor_formatter,
            'roster': _competitor_formatter
        }
    
    admin.add_view(RosterCompetitorsModelView(Roster_Competitors, db.session, name='Roster Competitors', category='Rosters'))
    
    # Enhanced Roster Partners view
    class RosterPartnersModelView(SecureModelView):
        column_list = ['id', 'partner1_user', 'partner2_user', 'roster']
        
        form_overrides = {
            'partner1_user': QuerySelectField,
            'partner2_user': QuerySelectField,
            'roster': QuerySelectField
        }
        
        form_args = {
            'partner1_user': {
                'query_factory': lambda: User.query.all(),
                'get_label': lambda u: f"{u.first_name} {u.last_name}"
            },
            'partner2_user': {
                'query_factory': lambda: User.query.all(),
                'get_label': lambda u: f"{u.first_name} {u.last_name}"
            },
            'roster': {
                'query_factory': lambda: Roster.query.all(),
                'get_label': lambda r: r.name
            }
        }
        
        def _roster_partners_formatter(view, context, model, name):
            obj = getattr(model, name)
            if obj:
                if name in ['partner1_user', 'partner2_user']:
                    return f"{obj.first_name} {obj.last_name}"
                elif name == 'roster':
                    return obj.name
            return ""
        
        column_formatters = {
            'partner1_user': _roster_partners_formatter,
            'partner2_user': _roster_partners_formatter,
            'roster': _roster_partners_formatter
        }
    
    admin.add_view(RosterPartnersModelView(Roster_Partners, db.session, name='Roster Partners', category='Rosters'))
    
    # Enhanced Published Rosters view
    class PublishedRostersModelView(SecureModelView):
        column_list = ['id', 'user', 'roster', 'tournament', 'event', 'notified', 'created_at']
        column_filters = ['notified', 'created_at']
        column_editable_list = ['notified']
        column_sortable_list = ['id', 'created_at']
        
        form_overrides = {
            'user': QuerySelectField,
            'roster': QuerySelectField,
            'tournament': QuerySelectField,
            'event': QuerySelectField
        }
        
        form_args = {
            'user': {
                'query_factory': lambda: User.query.all(),
                'get_label': lambda u: f"{u.first_name} {u.last_name}"
            },
            'roster': {
                'query_factory': lambda: Roster.query.all(),
                'get_label': lambda r: r.name
            },
            'tournament': {
                'query_factory': lambda: Tournament.query.all(),
                'get_label': lambda t: t.name
            },
            'event': {
                'query_factory': lambda: Event.query.all(),
                'get_label': lambda e: e.event_name
            }
        }
        
        def _published_formatter(view, context, model, name):
            obj = getattr(model, name)
            if obj:
                if name == 'user':
                    return f"{obj.first_name} {obj.last_name}"
                elif name == 'roster':
                    return obj.name
                elif name == 'tournament':
                    return obj.name
                elif name == 'event':
                    return obj.event_name
            return ""
        
        column_formatters = {
            'user': _published_formatter,
            'roster': _published_formatter,
            'tournament': _published_formatter,
            'event': _published_formatter
        }
    
    admin.add_view(PublishedRostersModelView(User_Published_Rosters, db.session, name='Published Rosters', category='Rosters'))
    
    # Enhanced Penalty Entries view
    class PenaltyEntriesModelView(SecureModelView):
        column_list = ['id', 'penalized_user', 'roster', 'tournament', 'event', 'original_rank', 'drops_applied', 'created_at']
        column_filters = ['original_rank', 'drops_applied', 'created_at']
        column_editable_list = ['original_rank', 'drops_applied']
        column_sortable_list = ['id', 'original_rank', 'drops_applied', 'created_at']
        
        form_overrides = {
            'penalized_user': QuerySelectField,
            'roster': QuerySelectField,
            'tournament': QuerySelectField,
            'event': QuerySelectField
        }
        
        form_args = {
            'penalized_user': {
                'query_factory': lambda: User.query.all(),
                'get_label': lambda u: f"{u.first_name} {u.last_name}"
            },
            'roster': {
                'query_factory': lambda: Roster.query.all(),
                'get_label': lambda r: r.name
            },
            'tournament': {
                'query_factory': lambda: Tournament.query.all(),
                'get_label': lambda t: t.name
            },
            'event': {
                'query_factory': lambda: Event.query.all(),
                'get_label': lambda e: e.event_name
            }
        }
        
        def _penalty_formatter(view, context, model, name):
            obj = getattr(model, name)
            if obj:
                if name == 'penalized_user':
                    return f"{obj.first_name} {obj.last_name}"
                elif name == 'roster':
                    return obj.name
                elif name == 'tournament':
                    return obj.name
                elif name == 'event':
                    return obj.event_name
            return ""
        
        column_formatters = {
            'penalized_user': _penalty_formatter,
            'roster': _penalty_formatter,
            'tournament': _penalty_formatter,
            'event': _penalty_formatter
        }
    
    admin.add_view(PenaltyEntriesModelView(Roster_Penalty_Entries, db.session, name='Penalty Entries', category='Rosters'))
    
    # Admin & System
    admin.add_view(RequirementsModelView(Requirements, db.session, name='Requirements', category='Admin & System'))
    admin.add_view(PopupsModelView(Popups, db.session, name='Popups', category='Admin & System'))
    admin.add_view(SecureModelView(MetricsSettings, db.session, name='Metrics Settings', category='Admin & System'))
    
    return admin
