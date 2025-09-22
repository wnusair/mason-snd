"""
Web-based testing dashboard for Mason-SND application.
Provides a visual interface to run tests, view results, and manage test data.
"""
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from flask_wtf.csrf import validate_csrf
from datetime import datetime
import json
import threading
import uuid
import os

# Create blueprint for test dashboard with proper template folder
test_dashboard_bp = Blueprint('test_dashboard', __name__, 
                             template_folder='templates',
                             static_folder='static',
                             url_prefix='/')

# Global storage for test results (in production, use Redis or database)
test_sessions = {}

@test_dashboard_bp.route('/')
def dashboard():
    """Main testing dashboard"""
    try:
        from flask_wtf.csrf import generate_csrf
        return render_template('test_dashboard/simple_dashboard.html', csrf_token=generate_csrf)
    except Exception as e:
        # Simple fallback if template fails
        return f'''
        <html>
        <head><title>Mason-SND Testing Dashboard</title></head>
        <body>
            <h1>🧪 Mason-SND Testing Dashboard</h1>
            <p>Dashboard is working! Template error: {str(e)}</p>
            <div style="margin: 20px 0;">
                <a href="/test_dashboard/mock_tournament" style="margin-right: 10px;">Mock Tournament</a>
                <a href="/test_dashboard/database_manager" style="margin-right: 10px;">Database Manager</a>
                <a href="/test_dashboard/coverage_report">Coverage Report</a>
            </div>
        </body>
        </html>
        '''

@test_dashboard_bp.route('/run_tests', methods=['POST'])
def run_tests():
    """Run tests via AJAX and return session ID"""
    try:
        # Validate CSRF token for AJAX requests
        validate_csrf(request.headers.get('X-CSRFToken'))
    except Exception as e:
        return jsonify({'error': 'CSRF token validation failed'}), 400
    
    test_type = request.json.get('test_type', 'all')
    session_id = str(uuid.uuid4())
    
    # Initialize test session
    test_sessions[session_id] = {
        'status': 'running',
        'progress': 0,
        'results': None,
        'start_time': datetime.now(),
        'test_type': test_type
    }
    
    # Run tests in background thread
    thread = threading.Thread(target=execute_tests, args=(session_id, test_type))
    thread.daemon = True
    thread.start()
    
    return jsonify({'session_id': session_id})

@test_dashboard_bp.route('/test_status/<session_id>')
def test_status(session_id):
    """Get status of running tests"""
    if session_id not in test_sessions:
        return jsonify({'error': 'Invalid session ID'}), 404
    
    session_data = test_sessions[session_id]
    return jsonify({
        'status': session_data['status'],
        'progress': session_data['progress'],
        'results': session_data['results']
    })

@test_dashboard_bp.route('/test_results/<session_id>')
def test_results(session_id):
    """View detailed test results"""
    if session_id not in test_sessions:
        return redirect(url_for('test_dashboard.dashboard'))
    
    session_data = test_sessions[session_id]
    return render_template('test_dashboard/results.html', 
                         session_data=session_data, 
                         session_id=session_id)

@test_dashboard_bp.route('/mock_tournament')
def mock_tournament():
    """Mock tournament simulation interface"""
    try:
        return render_template('test_dashboard/mock_tournament.html')
    except Exception as e:
        return f'''
        <html>
        <head><title>Mock Tournament</title></head>
        <body>
            <h1>Mock Tournament Simulation</h1>
            <p>Mock tournament interface would go here.</p>
            <p>Template error: {str(e)}</p>
            <a href="/test_dashboard/">Back to Dashboard</a>
        </body>
        </html>
        '''

@test_dashboard_bp.route('/create_mock_tournament', methods=['POST'])
def create_mock_tournament():
    """Create and run mock tournament simulation"""
    try:
        # Validate CSRF token for AJAX requests
        validate_csrf(request.headers.get('X-CSRFToken'))
    except Exception as e:
        return jsonify({'error': 'CSRF token validation failed'}), 400
    
    session_id = str(uuid.uuid4())
    
    # Get simulation parameters
    num_users = int(request.json.get('num_users', 30))
    num_events = int(request.json.get('num_events', 5))
    num_tournaments = int(request.json.get('num_tournaments', 2))
    
    # Initialize simulation session
    test_sessions[session_id] = {
        'status': 'running',
        'progress': 0,
        'results': None,
        'start_time': datetime.now(),
        'test_type': 'mock_tournament',
        'parameters': {
            'num_users': num_users,
            'num_events': num_events,
            'num_tournaments': num_tournaments
        }
    }
    
    # Run simulation in background
    thread = threading.Thread(target=execute_mock_tournament, args=(session_id,))
    thread.daemon = True
    thread.start()
    
    return jsonify({'session_id': session_id})

@test_dashboard_bp.route('/database_manager')
def database_manager():
    """Database management interface"""
    try:
        return render_template('test_dashboard/database_manager.html')
    except Exception as e:
        return f'''
        <html>
        <head><title>Database Manager</title></head>
        <body>
            <h1>Database Manager</h1>
            <p>Database manager interface would go here.</p>
            <p>Template error: {str(e)}</p>
            <a href="/test_dashboard/">Back to Dashboard</a>
        </body>
        </html>
        '''

@test_dashboard_bp.route('/list_test_databases')
def list_test_databases():
    """List all test databases"""
    try:
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        
        from database_manager import TestDatabaseManager
        db_manager = TestDatabaseManager()
        databases = db_manager.list_test_databases()
        
        return jsonify({'databases': databases})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@test_dashboard_bp.route('/cleanup_databases', methods=['POST'])
def cleanup_databases():
    """Clean up test databases"""
    try:
        # Validate CSRF token for AJAX requests
        validate_csrf(request.headers.get('X-CSRFToken'))
    except Exception as e:
        return jsonify({'error': 'CSRF token validation failed'}), 400
    
    try:
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        
        from database_manager import TestDatabaseManager
        db_manager = TestDatabaseManager()
        db_manager.cleanup_all_test_databases()
        
        return jsonify({'success': True, 'message': 'All test databases cleaned up'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@test_dashboard_bp.route('/coverage_report')
def coverage_report():
    """View test coverage report"""
    try:
        return render_template('test_dashboard/coverage.html')
    except Exception as e:
        return f'''
        <html>
        <head><title>Coverage Report</title></head>
        <body>
            <h1>Test Coverage Report</h1>
            <p>Coverage report interface would go here.</p>
            <p>Template error: {str(e)}</p>
            <a href="/test_dashboard/">Back to Dashboard</a>
        </body>
        </html>
        '''

def execute_tests(session_id, test_type):
    """Execute tests in background thread"""
    try:
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        
        # Update progress
        test_sessions[session_id]['progress'] = 10
        
        if test_type == 'all':
            from terminal_tests.test_suite import TestRunner
            runner = TestRunner()
            
            # Update progress during testing
            test_sessions[session_id]['progress'] = 50
            
            results = runner.run_all_tests()
            
            # Format results for web display
            formatted_results = {
                'summary': {
                    'total': results['total'],
                    'passed': results['passed'],
                    'failed': results['failed'],
                    'errors': results['errors'],
                    'success_rate': (results['passed'] / results['total']) * 100 if results['total'] > 0 else 0
                },
                'details': results['details'],
                'timestamp': datetime.now().isoformat()
            }
            
            test_sessions[session_id]['results'] = formatted_results
            
        elif test_type in ['auth', 'events', 'tournaments', 'profile', 'metrics', 'rosters', 'admin', 'main', 'data']:
            # Run specific test category
            from terminal_tests.test_suite import TestRunner
            import unittest
            
            # Import test classes
            from terminal_tests.test_suite import (
                TestAuthRoutes, TestEventRoutes, TestTournamentRoutes,
                TestProfileRoutes, TestMetricsRoutes, TestRosterRoutes,
                TestAdminRoutes, TestMainRoutes, TestDataIntegrity
            )
            
            test_classes = {
                'auth': TestAuthRoutes,
                'events': TestEventRoutes,
                'tournaments': TestTournamentRoutes,
                'profile': TestProfileRoutes,
                'metrics': TestMetricsRoutes,
                'rosters': TestRosterRoutes,
                'admin': TestAdminRoutes,
                'main': TestMainRoutes,
                'data': TestDataIntegrity
            }
            
            test_class = test_classes[test_type]
            
            test_sessions[session_id]['progress'] = 50
            
            suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
            runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
            result = runner.run(suite)
            
            # Format results
            passed = result.testsRun - len(result.failures) - len(result.errors)
            formatted_results = {
                'summary': {
                    'total': result.testsRun,
                    'passed': passed,
                    'failed': len(result.failures),
                    'errors': len(result.errors),
                    'success_rate': (passed / result.testsRun) * 100 if result.testsRun > 0 else 0
                },
                'details': [{
                    'class': test_class.__name__,
                    'passed': passed,
                    'failed': len(result.failures),
                    'errors': len(result.errors),
                    'total': result.testsRun,
                    'failures': result.failures,
                    'errors': result.errors
                }],
                'timestamp': datetime.now().isoformat()
            }
            
            test_sessions[session_id]['results'] = formatted_results
        
        test_sessions[session_id]['progress'] = 100
        test_sessions[session_id]['status'] = 'completed'
        
    except Exception as e:
        test_sessions[session_id]['status'] = 'error'
        test_sessions[session_id]['results'] = {'error': str(e)}

def execute_mock_tournament(session_id):
    """Execute mock tournament simulation"""
    try:
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        
        from database_manager import TestDatabaseManager, create_test_app
        from mock_data.generators import MockDataGenerator
        
        # Update progress
        test_sessions[session_id]['progress'] = 10
        
        # Create isolated test database
        db_manager = TestDatabaseManager()
        test_db_path = db_manager.create_test_database(f"mock_tournament_{session_id}")
        
        test_sessions[session_id]['progress'] = 20
        
        # Create test app
        app, _ = create_test_app(test_db_path)
        
        with app.app_context():
            from mason_snd.extensions import db
            db.create_all()
            
            test_sessions[session_id]['progress'] = 30
            
            # Generate mock data
            generator = MockDataGenerator(app.app_context())
            params = test_sessions[session_id]['parameters']
            
            mock_data = generator.generate_complete_mock_scenario(
                num_users=params['num_users'],
                num_events=params['num_events'],
                num_tournaments=params['num_tournaments']
            )
            
            test_sessions[session_id]['progress'] = 50
            
            # Create users in database
            from mason_snd.models.auth import User, Judges
            created_users = []
            
            for user_data in mock_data['users']:
                user = User(**user_data)
                db.session.add(user)
                db.session.commit()
                created_users.append(user.id)
            
            test_sessions[session_id]['progress'] = 70
            
            # Create events
            from mason_snd.models.events import Event
            created_events = []
            
            for event_data in mock_data['events']:
                event = Event(**event_data)
                db.session.add(event)
                db.session.commit()
                created_events.append(event.id)
            
            test_sessions[session_id]['progress'] = 85
            
            # Create tournaments
            from mason_snd.models.tournaments import Tournament
            created_tournaments = []
            
            for tournament_data in mock_data['tournaments']:
                tournament = Tournament(**tournament_data)
                db.session.add(tournament)
                db.session.commit()
                created_tournaments.append(tournament.id)
            
            test_sessions[session_id]['progress'] = 95
            
            # Create judge relationships
            for judge_data in mock_data['judges']:
                judge = Judges(**judge_data)
                db.session.add(judge)
            
            db.session.commit()
            
            # Prepare results
            simulation_results = {
                'summary': {
                    'users_created': len(created_users),
                    'events_created': len(created_events),
                    'tournaments_created': len(created_tournaments),
                    'judges_created': len(mock_data['judges']),
                    'test_database': test_db_path
                },
                'users': [f"User {i}: {u['first_name']} {u['last_name']}" for i, u in enumerate(mock_data['users'][:10])],
                'events': [f"Event {i}: {e['name']}" for i, e in enumerate(mock_data['events'])],
                'tournaments': [f"Tournament {i}: {t['name']}" for i, t in enumerate(mock_data['tournaments'])],
                'timestamp': datetime.now().isoformat()
            }
            
            test_sessions[session_id]['results'] = simulation_results
        
        test_sessions[session_id]['progress'] = 100
        test_sessions[session_id]['status'] = 'completed'
        
    except Exception as e:
        test_sessions[session_id]['status'] = 'error'
        test_sessions[session_id]['results'] = {'error': str(e)}

# Function to register the blueprint with the main app
def register_test_dashboard(app):
    """Register the test dashboard blueprint with the Flask app"""
    app.register_blueprint(test_dashboard_bp)