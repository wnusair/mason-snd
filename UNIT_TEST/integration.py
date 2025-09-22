"""
Integration with main Mason-SND Flask application.
Registers the testing dashboard and provides testing mode functionality.
"""
import os
from flask import Flask, request, session, redirect, url_for, flash

def enable_testing_mode(app):
    """
    Enable testing mode for the Flask application.
    This adds the testing dashboard and configures the app for testing.
    """
    
    # Register testing dashboard blueprint
    from UNIT_TEST.web_dashboard.dashboard import register_test_dashboard
    register_test_dashboard(app)
    
    # Add testing mode context processor
    @app.context_processor
    def inject_testing_mode():
        return dict(testing_mode=app.config.get('TESTING', False))
    
    # Add testing mode toggle route (admin only)
    @app.route('/admin/testing_mode', methods=['GET', 'POST'])
    def toggle_testing_mode():
        # This would be protected by admin authentication in production
        if request.method == 'POST':
            enable = request.form.get('enable') == 'true'
            if enable:
                session['testing_mode'] = True
                flash('Testing mode enabled. Access the testing dashboard at /test_dashboard', 'info')
            else:
                session['testing_mode'] = False
                flash('Testing mode disabled.', 'info')
        
        return redirect(request.referrer or url_for('main.index'))
    
    # Testing mode middleware
    @app.before_request
    def check_testing_mode():
        # Allow access to testing routes when in testing mode
        if request.path.startswith('/test_dashboard'):
            if not (app.config.get('TESTING', False) or session.get('testing_mode', False)):
                flash('Testing dashboard is only available in testing mode.', 'warning')
                return redirect(url_for('main.index'))
    
    print("✅ Testing mode enabled for Mason-SND application")
    print("📊 Testing dashboard available at: /test_dashboard")

def create_testing_blueprint():
    """Create a blueprint for testing integration"""
    from flask import Blueprint, render_template, jsonify
    
    testing_bp = Blueprint('testing_integration', __name__)
    
    @testing_bp.route('/enable_testing')
    def enable_testing():
        """Enable testing mode (for development)"""
        from flask import current_app
        current_app.config['TESTING'] = True
        return jsonify({'testing_enabled': True})
    
    @testing_bp.route('/disable_testing')
    def disable_testing():
        """Disable testing mode"""
        from flask import current_app
        current_app.config['TESTING'] = False
        return jsonify({'testing_enabled': False})
    
    return testing_bp

def add_testing_commands(app):
    """Add CLI commands for testing"""
    import click
    
    @app.cli.command()
    @click.option('--test-type', default='all', help='Type of tests to run')
    @click.option('--coverage', is_flag=True, help='Run with coverage report')
    def run_tests(test_type, coverage):
        """Run the test suite"""
        import subprocess
        import sys
        
        cmd = [sys.executable, '-m', 'UNIT_TEST.run_tests']
        if test_type != 'all':
            cmd.extend(['--test', test_type])
        
        if coverage:
            cmd = ['coverage', 'run', '--source=mason_snd'] + cmd
        
        result = subprocess.run(cmd, cwd=app.root_path)
        
        if coverage and result.returncode == 0:
            subprocess.run(['coverage', 'report'], cwd=app.root_path)
            subprocess.run(['coverage', 'html'], cwd=app.root_path)
    
    @app.cli.command()
    @click.option('--num-users', default=30, help='Number of users to create')
    @click.option('--num-events', default=5, help='Number of events to create')
    @click.option('--num-tournaments', default=2, help='Number of tournaments to create')
    def simulate_tournament(num_users, num_events, num_tournaments):
        """Run tournament simulation"""
        from UNIT_TEST.mock_data.tournament_simulator import TournamentSimulator
        
        with app.app_context():
            simulator = TournamentSimulator()
            results = simulator.simulate_complete_tournament_flow(
                num_users=num_users,
                num_events=num_events,
                num_tournaments=num_tournaments
            )
            
            click.echo(f"✅ Simulation completed!")
            click.echo(f"📊 Created {results['summary']['total_users']} users")
            click.echo(f"📅 Created {results['summary']['total_events']} events")
            click.echo(f"🏆 Created {results['summary']['total_tournaments']} tournaments")
    
    @app.cli.command()
    def cleanup_test_data():
        """Clean up all test databases"""
        from UNIT_TEST.database_manager import TestDatabaseManager
        
        db_manager = TestDatabaseManager()
        db_manager.cleanup_all_test_databases()
        click.echo("✅ Test databases cleaned up")

# Factory function to integrate testing with existing app
def integrate_testing_with_app(app):
    """
    Integrate testing system with the main Flask application.
    Adds testing routes and middleware safely.
    """
    try:
        # Only integrate if testing is explicitly enabled
        if not app.config.get('ENABLE_TESTING', False):
            app.logger.info("Testing integration skipped - ENABLE_TESTING not set")
            return False
        
        # Register the web dashboard blueprint
        from UNIT_TEST.web_dashboard.dashboard import test_dashboard_bp
        app.register_blueprint(test_dashboard_bp, url_prefix='/test_dashboard')
        
        # Add CLI commands for testing
        @app.cli.command()
        def run_tests():
            """Run the test suite via Flask CLI"""
            from UNIT_TEST.master_controller import run_quick_test
            run_quick_test()
        
        @app.cli.command()
        def verify_tests():
            """Verify testing system via Flask CLI"""
            from UNIT_TEST.final_verification import run_final_verification
            results = run_final_verification()
            print(f"Verification completed. Success rate: {results.get('success_rate', 0):.1f}%")
        
        @app.cli.command()
        def cleanup_tests():
            """Clean up test data via Flask CLI"""
            from UNIT_TEST.production_safety import emergency_cleanup
            results = emergency_cleanup()
            print(f"Cleanup completed. Removed {results.get('test_databases_removed', 0)} databases and {results.get('temp_directories_removed', 0)} directories")
        
        # Add testing status to template context
        @app.context_processor
        def inject_testing_status():
            """Inject testing system status into templates"""
            try:
                from UNIT_TEST.production_safety import get_safety_guard
                safety_guard = get_safety_guard()
                safety_report = safety_guard.generate_safety_report()
                
                return {
                    'testing_enabled': True,
                    'testing_safe': safety_report['safety_status'] == 'SAFE',
                    'testing_dashboard_url': '/test_dashboard'
                }
            except Exception:
                return {
                    'testing_enabled': True,
                    'testing_safe': False,
                    'testing_dashboard_url': '/test_dashboard'
                }
        
        # Add admin integration check
        try:
            # Check if admin blueprint exists
            admin_bp = app.blueprints.get('admin')
            if admin_bp:
                app.logger.info("Testing system integrated with admin panel")
            else:
                app.logger.info("Testing system integrated - admin panel not detected")
        except Exception:
            pass
        
        app.logger.info("Testing system successfully integrated")
        return True
        
    except Exception as e:
        app.logger.error(f"Failed to integrate testing system: {e}")
        return False