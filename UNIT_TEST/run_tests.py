"""
Command-line test runner for Mason-SND unit tests.
Provides easy commands to run different test suites.
"""
import sys
import os
import argparse
from datetime import datetime

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def run_terminal_tests():
    """Run the complete terminal test suite"""
    print("🚀 Starting Mason-SND Terminal Tests")
    print("=" * 60)
    
    try:
        from terminal_tests.test_suite import main
        main()
    except ImportError as e:
        print(f"❌ Error importing test suite: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Test execution error: {e}")
        sys.exit(1)

def run_specific_test(test_class_name):
    """Run a specific test class"""
    print(f"🎯 Running specific test: {test_class_name}")
    print("=" * 60)
    
    try:
        from terminal_tests.test_suite import TestRunner
        import unittest
        
        # Import all test classes
        from terminal_tests.test_suite import (
            TestAuthRoutes, TestEventRoutes, TestTournamentRoutes,
            TestProfileRoutes, TestMetricsRoutes, TestRosterRoutes,
            TestAdminRoutes, TestMainRoutes, TestDataIntegrity
        )
        
        # Map test class names
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
        
        if test_class_name.lower() not in test_classes:
            print(f"❌ Unknown test class: {test_class_name}")
            print(f"Available classes: {', '.join(test_classes.keys())}")
            sys.exit(1)
        
        test_class = test_classes[test_class_name.lower()]
        
        # Run specific test class
        suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        # Print summary
        passed = result.testsRun - len(result.failures) - len(result.errors)
        success_rate = (passed / result.testsRun) * 100 if result.testsRun > 0 else 0
        
        print(f"\n📊 Results: {passed}/{result.testsRun} passed ({success_rate:.1f}%)")
        
        sys.exit(0 if result.wasSuccessful() else 1)
        
    except Exception as e:
        print(f"❌ Error running specific test: {e}")
        sys.exit(1)

def cleanup_test_databases():
    """Clean up all test databases"""
    print("🧹 Cleaning up test databases...")
    
    try:
        from database_manager import TestDatabaseManager
        db_manager = TestDatabaseManager()
        db_manager.cleanup_all_test_databases()
        print("✅ Test database cleanup completed")
    except Exception as e:
        print(f"❌ Cleanup error: {e}")

def list_test_databases():
    """List all existing test databases"""
    print("📋 Listing test databases...")
    
    try:
        from database_manager import TestDatabaseManager
        db_manager = TestDatabaseManager()
        databases = db_manager.list_test_databases()
        
        if not databases:
            print("No test databases found.")
        else:
            print(f"Found {len(databases)} test databases:")
            for db in databases:
                print(f"  📁 {db['name']}")
                print(f"     Size: {db['size']} bytes")
                print(f"     Created: {db['created']}")
                print()
    except Exception as e:
        print(f"❌ Error listing databases: {e}")

def generate_mock_data():
    """Generate sample mock data for testing"""
    print("🎭 Generating mock data...")
    
    try:
        from mock_data.generators import MockDataGenerator
        generator = MockDataGenerator()
        mock_data = generator.generate_complete_mock_scenario()
        
        print(f"✅ Generated mock data:")
        print(f"   👥 Users: {len(mock_data['users'])}")
        print(f"   📅 Events: {len(mock_data['events'])}")
        print(f"   🏆 Tournaments: {len(mock_data['tournaments'])}")
        print(f"   ⚖️ Judge relationships: {len(mock_data['judges'])}")
        
    except Exception as e:
        print(f"❌ Error generating mock data: {e}")

def install_test_dependencies():
    """Install required testing dependencies"""
    print("📦 Installing test dependencies...")
    
    try:
        import subprocess
        
        dependencies = ['pytest', 'pytest-flask', 'faker', 'coverage']
        
        for dep in dependencies:
            print(f"Installing {dep}...")
            result = subprocess.run([sys.executable, '-m', 'pip', 'install', dep], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ {dep} installed successfully")
            else:
                print(f"❌ Failed to install {dep}: {result.stderr}")
        
        print("✅ Test dependency installation completed")
        
    except Exception as e:
        print(f"❌ Error installing dependencies: {e}")

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Mason-SND Testing CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                          # Run all tests
  python run_tests.py --test auth              # Run authentication tests
  python run_tests.py --cleanup                # Clean up test databases
  python run_tests.py --list-db                # List test databases
  python run_tests.py --mock-data              # Generate mock data
  python run_tests.py --install-deps           # Install dependencies
        """
    )
    
    parser.add_argument('--test', '-t', 
                       help='Run specific test class (auth, events, tournaments, profile, metrics, rosters, admin, main, data)')
    parser.add_argument('--cleanup', '-c', action='store_true',
                       help='Clean up all test databases')
    parser.add_argument('--list-db', '-l', action='store_true',
                       help='List all test databases')
    parser.add_argument('--mock-data', '-m', action='store_true',
                       help='Generate sample mock data')
    parser.add_argument('--install-deps', '-i', action='store_true',
                       help='Install required testing dependencies')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    print("🔧 Mason-SND Testing CLI")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    if args.cleanup:
        cleanup_test_databases()
    elif args.list_db:
        list_test_databases()
    elif args.mock_data:
        generate_mock_data()
    elif args.install_deps:
        install_test_dependencies()
    elif args.test:
        run_specific_test(args.test)
    else:
        run_terminal_tests()

if __name__ == "__main__":
    main()