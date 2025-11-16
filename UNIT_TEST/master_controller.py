"""
Master testing controller that orchestrates all testing functionality.
Provides comprehensive testing workflows and ensures proper cleanup.
"""
import os
import sys
import json
from datetime import datetime
import tempfile
import shutil

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

class MasterTestController:
    """
    Master controller for all testing functionality.
    Orchestrates the complete testing workflow from setup to cleanup.
    """
    
    def __init__(self):
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.test_session = {
            'session_id': self.session_id,
            'start_time': datetime.now(),
            'test_results': {},
            'created_resources': [],
            'cleanup_required': [],
            'overall_success': True
        }
        self.progress_callback = None
    
    def set_progress_callback(self, callback):
        """Set callback function for progress updates"""
        self.progress_callback = callback
    
    def update_progress(self, percentage, message):
        """Update progress and call callback if set"""
        if self.progress_callback:
            self.progress_callback(percentage, message)
        print(f"[{percentage:3d}%] {message}")
    
    def run_comprehensive_test_suite(self, test_config=None):
        """
        Run the complete testing suite with all components
        
        Args:
            test_config: Configuration dictionary for test parameters
        
        Returns:
            dict: Complete test results
        """
        if test_config is None:
            test_config = {
                'num_users': 30,
                'num_events': 5,
                'num_tournaments': 3,
                'run_unit_tests': True,
                'run_simulation': True,
                'run_roster_tests': True,
                'run_metrics_tests': True,
                'cleanup_after': True
            }
        
        try:
            self.update_progress(0, "Initializing comprehensive test suite")
            
            # Stage 1: Setup test environment
            self.update_progress(5, "Setting up test environment")
            test_db_path = self._setup_test_environment()
            if test_db_path:
                self.test_session['created_resources'].append(test_db_path)
                self.test_session['cleanup_required'].append(('database', test_db_path))
            
            # Stage 2: Run unit tests if requested
            if test_config.get('run_unit_tests', True):
                self.update_progress(15, "Running unit tests")
                unit_test_results = self._run_unit_tests()
                self.test_session['test_results']['unit_tests'] = unit_test_results
                if not unit_test_results.get('overall_success', False):
                    self.test_session['overall_success'] = False
            
            # Stage 3: Create tournament simulation
            if test_config.get('run_simulation', True):
                self.update_progress(35, "Creating tournament simulation")
                simulation_results = self._run_tournament_simulation(
                    test_config['num_users'],
                    test_config['num_events'],
                    test_config['num_tournaments'],
                    test_db_path
                )
                self.test_session['test_results']['simulation'] = simulation_results
                if not simulation_results.get('success', False):
                    self.test_session['overall_success'] = False
            else:
                simulation_results = None
            
            # Stage 4: Test roster functionality
            if test_config.get('run_roster_tests', True) and simulation_results:
                self.update_progress(60, "Testing roster functionality")
                roster_test_results = self._run_roster_tests(simulation_results)
                self.test_session['test_results']['roster_tests'] = roster_test_results
                if not roster_test_results.get('workflow_results', {}).get('overall_success', False):
                    self.test_session['overall_success'] = False
            
            # Stage 5: Test metrics functionality
            if test_config.get('run_metrics_tests', True) and simulation_results:
                self.update_progress(80, "Testing metrics functionality")
                metrics_test_results = self._run_metrics_tests(simulation_results)
                self.test_session['test_results']['metrics_tests'] = metrics_test_results
                if not metrics_test_results.get('workflow_results', {}).get('overall_success', False):
                    self.test_session['overall_success'] = False
            
            # Stage 6: Generate comprehensive report
            self.update_progress(95, "Generating test report")
            report = self._generate_comprehensive_report()
            self.test_session['test_results']['report'] = report
            
            # Stage 7: Cleanup if requested
            if test_config.get('cleanup_after', True):
                self.update_progress(98, "Cleaning up test resources")
                self._cleanup_test_resources()
            
            self.update_progress(100, "Test suite completed successfully")
            
            # Finalize session
            self.test_session['end_time'] = datetime.now()
            self.test_session['duration'] = (
                self.test_session['end_time'] - self.test_session['start_time']
            ).total_seconds()
            
            return self.test_session
            
        except Exception as e:
            self.update_progress(100, f"Test suite failed: {str(e)}")
            self.test_session['overall_success'] = False
            self.test_session['error'] = str(e)
            
            # Emergency cleanup
            try:
                self._cleanup_test_resources()
            except:
                pass
            
            return self.test_session
    
    def _setup_test_environment(self):
        """Setup isolated test environment"""
        try:
            from UNIT_TEST.database_manager import TestDatabaseManager
            
            db_manager = TestDatabaseManager()
            test_db_path = db_manager.create_test_database(f"comprehensive_{self.session_id}")
            
            return test_db_path
            
        except Exception as e:
            print(f"Failed to setup test environment: {e}")
            return None
    
    def _run_unit_tests(self):
        """Run the complete unit test suite"""
        try:
            from UNIT_TEST.terminal_tests.test_suite import TestRunner
            
            runner = TestRunner()
            results = runner.run_all_tests()
            
            return {
                'overall_success': results['failed'] == 0 and results['errors'] == 0,
                'summary': {
                    'total': results['total'],
                    'passed': results['passed'],
                    'failed': results['failed'],
                    'errors': results['errors'],
                    'success_rate': (results['passed'] / results['total']) * 100 if results['total'] > 0 else 0
                },
                'details': results['details']
            }
            
        except Exception as e:
            return {
                'overall_success': False,
                'error': str(e)
            }
    
    def _run_tournament_simulation(self, num_users, num_events, num_tournaments, test_db_path):
        """Run tournament simulation with database integration"""
        try:
            from UNIT_TEST.mock_data.tournament_simulator import (
                TournamentSimulator, 
                create_database_with_simulation
            )
            
            # Create simulation
            simulator = TournamentSimulator()
            simulation_results = simulator.simulate_complete_tournament_flow(
                num_users=num_users,
                num_events=num_events,
                num_tournaments=num_tournaments
            )
            
            # Create database with simulation data
            if test_db_path:
                db_result = create_database_with_simulation(simulation_results, test_db_path)
                simulation_results['database_integration'] = db_result
            
            return {
                'success': True,
                'simulation_results': simulation_results
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _run_roster_tests(self, simulation_results):
        """Run roster functionality tests"""
        try:
            from UNIT_TEST.roster_testing import run_roster_tests
            
            # Extract tournament data for testing
            tournaments_data = simulation_results['simulation_results']['tournaments']['tournaments']
            
            if tournaments_data:
                # Test with first tournament
                tournament = tournaments_data[0]
                participants = [signup['user_id'] for signup in tournament.get('signups', [])]
                
                if participants:
                    results = run_roster_tests(tournament, participants)
                    return results
            
            return {
                'workflow_results': {'overall_success': False},
                'error': 'No tournament data available for roster testing'
            }
            
        except Exception as e:
            return {
                'workflow_results': {'overall_success': False},
                'error': str(e)
            }
    
    def _run_metrics_tests(self, simulation_results):
        """Run metrics functionality tests"""
        try:
            from UNIT_TEST.metrics_testing import run_metrics_tests
            
            results = run_metrics_tests(simulation_results['simulation_results'])
            return results
            
        except Exception as e:
            return {
                'workflow_results': {'overall_success': False},
                'error': str(e)
            }
    
    def _generate_comprehensive_report(self):
        """Generate comprehensive test report"""
        try:
            report = {
                'session_info': {
                    'session_id': self.session_id,
                    'timestamp': datetime.now().isoformat(),
                    'overall_success': self.test_session['overall_success']
                },
                'summary': {},
                'detailed_results': {},
                'recommendations': []
            }
            
            # Summarize results
            total_tests = 0
            passed_tests = 0
            
            # Unit tests
            unit_results = self.test_session['test_results'].get('unit_tests', {})
            if unit_results.get('summary'):
                total_tests += unit_results['summary']['total']
                passed_tests += unit_results['summary']['passed']
                report['detailed_results']['unit_tests'] = unit_results['summary']
            
            # Roster tests
            roster_results = self.test_session['test_results'].get('roster_tests', {})
            if roster_results.get('test_summary'):
                total_tests += roster_results['test_summary']['total_tests']
                passed_tests += roster_results['test_summary']['passed_tests']
                report['detailed_results']['roster_tests'] = roster_results['test_summary']
            
            # Metrics tests
            metrics_results = self.test_session['test_results'].get('metrics_tests', {})
            if metrics_results.get('test_summary'):
                total_tests += metrics_results['test_summary']['total_tests']
                passed_tests += metrics_results['test_summary']['passed_tests']
                report['detailed_results']['metrics_tests'] = metrics_results['test_summary']
            
            # Calculate overall statistics
            report['summary'] = {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': total_tests - passed_tests,
                'overall_success_rate': (passed_tests / total_tests) * 100 if total_tests > 0 else 0
            }
            
            # Generate recommendations
            if report['summary']['overall_success_rate'] < 90:
                report['recommendations'].append("Consider reviewing failed tests and improving test coverage")
            
            if not unit_results.get('overall_success', True):
                report['recommendations'].append("Critical unit tests are failing - address before production deployment")
            
            if report['summary']['overall_success_rate'] >= 95:
                report['recommendations'].append("Excellent test coverage - system appears production ready")
            
            return report
            
        except Exception as e:
            return {
                'error': f"Failed to generate report: {str(e)}"
            }
    
    def _cleanup_test_resources(self):
        """Clean up all test resources"""
        try:
            from UNIT_TEST.database_manager import TestDatabaseManager
            
            cleanup_summary = {
                'databases_cleaned': 0,
                'files_removed': 0,
                'errors': []
            }
            
            # Clean up databases
            db_manager = TestDatabaseManager()
            
            for resource_type, resource_path in self.test_session.get('cleanup_required', []):
                try:
                    if resource_type == 'database':
                        if os.path.exists(resource_path):
                            os.remove(resource_path)
                            cleanup_summary['databases_cleaned'] += 1
                    elif resource_type == 'file':
                        if os.path.exists(resource_path):
                            os.remove(resource_path)
                            cleanup_summary['files_removed'] += 1
                    elif resource_type == 'directory':
                        if os.path.exists(resource_path):
                            shutil.rmtree(resource_path)
                            cleanup_summary['files_removed'] += 1
                            
                except Exception as e:
                    cleanup_summary['errors'].append(f"Failed to clean {resource_path}: {str(e)}")
            
            # Clean up any remaining test databases
            try:
                db_manager.cleanup_all_test_databases()
            except Exception as e:
                cleanup_summary['errors'].append(f"Failed to clean all test databases: {str(e)}")
            
            self.test_session['cleanup_summary'] = cleanup_summary
            
        except Exception as e:
            print(f"Cleanup failed: {e}")

def run_quick_test():
    """Run a quick test to verify everything works"""
    controller = MasterTestController()
    
    quick_config = {
        'num_users': 10,
        'num_events': 2,
        'num_tournaments': 1,
        'run_unit_tests': True,
        'run_simulation': True,
        'run_roster_tests': True,
        'run_metrics_tests': True,
        'cleanup_after': True
    }
    
    results = controller.run_comprehensive_test_suite(quick_config)
    
    print("\n" + "="*60)
    print("QUICK TEST RESULTS SUMMARY")
    print("="*60)
    
    if results.get('test_results', {}).get('report', {}).get('summary'):
        summary = results['test_results']['report']['summary']
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed_tests']}")
        print(f"Failed: {summary['failed_tests']}")
        print(f"Success Rate: {summary['overall_success_rate']:.1f}%")
    
    print(f"Overall Success: {'YES' if results['overall_success'] else 'NO'}")
    print(f"Duration: {results.get('duration', 0):.1f} seconds")
    
    if results.get('test_results', {}).get('report', {}).get('recommendations'):
        print("\nRecommendations:")
        for rec in results['test_results']['report']['recommendations']:
            print(f"  • {rec}")
    
    print("="*60)
    
    return results

def integrate_with_main_app():
    """Integrate testing system with main Flask application"""
    try:
        # This would be called from the main app's __init__.py
        from UNIT_TEST.integration import integrate_testing_with_app
        
        print("Testing system integration available.")
        print("To enable testing mode in your Flask app:")
        print("  1. Add ENABLE_TESTING=True to your environment")
        print("  2. Or call integrate_testing_with_app(app) in your app factory")
        print("  3. Access testing dashboard at /test_dashboard")
        
        return True
        
    except ImportError as e:
        print(f"Integration failed: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Mason-SND Master Test Controller")
    parser.add_argument('--quick', action='store_true', help='Run quick test')
    parser.add_argument('--full', action='store_true', help='Run full test suite')
    parser.add_argument('--integrate', action='store_true', help='Show integration instructions')
    
    args = parser.parse_args()
    
    if args.quick:
        run_quick_test()
    elif args.full:
        controller = MasterTestController()
        results = controller.run_comprehensive_test_suite()
        print(f"Full test suite completed. Success: {results['overall_success']}")
    elif args.integrate:
        integrate_with_main_app()
    else:
        print("Mason-SND Testing System")
        print("Available commands:")
        print("  --quick     Run quick test")
        print("  --full      Run full test suite")
        print("  --integrate Show integration instructions")