"""
Comprehensive terminal-based unit tests for mason-snd Flask application.
Tests all critical routes and functions with isolated test databases.
"""
import sys
import os
import pytest
import unittest
from datetime import datetime, timedelta
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from UNIT_TEST.database_manager import TestDatabaseManager, create_test_app
from UNIT_TEST.mock_data.generators import MockDataGenerator

class BaseTestCase(unittest.TestCase):
    """Base test case with common setup and teardown"""
    
    def setUp(self):
        """Set up test database and app context"""
        self.db_manager = TestDatabaseManager()
        self.test_db_path = self.db_manager.create_test_database(f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        self.app, _ = create_test_app(self.test_db_path)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Import models after app context is created
        from mason_snd.extensions import db
        db.create_all()
        self.db = db
        
        # Set up mock data generator
        self.mock_generator = MockDataGenerator(self.app_context)
        
    def tearDown(self):
        """Clean up test database and context"""
        self.app_context.pop()
        self.db_manager.cleanup_test_database(self.test_db_path)
    
    def create_test_user(self, **kwargs):
        """Helper method to create a test user"""
        from mason_snd.models.auth import User
        
        default_data = {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'password': 'testpass123',
            'role': 0,
            'is_parent': False,
            'account_claimed': True
        }
        default_data.update(kwargs)
        
        user = User(**default_data)
        self.db.session.add(user)
        self.db.session.commit()
        return user
    
    def login_user(self, email='test@example.com', password='testpass123'):
        """Helper method to log in a test user"""
        return self.client.post('/auth/login', data={
            'email': email,
            'password': password
        }, follow_redirects=True)

class TestAuthRoutes(BaseTestCase):
    """Test authentication and user management routes"""
    
    def test_01_user_registration(self):
        """Test user registration functionality"""
        response = self.client.post('/auth/register', data={
            'first_name': 'New',
            'last_name': 'User',
            'email': 'newuser@example.com',
            'password': 'newpass123',
            'confirm_password': 'newpass123',
            'phone_number': '123-456-7890'
        })
        
        # Should redirect on successful registration
        self.assertIn(response.status_code, [200, 302])
        
        # Verify user was created
        from mason_snd.models.auth import User
        user = User.query.filter_by(email='newuser@example.com').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.first_name, 'New')
    
    def test_02_user_login(self):
        """Test user login functionality"""
        # Create a test user first
        user = self.create_test_user()
        
        response = self.client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'testpass123'
        })
        
        # Should redirect on successful login
        self.assertIn(response.status_code, [200, 302])
    
    def test_03_user_logout(self):
        """Test user logout functionality"""
        user = self.create_test_user()
        self.login_user()
        
        response = self.client.get('/auth/logout')
        self.assertIn(response.status_code, [200, 302])

class TestEventRoutes(BaseTestCase):
    """Test event management routes"""
    
    def test_04_events_list_view(self):
        """Test events listing page"""
        user = self.create_test_user()
        self.login_user()
        
        response = self.client.get('/events/')
        self.assertEqual(response.status_code, 200)
    
    def test_05_add_event(self):
        """Test event creation"""
        user = self.create_test_user(role=1)  # EL role
        self.login_user()
        
        response = self.client.post('/events/add_event', data={
            'name': 'Test Event',
            'date': '2025-12-01',
            'description': 'Test event description',
            'capacity': '25',
            'location': 'Test Location',
            'mandatory': 'False',
            'points': '10'
        })
        
        # Should redirect on successful creation
        self.assertIn(response.status_code, [200, 302])
        
        # Verify event was created
        from mason_snd.models.events import Event
        event = Event.query.filter_by(name='Test Event').first()
        self.assertIsNotNone(event)
    
    def test_06_join_event(self):
        """Test joining an event"""
        user = self.create_test_user()
        self.login_user()
        
        # Create an event first
        from mason_snd.models.events import Event
        event = Event(
            name='Join Test Event',
            date=datetime.now().date(),
            description='Test event for joining',
            capacity=25,
            leader_id=user.id,
            points=10
        )
        self.db.session.add(event)
        self.db.session.commit()
        
        response = self.client.post(f'/events/join_event/{event.id}')
        self.assertIn(response.status_code, [200, 302])
    
    def test_07_leave_event(self):
        """Test leaving an event"""
        user = self.create_test_user()
        self.login_user()
        
        # Create event and join it first
        from mason_snd.models.events import Event, User_Event
        event = Event(
            name='Leave Test Event',
            date=datetime.now().date(),
            description='Test event for leaving',
            capacity=25,
            leader_id=user.id,
            points=10
        )
        self.db.session.add(event)
        self.db.session.commit()
        
        # Join the event
        user_event = User_Event(user_id=user.id, event_id=event.id)
        self.db.session.add(user_event)
        self.db.session.commit()
        
        response = self.client.post(f'/events/leave_event/{event.id}')
        self.assertIn(response.status_code, [200, 302])

class TestTournamentRoutes(BaseTestCase):
    """Test tournament management routes"""
    
    def test_08_tournaments_list_view(self):
        """Test tournaments listing page"""
        user = self.create_test_user()
        self.login_user()
        
        response = self.client.get('/tournaments/')
        self.assertEqual(response.status_code, 200)
    
    def test_09_add_tournament(self):
        """Test tournament creation"""
        user = self.create_test_user(role=1)  # EL role
        self.login_user()
        
        response = self.client.post('/tournaments/add_tournament', data={
            'name': 'Test Tournament',
            'date': '2025-12-15',
            'signup_deadline': '2025-12-01',
            'description': 'Test tournament description',
            'location': 'Test Location',
            'entry_fee': '50',
            'max_participants': '40'
        })
        
        self.assertIn(response.status_code, [200, 302])
        
        # Verify tournament was created
        from mason_snd.models.tournaments import Tournament
        tournament = Tournament.query.filter_by(name='Test Tournament').first()
        self.assertIsNotNone(tournament)
    
    def test_10_tournament_signup(self):
        """Test tournament signup functionality"""
        user = self.create_test_user()
        self.login_user()
        
        # Create a tournament first
        from mason_snd.models.tournaments import Tournament
        tournament = Tournament(
            name='Signup Test Tournament',
            date=datetime.now().date() + timedelta(days=30),
            signup_deadline=datetime.now().date() + timedelta(days=15),
            description='Test tournament for signup',
            created_by=user.id,
            active=True
        )
        self.db.session.add(tournament)
        self.db.session.commit()
        
        response = self.client.post('/tournaments/signup', data={
            'tournament_id': tournament.id,
            'bringing_judge': 'True',
            'dietary_restrictions': 'None'
        })
        
        self.assertIn(response.status_code, [200, 302])

class TestProfileRoutes(BaseTestCase):
    """Test user profile management routes"""
    
    def test_11_view_user_profile(self):
        """Test viewing user profile"""
        user = self.create_test_user()
        self.login_user()
        
        response = self.client.get(f'/profile/user/{user.id}')
        self.assertEqual(response.status_code, 200)
    
    def test_12_update_profile(self):
        """Test updating user profile"""
        user = self.create_test_user()
        self.login_user()
        
        response = self.client.post('/profile/update', data={
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'updated@example.com',
            'phone_number': '987-654-3210'
        })
        
        self.assertIn(response.status_code, [200, 302])
    
    def test_13_add_judge(self):
        """Test adding a judge relationship"""
        parent = self.create_test_user(is_parent=True)
        self.login_user()
        
        response = self.client.post('/profile/add_judge', data={
            'judge_first_name': 'Judge',
            'judge_last_name': 'Parent',
            'judge_email': 'judge@example.com',
            'judge_phone': '555-123-4567',
            'child_first_name': 'Child',
            'child_last_name': 'Competitor',
            'background_check': 'True'
        })
        
        self.assertIn(response.status_code, [200, 302])

class TestMetricsRoutes(BaseTestCase):
    """Test metrics and analytics routes"""
    
    def test_14_metrics_overview(self):
        """Test metrics overview page"""
        user = self.create_test_user()
        self.login_user()
        
        response = self.client.get('/metrics/')
        self.assertEqual(response.status_code, 200)
    
    def test_15_user_metrics(self):
        """Test user metrics page"""
        user = self.create_test_user()
        self.login_user()
        
        response = self.client.get('/metrics/user_metrics')
        self.assertEqual(response.status_code, 200)
    
    def test_16_my_metrics(self):
        """Test personal metrics page"""
        user = self.create_test_user()
        self.login_user()
        
        response = self.client.get('/metrics/my_metrics')
        self.assertEqual(response.status_code, 200)
    
    def test_17_tournament_metrics(self):
        """Test tournament metrics page"""
        user = self.create_test_user()
        self.login_user()
        
        response = self.client.get('/metrics/tournaments')
        self.assertEqual(response.status_code, 200)

class TestRosterRoutes(BaseTestCase):
    """Test roster management routes"""
    
    def test_18_rosters_list_view(self):
        """Test rosters listing page"""
        user = self.create_test_user()
        self.login_user()
        
        response = self.client.get('/rosters/')
        self.assertEqual(response.status_code, 200)
    
    def test_19_view_tournament_roster(self):
        """Test viewing tournament roster"""
        user = self.create_test_user()
        self.login_user()
        
        # Create a tournament first
        from mason_snd.models.tournaments import Tournament
        tournament = Tournament(
            name='Roster Test Tournament',
            date=datetime.now().date() + timedelta(days=30),
            signup_deadline=datetime.now().date() + timedelta(days=15),
            description='Test tournament for roster',
            created_by=user.id,
            active=True
        )
        self.db.session.add(tournament)
        self.db.session.commit()
        
        response = self.client.get(f'/rosters/view_tournament/{tournament.id}')
        self.assertEqual(response.status_code, 200)
    
    def test_20_download_tournament_roster(self):
        """Test downloading tournament roster"""
        user = self.create_test_user()
        self.login_user()
        
        # Create a tournament first
        from mason_snd.models.tournaments import Tournament
        tournament = Tournament(
            name='Download Test Tournament',
            date=datetime.now().date() + timedelta(days=30),
            signup_deadline=datetime.now().date() + timedelta(days=15),
            description='Test tournament for download',
            created_by=user.id,
            active=True
        )
        self.db.session.add(tournament)
        self.db.session.commit()
        
        response = self.client.get(f'/rosters/download_tournament/{tournament.id}')
        # Should return a file download or redirect
        self.assertIn(response.status_code, [200, 302, 404])  # 404 if no signups yet

class TestAdminRoutes(BaseTestCase):
    """Test admin functionality routes"""
    
    def test_21_admin_dashboard(self):
        """Test admin dashboard access"""
        admin_user = self.create_test_user(role=2)  # Chair+ role
        self.login_user()
        
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)
    
    def test_22_admin_user_search(self):
        """Test admin user search functionality"""
        admin_user = self.create_test_user(role=2)
        self.login_user()
        
        response = self.client.post('/admin/search', data={
            'search_query': 'test',
            'search_type': 'name'
        })
        
        self.assertIn(response.status_code, [200, 302])
    
    def test_23_admin_requirements_management(self):
        """Test admin requirements management"""
        admin_user = self.create_test_user(role=2)
        self.login_user()
        
        response = self.client.get('/admin/requirements')
        self.assertEqual(response.status_code, 200)

class TestMainRoutes(BaseTestCase):
    """Test main application routes"""
    
    def test_24_homepage(self):
        """Test homepage accessibility"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
    
    def test_25_life_check(self):
        """Test life/health check endpoint"""
        response = self.client.get('/life')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Life is good', response.data)
    
    def test_26_favicon(self):
        """Test favicon endpoint"""
        response = self.client.get('/favicon.ico')
        self.assertIn(response.status_code, [200, 404])  # May not exist in test
    
    def test_27_sitemap(self):
        """Test sitemap generation"""
        response = self.client.get('/sitemap.xml')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content_type.startswith('application/xml'))
    
    def test_28_robots_txt(self):
        """Test robots.txt file"""
        response = self.client.get('/robots.txt')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content_type.startswith('text/plain'))

class TestDataIntegrity(BaseTestCase):
    """Test data integrity and business logic"""
    
    def test_29_user_points_calculation(self):
        """Test user points calculation from tournaments and events"""
        user = self.create_test_user()
        
        # Add some tournament performance
        from mason_snd.models.tournaments import Tournament_Performance
        performance = Tournament_Performance(
            user_id=user.id,
            tournament_id=1,
            points=50,
            rank=5
        )
        self.db.session.add(performance)
        
        # Add some effort scores
        from mason_snd.models.events import Effort_Score
        effort = Effort_Score(
            user_id=user.id,
            event_id=1,
            score=25
        )
        self.db.session.add(effort)
        self.db.session.commit()
        
        # Test point calculations
        self.assertEqual(user.tournament_points, 50)
        self.assertEqual(user.effort_points, 25)
    
    def test_30_tournament_capacity_constraints(self):
        """Test tournament capacity and signup constraints"""
        from mason_snd.models.tournaments import Tournament, Tournament_Signups
        
        user1 = self.create_test_user(email='user1@test.com')
        user2 = self.create_test_user(email='user2@test.com')
        
        # Create tournament with capacity of 1
        tournament = Tournament(
            name='Capacity Test Tournament',
            date=datetime.now().date() + timedelta(days=30),
            signup_deadline=datetime.now().date() + timedelta(days=15),
            max_participants=1,
            created_by=user1.id,
            active=True
        )
        self.db.session.add(tournament)
        self.db.session.commit()
        
        # First signup should succeed
        signup1 = Tournament_Signups(
            tournament_id=tournament.id,
            user_id=user1.id,
            signup_date=datetime.now().date()
        )
        self.db.session.add(signup1)
        self.db.session.commit()
        
        # Check current signups
        current_signups = Tournament_Signups.query.filter_by(tournament_id=tournament.id).count()
        self.assertEqual(current_signups, 1)
        
        # Verify capacity constraint logic would be handled by application
        self.assertTrue(current_signups <= tournament.max_participants)

# Test runner and result reporting
class TestRunner:
    """Manages test execution and reporting"""
    
    def __init__(self):
        self.results = {
            'passed': 0,
            'failed': 0,
            'errors': 0,
            'total': 0,
            'details': []
        }
    
    def run_all_tests(self):
        """Run all test cases and collect results"""
        # Get all test classes
        test_classes = [
            TestAuthRoutes,
            TestEventRoutes, 
            TestTournamentRoutes,
            TestProfileRoutes,
            TestMetricsRoutes,
            TestRosterRoutes,
            TestAdminRoutes,
            TestMainRoutes,
            TestDataIntegrity
        ]
        
        print("Running Mason-SND Unit Tests...")
        print("=" * 50)
        
        for test_class in test_classes:
            print(f"\nRunning {test_class.__name__}...")
            
            # Create test suite
            suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
            
            # Run tests
            runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
            result = runner.run(suite)
            
            # Collect results
            class_results = {
                'class': test_class.__name__,
                'passed': result.testsRun - len(result.failures) - len(result.errors),
                'failed': len(result.failures),
                'errors': len(result.errors),
                'total': result.testsRun,
                'failures': result.failures,
                'errors': result.errors
            }
            
            self.results['passed'] += class_results['passed']
            self.results['failed'] += class_results['failed']
            self.results['errors'] += class_results['errors']
            self.results['total'] += class_results['total']
            self.results['details'].append(class_results)
            
            # Print progress
            print(f"  {class_results['passed']}/{class_results['total']} passed")
            
            if class_results['failed'] > 0 or class_results['errors'] > 0:
                print(f"  ❌ {class_results['failed']} failures, {class_results['errors']} errors")
            else:
                print(f"  ✅ All tests passed")
        
        return self.results
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "=" * 50)
        print("TEST RESULTS SUMMARY")
        print("=" * 50)
        
        success_rate = (self.results['passed'] / self.results['total']) * 100 if self.results['total'] > 0 else 0
        
        print(f"Total Tests: {self.results['total']}")
        print(f"Passed: {self.results['passed']} ✅")
        print(f"Failed: {self.results['failed']} ❌")
        print(f"Errors: {self.results['errors']} ⚠️")
        print(f"Success Rate: {success_rate:.1f}%")
        
        if self.results['failed'] > 0 or self.results['errors'] > 0:
            print("\nFAILED TESTS:")
            for class_result in self.results['details']:
                if class_result['failed'] > 0 or class_result['errors'] > 0:
                    print(f"\n{class_result['class']}:")
                    
                    for failure in class_result['failures']:
                        test_name = failure[0]._testMethodName
                        print(f"  ❌ {test_name}: {failure[1].split('AssertionError:')[-1].strip()}")
                    
                    for error in class_result['errors']:
                        test_name = error[0]._testMethodName
                        print(f"  ⚠️ {test_name}: {error[1].split('Exception:')[-1].strip()}")
        
        print("\n" + "=" * 50)
        
        # Return success status
        return self.results['failed'] == 0 and self.results['errors'] == 0

def main():
    """Main entry point for terminal tests"""
    print("Mason-SND Terminal Unit Test Suite")
    print(f"Starting tests at {datetime.now()}")
    
    # Add dependencies
    from UNIT_TEST.mock_data.generators import add_required_dependencies
    add_required_dependencies()
    
    # Run tests
    runner = TestRunner()
    results = runner.run_all_tests()
    success = runner.print_summary()
    
    # Cleanup any remaining test databases
    db_manager = TestDatabaseManager()
    db_manager.cleanup_all_test_databases()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()