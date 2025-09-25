"""
Database Manager for Test Suite
Handles creation, cloning, and cleanup of test databases in isolation from production.
Integrates with production safety guard for maximum protection.
"""
import os
import sqlite3
import shutil
from datetime import datetime
from .production_safety import get_safety_guard
import os
import shutil
import sqlite3
from datetime import datetime
import tempfile
from flask import current_app
from contextlib import contextmanager

class TestDatabaseManager:
    """
    Manages test databases with production safety integration.
    All operations are validated through the safety guard.
    """
    
    def __init__(self):
        # Get safety guard for production protection
        self.safety_guard = get_safety_guard()
        
        self.test_db_dir = os.path.join(os.path.dirname(__file__), "test_databases")
        self.production_db_path = "/workspaces/mason-snd/instance/db.sqlite3"
        self.test_databases = []
    
    def create_test_database(self, test_name="test"):
        """
        Create a new test database with safety validation
        
        Args:
            test_name: Name for the test database
            
        Returns:
            str: Path to the created test database
        """
        try:
            # Use safety guard to create isolated database
            test_db_path = self.safety_guard.create_isolated_test_database(test_name)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(test_db_path), exist_ok=True)
            
            # Clone production database safely if it exists
            if os.path.exists(self.production_db_path):
                print(f"🔄 Cloning production database for testing...")
                success = self.safety_guard.clone_production_safely(test_db_path)
                if not success:
                    # Create empty database if cloning fails
                    self._create_empty_database(test_db_path)
            else:
                print(f"⚠️  No production database found, creating empty test database")
                self._create_empty_database(test_db_path)
            
            # Register database
            self.test_databases.append(test_db_path)
            
            print(f"✅ Test database created: {os.path.basename(test_db_path)}")
            return test_db_path
            
        except Exception as e:
            print(f"❌ Failed to create test database: {e}")
            return None
    
    def _get_original_db_path(self):
        """Get the path to the original production database"""
        # Try to get from Flask config first
        try:
            db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
            if db_uri.startswith('sqlite:///'):
                return db_uri.replace('sqlite:///', '')
        except RuntimeError:
            # Not in Flask context
            pass
        
        # Fallback to instance directory
        instance_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance')
        return os.path.join(instance_path, 'db.sqlite3')
    
    def _create_empty_database(self):
        """Create an empty database with proper schema"""
        conn = sqlite3.connect(self.test_db_path)
        conn.close()
    
    @contextmanager
    def test_database_context(self, session_id=None):
        """
        Context manager for test database operations
        Automatically cleans up after testing
        """
        test_db_path = None
        try:
            test_db_path = self.create_test_database(session_id)
            yield test_db_path
        finally:
            if test_db_path:
                self.cleanup_test_database(test_db_path)
    
    def cleanup_test_database(self, test_db_path=None):
        """Remove test database after testing"""
        if test_db_path is None:
            test_db_path = self.test_db_path
        
        if test_db_path and os.path.exists(test_db_path):
            try:
                os.remove(test_db_path)
                print(f"Cleaned up test database: {test_db_path}")
            except OSError as e:
                print(f"Warning: Could not remove test database {test_db_path}: {e}")
    
    def cleanup_all_test_databases(self):
        """Remove all test databases with safety validation"""
        try:
            # Use safety guard for comprehensive cleanup
            cleanup_results = self.safety_guard.emergency_cleanup()
            
            # Also clean up tracked databases
            for db_path in list(self.test_databases):
                try:
                    if os.path.exists(db_path):
                        self.safety_guard.validate_test_database_path(db_path)
                        os.remove(db_path)
                        print(f"🗑️  Removed: {os.path.basename(db_path)}")
                    self.test_databases.remove(db_path)
                except Exception as e:
                    print(f"⚠️  Could not remove {db_path}: {e}")
            
            # Verify production database integrity
            integrity_check = self.safety_guard.verify_production_integrity()
            if not integrity_check['safe']:
                print(f"🚨 PRODUCTION INTEGRITY WARNING: {integrity_check}")
            else:
                print("✅ Production database integrity verified")
            
            return cleanup_results
            
        except Exception as e:
            print(f"❌ Cleanup failed: {e}")
            return {'error': str(e)}
    
    def cleanup_database(self, db_path):
        """
        Safely remove a test database with safety validation
        
        Args:
            db_path: Path to database to remove
            
        Returns:
            bool: Success status
        """
        try:
            # Validate this is a test database
            self.safety_guard.validate_test_database_path(db_path)
            
            if os.path.exists(db_path):
                os.remove(db_path)
                print(f"🗑️  Removed test database: {os.path.basename(db_path)}")
                
                # Remove from tracking
                if db_path in self.test_databases:
                    self.test_databases.remove(db_path)
                
                return True
            else:
                print(f"⚠️  Database not found: {db_path}")
                return False
                
        except ValueError as e:
            print(f"🚨 SAFETY VIOLATION: {e}")
            return False
        except Exception as e:
            print(f"❌ Failed to cleanup database: {e}")
            return False
    
    def list_test_databases(self):
        """List all existing test databases"""
        test_dbs = []
        
        # Check the safety guard's test resources
        try:
            safety_report = self.safety_guard.generate_safety_report()
            test_resources = safety_report.get('test_resources', {})
            
            # Get databases from safety guard
            if 'test_databases' in test_resources:
                for db_info in test_resources['test_databases']:
                    test_dbs.append(db_info['name'])
            
            # Also check temporary directories for active test databases
            import tempfile
            temp_dir = tempfile.gettempdir()
            
            for item in os.listdir(temp_dir):
                if item.startswith('mason_test_'):
                    test_dir = os.path.join(temp_dir, item)
                    if os.path.isdir(test_dir):
                        for db_file in os.listdir(test_dir):
                            if db_file.endswith('.db'):
                                test_dbs.append(db_file)
                                
        except Exception as e:
            print(f"Error listing test databases: {e}")
            
        # Remove duplicates and return
        return list(set(test_dbs))

class TestAppConfig:
    """Configuration manager for test environment"""
    
    @staticmethod
    def get_test_config(test_db_path):
        """
        Returns Flask configuration for testing environment
        
        Args:
            test_db_path: Path to the test database
            
        Returns:
            dict: Configuration dictionary
        """
        return {
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': f'sqlite:///{test_db_path}',
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
            'SECRET_KEY': 'test-secret-key-not-for-production',
            'WTF_CSRF_ENABLED': False,  # Disable CSRF for testing
            'SERVER_NAME': 'localhost:5000'
        }

def create_test_app(test_db_path=None, session_id=None):
    """
    Create a Flask app instance configured for testing
    
    Args:
        test_db_path: Optional path to existing test database
        session_id: Optional session identifier
        
    Returns:
        tuple: (Flask app, test database path)
    """
    from mason_snd import create_app
    
    # Create test database if not provided
    if test_db_path is None:
        db_manager = TestDatabaseManager()
        test_db_path = db_manager.create_test_database(session_id)
    
    # Create app with test configuration
    app = create_app()
    test_config = TestAppConfig.get_test_config(test_db_path)
    app.config.update(test_config)
    
    return app, test_db_path

# Convenience functions for common operations
def with_test_db(func):
    """Decorator to run a function with a test database"""
    def wrapper(*args, **kwargs):
        db_manager = TestDatabaseManager()
        with db_manager.test_database_context() as test_db_path:
            return func(test_db_path, *args, **kwargs)
    return wrapper

if __name__ == "__main__":
    # Example usage and testing
    db_manager = TestDatabaseManager()
    
    print("Creating test database...")
    test_db = db_manager.create_test_database("example_session")
    
    print(f"Test database created at: {test_db}")
    print(f"Existing test databases: {db_manager.list_test_databases()}")
    
    print("Cleaning up...")
    db_manager.cleanup_test_database()